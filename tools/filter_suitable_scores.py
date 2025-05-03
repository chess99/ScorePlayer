import argparse  # Added for command-line arguments
import os
import shutil
import sys

try:
    from music21 import chord, converter, note, pitch, stream
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
SOURCE_DIR = "scores2"
DEST_DIR = "scores"
MIN_MIDI = 48 # C3
MAX_MIDI = 83 # B5
# --- End Configuration ---

def get_score_range(score_stream):
    """Finds the min and max MIDI pitch in a music21 stream.
       Returns (min_midi, max_midi) or (None, None) if no notes.
    """
    min_midi = float('inf')
    max_midi = float('-inf')
    has_notes = False
    try:
        # Use .flatten().notes to handle nested streams correctly
        notes_iterator = score_stream.flatten().notes
        for element in notes_iterator:
            has_notes = True
            current_pitches = []
            if isinstance(element, note.Note):
                # Skip grace notes as they might have unusual ranges
                if element.duration.isGrace:
                    continue
                current_pitches.append(element.pitch)
            elif isinstance(element, chord.Chord):
                 # Skip grace notes within chords
                if element.duration.isGrace:
                     continue
                current_pitches.extend(element.pitches)
            
            for p in current_pitches:
                if p.midi is not None: # Ensure pitch has a MIDI value
                    min_midi = min(min_midi, p.midi)
                    max_midi = max(max_midi, p.midi)
    except stream.StreamException as e:
        print(f"  - Warning: Error iterating notes in stream: {e}", file=sys.stderr)
        return None, None # Cannot determine range
    except Exception as e:
        print(f"  - Warning: Unexpected error during range analysis: {e}", file=sys.stderr)
        return None, None
        
    if not has_notes or min_midi == float('inf'):
        return None, None # No notes found or only grace notes
    return min_midi, max_midi

def check_and_move_scores(tolerance, include_melody_fallback):
    """Checks scores in SOURCE_DIR and moves suitable ones to DEST_DIR, applying tolerance and fallback."""
    effective_min_midi = MIN_MIDI - tolerance
    effective_max_midi = MAX_MIDI + tolerance
    print(f"Checking scores in '{SOURCE_DIR}'...")
    print(f"Target strict MIDI range: {MIN_MIDI}-{MAX_MIDI} (C3-B5)")
    print(f"Acceptable full score range with tolerance {tolerance}: {effective_min_midi}-{effective_max_midi}")
    print(f"Include melody fallback if full score out of range: {include_melody_fallback}")

    if not os.path.isdir(SOURCE_DIR):
        print(f"Error: Source directory '{SOURCE_DIR}' not found.", file=sys.stderr)
        return

    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"Suitable scores will be moved to '{DEST_DIR}'.")

    moved_count = 0
    skipped_count = 0
    error_count = 0

    for filename in os.listdir(SOURCE_DIR):
        source_path = os.path.join(SOURCE_DIR, filename)
        dest_path = os.path.join(DEST_DIR, filename)

        if filename.lower().endswith(('.mxl', '.musicxml')) and os.path.isfile(source_path):
            print(f"\nChecking: {filename}")
            move_file = False
            move_reason = "Unknown"

            try:
                score = converter.parse(source_path)
                min_full, max_full = get_score_range(score)

                if min_full is None:
                    print("  - Skipped (No notes found)")
                    skipped_count += 1
                    continue

                print(f"  - Full Range: MIDI {min_full} - {max_full}")
                # --- Check 1: Full score within tolerance --- 
                if min_full >= effective_min_midi and max_full <= effective_max_midi:
                    move_file = True
                    move_reason = f"Full score within tolerance {tolerance}"
                
                # --- Check 2: Melody fallback (if enabled and Check 1 failed) ---
                elif include_melody_fallback:
                    print("  - Full score outside tolerance. Checking melody fallback...")
                    if not score.parts:
                         print("  - Skipped (Melody fallback: Score has no parts)")
                         skipped_count += 1
                    else:
                        melody_part = score.parts[0]
                        min_melody, max_melody = get_score_range(melody_part)
                        if min_melody is None:
                            print("  - Skipped (Melody fallback: Part 1 has no notes)")
                            skipped_count += 1
                        else:
                           # If Part 1 has notes, it's considered potentially playable via transposition
                           move_file = True
                           move_reason = "Melody (Part 1) suitable for transposition"
                
                # --- Skipped (If Check 1 failed and Check 2 disabled/failed) ---
                else:
                    reason = []
                    if min_full < effective_min_midi:
                        reason.append(f"too low ({min_full} < {effective_min_midi})")
                    if max_full > effective_max_midi:
                        reason.append(f"too high ({max_full} > {effective_max_midi})")                    
                    print(f"  - Skipped (Outside tolerance: {', '.join(reason)})")
                    skipped_count += 1

                # --- Perform Move --- 
                if move_file:
                    print(f"  - OK ({move_reason}): Moving to '{DEST_DIR}'...")
                    try:
                        shutil.move(source_path, dest_path)
                        moved_count += 1
                    except Exception as move_err:
                        print(f"  - Error moving file: {move_err}", file=sys.stderr)
                        error_count += 1
                        move_file = False # Don't count as moved if error occurs
            
            except Exception as parse_err:
                print(f"  - Error processing file: {parse_err}", file=sys.stderr)
                error_count += 1
        
    print("\nFinished.")
    print(f"Moved: {moved_count}, Skipped: {skipped_count}, Errors: {error_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Filter MusicXML scores based on pitch range. Moves scores where the full range is within C3-B5 +/- tolerance, or optionally, where only Part 1 (melody) can be transposed to fit C3-B5.',
        formatter_class=argparse.RawTextHelpFormatter # Nicer help text formatting
    )
    parser.add_argument(
        '-t', '--tolerance', 
        type=int, 
        default=0, 
        help='MIDI steps allowed outside the base range [48, 83] for FULL score check. \nDefault: 0 (strict C3-B5).'
    )
    parser.add_argument(
        '-m', '--include-melody-fallback', 
        action='store_true', # Makes it a flag, default is False
        help='If the full score is outside the tolerated range, also move the file \nif Part 1 (assumed melody) exists and contains notes (playable via transposition).'
    )
    args = parser.parse_args()

    check_and_move_scores(args.tolerance, args.include_melody_fallback) 