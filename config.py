from pynput import keyboard

# --- Configuration ---
DEFAULT_SCORES_DIRECTORY = 'scores'
PREV_SCORE_HOTKEY_COMBINATION = {keyboard.Key.f7}
NEXT_SCORE_HOTKEY_COMBINATION = {keyboard.Key.f8}
START_HOTKEY_COMBINATION = {keyboard.Key.f9}
STOP_HOTKEY_COMBINATION = {keyboard.Key.f10}
PAUSE_RESUME_HOTKEY_COMBINATION = {keyboard.Key.f11} # Added Pause key
EXIT_HOTKEY_COMBINATION = {keyboard.Key.esc}
DEFAULT_TEMPO_BPM = 120 # Default BPM if not found in score

# --- Keyboard Range Definition ---
KEYBOARD_MIN_MIDI = 48 # C3
KEYBOARD_MAX_MIDI = 83 # B5

# Define MIDI ranges supported by different backends
# Used to determine if full score playback is feasible
BACKEND_MIDI_RANGES = {
    'pynput': {'min': KEYBOARD_MIN_MIDI, 'max': KEYBOARD_MAX_MIDI}, # C3-B5
    'sample': {'min': 36, 'max': 92}, # C2-G#6 (Based on provided sample map keys)
    'midi': {'min': 0, 'max': 127}  # 完整MIDI范围，所有音符都支持
}

# MIDI后端配置
DEFAULT_MIDI_PORT_NAME = None  # 默认使用第一个可用端口，如果无可用端口则创建虚拟端口
# 可以设置为特定端口名称，如 "Microsoft GS Wavetable Synth" 或 "LoopMIDI Port"

# MIDI乐器配置
DEFAULT_MIDI_INSTRUMENT = 0  # 0 = 大钢琴 (Acoustic Grand Piano)
# General MIDI乐器参考:
# 0-7: 钢琴类 (0=大钢琴, 1=明亮钢琴, 2=电钢琴, 3=酒吧钢琴, 等)
# 详细列表请参考General MIDI标准

# For pynput_backend, can be moved later if more backends are added
# Maps standard accidental symbols to pynput modifier keys
ACCIDENTAL_MODIFIERS = {
    '#': keyboard.Key.shift,
    '-': keyboard.Key.ctrl, # Using '-' for flat (b) from music21 pitch name
}

# For pynput_backend, can be moved later
# This map uses the *internal* Jianpu representation derived from standard notation
KEY_MAP = {
    '1': 'a', '2': 's', '3': 'd', '4': 'f', '5': 'g', '6': 'h', '7': 'j',
    '1̇': 'q', '2̇': 'w', '3̇': 'e', '4̇': 'r', '5̇': 't', '6̇': 'y', '7̇': 'u',
    '1̣': 'z', '2̣': 'x', '3̣': 'c', '4̣': 'v', '5̣': 'b', '6̣': 'n', '7̣': 'm',
}

# For pynput_backend, can be moved later
# For translating standard note letters (C-B) to base Jianpu digits (1-7)
NOTE_TO_JIANPU_BASE = {
    'C': '1', 'D': '2', 'E': '3', 'F': '4', 'G': '5', 'A': '6', 'B': '7',
}

# Derived Configurations
# ABS_SCORES_DIRECTORY = os.path.abspath(SCORES_DIRECTORY) 