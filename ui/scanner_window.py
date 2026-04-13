import cv2
import numpy as np
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from services.ocr_engine import extract_text_from_frame, parse_medication_label
from utils.camera import load_camera_preference, initialize_camera_stream

class VideoThread(QThread):
    """
    A separate thread that continuously captures video frames from the webcam and 
    calculates a focus score to determine if the image is sharp enough for OCR processing. 
    It emits signals to update the UI with the current frame and focus score.
    """
    change_pixmap_signal = pyqtSignal(np.ndarray)
    focus_score_signal = pyqtSignal(float)

    def __init__(self, camera_index=0):
        super().__init__()
        self._run_flag = True
        self.camera_index = camera_index

    def run(self):
        """Captures video frames and calculates focus score in real-time."""
        cap = initialize_camera_stream(self.camera_index)

        if cap is None:
            print(f"Error: Could not open camera {self.camera_index}")
            return
        
        while self._run_flag:
            ret, cv_img = cap.read()
            if ret:
                # Focus Math: Calculate variance of Laplacian
                gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                focus_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                self.focus_score_signal.emit(focus_score)

                # Emit frame to UI
                self.change_pixmap_signal.emit(cv_img)
        
        cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class OCRScannerDialog(QDialog):
    """
    A dialog window that activates the webcam, processes the video feed in 
    real-time to detect focus, and allows the user to capture a frame for OCR processing.
    The parsed data is returned as a dictionary for auto-filling the medication form.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MedRec Smart Scanner")
        self.resize(800, 700)
        self.scanned_data = {} 

        layout = QVBoxLayout(self)

        # Video Feed with Focus Border
        self.image_label = QLabel("Initializing Camera...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet("border: 5px solid #c0392b; background: black;") # Start Red
        layout.addWidget(self.image_label)

        self.status_label = QLabel("Center the label and wait for focus...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2980b9;")
        layout.addWidget(self.status_label)

        self.capture_btn = QPushButton("Capture && Read Text")
        self.capture_btn.setEnabled(False) # Locked until focused
        self.capture_btn.setStyleSheet("padding: 15px; font-size: 16px;")
        self.capture_btn.clicked.connect(self.process_manual_ocr)
        layout.addWidget(self.capture_btn)

        self.current_frame = None
        # Ask camera.py which camera the user saved in their settings
        preferred_cam = load_camera_preference()
        
        # If they haven't saved one yet, default to the main webcam (0)
        if preferred_cam is None:
            preferred_cam = 0

        self.thread = VideoThread(camera_index=preferred_cam)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.focus_score_signal.connect(self.update_focus_ui)
        self.thread.start()

    def update_focus_ui(self, score):
        """Updates the border color and button state based on the focus score."""
        print(f"Current Focus Score: {score}")
        if score > 60: # Threshold for sharpness
            self.image_label.setStyleSheet("border: 5px solid #27ae60; background: black;")
            if not self.capture_btn.isEnabled():
                self.capture_btn.setEnabled(True)
                self.status_label.setText("READY: Image is in focus.")
        else:
            self.image_label.setStyleSheet("border: 5px solid #c0392b; background: black;")
            self.capture_btn.setEnabled(False)
            self.status_label.setText("BLURRY: Move bottle slowly until border is Green.")

    def update_image(self, cv_img):
        """Receives a new frame from the video thread, converts it to QImage, and updates the QLabel.
        Also stores the current frame for OCR processing when the button is clicked.
        """
        self.current_frame = cv_img
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        qt_img = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)

    def process_manual_ocr(self):
        """Triggered when user clicks the capture button. It processes the current frame with OCR and updates the scanned_data dictionary."""
        if self.current_frame is not None:
            self.capture_btn.setText("Analyzing Label...")
            self.capture_btn.setEnabled(False)
            
            raw_text = extract_text_from_frame(self.current_frame)
            ocr_results = parse_medication_label(raw_text)
            
            self.scanned_data.update(ocr_results)
            
            if 'medication_name' in self.scanned_data:
                self.accept() # Close the dialog and return the data.
            else:
                # Display the error cleanly in the status label
                self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #c0392b;")
                self.status_label.setText("Could not identify drug name. Reposition bottle and try again.")
                
                self.capture_btn.setEnabled(True)
                self.capture_btn.setText("Capture && Read Text")

    def closeEvent(self, event):
        """Ensures the video thread is properly stopped when the dialog is closed."""
        self.thread.stop()
        event.accept()