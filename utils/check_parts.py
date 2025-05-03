import os
import sys

try:
    from music21 import converter
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

def analyze_score_structure(file_path):
    """Analyzes the part structure of a MusicXML file."""
    print(f"Analyzing structure for: {file_path}...")
    try:
        score = converter.parse(file_path)
        print("Score parsed successfully.")
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        return

    try:
        num_parts = len(score.parts)
        print(f"Number of parts found: {num_parts}")

        if num_parts > 0:
            print("Part details:")
            for i, part in enumerate(score.parts):
                part_id = part.id if hasattr(part, 'id') else 'N/A'
                part_name = part.partName if hasattr(part, 'partName') and part.partName else 'Unnamed'
                print(f"  Part {i+1}: ID='{part_id}', Name='{part_name}'")
        else:
            print("No distinct parts found within the score structure.")

    except Exception as e:
        print(f"Error analyzing parts: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_parts.py <path_to_musicxml_file>")
        sys.exit(1)
    
    score_file = sys.argv[1]
    if not os.path.exists(score_file):
        print(f"Error: File not found: {score_file}", file=sys.stderr)
        sys.exit(1)
        
    analyze_score_structure(score_file) 