"""
gaze/eye_tracker.py
MediaPipe Face Mesh — iris landmark tracking for gaze estimation.
"""
import mediapipe as mp
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class GazeData:
    gaze_x: float   # 0.0 – 1.0 normalised screen coords
    gaze_y: float
    blink: bool     # True if both eyes blinked (acts as click)
    left_blink: bool
    right_blink: bool


# MediaPipe Face Mesh iris landmark indices
LEFT_IRIS   = [474, 475, 476, 477]
RIGHT_IRIS  = [469, 470, 471, 472]

# Eye corner landmarks for blink ratio
LEFT_EYE    = [362, 385, 387, 263, 373, 380]
RIGHT_EYE   = [33,  160, 158, 133, 153, 144]


def _eye_aspect_ratio(landmarks, eye_indices, img_w, img_h) -> float:
    pts = [(int(landmarks[i].x * img_w), int(landmarks[i].y * img_h)) for i in eye_indices]
    # Vertical distances
    v1 = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
    v2 = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
    # Horizontal distance
    h  = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
    return (v1 + v2) / (2.0 * h + 1e-6)


class EyeTracker:
    BLINK_THRESHOLD = 0.20   # EAR below this = blink

    def __init__(self, detection_conf: float = 0.7, tracking_conf: float = 0.5):
        self.mp_face = mp.solutions.face_mesh
        self.face_mesh = self.mp_face.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,       # enables iris landmarks
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        # Calibration mapping: iris center → screen fraction
        self._cal_min_x = 0.35
        self._cal_max_x = 0.65
        self._cal_min_y = 0.30
        self._cal_max_y = 0.70

    def set_calibration(self, min_x, max_x, min_y, max_y):
        self._cal_min_x = min_x
        self._cal_max_x = max_x
        self._cal_min_y = min_y
        self._cal_max_y = max_y

    def process(self, frame) -> Optional[GazeData]:
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            return None

        lm = result.multi_face_landmarks[0].landmark

        # --- Iris centre ---
        left_iris_pts  = np.array([[lm[i].x, lm[i].y] for i in LEFT_IRIS])
        right_iris_pts = np.array([[lm[i].x, lm[i].y] for i in RIGHT_IRIS])
        avg_x = float(np.mean([left_iris_pts[:, 0].mean(), right_iris_pts[:, 0].mean()]))
        avg_y = float(np.mean([left_iris_pts[:, 1].mean(), right_iris_pts[:, 1].mean()]))

        # Map to 0-1 using calibration range
        gaze_x = np.clip((avg_x - self._cal_min_x) / (self._cal_max_x - self._cal_min_x + 1e-6), 0, 1)
        gaze_y = np.clip((avg_y - self._cal_min_y) / (self._cal_max_y - self._cal_min_y + 1e-6), 0, 1)

        # --- Blink detection ---
        left_ear  = _eye_aspect_ratio(lm, LEFT_EYE,  w, h)
        right_ear = _eye_aspect_ratio(lm, RIGHT_EYE, w, h)
        left_blink  = left_ear  < self.BLINK_THRESHOLD
        right_blink = right_ear < self.BLINK_THRESHOLD
        blink = left_blink and right_blink

        # Draw iris circles on frame
        for idx in LEFT_IRIS + RIGHT_IRIS:
            cx, cy = int(lm[idx].x * w), int(lm[idx].y * h)
            cv2.circle(frame, (cx, cy), 2, (0, 170, 255), -1)

        return GazeData(
            gaze_x=float(gaze_x),
            gaze_y=float(gaze_y),
            blink=blink,
            left_blink=left_blink,
            right_blink=right_blink,
        )

    def release(self):
        self.face_mesh.close()
