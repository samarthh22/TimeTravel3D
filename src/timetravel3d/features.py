"""SIFT + Lowe ratio test with optional mutual nearest-neighbor matching."""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Features:
    xy: np.ndarray
    descriptors: np.ndarray
    colors: np.ndarray


def extract(image, max_features=6000):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    keypoints, desc = cv2.SIFT_create(nfeatures=max_features).detectAndCompute(gray, None)
    if desc is None:
        return Features(np.empty((0, 2)), np.empty((0, 128), np.float32), np.empty((0, 3), np.uint8))
    xy = np.array([k.pt for k in keypoints], dtype=np.float64)
    pixels = np.rint(xy).astype(int)
    pixels[:, 0] = pixels[:, 0].clip(0, image.shape[1] - 1)
    pixels[:, 1] = pixels[:, 1].clip(0, image.shape[0] - 1)
    colors = image[pixels[:, 1], pixels[:, 0], ::-1].copy()
    return Features(xy, desc, colors)


def match(a, b, ratio=0.75, mutual=True):
    if not 0 < ratio < 1:
        raise ValueError("Lowe ratio must be between 0 and 1")
    if len(a.descriptors) < 2 or len(b.descriptors) < 2:
        return np.empty((0, 2), dtype=int)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    pairs = [(m.queryIdx, m.trainIdx) for row in bf.knnMatch(a.descriptors, b.descriptors, k=2)
             if len(row) == 2 for m, n in [row] if m.distance < ratio * n.distance]
    if mutual:
        reverse = {(m.trainIdx, m.queryIdx) for row in bf.knnMatch(b.descriptors, a.descriptors, k=2)
                   if len(row) == 2 for m, n in [row] if m.distance < ratio * n.distance}
        pairs = [pair for pair in pairs if pair in reverse]
    # Always one-to-one, even when the mutual check is disabled.
    unique, used = [], set()
    for i, j in pairs:
        if j not in used:
            unique.append((i, j))
            used.add(j)
    return np.asarray(unique, dtype=int).reshape(-1, 2)
