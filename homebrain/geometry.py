"""Workspace pose only from operator-supplied calibration and fixed markers."""
import hashlib
import json
import cv2
import numpy as np


def calibration(data):
    matrix = np.asarray(data["intrinsics"],dtype=float)
    distortion = np.asarray(data.get("distortion",[0,0,0,0,0]),dtype=float)
    if matrix.shape!=(3,3) or not np.isfinite(matrix).all() or matrix[0,0]<=0 or matrix[1,1]<=0:
        raise ValueError("Invalid intrinsic calibration")
    if not data.get("camera_id") or not data.get("fixed_marker_world_corners") or len(data["resolution"])!=2:
        raise ValueError("Supply fixed marker coordinates and calibrated resolution")
    if not np.isfinite(distortion).all():
        raise ValueError("Invalid distortion")
    return {**data,"revision":hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:16]}


def pose(data, markers, resolution):
    if data is None or data["resolution"]!=resolution:
        return {"geometry_valid":False,"pose":None,"regions":[]}
    known = data["fixed_marker_world_corners"]
    visible = [m for m in markers if str(m["id"]) in known]
    if not visible:
        return {"geometry_valid":False,"pose":None,"regions":[]}
    points = np.asarray([p for m in visible for p in known[str(m["id"])]],np.float32)
    pixels = np.asarray([p for m in visible for p in m["corners"]],np.float32)
    matrix = np.asarray(data["intrinsics"],float)
    distortion = np.asarray(data.get("distortion",[0,0,0,0,0]),float)
    ok,rotation,translation = cv2.solvePnP(points,pixels,matrix,distortion)
    if not ok or float(translation[2,0])<=0:
        return {"geometry_valid":False,"pose":None,"regions":[]}
    projected,_ = cv2.projectPoints(points,rotation,translation,matrix,distortion)
    error = float(np.mean(np.linalg.norm(projected.reshape(-1,2)-pixels,axis=1)))
    regions = project_regions(data,rotation,translation,matrix,distortion,resolution) if error<2 else []
    return {"geometry_valid":error<2,"pose":{"rotation_vector":rotation.ravel().tolist(),
            "translation_m":translation.ravel().tolist(),"reprojection_error_px":error,
            "basis":"operator supplied fixed-marker world coordinates"},"regions":regions,
            "calibration_revision":data["revision"]}


def project_regions(data, rotation, translation, matrix, distortion, resolution):
    regions = []
    for name,corners in data.get("workspace_regions",{}).items():
        points,_ = cv2.projectPoints(np.asarray(corners,np.float32),rotation,translation,matrix,distortion)
        pixels = points.reshape(-1,2)
        inside = (pixels[:,0]>=0)&(pixels[:,0]<resolution[0])&(pixels[:,1]>=0)&(pixels[:,1]<resolution[1])
        regions.append({"name":name,"pixels":pixels.tolist(),"fraction_of_corners_visible":float(inside.mean()),
                        "basis":"projection of operator-defined region, not object detection"})
    return regions
