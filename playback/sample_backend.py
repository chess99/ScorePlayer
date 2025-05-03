import os
import sys

try:
    import pygame
except ImportError:
    print("Error: pygame library not found.", file=sys.stderr)
    print("Please install it using: pip install pygame", file=sys.stderr)
    sys.exit(1)

try:
    from music21 import pitch
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

from playback.base import PlaybackBackend

# --- Configuration ---
SAMPLES_DIR = "samples/piano"

# Mapping from the provided JavaScript object
# Note: Filenames seem arbitrary ('a54.mp3'), we rely on the note name key
# Using sharps (#) as per the map keys.
NOTE_SAMPLE_MAP = {
  'A2': "a54.mp3",
  'A3': "a69.mp3",
  'A4': "a80.mp3",
  'A5': "a74.mp3",
  'A6': "a66.mp3",
  'A#3': "b69.mp3",
  'A#4': "b80.mp3",
  'A#5': "b74.mp3",
  'A#6': "b66.mp3",
  'B2': "a55.mp3",
  'B3': "a82.mp3",
  'B4': "a65.mp3",
  'B5': "a75.mp3",
  'B6': "a78.mp3",
  'C2': "a49.mp3",
  'C3': "a56.mp3",
  'C4': "a84.mp3",
  'C5': "a83.mp3",
  'C6': "a76.mp3",
  'C7': "a77.mp3",
  'C#2': "b49.mp3",
  'C#3': "b56.mp3",
  'C#4': "b84.mp3",
  'C#5': "b83.mp3",
  'C#6': "b76.mp3",
  'D2': "a50.mp3",
  'D3': "a57.mp3",
  'D4': "a89.mp3",
  'D5': "a68.mp3",
  'D6': "a90.mp3",
  'D#2': "b50.mp3",
  'D#3': "b57.mp3",
  'D#4': "b89.mp3",
  'D#5': "b68.mp3",
  'D#6': "b90.mp3",
  'E2': "a51.mp3",
  'E3': "a48.mp3",
  'E4': "a85.mp3",
  'E5': "a70.mp3",
  'E6': "a88.mp3",
  'F2': "a52.mp3",
  'F3': "a81.mp3",
  'F4': "a73.mp3",
  'F5': "a71.mp3",
  'F6': "a67.mp3",
  'F#2': "b52.mp3",
  'F#3': "b81.mp3",
  'F#4': "b73.mp3",
  'F#5': "b71.mp3",
  'F#6': "b67.mp3",
  'G2': "a53.mp3",
  'G3': "a87.mp3",
  'G4': "a79.mp3",
  'G5': "a72.mp3",
  'G6': "a86.mp3",
  'G#2': "b53.mp3",
  'G#3': "b87.mp3",
  'G#4': "b79.mp3",
  'G#5': "b72.mp3",
  'G#6': "b86.mp3"
}


class SamplePlaybackBackend(PlaybackBackend):
    """Playback backend using pygame to play pre-recorded audio samples."""

    def __init__(self):
        self.samples: dict[str, pygame.mixer.Sound | None] = {}
        self.is_initialized = False
        print("SamplePlaybackBackend created. Call start() to initialize pygame and load samples.")

    def start(self):
        """Initialize pygame mixer and load audio samples."""
        if self.is_initialized:
            return
        print("Initializing pygame mixer...")
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32) # Increase available channels
            print("Pygame mixer initialized with 32 channels.")
        except Exception as e:
            print(f"Error initializing pygame mixer: {e}", file=sys.stderr)
            print("Sample playback will likely fail.", file=sys.stderr)
            return # Don't proceed with loading if mixer failed

        print(f"Loading samples from '{SAMPLES_DIR}'...")
        loaded_count = 0
        missing_count = 0
        error_count = 0

        if not os.path.isdir(SAMPLES_DIR):
             print(f"Warning: Samples directory not found: '{SAMPLES_DIR}'", file=sys.stderr)
             print("Cannot load any samples.", file=sys.stderr)
             # Mark as initialized but with no samples
             self.is_initialized = True 
             return

        for note_name, filename in NOTE_SAMPLE_MAP.items():
            file_path = os.path.join(SAMPLES_DIR, filename)
            if os.path.exists(file_path):
                try:
                    sound = pygame.mixer.Sound(file_path)
                    self.samples[note_name] = sound
                    loaded_count += 1
                except Exception as e:
                    print(f"Error loading sample '{filename}' for note '{note_name}': {e}", file=sys.stderr)
                    self.samples[note_name] = None # Mark as unloadable
                    error_count += 1
            else:
                print(f"Warning: Sample file missing for note '{note_name}': '{file_path}'", file=sys.stderr)
                self.samples[note_name] = None # Mark as missing
                missing_count += 1
        
        print(f"Sample loading complete. Loaded: {loaded_count}, Missing: {missing_count}, Errors: {error_count}")
        if loaded_count == 0:
             print("Warning: No samples were loaded successfully. Playback will be silent.", file=sys.stderr)

        self.is_initialized = True

    def stop(self):
        """Stop all currently playing sounds and quit the mixer."""
        if not self.is_initialized:
             return
        print("Stopping all sample sounds...")
        try:
             pygame.mixer.stop()
             # Consider if pygame.mixer.quit() is needed. 
             # If start() might be called again, maybe don't quit? Let's omit quit for now.
             # pygame.mixer.quit() 
        except Exception as e:
            print(f"Error stopping pygame mixer: {e}", file=sys.stderr)
        # Don't reset is_initialized here, allow restart?

    def _get_sample_key(self, note_pitch: pitch.Pitch) -> str | None:
        """Converts a music21 pitch object to the sharp-based key used in our map."""
        # Start with the standard name
        note_name = note_pitch.name
        octave = note_pitch.octave

        # Check if music21 representation uses flat (e.g., 'B-')
        if '-' in note_name:
             # Get the enharmonic equivalent that prefers sharps
             enharmonic_pitch = note_pitch.getEnharmonic()
             # Check if the enharmonic uses sharp, prefer that if available
             if '#' in enharmonic_pitch.name:
                  note_name = enharmonic_pitch.name
                  octave = enharmonic_pitch.octave # Octave might change too (e.g. Cb -> B)
             # If enharmonic is natural (e.g. F- -> E), use that
             elif enharmonic_pitch.accidental is None:
                  note_name = enharmonic_pitch.name
                  octave = enharmonic_pitch.octave
             # Else, stick with original name if enharmonic didn't help (shouldn't happen often)

        # Reconstruct the key format (e.g., "C#4", "A3")
        map_key = f"{note_name}{octave}"
        return map_key


    def play_note(self, note_pitch: pitch.Pitch, duration_sec: float, apply_octave_shift: bool, volume: float):
        if not self.is_initialized:
            print("Warning: Sample backend not initialized. Cannot play note.", file=sys.stderr)
            return
            
        # Octave shift is ignored by this backend as we play pre-recorded files
        if apply_octave_shift:
             # Optionally print a warning that shifting is ignored?
             pass 
             
        sample_key = self._get_sample_key(note_pitch)
        
        if sample_key and sample_key in self.samples:
            sound = self.samples[sample_key]
            if sound:
                try:
                    print(f"Playing Sample: {note_pitch.nameWithOctave} -> Key: '{sample_key}' -> File: '{NOTE_SAMPLE_MAP.get(sample_key)}' Vol: {volume:.2f}")
                    sound.set_volume(volume)
                    sound.play()
                except Exception as e:
                    print(f"Error playing sample for key '{sample_key}': {e}", file=sys.stderr)
            else:
                # Sample was missing or failed to load
                print(f"Warning: Sample for '{sample_key}' ({note_pitch.nameWithOctave}) not loaded. Skipping.", file=sys.stderr)
        else:
             print(f"Warning: No sample mapping found for pitch '{note_pitch.nameWithOctave}' (Key: '{sample_key}'). Skipping.", file=sys.stderr)
        
        # Duration is handled by the main playback loop, not the backend playing the sample.

    def play_chord(self, chord_pitches: list[pitch.Pitch], duration_sec: float, apply_octave_shift: bool, volume: float):
        if not self.is_initialized:
            print("Warning: Sample backend not initialized. Cannot play chord.", file=sys.stderr)
            return
        
        notes_played = []
        notes_skipped = []
        for p in chord_pitches:
            sample_key = self._get_sample_key(p)
            if sample_key and sample_key in self.samples:
                sound = self.samples[sample_key]
                if sound:
                     try:
                          sound.set_volume(volume)
                          sound.play()
                          notes_played.append(f"{p.nameWithOctave} ('{sample_key}')")
                     except Exception as e:
                          print(f"Error playing sample for chord note '{sample_key}': {e}", file=sys.stderr)
                          notes_skipped.append(f"{p.nameWithOctave} ('{sample_key}', Error)")
                else:
                     notes_skipped.append(f"{p.nameWithOctave} ('{sample_key}', Missing/LoadErr)")
            else:
                 notes_skipped.append(f"{p.nameWithOctave} (Key '{sample_key}' Invalid)")

        if notes_played:
             print(f"Playing Chord Samples: [ { ' | '.join(notes_played) } ]")
        if notes_skipped:
             print(f"  Skipped Chord Notes: [ { ' | '.join(notes_skipped) } ]")

    def rest(self, duration_sec: float):
        # The backend doesn't need to do anything active for a rest,
        # the main loop just waits.
        print(f"Resting for {duration_sec:.3f}s")
        pass 