# Build this same file on Windows or macOS. Only read-only resources are included.
import sys
from pathlib import Path

root = Path(SPECPATH)
analysis = Analysis(
    [str(root / "launcher.py")],
    pathex=[str(root)],
    datas=[(str(root / "templates"), "templates"),
           (str(root / "static"), "static"),
           (str(root / "demo.json"), ".")],
    excludes=["tkinter"],
)
archive = PYZ(analysis.pure)
executable = EXE(archive, analysis.scripts, [], exclude_binaries=True,
                 name="PaperSift", console=False, debug=False, upx=False)
distribution = COLLECT(executable, analysis.binaries, analysis.datas,
                       name="PaperSift", upx=False)
if sys.platform == "darwin":
    bundle = BUNDLE(distribution, name="PaperSift.app",
                    bundle_identifier="org.papersift.local",
                    info_plist={"CFBundleShortVersionString": "1.0.0",
                                "NSHighResolutionCapable": True})
