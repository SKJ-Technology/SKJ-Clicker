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

## 📷 Photos

<img width="996" height="979" alt="Zrzut ekranu 2026-05-28 153800" src="https://github.com/user-attachments/assets/1d4b19b1-46d3-4f66-b49c-b652b34612e8" />

Autoclicker Menu in Dark mode

<img width="1001" height="985" alt="Zrzut ekranu 2026-05-28 153809" src="https://github.com/user-attachments/assets/180d2b48-2f2d-40ca-b70c-e6cfb5f55982" />

Autoclicker Menu in White mode

<img width="990" height="977" alt="Zrzut ekranu 2026-05-28 153824" src="https://github.com/user-attachments/assets/16a0a84b-9c21-4fef-aaaa-c801971854d4" />

Macro Menu in Dark mode

<img width="999" height="982" alt="Zrzut ekranu 2026-05-28 153832" src="https://github.com/user-attachments/assets/bf4d2e0b-b567-45e0-beb2-b8d212f5acc1" />

Macro Menu in White mode

<img width="1001" height="977" alt="Zrzut ekranu 2026-05-28 153839" src="https://github.com/user-attachments/assets/2b7769dd-2d08-41d8-8965-ed933d59d290" />

Status Menu in Dark mode

<img width="1001" height="977" alt="Zrzut ekranu 2026-05-28 153839" src="https://github.com/user-attachments/assets/25cba0ea-d37a-454d-914c-2cdc720c0124" />

Status Menu in White Mode

<img width="1000" height="975" alt="Zrzut ekranu 2026-05-28 153849" src="https://github.com/user-attachments/assets/87739363-d506-4754-910d-e9047cf13865" />
 
## 📝 License

This project is licensed under the terms of the **MIT License**.  
You are free to use, modify, and distribute this software, provided that the original copyright notice remains intact.

See the [LICENSE](LICENSE) file for the full legal text.

---
*SKJ Tech © 2026*
