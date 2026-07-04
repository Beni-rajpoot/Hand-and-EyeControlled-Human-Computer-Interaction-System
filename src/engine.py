"""
src/engine.py
Main processing loop. It runs in a QThread so the GUI stays responsive.
"""
import time

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from src.actions.dispatcher import ActionDispatcher
from src.fusion.cursor_fusion import CursorFusion
from src.gaze.eye_tracker import EyeTracker
from src.gesture.hand_tracker import HandTracker
from src.utils.camera import CameraThread


class ProcessingEngine(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    status_ready = pyqtSignal(dict)

    def __init__(self, config: dict, screen_w: int, screen_h: int):
        super().__init__()
        self.config = config
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._running = False
        self.actions_enabled = True

        self.camera = CameraThread(camera_index=config.get("camera_index", 0))
        self.hand_trk = HandTracker(
            detection_conf=config.get("detection_confidence", 0.7),
            tracking_conf=config.get("tracking_confidence", 0.5),
        )
        self.eye_trk = EyeTracker(
            detection_conf=config.get("detection_confidence", 0.7),
            tracking_conf=config.get("tracking_confidence", 0.5),
        )

        cal = config.get("gaze_calibration", {})
        self.eye_trk.set_calibration(
            cal.get("min_x", 0.35),
            cal.get("max_x", 0.65),
            cal.get("min_y", 0.30),
            cal.get("max_y", 0.70),
        )

        self.fusion = CursorFusion(
            screen_w=screen_w,
            screen_h=screen_h,
            hand_weight=config.get("hand_weight", 0.75),
            smooth_alpha=config.get("smooth_alpha", 0.35),
        )
        self.fusion.dwell_enabled = config.get("dwell_enabled", False)
        self.fusion.dwell_seconds = config.get("dwell_seconds", 1.5)

        self.dispatcher = ActionDispatcher()
        self.dispatcher.CLICK_COOLDOWN = config.get("click_cooldown", 0.6)
        self.modules = config.get("active_modules", {"hand": True, "eye": True})

    def run(self):
        self._running = True
        if not self.camera.start():
            self.status_ready.emit({"error": "Camera not found. Try another camera index."})
            self.hand_trk.release()
            self.eye_trk.release()
            return

        fps_counter = 0
        fps_time = time.time()
        fps = 0

        while self._running:
            frame = self.camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            hand_data = None
            gaze_data = None

            if self.modules.get("hand", True):
                hand_data = self.hand_trk.process(frame)

            if self.modules.get("eye", True):
                gaze_data = self.eye_trk.process(frame)

            fused = self.fusion.process(hand_data, gaze_data)

            if fused is not None and self.actions_enabled:
                self.dispatcher.dispatch(fused)

            fps_counter += 1
            now = time.time()
            if now - fps_time >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_time = now

            cv2.putText(frame, f"FPS: {fps}", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 170), 2)
            if fused:
                cv2.putText(frame, f"Action: {fused.action}", (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
                cv2.putText(frame, f"Source: {fused.source}", (10, 76),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            if not self.actions_enabled:
                cv2.putText(frame, "PAUSED - preview only", (10, 104),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 180, 255), 2)

            self.frame_ready.emit(frame.copy())
            self.status_ready.emit({
                "fps": fps,
                "gesture": hand_data.gesture if hand_data else "-",
                "action": fused.action if fused else "-",
                "source": fused.source if fused else "-",
                "gaze_x": round(gaze_data.gaze_x, 2) if gaze_data else "-",
                "gaze_y": round(gaze_data.gaze_y, 2) if gaze_data else "-",
                "hand_seen": hand_data is not None,
                "face_seen": gaze_data is not None,
                "paused": not self.actions_enabled,
            })

        self.camera.stop()
        self.hand_trk.release()
        self.eye_trk.release()

    def stop(self):
        self._running = False
        self.wait(3000)

    def update_config(self, config: dict):
        self.config = config
        self.fusion.set_smooth_alpha(config.get("smooth_alpha", 0.35))
        self.fusion.set_hand_weight(config.get("hand_weight", 0.75))
        self.fusion.dwell_enabled = config.get("dwell_enabled", False)
        self.fusion.dwell_seconds = config.get("dwell_seconds", 1.5)
        self.dispatcher.CLICK_COOLDOWN = config.get("click_cooldown", 0.6)
        self.modules = config.get("active_modules", {"hand": True, "eye": True})

    def set_actions_enabled(self, enabled: bool):
        self.actions_enabled = enabled
