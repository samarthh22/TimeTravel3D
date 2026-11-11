# Course alignment

Source: the user's `CVsyllabus.pdf`, LNMIIT BTech CCE Computer Vision,
updated July 2026. The user confirmed this is the intended CIF.

| CIF topic | Implementation / evidence |
|---|---|
| Unit I: image formation and digital camera; geometric transformations | Calibrated PINHOLE model, resizing intrinsics, world-to-camera transformations in `data.py` and `geometry.py` |
| Unit III 3.2-3.3: DoG and SIFT | OpenCV SIFT detector and descriptors in `features.py`; DoG is part of SIFT, not separately reimplemented |
| Unit III 3.4: feature matching | Descriptor distance, Lowe ratio, mutual matching in `features.py` |
| Unit III 3.5: RANSAC | Robust essential-matrix estimation in `geometry.py` |
| Unit V 5.1: epipolar geometry | Calibrated essential matrix and normalized image coordinates |
| Unit V 5.2: stereo vision | ETH3D stereo pairs with real intrinsics; sparse geometry, not a dense stereo network |
| Unit V 5.3: triangulation | Homogeneous triangulation, finite-point and cheirality checks, camera-center ray angles |
| Unit V 5.4: Structure from Motion | Estimated two-view initialization, consistent tracks, incremental PnP registration, consensus multi-view triangulation, constrained sparse bundle adjustment |

The project is centered on CO-3 (feature detection/matching) and CO-5
(3D reconstruction), with CO-1 camera geometry as a foundation. It does not
claim to implement every unit, deep learning architecture, or optical flow lab.

The syllabus lists a 10% lab project. The separate handover specifies the
motivation/PPT/code/viva rubric and ten-slide structure; those details are
handover requirements, not text verified in the syllabus.
