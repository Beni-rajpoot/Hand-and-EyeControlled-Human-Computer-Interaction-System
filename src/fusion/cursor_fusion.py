"""
fusion/cursor_fusion.py
Combines hand gesture + eye gaze into a single cursor position.
Weight is configurable: 1.0 = full hand, 0.0 = full eye.
"""
from src.gesture.hand_tracker import HandData
from src.gaze.eye_tracker import GazeData
from src.utils.smoother import EMASmoother
from typing import Optional
from dataclasses import dataclass


@dataclass
class FusedOutput:
    screen_x: int       # final pixel position
    screen_y: int
    action: str         # 'move', 'click', 'right_click', 'scroll', 'stop', 'blink_click'
    scroll_delta: float
    source: str         # 'hand', 'eye', 'fused'


class CursorFusion:
    def __init__(self, screen_w: int, screen_h: int,
                 hand_weight: float = 0.75,
                 smooth_alpha: float = 0.35):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.hand_weight = hand_weight          # 0.0–1.0
        self.eye_weight  = 1.0 - hand_weight
        self.smoother = EMASmoother(alpha=smooth_alpha)

        # Dwell click (for motor-impaired users)
        self.dwell_enabled = False
        self.dwell_seconds = 1.5
        self._dwell_start = None
        self._dwell_pos   = None
        self._dwell_radius = 30   # px

    def set_smooth_alpha(self, alpha: float):
        self.smoother.set_alpha(alpha)

    def set_hand_weight(self, w: float):
        self.hand_weight = max(0.0, min(1.0, w))
        self.eye_weight  = 1.0 - self.hand_weight

    def process(self,
                hand: Optional[HandData],
                gaze: Optional[GazeData],
                dt: float = 0.033) -> Optional[FusedOutput]:

        # --- Determine raw normalised position ---
        nx, ny = None, None
        action = 'move'
        scroll_delta = 0.0
        source = 'fused'

        if hand is not None:
            hx, hy = hand.cursor_x, hand.cursor_y
            action = hand.gesture
            scroll_delta = hand.scroll_delta

        if gaze is not None:
            gx, gy = gaze.gaze_x, gaze.gaze_y
            # Blink = click (only when hand is in 'move' or stop mode)
            if gaze.blink and action in ('move', 'stop'):
                action = 'blink_click'

        # Fusion
        if hand is not None and gaze is not None:
            nx = self.hand_weight * hand.cursor_x + self.eye_weight * gaze.gaze_x
            ny = self.hand_weight * hand.cursor_y + self.eye_weight * gaze.gaze_y
            source = 'fused'
        elif hand is not None:
            nx, ny = hand.cursor_x, hand.cursor_y
            source = 'hand'
        elif gaze is not None:
            nx, ny = gaze.gaze_x, gaze.gaze_y
            source = 'eye'
            action = 'move'
            if gaze.blink:
                action = 'blink_click'
        else:
            return None

        if action == 'stop':
            self.smoother.reset()
            return FusedOutput(
                screen_x=0, screen_y=0,
                action='stop', scroll_delta=0.0, source=source
            )

        # Smooth
        sx, sy = self.smoother.smooth(nx, ny)

        # Map to screen pixels
        px = int(sx * self.screen_w)
        py = int(sy * self.screen_h)
        px = max(0, min(self.screen_w - 1, px))
        py = max(0, min(self.screen_h - 1, py))

        # Dwell click logic
        if self.dwell_enabled and action == 'move':
            import time, math
            now = time.time()
            if self._dwell_pos is None:
                self._dwell_pos   = (px, py)
                self._dwell_start = now
            else:
                dist = math.hypot(px - self._dwell_pos[0], py - self._dwell_pos[1])
                if dist > self._dwell_radius:
                    self._dwell_pos   = (px, py)
                    self._dwell_start = now
                elif (now - self._dwell_start) >= self.dwell_seconds:
                    action = 'click'
                    self._dwell_start = now

        return FusedOutput(
            screen_x=px, screen_y=py,
            action=action,
            scroll_delta=scroll_delta,
            source=source,
        )
