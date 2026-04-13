import cv2
import json
import numpy as np

CONFIG_PATH = "config.json"

def find_available_cameras() -> list[int]:
    """
    Finds cameras available on device and returns them as a list of integers.
    :return: List of available cameras.
    """
    cameras = []
    for i in range(3):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append(i)
            cap.release()
    return cameras

def save_camera_preference(camera_index: int) -> bool:
    """
    Takes a camera index and saves it to JSON config file.
    :param camera_index: The index of the camera to save. 
    :return: True if preference successfully saved to config file, False otherwise.
    """
    camera = {"preferred_camera_index": camera_index}
    try:
        with open("config.json", "w") as file:
            json.dump(camera, file)
        return True
    except Exception:
        return False

def load_camera_preference() -> int | None:
    """
    Loads index of preferred camera from config file. Returns None if preference was not found.
    :return: Index of preferred camera.
    """
    try:
        with open("config.json", "r") as file:
            config_file = json.load(file)
            return config_file["preferred_camera_index"]
    except Exception:
        return None

def validate_camera_preference(preferred_camera_index: int | None, available_cameras: list[int]) -> int | None:
    """
    Checks list of available cameras for preferred camera index and returns it. If preferred camera is not available or no preferred camera is selected, returns None.
    :param preferred_camera_index: The index of the preferred camera to validate.
    :param available_cameras: List of available cameras.
    :return: Index of preferred camera if available, None otherwise.
    """
    if preferred_camera_index in available_cameras:
        return preferred_camera_index
    else:
        return None

def capture_frame(camera: int) -> np.ndarray | None:
    """
    Captures frame from camera and returns it.
    :param camera: Index of camera to use for capture.
    :return: Frame as numpy array or None if no frame was captured.
    """
    try:
        cap = cv2.VideoCapture(camera)
        ret, frame = cap.read()
        cap.release()

        if ret:
            return frame
        else:
            return None
    except Exception:
        return None

