"""
gesture/hand_tracker.py
MediaPipe Hands — detects 21 landmarks per hand.
"""
import mediapipe as mp
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class HandData:
    landmarks: list          # raw normalized landmarks
    cursor_x: float          # 0.0 – 1.0 (index fingertip)
    cursor_y: float
    gesture: str             # 'move', 'click', 'right_click', 'scroll', 'stop', 'drag'
    scroll_delta: float      # used when gesture == 'scroll'


class HandTracker:
    # Landmark indices
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    INDEX_MCP = 5
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20

    def __init__(self, max_hands: int = 1, detection_conf: float = 0.7, tracking_conf: float = 0.5):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self._prev_y = None

    def process(self, frame) -> Optional[HandData]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        if not result.multi_hand_landmarks:
            self._prev_y = None
            return None

        lm = result.multi_hand_landmarks[0].landmark

        # Draw landmarks on frame (modifies in place)
        self.mp_draw.draw_landmarks(
            frame,
            result.multi_hand_landmarks[0],
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_draw.DrawingSpec(color=(0, 255, 170), thickness=2, circle_radius=3),
            self.mp_draw.DrawingSpec(color=(0, 200, 130), thickness=1),
        )
        # Extract cursor position and classify gesture
        cursor_x = lm[self.INDEX_TIP].x
        cursor_y = lm[self.INDEX_TIP].y
        gesture, scroll_delta = self._classify_gesture(lm)

        return HandData(
            landmarks=lm,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            gesture=gesture,
            scroll_delta=scroll_delta,
        )
        
    def _finger_up(self, lm, tip: int, pip: int) -> bool:
        return lm[tip].y < lm[pip].y

    def _classify_gesture(self, lm) -> tuple[str, float]:
        index_up  = self._finger_up(lm, 8,  6)
        middle_up = self._finger_up(lm, 12, 10)
        ring_up   = self._finger_up(lm, 16, 14)
        pinky_up  = self._finger_up(lm, 20, 18)

        # Thumb: compare tip x to IP joint x (mirrored frame)
        thumb_up = lm[4].x < lm[3].x

        # Pinch detection (thumb + index close together)
        pinch_dist = np.hypot(
            lm[self.THUMB_TIP].x - lm[self.INDEX_TIP].x,
            lm[self.THUMB_TIP].y - lm[self.INDEX_TIP].y,
        )
        pinching = pinch_dist < 0.05

        # --- Gesture rules ---
        # Fist → stop
        if not any([index_up, middle_up, ring_up, pinky_up]):
            self._prev_y = None
            return 'stop', 0.0

        # Pinch → right click
        if pinching:
            return 'right_click', 0.0

        # V sign (index + middle up, ring + pinky down) → left click
        if index_up and middle_up and not ring_up and not pinky_up:
            return 'click', 0.0

        # All fingers up → scroll
        if index_up and middle_up and ring_up and pinky_up:
            curr_y = lm[self.INDEX_TIP].y
            delta = 0.0
            if self._prev_y is not None:
                delta = (curr_y - self._prev_y) * 20   # scale factor
            self._prev_y = curr_y
            return 'scroll', delta

        # Index only → move
        if index_up and not middle_up:
            return 'move', 0.0

        return 'move', 0.0

    def release(self):
        self.hands.close()
