"""Controlled fixed-camera study: Gaussian image noise, variable geometry/support."""
import json
from pathlib import Path

import numpy as np

from timetravel3d.geometry import Pose, normalize, point_metrics, project
from timetravel3d.output import write_json
from timetravel3d.experiments import write_csv
from timetravel3d.uncertainty import variants


def main():
    rows = []
    for seed in range(100, 110):
        rng = np.random.default_rng(seed)
        count = 1000
        truth = rng.uniform([-2, -1.5, 4], [2, 1.5, 20], (count, 3))
        K = {i: np.array([[800., 0, 640], [0, 800, 360], [0, 0, 1]]) for i in range(5)}
        poses = {i: Pose(np.eye(3), np.array([-x, 0., 0.])) for i, x in enumerate([-.8, -.25, 0, .25, .8])}
        projected = {v: project(truth, K[v], poses[v])[0] for v in poses}
        points, observations = [], []
        for pid, X in enumerate(truth):
            views = sorted(rng.choice(5, size=int(rng.integers(2, 6)), replace=False))
            sigma = np.exp(rng.uniform(np.log(.3), np.log(3.)))
            obs = [(v, projected[v][pid] + rng.normal(0, sigma, 2)) for v in views]
            A = []
            for v, uv in obs:
                x, y = normalize(uv[None], K[v])[0]
                P = poses[v].matrix
                A.extend([x * P[2] - P[0], y * P[2] - P[1]])
            h = np.linalg.svd(A)[2][-1]
            points.append(h[:3] / h[3])
            observations.append(obs)
        points = np.array(points)
        errors, angles, support = point_metrics(points, observations, poses, K)
        op, ov, oxy = [], [], []
        for pid, obs in enumerate(observations):
            for v, uv in obs:
                op.append(pid); ov.append(v); oxy.append(uv)
        data = {'points': points, 'errors': errors, 'angles': angles, 'support': support,
            'view_ids': np.arange(5), 'rotations': np.array([p.R for p in poses.values()]),
            'translations': np.array([p.t for p in poses.values()]), 'intrinsics': np.array(list(K.values())),
            'obs_point': np.array(op), 'obs_view': np.array(ov), 'obs_xy': np.array(oxy)}
        _, masks = variants(data)
        actual = np.linalg.norm(points - truth, axis=1)
        for method, keep in masks.items():
            rows.append({'seed': seed, 'method': method, 'initial_points': count, 'retained_points': int(keep.sum()),
                'median_point_error_m': float(np.median(actual[keep])), 'mean_point_error_m': float(np.mean(actual[keep]))})
    dest = Path('benchmarks/synthetic')
    dest.mkdir(parents=True, exist_ok=True)
    write_json(dest / 'results.json', rows)
    write_csv(dest / 'results.csv', rows)
    write_json(dest / 'protocol.json', {'seeds': list(range(100, 110)), 'points_per_seed': 1000,
        'cameras': 5, 'noise': 'per-track log-uniform sigma 0.3-3.0 px; zero-mean Gaussian observations',
        'depth_range_m': [4, 20], 'observations': 'uniform integer 2-5 views',
        'camera_poses': 'known exactly; this validates conditional point uncertainty, not estimated-camera robustness',
        'retention': .8, 'noise_floor_px': .5, 'matching': 'known correct correspondences; no SIFT or gross mismatch outliers'})
    for method in masks:
        print(method, np.mean([r['median_point_error_m'] for r in rows if r['method'] == method]))


if __name__ == '__main__':
    main()
