import math
import re
import sys
import time

from pynput import keyboard

try:
    from music21 import pitch
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

from config import (
    ACCIDENTAL_MODIFIERS,
    KEY_MAP,
    KEYBOARD_MAX_MIDI,
    KEYBOARD_MIN_MIDI,
    NOTE_TO_JIANPU_BASE,
)
from playback.base import PlaybackBackend


def standard_note_to_internal_jianpu(standard_note_name_with_octave):
    """Translates a music21 pitch name (e.g., 'C4', 'G#5') to internal Jianpu for KEY_MAP.
       Returns the base Jianpu string (e.g., '1', '5̇', '6̣'). Accidental is handled separately.
    """
    # music21 format often is like C#4, G-5 (flat is -)
    match = re.match(r'([A-G])([#-]?)(\d+)', standard_note_name_with_octave)
    if not match:
        return None
    note_letter, _, octave_str = match.groups() # Accidental handled separately
    octave = int(octave_str)

    base_jianpu = NOTE_TO_JIANPU_BASE.get(note_letter)
    if not base_jianpu:
        return None # Should not happen

    octave_mark = ''
    # Reference octave is 4 for middle row 'a'-'j'
    if octave > 4:
        octave_mark = '\u0307' * (octave - 4) # Dot above
    elif octave < 4:
        octave_mark = '\u0323' * (4 - octave) # Dot below

    return f"{base_jianpu}{octave_mark}"

class PynputKeyboardBackend(PlaybackBackend):
    """Playback backend using pynput to simulate global keyboard presses."""
    def __init__(self):
        self.keyboard_controller = keyboard.Controller()
        print("Initialized PynputKeyboardBackend")

    def start(self):
        # No specific start action needed for pynput controller itself
        pass

    def stop(self):
        # No specific stop action needed, but could release held keys if tracked
        pass

    def _get_key_and_modifier(self, note_pitch: pitch.Pitch, apply_octave_shift: bool):
        """Calculates the target key character and modifier key for a given pitch."""
        original_pitch = note_pitch
        adjusted_pitch = note_pitch
        shift_applied = ""

        if apply_octave_shift:
            if adjusted_pitch.midi < KEYBOARD_MIN_MIDI:
                shift_amount = 12 * math.ceil((KEYBOARD_MIN_MIDI - adjusted_pitch.midi) / 12.0)
                adjusted_pitch = adjusted_pitch.transpose(shift_amount)
                shift_applied = f" (Shifted +{shift_amount})"
            elif adjusted_pitch.midi > KEYBOARD_MAX_MIDI:
                shift_amount = -12 * math.ceil((adjusted_pitch.midi - KEYBOARD_MAX_MIDI) / 12.0)
                adjusted_pitch = adjusted_pitch.transpose(shift_amount)
                shift_applied = f" (Shifted {shift_amount})"

        standard_note_name = adjusted_pitch.nameWithOctave
        keymap_jianpu = standard_note_to_internal_jianpu(standard_note_name)

        if not keymap_jianpu:
            print(f"Warning: Could not map standard note {standard_note_name} to internal Jianpu key.{shift_applied}", file=sys.stderr)
            return None, None, original_pitch.nameWithOctave, shift_applied

        key_to_press_char = KEY_MAP.get(keymap_jianpu)
        accidental_symbol = None
        if '#' in adjusted_pitch.name:
            accidental_symbol = '#'
        elif '-' in adjusted_pitch.name:
            accidental_symbol = '-'
        modifier_key = ACCIDENTAL_MODIFIERS.get(accidental_symbol)

        if not key_to_press_char:
            print(f"Warning: No key mapping for Jianpu key: {keymap_jianpu} (from {standard_note_name}).{shift_applied}", file=sys.stderr)
            return None, None, original_pitch.nameWithOctave, shift_applied

        return key_to_press_char, modifier_key, original_pitch.nameWithOctave, shift_applied

    def _press_key_combo(self, key_char: str, modifier_key=None):
        """Simulates pressing a key, potentially with a modifier."""
        try:
            if modifier_key:
                self.keyboard_controller.press(modifier_key)
                time.sleep(0.01) # Small delay for reliability
                self.keyboard_controller.tap(key_char)
                time.sleep(0.01)
                self.keyboard_controller.release(modifier_key)
            else:
                self.keyboard_controller.tap(key_char)
            return True
        except Exception as e:
            print(f"Error simulating key '{key_char}' (Modifier: {modifier_key}): {e}", file=sys.stderr)
            return False

    def play_note(self, note_pitch: pitch.Pitch, duration_sec: float, apply_octave_shift: bool, volume: float):
        # Volume is ignored for pynput backend
        key_char, mod_key, orig_name, shift_info = self._get_key_and_modifier(note_pitch, apply_octave_shift)

        if key_char:
            log_msg = f"Playing Note: {orig_name}"
            if shift_info:
                log_msg += f" -> {note_pitch.transpose(int(shift_info.split(' ')[2].replace('(','').replace(')',''))).nameWithOctave}{shift_info}"
            log_msg += f" -> Key: '{key_char}', Mod: {mod_key or 'None'}"
            print(log_msg)
            self._press_key_combo(key_char, mod_key)
        # Duration is handled by the main playback loop

    def play_chord(self, chord_pitches: list[pitch.Pitch], duration_sec: float, apply_octave_shift: bool, volume: float):
        # Volume is ignored for pynput backend
        keys_to_press = []
        log_parts = []
        orig_names = [p.nameWithOctave for p in chord_pitches]

        for p in chord_pitches:
            key_char, mod_key, orig_name, shift_info = self._get_key_and_modifier(p, apply_octave_shift)
            if key_char:
                keys_to_press.append((key_char, mod_key))
                log_part = f"{orig_name}"
                if shift_info:
                     log_part += f"->{p.transpose(int(shift_info.split(' ')[2].replace('(','').replace(')',''))).nameWithOctave}{shift_info}"
                log_part += f"->('{key_char}',{mod_key or 'N'})"
                log_parts.append(log_part)
            else:
                 log_parts.append(f"{orig_name}->(Map Err)")

        if keys_to_press:
            print(f"Playing Chord: { ' | '.join(log_parts) }")
            # Simple sequential tap for chords in this backend
            # More complex backends might handle true simultaneity
            for key_char, mod_key in keys_to_press:
                self._press_key_combo(key_char, mod_key)
                time.sleep(0.005) # Tiny delay between chord notes
        else:
            print(f"Warning: Could not map any notes in chord: {orig_names}", file=sys.stderr)
         # Duration is handled by the main playback loop

    def rest(self, duration_sec: float):
        # The backend doesn't need to do anything for a rest,
        # the main loop just waits.
        print(f"Resting for {duration_sec:.3f}s")
        pass 