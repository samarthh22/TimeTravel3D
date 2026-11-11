"""Independent sparse diagnostic evaluation, not official ETH3D benchmark scores."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np
from plyfile import PlyData
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from .confidence import ConfidenceConfig, score_and_filter
from .data import load_scene
from .experiments import grid_coverage, matched_retention_masks, write_csv
from .geometry import Pose
from .output import summary, write_json


def read_pfm(path):
    with Path(path).open("rb") as f:
        if f.readline().strip() != b"Pf":
            raise ValueError("Expected grayscale PFM")
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        w, h = map(int, line.split())
        scale = float(f.readline())
        if not np.isfinite(scale) or scale == 0 or min(w, h) <= 0:
            raise ValueError("Invalid PFM header")
        values = np.fromfile(f, dtype="<f4" if scale < 0 else ">f4")
        if values.size != w * h:
            raise ValueError("Truncated or oversized PFM payload")
    return np.flipud(values.reshape(h, w)).astype(float) * abs(scale)


def read_stereo_calibration(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        key, value = line.split("=", 1)
        if key.startswith("cam"):
            values[key] = np.array([[float(x) for x in row.split()]
                                    for row in value.strip("[]").split(";")])
        else:
            values[key] = float(value)
    return values


def stereo_ground_truth(data, scene, gt):
    calibration = read_stereo_calibration(Path(scene) / "calib.txt")
    disparity = read_pfm(Path(gt) / "disp0GT.pfm")
    mask = cv2.imread(str(Path(gt) / "mask0nocc.png"), cv2.IMREAD_GRAYSCALE)
    if mask is None or mask.shape != disparity.shape:
        raise ValueError("Missing or mismatched stereo non-occlusion mask")
    if disparity.shape != (int(calibration["height"]), int(calibration["width"])):
        raise ValueError("Disparity/calibration size mismatch")
    names = data["names"].tolist()
    if names != ["im0.png", "im1.png"]:
        raise ValueError("Stereo evaluation requires im0.png then im1.png")
    K = data["intrinsics"][0]
    original = calibration["cam0"].copy()
    original[0, 2] -= .5
    original[1, 2] -= .5
    ids = np.flatnonzero(data["obs_view"] == data["view_ids"][0])
    uv = data["obs_xy"][ids]
    # Invert the calibrated pinhole mapping, including the resize center offset.
    native = np.column_stack(((uv[:, 0] - K[0, 2]) / K[0, 0] * original[0, 0] + original[0, 2],
                             (uv[:, 1] - K[1, 2]) / K[1, 1] * original[1, 1] + original[1, 2]))
    pixels = np.rint(native).astype(int)
    inside = (pixels[:, 0] >= 0) & (pixels[:, 0] < mask.shape[1]) & (pixels[:, 1] >= 0) & (pixels[:, 1] < mask.shape[0])
    point_error = np.full(len(data["points"]), np.nan)
    depth_error = np.full_like(point_error, np.nan)
    disparity_error = np.full_like(point_error, np.nan)
    pids, native, pixels = data["obs_point"][ids][inside], native[inside], pixels[inside]
    d = disparity[pixels[:, 1], pixels[:, 0]]
    valid = np.isfinite(d) & (d + calibration["doffs"] > 0) & (mask[pixels[:, 1], pixels[:, 0]] == 255)
    pids, native, d = pids[valid], native[valid], d[valid]
    baseline_m = calibration["baseline"] / 1000.
    estimated_baseline = np.linalg.norm(data["translations"][1])
    if estimated_baseline <= 0:
        raise ValueError("Invalid estimated baseline")
    scale = baseline_m / estimated_baseline
    predicted = data["points"][pids] * scale
    depth_gt = original[0, 0] * baseline_m / (d + calibration["doffs"])
    rays = np.column_stack(((native[:, 0] - original[0, 2]) / original[0, 0],
                            (native[:, 1] - original[1, 2]) / original[1, 1], np.ones(len(native))))
    truth = rays * depth_gt[:, None]
    point_error[pids] = np.linalg.norm(predicted - truth, axis=1)
    depth_error[pids] = np.abs(predicted[:, 2] - depth_gt)
    with np.errstate(divide="ignore", invalid="ignore"):
        predicted_disparity = original[0, 0] * baseline_m / predicted[:, 2] - calibration["doffs"]
    disparity_error[pids] = np.abs(predicted_disparity - d)
    return {"point_error_m": point_error, "depth_error_m": depth_error,
            "disparity_error_px": disparity_error}, {
        "protocol": "Sparse nearest-pixel non-occluded PFM diagnostics; not official dense benchmark score",
        "alignment": "Estimated first-camera frame; calibrated stereo baseline fixes metric scale for evaluation only",
        "scale_to_meters": float(scale), "valid_baseline_gt_points": int(np.isfinite(point_error).sum()),
        "sampling": "nearest native image pixel; only mask value 255; no interpolation across invalid pixels"}


def align_camera_poses(estimated, reference):
    """Rotation-informed similarity using camera correspondences, never scan ICP.

    Orientations constrain rotation even for nearly collinear video trajectories.
    Translation and positive scale are fitted to corresponding camera centers.
    """
    ids = sorted(estimated)
    if len(ids) < 2:
        raise ValueError("Need at least two corresponding cameras for metric alignment")
    rotations = np.array([reference[v].R.T @ estimated[v].R for v in ids])
    R = Rotation.from_matrix(rotations).mean().as_matrix()
    a = np.array([estimated[v].center for v in ids]) @ R.T
    b = np.array([reference[v].center for v in ids])
    ca, cb = a.mean(axis=0), b.mean(axis=0)
    denom = np.sum((a - ca) ** 2)
    if denom < 1e-12:
        raise ValueError("Degenerate zero-baseline camera trajectory")
    scale = np.sum((a - ca) * (b - cb)) / denom
    if scale <= 0:
        raise ValueError("Nonpositive camera-alignment scale")
    t = cb - scale * ca
    aligned = scale * a + t
    angular = [(Rotation.from_matrix(estimated[v].R @ R.T @ reference[v].R.T).magnitude()) for v in ids]
    return float(scale), R, t, {"camera_center_rmse_m": float(np.sqrt(np.mean(np.sum((aligned - b) ** 2, axis=1)))),
        "camera_rotation_median_deg": float(np.degrees(np.median(angular)))}


def load_scan_samples(directory, max_points=200000):
    directory = Path(directory)
    project = directory / "scan_alignment.mlp"
    scans = []
    if project.is_file():
        root = ET.parse(project).getroot()
        for mesh in root.iter("MLMesh"):
            matrix = np.fromstring(mesh.findtext("MLMatrix44"), sep=" ").reshape(4, 4)
            scans.append((directory / mesh.attrib["filename"], matrix))
    else:
        files = sorted(directory.glob("*.ply"))
        if len(files) != 1:
            raise ValueError("Multiple scans require scan_alignment.mlp")
        scans = [(files[0], np.eye(4))]
    if not scans or max_points < len(scans):
        raise ValueError("Invalid scan sampling budget")
    sampled, records = [], []
    for path, transform in scans:
        vertices = PlyData.read(path, mmap="r")["vertex"].data
        count = min(len(vertices), max_points // len(scans))
        indices = np.linspace(0, len(vertices) - 1, count, dtype=int)
        xyz = np.column_stack([vertices[k][indices] for k in ("x", "y", "z")]).astype(float)
        xyz = xyz @ transform[:3, :3].T + transform[:3, 3]
        sampled.append(xyz[np.isfinite(xyz).all(axis=1)])
        records.append({"file": path.name, "vertices": len(vertices), "sampled": count,
                        "scan_to_world": transform.tolist()})
    points = np.concatenate(sampled)
    if not len(points):
        raise ValueError("No finite scan points")
    return points, records


def run(reconstruction, scene, gt, output, config_path=None, distance_threshold=.05, max_scan_points=200000):
    reconstruction, output = Path(reconstruction), Path(output)
    if reconstruction.is_dir():
        reconstruction /= "reconstruction.npz"
    if distance_threshold <= 0 or not np.isfinite(distance_threshold):
        raise ValueError("Distance threshold must be finite and positive")
    output.mkdir(parents=True, exist_ok=True)
    with np.load(reconstruction, allow_pickle=False) as archive:
        data = dict(archive)
    source = json.loads((reconstruction.parent / "report.json").read_text())
    config = ConfidenceConfig.load(config_path)
    scores, masks = score_and_filter(data["errors"], data["angles"], data["support"], config)
    masks.update(matched_retention_masks(scores, masks, data["angles"]))
    _, views, category = load_scene(scene)
    scan = None
    if category == "two_view":
        error_arrays, protocol = stereo_ground_truth(data, scene, gt)
        aligned = None
    else:
        lookup = {v.name: Pose(v.R, v.t) for v in views}
        estimated = {int(v): Pose(R, t) for v, R, t in zip(data["view_ids"], data["rotations"], data["translations"])}
        reference = {int(v): lookup[str(name)] for v, name in zip(data["view_ids"], data["names"])}
        if source["mode"] == "known_pose_triangulation":
            scale, rotation, translation, pose_metrics = 1., np.eye(3), np.zeros(3), {}
        else:
            scale, rotation, translation, pose_metrics = align_camera_poses(estimated, reference)
        aligned = scale * data["points"] @ rotation.T + translation
        scan, scans = load_scan_samples(gt, max_scan_points)
        distances = cKDTree(scan).query(aligned, workers=1)[0]
        error_arrays = {"point_error_m": distances}
        protocol = {"protocol": "Camera-aligned sparse-to-sampled-scan nearest-neighbor diagnostics; not official ETH3D scores",
            "alignment": "Rotation-informed camera-pose similarity; same transform for every filter; no scan ICP",
            "scale_to_meters": scale, "rotation": rotation.tolist(), "translation": translation.tolist(),
            "scan_sampling": "uniform vertex indices per scan; fixed deterministic budget",
            "sampled_scan_points": len(scan), "scans": scans,
            "visibility_masks_used": False, **pose_metrics}
    rows = []
    for method, keep in masks.items():
        row = {"scene": source["scene"], "category": category, "mode": source["mode"], "method": method,
            "initial_points": len(keep), "retained_points": int(keep.sum()),
            "retention_percent": float(keep.mean() * 100) if len(keep) else 0.,
            "registered_cameras": source["registered_cameras"], "selected_cameras": source["selected_cameras"],
            "reconstruction_seconds": source["runtime_seconds"],
            **summary(data["errors"][keep], data["angles"][keep], data["support"][keep]), **grid_coverage(data, keep)}
        for name, values in error_arrays.items():
            valid = values[keep & np.isfinite(values)]
            row[f"evaluated_{name}_count"] = len(valid)
            row[f"median_{name}"] = float(np.median(valid)) if len(valid) else None
            row[f"mean_{name}"] = float(np.mean(valid)) if len(valid) else None
        distances = error_arrays["point_error_m"][keep]
        distances = distances[np.isfinite(distances)]
        row["accuracy_within_threshold_fraction"] = float(np.mean(distances <= distance_threshold)) if len(distances) else None
        if scan is not None:
            row["sampled_scene_coverage_fraction"] = float(np.mean(cKDTree(aligned[keep]).query(scan, workers=1)[0] <= distance_threshold)) if keep.any() else 0.
        rows.append(row)
    report = {"scene": source["scene"], "category": category, "mode": source["mode"],
        "confidence_config": config.dictionary(), "distance_threshold_m": distance_threshold,
        "source_config": source["config"], "source_versions": source["versions"], "protocol": protocol, "rows": rows}
    write_json(output / "evaluation_report.json", report)
    write_csv(output / "evaluation.csv", rows)
    return report
