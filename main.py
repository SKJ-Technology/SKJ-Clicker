import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import threading
import time
from pynput.mouse import Button, Controller as MouseController, Listener as MouseListener
from pynput.keyboard import Listener, KeyCode, Controller as KeyboardController, Key
import json
import os
import sys
import random

# --- Configuration Constants ---
INITIAL_DELAY = 0.00
MAX_MACRO_LOOPS = 9999999
SCROLL_WHEEL_DIVISOR = 2
MACRO_PLAYBACK_SPEED = 1.0  # Speed multiplier for playback
SETTINGS_FILE = "clicker_settings.json"

# Theme colors as constants
THEME_COLORS = {
    'DARK': {
        'bg': '#0f0f0f',
        'fg': '#ffffff',
        'button_bg': '#2b2b2b',
        'button_fg': '#ffffff',
        'frame_bg': '#1a1a1a',
        'text_bg': '#202020',
        'text_fg': '#ffffff',
        'accent': '#0078d4',
        'accent_light': '#003e5c',
        'success': '#2ecc71',
        'warning': '#ffb900',
        'error': '#e74c3c',
        'disabled_fg': '#555555'
    },
    'LIGHT': {
        'bg': '#fafafa',
        'fg': '#1c1c1c',
        'button_bg': '#f2f2f2',
        'button_fg': '#000000',
        'frame_bg': '#ffffff',
        'text_bg': '#f9f9f9',
        'text_fg': '#000000',
        'accent': '#0078d4',
        'accent_light': '#d0e7ff',
        'success': '#10893e',
        'warning': '#ffb900',
        'error': '#c42b1c',
        'disabled_fg': '#808080'
    }
}

# --- Global State ---
mouse = MouseController()
keyboard = KeyboardController()
running = False
click_delay = INITIAL_DELAY
click_button = Button.left
target_key = KeyCode(char='a')
is_recording_key = False
is_recording_toggle_key = False
click_thread = None
TOGGLE_KEY = KeyCode(char='w')
MACRO_TOGGLE_KEY = KeyCode(char='p')
macro_playback_speed = MACRO_PLAYBACK_SPEED
last_macro_pos = None
KILL_KEY = Key.esc
is_recording_kill_key = False
macro_storage = {}
current_macro_name = "Macro_1"
is_recording_macro = False
is_macro_paused = False
is_macro_countdown_active = False # New flag for macro countdown state
is_clicker_countdown_active = False # New flag for clicker countdown state
is_playing_macro = False
macro_start_time = None
macro_playback_thread = None
mouse_listener = None
keyboard_macro_listener = None
held_keys = {}
MACRO_REC_KEY = KeyCode(char='r')
is_recording_macro_play_key = False
is_recording_macro_rec_key = False
clicker_countdown_job = None
macro_countdown_job = None

# --- HUD State ---
hud_window = None
hud_label = None
macro_current_loop = 0
macro_total_loops = 0

# --- Statistics State ---
session_stats = {
    'clicks': 0,
    'keys': 0,
    'macros': 0,
    'macro_events': 0,
    'start_time': time.time(),
    'active_seconds': 0
}

# --- Settings (Persistence) ---
user_preferences = {
    'dark_mode': True,
    'delay': INITIAL_DELAY,
    'macro_loop': False,
    'playback_speed': MACRO_PLAYBACK_SPEED,
    'toggle_key': 'w',
    'target_key': 'a',
    'show_hud': True,
    'use_countdown': True,
    'kill_key': 'key:esc',
    'macro_toggle_key': 'p',
    'macro_rec_key': 'r',
    'macro_loops': 1,
    'macro_infinite': False,
    'start_delay': 3,
    'humanizer_enabled': False,
    'stat_lifetime_clicks': 0,
    'stat_lifetime_keys': 0,
    'stat_lifetime_macros': 0,
    'stat_lifetime_active_seconds': 0,
    'show_stats_tab': True
}

# --- Settings Management ---

def save_user_preferences():
    """Save user preferences to file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(user_preferences, f, indent=2)
        print(f"[SETTINGS] Saved preferences to {SETTINGS_FILE}")
    except Exception as e:
        print(f"[SETTINGS ERROR] Failed to save preferences: {str(e)}")


def load_user_preferences():
    """Load user preferences from file."""
    global user_preferences, click_delay, macro_playback_speed
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
                user_preferences.update(saved)
            
            # Update globals from preferences
            global TOGGLE_KEY, target_key, MACRO_TOGGLE_KEY, MACRO_REC_KEY, KILL_KEY
            TOGGLE_KEY = deserialize_key(user_preferences.get('toggle_key', 'w'))
            target_key = deserialize_key(user_preferences.get('target_key', 'a'))
            MACRO_TOGGLE_KEY = deserialize_key(user_preferences.get('macro_toggle_key', 'p'))
            MACRO_REC_KEY = deserialize_key(user_preferences.get('macro_rec_key', 'r'))
            KILL_KEY = deserialize_key(user_preferences.get('kill_key', 'key:esc'))
            click_delay = user_preferences.get('delay', INITIAL_DELAY)
            macro_playback_speed = user_preferences.get('playback_speed', MACRO_PLAYBACK_SPEED)
            print(f"[SETTINGS] Loaded preferences from {SETTINGS_FILE}")
            return True
    except Exception as e:
        print(f"[SETTINGS ERROR] Failed to load preferences: {str(e)}")
    return False


# --- Helper Functions for Key Serialization ---

def serialize_key(key):
    """Convert a key object to a serializable string."""
    try:
        if hasattr(key, 'char') and key.char is not None:
            return f"char:{key.char}"
        elif isinstance(key, Key):
            return f"key:{key.name}"
        else:
            return f"key:{str(key).split('.')[-1]}"
    except Exception as e:
        print(f"[SERIALIZE ERROR] {str(e)}")
        return f"unknown:{str(key)}"


def deserialize_key(key_str):
    """Convert a serialized key string back to a key object."""
    try:
        if not isinstance(key_str, str):
            return key_str
        
        if key_str.startswith("char:"):
            return KeyCode(char=key_str[5:])
        elif key_str.startswith("key:"):
            key_name = key_str[4:]
            key_map = {
                'space': Key.space, 'enter': Key.enter, 'shift': Key.shift,
                'ctrl': Key.ctrl, 'alt': Key.alt, 'tab': Key.tab,
                'backspace': Key.backspace, 'delete': Key.delete, 'esc': Key.esc
            }
            if key_name in key_map:
                return key_map[key_name]
            try:
                return getattr(Key, key_name)
            except AttributeError:
                print(f"[DESERIALIZE] Unknown key: {key_name}, defaulting to 'a'")
                return KeyCode(char='a')
        return key_str
    except Exception as e:
        print(f"[DESERIALIZE ERROR] {str(e)}")
        return KeyCode(char='a')


def get_key_display_name(key):
    """Get a human-readable name for a key."""
    try:
        if hasattr(key, 'char') and key.char is not None:
            return 'SPACE' if key.char == ' ' else key.char.upper()
        elif isinstance(key, Key):
            name_map = {
                'space': 'SPACE', 'enter': 'ENTER', 'shift': 'SHIFT',
                'ctrl': 'CTRL', 'alt': 'ALT', 'tab': 'TAB',
                'backspace': 'BACKSPACE', 'delete': 'DELETE', 'esc': 'ESC'
            }
            return name_map.get(key.name, key.name.upper())
        else:
            return str(key).split('.')[-1].upper()
    except Exception as e:
        print(f"[KEY DISPLAY ERROR] {str(e)}")
        return 'UNKNOWN'


# --- Core Click Logic Functions ---

def click_loop(is_hold, is_kb, btn, target, delay):
    """Main click loop handling hold mode and spam mode for both mouse and keyboard."""
    global running

    try:
        if is_hold:
            # HOLD MODE
            target_name = ""
            if is_kb:
                keyboard.press(target)
                target_name = f"Key: {get_key_display_name(target)}"
                increment_stat('keys')
            else:
                mouse.press(btn)
                target_name = f"Button: {'LEFT' if btn == Button.left else 'RIGHT'}"
                increment_stat('clicks')

            print(f"Holding {target_name}")
            
            while running:
                time.sleep(0.001)

            if is_kb:
                keyboard.release(target)
            else:
                mouse.release(btn)

            print("Released input.")

        else:
            # SPAM/REPEATED PRESS MODE
            while running:
                if is_kb:
                    keyboard.press(target)
                    keyboard.release(target)
                    increment_stat('keys')
                else:
                    mouse.click(btn, 1)
                    increment_stat('clicks')
                
                stop_time = time.time() + delay
                while running and time.time() < stop_time:
                    pass

    except Exception as e:
        print(f"[CLICK LOOP ERROR] {str(e)}")
    finally:
        update_status("Status: INACTIVE", "red")


def toggle_clicker_state(ignore_countdown=False):
    """Toggle the running state with proper race condition prevention."""
    global running, click_thread, is_clicker_countdown_active, clicker_countdown_job

    if is_recording_macro:
        update_status("Status: Cannot toggle clicker while recording macro.", "orange")
        print("Auto-Clicker: Cannot toggle while recording macro")
        return
    
    if is_playing_macro:
        update_status("Status: Cannot toggle clicker while playing macro.", "orange")
        print("Auto-Clicker: Cannot toggle while playing macro")
        return

    if is_clicker_countdown_active: # If a countdown is active, pressing toggle key cancels it
        if clicker_countdown_job:
            root.after_cancel(clicker_countdown_job)
            clicker_countdown_job = None
        is_clicker_countdown_active = False # Signal to stop countdown
        update_status("Status: Clicker start cancelled.", "blue")
        start_stop_button.config(text="▶️  START CLICKER", bg=current_colors['accent'], fg='white')
        print("Auto-Clicker: Countdown cancelled.")
        return

    if running:
        running = False
        start_stop_button.config(text="▶️  START CLICKER", bg=current_colors['accent'], fg='white')
        print("Auto-Clicker: INACTIVE")
        update_status("Status: INACTIVE", "red") # Explicitly update status here

    else:
        start_delay = int(user_preferences.get('start_delay', 0))
        if use_countdown_var.get() and start_delay > 0 and not ignore_countdown:
            is_clicker_countdown_active = True
            def perform_countdown(remaining):
                global running, clicker_countdown_job, is_clicker_countdown_active
                if not is_clicker_countdown_active: # Check the new flag for cancellation
                    update_status("Status: INACTIVE", "red")
                    start_stop_button.config(text="▶️  START CLICKER", bg=current_colors['accent'], fg='white')
                    return
                if remaining > 0:
                    update_status(f"Status: STARTING IN {remaining}s...", "orange")
                    clicker_countdown_job = root.after(1000, lambda: perform_countdown(remaining - 1))
                else:
                    is_clicker_countdown_active = False # Countdown finished
                    clicker_countdown_job = None
                    toggle_clicker_state(ignore_countdown=True)
            
            start_stop_button.config(text="⏹️  CANCEL START", bg='#ffb900', fg='black')
            clicker_countdown_job = root.after(0, lambda: perform_countdown(start_delay))
            return

        running = True

        if not (click_thread and click_thread.is_alive()):
            click_thread = threading.Thread(
                target=click_loop, 
                args=(is_hold_mode.get(), is_keyboard_mode.get(), click_button, target_key, click_delay),
                daemon=True
            )
            click_thread.start()

        start_stop_button.config(text="⏹️  STOP CLICKER", bg='#c50f1f', fg='white', state='normal')
        
        mode_type = "HOLDING" if is_hold_mode.get() else "PRESSING"
        
        if is_keyboard_mode.get():
            display_key = get_key_display_name(target_key)
            status_message = f"Status: ACTIVE ({mode_type} Key: {display_key}, Delay: {click_delay:.3f}s)"
            print(f"Auto-Key-{mode_type}: ACTIVE, Key: {display_key}")
        else:
            button_name = "LEFT" if click_button == Button.left else "RIGHT"
            status_message = f"Status: ACTIVE ({mode_type} Button: {button_name}, Delay: {click_delay:.3f}s)"
            print(f"Auto-Clicker-{mode_type}: ACTIVE, Button: {button_name}")
            
        update_status(status_message, "green")


def on_key_press_listener(key):
    """Global keyboard listener with proper exception handling."""
    global is_recording_key, target_key, TOGGLE_KEY, is_recording_toggle_key
    global MACRO_TOGGLE_KEY, is_recording_macro_play_key, MACRO_REC_KEY, is_recording_macro_rec_key
    global KILL_KEY, is_recording_kill_key

    try:
        if key == KILL_KEY and not is_recording_kill_key:
            emergency_kill()
            return

        # Recording toggle key takes priority
        if is_recording_toggle_key:
            TOGGLE_KEY = key
            display_key = get_key_display_name(key)
            user_preferences['toggle_key'] = serialize_key(key)
            is_recording_toggle_key = False
            root.after(0, lambda k=display_key: [
                toggle_key_label.config(text=f"Toggle Key: {k}"),
                toggle_key_display.config(text=k),
                toggle_key_info_label.config(text=f"Keyboard Toggle Key: Press '{k}' to toggle."),
                record_toggle_key_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white'),
                update_status("Status: Toggle Key Recorded. Ready to Start.", "blue")
            ])
            print(f"Toggle key recorded: {display_key}")
            return

        # Kill Key recording
        if is_recording_kill_key:
            KILL_KEY = key
            display_key = get_key_display_name(key)
            user_preferences['kill_key'] = serialize_key(key)
            is_recording_kill_key = False
            root.after(0, lambda k=display_key: [
                kill_key_display.config(text=k),
                record_kill_key_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white'),
                update_status("Status: Kill Key Recorded.", "blue")
            ])
            return

        # Macro Playback Key recording
        if is_recording_macro_play_key:
            MACRO_TOGGLE_KEY = key
            display_key = get_key_display_name(key)
            user_preferences['macro_toggle_key'] = serialize_key(key)
            is_recording_macro_play_key = False
            root.after(0, lambda k=display_key: [
                macro_play_key_display.config(text=k),
                record_macro_play_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white'),
                update_status("Status: Macro Play Key Recorded.", "blue")
            ])
            print(f"Macro Play key recorded: {display_key}")
            return

        # Macro Record Key recording
        if is_recording_macro_rec_key:
            MACRO_REC_KEY = key
            display_key = get_key_display_name(key)
            user_preferences['macro_rec_key'] = serialize_key(key)
            is_recording_macro_rec_key = False
            root.after(0, lambda k=display_key: [
                macro_rec_key_display.config(text=k),
                record_macro_rec_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white'),
                update_status("Status: Macro Record Key Recorded.", "blue")
            ])
            print(f"Macro Record key recorded: {display_key}")
            return

        if key == TOGGLE_KEY:
            if not (is_recording_macro or is_playing_macro):
                root.after(0, toggle_clicker_state)
            return

        if key == MACRO_TOGGLE_KEY:
            if not is_recording_macro:
                root.after(0, lambda: stop_macro_playback() if is_playing_macro else playback_macro_sequence())
            return

        if key == MACRO_REC_KEY:
            if not is_playing_macro:
                root.after(0, toggle_macro_recording)
            return

        if is_recording_key:
            target_key = key
            display_key = get_key_display_name(key)
            user_preferences['target_key'] = serialize_key(key)
            is_recording_key = False
            root.after(0, lambda k=display_key: [
                key_label.config(text=f"Target Key: {k}"),
                key_display.config(text=k),
                record_key_button.config(text="🎹 Set Key", bg=current_colors['accent'], fg='white'),
                update_status("Status: Key Recorded. Ready to Start.", "blue")
            ])
            print(f"Target key recorded: {display_key}")
            return

    except Exception as e:
        print(f"[KEY LISTENER ERROR] {str(e)}")


# Start global keyboard listener with exception handling
try:
    keyboard_listener = Listener(on_press=on_key_press_listener)
    keyboard_listener.daemon = True
    keyboard_listener.start()
except Exception as e:
    print(f"[ERROR] Failed to start keyboard listener: {str(e)}")
    keyboard_listener = None


# --- GUI Update Functions ---

def update_delay():
    """Update click delay with validation."""
    global click_delay
    try:
        new_delay = float(delay_entry.get())
        if new_delay >= 0:
            click_delay = new_delay
            user_preferences['delay'] = click_delay
            delay_label.config(text=f"Current Delay (s): {click_delay:.3f}")
            print(f"Delay updated to {click_delay} seconds.")
        else:
            update_status("Status: Delay cannot be negative.", "orange")
    except ValueError:
        update_status("Status: Invalid number for delay.", "orange")


def update_playback_speed():
    """Update macro playback speed multiplier."""
    global macro_playback_speed
    try:
        new_speed = float(speed_entry.get())
        if 0.1 <= new_speed <= 10.0:
            macro_playback_speed = new_speed
            user_preferences['playback_speed'] = macro_playback_speed
            speed_label.config(text=f"Playback Speed: {macro_playback_speed:.2f}x")
            print(f"Playback speed updated to {macro_playback_speed}x")
        else:
            update_status("Status: Speed must be between 0.1x and 10.0x", "orange")
    except ValueError:
        update_status("Status: Invalid number for speed.", "orange")


def update_start_delay():
    """Update the countdown delay before automation starts."""
    try:
        entry_val = start_delay_entry.get().strip()
        if entry_val:
            val = int(entry_val)
            user_preferences['start_delay'] = max(0, val)
            print(f"[SETTINGS] Start delay set to {user_preferences['start_delay']}s")
        else:
            user_preferences['start_delay'] = 0
    except ValueError:
        update_status("Status: Start delay must be a number.", "orange")


def update_button_type(*args):
    """Update mouse button type with proper restarts."""
    global click_button
    selection = button_var.get()
    click_button = Button.left if selection == "Left Click" else Button.right

    if running and not is_keyboard_mode.get():
        # Stop the clicker first
        toggle_clicker_state() 

        # Restart with a tiny delay to allow the previous thread to exit properly
        # This ensures the 'is_alive()' check in toggle_clicker_state doesn't block the restart
        root.after(200, lambda: toggle_clicker_state(ignore_countdown=True))

    print(f"Click button set to: {selection}")


def set_recording_state():
    """Toggle keyboard key recording state."""
    global is_recording_key
    
    if is_recording_key:
        is_recording_key = False
        record_key_button.config(text="🎹 Set Key", bg=current_colors['accent'], fg='white')
        update_status("Status: Key recording cancelled.", "blue")
    else:
        is_recording_key = True
        record_key_button.config(text="⏸️  LISTENING...", bg='#c50f1f', fg='white')
        update_status("Status: Press the key you want to auto-press now.", "orange")


def set_toggle_key_recording_state():
    """Toggle toggle key recording state."""
    global is_recording_toggle_key
    
    if is_recording_toggle_key:
        is_recording_toggle_key = False
        record_toggle_key_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white')
        update_status("Status: Toggle key recording cancelled.", "blue")
    else:
        is_recording_toggle_key = True
        record_toggle_key_button.config(text="⏸️  LISTENING...", bg='#c50f1f', fg='white')
        update_status("Status: Press the key you want to use as toggle.", "orange")


def set_macro_play_key_recording_state():
    """Toggle macro play key recording state."""
    global is_recording_macro_play_key
    if is_recording_macro_play_key:
        is_recording_macro_play_key = False
        record_macro_play_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white')
        update_status("Status: Playback key recording cancelled.", "blue")
    else:
        is_recording_macro_play_key = True
        record_macro_play_button.config(text="⏸️  LISTENING...", bg='#c50f1f', fg='white')
        update_status("Status: Press the key you want to use for Macro Play/Stop.", "orange")


def set_macro_rec_key_recording_state():
    """Toggle macro record key recording state."""
    global is_recording_macro_rec_key
    if is_recording_macro_rec_key:
        is_recording_macro_rec_key = False
        record_macro_rec_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white')
        update_status("Status: Recording key recording cancelled.", "blue")
    else:
        is_recording_macro_rec_key = True
        record_macro_rec_button.config(text="⏸️  LISTENING...", bg='#c50f1f', fg='white')
        update_status("Status: Press the key you want to use for Macro Record/Stop.", "orange")


def set_kill_key_recording_state():
    """Toggle kill key recording state."""
    global is_recording_kill_key
    if is_recording_kill_key:
        is_recording_kill_key = False
        record_kill_key_button.config(text="🔄 Change", bg=current_colors['accent'], fg='white')
        update_status("Status: Kill key recording cancelled.", "blue")
    else:
        is_recording_kill_key = True
        record_kill_key_button.config(text="⏸️  LISTENING...", bg='#c50f1f', fg='white')
        update_status("Status: Press the key you want to use for Emergency Kill.", "orange")


def update_mode_status():
    """Update status when mode changes."""
    if running:
        toggle_clicker_state()  # stop first
        # Restart after the click thread has had time to exit cleanly
        root.after(250, lambda: toggle_clicker_state(ignore_countdown=True))
    else:
        mode_text = "Keyboard Mode Selected" if is_keyboard_mode.get() else "Mouse Mode Selected"
        hold_text = " (HOLD Mode)" if is_hold_mode.get() else ""
        update_status(f"Status: {mode_text}{hold_text}. Ready to Start.", "blue")


def update_status(message, color):
    """Updates the status label safely from any thread."""
    def _update():
        color_map = {
            'red': current_colors['error'],
            'green': current_colors['success'],
            'blue': current_colors['accent'],
            'orange': current_colors['warning']
        }
        actual_color = color_map.get(color, color)
        status_label.config(text=message, foreground=actual_color)
        update_hud()
    
    # Schedule the update on the main thread
    root.after(0, _update)

def update_hud():
    """Updates the HUD overlay window with current state information."""
    global hud_window, hud_label
    
    if not show_hud_var.get():
        if hud_window:
            hud_window.destroy()
            hud_window = None
        return

    if not hud_window or not hud_window.winfo_exists():
        hud_window = tk.Toplevel(root)
        hud_window.overrideredirect(True)
        hud_window.attributes("-topmost", True)
        hud_window.attributes("-alpha", 0.7)
        hud_window.configure(bg='black')
        
        hud_label = tk.Label(
            hud_window, text="", fg='white', bg='black', 
            font=('Consolas', 11, 'bold'), padx=10, pady=5
        )
        hud_label.pack()
        hud_window.geometry("+20+20")
        
        # Dragging logic for HUD
        def start_move(event): hud_window.x, hud_window.y = event.x, event.y
        def on_motion(event):
            x = hud_window.winfo_x() + (event.x - hud_window.x)
            y = hud_window.winfo_y() + (event.y - hud_window.y)
            hud_window.geometry(f"+{x}+{y}")
        hud_window.bind("<Button-1>", start_move)
        hud_window.bind("<B1-Motion>", on_motion)

    if running:
        text, color = f"CLICKER: ACTIVE ({'KB' if is_keyboard_mode.get() else 'MOUSE'})", "lime"
    elif is_recording_macro:
        text, color = f"RECORDING: {current_macro_name}", "red"
    elif is_playing_macro:
        loop_info = "∞" if macro_infinite_var.get() else f"{macro_current_loop}/{macro_total_loops}"
        text, color = f"PLAYING: {current_macro_name} ({loop_info})", "cyan"
    elif is_clicker_countdown_active or is_macro_countdown_active:
        text, color = "STARTING...", "orange"
    else:
        text, color = "CLICKER: INACTIVE", "white"
    
    hud_label.config(text=text, fg=color)

def increment_stat(stat_type):
    """Helper to increment session and lifetime statistics."""
    # Privacy Check: Do not count anything if the stats dashboard is disabled
    if not user_preferences.get('show_stats_tab', True):
        return
        
    if stat_type == 'clicks':
        session_stats['clicks'] += 1
        user_preferences['stat_lifetime_clicks'] += 1
    elif stat_type == 'keys':
        session_stats['keys'] += 1
        user_preferences['stat_lifetime_keys'] += 1
    elif stat_type == 'macros':
        session_stats['macros'] += 1
        user_preferences['stat_lifetime_macros'] += 1
    elif stat_type == 'macro_events':
        session_stats['macro_events'] += 1

def format_time(seconds):
    """Format seconds into a human-readable string."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    elif mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"

def update_stats_dashboard():
    """Refreshes the statistics labels in the UI."""
    if not stats_tab_active:
        return

    try:
        # Session Labels
        s_clicks_val.config(text=str(session_stats['clicks']))
        s_keys_val.config(text=str(session_stats['keys']))
        s_macros_val.config(text=str(session_stats['macros']))
        s_uptime_val.config(text=format_time(session_stats['active_seconds']))

        # Lifetime Labels
        l_clicks_val.config(text=str(user_preferences['stat_lifetime_clicks']))
        l_keys_val.config(text=str(user_preferences['stat_lifetime_keys']))
        l_macros_val.config(text=str(user_preferences['stat_lifetime_macros']))
        l_uptime_val.config(text=format_time(user_preferences['stat_lifetime_active_seconds']))
    except Exception:
        pass

    # Update every second
    root.after(1000, update_stats_dashboard)

def reset_session_stats():
    """Reset only the current session's counters."""
    session_stats['clicks'] = 0
    session_stats['keys'] = 0
    session_stats['macros'] = 0
    session_stats['macro_events'] = 0
    session_stats['active_seconds'] = 0
    session_stats['start_time'] = time.time()
    update_status("Status: Session statistics reset.", "blue")

def reset_lifetime_stats():
    """Prompt to reset lifetime statistics."""
    if messagebox.askyesno("Reset Lifetime Stats", "Are you sure you want to permanently clear all lifetime statistics?"):
        user_preferences['stat_lifetime_clicks'] = 0
        user_preferences['stat_lifetime_keys'] = 0
        user_preferences['stat_lifetime_macros'] = 0
        user_preferences['stat_lifetime_active_seconds'] = 0
        update_status("Status: Lifetime statistics cleared.", "orange")

stats_tab_active = False
def on_tab_changed(event):
    """Trigger dashboard update when the stats tab is selected."""
    global stats_tab_active
    selected_tab = notebook.index(notebook.select())
    # Now merged into Status tab (index 2)
    if selected_tab == 2:
        stats_tab_active = True
        update_stats_dashboard()
    else:
        stats_tab_active = False

# --- Macro Recording Functions ---

def on_mouse_click_macro(x, y, button, pressed):
    """Capture mouse clicks during macro recording."""
    global is_recording_macro, macro_start_time, current_macro_name
    
    if not is_recording_macro:
        return
    
    try:
        elapsed_time = time.time() - macro_start_time
        button_name = "left" if button == Button.left else "right" if button == Button.right else "middle"
        action = "mouse_down" if pressed else "mouse_up"
        
        macro_storage[current_macro_name]["events"].append({
            "timestamp": elapsed_time,
            "action": action,
            "button": button_name,
            "x": x,
            "y": y
        })
        print(f"[MACRO] {action}: {button_name} at ({x}, {y})")
    except Exception as e:
        print(f"[MACRO CLICK ERROR] {str(e)}")


def on_mouse_move_macro(x, y):
    """Capture mouse movements with throttling."""
    global is_recording_macro, macro_start_time, current_macro_name, last_macro_pos

    if not is_recording_macro:
        return
    
    try:
        elapsed_time = time.time() - macro_start_time
        events = macro_storage[current_macro_name]["events"]

        # Calculate deltas for game compatibility (e.g., Minecraft camera)
        dx, dy = 0, 0
        if last_macro_pos is not None:
            dx = x - last_macro_pos[0]
            dy = y - last_macro_pos[1]
        
        last_macro_pos = (x, y)
        
        if events and events[-1].get("action") == "mouse_move":
            if elapsed_time - events[-1]["timestamp"] < 0.05:
                return
        
        macro_storage[current_macro_name]["events"].append({
            "timestamp": elapsed_time,
            "action": "mouse_move",
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy
        })
        print(f"[MACRO] mouse_move: ({x}, {y})")
    except Exception as e:
        print(f"[MACRO MOVE ERROR] {str(e)}")


def on_scroll_macro(x, y, dx, dy):
    """Capture scroll wheel with intermediate button handling."""
    global is_recording_macro, macro_start_time, current_macro_name
    
    if not is_recording_macro:
        return
    
    try:
        elapsed_time = time.time() - macro_start_time
        if abs(dx) > abs(dy):
            direction = "right" if dx > 0 else "left"
            amount = max(1, round(abs(dx) / SCROLL_WHEEL_DIVISOR))
        else:
            direction = "up" if dy > 0 else "down"
            amount = max(1, round(abs(dy) / SCROLL_WHEEL_DIVISOR))
        
        macro_storage[current_macro_name]["events"].append({
            "timestamp": elapsed_time,
            "action": "scroll",
            "direction": direction,
            "amount": max(1, amount)
        })
        print(f"[MACRO] scroll: {direction} ({amount} units)")
    except Exception as e:
        print(f"[MACRO SCROLL ERROR] {str(e)}")


def on_key_press_macro(key):
    """Capture key press events."""
    global is_recording_macro, macro_start_time, held_keys, MACRO_REC_KEY
    
    # Don't record the key used to stop the recording
    if not is_recording_macro or key == MACRO_REC_KEY:
        return
    
    try:
        elapsed_time = time.time() - macro_start_time
        key_str = serialize_key(key)
        held_keys[key_str] = elapsed_time
        
        macro_storage[current_macro_name]["events"].append({
            "timestamp": elapsed_time,
            "action": "key_down",
            "key": key_str
        })
        display_name = get_key_display_name(key)
        print(f"[MACRO] key_down: {display_name}")
    except Exception as e:
        print(f"[MACRO KEY DOWN ERROR] {str(e)}")


def on_key_release_macro(key):
    """Capture key release events with hold duration."""
    global is_recording_macro, macro_start_time, held_keys, MACRO_REC_KEY
    
    # Don't record the key used to stop the recording
    if not is_recording_macro or key == MACRO_REC_KEY:
        return
    
    try:
        elapsed_time = time.time() - macro_start_time
        key_str = serialize_key(key)
        press_time = held_keys.get(key_str, elapsed_time)
        hold_duration = elapsed_time - press_time
        held_keys.pop(key_str, None)
        
        macro_storage[current_macro_name]["events"].append({
            "timestamp": elapsed_time,
            "action": "key_up",
            "key": key_str,
            "hold_duration": hold_duration
        })
        display_name = get_key_display_name(key)
        print(f"[MACRO] key_up: {display_name} (held {hold_duration:.3f}s)")
    except Exception as e:
        print(f"[MACRO KEY UP ERROR] {str(e)}")


def start_macro_recording():
    """Start recording a macro with validation."""
    global is_recording_macro, macro_start_time, mouse_listener, keyboard_macro_listener, current_macro_name, held_keys, last_macro_pos

    if is_recording_macro:
        return
        
    last_macro_pos = mouse.position
    
    if running:
        update_status("Status: Cannot record macro while clicker is running. Stop the clicker first.", "orange")
        print("Macro recording: Cannot start while clicker is running")
        return
    
    macro_name = macro_name_entry.get().strip()
    if not macro_name:
        update_status("Status: Please enter a macro name.", "orange")
        return
    
    if macro_name in macro_storage:
        update_status(f"Status: Macro '{macro_name}' already exists. Use a different name.", "orange")
        print(f"Macro recording: Duplicate macro name '{macro_name}'")
        return
    
    current_macro_name = macro_name
    is_recording_macro = True
    macro_start_time = time.time()
    held_keys = {}
    
    macro_storage[macro_name] = {
        "events": [],
        "created": time.time(),
        "hardware_macro_key": None
    }
    
    try:
        mouse_listener = MouseListener(
            on_click=on_mouse_click_macro, 
            on_move=on_mouse_move_macro,
            on_scroll=on_scroll_macro
        )
        mouse_listener.start()
    except Exception as e:
        print(f"[MACRO] Error starting mouse listener: {str(e)}")
        update_status("Status: Error starting mouse listener.", "red")
        is_recording_macro = False
        return
    
    try:
        keyboard_macro_listener = Listener(
            on_press=on_key_press_macro,
            on_release=on_key_release_macro
        )
        keyboard_macro_listener.start()
    except Exception as e:
        print(f"[MACRO] Error starting keyboard listener: {str(e)}")
        update_status("Status: Error starting keyboard listener.", "red")
        is_recording_macro = False
        if mouse_listener:
            try:
                mouse_listener.stop()
            except:
                pass
        return
    
    record_macro_button.config(text="⏹️  Stop", bg='#c50f1f', fg='white')
    start_stop_button.config(state='disabled')
    update_status(f"Status: Recording macro '{macro_name}'. All inputs are captured...", "orange")
    print(f"[MACRO] Started recording: {macro_name}")


def stop_macro_recording():
    """Stop recording with proper cleanup."""
    global is_recording_macro, mouse_listener, keyboard_macro_listener, held_keys
    
    if not is_recording_macro:
        return
    
    is_recording_macro = False
    held_keys = {}
    
    if mouse_listener:
        try:
            mouse_listener.stop()
        except Exception as e:
            print(f"[CLEANUP] Error stopping mouse listener: {str(e)}")
        finally:
            mouse_listener = None
    
    if keyboard_macro_listener:
        try:
            keyboard_macro_listener.stop()
        except Exception as e:
            print(f"[CLEANUP] Error stopping keyboard listener: {str(e)}")
        finally:
            keyboard_macro_listener = None
    
    num_events = len(macro_storage.get(current_macro_name, {}).get("events", []))
    record_macro_button.config(text="⏺️  Start", bg=current_colors['accent'], fg='white')
    start_stop_button.config(state='normal')
    update_status(f"Status: Macro recorded with {num_events} events.", "blue")
    update_macro_list()
    print(f"[MACRO] Stopped recording: {num_events} events captured")


def toggle_macro_recording():
    """Toggle macro recording on/off."""
    global is_recording_macro
    
    if is_recording_macro:
        stop_macro_recording()
    else:
        start_macro_recording()


# --- Macro Playback Functions ---

def playback_macro_sequence(ignore_countdown=False):
    """Start macro playback with proper validation."""
    global is_playing_macro, macro_playback_thread, is_macro_countdown_active, macro_countdown_job
    
    if is_playing_macro:
        return
    
    if running:
        update_status("Status: Cannot play macro while clicker is running. Stop the clicker first.", "orange")
        print("Macro playback: Cannot start while clicker is running")
        return
    
    if is_macro_countdown_active: # If a macro countdown is active, pressing toggle key cancels it
        if macro_countdown_job:
            root.after_cancel(macro_countdown_job)
            macro_countdown_job = None
        is_macro_countdown_active = False
        update_status("Status: Macro playback cancelled.", "blue")
        play_macro_button.config(state='normal')
        stop_macro_button.config(state='disabled', text="⏹️  Stop") # Reset text
        start_stop_button.config(state='normal')
        print("Macro playback: Countdown cancelled.")
        return

    selected_index = macro_list_var.curselection()
    if not selected_index:
        update_status("Status: Please select a macro to play.", "orange")
        return
    
    list_entry = macro_list_var.get(selected_index[0])
    macro_name = list_entry.rsplit(' (', 1)[0]

    macro_data = macro_storage.get(macro_name)
    if not macro_data or not macro_data.get("events"):
        update_status("Status: Selected macro is empty.", "orange")
        return

    try:
        loop_target = int(macro_loops_entry.get())
        infinite = macro_infinite_var.get()
        speed = float(speed_entry.get())
        jitter_val = jitter_entry.get().strip()
        jitter = (float(jitter_val) / 1000.0) if (humanizer_enabled_var.get() and jitter_val) else 0.0
        start_delay = int(user_preferences.get('start_delay', 0))
    except ValueError:
        update_status("Status: Invalid playback settings (Loops/Speed).", "orange")
        return

    if use_countdown_var.get() and start_delay > 0 and not ignore_countdown:
        is_macro_countdown_active = True
        def perform_macro_countdown(remaining):
            global is_playing_macro, macro_countdown_job, is_macro_countdown_active
            if not is_macro_countdown_active: # Check the new flag for cancellation
                update_status("Status: Macro playback cancelled.", "blue")
                play_macro_button.config(state='normal')
                stop_macro_button.config(state='disabled')
                start_stop_button.config(state='normal')
                return
            if remaining > 0:
                update_status(f"Status: PLAYING IN {remaining}s...", "orange")
                macro_countdown_job = root.after(1000, lambda: perform_macro_countdown(remaining - 1))
            else: # Countdown finished
                is_macro_countdown_active = False
                macro_countdown_job = None
                playback_macro_sequence(ignore_countdown=True)
        
        play_macro_button.config(state='disabled')
        stop_macro_button.config(state='normal', text="⏹️  CANCEL")
        macro_countdown_job = root.after(0, lambda: perform_macro_countdown(start_delay))
        return

    is_playing_macro = True
    stop_macro_button.config(text="⏹️  Stop")
    macro_playback_thread = threading.Thread(
        target=_playback_worker,
        args=(macro_name, loop_target, infinite, speed, jitter),
        daemon=True
    )
    macro_playback_thread.start()
    
    root.after(0, lambda: [play_macro_button.config(state='disabled'), pause_macro_button.config(state='normal'), 
                          stop_macro_button.config(state='normal'), start_stop_button.config(state='disabled')])


def _playback_worker(macro_name, loop_target, infinite, speed, jitter):
    global is_playing_macro, macro_current_loop, macro_total_loops, current_macro_name, is_macro_paused
    macro_total_loops = loop_target
    current_macro_name = macro_name
    is_macro_paused = False
    try:
        if macro_name not in macro_storage:
            return
        events = list(macro_storage[macro_name]["events"]) # Copy to prevent external modification issues
        current_loop = 0
        
        while is_playing_macro:
            current_loop += 1
            macro_current_loop = current_loop
            increment_stat('macros')
            update_status(f"Status: Playing '{macro_name}' (Loop {current_loop})", "green")

            start_time = time.time()
            for event in events:
                if not is_playing_macro: break

                # Handle pause before computing timing for this event
                if is_macro_paused:
                    pause_start = time.time()
                    while is_macro_paused and is_playing_macro:
                        time.sleep(0.001)
                    start_time += (time.time() - pause_start)

                if not is_playing_macro: break

                # Timing logic: use absolute timestamp scaled by speed
                target = event["timestamp"] / speed

                while (time.time() - start_time) < target:
                    if not is_playing_macro: break
                    # Re-check pause inside the timing wait too
                    if is_macro_paused:
                        pause_start = time.time()
                        while is_macro_paused and is_playing_macro:
                            time.sleep(0.001)
                        start_time += (time.time() - pause_start)
                    pass  # busy-spin for precise sub-millisecond timing

                if not is_playing_macro: break

                _execute_event(event)

                # Jitter applied as an inter-event sleep so it never shifts
                # absolute timestamps and cannot reorder subsequent events
                if jitter > 0:
                    time.sleep(random.uniform(0, jitter))
            
            # Check loop conditions
            if not infinite and current_loop >= loop_target:
                break
                
    finally:
        root.after(0, stop_macro_playback)
        
def _execute_event(event):
    """Execute a single macro event with proper error handling."""
    try:
        increment_stat('macro_events')
        
        action = event.get("action")
        
        if action == "mouse_down":
            button_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
            button = button_map.get(event["button"], Button.left)
            mouse.press(button)
            print(f"[PLAYBACK] mouse_down: {event['button']}")
        
        elif action == "mouse_up":
            button_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
            button = button_map.get(event["button"], Button.left)
            mouse.release(button)
            print(f"[PLAYBACK] mouse_up: {event['button']}")
        
        elif action == "mouse_move":
            # Use relative move for 3D games (camera) and absolute position for UI
            if event.get("dx") is not None and (event.get("dx") != 0 or event.get("dy") != 0):
                mouse.move(event["dx"], event["dy"])
            else:
                mouse.position = (event["x"], event["y"])
            print(f"[PLAYBACK] mouse_move: ({event['x']}, {event['y']})")
        
        elif action == "scroll":
            direction = event["direction"]
            amount = event["amount"]
            if direction in ["up", "down"]:
                scroll_amount = amount if direction == "up" else -amount
                mouse.scroll(0, scroll_amount)
            elif direction in ["left", "right"]:
                scroll_amount = amount if direction == "right" else -amount
                mouse.scroll(scroll_amount, 0)
            print(f"[PLAYBACK] scroll: {direction} ({amount})")
        
        elif action == "key_down":
            key = deserialize_key(event["key"])
            keyboard.press(key)
            print(f"[PLAYBACK] key_down: {get_key_display_name(key)}")
        
        elif action == "key_up":
            key = deserialize_key(event["key"])
            keyboard.release(key)
            print(f"[PLAYBACK] key_up: {get_key_display_name(key)}")
    
    except Exception as e:
        print(f"[EVENT ERROR] {str(e)}")


def pause_macro_playback():
    """Pause/resume macro playback."""
    global is_macro_paused, is_playing_macro
    
    if not is_playing_macro:
        return
        
    is_macro_paused = not is_macro_paused
    if not is_macro_paused:
        pause_macro_button.config(text="⏸️  Pause")
        update_status("Status: Macro playback resumed.", "green")
    else:
        pause_macro_button.config(text="▶️  Resume")
        update_status("Status: Macro playback paused.", "blue")


def stop_macro_playback():
    """Stop macro playback."""
    global is_playing_macro, macro_current_loop, is_macro_paused, is_macro_countdown_active, macro_countdown_job
    
    if is_macro_countdown_active and macro_countdown_job:
        root.after_cancel(macro_countdown_job)
        macro_countdown_job = None
    
    is_playing_macro = False
    macro_current_loop = 0
    is_macro_countdown_active = False # Reset countdown flag
    is_macro_paused = False
    update_status("Status: Macro playback stopped.", "blue")
    play_macro_button.config(state='normal')
    pause_macro_button.config(state='disabled')
    pause_macro_button.config(text="⏸️  Pause")
    stop_macro_button.config(state='disabled')
    start_stop_button.config(state='normal')


def delete_macro():
    """Delete selected macro with proper name extraction."""
    selected_index = macro_list_var.curselection()
    if not selected_index:
        update_status("Status: Please select a macro to delete.", "orange")
        return
    
    list_entry = macro_list_var.get(selected_index[0])
    macro_name = list_entry.rsplit(' (', 1)[0]

    if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{macro_name}'?", parent=root):
        return

    if macro_name in macro_storage:
        del macro_storage[macro_name]
        update_macro_list()
        update_status(f"Status: Macro '{macro_name}' deleted.", "blue")
        print(f"[MACRO] Deleted macro: {macro_name}")


def update_macro_list():
    """Safely update macro list display from any thread."""
    def _do_update():
        if not macro_list_var.winfo_exists(): return
        macro_list_var.delete(0, tk.END)
        for name in sorted(macro_storage.keys()):
            data = macro_storage[name]
            events = data.get("events", [])
            duration = events[-1]["timestamp"] if events else 0
            macro_list_var.insert(tk.END, f"{name} ({len(events)} ev, {duration:.2f}s)")
        
        if macro_list_var.size() > 0 and not macro_list_var.curselection():
            macro_list_var.selection_set(0)
            
    root.after(0, _do_update)
def save_macros_to_file():
    """Save macros to JSON with proper validation."""
    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="macros_backup.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save All Macros"
        )
        if not filename:
            return
        save_data = {}
        
        for macro_name, macro_data in macro_storage.items():
            save_data[macro_name] = {
                "events": macro_data.get("events", []),
                "created": macro_data.get("created", 0),
                "hardware_macro_key": macro_data.get("hardware_macro_key")
            }
        
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        update_status(f"Status: Macros saved to {filename}", "blue")
        print(f"[MACRO] Saved {len(macro_storage)} macros to {filename}")
    except Exception as e:
        update_status(f"Status: Error saving macros: {str(e)}", "red")
        print(f"[SAVE ERROR] {str(e)}")


def load_macros_from_file():
    """Load macros from JSON with proper validation."""
    try:
        filename = "macros_backup.json"
        if not os.path.exists(filename):
            update_status(f"Status: No backup file found ({filename})", "orange")
            return
        
        with open(filename, 'r') as f:
            save_data = json.load(f)
        
        if not isinstance(save_data, dict):
            update_status("Status: Invalid macro file format.", "red")
            print(f"[LOAD ERROR] Invalid file format: expected dict, got {type(save_data)}")
            return
        
        loaded_count = 0
        for macro_name, macro_info in save_data.items():
            if not isinstance(macro_info, dict):
                print(f"[LOAD WARNING] Skipping invalid macro: {macro_name}")
                continue
            
            macro_storage[macro_name] = {
                "events": macro_info.get("events", []),
                "created": macro_info.get("created", 0),
                "hardware_macro_key": macro_info.get("hardware_macro_key")
            }
            loaded_count += 1
        
        update_macro_list()
        update_status(f"Status: Loaded {loaded_count} macros from {filename}", "blue")
        print(f"[MACRO] Loaded {loaded_count} macros from {filename}")
    except json.JSONDecodeError as e:
        update_status(f"Status: Error: Invalid JSON in {filename}", "red")
        print(f"[LOAD ERROR] JSON decode error: {str(e)}")
    except Exception as e:
        update_status(f"Status: Error loading macros: {str(e)}", "red")
        print(f"[LOAD ERROR] {str(e)}")


def import_macro_from_file():
    """Import a macro from a JSON file."""
    try:
        filename = filedialog.askopenfilename(
            title="Import Macro",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return

        with open(filename, 'r') as f:
            import_data = json.load(f)

        # Detect single export vs full backup
        if isinstance(import_data, dict) and "name" in import_data and "events" in import_data:
            macros_to_import = {import_data["name"]: {
                "events": import_data["events"],
                "created": import_data.get("created", time.time()),
                "hardware_macro_key": import_data.get("hardware_macro_key")
            }}
        elif isinstance(import_data, dict):
            macros_to_import = import_data
        else:
            update_status("Status: Invalid macro file format.", "red")
            return

        for name, data in macros_to_import.items():
            final_name = name
            counter = 1
            while final_name in macro_storage:
                final_name = f"{name}_imported_{counter}"
                counter += 1
            macro_storage[final_name] = data

        update_macro_list()
        update_status(f"Status: Imported {len(macros_to_import)} macro(s).", "green")
    except Exception as e:
        update_status(f"Status: Error importing macro.", "red")

def export_macro_to_file():
    """Export selected macro to a separate JSON file."""
    selected_index = macro_list_var.curselection()
    if not selected_index:
        update_status("Status: Please select a macro to export.", "orange")
        return
    
    list_entry = macro_list_var.get(selected_index[0])
    macro_name = list_entry.rsplit(' (', 1)[0]

    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"{macro_name}_export.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Macro"
        )
        if not filename:
            return
            
        macro_data = macro_storage.get(macro_name)
        
        export_data = {
            "name": macro_name,
            "events": macro_data.get("events", []),
            "created": macro_data.get("created", 0)
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        update_status(f"Status: Exported '{macro_name}' to {filename}", "green")
        print(f"[EXPORT] Exported macro to {filename}")
    except Exception as e:
        update_status(f"Status: Error exporting macro: {str(e)}", "red")
        print(f"[EXPORT ERROR] {str(e)}")


def view_macro_details():
    """Display macro details in a popup."""
    selected_index = macro_list_var.curselection()
    if not selected_index:
        update_status("Status: Please select a macro to view.", "orange")
        return
    
    list_entry = macro_list_var.get(selected_index[0])
    macro_name = list_entry.rsplit(' (', 1)[0]

    macro_data = macro_storage.get(macro_name)
    if not macro_data or not macro_data.get("events"):
        update_status("Status: Selected macro is empty.", "orange")
        return

    events = macro_data.get("events", [])
    
    popup = tk.Toplevel(root)
    popup.title(f"Macro Details: {macro_name}")
    popup.geometry("800x600")
    popup.configure(bg=current_colors['bg'])
    
    header_frame = tk.Frame(popup, bg=current_colors['bg'])
    header_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(header_frame, text=f"Macro: {macro_name}", font=('Segoe UI', 14, 'bold'), 
            bg=current_colors['bg'], fg=current_colors['fg']).pack(anchor='w', pady=5)
    tk.Label(header_frame, text=f"Total Events: {len(events)}", font=('Segoe UI', 10), 
            bg=current_colors['bg'], fg=current_colors['fg']).pack(anchor='w')
    
    if events:
        duration = events[-1]['timestamp']
        tk.Label(header_frame, text=f"Duration: {duration:.2f}s", font=('Segoe UI', 10), 
                bg=current_colors['bg'], fg=current_colors['fg']).pack(anchor='w')
    
    text_frame = tk.Frame(popup, bg=current_colors['bg'])
    text_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    scrollbar = ttk.Scrollbar(text_frame)
    scrollbar.pack(side='right', fill='y')
    
    text_widget = tk.Text(text_frame, height=25, width=90, yscrollcommand=scrollbar.set, 
                         font=('Courier', 9), bg=current_colors['text_bg'], fg=current_colors['text_fg'],
                         borderwidth=1, relief='solid')
    text_widget.pack(side='left', fill='both', expand=True)
    scrollbar.config(command=text_widget.yview)
    
    details = f"{'='*80}\nMacro: {macro_name}\n{'='*80}\n\n"
    details += f"Total Events: {len(events)}\n"
    
    if events:
        duration = events[-1]['timestamp']
        details += f"Duration: {duration:.2f}s\n"
        details += f"Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(macro_data.get('created', 0)))}\n\n"
        details += f"{'#':<4} {'Timestamp':<12} {'Action':<15} {'Details':<50}\n"
        details += "-" * 80 + "\n"
        
        for i, event in enumerate(events, 1):
            action = event.get("action", "unknown")
            timestamp = event.get("timestamp", 0)
            
            if action == "mouse_move":
                details += f"{i:<4} {timestamp:<12.3f} {action:<15} X:{event['x']:<6} Y:{event['y']:<6}\n"
            elif action == "mouse_down":
                details += f"{i:<4} {timestamp:<12.3f} {action:<15} Button: {event['button']:<10}\n"
            elif action == "mouse_up":
                details += f"{i:<4} {timestamp:<12.3f} {action:<15} Button: {event['button']:<10}\n"
            elif action == "scroll":
                details += f"{i:<4} {timestamp:<12.3f} {action:<15} Direction: {event['direction']:<8} Amount: {event['amount']}\n"
            elif action == "key_down":
                details += f"{i:<4} {timestamp:<12.3f} {action:<15} Key: {event['key']:<15}\n"
            elif action == "key_up":
                hold = event.get('hold_duration', 0)
                details += f"{i:<4} {timestamp:<12.3f} {action:<15} Key: {event['key']:<8} (held {hold:.3f}s)\n"
    else:
        details += "\n[No events recorded]\n"
    
    details += "\n" + "="*80
    
    text_widget.insert('1.0', details)
    text_widget.config(state='disabled')
    
    button_frame = tk.Frame(popup, bg=current_colors['bg'])
    button_frame.pack(fill='x', padx=10, pady=10)
    tk.Button(button_frame, text="Close", command=popup.destroy, bg=current_colors['button_bg'], 
             fg=current_colors['button_fg'], borderwidth=0, relief='flat', 
             font=('Segoe UI', 10), cursor='hand2').pack(pady=5)
    
    update_status(f"Status: Viewing {macro_name} details", "blue")


def rename_macro():
    """Rename the selected macro with a themed dialog."""
    selected_index = macro_list_var.curselection()
    if not selected_index:
        update_status("Status: Please select a macro to rename.", "orange")
        return

    list_entry = macro_list_var.get(selected_index[0])
    old_name = list_entry.rsplit(' (', 1)[0]

    # Custom Themed Dialog
    dialog = tk.Toplevel(root)
    dialog.title("Rename Macro")
    dialog.geometry("400x200")
    dialog.configure(bg=current_colors['bg'])
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    # Center dialog relative to main window
    dialog.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")

    tk.Label(dialog, text=f"New name for '{old_name}':", bg=current_colors['bg'], fg=current_colors['fg'], 
             font=('Segoe UI', 11, 'bold')).pack(pady=(20, 10))
    
    name_entry = tk.Entry(dialog, width=30, bg=current_colors['text_bg'], fg=current_colors['text_fg'],
                          insertbackground=current_colors['accent'], font=('Segoe UI', 11), relief='solid', borderwidth=1)
    name_entry.insert(0, old_name)
    name_entry.pack(pady=10, padx=20)
    name_entry.focus_set()
    name_entry.selection_range(0, tk.END)

    def on_confirm(event=None):
        new_name = name_entry.get().strip()
        if new_name and new_name != old_name:
            if new_name in macro_storage:
                update_status(f"Status: Macro '{new_name}' already exists.", "orange")
            else:
                macro_storage[new_name] = macro_storage.pop(old_name)
                update_macro_list()
                update_status(f"Status: Renamed '{old_name}' to '{new_name}'.", "blue")
                print(f"[MACRO] Renamed: {old_name} -> {new_name}")
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=current_colors['bg'])
    btn_frame.pack(pady=20)

    tk.Button(btn_frame, text="OK", command=on_confirm, width=10, bg=current_colors['accent'], fg='white',
              relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2').pack(side='left', padx=10)
    tk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10, bg=current_colors['button_bg'], fg=current_colors['fg'],
              relief='flat', font=('Segoe UI', 10), cursor='hand2').pack(side='left', padx=10)

    dialog.bind("<Return>", on_confirm)
    dialog.bind("<Escape>", lambda e: dialog.destroy())


def duplicate_macro():
    """Create a copy of the selected macro."""
    selected_index = macro_list_var.curselection()
    if not selected_index:
        update_status("Status: Please select a macro to duplicate.", "orange")
        return

    list_entry = macro_list_var.get(selected_index[0])
    original_name = list_entry.rsplit(' (', 1)[0]

    new_name = f"{original_name}_copy"
    counter = 1
    while new_name in macro_storage:
        new_name = f"{original_name}_copy_{counter}"
        counter += 1
        
    macro_storage[new_name] = json.loads(json.dumps(macro_storage[original_name])) # Deep copy
    update_macro_list()
    update_status(f"Status: Duplicated '{original_name}' as '{new_name}'.", "blue")


def edit_macro_events():
    """Open a card-based timeline editor for macro events (SteelSeries GG style)."""
    selected_index = macro_list_var.curselection()
    if not selected_index:
        update_status("Status: Please select a macro to edit.", "orange")
        return
    
    list_entry = macro_list_var.get(selected_index[0])
    macro_name = list_entry.rsplit(' (', 1)[0]
    macro_data = macro_storage.get(macro_name)
    if not macro_data:
        return

    popup = tk.Toplevel(root)
    popup.title(f"Timeline Editor: {macro_name}")
    popup.geometry("800x850")
    popup.configure(bg=current_colors['bg'])
    popup.transient(root)
    popup.grab_set()

    tk.Label(popup, text=f"Timeline: {macro_name}", font=('Segoe UI', 16, 'bold'), 
             bg=current_colors['bg'], fg=current_colors['accent']).pack(pady=(20, 10))

    # --- Footer Controls (Pack first to ensure visibility at bottom) ---
    footer = tk.Frame(popup, bg=current_colors['bg'], pady=15)
    footer.pack(fill='x', side='bottom', padx=20)

    # --- Main Container ---
    main_container = tk.Frame(popup, bg=current_colors['bg'])
    main_container.pack(fill='both', expand=True, padx=20)

    # --- Scrollable Area ---
    canvas = tk.Canvas(main_container, bg=current_colors['bg'], highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
    timeline_frame = tk.Frame(canvas, bg=current_colors['bg'])

    timeline_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=timeline_frame, anchor="nw", width=650)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')

    # --- Logic ---
    def delete_action(index):
        if messagebox.askyesno("Delete", "Remove this action?", parent=popup):
            macro_data["events"].pop(index)
            render_timeline()

    def move_action(index, direction):
        new_idx = index + direction
        if 0 <= new_idx < len(macro_data["events"]):
            macro_data["events"][index], macro_data["events"][new_idx] = macro_data["events"][new_idx], macro_data["events"][index]
            render_timeline()

    def update_action_data(index, field, value):
        try:
            if field == "delay":
                new_delay = float(value)
                prev_ts = macro_data["events"][index-1]["timestamp"] if index > 0 else 0
                new_ts = prev_ts + new_delay
                diff = new_ts - macro_data["events"][index]["timestamp"]
                for i in range(index, len(macro_data["events"])):
                    macro_data["events"][i]["timestamp"] += diff
            elif field in ["x", "y", "amount"]:
                macro_data["events"][index][field] = int(value)
            else:
                macro_data["events"][index][field] = value
        except: pass

    def bulk_scale():
        try:
            factor = simpledialog.askfloat("Bulk Scale", "Multiply all delays by (e.g. 0.5 for 2x speed):", parent=popup, minvalue=0.01, maxvalue=100.0)
            if factor:
                prev_ts = 0
                for ev in macro_data["events"]:
                    delay = ev["timestamp"] - prev_ts
                    new_delay = delay * factor
                    ev["timestamp"] = prev_ts + new_delay
                    prev_ts = ev["timestamp"]
                render_timeline()
        except: pass

    def bulk_speed():
        factor = simpledialog.askfloat("Speed", "Multiplier (0.5=2x faster, 2.0=0.5x slower):", parent=popup)
        if factor:
            prev = 0
            for ev in macro_data["events"]:
                d = ev["timestamp"] - prev
                ev["timestamp"] = prev + (d * factor)
                prev = ev["timestamp"]
            render_timeline()

    def insert_new(action_type="mouse_move"):
        last_ts = macro_data["events"][-1]["timestamp"] if macro_data["events"] else 0
        
        new_event = {"timestamp": last_ts + 0.1, "action": action_type}
        if "key" in action_type:
            new_event["key"] = "char:a"
        elif action_type == "mouse_move":
            new_event.update({"x": 0, "y": 0})
        elif "mouse" in action_type:
            new_event["button"] = "left"
        elif action_type == "scroll":
            new_event.update({"direction": "up", "amount": 1})
            
        macro_data["events"].append(new_event)
        render_timeline()
        canvas.yview_moveto(1.0)

    def render_timeline():
        for widget in timeline_frame.winfo_children():
            widget.destroy()

        prev_ts = 0
        for i, ev in enumerate(macro_data.get("events", [])):
            delay = ev.get("timestamp", 0) - prev_ts
            prev_ts = ev.get("timestamp", 0)
            action = ev.get("action", "")
            
            # --- Delay Block (Independent Block) ---
            delay_container = tk.Frame(timeline_frame, bg=current_colors['bg'])
            delay_container.pack(fill='x')
            
            # Vertical connector
            tk.Frame(delay_container, bg='#444', width=2, height=8).pack()
            
            delay_card = tk.Frame(delay_container, bg=current_colors['frame_bg'], padx=10, pady=2, highlightthickness=1, highlightbackground='#333')
            delay_card.pack()
            
            tk.Label(delay_card, text="⌛ Wait:", bg=current_colors['frame_bg'], fg=current_colors['accent'], font=('Segoe UI', 8)).pack(side='left')
            
            d_ent = tk.Entry(delay_card, width=8, bg='#151515', fg='white', borderwidth=0, font=('Segoe UI', 9, 'bold'), justify='center')
            d_ent.insert(0, f"{delay:.3f}")
            d_ent.pack(side='left', padx=5)
            
            tk.Label(delay_card, text="s", bg=current_colors['frame_bg'], fg='#888', font=('Segoe UI', 8)).pack(side='left')
            
            d_ent.bind("<FocusOut>", lambda e, i=i, ent=d_ent: update_action_data(i, "delay", ent.get()))
            d_ent.bind("<Return>", lambda e, i=i, ent=d_ent: update_action_data(i, "delay", ent.get()))
            
            # Vertical connector
            tk.Frame(delay_container, bg='#444', width=2, height=8).pack()

            # --- Action Card ---
            color = "#1e3a5f" if "key" in action else "#107c10" if "mouse" in action and "move" not in action else "#3d3d3d"
            card = tk.Frame(timeline_frame, bg=color, relief='flat', pady=5, padx=10)
            card.pack(fill='x', pady=5, padx=5)

            # Card UI Components
            ctrl_frame = tk.Frame(card, bg=color)
            ctrl_frame.pack(side='left', padx=(0, 10))
            tk.Label(ctrl_frame, text=f"#{i+1}", bg=color, fg='white', font=('Segoe UI', 8, 'bold')).pack()
            tk.Button(ctrl_frame, text="▲", bg=color, fg='white', relief='flat', font=('Segoe UI', 7), command=lambda i=i: move_action(i, -1)).pack()
            tk.Button(ctrl_frame, text="▼", bg=color, fg='white', relief='flat', font=('Segoe UI', 7), command=lambda i=i: move_action(i, 1)).pack()

            icon_map = {"key_down": "⌨️ DN", "key_up": "⌨️ UP", "mouse_down": "🖱️ DN", "mouse_up": "🖱️ UP", "mouse_move": "📍 MOV", "scroll": "📜 SCR"}
            tk.Label(card, text=icon_map.get(action, "??"), bg=color, fg='white', font=('Segoe UI', 10, 'bold'), width=8).pack(side='left', padx=10)

            val_frame = tk.Frame(card, bg=color)
            val_frame.pack(side='left', fill='x', expand=True, padx=10)
            
            if "key" in action:
                tk.Label(val_frame, text="KEY", bg=color, fg='#bbb', font=('Segoe UI', 7)).pack(anchor='w')
                k_ent = tk.Entry(val_frame, bg='#252525', fg='white', borderwidth=0, font=('Segoe UI', 9))
                k_ent.insert(0, ev.get('key', ''))
                k_ent.pack(fill='x')
                k_ent.bind("<FocusOut>", lambda e, i=i, ent=k_ent: update_action_data(i, "key", ent.get()))
            elif action == "mouse_move":
                tk.Label(val_frame, text="POSITION (X, Y)", bg=color, fg='#bbb', font=('Segoe UI', 7)).pack(anchor='w')
                p_inner = tk.Frame(val_frame, bg=color)
                p_inner.pack(anchor='w')
                x_ent = tk.Entry(p_inner, width=5, bg='#252525', fg='white', borderwidth=0); x_ent.insert(0, str(ev.get('x'))); x_ent.pack(side='left')
                tk.Label(p_inner, text=",", bg=color, fg='white').pack(side='left')
                y_ent = tk.Entry(p_inner, width=5, bg='#252525', fg='white', borderwidth=0); y_ent.insert(0, str(ev.get('y'))); y_ent.pack(side='left')
                x_ent.bind("<FocusOut>", lambda e, i=i, ent=x_ent: update_action_data(i, "x", ent.get()))
                y_ent.bind("<FocusOut>", lambda e, i=i, ent=y_ent: update_action_data(i, "y", ent.get()))
            elif "mouse" in action:
                tk.Label(val_frame, text="BUTTON", bg=color, fg='#bbb', font=('Segoe UI', 7)).pack(anchor='w')
                b_var = tk.StringVar(value=ev.get('button', 'left'))
                b_sel = ttk.Combobox(val_frame, textvariable=b_var, values=["left", "right", "middle"], width=8, state="readonly")
                b_sel.pack(anchor='w')
                b_sel.bind("<<ComboboxSelected>>", lambda e, i=i, var=b_var: update_action_data(i, "button", var.get()))
            elif action == "scroll":
                tk.Label(val_frame, text="DIR / AMT", bg=color, fg='#bbb', font=('Segoe UI', 7)).pack(anchor='w')
                s_inner = tk.Frame(val_frame, bg=color)
                s_inner.pack(anchor='w')
                d_var = tk.StringVar(value=ev.get('direction', 'up'))
                d_sel = ttk.Combobox(s_inner, textvariable=d_var, values=["up", "down", "left", "right"], width=6, state="readonly"); d_sel.pack(side='left')
                a_ent = tk.Entry(s_inner, width=4, bg='#252525', fg='white', borderwidth=0); a_ent.insert(0, str(ev.get('amount', 1))); a_ent.pack(side='left', padx=5)
                d_sel.bind("<<ComboboxSelected>>", lambda e, i=i, var=d_var: update_action_data(i, "direction", var.get()))
                a_ent.bind("<FocusOut>", lambda e, i=i, ent=a_ent: update_action_data(i, "amount", ent.get()))

            tk.Button(card, text="✕", bg='#c50f1f', fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), command=lambda i=i: delete_action(i)).pack(side='right', padx=5)

    tk.Button(footer, text="+ ⌨️ Key", command=lambda: insert_new("key_down"), bg=current_colors['success'], fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), padx=8).pack(side='left', padx=2)
    tk.Button(footer, text="+ 🖱️ Click", command=lambda: insert_new("mouse_down"), bg=current_colors['success'], fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), padx=8).pack(side='left', padx=2)
    tk.Button(footer, text="+ 📍 Move", command=lambda: insert_new("mouse_move"), bg=current_colors['success'], fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), padx=8).pack(side='left', padx=2)
    tk.Button(footer, text="+ 📜 Scroll", command=lambda: insert_new("scroll"), bg=current_colors['success'], fg='white', relief='flat', font=('Segoe UI', 9, 'bold'), padx=8).pack(side='left', padx=2)
    
    tk.Frame(footer, width=10, bg=current_colors['bg']).pack(side='left')

    tk.Button(footer, text="⚡ Speed", command=bulk_speed, bg=current_colors['accent'], fg='white', relief='flat', font=('Segoe UI', 9), padx=10).pack(side='left', padx=2)
    tk.Button(footer, text="⌛ Delay", command=bulk_scale, bg=current_colors['button_bg'], fg=current_colors['fg'], relief='flat', font=('Segoe UI', 9), padx=10).pack(side='left', padx=2)

    def save_changes():
        update_macro_list()
        update_status(f"Status: Saved '{macro_name}'.", "green")
        popup.destroy()

    tk.Button(footer, text="Apply & Exit", command=save_changes, bg=current_colors['accent'], 
              fg='white', relief='flat', font=('Segoe UI', 10, 'bold'), padx=20).pack(side='right', padx=5)
    tk.Button(footer, text="Discard", command=popup.destroy, bg=current_colors['button_bg'], 
              fg=current_colors['fg'], relief='flat', font=('Segoe UI', 10), padx=20).pack(side='right', padx=5)

    render_timeline()

# --- Emergency Kill Logic ---

def emergency_kill():
    """Instantly stops all automation, releases stuck keys, and terminates the process."""
    global running, is_playing_macro, is_recording_macro, is_clicker_countdown_active, is_macro_countdown_active, clicker_countdown_job, macro_countdown_job
    
    # Immediate flag reset
    running = False
    is_playing_macro = False
    is_recording_macro = False
    
    try:
        if clicker_countdown_job:
            root.after_cancel(clicker_countdown_job)
        if macro_countdown_job:
            root.after_cancel(macro_countdown_job)
    except: pass

    is_clicker_countdown_active = False # Reset countdown flag
    is_macro_countdown_active = False # Reset countdown flag
    # Release common modifier keys to clear the OS input queue
    for k in [Key.ctrl, Key.shift, Key.alt, Key.cmd, Key.alt_gr]:
        try:
            keyboard.release(k)
        except:
            pass
            
    # Release the current target key and mouse buttons
    try:
        keyboard.release(target_key)
    except:
        pass
        
    for btn in [Button.left, Button.right, Button.middle]:
        try:
            mouse.release(btn)
        except:
            pass

    print("[KILL] Emergency exit triggered. Force closing program.")
    # Force immediate termination of the process and all threads
    os._exit(0)


# --- GUI Setup ---

load_user_preferences()
current_colors = THEME_COLORS['DARK'].copy() if user_preferences.get('dark_mode', True) else THEME_COLORS['LIGHT'].copy()

root = tk.Tk()
root.title("SKJ Clicker")
root.geometry("1000x950")
root.resizable(True, True)
root.configure(bg=current_colors['bg'])

def create_scrollable_tab(parent):
    canvas = tk.Canvas(parent, bg=current_colors['bg'], highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=current_colors['bg'])

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        # Dynamic width to prevent "small window" layout bugs
        canvas.itemconfig(window_id, width=event.width)

    scrollable_frame.bind("<Configure>", on_frame_configure)
    window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.bind("<Configure>", on_canvas_configure)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return scrollable_frame, canvas

style = ttk.Style()

def _update_widget_theme(widget):
    """Recursively update widget themes with smart color preservation."""
    # Standard colors to look for
    std_bgs = [THEME_COLORS['DARK']['bg'], THEME_COLORS['LIGHT']['bg'], 
               THEME_COLORS['DARK']['button_bg'], THEME_COLORS['LIGHT']['button_bg'],
               THEME_COLORS['DARK']['text_bg'], THEME_COLORS['LIGHT']['text_bg'],
               '#1e1e1e', '#0f0f0f', '#fafafa', '#f0f0f0', '#2b2b2b', '#f2f2f2', 
               '#202020', '#f9f9f9', '#252525']
    std_fgs = [THEME_COLORS['DARK']['fg'], THEME_COLORS['LIGHT']['fg'], '#ffffff', '#e0e0e0', '#000000', '#1c1c1c']
    std_btn_bgs = [THEME_COLORS['DARK']['button_bg'], THEME_COLORS['LIGHT']['button_bg'], '#3d3d3d', '#2b2b2b', '#f2f2f2', '#e0e0e0']
    std_accents = [THEME_COLORS['DARK']['accent'], THEME_COLORS['LIGHT']['accent']]
    std_accent_lights = [THEME_COLORS['DARK']['accent_light'], THEME_COLORS['LIGHT']['accent_light']]

    try:
        w_class = widget.winfo_class()
        
        # Safely update standard background colors
        try:
            curr_bg = widget.cget('bg')
            if curr_bg in std_bgs:
                widget.configure(bg=current_colors['bg'])
            elif curr_bg in std_accent_lights:
                widget.configure(bg=current_colors['accent_light'])
        except: pass
        
        # Safely handle standard foreground colors
        try:
            curr_fg = widget.cget('fg')
            if curr_fg in std_fgs:
                widget.configure(fg=current_colors['fg'])
            elif curr_fg in std_accents:
                widget.configure(fg=current_colors['accent'])
        except: pass
            
        if w_class == 'LabelFrame':
            widget.configure(bg=current_colors['bg'], fg=current_colors['accent'])
        elif w_class == 'Canvas':
            widget.configure(bg=current_colors['bg'], highlightthickness=0)
        elif w_class in ('Entry', 'Text', 'Listbox'):
            widget.configure(bg=current_colors['text_bg'], fg=current_colors['text_fg'])
            if w_class in ('Entry', 'Text'):
                widget.configure(insertbackground=current_colors['accent'])
            elif w_class == 'Listbox':
                widget.configure(selectbackground=current_colors['accent'], selectforeground='white')
        elif w_class == 'Button':
            # Update generic buttons, preserve specialized ones (red/green/orange)
            try:
                if widget.cget('bg') in std_btn_bgs:
                    widget.configure(bg=current_colors['button_bg'], fg=current_colors['button_fg'])
            except: pass
    except: pass

    # Always attempt to recurse into children even if parent updates fail
    for child in widget.winfo_children():
        _update_widget_theme(child)

def apply_theme():
    """Apply theme to all widgets."""
    root.configure(bg=current_colors['bg'])
    # Configure ttk styles properly
    style.theme_use('clam')
    style.configure('TFrame', background=current_colors['bg'])
    style.configure('TLabelFrame', background=current_colors['bg'], foreground=current_colors['fg'], 
                   borderwidth=1, relief='solid', font=('Segoe UI', 11, 'bold'))
    style.configure('TLabel', background=current_colors['bg'], foreground=current_colors['fg'])

    style.configure('Red.TButton', background='#c50f1f', foreground='white', borderwidth=1, 
                   relief='solid', padding=8, font=('Segoe UI', 10, 'bold'), focuscolor='none', 
                   highlightthickness=0, lightcolor='#c50f1f', darkcolor='#c50f1f')
    style.map('Red.TButton', background=[('active', '#da3b01'), ('pressed', '#da3b01')], 
             foreground=[('active', 'white'), ('pressed', 'white')],
             lightcolor=[('active', '#da3b01')],
             darkcolor=[('active', '#da3b01')])
    
    style.configure('TRadiobutton', background=current_colors['bg'], foreground=current_colors['fg'], 
                   font=('Segoe UI', 10), focuscolor='none', highlightthickness=0)
    style.map('TRadiobutton', background=[('active', current_colors['bg'])],
             foreground=[('active', current_colors['fg'])])
    
    style.configure('TCheckbutton', background=current_colors['bg'], foreground=current_colors['fg'], 
                   font=('Segoe UI', 10), focuscolor='none', highlightthickness=0)
    style.map('TCheckbutton', background=[('active', current_colors['bg'])],
             foreground=[('active', current_colors['fg'])])
    
    style.configure('Mode.TRadiobutton', background=current_colors['bg'], foreground=current_colors['accent'], 
                   font=('Segoe UI', 11, 'bold'), focuscolor='none', highlightthickness=0)
    style.map('Mode.TRadiobutton', background=[('active', current_colors['bg'])],
             foreground=[('active', current_colors['accent'])])
    
    style.configure('Accent.TLabel', background=current_colors['accent_light'], foreground=current_colors['accent'],
                   font=('Segoe UI', 11, 'bold'), padding=10, relief='solid', borderwidth=1)
    
    # Notebook styling
    style.configure('TNotebook', background=current_colors['bg'], foreground=current_colors['fg'], 
                   borderwidth=0, relief='flat', padding=0)
    style.configure('TNotebook.Tab', background=current_colors['button_bg'], foreground=current_colors['fg'],
                   padding=[20, 10], font=('Segoe UI', 10, 'bold'), borderwidth=0, relief='flat')
    style.map('TNotebook', background=[('selected', current_colors['bg'])])
    style.map('TNotebook.Tab', 
             background=[('selected', current_colors['bg']), ('active', current_colors['button_bg'])],
             foreground=[('selected', current_colors['accent']), ('active', current_colors['fg'])])
    
    # Combobox styling
    style.configure('TCombobox', fieldbackground=current_colors['text_bg'], background=current_colors['button_bg'],
                   foreground=current_colors['fg'], font=('Segoe UI', 10), borderwidth=1, relief='solid',
                   focuscolor='none', highlightthickness=0)
    style.map('TCombobox', fieldbackground=[('readonly', current_colors['text_bg']),
                                           ('active', current_colors['text_bg'])],
             background=[('active', current_colors['button_bg'])],
             foreground=[('active', current_colors['fg'])])
    
    # Scrollbar styling
    style.configure('Vertical.TScrollbar', background=current_colors['button_bg'],
                   troughcolor=current_colors['bg'], borderwidth=0, lightcolor=current_colors['button_bg'],
                   darkcolor=current_colors['button_bg'])
    _update_widget_theme(root)
    
    # Explicitly restore specialized backgrounds for header components
    try:
        title_frame.configure(bg=current_colors['button_bg'])
        title_inner.configure(bg=current_colors['button_bg'])
        top_right.configure(bg=current_colors['button_bg'])
    except: pass

def toggle_dark_mode():
    global current_colors
    current_colors = THEME_COLORS['DARK'].copy() if dark_mode.get() else THEME_COLORS['LIGHT'].copy()
    user_preferences['dark_mode'] = dark_mode.get()
    apply_theme()
    root.update_idletasks()

# Initialize variables
is_keyboard_mode = tk.BooleanVar(root, value=False)
is_hold_mode = tk.BooleanVar(root, value=False)
button_var = tk.StringVar(root, value="Left Click")
macro_infinite_var = tk.BooleanVar(root, value=user_preferences.get('macro_infinite', False))
dark_mode = tk.BooleanVar(root, value=user_preferences.get('dark_mode', True))
humanizer_enabled_var = tk.BooleanVar(root, value=user_preferences.get('humanizer_enabled', False))
show_hud_var = tk.BooleanVar(root, value=user_preferences.get('show_hud', True))
use_countdown_var = tk.BooleanVar(root, value=user_preferences.get('use_countdown', True))

# Top menu bar

# Top menu bar
top_frame = tk.Frame(root, bg=current_colors['bg'], highlightthickness=0)
top_frame.pack(fill='x', padx=0, pady=0)

title_frame = tk.Frame(root, bg=current_colors['button_bg'], highlightthickness=0)
title_frame.pack(fill='x', padx=0, pady=0)

title_inner = tk.Frame(title_frame, bg=current_colors['button_bg'], highlightthickness=0, pady=5)
title_inner.pack(fill='x', padx=15, pady=12)

ttk.Label(title_inner, text="SKJ Clicker", font=('Segoe UI', 18, 'bold')).pack(side='left', padx=0)

top_right = tk.Frame(title_inner, bg=current_colors['button_bg'], highlightthickness=0)
top_right.pack(side='right')

kill_button = tk.Button(
    top_right, text="🔥 KILL", command=emergency_kill, bg='#c50f1f', fg='white', 
    font=('Segoe UI', 9, 'bold'), relief='flat', padx=10, pady=2, cursor='hand2'
)
kill_button.pack(side='left', padx=10)

ttk.Label(top_right, text="🌓", font=('Segoe UI', 11)).pack(side='left', padx=8)
dark_mode_toggle = ttk.Checkbutton(top_right, variable=dark_mode, command=toggle_dark_mode)
dark_mode_toggle.pack(side='left', padx=5)

# Notebook
notebook_frame = tk.Frame(root, bg=current_colors['bg'], highlightthickness=0)
notebook_frame.pack(fill='both', expand=True, padx=12, pady=12)

notebook = ttk.Notebook(notebook_frame)
notebook.pack(fill='both', expand=True, pady=(10, 0))

# ==================== TAB 1: CLICKER ====================
tab1 = tk.Frame(notebook, bg=current_colors['bg'], highlightthickness=0)
notebook.add(tab1, text="⚙️  Clicker")

scrollable_frame1, canvas1 = create_scrollable_tab(tab1)

# Mode Selection
mode_frame = tk.LabelFrame(scrollable_frame1, text="🎯 TARGET MODE", bg=current_colors['bg'], fg=current_colors['accent'], 
                           borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=10)
mode_frame.pack(fill='x', pady=10, padx=10)

is_keyboard_mode.trace_add("write", lambda *args: update_mode_status()) 
is_hold_mode.trace_add("write", lambda *args: update_mode_status())

mode_buttons_frame = tk.Frame(mode_frame, bg=current_colors['bg'], highlightthickness=0)
mode_buttons_frame.pack(fill='x')

ttk.Radiobutton(
    mode_buttons_frame, text="🖱️  Mouse Click", variable=is_keyboard_mode, value=False, 
    style='Mode.TRadiobutton'
).pack(anchor='w', padx=15, pady=8)

ttk.Radiobutton(
    mode_buttons_frame, text="⌨️  Keyboard Press", variable=is_keyboard_mode, value=True, 
    style='Mode.TRadiobutton'
).pack(anchor='w', padx=15, pady=8)

# Action Type
hold_frame = tk.LabelFrame(scrollable_frame1, text="⚡ ACTION TYPE", bg=current_colors['bg'], fg=current_colors['accent'],
                          borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=10)
hold_frame.pack(fill='x', pady=10, padx=10)

action_buttons_frame = tk.Frame(hold_frame, bg=current_colors['bg'], highlightthickness=0)
action_buttons_frame.pack(fill='x')

ttk.Radiobutton(
    action_buttons_frame, text="🔄 Rapid Fire (Spam)", variable=is_hold_mode, value=False, 
    style='Mode.TRadiobutton'
).pack(anchor='w', padx=15, pady=8)

ttk.Radiobutton(
    action_buttons_frame, text="⏸️  Hold Down", variable=is_hold_mode, value=True, 
    style='Mode.TRadiobutton'
).pack(anchor='w', padx=15, pady=8)

# Delay Settings
delay_frame = tk.LabelFrame(scrollable_frame1, text="⏱️  SPEED CONTROL", bg=current_colors['bg'], fg=current_colors['accent'],
                           borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=10)
delay_frame.pack(fill='x', pady=10, padx=10)

delay_frame_inner = tk.Frame(delay_frame, bg=current_colors['bg'], highlightthickness=0)
delay_frame_inner.pack(fill='x', padx=5, pady=8)
ttk.Label(delay_frame_inner, text="Delay (seconds):").pack(side='left', padx=5)
delay_entry = tk.Entry(delay_frame_inner, width=10, bg=current_colors['text_bg'], 
                      fg=current_colors['text_fg'], borderwidth=1, relief='solid',
                      highlightthickness=0, insertbackground=current_colors['accent'],
                      font=('Segoe UI', 11, 'bold'))
delay_entry.insert(0, str(click_delay))
delay_entry.pack(side='left', padx=8)
apply_button = tk.Button(delay_frame_inner, text="✓ Apply", command=update_delay, bg=current_colors['accent'], fg='white', 
                        borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=15, pady=6, highlightthickness=0)
apply_button.pack(side='left', padx=5)

# Start Delay Setting
delay_row_2 = tk.Frame(delay_frame, bg=current_colors['bg'], highlightthickness=0)
delay_row_2.pack(fill='x', padx=5, pady=8)

countdown_check = ttk.Checkbutton(delay_row_2, text="Enable Countdown", variable=use_countdown_var)
countdown_check.pack(side='left', padx=5)

ttk.Label(delay_row_2, text="Start Delay (countdown):").pack(side='left', padx=5)
start_delay_entry = tk.Entry(delay_row_2, width=10, bg=current_colors['text_bg'], 
                      fg=current_colors['text_fg'], borderwidth=1, relief='solid',
                      highlightthickness=0, insertbackground=current_colors['accent'],
                      font=('Segoe UI', 11))
start_delay_entry.insert(0, str(user_preferences.get('start_delay', 3)))
start_delay_entry.pack(side='left', padx=8)
start_delay_entry.bind("<FocusOut>", lambda e: update_start_delay())
ttk.Label(delay_row_2, text="seconds").pack(side='left')

# Input Selection
input_frame = tk.LabelFrame(scrollable_frame1, text="🎮 INPUT SETTINGS", bg=current_colors['bg'], fg=current_colors['accent'],
                           borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=10)
input_frame.pack(fill='x', pady=10, padx=10)

mouse_row = tk.Frame(input_frame, bg=current_colors['bg'], highlightthickness=0)
mouse_row.pack(fill='x', pady=8, padx=10)
ttk.Label(mouse_row, text="Mouse Button:").pack(side='left', padx=5)
button_options = ["Left Click", "Right Click"]
button_selector = ttk.Combobox(
    mouse_row, textvariable=button_var, values=button_options, state="readonly", width=16,
    font=('Segoe UI', 10)
)
button_selector.pack(side='left', padx=8)
button_var.trace_add("write", update_button_type)

keyboard_row = tk.Frame(input_frame, bg=current_colors['bg'], highlightthickness=0)
keyboard_row.pack(fill='x', pady=8, padx=10)
key_label = tk.Label(keyboard_row, text=f"Target Key: ", bg=current_colors['bg'], fg=current_colors['fg'], font=('Segoe UI', 10))
key_label.pack(side='left', padx=5)
key_display = tk.Label(keyboard_row, text=f"{get_key_display_name(target_key)}", bg=current_colors['accent_light'], 
                       fg=current_colors['accent'], font=('Segoe UI', 10, 'bold'), relief='solid', borderwidth=1, padx=10, pady=4)
key_display.pack(side='left', padx=5)
record_key_button = tk.Button(
    keyboard_row, text="🎹 Set Key", command=set_recording_state, bg=current_colors['accent'], fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=12, pady=6, highlightthickness=0
)
record_key_button.pack(side='left', padx=5)

# Toggle Key
toggle_key_frame = tk.LabelFrame(scrollable_frame1, text="🔑 TOGGLE KEY", bg=current_colors['bg'], fg=current_colors['accent'],
                                borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=10)
toggle_key_frame.pack(fill='x', pady=10, padx=10)

toggle_row = tk.Frame(toggle_key_frame, bg=current_colors['bg'], highlightthickness=0)
toggle_row.pack(fill='x', padx=10, pady=8)
toggle_key_label = tk.Label(toggle_row, text=f"Press to Start/Stop: ", bg=current_colors['bg'], fg=current_colors['fg'], font=('Segoe UI', 10))
toggle_key_label.pack(side='left', padx=5)
toggle_key_display = tk.Label(toggle_row, text=f"{get_key_display_name(TOGGLE_KEY)}", bg='#c50f1f', 
                              fg='white', font=('Segoe UI', 10, 'bold'), relief='solid', borderwidth=1, padx=12, pady=4)
toggle_key_display.pack(side='left', padx=5)
record_toggle_key_button = tk.Button(
    toggle_row, text="🔄 Change", command=set_toggle_key_recording_state, bg=current_colors['accent'], fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=12, pady=6, highlightthickness=0
)
record_toggle_key_button.pack(side='left', padx=5)

# Control Button
control_frame_tab1 = tk.Frame(scrollable_frame1, bg=current_colors['bg'], highlightthickness=0)
control_frame_tab1.pack(fill='x', pady=15, padx=10)
start_stop_button = tk.Button(
    control_frame_tab1, text="▶️  START CLICKER", command=toggle_clicker_state, 
    bg=current_colors['accent'], fg='white', borderwidth=0, relief='flat', font=('Segoe UI', 13, 'bold'), 
    cursor='hand2', activebackground='#0066b3', activeforeground='white', padx=20, pady=15, highlightthickness=0
)
start_stop_button.pack(fill='x', pady=8)

# ==================== TAB 2: MACROS ====================
tab2 = tk.Frame(notebook, bg=current_colors['bg'], highlightthickness=0)
notebook.add(tab2, text="📹 Macros")

scrollable_frame2, canvas2 = create_scrollable_tab(tab2)

# Macro Recording
record_frame = tk.LabelFrame(scrollable_frame2, text="🔴 RECORD MACRO", bg=current_colors['bg'], fg=current_colors['accent'],
                            borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=5)
record_frame.pack(fill='x', pady=5, padx=10)

macro_row = tk.Frame(record_frame, bg=current_colors['bg'], highlightthickness=0)
macro_row.pack(fill='x', pady=8, padx=10)
ttk.Label(macro_row, text="Macro Name:").pack(side='left', padx=5)
macro_name_entry = tk.Entry(macro_row, width=18, bg=current_colors['text_bg'], 
                           fg=current_colors['text_fg'], borderwidth=1, relief='solid',
                           highlightthickness=0, insertbackground=current_colors['accent'],
                           font=('Segoe UI', 11))
macro_name_entry.insert(0, "Macro_1")
macro_name_entry.pack(side='left', padx=8)
record_macro_button = tk.Button(
    macro_row, text="⏺️  Start", command=toggle_macro_recording, bg=current_colors['accent'], fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=15, pady=6, highlightthickness=0
)
record_macro_button.pack(side='left', padx=5)

# Macro Shortcuts
shortcuts_frame = tk.LabelFrame(scrollable_frame2, text="⌨️ MACRO SHORTCUTS", bg=current_colors['bg'], fg=current_colors['accent'],
                                borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=5)
shortcuts_frame.pack(fill='x', pady=5, padx=10)

play_key_row = tk.Frame(shortcuts_frame, bg=current_colors['bg'], highlightthickness=0)
play_key_row.pack(fill='x', pady=5, padx=10)
tk.Label(play_key_row, text="Play/Stop Shortcut: ", bg=current_colors['bg'], fg=current_colors['fg'], font=('Segoe UI', 10)).pack(side='left', padx=5)
macro_play_key_display = tk.Label(play_key_row, text=f"{get_key_display_name(MACRO_TOGGLE_KEY)}", bg='#107c10', 
                                 fg='white', font=('Segoe UI', 10, 'bold'), relief='solid', borderwidth=1, padx=12, pady=4)
macro_play_key_display.pack(side='left', padx=5)
record_macro_play_button = tk.Button(
    play_key_row, text="🔄 Change", command=set_macro_play_key_recording_state, bg=current_colors['accent'], fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=12, pady=6, highlightthickness=0
)
record_macro_play_button.pack(side='left', padx=5)

rec_key_row = tk.Frame(shortcuts_frame, bg=current_colors['bg'], highlightthickness=0)
rec_key_row.pack(fill='x', pady=5, padx=10)
tk.Label(rec_key_row, text="Record/Stop Shortcut: ", bg=current_colors['bg'], fg=current_colors['fg'], font=('Segoe UI', 10)).pack(side='left', padx=5)
macro_rec_key_display = tk.Label(rec_key_row, text=f"{get_key_display_name(MACRO_REC_KEY)}", bg='#c50f1f', 
                                fg='white', font=('Segoe UI', 10, 'bold'), relief='solid', borderwidth=1, padx=12, pady=4)
macro_rec_key_display.pack(side='left', padx=5)
record_macro_rec_button = tk.Button(
    rec_key_row, text="🔄 Change", command=set_macro_rec_key_recording_state, bg=current_colors['accent'], fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=12, pady=6, highlightthickness=0
)
record_macro_rec_button.pack(side='left', padx=5)

# Macro List
list_frame = tk.LabelFrame(scrollable_frame2, text="📋 SAVED MACROS", bg=current_colors['bg'], fg=current_colors['accent'],
                          borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=5)
list_frame.pack(fill='both', expand=True, pady=5, padx=10)

scrollbar = ttk.Scrollbar(list_frame)
scrollbar.pack(side='right', fill='y')

macro_list_var = tk.Listbox(list_frame, height=8, width=60, yscrollcommand=scrollbar.set,
                            bg=current_colors['text_bg'], fg=current_colors['text_fg'],
                            font=('Segoe UI', 10), selectmode='single', activestyle='none',
                            relief='solid', borderwidth=1, highlightthickness=0,
                            selectbackground=current_colors['accent'], selectforeground='white')
macro_list_var.pack(side='left', fill='both', expand=True)
scrollbar.config(command=macro_list_var.yview)

# Playback Controls
playback_frame = tk.LabelFrame(scrollable_frame2, text="▶️  PLAYBACK", bg=current_colors['bg'], fg=current_colors['accent'],
                             borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=5)
playback_frame.pack(fill='x', pady=5, padx=10)

play_row = tk.Frame(playback_frame, bg=current_colors['bg'], highlightthickness=0)
play_row.pack(fill='x', pady=8, padx=10)
play_macro_button = tk.Button(
    play_row, text="▶️  Play", command=playback_macro_sequence, bg='#107c10', fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=15, pady=8, highlightthickness=0
)
play_macro_button.pack(side='left', padx=5)
pause_macro_button = tk.Button(
    play_row, text="⏸️  Pause", command=pause_macro_playback, bg='#ff9500', fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=15, pady=8, 
    state='disabled', highlightthickness=0
)
pause_macro_button.pack(side='left', padx=5)
stop_macro_button = tk.Button(
    play_row, text="⏹️  Stop", command=stop_macro_playback, bg='#c50f1f', fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=15, pady=8, 
    state='disabled', highlightthickness=0
)
stop_macro_button.pack(side='left', padx=5)

loop_options_frame = tk.Frame(playback_frame, bg=current_colors['bg'], highlightthickness=0)
loop_options_frame.pack(fill='x', pady=5, padx=10)

loop_check = ttk.Checkbutton(loop_options_frame, text="🔄 Infinite Loop", variable=macro_infinite_var)
loop_check.pack(side='left', padx=5)

ttk.Label(loop_options_frame, text="Loops:").pack(side='left', padx=10)
macro_loops_entry = tk.Entry(loop_options_frame, width=8, bg=current_colors['text_bg'], 
                            fg=current_colors['text_fg'], borderwidth=1, relief='solid',
                            font=('Segoe UI', 10))
macro_loops_entry.insert(0, str(user_preferences.get('macro_loops', 1)))
macro_loops_entry.pack(side='left', padx=5)

# Speed Multiplier
speed_row = tk.Frame(playback_frame, bg=current_colors['bg'], highlightthickness=0)
speed_row.pack(fill='x', pady=8, padx=10)
ttk.Label(speed_row, text="Playback Speed:").pack(side='left', padx=5)
speed_entry = tk.Entry(speed_row, width=10, bg=current_colors['text_bg'], 
                      fg=current_colors['text_fg'], borderwidth=1, relief='solid',
                      highlightthickness=0, insertbackground=current_colors['accent'],
                      font=('Segoe UI', 11, 'bold'))
speed_entry.insert(0, str(macro_playback_speed))
speed_entry.pack(side='left', padx=8)
speed_apply_button = tk.Button(speed_row, text="✓ Apply", command=update_playback_speed, bg=current_colors['accent'], fg='white', 
                              borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=15, pady=6, highlightthickness=0)
speed_apply_button.pack(side='left', padx=5)
speed_label = tk.Label(speed_row, text=f"Playback Speed: {macro_playback_speed:.2f}x", bg=current_colors['bg'], fg=current_colors['fg'], font=('Segoe UI', 10))
speed_label.pack(side='left', padx=10)

jitter_row = tk.Frame(playback_frame, bg=current_colors['bg'], highlightthickness=0)
jitter_row.pack(fill='x', pady=8, padx=10)

humanizer_check = ttk.Checkbutton(jitter_row, text="🧠 Humanizer", variable=humanizer_enabled_var)
humanizer_check.pack(side='left', padx=5)

ttk.Label(jitter_row, text="Jitter (ms):").pack(side='left', padx=10)
jitter_entry = tk.Entry(jitter_row, width=10, bg=current_colors['text_bg'], 
                      fg=current_colors['text_fg'], borderwidth=1, relief='solid',
                      highlightthickness=0, insertbackground=current_colors['accent'],
                      font=('Segoe UI', 11))
jitter_entry.insert(0, "0")
jitter_entry.pack(side='left', padx=8)
ttk.Label(jitter_row, text="(Adds 0 to X ms random delay)").pack(side='left', padx=5)

# Management
management_frame = tk.LabelFrame(scrollable_frame2, text="⚙️  MANAGEMENT", bg=current_colors['bg'], fg=current_colors['accent'],
                                borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=5)
management_frame.pack(fill='x', pady=5, padx=10)

mgmt_buttons = tk.Frame(management_frame, bg=current_colors['bg'], highlightthickness=0)
mgmt_buttons.pack(fill='x', pady=8, padx=10)

mgmt_buttons.columnconfigure((0, 1, 2, 3), weight=1)
mgmt_buttons.rowconfigure((0, 1, 2), weight=1)

btn_config = {'bg': current_colors['button_bg'], 'fg': current_colors['button_fg'], 'borderwidth': 0, 
              'relief': 'flat', 'font': ('Segoe UI', 11, 'bold'), 'cursor': 'hand2', 'pady': 12}

tk.Button(mgmt_buttons, text="👁️ Details", command=view_macro_details, **btn_config).grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="👯 Duplicate", command=duplicate_macro, **btn_config).grid(row=0, column=1, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="🛠️ Edit", command=edit_macro_events, **btn_config).grid(row=0, column=2, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="✏️ Rename", command=rename_macro, **btn_config).grid(row=0, column=3, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="📤 Export", command=export_macro_to_file, **btn_config).grid(row=1, column=0, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="📥 Import", command=import_macro_from_file, **btn_config).grid(row=1, column=1, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="💾 Save All", command=save_macros_to_file, **btn_config).grid(row=1, column=2, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="📂 Load All", command=load_macros_from_file, **btn_config).grid(row=1, column=3, sticky='nsew', padx=2, pady=2)
tk.Button(mgmt_buttons, text="🗑️ Delete", command=delete_macro, **btn_config).grid(row=2, column=0, columnspan=4, sticky='nsew', padx=2, pady=2)

# ==================== TAB 3: STATUS ====================
tab3 = tk.Frame(notebook, bg=current_colors['bg'], highlightthickness=0)
notebook.add(tab3, text="📊 Status")

scrollable_frame3, canvas3 = create_scrollable_tab(tab3)

# Status Display
info_frame = tk.LabelFrame(scrollable_frame3, text="⚡ STATUS", bg=current_colors['bg'], fg=current_colors['accent'],
                          borderwidth=2, relief='solid', font=('Segoe UI', 12, 'bold'), padx=15, pady=15)
info_frame.pack(fill='x', pady=15, padx=10)

status_label = tk.Label(info_frame, text="Status: INACTIVE", font=('Segoe UI', 16, 'bold'), foreground='#c50f1f', bg=current_colors['bg'])
status_label.pack(anchor='w', pady=10)

delay_label = tk.Label(info_frame, text=f"⏱️  Speed: {INITIAL_DELAY:.3f}s", font=('Segoe UI', 12), bg=current_colors['bg'], fg=current_colors['fg'])
delay_label.pack(anchor='w', pady=5)

toggle_key_info_label = tk.Label(info_frame, text=f"🔑 Toggle Key: '{get_key_display_name(TOGGLE_KEY)}'", font=('Segoe UI', 11, 'italic'), bg=current_colors['bg'], fg=current_colors['accent'])
toggle_key_info_label.pack(anchor='w', pady=10)

kill_key_row = tk.Frame(info_frame, bg=current_colors['bg'], highlightthickness=0)
kill_key_row.pack(anchor='w', pady=5)
tk.Label(kill_key_row, text="🔥 Emergency Kill Shortcut: ", bg=current_colors['bg'], fg=current_colors['fg'], font=('Segoe UI', 10)).pack(side='left', padx=5)
kill_key_display = tk.Label(kill_key_row, text=f"{get_key_display_name(KILL_KEY)}", bg='#c50f1f', 
                             fg='white', font=('Segoe UI', 10, 'bold'), relief='solid', borderwidth=1, padx=12, pady=4)
kill_key_display.pack(side='left', padx=5)
record_kill_key_button = tk.Button(
    kill_key_row, text="🔄 Change", command=set_kill_key_recording_state, bg=current_colors['accent'], fg='white', 
    borderwidth=0, relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2', padx=12, pady=6, highlightthickness=0
)
record_kill_key_button.pack(side='left', padx=10)


hud_toggle_frame = tk.Frame(info_frame, bg=current_colors['bg'], highlightthickness=0)
hud_toggle_frame.pack(anchor='w', pady=5)
ttk.Label(hud_toggle_frame, text="Display HUD Overlay:").pack(side='left', padx=5)
hud_check = ttk.Checkbutton(hud_toggle_frame, variable=show_hud_var, command=update_hud)
hud_check.pack(side='left', padx=5)

stats_toggle_frame = tk.Frame(info_frame, bg=current_colors['bg'], highlightthickness=0)
stats_toggle_frame.pack(anchor='w', pady=5)
ttk.Label(stats_toggle_frame, text="Enable Stats Dashboard:").pack(side='left', padx=5)
# Variable will be initialized after tab4 is defined to handle visibility

# Quick Tips
tips_frame = tk.LabelFrame(scrollable_frame3, text="💡 QUICK TIPS", bg=current_colors['bg'], fg=current_colors['accent'],
                          borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=10)
tips_frame.pack(fill='x', pady=10, padx=10)

tips_text = tk.Text(tips_frame, height=8, width=70, bg=current_colors['text_bg'], 
                   fg=current_colors['text_fg'], font=('Segoe UI', 9), 
                   relief='solid', borderwidth=1, wrap='word', state='normal',
                   highlightthickness=0, insertbackground=current_colors['accent'])

tips_content = """✓ Use Alt+Tab to quickly switch windows
✓ Keep your toggle key distinct to avoid accidental activation
✓ Test macros with short delays first
✓ Use Rapid Fire for games, Hold Down for apps
✓ Save important macros regularly to backup
✓ Dark Mode is easy on the eyes for long sessions
✓ Try different playback speeds for optimal timing"""

tips_text.insert('1.0', tips_content)
tips_text.config(state='disabled')
tips_text.pack(fill='x', padx=5, pady=8)

# Info Box
info_box = tk.LabelFrame(scrollable_frame3, text="ℹ️  FEATURES", bg=current_colors['bg'], fg=current_colors['accent'],
                        borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=12, pady=10)
info_box.pack(fill='both', expand=True, pady=10, padx=10)

info_text = tk.Text(info_box, height=12, width=70, bg=current_colors['text_bg'], 
                   fg=current_colors['text_fg'], font=('Segoe UI', 9), 
                   relief='solid', borderwidth=1, wrap='word', state='disabled',
                   highlightthickness=0, insertbackground=current_colors['accent'])

info_content = """
🖱️  AUTO-CLICKER
Automate repetitive mouse clicks for games and applications.

⌨️  AUTO-PRESSER
Automate keyboard key presses with customizable delays.

📹 MACRO RECORDER
Record and playback complex sequences of mouse and keyboard actions.

🎨 DARK/LIGHT MODE
Switch between themes for comfortable viewing - preferences saved!

⏱️  SPEED CONTROL
Fine-tune delays and playback speeds with real-time preview.

🔑 CUSTOM TOGGLE KEY
Set any key to start/stop automation without UI interaction.

📤 MACRO EXPORT
Export individual macros to separate JSON files for sharing.

⏸️  PAUSE/RESUME
Pause and resume macro playback on demand.
"""

info_text.config(state='normal')
info_text.insert('1.0', info_content.strip())
info_text.config(state='disabled')
info_text.pack(fill='both', expand=True, padx=5, pady=8)

def create_stat_row(parent, label_text):
    row = tk.Frame(parent, bg=current_colors['bg'])
    row.pack(fill='x', pady=4)
    tk.Label(row, text=label_text, font=('Segoe UI', 10), bg=current_colors['bg'], fg=current_colors['fg']).pack(side='left')
    val_lbl = tk.Label(row, text="0", font=('Segoe UI', 10, 'bold'), bg=current_colors['bg'], fg=current_colors['accent'])
    val_lbl.pack(side='right')
    return val_lbl

# --- Integrated Statistics Section ---
stats_container = tk.Frame(scrollable_frame3, bg=current_colors['bg'])
# We don't pack it yet; refresh_stats_tab_visibility handles it

# Session Stats
s_stats_frame = tk.LabelFrame(stats_container, text="🕒 SESSION STATISTICS", bg=current_colors['bg'], fg=current_colors['accent'],
                             borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=15, pady=10)
s_stats_frame.pack(fill='x', pady=10, padx=10)

s_clicks_val = create_stat_row(s_stats_frame, "Mouse Clicks:")
s_keys_val = create_stat_row(s_stats_frame, "Keyboard Presses:")
s_macros_val = create_stat_row(s_stats_frame, "Macros Played:")
s_uptime_val = create_stat_row(s_stats_frame, "Session Uptime:")

tk.Button(s_stats_frame, text="Reset Session", command=reset_session_stats, bg=current_colors['button_bg'], 
          fg=current_colors['fg'], font=('Segoe UI', 9), relief='flat', padx=10).pack(pady=10)

# Lifetime Stats
l_stats_frame = tk.LabelFrame(stats_container, text="🌎 LIFETIME STATISTICS", bg=current_colors['bg'], fg=current_colors['accent'],
                             borderwidth=2, relief='solid', font=('Segoe UI', 11, 'bold'), padx=15, pady=10)
l_stats_frame.pack(fill='x', pady=10, padx=10)

l_clicks_val = create_stat_row(l_stats_frame, "Total Clicks:")
l_keys_val = create_stat_row(l_stats_frame, "Total Presses:")
l_macros_val = create_stat_row(l_stats_frame, "Total Macros Played:")
l_uptime_val = create_stat_row(l_stats_frame, "Total Active Time:")

tk.Button(l_stats_frame, text="Reset Lifetime Data", command=reset_lifetime_stats, bg='#c50f1f', 
          fg='white', font=('Segoe UI', 9, 'bold'), relief='flat', padx=10).pack(pady=10)

notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

# Helper for Uptime tracking
last_active_calc_time = time.time()
def track_active_time():
    """Background task to track session and lifetime uptime."""
    global last_active_calc_time
    now = time.time()
    delta = now - last_active_calc_time
    last_active_calc_time = now
    
    # Privacy: Only track if the dashboard is enabled
    if user_preferences.get('show_stats_tab', True):
        # Session Uptime (Total time app is open with stats enabled)
        session_stats['active_seconds'] += delta
        
        # Lifetime Active Time (Time clicker is actually working)
        if running or is_playing_macro:
            user_preferences['stat_lifetime_active_seconds'] += delta
    
    root.after(1000, track_active_time)

root.after(1000, track_active_time)

# --- Optional Tab Logic ---
def refresh_stats_tab_visibility(*args):
    """Toggle the Statistics sections within the Status tab."""
    enabled = show_stats_var.get()
    user_preferences['show_stats_tab'] = enabled
    
    if enabled:
        # Insert after the main status info frame
        stats_container.pack(fill='x', after=info_frame)
    else:
        stats_container.pack_forget()

show_stats_var = tk.BooleanVar(value=user_preferences.get('show_stats_tab', True))
stats_check = ttk.Checkbutton(stats_toggle_frame, variable=show_stats_var, command=refresh_stats_tab_visibility)
stats_check.pack(side='left', padx=5)

# Apply initial theme after UI is built
apply_theme()

# Initial Status
update_status("Status: INACTIVE", "red")

# Trigger initial visibility
refresh_stats_tab_visibility()

def on_closing():
    """Stops all threads and listeners before exiting."""
    global running, is_playing_macro, is_recording_macro
    
    # Signal threads to stop
    running = False
    is_playing_macro = False
    is_recording_macro = False
    
    # Sync current UI state to preferences before saving
    user_preferences.update({
        'dark_mode': dark_mode.get(),
        'humanizer_enabled': humanizer_enabled_var.get(),
        'show_hud': show_hud_var.get(),
        'use_countdown': use_countdown_var.get(),
        'macro_infinite': macro_infinite_var.get(),
        'macro_loops': int(macro_loops_entry.get()) if macro_loops_entry.get().isdigit() else user_preferences.get('macro_loops', 1),
        'start_delay': int(start_delay_entry.get()) if start_delay_entry.get().isdigit() else user_preferences.get('start_delay', 0),
        'show_stats_tab': show_stats_var.get()
    })

    # Stop listeners
    if mouse_listener:
        try: mouse_listener.stop()
        except: pass
    if keyboard_macro_listener:
        try: keyboard_macro_listener.stop()
        except: pass
    if keyboard_listener:
        try: keyboard_listener.stop()
        except: pass
        
    if hud_window and hud_window.winfo_exists():
        try: hud_window.destroy()
        except: pass
        
    save_user_preferences()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Run
root.mainloop()