"""Conservative feature geometry: focus and illumination are not pose evidence."""
import time
import cv2
import numpy as np


def normalized(image):
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(2,(8,8)).apply(gray)


def motion(reference, image):
    detector = cv2.ORB_create(650)
    kp1,d1 = detector.detectAndCompute(reference,None)
    kp2,d2 = detector.detectAndCompute(image,None)
    if d1 is None or d2 is None:
        return {"observable":False,"reason":"Insufficient stationary texture"}
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1,d2,k=2)
    good = [p[0] for p in pairs if len(p)==2 and p[0].distance < .7*p[1].distance]
    if len(good)<24:
        return {"observable":False,"reason":"Focus, occlusion or view change; reference cannot be verified"}
    a = np.float32([kp1[m.queryIdx].pt for m in good])
    b = np.float32([kp2[m.trainIdx].pt for m in good])
    homography,mask = cv2.findHomography(a,b,cv2.RANSAC,3)
    if homography is None:
        return {"observable":False,"reason":"No stable background transform"}
    accepted = a[mask.ravel()==1]
    coverage = cv2.contourArea(cv2.convexHull(accepted))/float(image.size) if len(accepted)>2 else 0
    h,w = image.shape
    corners = np.float32([[[0,0],[w,0],[w,h],[0,h]]])
    mapped = cv2.perspectiveTransform(corners,homography)
    displacement = float(np.median(np.linalg.norm(mapped-corners,axis=2)))
    scale = float(np.sqrt(abs(np.linalg.det(homography[:2,:2]))))
    angle = abs(float(np.degrees(np.arctan2(homography[1,0],homography[0,0]))))
    focus_ambiguous = abs(scale-1)>.025 and angle<.8
    return {"observable":coverage>.22 and int(mask.sum())>=24,
            "coverage":round(coverage,3),"inliers":int(mask.sum()),
            "displacement_px":round(displacement,2),"scale":round(scale,3),"focus_ambiguous":focus_ambiguous,
            "moved":displacement>max(12,w*.035) and not focus_ambiguous}


class Scene:
    def __init__(self):
        self.reference = None
        self.pending = 0
        self.revision = 0
        self.calibration = None
        self.state = {"geometry_valid":False,"pose":None,"calibration_revision":None,
                      "regions":[],"objects":[],"status":"No observation","markers":[]}

    def invalidate(self, reason):
        self.revision += 1
        self.state.update(geometry_valid=False,pose=None,regions=[],objects=[],
                          status=reason,revision=self.revision)

    def observe(self, image, camera, timestamp=None):
        stamp = time.time() if timestamp is None else timestamp
        if time.time()-stamp>3 or stamp>time.time()+1:
            self.invalidate("Stale camera frame")
            return self.state
        if self.state.get("camera_id") not in (None,camera):
            self.invalidate("Camera identity changed; spatial assumptions invalidated")
            self.reference = None
        gray = normalized(image)
        quality = self.quality(image)
        changed = self.compare(gray)
        self.state.update(camera_id=camera,observed_at=stamp,resolution=list(image.shape[1::-1]),
                          revision=self.revision,quality=quality,motion=changed,markers=self.markers(gray))
        from .geometry import pose
        applicable = self.calibration if self.calibration and self.calibration.get("camera_id")==camera and not changed.get("focus_ambiguous") else None
        self.state.update(pose(applicable,self.state["markers"],list(image.shape[1::-1])))
        if self.reference is None:
            self.reference = gray.copy()
            self.state["status"] = "Image assistance available; metric geometry unavailable"
        if quality["dark"]:
            self.state["guidance"] = "The image is dark. Increase workspace lighting before checking object visibility."
        else:
            self.state["guidance"] = "No calibrated workspace geometry is available. Show reference markers for spatial checks."
        clipped = [r["name"] for r in self.state["regions"] if r["fraction_of_corners_visible"]<1]
        if clipped and not quality["dark"]:
            self.state["guidance"] = "The configured "+", ".join(clipped)+" region projects partly outside the frame. Reframe to include it, then recheck the fixed markers."
        return self.state

    def compare(self, gray):
        result = motion(self.reference,gray) if self.reference is not None and self.reference.shape==gray.shape else {"observable":False}
        self.pending = self.pending+1 if result.get("observable") and result.get("moved") else 0
        if self.pending>=2:
            self.invalidate("Camera viewpoint changed; spatial assumptions invalidated")
            self.reference = gray.copy()
            self.pending = 0
        if self.reference is not None and (not result.get("observable") or result.get("focus_ambiguous")):
            self.state.update(geometry_valid=False,pose=None,status="Reference unverified; geometry suspended")
        return result

    def quality(self, image):
        gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        return {"brightness":round(float(gray.mean()),1),"dark":bool(gray.mean()<45),
                "sharpness":round(float(cv2.Laplacian(gray,cv2.CV_64F).var()),1)}

    def markers(self, gray):
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        corners,ids,_ = cv2.aruco.ArucoDetector(dictionary).detectMarkers(gray)
        return [] if ids is None else [{"id":int(i),"corners":c.reshape(4,2).tolist()} for i,c in zip(ids.ravel(),corners)]
