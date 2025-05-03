import os
import sys

try:
    from music21 import chord, converter, note, pitch
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

def dump_pitches(input_path, output_path):
    """Parses a MusicXML file and writes all pitch names+MIDI to an output file."""
    print(f"Parsing score: {input_path}...")
    try:
        score = converter.parse(input_path)
        print("Score parsed. Extracting pitches...")
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        return

    pitches_found = []
    try:
        # Iterate through all notes and chords in the flattened score
        for element in score.flat.notes:
            if isinstance(element, note.Note):
                p = element.pitch
                pitches_found.append(f"{p.nameWithOctave} (MIDI: {p.midi})")
            elif isinstance(element, chord.Chord):
                for p in element.pitches:
                    pitches_found.append(f"{p.nameWithOctave} (MIDI: {p.midi})")
        
        print(f"Found {len(pitches_found)} note events.")

        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Pitch List Extracted from: " + os.path.basename(input_path) + "\n")
            f.write("# Format: StandardNameWithOctave (MIDI: MIDINumber)\n")
            f.write("----------------------------------------------------\n")
            for pitch_info in pitches_found:
                f.write(pitch_info + '\n')
        
        print(f"Pitch list saved to: {output_path}")

    except Exception as e:
        print(f"Error extracting or writing pitches: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dump_pitches.py <path_to_musicxml_file> [output_file]")
        sys.exit(1)
    
    score_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "temp_extracted_pitches.txt"

    if not os.path.exists(score_file):
        print(f"Error: Input file not found: {score_file}", file=sys.stderr)
        sys.exit(1)
        
    dump_pitches(score_file, output_file) 