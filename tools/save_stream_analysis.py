# save_stream_analysis.py
import os
import sys

try:
    from music21 import (
        articulations,
        chord,
        converter,
        dynamics,
        expressions,
        note,
        spanner,
        stream,
        tempo,
    )
except ImportError:
    print("music21 not found")
    sys.exit(1)

def format_element_info(element):
    """Formats information about a music21 element into a string."""
    info = f"Offset={float(element.offset):<6.2f} "
    info += f"Dur={element.duration.quarterLength:<5.2f} "
    info += f"Class={element.__class__.__name__:<15} "
    if hasattr(element, 'pitches'):
         info += f"Pitches={[p.nameWithOctave for p in element.pitches]} "
    elif hasattr(element, 'pitch'):
         info += f"Pitch={element.pitch.nameWithOctave} "
    # Don't show articulations/expressions for chords after chordify for brevity
    # But show them for the original stream
    if not (isinstance(element, chord.Chord) and element.derivation.method == 'chordify'): 
        if hasattr(element, 'articulations') and element.articulations:
             info += f"Artic={[a.__class__.__name__ for a in element.articulations]} "
        if hasattr(element, 'expressions') and element.expressions:
             expr_strs = []
             for e in element.expressions:
                  expr_str = e.__class__.__name__
                  if isinstance(e, expressions.SustainPedal):
                       expr_str += f"(type={getattr(e, 'type', 'unknown')})"
                  expr_strs.append(expr_str)
             info += f"Expr={expr_strs} "
    if isinstance(element, spanner.Spanner):
         info += f"SpannedIDs={[el.id if hasattr(el, 'id') else repr(el) for el in element.getSpannedElements()]} "
    # Check for tie only if the element might have one (Note, Chord)
    if isinstance(element, (note.Note, chord.Chord)) and element.tie:
         info += f"Tie={element.tie.type} "
    return info.strip()

def save_stream_elements(m21_stream, output_filename):
    """Iterates through a stream's flat elements and saves formatted info to a file."""
    print(f"Saving element info to '{output_filename}'...")
    count = 0
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Element analysis for stream (Source: {getattr(m21_stream, 'filePath', 'In Memory')})\n")
            f.write(f"# Derivation Method: {m21_stream.derivation.method if m21_stream.derivation else 'Original'}\n")
            f.write("---------------------------------------------------\n")
            # Iterate through all elements, not just notes/chords, to see everything
            for element in m21_stream.flat.elements:
                f.write(format_element_info(element) + '\n')
                count += 1
        print(f"Saved {count} elements to '{output_filename}'.")
    except Exception as e:
        print(f"Error writing to {output_filename}: {e}")

if __name__ == "__main__":
    score_file = os.path.join("scores", "Game_Anime", "tiankongzhicheng.mxl") 
    output_original = "tiankong_original_flat.txt"
    output_chordified = "tiankong_chordified_flat.txt"

    if not os.path.exists(score_file):
         print(f"Error: Score file not found at {score_file}")
         sys.exit(1)

    try:
        print(f"Loading score: {score_file}")
        score = converter.parse(score_file)
        score.filePath = score_file # Store filepath for reference in output
        print("Score loaded.")
        
        # Save original flattened stream info
        save_stream_elements(score, output_original)
        
        print("\nChordifying score...")
        score_chordified = score.chordify()
        print("Score chordified.")
        
        # Save chordified flattened stream info
        save_stream_elements(score_chordified, output_chordified)
        
        print("\nAnalysis complete.")

    except Exception as e:
        print(f"An error occurred during the process: {e}")
        sys.exit(1) 