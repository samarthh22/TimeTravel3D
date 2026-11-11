import argparse
import json
from pathlib import Path

import yaml

DEFAULTS = {"seed": 22, "max_size": 1600, "max_features": 6000,
            "lowe_ratio": 0.75, "mutual_matching": True,
            "ransac_px": 1., "ransac_probability": 0.999}


def read_config(path):
    config = DEFAULTS.copy()
    if path:
        custom = yaml.safe_load(Path(path).read_text()) or {}
        unknown = set(custom) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
        config.update(custom)
    return config


def main():
    parser = argparse.ArgumentParser(description="TimeTravel3D calibrated sparse SfM")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Inspect actual ETH3D calibration and image paths")
    inspect.add_argument("scene", type=Path)
    pair = sub.add_parser("two-view", help="Estimate two-view pose and triangulate baseline")
    pair.add_argument("scene", type=Path)
    pair.add_argument("--output", type=Path, required=True)
    pair.add_argument("--config", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            from .data import inspect_scene
            result = inspect_scene(args.scene)
        else:
            from .two_view import run
            result = run(args.scene, args.output, read_config(args.config))
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
