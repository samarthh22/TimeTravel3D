"""Read ETH3D's actual COLMAP text calibration; never guess intrinsics.

Extrinsics use X_camera = R @ X_world + t, quaternion order w,x,y,z.
COLMAP keypoint coordinates refer to pixel centers at (0.5, 0.5);
OpenCV coordinates use (0, 0), so principal points are shifted by -0.5.
Provided points3D/feature observations are deliberately not used as SfM input.
"""
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation


@dataclass
class Camera:
    id: int
    width: int
    height: int
    K: np.ndarray


@dataclass
class View:
    id: int
    camera_id: int
    name: str
    path: Path
    R: np.ndarray
    t: np.ndarray

    @property
    def center(self):
        return -self.R.T @ self.t


def read_cameras(path):
    cameras = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cid, model, w, h, *params = line.split()
        if model == "PINHOLE" and len(params) == 4:
            fx, fy, cx, cy = map(float, params)
        elif model == "SIMPLE_PINHOLE" and len(params) == 3:
            fx, cx, cy = map(float, params)
            fy = fx
        else:
            raise ValueError(f"Unsupported camera model {model}; use undistorted PINHOLE images")
        K = np.array([[fx, 0, cx - 0.5], [0, fy, cy - 0.5], [0, 0, 1.]])
        if not np.isfinite(K).all() or min(fx, fy) <= 0:
            raise ValueError("Invalid camera intrinsics")
        cameras[int(cid)] = Camera(int(cid), int(w), int(h), K)
    if not cameras:
        raise ValueError(f"No cameras in {path}")
    return cameras


def read_views(path, image_root):
    # Preserve empty observation lines: filtering blank lines would corrupt
    # ETH3D two-view images.txt, which has empty second lines.
    lines = Path(path).read_text().splitlines()
    views, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#"):
            continue
        fields = line.split(maxsplit=9)
        if len(fields) != 10:
            raise ValueError(f"Malformed image pose in {path}: {line[:80]}")
        iid, qw, qx, qy, qz, tx, ty, tz, cid, name = fields
        q = np.array([qx, qy, qz, qw], dtype=float)
        R = Rotation.from_quat(q).as_matrix()
        t = np.array([tx, ty, tz], dtype=float)
        candidate = Path(image_root) / name
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        views.append(View(int(iid), int(cid), name, candidate, R, t))
        if i >= len(lines):
            raise ValueError(f"Missing observation line in {path}")
        i += 1  # supplied feature observations are not ground truth
    if not views:
        raise ValueError(f"No images in {path}")
    return sorted(views, key=lambda v: v.name)


def load_scene(scene):
    scene = Path(scene)
    if (scene / "cameras.txt").is_file():
        calibration, image_root, category = scene, scene, "two_view"
    else:
        choices = [p for p in scene.glob("*_calibration_undistorted") if p.is_dir()]
        if len(choices) != 1:
            raise ValueError(f"Expected one undistorted calibration directory in {scene}")
        calibration, image_root = choices[0], scene / "images"
        category = "rig" if "rig" in calibration.name else "dslr"
    cameras = read_cameras(calibration / "cameras.txt")
    views = read_views(calibration / "images.txt", image_root)
    for view in views:
        if view.camera_id not in cameras:
            raise ValueError(f"Missing camera {view.camera_id}")
    return cameras, views, category


def load_image(view, camera, max_size=1600):
    image = cv2.imread(str(view.path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot read image: {view.path}")
    h, w = image.shape[:2]
    if (w, h) != (camera.width, camera.height):
        raise ValueError(f"Image/calibration size mismatch for {view.name}")
    scale = min(1., max_size / max(w, h)) if max_size > 0 else 1.
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    if (nw, nh) != (w, h):
        image = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    # cv2.resize maps centers using x' = sx*(x+0.5)-0.5.
    K = camera.K.copy()
    K[0, 0] *= nw / w
    K[1, 1] *= nh / h
    K[0, 2] = (K[0, 2] + 0.5) * nw / w - 0.5
    K[1, 2] = (K[1, 2] + 0.5) * nh / h - 0.5
    return image, K


def inspect_scene(scene):
    cameras, views, category = load_scene(scene)
    groups = {}
    for v in views:
        groups[v.camera_id] = groups.get(v.camera_id, 0) + 1
    return {
        "scene": Path(scene).name, "category": category,
        "image_count": len(views), "images_per_camera": groups,
        "cameras": [{"id": c.id, "width": c.width, "height": c.height,
                     "K_opencv": c.K.tolist()} for c in cameras.values()],
        "supplied_poses": True, "pose_convention": "world_to_camera",
        "supplied_points_used": False,
        "first_images": [v.name for v in views[:5]],
        "note": "Rig timestamps are image stems in nanoseconds; extrinsics are supplied per image.",
    }
