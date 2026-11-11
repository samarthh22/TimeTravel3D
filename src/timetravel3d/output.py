"""Portable exports and machine-readable provenance."""
import importlib.metadata
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def versions():
    return {"python": platform.python_version(), **{
        pkg: importlib.metadata.version(pkg) for pkg in
        ("numpy", "opencv-python", "scipy", "matplotlib", "PyYAML")}}


def summary(errors, angle, support):
    if not len(errors):
        return {"points": 0, "mean_reprojection_px": None, "median_reprojection_px": None,
                "median_angle_deg": None, "mean_observation_support": None}
    return {"points": len(errors), "mean_reprojection_px": float(np.mean(errors)),
            "median_reprojection_px": float(np.median(errors)),
            "median_angle_deg": float(np.median(angle)),
            "mean_observation_support": float(np.mean(support))}


def write_ply(path, points, colors):
    with Path(path).open("w", encoding="ascii") as f:
        f.write(f"ply\nformat ascii 1.0\nelement vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
        for xyz, rgb in zip(points, colors):
            f.write(" ".join(f"{float(v):.8g}" for v in xyz) + " " +
                    " ".join(str(int(v)) for v in rgb) + "\n")


def plot_cloud(path, points, colors):
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection="3d")
    if len(points):
        keep = np.linspace(0, len(points) - 1, min(len(points), 10000), dtype=int)
        ax.scatter(*points[keep].T, c=colors[keep] / 255., s=2)
    ax.set(xlabel="X (arbitrary scale)", ylabel="Y", zlabel="Z", title="Sparse reconstruction")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_reconstruction(output, points, colors, errors, angle, support, observations, poses, intrinsics, names, report):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    point_ids, view_ids, xy = [], [], []
    for pid, obs in enumerate(observations):
        for vid, uv in obs:
            point_ids.append(pid)
            view_ids.append(vid)
            xy.append(uv)
    np.savez_compressed(output / "reconstruction.npz", points=points, colors=colors,
                        errors=errors, angles=angle, support=support,
                        obs_point=np.array(point_ids, int), obs_view=np.array(view_ids, int),
                        obs_xy=np.array(xy).reshape(-1, 2),
                        view_ids=np.array(sorted(poses)),
                        rotations=np.array([poses[i].R for i in sorted(poses)]),
                        translations=np.array([poses[i].t for i in sorted(poses)]),
                        intrinsics=np.array([intrinsics[i] for i in sorted(poses)]),
                        names=np.array([names[i] for i in sorted(poses)]))
    write_ply(output / "points_baseline.ply", points, colors)
    write_json(output / "cameras.json", [{"view_id": i, "name": names[i],
        "R": poses[i].R.tolist(), "t": poses[i].t.tolist(), "center": poses[i].center.tolist(),
        "K": intrinsics[i].tolist()} for i in sorted(poses)])
    plot_cloud(output / "reconstruction.png", points, colors)
    write_json(output / "report.json", report)
