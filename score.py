import os
import statistics  # Import statistics module
import sys

# Attempt to import music21
try:
    from music21 import (
        chord,
        converter,
        interval,
        note,
        pitch,  # Added for type hinting
        stream,
        tempo,
    )
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

from config import (
    DEFAULT_TEMPO_BPM,
)


def scan_scores(directory_path: str) -> list[str]:
    """Scans the specified directory for .mxl and .musicxml files."""
    discovered_scores = []
    try:
        if not os.path.isdir(directory_path):
            try: # Attempt to create if it doesn't exist
                 os.makedirs(directory_path)
                 print(f"Created scores directory: {directory_path}")
            except Exception as create_e:
                 print(f"Error: Scores directory not found and could not be created: {directory_path}", file=sys.stderr)
                 print(f"  Reason: {create_e}", file=sys.stderr)
                 return [] # Return empty list if directory is invalid

        print(f"Scanning for scores in '{directory_path}'...")
        for filename in sorted(os.listdir(directory_path)):
            if filename.lower().endswith(('.mxl', '.musicxml')):
                full_path = os.path.join(directory_path, filename)
                discovered_scores.append(full_path)

        if not discovered_scores:
            print(f"No scores found in '{directory_path}'. Please add .mxl or .musicxml files.")

    except Exception as e:
        print(f"Error scanning scores directory '{directory_path}': {e}", file=sys.stderr)
        discovered_scores = [] # Ensure empty list on error

    return discovered_scores

def get_score_range(score_stream: stream.Stream) -> tuple[int | None, int | None]:
    """Finds the min and max MIDI pitch in a music21 stream."""
    min_midi = float('inf')
    max_midi = float('-inf')
    has_notes = False
    for element in score_stream.flat.notes:
        has_notes = True
        current_pitches: list[pitch.Pitch] = []
        if isinstance(element, note.Note):
            current_pitches.append(element.pitch)
        elif isinstance(element, chord.Chord):
            current_pitches.extend(element.pitches)

        for p in current_pitches:
            if p and p.midi is not None: # Check if pitch and midi are valid
                min_midi = min(min_midi, p.midi)
                max_midi = max(max_midi, p.midi)
            else:
                print(f"Warning: Found element {element} with invalid pitch/midi.", file=sys.stderr)

    if not has_notes:
        return None, None # No notes found

    # If inf values remain, means notes were present but had invalid MIDI
    if min_midi == float('inf') or max_midi == float('-inf'):
        print("Warning: Notes found but unable to determine valid MIDI range.", file=sys.stderr)
        return None, None

    return int(min_midi), int(max_midi)

def get_tempo_bpm(music21_stream: stream.Stream) -> float:
    """Extracts the first tempo marking found in the stream, defaults to DEFAULT_TEMPO_BPM."""
    try:
        mm_marks = music21_stream.flat.getElementsByClass(tempo.MetronomeMark)
        if mm_marks:
            first_mark = mm_marks[0]
            if hasattr(first_mark, 'number') and first_mark.number is not None:
                bpm = first_mark.number
                # Sometimes tempo is stored as text, try converting
                if isinstance(bpm, str):
                    try:
                        bpm = float(bpm)
                    except ValueError:
                        print(f"Warning: Found text tempo '{bpm}' that couldn't be converted to number. Using default.")
                        bpm = float(DEFAULT_TEMPO_BPM)

                if isinstance(bpm, (int, float)) and bpm > 0:
                    print(f"Found tempo: {bpm} BPM")
                    return float(bpm)
                else:
                    print(f"Warning: Found invalid tempo mark ({first_mark}). Using default.")
            else:
                 print(f"Warning: Found MetronomeMark ({first_mark}) but it has no BPM number. Using default.")

        # Fallback if no valid MetronomeMark found
        print(f"No valid tempo found in score, using default: {DEFAULT_TEMPO_BPM} BPM")
        return float(DEFAULT_TEMPO_BPM)
    except Exception as e:
        print(f"Error extracting tempo: {e}. Using default.", file=sys.stderr)
        return float(DEFAULT_TEMPO_BPM)

def load_and_prepare_score(score_path: str, tolerance: int, backend_min_midi: int, backend_max_midi: int) -> tuple[stream.Stream | None, bool, str, float]:
    """Loads a score, determines playback mode (full/melody) based on backend range,
       performs transposition if needed, and returns the elements to play,
       whether to apply individual shifts, the mode description, and tempo.
    """
    elements_to_play = None
    apply_individual_shifts = True
    playback_mode = "Unknown"
    bpm = float(DEFAULT_TEMPO_BPM)
    error_occurred = False

    try:
        print(f"Loading score '{os.path.basename(score_path)}' with music21...")
        score = converter.parse(score_path)
        print("Score loaded.")

        min_full, max_full = get_score_range(score)
        if min_full is None:
             print("Score contains no valid notes. Nothing to play.")
             return None, False, "No Notes", bpm # Return None if no notes

        print(f"Full score range: MIDI {min_full} - {max_full}")
        print(f"Backend supported range: MIDI {backend_min_midi} - {backend_max_midi}")
        effective_min = backend_min_midi - tolerance
        effective_max = backend_max_midi + tolerance

        if min_full >= effective_min and max_full <= effective_max:
            print(f"Full score fits within backend range + tolerance {tolerance}. Playing all parts.")
            # Chordify the score to group simultaneous notes from different parts into chords
            try:
                print("Chordifying score...")
                score = score.chordify()
                print("Score chordified.")
            except Exception as e:
                print(f"Warning: Chordify failed: {e}. Playback might have incorrect simultaneity.", file=sys.stderr)
                # Proceed without chordify if it fails
                
            elements_to_play = score.flat.notesAndRests
            apply_individual_shifts = True # Shift notes slightly outside strict backend range if tolerance > 0
            playback_mode = "Full Score"
        else:
            print("Full score range exceeds backend range + tolerance. Attempting melody (Part 1) playback.")
            if not score.parts:
                print("Error: Score has no parts, cannot extract melody.", file=sys.stderr)
                raise ValueError("Score has no parts")

            melody_part = score.parts[0]
            min_melody, max_melody = get_score_range(melody_part)

            if min_melody is None:
                print("Warning: Part 1 (melody) contains no valid notes. Nothing to play.")
                return None, False, "No Melody Notes", bpm # Return None if no melody notes

            print(f"Melody (Part 1) range: MIDI {min_melody} - {max_melody}")

            # --- New Transposition Logic: Center the melody --- 
            melody_notes = list(melody_part.flat.notes)
            if not melody_notes:
                print("Warning: Part 1 contains no actual notes for transposition analysis.")
                # Keep existing min/max based range check as fallback?
                # Or just return None? Let's return None for simplicity.
                return None, False, "No Melody Notes", bpm
                
            melody_midi_values = []
            for element in melody_notes:
                 if isinstance(element, note.Note):
                      if element.pitch.midi is not None:
                           melody_midi_values.append(element.pitch.midi)
                 elif isinstance(element, chord.Chord):
                      # Use the highest note of the chord for centering analysis? Or lowest? Or average?
                      # Let's use the highest note for now, as it's often the melodic one.
                      # Alternatively, could use average, or all notes.
                      highest_midi_in_chord = float('-inf')
                      has_valid_pitch = False
                      for p in element.pitches:
                           if p.midi is not None:
                                has_valid_pitch = True
                                highest_midi_in_chord = max(highest_midi_in_chord, p.midi)
                      if has_valid_pitch:
                           melody_midi_values.append(highest_midi_in_chord)
                           
            if not melody_midi_values:
                 print("Warning: Could not extract valid MIDI values from Part 1 notes.")
                 return None, False, "No Melody Notes", bpm

            median_midi = statistics.median(melody_midi_values)
            TARGET_CENTER_MIDI = 65 # Target G4 as the center
            transpose_semitones = round(TARGET_CENTER_MIDI - median_midi) # Round to nearest semitone

            print(f"Melody median MIDI: {median_midi:.1f}. Targeting center: {TARGET_CENTER_MIDI}.")
            print(f"Calculated transposition based on median: {transpose_semitones} semitones.")

            # --- Original Transposition Logic (commented out for reference) ---
            # transpose_semitones = 0
            # if min_melody < backend_min_midi:
            #     transpose_semitones = 12 * math.ceil((backend_min_midi - min_melody) / 12.0)
            # elif max_melody > backend_max_midi:
            #     transpose_semitones = -12 * math.ceil((max_melody - backend_max_midi) / 12.0)
            # --- End Original Logic --- 

            if transpose_semitones != 0:
                print(f"Transposing melody by {transpose_semitones} semitones to center on keyboard.")
                transposition_interval = interval.Interval(transpose_semitones)
                melody_part = melody_part.transpose(transposition_interval)
                print("Melody transposed.")
            else:
                 print("Melody median already centered or no transposition needed.")

            elements_to_play = melody_part.flat.notesAndRests
            apply_individual_shifts = True # IMPORTANT: Allow individual shifting for outliers
            playback_mode = f"Melody Only+Centered (Transposed {transpose_semitones})"

        bpm = get_tempo_bpm(score)
        if not isinstance(bpm, (int, float)) or bpm <= 0:
             print(f"Error: Invalid BPM ({bpm}) obtained. Cannot calculate duration.", file=sys.stderr)
             raise ValueError(f"Invalid BPM: {bpm}")

    except stream.StreamException as e:
         print(f"Music21 Error processing score file: {e}", file=sys.stderr)
         error_occurred = True
    except ValueError as e:
        print(f"Configuration Error during score preparation: {e}", file=sys.stderr)
        error_occurred = True
    except Exception as e:
        print(f"Unexpected error during score preparation: {e}", file=sys.stderr)
        error_occurred = True

    if error_occurred or elements_to_play is None:
        return None, False, "Error Loading", float(DEFAULT_TEMPO_BPM)

    return elements_to_play, apply_individual_shifts, playback_mode, bpm 