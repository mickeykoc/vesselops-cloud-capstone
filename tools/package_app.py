"""Allowlist deployable files so evidence, state and local databases stay out."""

import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / "wsgi.py", ROOT / "requirements.txt"]
    paths += [
        p
        for p in (ROOT / "app").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".html", ".css", ".js")
    ]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, path.relative_to(ROOT))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(package(parser.parse_args().output))
