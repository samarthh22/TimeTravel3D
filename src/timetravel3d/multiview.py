"""Incremental SfM with fresh SIFT tracks, PnP-RANSAC and constrained BA."""
from itertools import combinations
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from .bundle import bundle_adjust
from .data import load_image, load_scene
from .features import extract, match
from .geometry import Pose, angles, estimate_relative, normalize, point_metrics, project, triangulate
from .output import save_reconstruction, summary, versions
from .tracks import build_tracks


def triangulate_track(obs, poses, K, max_error=4., min_angle=.05):
    """Best two-view hypothesis, consensus, then normalized multi-view DLT."""
    if len(obs) < 2:
        return None
    best = None
    for (i, a), (j, b) in combinations(obs, 2):
        X, valid = triangulate(np.array([a]), np.array([b]), K[i], K[j], poses[i], poses[j])
        if not valid[0]:
            continue
        angle = float(angles(X, poses[i].center, poses[j].center)[0])
        if angle < min_angle:
            continue
        good, residuals = [], []
        for v, uv in obs:
            pixel, z = project(X, K[v], poses[v])
            error = np.linalg.norm(pixel[0] - uv)
            if z[0] > 1e-9 and error <= max_error:
                good.append((v, uv))
                residuals.append(error)
        score = (len(good), -float(np.mean(residuals)) if residuals else -np.inf)
        if len(good) >= 2 and (best is None or score > best[0]):
            best = score, good
    if best is None:
        return None
    good = best[1]
    A = []
    for v, uv in good:
        x, y = normalize(np.array([uv]), K[v])[0]
        P = poses[v].matrix
        A.extend([x * P[2] - P[0], y * P[2] - P[1]])
    _, _, vt = np.linalg.svd(np.array(A))
    h = vt[-1]
    if abs(h[3]) < 1e-12:
        return None
    X = h[:3] / h[3]
    for v, uv in good:
        pred, depth = project(X[None], K[v], poses[v])
        if not np.isfinite(pred).all() or depth[0] <= 1e-9 or np.linalg.norm(pred[0] - uv) > max_error:
            return None
    return X, good


def register_camera(xyz, xy, K, threshold=3., min_inliers=8):
    if len(xyz) < max(6, min_inliers):
        return None
    xyz, xy = np.asarray(xyz, np.float64), np.asarray(xy, np.float64)
    ok, rvec, tvec, inliers = cv2.solvePnPRansac(xyz, xy, K, None,
        iterationsCount=500, reprojectionError=threshold, confidence=.999, flags=cv2.SOLVEPNP_EPNP)
    if not ok or inliers is None or len(inliers) < min_inliers:
        return None
    idx = inliers.ravel()
    rvec, tvec = cv2.solvePnPRefineLM(xyz[idx], xy[idx], K, None, rvec, tvec)
    pose = Pose(cv2.Rodrigues(rvec)[0], tvec.ravel())
    pred, depth = project(xyz, K, pose)
    valid = (depth > 0) & (np.linalg.norm(pred - xy, axis=1) <= threshold)
    return (pose, int(valid.sum())) if valid.sum() >= min_inliers else None


def reconstruct(features, K, config, known_poses=None):
    edges, seeds = [], []
    for i, j in combinations(range(len(features)), 2):
        pairs = match(features[i], features[j], config["lowe_ratio"], config["mutual_matching"])
        try:
            pose, good, X, _ = estimate_relative(features[i].xy[pairs[:, 0]],
                features[j].xy[pairs[:, 1]], K[i], K[j], config["ransac_px"], config["ransac_probability"])
        except (ValueError, cv2.error):
            continue
        edges.append((i, j, pairs[good]))
        angle = float(np.median(angles(X, np.zeros(3), pose.center)))
        if len(good) >= config["min_initial_points"] and angle >= config["seed_min_angle_deg"]:
            seeds.append((len(good) * min(angle / 5., 1.), i, j, pose, angle))
    tracks, conflicts = build_tracks(edges)
    if known_poses is None:
        if not seeds:
            raise ValueError("No initial pair has enough inliers and parallax; increase temporal stride or subset size")
        _, first, second, relative, seed_angle = max(seeds, key=lambda s: s[0])
        poses = {first: Pose(np.eye(3), np.zeros(3)), second: relative}
        fixed = {first, second}
    else:
        poses, fixed = dict(known_poses), set(known_poses)
        first, second, seed_angle = None, None, None

    def triangulate_all():
        cloud, observations = {}, {}
        for tid, track in enumerate(tracks):
            obs = [(v, features[v].xy[k]) for v, k in track.items() if v in poses]
            result = triangulate_track(obs, poses, K, config["track_max_error_px"], config["point_min_angle_deg"])
            if result is not None:
                cloud[tid], observations[tid] = result
        return cloud, observations

    cloud, observations = triangulate_all()
    registration = []
    while len(poses) < len(features):
        candidates = []
        for v in range(len(features)):
            if v not in poses:
                tids = [tid for tid in cloud if v in tracks[tid]]
                candidates.append((len(tids), v, tids))
        registered = False
        for count, v, tids in sorted(candidates, reverse=True):
            result = register_camera([cloud[t] for t in tids],
                [features[v].xy[tracks[t][v]] for t in tids], K[v], config["pnp_error_px"], config["min_pnp_inliers"])
            if result is None:
                continue
            poses[v], inliers = result
            registration.append({"view": v, "correspondences": count, "inliers": inliers})
            cloud, observations = triangulate_all()
            registered = True
            break
        if not registered:
            break
    if not cloud:
        raise ValueError("No geometrically valid multi-view points")
    tids = list(cloud)
    points = np.array([cloud[t] for t in tids])
    obs = [observations[t] for t in tids]
    ba = {"enabled": False}
    if config["bundle_adjustment"] and known_poses is None:
        points, poses, ba = bundle_adjust(points, obs, poses, K, fixed, config["ba_max_nfev"])
    valid = np.ones(len(points), bool)
    for pid, observation in enumerate(obs):
        for v, xy in observation:
            uv, z = project(points[pid:pid + 1], K[v], poses[v])
            valid[pid] &= bool(z[0] > 0 and np.isfinite(uv).all() and
                               np.linalg.norm(uv[0] - xy) <= config["track_max_error_px"])
    colors = np.array([features[obs[idx][0][0]].colors[tracks[t][obs[idx][0][0]]]
                       for idx, t in enumerate(tids) if valid[idx]], dtype=np.uint8).reshape(-1, 3)
    points, obs = points[valid], [o for o, keep in zip(obs, valid) if keep]
    if not len(points):
        raise ValueError("No points survived final geometric verification")
    errors, angle, support = point_metrics(points, obs, poses, K)
    details = {"tracks": len(tracks), "track_conflicts_rejected": conflicts,
        "verified_image_pairs": len(edges), "seed_pair": [first, second],
        "seed_median_angle_deg": seed_angle, "registration": registration,
        "bundle_adjustment": ba, "unregistered_views": sorted(set(range(len(features))) - set(poses))}
    return points, colors, errors, angle, support, obs, poses, details


def run(scene, output, config, count=8, stride=1, start=0, camera_id=None, known_poses=False):
    begin = perf_counter()
    if count < 3 or stride < 1 or start < 0:
        raise ValueError("Need at least 3 views, positive stride and nonnegative start")
    cv2.setRNGSeed(config["seed"])
    cv2.setNumThreads(1)
    cameras, views, category = load_scene(scene)
    if category == "rig" and camera_id is None:
        camera_id = min(cameras)
    if camera_id is not None:
        views = [v for v in views if v.camera_id == camera_id]
    selected = views[start::stride][:count]
    if len(selected) < 3:
        raise ValueError("Selected subset contains fewer than 3 images")
    features, K = [], {}
    for i, v in enumerate(selected):
        image, K[i] = load_image(v, cameras[v.camera_id], config["max_size"])
        features.append(extract(image, config["max_features"]))
    known = {i: Pose(v.R, v.t) for i, v in enumerate(selected)} if known_poses else None
    points, colors, errors, angle, support, obs, poses, details = reconstruct(features, K, config, known)
    report = {"scene": Path(scene).name, "category": category,
        "mode": "known_pose_triangulation" if known_poses else "estimated_sfm",
        "provided_extrinsics_used_for_estimation": known_poses,
        "provided_feature_tracks_used": False,
        "scale": "dataset world units (meters)" if known_poses else "arbitrary seed baseline = 1",
        "config": config, "versions": versions(), "selected_cameras": len(selected),
        "selected_images": [v.name for v in selected], "camera_id_filter": camera_id,
        "subset": {"requested_views": count, "stride": stride, "start": start},
        "features": [len(f.xy) for f in features], "registered_cameras": len(poses),
        "registration_rate": len(poses) / len(selected), "metrics": summary(errors, angle, support),
        "runtime_seconds": perf_counter() - begin, **details}
    save_reconstruction(output, points, colors, errors, angle, support, obs, poses, K,
        {i: v.name for i, v in enumerate(selected)}, report)
    return report
