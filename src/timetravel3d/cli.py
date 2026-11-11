import argparse
import json
from pathlib import Path

import yaml

DEFAULTS = {"seed": 22, "max_size": 1600, "max_features": 6000,
            "lowe_ratio": 0.75, "mutual_matching": True,
            "ransac_px": 1., "ransac_probability": 0.999,
            "seed_min_angle_deg": .3, "min_initial_points": 20,
            "point_min_angle_deg": .05, "track_max_error_px": 4.,
            "pnp_error_px": 3., "min_pnp_inliers": 8,
            "bundle_adjustment": True, "ba_max_nfev": 80, 'minimal_gauge_ba': True,
            'rectified_stereo': False}


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
    multi = sub.add_parser("multi-view", help="Incremental SfM or explicit known-pose experiment")
    multi.add_argument("scene", type=Path)
    multi.add_argument("--output", type=Path, required=True)
    multi.add_argument("--config", type=Path)
    multi.add_argument("--views", type=int, default=8)
    multi.add_argument("--stride", type=int, default=1)
    multi.add_argument("--start", type=int, default=0)
    multi.add_argument("--camera-id", type=int)
    multi.add_argument("--known-poses", action="store_true")
    multi.add_argument("--no-ba", action="store_true")
    ablate = sub.add_parser("ablate", help="Confidence contribution: frozen-baseline ablations")
    ablate.add_argument("reconstruction", type=Path)
    ablate.add_argument("--output", type=Path, required=True)
    ablate.add_argument("--config", type=Path, help="Confidence YAML, not the SfM configuration")
    evaluate = sub.add_parser("evaluate", help="Independent sparse ground-truth diagnostics")
    evaluate.add_argument("reconstruction", type=Path)
    evaluate.add_argument("--scene", type=Path, required=True)
    evaluate.add_argument("--ground-truth", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--config", type=Path, help="Confidence configuration")
    evaluate.add_argument("--distance-threshold", type=float, default=.05)
    evaluate.add_argument("--max-scan-points", type=int, default=200000)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            from .data import inspect_scene
            result = inspect_scene(args.scene)
        elif args.command == "two-view":
            from .two_view import run
            result = run(args.scene, args.output, read_config(args.config))
        elif args.command == "multi-view":
            from .multiview import run
            config = read_config(args.config)
            if args.no_ba:
                config["bundle_adjustment"] = False
            result = run(args.scene, args.output, config, args.views, args.stride,
                         args.start, args.camera_id, args.known_poses)
        elif args.command == "ablate":
            from .experiments import run
            result = run(args.reconstruction, args.output, args.config)
        else:
            from .evaluation import run
            result = run(args.reconstruction, args.scene, args.ground_truth, args.output,
                         args.config, args.distance_threshold, args.max_scan_points)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
