"""
utils/smoother.py
Exponential Moving Average smoother — removes cursor jitter.
"""


class EMASmoother:
    """
    Exponential Moving Average.
    alpha closer to 1.0 = more responsive but jittery.
    alpha closer to 0.0 = smoother but laggy.
    Recommended: 0.25 – 0.45
    """

    def __init__(self, alpha: float = 0.35):
        self.alpha = alpha
        self._x = None
        self._y = None

    def smooth(self, x: float, y: float) -> tuple[float, float]:
        if self._x is None:
            self._x, self._y = x, y
        else:
            self._x = self.alpha * x + (1 - self.alpha) * self._x
            self._y = self.alpha * y + (1 - self.alpha) * self._y
        return self._x, self._y

    def reset(self):
        self._x = None
        self._y = None

    def set_alpha(self, alpha: float):
        self.alpha = max(0.05, min(0.95, alpha))
