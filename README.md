# AI-Powered Hand & Eye HCI Controller

Control your Windows PC using **hand gestures** and **eye gaze** — no mouse, no keyboard.

---

## ⚡ Quick Setup (Windows)

### Step 1 — Install Python
Download **Python 3.11** from https://python.org  
✅ Check **"Add Python to PATH"** during installation.

### Step 2 — Open project in VS Code
```
File → Open Folder → select the hci_project folder
```

### Step 3 — Create virtual environment
Open VS Code Terminal (`Ctrl + `` ` ``) and run:
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 4 — Install dependencies
```bash
pip install -r requirements.txt
```
> First install may take 2–5 minutes (MediaPipe is large)

### Step 5 — Run the app
```bash
python main.py
```
Or press **F5** in VS Code (launch config is already set up).

---

## 🖐️ Gesture Reference

| Hand Gesture | Action |
|---|---|
| ☝️ Index finger up | Move cursor |
| ✌️ Index + Middle (V sign) | **Left Click** |
| 🤌 Thumb + Index Pinch | **Right Click** |
| 🖐️ All fingers spread | **Scroll mode** (move hand up/down) |
| ✊ Fist | **Freeze / Stop** cursor |

| Eye Action | Action |
|---|---|
| 😉 Blink both eyes | **Left Click** |
| 👁️ Look around | Assists cursor position |

---

## ⚙️ Settings Guide

| Setting | What it does |
|---|---|
| **Smooth Alpha** | Higher = faster but jittery. Lower = smoother but laggy. Start at 0.35 |
| **Hand Weight** | 1.0 = full hand control. 0.0 = full eye control. 0.75 recommended |
| **Click Cooldown** | Minimum time between clicks (avoid accidental double-clicks) |
| **Dwell Click** | Cursor stays still for N seconds → auto-click (great for motor impairments) |
| **Gaze Calibration** | Adjust iris-to-screen mapping if cursor drifts |

---

## 🗂️ Project Structure

```
hci_project/
├── main.py                    ← Entry point
├── requirements.txt
├── src/
│   ├── engine.py              ← Main processing loop (QThread)
│   ├── gesture/
│   │   └── hand_tracker.py   ← MediaPipe hands, gesture classification
│   ├── gaze/
│   │   └── eye_tracker.py    ← Face mesh, iris tracking, blink detection
│   ├── fusion/
│   │   └── cursor_fusion.py  ← Combines hand + eye → final cursor position
│   ├── actions/
│   │   └── dispatcher.py     ← PyAutoGUI mouse/keyboard actions
│   └── utils/
│       ├── camera.py         ← Threaded webcam capture
│       └── smoother.py       ← EMA jitter filter
├── gui/
│   └── main_window.py        ← PyQt6 dark UI
├── config/
│   ├── config_manager.py     ← JSON settings load/save
│   └── user_profiles/        ← Saved user configs
└── .vscode/
    ├── launch.json           ← F5 to run
    └── settings.json
```

---

## 🔧 Troubleshooting

**Camera not found**
- Try changing Camera Index (0, 1, 2) in Settings tab
- Make sure no other app is using the webcam

**Cursor too jittery**
- Lower Smooth Alpha to 0.2–0.25

**Cursor too slow/laggy**
- Raise Smooth Alpha to 0.5–0.6

**Eye gaze cursor drifts**
- Go to Calibration tab and adjust Min/Max X and Y sliders
- Good lighting on your face improves accuracy significantly

**App freezes**
- Move mouse to top-left corner of screen → PyAutoGUI failsafe stops all actions

---

## 📋 Requirements

- Windows 10/11
- Python 3.11
- Webcam (built-in or USB)
- Good lighting on hands and face
