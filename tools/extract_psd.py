"""Optional PSD inspection/export. Requires Pillow and psd-tools.
Raw layer PNGs are not a Photoshop-equivalent flattened composite.
"""
import argparse
import json
from pathlib import Path
import re
import sys


def extract(source, out):
    from psd_tools import PSDImage
    psd = PSDImage.open(source)
    out.mkdir(parents=True, exist_ok=False)
    records = []
    composite = psd.composite()
    if composite is not None:
        composite.save(out / "reference_composite.png")

    def walk(group, parents):
        for index, layer in enumerate(group):
            path = parents + [layer.name]
            rec = {"index": len(records), "siblingIndex": index, "name": layer.name,
                   "path": "/".join(path), "kind": str(layer.kind), "bbox": list(layer.bbox),
                   "visible": bool(layer.visible), "opacity": layer.opacity,
                   "blend": str(layer.blend_mode), "group": layer.is_group()}
            records.append(rec)
            if layer.is_group():
                walk(layer, path)
                continue
            try:
                image = layer.topil()
                if image is not None:
                    label = re.sub(r'[\\/:*?"<>|\s]+', '_', layer.name)[:60].strip(' .') or 'layer'
                    name = f"{rec['index']:04d}_{label}.png"
                    image.save(out / name)
                    rec.update(png=name, png_size=list(image.size), extraction="raw_pixels")
                else:
                    rec["note"] = "No raw pixels; adjustment/effect/shape may require Photoshop export."
            except Exception as error:
                rec["error"] = str(error)
    walk(psd, [])
    manifest = {"source": source.name, "size": list(psd.size), "layers": records,
                "note": "Preserve bbox offsets. Raw pixels do not bake group opacity, adjustments, masks or layer effects. Compare reference against designer's Photoshop export."}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(records)} layer records to {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path, help="New directory")
    args = parser.parse_args()
    extract(args.source.resolve(), args.out.resolve())
