"""
gui/main_window.py
Main PyQt5 window for the AI Hand & Eye HCI Controller.
"""
import cv2
import numpy as np
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QImage, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QShortcut,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.config_manager import PROFILE_PRESETS, apply_profile, load_config, save_config
from src.engine import ProcessingEngine


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0d0f14;
    color: #d5dde9;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #254466;
    border-radius: 8px;
    margin-top: 12px;
    padding: 9px;
    color: #72d0f7;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    background-color: #112240;
    color: #72d0f7;
    border: 1px solid #254466;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover { background-color: #1a3a6c; border-color: #72d0f7; }
QPushButton:disabled { color: #607080; border-color: #1b2b3d; background-color: #111722; }
QPushButton#btn_start { background-color: #0a3d2e; color: #19f0a8; border-color: #19f0a8; }
QPushButton#btn_stop { background-color: #3d0a0a; color: #ff6767; border-color: #ff6767; }
QPushButton#btn_pause { background-color: #3c3210; color: #ffd36b; border-color: #ffd36b; }
QSlider::groove:horizontal { height: 4px; background: #254466; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #72d0f7;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #72d0f7; border-radius: 2px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #254466; border-radius: 3px; }
QCheckBox::indicator:checked { background: #72d0f7; }
QTabWidget::pane { border: 1px solid #254466; border-radius: 6px; }
QTabBar::tab { background: #112240; color: #72d0f7; padding: 8px 13px; border-radius: 4px 4px 0 0; }
QTabBar::tab:selected { background: #1a3a6c; color: #ffffff; }
QLabel#stat_val { color: #19f0a8; font-weight: bold; font-size: 14px; }
QLabel#stat_label { color: #93a3b8; font-size: 11px; }
QStatusBar { background: #080a10; color: #72d0f7; border-top: 1px solid #254466; }
QFrame#divider { background: #254466; }
QDoubleSpinBox, QSpinBox, QComboBox {
    background: #112240;
    color: #d5dde9;
    border: 1px solid #254466;
    border-radius: 4px;
    padding: 4px;
}
"""


class StatCard(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self.val_lbl = QLabel("-")
        self.val_lbl.setObjectName("stat_val")
        self.val_lbl.setAlignment(Qt.AlignCenter)

        self.lbl = QLabel(label)
        self.lbl.setObjectName("stat_label")
        self.lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.val_lbl)
        layout.addWidget(self.lbl)
        self.setFixedHeight(64)
        self.setStyleSheet("background:#112240; border:1px solid #254466; border-radius:8px;")

    def set_value(self, value):
        self.val_lbl.setText(str(value))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Hand & Eye HCI Controller")
        self.setMinimumSize(1160, 730)
        self.setStyleSheet(DARK_STYLE)

        self.config = load_config()
        self.engine = None
        self.is_paused = False
        self.practice_step = 0
        self._screen = self._get_screen_size()

        self._build_ui()
        self._bind_shortcuts()
        self.statusBar().showMessage("Ready")

    def _get_screen_size(self) -> tuple[int, int]:
        screen = self.screen().geometry()
        return screen.width(), screen.height()

    def _bind_shortcuts(self):
        pause_shortcut = QShortcut(QKeySequence("Ctrl+Alt+H"), self)
        pause_shortcut.activated.connect(self._toggle_pause)

        esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        esc_shortcut.activated.connect(self._toggle_pause)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(10)

        self.camera_lbl = QLabel()
        self.camera_lbl.setFixedSize(640, 480)
        self.camera_lbl.setAlignment(Qt.AlignCenter)
        self.camera_lbl.setText("Camera preview")
        self.camera_lbl.setStyleSheet(
            "background:#080a10; border:1px solid #254466; border-radius:8px; color:#93a3b8;"
        )
        left.addWidget(self.camera_lbl)

        stats_row = QHBoxLayout()
        self.st_fps = StatCard("FPS")
        self.st_gesture = StatCard("Gesture")
        self.st_action = StatCard("Action")
        self.st_source = StatCard("Source")
        self.st_gaze = StatCard("Gaze X/Y")
        for widget in [self.st_fps, self.st_gesture, self.st_action, self.st_source, self.st_gaze]:
            stats_row.addWidget(widget)
        left.addLayout(stats_row)

        health_row = QHBoxLayout()
        self.st_hand = StatCard("Hand")
        self.st_face = StatCard("Face")
        self.st_mode = StatCard("Mode")
        for widget in [self.st_hand, self.st_face, self.st_mode]:
            health_row.addWidget(widget)
        left.addLayout(health_row)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self._on_start)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_pause.setEnabled(False)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_stop)
        left.addLayout(btn_row)

        root.addLayout(left, stretch=3)

        tabs = QTabWidget()
        tabs.setFixedWidth(410)
        tabs.addTab(self._build_settings_tab(), "Settings")
        tabs.addTab(self._build_calibration_tab(), "Calibration")
        tabs.addTab(self._build_setup_tab(), "Setup")
        # TODO: Add practice tab when ready
        # tabs.addTab(self._build_practice_tab(), "Practice")
        tabs.addTab(self._build_gestures_tab(), "Gestures")
        root.addWidget(tabs)

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        profile_box = QGroupBox("Profile")
        profile_layout = QGridLayout(profile_box)
        profile_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.cmb_profile = QComboBox()
        self.cmb_profile.addItems(PROFILE_PRESETS.keys())
        self.cmb_profile.setCurrentText(self.config.get("profile_name", "Balanced"))
        self.cmb_profile.currentTextChanged.connect(self._apply_profile_preset)
        profile_layout.addWidget(self.cmb_profile, 0, 1)
        layout.addWidget(profile_box)

        mod_box = QGroupBox("Modules")
        mod_layout = QVBoxLayout(mod_box)
        self.chk_hand = QCheckBox("Hand tracking")
        self.chk_eye = QCheckBox("Eye tracking")
        self.chk_hand.setChecked(self.config["active_modules"]["hand"])
        self.chk_eye.setChecked(self.config["active_modules"]["eye"])
        mod_layout.addWidget(self.chk_hand)
        mod_layout.addWidget(self.chk_eye)
        layout.addWidget(mod_box)

        smooth_box = QGroupBox("Cursor")
        smooth_layout = QGridLayout(smooth_box)
        smooth_layout.addWidget(QLabel("Smooth alpha:"), 0, 0)
        self.sl_alpha = QSlider(Qt.Horizontal)
        self.sl_alpha.setRange(5, 95)
        self.sl_alpha.setValue(int(self.config["smooth_alpha"] * 100))
        self.lbl_alpha = QLabel(f"{self.config['smooth_alpha']:.2f}")
        self.sl_alpha.valueChanged.connect(lambda v: self.lbl_alpha.setText(f"{v / 100:.2f}"))
        smooth_layout.addWidget(self.sl_alpha, 0, 1)
        smooth_layout.addWidget(self.lbl_alpha, 0, 2)

        smooth_layout.addWidget(QLabel("Hand weight:"), 1, 0)
        self.sl_hw = QSlider(Qt.Horizontal)
        self.sl_hw.setRange(0, 100)
        self.sl_hw.setValue(int(self.config["hand_weight"] * 100))
        self.lbl_hw = QLabel(f"{self.config['hand_weight']:.2f}")
        self.sl_hw.valueChanged.connect(lambda v: self.lbl_hw.setText(f"{v / 100:.2f}"))
        smooth_layout.addWidget(self.sl_hw, 1, 1)
        smooth_layout.addWidget(self.lbl_hw, 1, 2)
        layout.addWidget(smooth_box)

        click_box = QGroupBox("Click")
        click_layout = QGridLayout(click_box)
        click_layout.addWidget(QLabel("Cooldown:"), 0, 0)
        self.sp_cooldown = QDoubleSpinBox()
        self.sp_cooldown.setRange(0.2, 2.0)
        self.sp_cooldown.setSingleStep(0.1)
        self.sp_cooldown.setValue(self.config["click_cooldown"])
        click_layout.addWidget(self.sp_cooldown, 0, 1)

        self.chk_dwell = QCheckBox("Dwell click")
        self.chk_dwell.setChecked(self.config["dwell_enabled"])
        click_layout.addWidget(self.chk_dwell, 1, 0, 1, 2)

        click_layout.addWidget(QLabel("Dwell time:"), 2, 0)
        self.sp_dwell = QDoubleSpinBox()
        self.sp_dwell.setRange(0.5, 5.0)
        self.sp_dwell.setSingleStep(0.25)
        self.sp_dwell.setValue(self.config["dwell_seconds"])
        click_layout.addWidget(self.sp_dwell, 2, 1)
        layout.addWidget(click_box)

        camera_box = QGroupBox("Camera")
        camera_layout = QHBoxLayout(camera_box)
        camera_layout.addWidget(QLabel("Index:"))
        self.sp_cam = QSpinBox()
        self.sp_cam.setRange(0, 9)
        self.sp_cam.setValue(self.config["camera_index"])
        camera_layout.addWidget(self.sp_cam)
        btn_scan = QPushButton("Scan")
        btn_scan.clicked.connect(self._scan_cameras)
        camera_layout.addWidget(btn_scan)
        layout.addWidget(camera_box)

        btn_save = QPushButton("Save settings")
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)
        layout.addStretch()
        return widget

    def _build_calibration_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        cal_box = QGroupBox("Gaze range")
        cal_layout = QGridLayout(cal_box)
        cal = self.config["gaze_calibration"]

        def make_slider(value):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(value * 100))
            return slider

        self.cal_min_x = make_slider(cal["min_x"])
        self.cal_max_x = make_slider(cal["max_x"])
        self.cal_min_y = make_slider(cal["min_y"])
        self.cal_max_y = make_slider(cal["max_y"])

        rows = [
            ("Min X:", self.cal_min_x),
            ("Max X:", self.cal_max_x),
            ("Min Y:", self.cal_min_y),
            ("Max Y:", self.cal_max_y),
        ]
        for row, (label, slider) in enumerate(rows):
            cal_layout.addWidget(QLabel(label), row, 0)
            cal_layout.addWidget(slider, row, 1)
        layout.addWidget(cal_box)

        target_box = QGroupBox("Guided dots")
        target_layout = QGridLayout(target_box)
        self.calibration_points = []
        labels = ["Top left", "Top right", "Center", "Bottom left", "Bottom right"]
        positions = [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)]
        for label, pos in zip(labels, positions):
            dot = QLabel(label)
            dot.setAlignment(Qt.AlignCenter)
            dot.setMinimumHeight(44)
            dot.setStyleSheet("background:#112240; border:1px solid #254466; border-radius:6px;")
            target_layout.addWidget(dot, *pos)
            self.calibration_points.append(dot)
        layout.addWidget(target_box)

        btn_apply = QPushButton("Apply calibration")
        btn_apply.clicked.connect(self._apply_calibration)
        layout.addWidget(btn_apply)

        btn_reset = QPushButton("Reset calibration")
        btn_reset.clicked.connect(self._reset_calibration)
        layout.addWidget(btn_reset)
        layout.addStretch()
        return widget

    def _build_setup_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        self.setup_camera = QLabel("Camera: not checked")
        self.setup_hand = QLabel("Hand: waiting")
        self.setup_face = QLabel("Face: waiting")
        self.setup_actions = QLabel("Actions: stopped")
        for label in [self.setup_camera, self.setup_hand, self.setup_face, self.setup_actions]:
            label.setMinimumHeight(34)
            label.setStyleSheet("background:#112240; border:1px solid #254466; border-radius:6px; padding:6px;")
            layout.addWidget(label)

        btn_scan = QPushButton("Check camera")
        btn_scan.clicked.connect(self._scan_cameras)
        layout.addWidget(btn_scan)
        layout.addStretch()
        return widget

    def _build_practice_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        self.practice_panel = QFrame()
        self.practice_panel.setMinimumHeight(260)
        self.practice_panel.setStyleSheet("background:#080a10; border:1px solid #254466; border-radius:8px;")
        panel_layout = QGridLayout(self.practice_panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)
        self.practice_target = QPushButton("Target")
        self.practice_target.setMinimumSize(96, 54)
        self.practice_target.clicked.connect(self._advance_practice_target)
        panel_layout.addWidget(self.practice_target, 1, 1)
        layout.addWidget(self.practice_panel)

        self.practice_score = QLabel("Hits: 0")
        self.practice_score.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.practice_score)
        layout.addStretch()
        return widget

    def _build_gestures_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        gestures = [
            ("Index up", "Move cursor"),
            ("Index + middle", "Left click"),
            ("Thumb + index pinch", "Right click"),
            ("All fingers up", "Scroll"),
            ("Fist", "Freeze"),
            ("Both-eye blink", "Left click"),
        ]
        for gesture, action in gestures:
            row = QHBoxLayout()
            g_lbl = QLabel(gesture)
            g_lbl.setFixedWidth(170)
            a_lbl = QLabel(action)
            a_lbl.setStyleSheet("color:#19f0a8; font-weight:bold;")
            row.addWidget(g_lbl)
            row.addWidget(a_lbl)
            layout.addLayout(row)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)
        layout.addStretch()
        return widget

    def _apply_profile_preset(self, profile_name: str):
        self.config = apply_profile(self.config, profile_name)
        self._sync_controls_from_config()
        self._on_save()

    def _sync_controls_from_config(self):
        self.chk_hand.setChecked(self.config["active_modules"]["hand"])
        self.chk_eye.setChecked(self.config["active_modules"]["eye"])
        self.sl_alpha.setValue(int(self.config["smooth_alpha"] * 100))
        self.sl_hw.setValue(int(self.config["hand_weight"] * 100))
        self.sp_cooldown.setValue(self.config["click_cooldown"])
        self.chk_dwell.setChecked(self.config["dwell_enabled"])
        self.sp_dwell.setValue(self.config["dwell_seconds"])

    def _scan_cameras(self):
        available = []
        for index in range(5):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(index)
            cap.release()

        if available:
            self.sp_cam.setValue(available[0])
            self.setup_camera.setText(f"Camera: found {available}")
            self.statusBar().showMessage(f"Camera found at index {available[0]}", 3000)
        else:
            self.setup_camera.setText("Camera: none found")
            self.statusBar().showMessage("No camera found", 4000)

    def _on_start(self):
        self._on_save()
        self.engine = ProcessingEngine(self.config, *self._screen)
        self.engine.frame_ready.connect(self._update_frame)
        self.engine.status_ready.connect(self._update_status)
        self.engine.finished.connect(self._on_engine_finished)
        self.engine.start()

        self.is_paused = False
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("Pause")
        self.btn_stop.setEnabled(True)
        self.setup_actions.setText("Actions: running")
        self.statusBar().showMessage("Tracking active")

    def _on_stop(self):
        if self.engine:
            self.engine.stop()
            self.engine = None
        self.is_paused = False
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Pause")
        self.btn_stop.setEnabled(False)
        self.camera_lbl.setPixmap(QPixmap())
        self.camera_lbl.setText("Camera preview")
        self.st_mode.set_value("Stopped")
        self.setup_actions.setText("Actions: stopped")
        self.statusBar().showMessage("Tracking stopped")

    def _toggle_pause(self):
        if not self.engine:
            return
        self.is_paused = not self.is_paused
        self.engine.set_actions_enabled(not self.is_paused)
        self.btn_pause.setText("Resume" if self.is_paused else "Pause")
        self.st_mode.set_value("Paused" if self.is_paused else "Live")
        self.setup_actions.setText("Actions: paused" if self.is_paused else "Actions: running")
        self.statusBar().showMessage("Paused" if self.is_paused else "Tracking active", 2500)

    def _on_engine_finished(self):
        if self.engine:
            self.engine = None
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

    def _on_save(self):
        self.config["profile_name"] = self.cmb_profile.currentText()
        self.config["smooth_alpha"] = self.sl_alpha.value() / 100
        self.config["hand_weight"] = self.sl_hw.value() / 100
        self.config["click_cooldown"] = self.sp_cooldown.value()
        self.config["dwell_enabled"] = self.chk_dwell.isChecked()
        self.config["dwell_seconds"] = self.sp_dwell.value()
        self.config["camera_index"] = self.sp_cam.value()
        self.config["active_modules"]["hand"] = self.chk_hand.isChecked()
        self.config["active_modules"]["eye"] = self.chk_eye.isChecked()
        save_config(self.config)
        if self.engine:
            self.engine.update_config(self.config)
        self.statusBar().showMessage("Settings saved", 2500)

    def _apply_calibration(self):
        cal = {
            "min_x": self.cal_min_x.value() / 100,
            "max_x": self.cal_max_x.value() / 100,
            "min_y": self.cal_min_y.value() / 100,
            "max_y": self.cal_max_y.value() / 100,
        }
        if cal["min_x"] >= cal["max_x"] or cal["min_y"] >= cal["max_y"]:
            QMessageBox.warning(self, "Calibration", "Minimum values must be lower than maximum values.")
            return

        self.config["gaze_calibration"] = cal
        save_config(self.config)
        if self.engine:
            self.engine.eye_trk.set_calibration(**cal)
        self.statusBar().showMessage("Calibration applied", 3000)

    def _reset_calibration(self):
        defaults = {"min_x": 0.35, "max_x": 0.65, "min_y": 0.30, "max_y": 0.70}
        self.cal_min_x.setValue(35)
        self.cal_max_x.setValue(65)
        self.cal_min_y.setValue(30)
        self.cal_max_y.setValue(70)
        self.config["gaze_calibration"] = defaults
        save_config(self.config)
        if self.engine:
            self.engine.eye_trk.set_calibration(**defaults)
        self.statusBar().showMessage("Calibration reset", 3000)

    def _advance_practice_target(self):
        self.practice_step += 1
        positions = [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)]
        layout = self.practice_panel.layout()
        layout.removeWidget(self.practice_target)
        row, col = positions[self.practice_step % len(positions)]
        layout.addWidget(self.practice_target, row, col)
        self.practice_score.setText(f"Hits: {self.practice_step}")

    @pyqtSlot(np.ndarray)
    def _update_frame(self, frame: np.ndarray):
        h, w, channels = frame.shape
        frame_rgb = frame[..., ::-1].copy()
        image = QImage(frame_rgb.data, w, h, channels * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image).scaled(
            640,
            480,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.camera_lbl.setPixmap(pixmap)

    @pyqtSlot(dict)
    def _update_status(self, status: dict):
        if "error" in status:
            self.statusBar().showMessage(status["error"])
            self.setup_camera.setText("Camera: error")
            self._on_engine_finished()
            return

        self.st_fps.set_value(status.get("fps", "-"))
        self.st_gesture.set_value(status.get("gesture", "-"))
        self.st_action.set_value(status.get("action", "-"))
        self.st_source.set_value(status.get("source", "-"))
        self.st_gaze.set_value(f"{status.get('gaze_x', '-')}, {status.get('gaze_y', '-')}")

        hand_seen = status.get("hand_seen", False)
        face_seen = status.get("face_seen", False)
        paused = status.get("paused", False)
        self.st_hand.set_value("Seen" if hand_seen else "Missing")
        self.st_face.set_value("Seen" if face_seen else "Missing")
        self.st_mode.set_value("Paused" if paused else "Live")
        self.setup_hand.setText("Hand: detected" if hand_seen else "Hand: waiting")
        self.setup_face.setText("Face: detected" if face_seen else "Face: waiting")

    def closeEvent(self, event):
        self._on_stop()
        event.accept()
