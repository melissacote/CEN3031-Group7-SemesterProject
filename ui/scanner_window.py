import cv2
import numpy as np
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from services.ocr_engine import extract_text_from_frame, parse_medication_label
from utils.camera import load_camera_preference, initialize_camera_stream, crop_to_roi, preprocess_for_ocr

class VideoThread(QThread):
    """
    A separate thread that continuously captures video frames from the webcam and 
    calculates a focus score to determine if the image is sharp enough for OCR processing. 
    It emits signals to update the UI with the current frame and focus score.
    """
    change_pixmap_signal = pyqtSignal(np.ndarray)
    focus_score_signal = pyqtSignal(float, float) 

    def __init__(self, camera_index=0):
        super().__init__()
        self.daemon = True
        self._run_flag = True
        self.camera_index = camera_index
        self.setTerminationEnabled(True)

    def run(self):
        """Captures video frames and calculates focus score in real-time."""
        cap = initialize_camera_stream(self.camera_index)

        if cap is None:
            print(f"Error: Could not open camera {self.camera_index}")
            return
        
        # Calibration Setup
        calibration_frames = 30
        baseline_sum = 0
        baseline_focus = 0
        frame_count = 0

        while self._run_flag:
            ret, cv_img = cap.read()
            if ret:
                # Focus Math: Calculate variance of Laplacian
                gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                focus_score = cv2.Laplacian(gray, cv2.CV_64F).var()

                # Calibration Phase: Learn the camera's baseline blurriness
                if frame_count < calibration_frames:
                    baseline_sum += focus_score
                    frame_count += 1
                    if frame_count == calibration_frames:
                        baseline_focus = baseline_sum / calibration_frames
                    self.focus_score_signal.emit(focus_score, 9999.0)
                else:
                    # Dynamic Phase: Require 1.5x sharpness over the baseline (or flat 15 minimum)
                    threshold = max(baseline_focus * 1.5, 15.0)
                    self.focus_score_signal.emit(focus_score, threshold)

                # Emit frame to UI
                self.change_pixmap_signal.emit(cv_img)
        
        if cap.isOpened():
            # Restore OS-level Auto-Focus BEFORE releasing the hardware lock
            # cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            cap.release()

    def stop(self):
        self._run_flag = False
        # Give the thread a moment to exit the loop
        if not self.wait(500): # Wait 500ms
            self.terminate()   # Force kill if it doesn't stop gracefully

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
        self.image_label.setStyleSheet("border: 5px solid #f39c12; background: black;") # Start Yellow/Orange
        layout.addWidget(self.image_label)

        self.status_label = QLabel("Calibrating camera... Keep background clear.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2980b9;")
        layout.addWidget(self.status_label)

        self.capture_btn = QPushButton("Capture && Read Text")
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

    def update_focus_ui(self, score, threshold):
        """Updates the border color and button state based on the focus score."""
        if threshold == 9999.0:
            return # Still in calibration phase, do nothing
            
        if score > threshold: 
            self.image_label.setStyleSheet("border: 5px solid #27ae60; background: black;")
            self.status_label.setText("READY: Image is in focus.")
        else:
            self.image_label.setStyleSheet("border: 5px solid #f39c12; background: black;") 
            self.status_label.setText("BLURRY: Move bottle slowly, or click Capture if legible.")

    def update_image(self, cv_img):
        """Receives a new frame from the video thread, converts it to QImage, and updates the QLabel.
        Also stores the current frame for OCR processing when the button is clicked.
        """
        # Save a clean, unaltered copy of the frame for the OCR engine
        self.current_frame = cv_img.copy()

        # Get frame dimensions to calculate the center
        h, w, ch = cv_img.shape

        # Define the exact dimensions used in camera.crop_to_roi() function
        crop_width = 800
        crop_height = 400
        
        # Calculate the center box coordinates
        start_x = (w // 2) - (crop_width // 2)
        start_y = (h // 2) - (crop_height // 2)
        end_x = start_x + crop_width
        end_y = start_y + crop_height

        # Draw the targeting box on the UI frame (Cyan color)
        cv2.rectangle(cv_img, (start_x, start_y), (end_x, end_y), (255, 255, 0), 4)
        
        # Dim the background outside the box to make the target area pop
        mask = np.zeros_like(cv_img)
        cv2.rectangle(mask, (start_x, start_y), (end_x, end_y), (255, 255, 255), -1)
        cv_img = np.where(mask == np.array([255, 255, 255]), cv_img, cv2.addWeighted(cv_img, 0.4, np.zeros_like(cv_img), 0.6, 0))

        # Add instructions above the box
        cv2.putText(cv_img, "Align Medication Label Here", (start_x, start_y - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)

        # Convert the marked-up frame to PyQt format for UI display
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        qt_img = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)

    def process_manual_ocr(self):
        """Triggered when user clicks the capture button. It processes the current frame with OCR and updates the scanned_data dictionary."""
        if self.current_frame is not None:
            self.capture_btn.setText("Analyzing Label...")
            self.capture_btn.setEnabled(False)
            self.status_label.setText("Processing OCR... Please wait.")
            
            # Crop to the center Region of Interest to remove background noise
            cropped_frame = crop_to_roi(self.current_frame)
            
            # Apply CLAHE contrast fixing to destroy webcam glare
            clean_frame = preprocess_for_ocr(cropped_frame)
            
            # Send the highly optimized frame to PaddleOCR
            raw_text = extract_text_from_frame(clean_frame)
            
            # --- Fetch the current user's name dynamically to blacklist it ---
            dynamic_blacklist = []
            
            # The AddMedicationDialog is the parent, and it holds the active user_id
            if self.parent() and hasattr(self.parent(), 'user_id'):
                active_user_id = self.parent().user_id
                import sqlite3
                import os
                
                db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'medrec.db')
                try:
                    with sqlite3.connect(db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT first_name, last_name FROM users WHERE user_id = ?", (active_user_id,))
                        user_record = cursor.fetchone()
                        
                        if user_record:
                            if user_record[0]: dynamic_blacklist.append(user_record[0].lower())
                            if user_record[1]: dynamic_blacklist.append(user_record[1].lower())
                except Exception as e:
                    print(f"Could not fetch dynamic PII blacklist: {e}")
            
            # Parse the text using the multi-stage security heuristics
            ocr_results = parse_medication_label(raw_text, patient_name_words=dynamic_blacklist)
            
            # Completely wipe out any data from previous scans
            self.scanned_data.clear() 
            
            # Now save the fresh data
            self.scanned_data.update(ocr_results)
            
            if 'medication_name' in self.scanned_data:
                self.thread.stop()
                self.thread.wait()
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
        self.thread.wait()
        # Standard exit
        event.accept()