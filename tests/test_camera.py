from unittest.mock import patch, MagicMock, mock_open
from utils.camera import find_available_cameras, save_camera_preference, load_camera_preference, \
    validate_camera_preference, capture_frame


def test_find_available_cameras_success():
    with patch("utils.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_cap.return_value = mock_instance
        mock_instance.isOpened.return_value = True
        result = find_available_cameras()
        assert result == [0, 1, 2]

def test_find_available_cameras_success_skipped_index():
    with patch("utils.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_cap.return_value = mock_instance
        mock_instance.isOpened.side_effect = [True, False, True]
        result = find_available_cameras()
        assert result == [0, 2]

def test_find_available_cameras_no_camera():
    with patch("utils.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_cap.return_value = mock_instance
        mock_instance.isOpened.return_value = False
        result = find_available_cameras()
        assert result == []

def test_save_camera_preference_success():
    with patch("builtins.open", mock_open()):
        result = save_camera_preference(0)
        assert result == True

def test_save_camera_preference_failure():
    with patch("builtins.open") as mock_file:
        mock_file.side_effect = Exception
        result = save_camera_preference(0)
        assert result == False

def test_load_camera_preference_success():
    with patch("builtins.open", mock_open(read_data='{"preferred_camera_index": 1}')):
        result = load_camera_preference()
        assert result == 1

def test_load_camera_preference_failure():
    with patch("builtins.open") as mock_file:
        mock_file.side_effect = Exception
        result = load_camera_preference()
        assert result is None

def test_validate_camera_preference_success():
    preferred_camera_index = 0
    cameras = [0, 1]
    result = validate_camera_preference(preferred_camera_index, cameras)
    assert result == preferred_camera_index

def test_validate_camera_preference_failure():
    preferred_camera_index = 1
    cameras = [0]
    result = validate_camera_preference(preferred_camera_index, cameras)
    assert result is None

def test_validate_camera_preference_none():
    preferred_camera_index = None
    cameras = [0]
    result = validate_camera_preference(preferred_camera_index, cameras)
    assert result is None

def test_validate_camera_preference_empty_list():
    preferred_camera_index = 0
    cameras = []
    result = validate_camera_preference(preferred_camera_index, cameras)
    assert result is None

def test_capture_frame_success():
    with patch("utils.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_cap.return_value = mock_instance
        mock_instance.read.return_value = (True, MagicMock())
        result = capture_frame(0)
        assert result is not None

def test_capture_frame_failure():
    with patch("utils.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_cap.return_value = mock_instance
        mock_instance.read.return_value = (False, None)
        result = capture_frame(0)
        assert result is None

