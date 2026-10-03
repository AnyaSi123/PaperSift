const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');

async function harness(close = () => {}) {
  const nodes = new Map();
  function node(selector) {
    if (!nodes.has(selector)) nodes.set(selector, {
      disabled: false, hidden: true, textContent: '', dataset: { token: 'test-token' },
      listeners: {}, addEventListener(name, callback) { this.listeners[name] = callback; },
      replaceChildren() {},
    });
    return nodes.get(selector);
  }
  let finishQuit;
  let request;
  let closes = 0;
  const context = vm.createContext({
    document: { querySelector: node, querySelectorAll: () => [node('#quit-button')] },
    window: { close() { closes++; close(); } },
    fetch: async (url, options) => {
      if (url === '/api/topics') return { ok: true, json: async () => ({ topics: [] }) };
      assert.equal(url, '/api/quit');
      request = options;
      return new Promise(resolve => { finishQuit = resolve; });
    },
  });
  vm.runInContext(readFileSync(join(__dirname, '../static/script.js'), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  return { node, get closes() { return closes; }, get request() { return request; },
    click: () => node('#quit-button').listeners.click(),
    respond: ok => finishQuit({ ok, json: async () => ({}) }),
  };
}

test('Quit waits for successful authenticated shutdown before closing the tab', async () => {
  const app = await harness();
  const pending = app.click();
  assert.equal(app.closes, 0);
  assert.equal(app.request.method, 'POST');
  assert.equal(app.request.headers['X-PaperSift-Quit'], 'test-token');
  app.respond(true);
  await pending;
  assert.equal(app.closes, 1);
  assert.equal(app.node('#quit-button').disabled, true);
});

test('Rejected shutdown keeps tab open and enables retry', async () => {
  const app = await harness();
  const pending = app.click();
  app.respond(false);
  await pending;
  assert.equal(app.closes, 0);
  assert.equal(app.node('#quit-button').disabled, false);
  assert.equal(app.node('#error').hidden, false);
});

for (const mode of ['ignored', 'throws']) {
  test(`Blocked tab closure (${mode}) keeps successful shutdown message`, async () => {
    const app = await harness(() => { if (mode === 'throws') throw new Error('Blocked'); });
    const pending = app.click();
    app.respond(true);
    await pending;
    assert.match(app.node('#status').textContent, /PaperSift has stopped/);
    assert.equal(app.node('#quit-button').disabled, true);
    assert.equal(app.node('#error').hidden, true);
  });
}
