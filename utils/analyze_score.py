import os
import sys

try:
    from music21 import chord, converter, note, pitch
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

def analyze_pitch_range(file_path):
    """Analyzes the pitch range of a MusicXML file by iterating notes."""
    print(f"Analyzing pitch range for: {file_path}...")
    try:
        score = converter.parse(file_path)
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        return

    min_pitch = None
    max_pitch = None

    try:
        # Iterate through all notes and chords in the flattened score
        for element in score.flat.notes:
            current_pitches = []
            if isinstance(element, note.Note):
                current_pitches.append(element.pitch)
            elif isinstance(element, chord.Chord):
                current_pitches.extend(element.pitches)
            
            for p in current_pitches:
                if min_pitch is None or p.midi < min_pitch.midi:
                    min_pitch = p
                if max_pitch is None or p.midi > max_pitch.midi:
                    max_pitch = p

        if min_pitch is None or max_pitch is None:
             print("No notes found in the score.")
             return

        print("Score Pitch Range:")
        print(f"  Lowest Note:  {min_pitch.nameWithOctave} (MIDI: {min_pitch.midi})")
        print(f"  Highest Note: {max_pitch.nameWithOctave} (MIDI: {max_pitch.midi})")

        # Define the keyboard's approximate MIDI range (C3 to B5)
        min_midi = 48 # C3
        max_midi = 83 # B5
        print(f"\nKeyboard Range (Approx): C3 - B5 (MIDI: {min_midi} - {max_midi})")

        # Check if range is exceeded
        out_of_range = False
        if min_pitch.midi < min_midi:
            print(f"  -> Lowest note ({min_pitch.nameWithOctave}) is BELOW keyboard range.")
            out_of_range = True
        if max_pitch.midi > max_midi:
            print(f"  -> Highest note ({max_pitch.nameWithOctave}) is ABOVE keyboard range.")
            out_of_range = True
        
        if not out_of_range:
            print("  -> Score range appears to be within keyboard range.")

    except Exception as e:
        print(f"Error during pitch analysis: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_score.py <path_to_musicxml_file>")
        sys.exit(1)
    
    score_file = sys.argv[1]
    if not os.path.exists(score_file):
        print(f"Error: File not found: {score_file}", file=sys.stderr)
        sys.exit(1)
        
    analyze_pitch_range(score_file) 