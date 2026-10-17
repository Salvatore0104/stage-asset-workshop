"""Check a completed workshop PNG export. Requires Pillow."""
import argparse
import json
from pathlib import Path
import sys


def check(root):
    from PIL import Image
    data = json.loads((root / "export_manifest.json").read_text(encoding="utf-8"))
    errors = []
    if not data.get("complete"):
        errors.append("Export is incomplete")
    total = 0
    for layer in data["layers"]:
        directory = root / layer["id"]
        files = sorted(directory.glob("*.png"))
        if len(files) != layer["expectedFiles"]:
            errors.append(f"{layer['id']}: count {len(files)} != {layer['expectedFiles']}")
        start = data["sourceFrameStart"]
        indexes = [start] if layer["static"] else range(start, data["sourceFrameEnd"] + 1)
        expected = {f"{data['partId']}_{layer['id']}_{i:06d}.png" for i in indexes}
        if {p.name for p in files} != expected:
            errors.append(f"{layer['id']}: filenames or frame continuity mismatch")
        for path in files:
            try:
                with Image.open(path) as image:
                    image.load()
                    if image.size != (data["width"], data["height"]):
                        errors.append(f"Wrong dimensions: {path.name}")
                    if "A" not in image.getbands():
                        errors.append(f"No alpha channel: {path.name}")
            except Exception as error:
                errors.append(f"Invalid PNG {path.name}: {error}")
        total += len(files)
    if total != data.get("writtenFiles"):
        errors.append("writtenFiles total mismatch")
    if errors:
        raise ValueError("\n".join(errors[:30]))
    print(f"PASS: {total} PNG files; dimensions, alpha, names, continuity and completion checked")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    check(args.folder.resolve())
