import argparse
import sys

# Check for music21 before other imports that might depend on it indirectly
try:
    import music21
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

# Local imports after checking dependencies
from config import (
    ABS_SCORES_DIRECTORY,
    EXIT_HOTKEY_COMBINATION,
    NEXT_SCORE_HOTKEY_COMBINATION,
    PAUSE_RESUME_HOTKEY_COMBINATION,
    PREV_SCORE_HOTKEY_COMBINATION,
    START_HOTKEY_COMBINATION,
    STOP_HOTKEY_COMBINATION,
)
from hotkey_listener import HotkeyListener
from playback.pynput_backend import PynputKeyboardBackend
from player import Player
from score import scan_scores


def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description='Play MusicXML scores via keyboard simulation with hotkeys.')
    parser.add_argument(
        '-t', '--tolerance',
        type=int,
        default=0,
        help='MIDI steps allowed outside the base range [48, 83] for full score playback. Default is 0 (strict).'
    )
    parser.add_argument(
        '-m', '--mode',
        type=str,
        default='random',
        choices=['random', 'sequential'],
        help='Playback mode: sequential or random (default).'
    )
    args = parser.parse_args()

    # --- Initialization ---
    print("--- Piano Player Initializing ---")
    # Scan for scores initially
    discovered_scores = scan_scores()

    # Initialize Playback Backend
    # In the future, could select different backends here
    playback_backend = PynputKeyboardBackend()

    # Initialize Player Controller
    player = Player(backend=playback_backend,
                    scores=discovered_scores,
                    mode=args.mode,
                    tolerance=args.tolerance)

    # Initialize Hotkey Listener
    listener = HotkeyListener(player=player)

    # --- Print Status and Instructions ---
    print("\n--- Controls ---")
    print(f" Playback Mode:   {args.mode.capitalize()}")
    print(f" Score Tolerance: {args.tolerance}")
    print(f" Scores Directory: '{ABS_SCORES_DIRECTORY}'")
    if discovered_scores:
        print(f" Discovered {len(discovered_scores)} scores.")
    else:
        print("  No scores found.")
    print(f"  {PREV_SCORE_HOTKEY_COMBINATION} / {NEXT_SCORE_HOTKEY_COMBINATION} : Previous / Next track")
    print(f"  {START_HOTKEY_COMBINATION} : Start playback / Resume if paused")
    print(f"  {STOP_HOTKEY_COMBINATION} : Stop playback")
    print(f"  {PAUSE_RESUME_HOTKEY_COMBINATION} : Pause / Resume playback")
    print(f"  {EXIT_HOTKEY_COMBINATION} : Exit application")
    print("----------------")

    # --- Start Listening ---
    listener.start()

    # Keep the main thread alive until the listener stops (e.g., via Exit hotkey)
    # The listener thread will call player.cleanup() when it stops.
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Stopping listener and cleaning up...")
        listener.stop()
        # Player cleanup is triggered by listener stopping

    print("\nApplication exited.")

if __name__ == "__main__":
    main() 