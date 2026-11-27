"""Synthetic imagery tests are not physical camera-movement verification."""
import time
import cv2
import numpy as np
from homebrain.scene import Scene,motion,normalized
from homebrain.vision import Vision


def textured():
    rng = np.random.default_rng(44)
    image = np.zeros((480,640,3),np.uint8)+110
    for x,y in rng.integers([10,10],[630,470],(350,2)):
        cv2.circle(image,(int(x),int(y)),3,(235,235,235),-1)
    return image


def test_camera_translation_invalidates_geometry():
    scene = Scene()
    image = textured()
    scene.observe(image,"fixture")
    moved = cv2.warpAffine(image,np.float32([[1,0,40],[0,1,25]]),(640,480))
    scene.observe(moved,"fixture")
    result = scene.observe(moved,"fixture")
    assert result["revision"]==1
    assert not result["geometry_valid"]
    assert result["pose"] is None


def test_foreground_object_does_not_mean_camera_movement():
    image = textured()
    changed = image.copy()
    cv2.rectangle(changed,(260,180),(320,240),(255,0,0),-1)
    result = motion(normalized(image),normalized(changed))
    assert result["observable"] and not result["moved"]


def test_exposure_and_focus_are_not_movement():
    image = textured()
    exposure = np.clip(image.astype(float)*.6+20,0,255).astype(np.uint8)
    focus = cv2.GaussianBlur(image,(5,5),1)
    assert not motion(normalized(image),normalized(exposure)).get("moved",False)
    assert not motion(normalized(image),normalized(focus)).get("moved",False)


def test_stale_frames_and_missing_markers():
    scene = Scene()
    image = textured()
    result = scene.observe(image,"fixture")
    assert result["markers"]==[] and not result["geometry_valid"]
    scene.observe(image,"fixture",time.time()-20)
    assert scene.state["status"]=="Stale camera frame"


def test_aruco_marker_detection():
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),7,100)
    image = np.ones((300,300),np.uint8)*255
    image[100:200,100:200]=marker
    scene = Scene()
    result = scene.observe(cv2.cvtColor(image,cv2.COLOR_GRAY2BGR),"fixture")
    assert result["markers"][0]["id"]==7
    assert not result["geometry_valid"]
