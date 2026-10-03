"""Run from the project folder: python -m unittest discover -s tests -v"""

import unittest
from unittest.mock import patch

import requests

from analysis import classify_paper, extract_statistics, identify_study_type
from app import app
from research import SearchError, make_search_terms, parse_papers, search_pubmed

QUESTION = "Does social media use increase depression in teenagers?"


class AnalysisTests(unittest.TestCase):
    def test_statistics_preserve_text_and_missing_values(self):
        result = extract_statistics("N = 245; study included 1,200 patients. p < 0.05; p = 0.032; p >= .10; 95% CI: -0.2 to 0.8.")
        self.assertEqual(result["sample_size"], "N = 245; 1,200 patients")
        self.assertEqual(result["p_value"], "p < 0.05; p = 0.032; p >= .10")
        self.assertEqual(result["confidence_interval"], "95% CI: -0.2 to 0.8")
        self.assertTrue(all(value == "Not reported" for value in extract_statistics("").values()))
        self.assertEqual(extract_statistics("over 11 000 participants")["sample_size"], "11 000 participants")

    def test_directions_and_uncertainty(self):
        self.assertEqual(classify_paper(QUESTION, "Results: Social media use was associated with higher depression."), "supporting")
        self.assertEqual(classify_paper(QUESTION.replace("increase", "decrease"), "Results: Social media use was associated with higher depression."), "conflicting")
        self.assertEqual(classify_paper(QUESTION, "Results: There was no significant association between social media use and depression."), "conflicting")
        self.assertEqual(classify_paper(QUESTION, "Results: Social media use and depression had mixed associations."), "nuanced")
        self.assertEqual(classify_paper(QUESTION, "Results: Social media use was associated with higher depression. Conclusions: Social media use was associated with lower depression."), "nuanced")

    def test_unrelated_background_negation_and_causation_stay_unclear(self):
        for question, abstract in [
            (QUESTION, "Results: Exercise was associated with lower blood pressure."),
            (QUESTION, "Background: Social media use was associated with higher depression."),
            (QUESTION, "Results: Social media use was not associated with higher depression."),
            (QUESTION.replace("increase", "not increase"), "Results: Social media use was associated with higher depression."),
            (QUESTION.replace("increase", "cause"), "Results: Social media use was associated with higher depression."),
            ("Does screen time negatively affect sleep?", "Results: Screen time was associated with poor sleep."),
        ]:
            with self.subTest(question=question, abstract=abstract):
                self.assertIn(classify_paper(question, abstract), ("unclear", "conflicting"))
        self.assertEqual(identify_study_type("", []), "Not identified")
        self.assertEqual(identify_study_type("", ["Randomized Controlled Trial"]), "Randomized Controlled Trial")


class PubMedTests(unittest.TestCase):
    def test_query_removes_direction(self):
        self.assertEqual(make_search_terms(QUESTION), "social media depression teenagers")

    def test_xml_metadata_missing_fields_and_markup(self):
        xml = '''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
        <Article><ArticleTitle>Some <i>formatted</i> title</ArticleTitle>
        <Abstract><AbstractText Label="RESULTS">N = 50. p &lt; 0.05.</AbstractText></Abstract>
        <Journal><Title>Example journal</Title><JournalIssue><PubDate><MedlineDate>2020 Jan-Feb</MedlineDate></PubDate></JournalIssue></Journal>
        <AuthorList><Author><ForeName>Alex</ForeName><LastName>Example</LastName></Author></AuthorList>
        <GrantList><Grant><Agency>Example funder</Agency><GrantID>ABC</GrantID></Grant></GrantList>
        </Article><CoiStatement>No competing interests.</CoiStatement></MedlineCitation>
        <PubmedData><ArticleIdList><ArticleId IdType="doi">10.example/test</ArticleId></ArticleIdList></PubmedData>
        </PubmedArticle></PubmedArticleSet>'''
        paper = parse_papers(xml)[0]
        self.assertEqual(paper["title"], "Some formatted title")
        self.assertEqual(paper["year"], "2020")
        self.assertEqual(paper["authors"], "Alex Example")
        self.assertEqual(paper["abstract"], "RESULTS: N = 50. p < 0.05.")
        self.assertEqual(paper["funding"], "Example funder — ABC")
        self.assertEqual(paper["disclosure"], "No competing interests.")
        self.assertEqual(paper["doi"], "10.example/test")
        missing = parse_papers("<PubmedArticleSet><PubmedArticle><MedlineCitation><Article/></MedlineCitation></PubmedArticle></PubmedArticleSet>")[0]
        self.assertEqual(missing["funding"], "Not reported")
        self.assertEqual(missing["abstract"], "")

    @patch("research.api_get")
    def test_no_results_and_bad_response(self, get):
        get.return_value.json.return_value = {"esearchresult": {"idlist": []}}
        self.assertEqual(search_pubmed(QUESTION)[0], [])
        get.return_value.json.return_value = {"error": "unavailable"}
        with self.assertRaises(SearchError):
            search_pubmed(QUESTION)

    @patch("research.api_get")
    def test_timeout_and_rate_limit(self, get):
        get.side_effect = requests.Timeout()
        with self.assertRaises(SearchError):
            search_pubmed(QUESTION)
        response = requests.Response()
        response.status_code = 429
        get.side_effect = requests.HTTPError(response=response)
        with self.assertRaisesRegex(SearchError, "too many requests"):
            search_pubmed(QUESTION)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_page_and_offline_demo(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        with patch("app.search_pubmed", side_effect=AssertionError("Demo must be offline")):
            response = self.client.post("/api/search", json={"question": "some other question", "demo": True})
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["question"], QUESTION)
        self.assertEqual(data["counts"], {"supporting": 2, "conflicting": 1, "nuanced": 1, "unclear": 2})
        self.assertTrue(all("FICTIONAL SAMPLE" in paper["title"] for paper in data["papers"]))

    def test_invalid_input(self):
        for data in ({}, {"question": []}, {"question": "x"}, {"question": "x" * 501}, ["question"]):
            self.assertEqual(self.client.post("/api/search", json=data).status_code, 400)
        self.assertEqual(self.client.post("/api/search", json={"question": "x" * 9000}).status_code, 413)

    @patch("app.search_pubmed")
    def test_live_success_empty_and_failure(self, search):
        search.return_value = ([], "social media depression")
        response = self.client.post("/api/search", json={"question": QUESTION})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["papers"], [])
        search.side_effect = SearchError("Try later")
        response = self.client.post("/api/search", json={"question": QUESTION})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"], "Try later")


if __name__ == "__main__":
    unittest.main()
