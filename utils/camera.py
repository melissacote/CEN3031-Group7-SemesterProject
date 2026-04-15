import cv2
import json
import numpy as np
import os

# Safely anchor to the root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def find_available_cameras() -> list[int]:
    """
    Finds cameras available on device and returns them as a list of integers.
    :return: List of available cameras.
    """
    cameras = []
    # Check up to 3 ports, but use CAP_DSHOW to prevent the massive timeout lag on Windows
    for i in range(3):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
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
        with open(CONFIG_PATH, "w") as file:
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
        with open(CONFIG_PATH, "r") as file:
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

def initialize_camera_stream(camera_index: int) -> cv2.VideoCapture | None:
    """
    Initializes a continuous video stream optimized for OCR scanning.
    Leaves the camera open so a thread can continuously read frames.
    :param camera_index: Index of the camera to open.
    :return: An opened cv2.VideoCapture object, or None if failed.
    """
    try:
        # CAP_DSHOW to prevent startup lag (Windows specific)
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            return None
            
        # Request the high-fidelity resolution for OCR
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # Disable hardware Auto-Focus (Locks focus to infinity/fixed)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        
        # Verify what the hardware driver ACTUALLY granted
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"[Hardware Setup] Camera {camera_index} | Requested: 1920x1080 | Actual Output: {actual_width}x{actual_height}")
        
        return cap
    except Exception as e:
        print(f"[Hardware Error] Could not initialize stream: {e}")
        return None

def crop_to_roi(frame, crop_width=800, crop_height=400):
    """Crops the frame to the center Region of Interest (ROI)."""
    h, w = frame.shape[:2]
    
    # Calculate center coordinates
    start_x = (w // 2) - (crop_width // 2)
    start_y = (h // 2) - (crop_height // 2)
    end_x = start_x + crop_width
    end_y = start_y + crop_height
    
    # Slice the numpy array
    return frame[start_y:end_y, start_x:end_x]

def preprocess_for_ocr(frame):
    """Applies Grayscale and CLAHE to enhance text readability against glare."""
    # Convert to Grayscale (OCR doesn't need color, and it reduces array size by 3x)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # PaddleOCR expects a 3-channel image even if it's black and white
    # So we stack the grayscale image back to 3 channels
    final_img = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    
    return final_img