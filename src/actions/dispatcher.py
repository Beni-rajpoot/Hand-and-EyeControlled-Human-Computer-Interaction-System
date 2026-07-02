"""
actions/dispatcher.py
Translates FusedOutput into real OS mouse/keyboard actions via PyAutoGUI.
"""
import pyautogui
import time
from src.fusion.cursor_fusion import FusedOutput

pyautogui.FAILSAFE = True     # Move mouse to top-left corner to abort
pyautogui.PAUSE    = 0.0      # No delay between calls (we control timing)


class ActionDispatcher:
    CLICK_COOLDOWN   = 0.6    # seconds between clicks to avoid double-clicks
    SCROLL_SCALE     = 3      # scroll ticks per unit delta

    def __init__(self):
        self._last_action_time = {}
        self._last_gesture = 'move'
        self._click_armed  = False   # rising-edge click detection

    def _cooldown_ok(self, action: str) -> bool:
        now = time.time()
        last = self._last_action_time.get(action, 0)
        if now - last >= self.CLICK_COOLDOWN:
            self._last_action_time[action] = now
            return True
        return False

    def dispatch(self, output: FusedOutput):
        if output is None:
            return

        action = output.action
        x, y   = output.screen_x, output.screen_y

        if action == 'stop':
            self._last_gesture = 'stop'
            return

        # Always move cursor (smooth)
        if action != 'stop':
            pyautogui.moveTo(x, y, duration=0)

        # Rising-edge click: fire only on transition INTO click gesture
        if action in ('click', 'blink_click'):
            if self._last_gesture not in ('click', 'blink_click'):
                if self._cooldown_ok('click'):
                    pyautogui.click(x, y)

        elif action == 'right_click':
            if self._last_gesture != 'right_click':
                if self._cooldown_ok('right_click'):
                    pyautogui.rightClick(x, y)

        elif action == 'scroll':
            ticks = int(output.scroll_delta * self.SCROLL_SCALE)
            if ticks != 0:
                pyautogui.scroll(-ticks)   # negative = down

        self._last_gesture = action
