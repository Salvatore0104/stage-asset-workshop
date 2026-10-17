"""Build the portable workshop. Standard library only; paths are config-relative."""
import argparse
import base64
import json
import math
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def positive(value, name, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name}: must be a positive finite number")
    if integer and int(value) != value:
        raise ValueError(f"{name}: must be an integer")


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise ValueError(f"Invalid ID: {value!r}; use letters, digits, _ and -")


def validate(config, base):
    if config.get("schemaVersion") != 1:
        raise ValueError("Unsupported schemaVersion")
    valid_id(config["projectId"])
    w, h = config["stage"]["width"], config["stage"]["height"]
    positive(w, "width", True)
    positive(h, "height", True)
    positive(config["fps"], "fps", True)
    positive(config["bpm"], "bpm")
    positive(config["previewMaxWidth"], "previewMaxWidth", True)
    for key in ("imageSmoothing", "clipExportToStage"):
        if not isinstance(config[key], bool):
            raise ValueError(f"{key} must be boolean")

    def check_mask(mask):
        if mask["type"] == "image":
            if mask.get("channel") not in ("alpha", "luminance"):
                raise ValueError("Mask channel must be alpha or luminance")
            if not isinstance(mask.get("invert", False), bool):
                raise ValueError("Mask invert must be boolean")
            path = base / mask["file"]
            with path.open("rb") as stream:
                header = stream.read(24)
            if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError(f"Mask must be PNG: {path}")
            if struct.unpack(">II", header[16:24]) != (w, h):
                raise ValueError(f"Mask size must equal stage {w}x{h}: {path}")
        elif mask["type"] == "geometry":
            if not mask["shapes"]:
                raise ValueError("Mask shapes cannot be empty")
            for shape in mask["shapes"]:
                if shape["type"] == "rect":
                    positive(shape["w"], "mask w")
                    positive(shape["h"], "mask h")
                    points = [(shape["x"], shape["y"]), (shape["x"] + shape["w"], shape["y"] + shape["h"])]
                elif shape["type"] == "polygon" and len(shape["points"]) >= 3:
                    points = shape["points"]
                else:
                    raise ValueError("Mask shape must be rect or polygon with >=3 points")
                for x, y in points:
                    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (x, y)):
                        raise ValueError("Mask coordinates must be finite numbers")
                    if not (0 <= x <= w and 0 <= y <= h):
                        raise ValueError(f"Mask point outside stage: {(x, y)}")
        else:
            raise ValueError("Mask type must be geometry or image")

    check_mask(config["stageMask"])
    if not isinstance(config["pgm"]["enabled"], bool):
        raise ValueError("pgm.enabled must be boolean")
    if config["pgm"]["enabled"]:
        check_mask(config["pgm"]["mask"])
    ids = set()
    if not config["parts"]:
        raise ValueError("At least one part required")
    for part in config["parts"]:
        valid_id(part["id"])
        if part["id"] in ids:
            raise ValueError("Duplicate part ID")
        ids.add(part["id"])
        if part["duration"]["unit"] not in ("seconds", "beats"):
            raise ValueError("Duration unit must be seconds or beats")
        positive(part["duration"]["value"], "duration")
        if not isinstance(part["loop"], bool):
            raise ValueError("Part loop must be boolean")
        layer_ids = set()
        if not part["layers"]:
            raise ValueError("Part needs at least one layer")
        for layer in part["layers"]:
            valid_id(layer["id"])
            if layer["id"] in layer_ids or layer["id"] in ("stage_mask", "pgm_matte", "comp", "all"):
                raise ValueError("Duplicate or reserved layer ID")
            layer_ids.add(layer["id"])
            for key in ("static", "cutPgm", "defaultVisible"):
                if key in layer and not isinstance(layer[key], bool):
                    raise ValueError(f"Layer {key} must be boolean")
    for key, asset in config["assets"].items():
        valid_id(key)
        for field in ("x", "y", "w", "h"):
            value = asset[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise ValueError(f"Invalid asset coordinate {key}.{field}")
        positive(asset["w"], f"{key}.w")
        positive(asset["h"], f"{key}.h")
        if not 0 <= asset.get("opacity", 1) <= 1:
            raise ValueError(f"Invalid opacity: {key}")
        if not (base / asset["file"]).is_file():
            raise ValueError(f"Missing asset: {asset['file']}")


def build(config_path, out):
    config_path = config_path.resolve()
    base = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    validate(config, base)
    media = {}
    files = {a["file"] for a in config["assets"].values()}
    for mask in [config["stageMask"]] + ([config["pgm"]["mask"]] if config["pgm"]["enabled"] else []):
        if mask["type"] == "image":
            files.add(mask["file"])
    audio = config.get("audio", {})
    if audio.get("file") and audio.get("embedPreview"):
        files.add(audio["file"])
    mime = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}
    for name in sorted(files):
        path = base / name
        if path.suffix.lower() not in mime:
            raise ValueError(f"Unsupported asset extension: {name}")
        media[name] = "data:" + mime[path.suffix.lower()] + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    # New directory per build avoids stale asset packs and accidental overwrites.
    out.mkdir(parents=True, exist_ok=False)
    limit = 8 * 1024 * 1024
    packs, pack, size = [], {}, 0
    for key, value in media.items():
        if size + len(value) > limit and pack:
            packs.append(pack)
            pack, size = {}, 0
        pack[key] = value
        size += len(value)
    if pack:
        packs.append(pack)
    tags = []
    for i, pack in enumerate(packs, 1):
        name = f"assets_{i:03}.js"
        (out / name).write_text("Object.assign(window.WORKSHOP_MEDIA," + json.dumps(pack) + ");", encoding="utf-8")
        tags.append(f'<script src="{name}"></script>')
    cfg = json.dumps(config, ensure_ascii=False).replace("<", "\\u003c")
    html = (ROOT / "src/index.html").read_text(encoding="utf-8")
    html = html.replace("__CONFIG__", cfg).replace("__PACKS__", "\n".join(tags))
    for token, file in [("__ENGINE__", "engine.js"), ("__SCENES__", "scenes.js"), ("__APP__", "app.js")]:
        html = html.replace(token, (ROOT / "src" / file).read_text(encoding="utf-8"))
    (out / "workshop.html").write_text(html, encoding="utf-8")
    (out / "project.snapshot.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "使用说明.txt").write_text("双击 workshop.html。请将整个资料夹一起复制。\nPNG 序列需支援资料夹选择的浏览器；若不可用，请由 Codex 启动 localhost 服务。\n此版本为通用功能示范；正式内容需依新专案设计稿制作。\n", encoding="utf-8")
    print(f"Built {out}: {len(files)} media, {len(packs)} packs, {config['stage']['width']}x{config['stage']['height']}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "project.config.json")
    parser.add_argument("--out", type=Path, required=True, help="New output folder (must not exist)")
    args = parser.parse_args()
    try:
        build(args.config, args.out.resolve())
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(1, f"Build failed: {error}\n")
