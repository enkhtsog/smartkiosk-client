"""Package the compiled Smartkiosk Windows x64 client using upstream WiX."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path,
                        default=ROOT / "flutter/build/windows/x64/runner/Release")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only")
    args = parser.parse_args()
    missing = []
    for tool in ("nuget", "msbuild"):
        if not shutil.which(tool):
            missing.append(f"{tool} is missing from PATH")
    for name in ("rustdesk.exe", "librustdesk.dll", "flutter_windows.dll", "data"):
        if not (args.dist / name).exists():
            missing.append(f"Missing compiled client payload: {args.dist / name}")
    if os.name != "nt":
        missing.append("Packaging requires Windows and Visual Studio 2022 C++ tools")
    if missing:
        raise RuntimeError("\n".join(missing))
    if args.check:
        print("Packaging prerequisites found; no installer was built.")
        return

    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output.resolve()
    with tempfile.TemporaryDirectory(prefix="smartkiosk-msi-") as temporary:
        stage = Path(temporary)
        payload = stage / "payload"
        shutil.copytree(args.dist, payload)
        (payload / "rustdesk.exe").rename(payload / "Smartkiosk.exe")
        shutil.copy2(ROOT / "LICENCE", payload / "LICENCE")
        (payload / "UPSTREAM.txt").write_text(
            "Smartkiosk is a customized build of RustDesk.\n"
            "Upstream: https://github.com/rustdesk/rustdesk\n"
            "Original copyright and license notices are retained.\n",
            encoding="utf-8",
        )
        msi = stage / "msi"
        shutil.copytree(ROOT / "res/msi", msi)
        shutil.copy2(ROOT / "res/icon.ico", stage / "icon.ico")
        # Always create and start the Windows service, even if an old config
        # file on the machine contains stop-service = 'Y'.
        wxs = msi / "Package/Components/RustDesk.wxs"
        wxs_text = wxs.read_text(encoding="utf-8")
        stop_condition = "STOP_SERVICE=&quot;&apos;Y&apos;&quot;"
        if wxs_text.count(stop_condition) != 5:
            raise RuntimeError("Unexpected STOP_SERVICE conditions in RustDesk.wxs")
        wxs.write_text(wxs_text.replace(stop_condition, "0"), encoding="utf-8")
        run([sys.executable, "preprocess.py", "--app-name", "Smartkiosk",
             "--manufacturer", "Smartkiosk", "-d", "../payload"], msi)
        # This fork uses the repository license, not the branded upstream EULA.
        license_text = (ROOT / "LICENCE").read_text(encoding="utf-8")
        escaped = license_text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        escaped = escaped.replace("\n", "\\par\n")
        (msi / "Package/License.rtf").write_text(
            "{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Courier New;}}\\f0\\fs16\n"
            + escaped + "\n}", encoding="utf-8",
        )
        run(["nuget", "restore", "msi.sln"], msi)
        run(["msbuild", "msi.sln", "-restore", "-p:Configuration=Release",
             "-p:Platform=x64", "/p:TargetVersion=Windows10"], msi)
        candidates = list((msi / "Package/bin").glob("*/Release/en-us/Package.msi"))
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one MSI, found {len(candidates)}")
        destination = output / "Smartkiosk-Setup-x64.msi"
        shutil.copy2(candidates[0], destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        destination.with_suffix(".msi.sha256").write_text(
            f"{digest}  {destination.name}\n", encoding="ascii",
        )
        print(f"Created unsigned installer: {destination}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Cannot build Smartkiosk MSI: {error}", file=sys.stderr)
        sys.exit(1)
