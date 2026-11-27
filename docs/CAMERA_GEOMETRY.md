# Viewpoint changes, focus and workspace geometry

The C920 has autofocus and automatic exposure. A change in sharpness, brightness or apparent scale alone is insufficient evidence that the physical camera moved.

Homebrain normalizes illumination with CLAHE and matches ORB features using RANSAC. It requires distributed inliers and repeated displacement before reporting a viewpoint change. Approximate scale-only changes are treated as focus-breathing ambiguity. Missing stationary texture suspends geometry. This is a conservative image-reference check, not a calibrated pose tracker and not proof that the robot or camera is stationary.

Use fixed laboratory structure around the workspace as reference features. Avoid relying on the moving arm, movable box or carried object. A usable view includes pickup, travel, release and destination; markers/reference areas must remain visible. An operator-reviewed framing receipt does not establish metric geometry or scientific station qualification.

ArUco 4×4/50 detection and PnP are implemented with OpenCV. Optional calibration imports require measured camera intrinsics, resolution, fixed marker world corners and region definitions. Calibration identity and image resolution must match the actual camera. Known corners can support visibility checks and pose estimation; unknown intrinsics or reference coordinates produce unknown geometry.

AprilTag 36h11 is an alternative for robust fiducial identity. It should be compared under the real C920 distance, exposure, blur and occlusion conditions before choosing a different detector. The current app does not claim that an AprilTag detector or a physically measured marker map has been qualified. No new marker hardware is required for the first native recording.

A detected viewpoint change invalidates geometry-dependent memory and blocks reuse of the old framing qualification. Reframe and inspect the actual views. Smart Swarm requires its authoritative station requalification. Stream interruption also invalidates confidence in the old references; no motor action resumes on reconnect.
