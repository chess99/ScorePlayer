# temporary script to analyze repeated notes
import os
import sys

try:
    from music21 import chord, converter, note, stream
except ImportError:
    print("music21 not found")
    sys.exit(1)

def analyze_repeats(file_path, pitch_focus="F#5"):
    print(f"\n--- Analyzing {pitch_focus} in {os.path.basename(file_path)} ---")
    try:
        score = converter.parse(file_path)
        found_count = 0
        # Iterate through all notes in the score
        # Use score.flat.getElementsByClass([note.Note, chord.Chord]) 
        # as .flat.notes might miss things depending on structure and version
        for element in score.flat.getElementsByClass([note.Note, chord.Chord]): 
            pitches_in_element = []
            is_target_in_element = False
            element_pitch_names = []

            if isinstance(element, note.Note):
                pitches_in_element.append(element.pitch)
                element_pitch_names.append(element.pitch.nameWithOctave)
                if element.pitch.nameWithOctave == pitch_focus:
                    is_target_in_element = True
            elif isinstance(element, chord.Chord):
                pitches_in_element.extend(element.pitches)
                element_pitch_names = [p.nameWithOctave for p in element.pitches]
                if pitch_focus in element_pitch_names:
                     is_target_in_element = True

            if is_target_in_element:
                found_count += 1
                # Record offset, duration, and maybe if it was part of a chord
                duration_ql = element.duration.quarterLength
                tie_info = f"Tie: {element.tie.type}" if element.tie else "Tie: None"
                print(f"  Offset={float(element.offset):<6.2f} Duration={duration_ql:<5.2f} Pitches={element_pitch_names} {tie_info}")

        if found_count == 0:
             print(f"  No instances of {pitch_focus} found as separate Note/Chord objects in the flattened stream.")
        else:
             print(f"  Found {found_count} instances containing {pitch_focus}.")

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")

if __name__ == "__main__":
    # Assuming the script is run from the project root
    score_file = os.path.join("scores", "Canon_in_D.mxl") 
    if not os.path.exists(score_file):
         print(f"Error: Score file not found at {score_file}")
         sys.exit(1)

    analyze_repeats(score_file, "F#5")
    analyze_repeats(score_file, "E5")
