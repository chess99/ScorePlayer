import os
import random
import sys
import threading
import time

# Attempt to import music21 components used here
try:
    from music21 import articulations, chord, dynamics, note, stream, tempo
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

from config import BACKEND_MIDI_RANGES  # Import backend ranges
from playback.base import PlaybackBackend

# Import specific backends for type checking if needed, avoids circular imports
from playback.pynput_backend import PynputKeyboardBackend
from playback.sample_backend import SamplePlaybackBackend

# 导入MIDI后端进行类型检查
try:
    from playback.midi_backend import MidiPlaybackBackend
except ImportError:
    # 如果导入失败，定义一个占位类型以避免运行时错误
    class MidiPlaybackBackend:
        pass
    print("Warning: MidiPlaybackBackend not available for type checking.", file=sys.stderr)
    print("This is not an error if you don't use the midi backend.", file=sys.stderr)

from score import load_and_prepare_score


class Player:
    def __init__(self, backend: PlaybackBackend, scores: list[str], mode: str = 'random', tolerance: int = 0):
        self.backend = backend
        self.playback_mode = mode
        self.tolerance = tolerance
        self.discovered_scores = scores
        self.selected_score_index = -1 # -1 indicates nothing selected/played yet
        self.current_score_path = None

        self.is_playing = False
        self.is_paused = False
        self.playback_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

        # Determine backend range
        self.backend_min_midi = 48 # Default fallback (C3)
        self.backend_max_midi = 83 # Default fallback (B5)
        backend_name = None
        if isinstance(backend, PynputKeyboardBackend):
            backend_name = 'pynput'
        elif isinstance(backend, SamplePlaybackBackend):
            backend_name = 'sample'
        elif isinstance(backend, MidiPlaybackBackend):
            backend_name = 'midi'
        
        if backend_name and backend_name in BACKEND_MIDI_RANGES:
            self.backend_min_midi = BACKEND_MIDI_RANGES[backend_name]['min']
            self.backend_max_midi = BACKEND_MIDI_RANGES[backend_name]['max']
        else:
             print(f"Warning: Could not determine MIDI range for backend type {type(backend)}. Using default C3-B5.", file=sys.stderr)

        print(f"Player initialized with backend MIDI range: {self.backend_min_midi}-{self.backend_max_midi}")
        self.backend.start()

    def _playback_loop(self):
        """The actual playback logic run in a separate thread. Loops automatically on natural finish."""
        print("Playback thread started.")
        playback_should_continue = True

        while playback_should_continue:
            # --- Check if stop requested before starting next song --- 
            if self.stop_event.is_set():
                print("Stop event detected before starting next song.")
                playback_should_continue = False
                break
            
            # --- Ensure we have a score path --- 
            if not self.current_score_path:
                 print("Error: No current score path set. Stopping playback loop.", file=sys.stderr)
                 playback_should_continue = False
                 break

            # --- Inner loop for playing a single score ---
            error_occurred = False
            elements_to_play = None
            apply_shifts = False
            playback_mode_desc = "Unknown"
            bpm = 120.0
            song_finished_naturally = False
            current_volume = 0.6 # Default volume (approx mf)
            
            # 用于跟踪tied notes的字典
            tied_pitches = {}  # pitch.nameWithOctave -> pitch object

            try:
                # Load and prepare score within the thread, passing the backend's range
                elements_to_play, apply_shifts, playback_mode_desc, bpm = \
                    load_and_prepare_score(self.current_score_path,
                                             self.tolerance,
                                             self.backend_min_midi,
                                             self.backend_max_midi)

                if elements_to_play is None:
                    print(f"Failed to load or prepare score '{os.path.basename(self.current_score_path)}'. Aborting playback of this score.")
                    error_occurred = True # Treat loading failure as an error
                else:
                    sec_per_quarter = 60.0 / bpm
                    print(f"Starting playback of '{os.path.basename(self.current_score_path)}' ({playback_mode_desc}, Tempo: {bpm} BPM)")

                    # Iterate through notes and rests
                    for element in elements_to_play:
                        if self.stop_event.is_set():
                            print("Playback stop signal received during score.")
                            break

                        while self.is_paused:
                            if self.stop_event.is_set(): break
                            time.sleep(0.1)
                        if self.stop_event.is_set(): break

                        duration_sec = element.duration.quarterLength * sec_per_quarter
                        
                        # --- Determine wait duration (handling staccato) ---
                        wait_duration_sec = duration_sec # Default to full duration
                        is_staccato = False
                        if hasattr(element, 'articulations'):
                            for art in element.articulations:
                                if isinstance(art, articulations.Staccato):
                                    is_staccato = True
                                    break
                        if is_staccato:
                            wait_duration_sec = duration_sec * 0.5 # Shorten wait for staccato
                            
                        # --- 处理音符和休止符，包括tie信息 ---
                        if isinstance(element, note.Note):
                            # 检查这个音符是否是tied continuation
                            is_tied = (element.pitch.nameWithOctave in tied_pitches)
                            
                            # 检查这个音符是否有tie开始
                            has_tie_start = False
                            if hasattr(element, 'tie') and element.tie:
                                has_tie_start = element.tie.type in ('start', 'continue')
                                
                            # 播放音符，传递tied状态
                            self.backend.play_note(element.pitch, duration_sec, apply_shifts, current_volume, is_tied)
                            
                            # 更新tied音符跟踪字典
                            if has_tie_start:
                                # 标记为tied，供下一个音符使用
                                tied_pitches[element.pitch.nameWithOctave] = element.pitch
                            elif element.pitch.nameWithOctave in tied_pitches and not has_tie_start:
                                # 如果之前是tied但现在不是start/continue，移除
                                del tied_pitches[element.pitch.nameWithOctave]
                                
                        elif isinstance(element, chord.Chord):
                            # 收集当前chord中哪些音符是tied
                            current_tied_pitches = []
                            for p in element.pitches:
                                if p.nameWithOctave in tied_pitches:
                                    current_tied_pitches.append(tied_pitches[p.nameWithOctave])
                            
                            # 播放和弦，传递tied信息
                            self.backend.play_chord(element.pitches, duration_sec, apply_shifts, current_volume, current_tied_pitches)
                            
                            # 更新tied音符跟踪
                            new_tied_pitches = {}
                            
                            # 检查和弦中每个音符的tie状态
                            for note_in_chord in element:
                                if hasattr(note_in_chord, 'tie') and note_in_chord.tie:
                                    has_tie_start = note_in_chord.tie.type in ('start', 'continue')
                                    if has_tie_start:
                                        # 这个音符将延续到下一个音符/和弦
                                        new_tied_pitches[note_in_chord.pitch.nameWithOctave] = note_in_chord.pitch
                            
                            # 更新tied音符字典，仅保留仍然有tie的音符
                            tied_pitches = new_tied_pitches
                            
                        elif isinstance(element, note.Rest):
                            # 休止符不影响tied状态，所有tied音符都保持不变
                            self.backend.rest(duration_sec)
                        else:
                            print(f"Skipping unknown element type: {type(element)}")
                            continue # Skip the wait for unknown elements

                        # Wait for duration (with pause/stop checks)
                        sleep_end_time = time.monotonic() + wait_duration_sec # Use potentially shortened duration
                        while time.monotonic() < sleep_end_time:
                            while self.is_paused:
                                if self.stop_event.is_set(): break
                                time.sleep(0.1)
                            if self.stop_event.is_set(): break
                            time.sleep(min(0.01, max(0, sleep_end_time - time.monotonic())))
                        if self.stop_event.is_set(): break

                    # If the loop finished without being stopped
                    if not self.stop_event.is_set():
                         song_finished_naturally = True

            except ValueError as e:
                print(f"Configuration/Value Error during playback: {e}", file=sys.stderr)
                error_occurred = True
            except Exception as e:
                print(f"Unexpected error during playback loop: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                error_occurred = True
            # No finally block here, decision logic below

            # --- Decide whether to continue after score attempt ---
            if error_occurred:
                print("Playback terminated due to an error.")
                playback_should_continue = False
            elif self.stop_event.is_set():
                print("Playback stopped by user signal.")
                playback_should_continue = False
            elif song_finished_naturally:
                print(f"Song '{os.path.basename(self.current_score_path)}' finished naturally.")
                print("Autoplaying next in 3 seconds...")
                # Wait, but allow interruption by stop_event
                wait_start_time = time.monotonic()
                while time.monotonic() < wait_start_time + 3.0:
                     if self.stop_event.is_set():
                          print("Stop requested during autoplay pause.")
                          playback_should_continue = False
                          break
                     time.sleep(0.1)
                
                if not playback_should_continue: # Stop was requested during pause
                     break # Exit the outer while loop

                # Get next score to continue the loop
                print("Selecting next track for autoplay...")
                next_index = self._get_next_score_index()
                if next_index != -1:
                    self.selected_score_index = next_index
                    self.current_score_path = self.discovered_scores[self.selected_score_index]
                    print(f"Next up: {os.path.basename(self.current_score_path)}")
                    # Let the outer while loop continue
                else:
                    print("Could not determine next score or no scores left. Stopping playback.")
                    playback_should_continue = False
            else:
                 # Should not happen, but safety break
                 print("Unknown playback loop state. Stopping.", file=sys.stderr)
                 playback_should_continue = False

        # --- Cleanup after outer loop finishes ---
        self.is_playing = False
        self.is_paused = False # Ensure pause is reset
        self.current_score_path = None # Clear current path
        # Keep selected_score_index as is, don't reset to -1
        print("Playback thread finished.")

    def _start_thread(self, score_path: str):
        if self.is_playing:
            print("Warning: Playback already in progress. Stopping first.")
            self.stop()

        self.current_score_path = score_path
        print(f"Attempting to play: {os.path.basename(self.current_score_path)} (Index: {self.selected_score_index}) with tolerance {self.tolerance}...")
        try:
            self.stop_event.clear()
            self.is_paused = False # Ensure not starting paused
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.is_playing = True
            self.playback_thread.start()
        except Exception as e:
            print(f"Error starting playback thread: {e}", file=sys.stderr)
            self.is_playing = False
            self.current_score_path = None

    def _get_next_score_index(self) -> int:
        if not self.discovered_scores:
            return -1

        num_scores = len(self.discovered_scores)
        current_idx = self.selected_score_index

        if self.playback_mode == 'random':
            if num_scores == 1:
                return 0
            possible_indices = list(range(num_scores))
            if current_idx >= 0:
                try:
                    if 0 <= current_idx < len(possible_indices):
                         possible_indices.pop(current_idx)
                    else: # Invalid index state, choose from all
                        print(f"Warning: Current index {current_idx} out of bounds. Choosing random from all.")
                except IndexError: # Should not happen with check, but safety
                    pass
            if not possible_indices: # If pop removed the only element
                 possible_indices = list(range(num_scores))
            return random.choice(possible_indices)
        elif self.playback_mode == 'sequential':
            # If index is -1 (initial state), start from 0, otherwise increment
            return (current_idx + 1) % num_scores
        else:
            print(f"Error: Unknown playback mode '{self.playback_mode}'", file=sys.stderr)
            return -1 # Indicate error

    def start_or_resume(self):
        if not self.discovered_scores:
            print("No scores found to play.")
            return

        if self.is_playing:
            if self.is_paused:
                print("Resuming playback...")
                self.is_paused = False
            else:
                print(f"Playback is already running ('{os.path.basename(self.current_score_path or 'Unknown')}'). Press F11 to Pause/Resume, F10 to Stop.")
            return

        # Not playing, start a new track
        score_index_to_play = -1
        if self.selected_score_index >= 0:
            # A track was previously selected by F7/F8, play that one
            print(f"Starting playback of pre-selected track (Index: {self.selected_score_index})...")
            score_index_to_play = self.selected_score_index
        else:
            # No track pre-selected, get the next one based on mode
            print(f"Selecting next track based on '{self.playback_mode}' mode...")
            next_index = self._get_next_score_index()
            if next_index != -1:
                self.selected_score_index = next_index # Update selected index
                score_index_to_play = next_index
            else:
                print("Could not determine next score to play.")

        # Start playback if we determined an index
        if score_index_to_play != -1:
             self._start_thread(self.discovered_scores[score_index_to_play])
        # else: # Already printed error if needed
        #     pass

    def stop(self):
        if not self.is_playing:
            # print("Playback is not running.") # Optional: too noisy?
            return

        print("Stopping playback...")
        self.stop_event.set()
        self.is_paused = False # Clear pause state on stop
        # Don't wait indefinitely, the thread checks the event
        if self.playback_thread and self.playback_thread.is_alive():
            try:
                # Give it a short time to exit gracefully
                self.playback_thread.join(timeout=0.2)
            except Exception as e:
                 print(f"Warning: Error joining playback thread: {e}")
        # State is reset in finally block of _playback_loop

    def pause_resume(self):
        if not self.is_playing:
            print("Nothing is playing to pause/resume.")
            return

        self.is_paused = not self.is_paused
        if self.is_paused:
            print("Playback Paused.")
        else:
            print("Playback Resumed.")

    def _change_track(self, direction: int):
        if not self.discovered_scores:
            print("No scores found to select from.")
            return

        num_scores = len(self.discovered_scores)
        new_index = (self.selected_score_index + direction + num_scores) % num_scores

        print(f"Selecting {'Next' if direction == 1 else 'Previous'} Track (Index: {new_index})...")

        # Stop current playback cleanly before starting next
        if self.is_playing:
             print("Stopping current track...")
             self.stop()
             # Wait briefly to ensure thread finishes if stop didn't join completely
             # time.sleep(0.1) # No longer needed as we don't auto-start

        self.selected_score_index = new_index
        # self._start_thread(self.discovered_scores[self.selected_score_index]) # REMOVED: Don't auto-start
        print(f"Selected: {os.path.basename(self.discovered_scores[self.selected_score_index])}. Press F9 to play.")

    def next_track(self):
        self._change_track(1)

    def prev_track(self):
        self._change_track(-1)

    def update_score_list(self, scores: list[str]):
        self.discovered_scores = scores
        # Reset index if current selection is now invalid? Or keep? Let's keep for now.
        if not self.discovered_scores:
            self.selected_score_index = -1
        elif self.selected_score_index >= len(self.discovered_scores):
             self.selected_score_index = len(self.discovered_scores) -1 # Select last one
        print(f"Player updated with {len(scores)} scores.")

    def cleanup(self):
        print("Cleaning up Player...")
        self.stop() # Ensure playback is stopped
        self.backend.stop()
        print("Player cleanup complete.")
