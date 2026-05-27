# SKJ Clicker 🖱️🚀

**SKJ Clicker** is an advanced, high-performance automation suite and macro recorder built entirely in Python. Unlike basic autoclickers, it features a smart macro engine capable of capturing precise mouse paths (including hardware-relative delta movements), keyboard combinations, scroll events, and tracking persistent lifetime statistics.

Developed with ❤️ by **SKJ Tech**

---

## 🌟 Advanced Features

* **Dual Automation Engine:** Toggle seamlessly between rapid-fire mouse clicking (Left/Right) and keyboard key-spamming or holding modes.
* **Intelligent Scroll Capturing:** Records mouse wheel directional inputs with intermediate scroll-wheel division for flawless playback.
* **Smart Countdown System:** Prevent accidental clicks with a configurable startup delay that prepares you before automation kicks in.
* **Persistent Dashboard Stats:** Built-in telemetry that tracks your active uptime, macro executions, and click counts across individual sessions or lifetime usage.
* **Draggable HUD Overlay:** Transparent HUD window displaying real-time state information directly over your active application or game.
* **Dynamic Theme Engine:** Full support for modern, high-contrast Dark Mode and clean Light Mode layouts.

## 🛠️ Built With

* **Python 3.8+** - Core language architecture.
* **Pynput** - Global low-level mouse and keyboard event listening and hardware emulation.
* **Tkinter / TTK** - Structured Graphical User Interface with dynamic coloring.
* **JSON** - Local preference and macro profile persistence (`clicker_settings.json`).

## 🚀 Installation & Setup

### ⚠️ Critical Requirement
Before running the application, you **must** have Python installed on your Windows system, otherwise the executable will close instantly.
1. Download **Python 3.8+** from the official [python.org](https://python.org) website.
2. During setup, make sure to check the box: **"Add Python to PATH"**.

---

### 📥 Getting Started

#### Option 1: Using the Standalone Installer (Recommended for Users)
1. Navigate to the **Releases** tab on the right side of this GitHub repository.
2. Download the latest pre-built `SKJ-Clicker.exe`.
3. Run the executable. It will automatically extract the core assets, install the required packages via your local Python environment, and launch the dashboard.

#### Option 2: Running Directly from Source Code
1. Clone this repository or download the source code zip:
   ```bash
   git clone https://github.com
   cd SKJ-Clicker
   ```
2. Install the necessary input hooks manually:
   ```bash
   pip install -r r.txt
   ```
3. Boot the application:
   ```bash
   python main.py
   ```

## 📝 License

This project is licensed under the terms of the **MIT License**.  
You are free to use, modify, and distribute this software, provided that the original copyright notice remains intact.

See the [LICENSE](LICENSE) file for the full legal text.

---
*SKJ Tech © 2026*
