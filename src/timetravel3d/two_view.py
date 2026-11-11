from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from .data import load_image, load_scene
from .features import extract, match
from .geometry import Pose, angles, estimate_relative, project
from .output import save_reconstruction, summary, versions


def run(scene, output, config):
    start = perf_counter()
    cv2.setRNGSeed(config["seed"])
    cv2.setNumThreads(1)
    cameras, views, category = load_scene(scene)
    if category != "two_view" or len(views) != 2:
        raise ValueError("two-view expects an ETH3D rectified pair directory")
    images, K, features = [], [], []
    for v in views:
        image, intrinsic = load_image(v, cameras[v.camera_id], config["max_size"])
        images.append(image)
        K.append(intrinsic)
        features.append(extract(image, config["max_features"]))
    pairs = match(*features, config["lowe_ratio"], config["mutual_matching"])
    a, b = features[0].xy[pairs[:, 0]], features[1].xy[pairs[:, 1]]
    pose, valid_ids, points, inliers = estimate_relative(a, b, *K,
        config["ransac_px"], config["ransac_probability"])
    a, b = a[valid_ids], b[valid_ids]
    identity = Pose(np.eye(3), np.zeros(3))
    errors = (np.linalg.norm(project(points, K[0], identity)[0] - a, axis=1) +
              np.linalg.norm(project(points, K[1], pose)[0] - b, axis=1)) / 2
    angle = angles(points, identity.center, pose.center)
    support = np.full(len(points), 2)
    colors = features[0].colors[pairs[valid_ids, 0]]
    observations = [[(0, x), (1, y)] for x, y in zip(a, b)]
    report = {"scene": Path(scene).name, "category": category, "mode": "estimated_sfm",
        "scale": "arbitrary; estimated translation norm = 1", "config": config,
        "versions": versions(), "seed": config["seed"],
        "features": [len(f.xy) for f in features], "ratio_matches": len(pairs),
        "essential_inliers": inliers, "cheirality_points": len(points),
        "registered_cameras": 2, "selected_cameras": 2,
        "metrics": summary(errors, angle, support),
        "runtime_seconds": perf_counter() - start,
        "provided_extrinsics_used_for_estimation": False}
    save_reconstruction(output, points, colors, errors, angle, support, observations,
        {0: identity, 1: pose}, dict(enumerate(K)), {i: v.name for i, v in enumerate(views)}, report)
    out = Path(output)
    vis = cv2.drawMatches(images[0], [cv2.KeyPoint(*xy.astype(float), 3) for xy in a[:100]],
        images[1], [cv2.KeyPoint(*xy.astype(float), 3) for xy in b[:100]],
        [cv2.DMatch(i, i, 0) for i in range(min(100, len(a)))], None,
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    cv2.imwrite(str(out / "feature_matches.jpg"), vis)
    return report
