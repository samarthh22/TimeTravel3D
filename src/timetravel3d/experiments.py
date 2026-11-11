"""Frozen-baseline ablations with retention and image feature-coverage controls."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .confidence import ConfidenceConfig, score_and_filter
from .output import summary, write_json, write_ply


def grid_coverage(data, mask, bins=10):
    """Occupied-cell retention over fixed baseline feature bounds, not completeness."""
    baseline_cells, retained_cells = set(), set()
    for v in data["view_ids"]:
        ids = np.flatnonzero(data["obs_view"] == v)
        if not len(ids):
            continue
        xy = data["obs_xy"][ids]
        lo, hi = xy.min(axis=0), xy.max(axis=0)
        indices = np.floor((xy - lo) / np.maximum(hi - lo, 1e-9) * bins).astype(int).clip(0, bins - 1)
        for oid, (x, y) in zip(ids, indices):
            cell = (int(v), int(x), int(y))
            baseline_cells.add(cell)
            if mask[data["obs_point"][oid]]:
                retained_cells.add(cell)
    return {"occupied_cells": len(retained_cells), "baseline_occupied_cells": len(baseline_cells),
        "grid_coverage_retention": len(retained_cells) / len(baseline_cells) if baseline_cells else 0.,
        "coverage_definition": "10x10 grid per view over frozen baseline feature bounds"}


def matched_retention_masks(scores, masks):
    """Compare single-signal rankings at the combined method's point budget."""
    count = int(masks["combined"].sum())
    output = {}
    for name in ("reprojection", "angle"):
        order = np.argsort(-scores[name], kind="stable")
        keep = np.zeros(len(order), bool)
        keep[order[:count]] = True
        output[name + "_matched_count"] = keep
    return output


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_analysis(output, data, scores, rows):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].hist(data["errors"], bins=40, color="#3069a4")
    axes[0].set(xlabel="Mean reprojection residual (px)", ylabel="Points")
    axes[1].hist(data["angles"], bins=40, color="#418668")
    axes[1].set(xlabel="Maximum triangulation angle (degrees)")
    for name in ("combined", "multiview"):
        axes[2].hist(scores[name], bins=30, alpha=.6, label=name)
    axes[2].set(xlabel="Heuristic confidence score")
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(output / "confidence_analysis.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    main = rows[:5]
    names = [r["method"] for r in main]
    axes[0].bar(names, [r["retention_percent"] for r in main], color="#3069a4")
    axes[0].set(ylabel="Retained points (%)", ylim=(0, 105))
    axes[1].bar(names, [r["grid_coverage_retention"] * 100 for r in main], color="#418668")
    axes[1].set(ylabel="Baseline occupied grid cells retained (%)", ylim=(0, 105))
    for ax in axes:
        ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(output / "retention_coverage.png", dpi=160)
    plt.close(fig)


def run(reconstruction, output, config_path=None):
    reconstruction, output = Path(reconstruction), Path(output)
    if reconstruction.is_dir():
        reconstruction = reconstruction / "reconstruction.npz"
    output.mkdir(parents=True, exist_ok=True)
    config = ConfidenceConfig.load(config_path)
    with np.load(reconstruction, allow_pickle=False) as archive:
        data = dict(archive)
    scores, masks = score_and_filter(data["errors"], data["angles"], data["support"], config)
    masks.update(matched_retention_masks(scores, masks))
    source_path = reconstruction.parent / "report.json"
    source = json.loads(source_path.read_text()) if source_path.exists() else {}
    rows = []
    for method, keep in masks.items():
        row = {"scene": source.get("scene"), "category": source.get("category"),
               "mode": source.get("mode"), "method": method,
               "initial_points": len(keep), "retained_points": int(keep.sum()),
               "retention_percent": float(keep.mean() * 100) if len(keep) else 0.,
               **summary(data["errors"][keep], data["angles"][keep], data["support"][keep]),
               **grid_coverage(data, keep)}
        rows.append(row)
        write_ply(output / f"points_{method}.ply", data["points"][keep], data["colors"][keep])
    report = {"source_scene": source.get("scene"), "source_mode": source.get("mode"),
        "source_versions": source.get("versions"), "config": config.dictionary(), "rows": rows,
        "support_is_discriminative": bool(len(np.unique(data["support"])) > 1),
        "caveat": "Heuristic scores; image grid retention is not dense 3D completeness. No accuracy improvement is assumed."}
    write_json(output / "ablation_report.json", report)
    write_csv(output / "metrics.csv", rows)
    np.savez_compressed(output / "confidence.npz", **scores, **{f"mask_{k}": v for k, v in masks.items()})
    plot_analysis(output, data, scores, rows)
    return report
