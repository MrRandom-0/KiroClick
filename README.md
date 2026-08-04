# KiroClick

KiroClick is a small Windows/macOS app that watches the Kiro IDE for a saved image of the **Run** or **Run Task** button and clicks its center. On Windows it captures and clicks Kiro directly in the background, even while another application is active. It scans twice per second by default, requires an 82% OpenCV match, and waits at least 2.5 seconds between clicks.

## Safety behavior

- On Windows, it finds the real `Kiro.exe` window, captures it in the background, and sends the click directly to Kiro without moving your pointer.
- On macOS, visual matching currently requires Kiro to be visible and foreground.
- `Ctrl+Shift+S` on Windows or `Cmd+Shift+S` on macOS toggles Active/Paused.
- Moving the pointer into a primary-screen corner immediately exits the app.
- A compact status window shows whether monitoring is active, what the scanner is doing, and the last click.
- The tray icon is green while active and yellow while paused or missing a template.
- Right-click the tray icon to pause, reload templates, open the templates folder, or quit.

## 1. Install

Use Python 3.10 or newer. Python 3.11 is recommended.

### Windows

```powershell
cd C:\path\to\KiroClick
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run this once in that terminal:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### macOS

```bash
cd /path/to/KiroClick
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On first use, macOS will ask for permissions. Enable the terminal/Python application in **System Settings > Privacy & Security > Accessibility** and **Screen Recording**, then restart it.

## 2. Capture the button template

Image matching works best with a crop made on the same monitor, DPI scaling, and Kiro theme used by the app.

1. In Kiro, reach the state where the **Run** button is visible.
2. From a terminal in this project, run:

   ```powershell
   python capture_template.py --output run_button.png
   ```

3. During the five-second countdown, switch back to Kiro and leave its button visible.
4. A screenshot opens. Drag a **tight rectangle around the entire light button**, including its border but as little surrounding background as possible.
5. Press Enter or Space to save. Press Esc to cancel.
6. If Kiro also displays **Run Task**, repeat with:

   ```powershell
   python capture_template.py --output run_task_button.png
   ```

The images are saved in `templates/`. You can also use any screenshot tool, crop the button tightly, and save a PNG there. Do not crop only the word—include the button background and border. Keep Kiro on the primary monitor for the most dependable cross-platform coordinate behavior.

## 3. Run

With the virtual environment active:

```powershell
python main.py
```

Keep Kiro in the foreground when you expect the button. A small always-on-top window shows **Active/Paused**, scanner status, loaded templates, the last click and confidence, and the session click count. Use **Hide to tray** when you do not need it. If tray integration is unavailable, use:

```powershell
python main.py --no-tray
```

The global hotkey and corner fail-safe still work in console-only mode. After adding or replacing an image while KiroClick is running, choose **Reload button templates** from the tray menu or restart the app.

## Configuration

Edit `config.json` before starting. Useful options:

| Option | Default | Purpose |
|---|---:|---|
| `confidence_threshold` | `0.82` | Minimum normalized match score; raise it if false matches occur. |
| `scan_interval_seconds` | `0.5` | Two captures per second. |
| `cooldown_seconds` | `2.5` | Minimum delay after a click. |
| `require_button_to_disappear` | `true` | Prevents repeat clicks on one persistent button. |
| `monitor_kiro_in_background` | `true` | Windows: detects and clicks Kiro behind another active application. |
| `monitor_active_kiro_window` | `true` | Restricts capture and clicks to foreground Kiro. |
| `toggle_hotkey` | `auto` | Uses the OS shortcut above; accepts pynput syntax such as `<ctrl>+<alt>+k`. |
| `show_status_window` | `true` | Opens the compact status window when the app starts. |
| `window_always_on_top` | `true` | Keeps the compact status window visible above Kiro. |
| `template_scales` | `[0.9, 1.0, 1.1]` | Small scale search to tolerate minor UI scaling changes. |
| `debug` | `false` | Logs every match and foreground-window state. |

On Windows, `monitor_kiro_in_background` takes priority over the foreground-window setting. On macOS, add part of a customized Kiro title to `kiro_window_keywords` if needed.

## Build a standalone Windows app

Install the development requirements, then run the build script:

```powershell
pip install -r requirements-dev.txt
.\build_windows.ps1
```

Outputs:

- `dist\KiroClick\KiroClick.exe` (the unpacked app folder must stay together)
- `dist\KiroClick-Windows.zip`

Put captured PNGs in `dist\KiroClick\templates\` before launching the EXE. Windows may show a SmartScreen warning because a locally built executable is unsigned.

## Build a standalone macOS app

Run the build on the Mac that will use it:

```bash
pip install -r requirements-dev.txt
chmod +x build_macos.sh
./build_macos.sh
```

Put captured PNGs in `dist/KiroClick.app/Contents/MacOS/templates/`. Unsigned local apps may require right-clicking the app and choosing **Open** once. Accessibility and Screen Recording permissions are still required.

## Troubleshooting

- **No clicks:** Confirm the tray status does not say "Needs a button template", Kiro is foreground, and the PNG matches the current Kiro theme/DPI. Turn on `debug` to see confidence scores.
- **False match:** Crop more tightly or raise `confidence_threshold` to `0.88` or `0.92`.
- **Kiro is not recognized:** Add part of its visible window title to `kiro_window_keywords`.
- **macOS captures but cannot click:** Grant Accessibility permission and restart Python/KiroClick.
- **macOS sees a black screenshot:** Grant Screen Recording permission and restart Python/KiroClick.
- **App exits unexpectedly:** The pointer reached a screen corner, intentionally triggering the fail-safe.

Only automate prompts you have reviewed and trust: clicking **Run** can execute commands or modify files in the active Kiro workspace.
