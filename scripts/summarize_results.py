"""Generate a measured report and comparison figure from published metric tables."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def number(value, digits=4):
    return "undefined" if value is None else f"{value:.{digits}f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("benchmarks/measured/results.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/RESULTS.md"))
    args = parser.parse_args()
    rows = json.loads(args.input.read_text())
    groups = {}
    for row in rows:
        groups.setdefault(row["experiment"], {})[row["method"]] = row
    stereo = {k: v for k, v in groups.items() if k.startswith("two_view_")}
    multi = {k: v for k, v in groups.items() if not k.startswith("two_view_")}
    valid = [v for v in stereo.values() if v["combined"]["median_point_error_m"] is not None and v["baseline"]["median_point_error_m"] is not None]
    lower = sum(v["combined"]["median_point_error_m"] < v["baseline"]["median_point_error_m"] for v in valid)
    empty = [k.removeprefix("two_view_") for k, v in stereo.items() if not v["combined"]["retained_points"]]
    text = ["# Measured results", "",
        "Generated from `benchmarks/measured/results.json`; all values below are measured.",
        "See `manifest.json` for exact selected images, commands, versions and configurations.", "",
        f"The run completed {len(groups)} experiments: {len(stereo)} two-view scenes and {len(multi)} multi-view subsets.",
        "Completed means the pipeline and evaluation ran; it does not imply all selected cameras registered.", "",
        "## Two-view estimated SfM", "",
        f"Baseline triangulation produced {sum(v['baseline']['retained_points'] for v in stereo.values()):,} points across the {len(stereo)} scenes.",
        f"The combined filter had lower median sparse 3D error in {lower}/{len(valid)} scenes with defined ground-truth errors for both methods.",
        f"It returned zero points in {len(empty)} scenes: {', '.join(empty)}.",
        "Other undefined errors indicate that retained features had no eligible non-occluded ground-truth samples.",
        "The multi-view support filter returns zero points for every two-view scene because its minimum support is three.", "",
        "| Scene | Baseline points | Combined points | Baseline median error (m) | Combined median error (m) | Grid retention (%) |",
        "|---|---:|---:|---:|---:|---:|"]
    for name, group in stereo.items():
        b, c = group["baseline"], group["combined"]
        text.append(f"| {name.removeprefix('two_view_')} | {b['retained_points']} | {c['retained_points']} | {number(b['median_point_error_m'])} | {number(c['median_point_error_m'])} | {c['grid_coverage_retention'] * 100:.1f} |")
    text += ["", "Errors use nearest-pixel PFM disparity and calibrated baseline scale in the first-camera frame.",
        "Very weak parallax can lead to incorrect estimated pose/depth despite small pixel residuals.", "",
        "## Multi-view estimated SfM", "",
        "Sources are low-resolution rig sequences and high-resolution DSLR datasets resized to 1600 px maximum.",
        "Distances are nearest neighbors to fixed 200,000-point scene scan samples after camera-pose similarity alignment.",
        "They are approximate diagnostics, not official ETH3D accuracy/completeness scores.", "",
        "| Subset | Method | Cameras | Points | Retention (%) | Grid retention (%) | Median scan distance (m) | Median reprojection (px) |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for name, group in multi.items():
        for method in ("baseline", "combined", "multiview"):
            r = group[method]
            text.append(f"| {name} | {method} | {r['registered_cameras']}/{r['selected_cameras']} | {r['retained_points']} | {r['retention_percent']:.1f} | {r['grid_coverage_retention'] * 100:.1f} | {number(r['median_point_error_m'])} | {number(r['median_reprojection_px'])} |")
    text += ["", "| Subset | Reconstruction seconds | Peak process memory (MiB) |",
             "|---|---:|---:|"]
    for name, group in multi.items():
        b = group["baseline"]
        text.append(f"| {name} | {b['reconstruction_seconds']:.2f} | {number(b.get('peak_process_memory_mb'), 1)} |")
    text += ["", "Reconstruction time and memory refer to one frozen baseline; all filters share that cost.",
        "The complete CSV includes reprojection-only, angle-only, and both point-count-matched controls.", "",
        "## Interpretation", "",
        "Confidence filtering does not consistently improve the independent ground-truth diagnostics.",
        "Observation-support filtering can lower scan distance on some DSLR subsets while discarding much of the cloud and image coverage.",
        "The experiment does not establish a general accuracy advantage for the proposed heuristic.",
        "Pose estimation errors cannot be repaired by discarding individual points from a frozen reconstruction.",
        "These are prespecified exploratory training-data runs, with no held-out or multi-seed significance claim.", "",
        "![Multi-view quality and retention comparison](../benchmarks/measured/comparison.png)", ""]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(text), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    x = np.arange(len(multi))
    colors = {"baseline": "#4b6584", "combined": "#2563a6", "multiview": "#2b9375"}
    for index, method in enumerate(("baseline", "combined", "multiview")):
        offset = (index - 1) * .25
        axes[0].plot(x + offset, [g[method]["median_point_error_m"] for g in multi.values()], "o", label=method, color=colors[method])
        axes[1].bar(x + offset, [g[method]["retention_percent"] for g in multi.values()], .24, label=method, color=colors[method])
    labels = [name.replace("_", "\n", 1) for name in multi]
    for ax in axes:
        ax.set_xticks(x, labels)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    axes[0].set(ylabel="Median sampled-scan distance (m; log scale)", yscale="log", title="Independent geometry diagnostic")
    axes[1].set(ylabel="Baseline points retained (%)", ylim=(0, 110), title="Point retention tradeoff")
    axes[0].legend(frameon=False, loc="upper right")
    fig.suptitle("Fixed ETH3D subsets: confidence does not consistently improve 3D error", fontsize=12)
    fig.tight_layout()
    fig.savefig(args.input.parent / "comparison.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {args.report} and {args.input.parent / 'comparison.png'}")


if __name__ == "__main__":
    main()
