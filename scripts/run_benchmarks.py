"""Reproduce local ETH3D experiments with a fresh virtualenv process per scene."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

from timetravel3d.experiments import write_csv
from timetravel3d.output import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path(".."))
    parser.add_argument("--output", type=Path, default=Path("results/benchmark"))
    parser.add_argument("--publish-dir", type=Path, default=Path("benchmarks/measured"))
    parser.add_argument("--only", choices=["two-view", "multi-view", "all"], default="all")
    parser.add_argument("--max-scan-points", type=int, default=200000)
    parser.add_argument("--reuse-baselines", action="store_true", help="Reuse existing frozen geometry; recompute all ablations/evaluation")
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error("Run this script using the project's virtual environment")
    root, output = args.data_root, args.output
    repo = Path(__file__).resolve().parents[1]
    confidence_config = repo / "configs/confidence.yaml"
    jobs = []
    if args.only in ("two-view", "all"):
        for scene in sorted((root / "two_view_training").iterdir()):
            if scene.is_dir():
                jobs.append(("two_view_" + scene.name, "two-view", scene, root / "two_view_training_gt" / scene.name, []))
    if args.only in ("multi-view", "all"):
        for category, scenes, params in [
            ("rig", ["delivery_area", "electro"], ["--views", "5", "--stride", "12"]),
            ("dslr", ["courtyard", "meadow"], ["--views", "6"])]:
            for scene in scenes:
                jobs.append((category + "_" + scene, "multi-view", root / f"multi_view_training_{category}_undistorted" / scene,
                    root / f"multi_view_training_{category}_scan_eval" / scene / f"{category}_scan_eval", params))
    records, all_rows = [], []
    for name, mode, scene, gt, params in jobs:
        destination = output / name
        destination.mkdir(parents=True, exist_ok=True)
        record = {"experiment": name, "status": "failed", "commands": []}
        steps = [
            [mode, str(scene), "--output", str(destination / "baseline"), *params],
            ["ablate", str(destination / "baseline"), "--config", str(confidence_config), "--output", str(destination / "ablation")],
            ["evaluate", str(destination / "baseline"), "--scene", str(scene), "--ground-truth", str(gt),
             "--config", str(confidence_config), "--max-scan-points", str(args.max_scan_points), "--output", str(destination / "evaluation")]]
        if args.reuse_baselines:
            baseline_path = destination / "baseline/report.json"
            if not baseline_path.is_file() or not (destination / "baseline/reconstruction.npz").is_file():
                raise FileNotFoundError(f"No existing baseline for {name}; omit --reuse-baselines")
            from timetravel3d.cli import DEFAULTS
            if json.loads(baseline_path.read_text())["config"] != DEFAULTS:
                raise ValueError(f"Baseline config differs from current defaults: {name}")
            steps = steps[1:]
            record["baseline_reused"] = True
        for index, step in enumerate(steps):
            command = [sys.executable, "-m", "timetravel3d", *step]
            # Published commands contain portable paths rather than this machine's absolute paths.
            record["commands"].append(["python", "-m", "timetravel3d", *[str(x).replace(str(repo), ".") for x in step]])
            result = subprocess.run(command, text=True, capture_output=True, encoding="utf-8")
            (destination / f"step_{index}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            if result.returncode:
                record["error"] = result.stderr[-1500:]
                print(f"FAILED {name}: step {index}", flush=True)
                break
        else:
            report = json.loads((destination / "evaluation/evaluation_report.json").read_text())
            baseline = json.loads((destination / "baseline/report.json").read_text())
            for row in report["rows"]:
                row["experiment"] = name
                row["peak_process_memory_mb"] = baseline.get("peak_process_memory_mb")
            all_rows.extend(report["rows"])
            record.update(status="success", protocol=report["protocol"],
                          versions=report["source_versions"], config=report["source_config"],
                          selected_images=baseline.get("selected_images", ["im0.png", "im1.png"]))
            print(f"OK {name}: {baseline['metrics']['points']} points; {baseline['registered_cameras']}/{baseline['selected_cameras']} cameras", flush=True)
        records.append(record)
        write_json(output / "manifest.json", {"experiments": records})
    args.publish_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"platform": platform.platform(), "processor": platform.processor(),
        "confidence_config": confidence_config.read_text(),
        "confidence_config_sha256": hashlib.sha256(confidence_config.read_bytes()).hexdigest(),
        "max_scan_points": args.max_scan_points, "experiments": records}
    write_json(args.publish_dir / "manifest.json", manifest)
    write_csv(args.publish_dir / "results.csv", all_rows)
    write_json(args.publish_dir / "results.json", all_rows)
    success = sum(r["status"] == "success" for r in records)
    print(f"Completed {success}/{len(records)} experiments; tables: {args.publish_dir}", flush=True)
    return 0 if success == len(records) and records else 1


if __name__ == "__main__":
    raise SystemExit(main())
