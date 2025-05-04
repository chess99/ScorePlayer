import argparse
import os
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
    DEFAULT_MIDI_PORT_NAME,
    DEFAULT_SCORES_DIRECTORY,
    EXIT_HOTKEY_COMBINATION,
    NEXT_SCORE_HOTKEY_COMBINATION,
    PAUSE_RESUME_HOTKEY_COMBINATION,
    PREV_SCORE_HOTKEY_COMBINATION,
    START_HOTKEY_COMBINATION,
    STOP_HOTKEY_COMBINATION,
)
from hotkey_listener import HotkeyListener
from playback.pynput_backend import PynputKeyboardBackend

# We'll import other backends conditionally later
from player import Player
from score import scan_scores


def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description='Play MusicXML scores via keyboard simulation or audio samples.')
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
    parser.add_argument(
        '-b', '--backend',
        type=str,
        default='pynput',
        choices=['pynput', 'sample', 'midi'],
        help='Playback backend: pynput (keyboard simulation), sample (audio files), or midi (MIDI output). Default: pynput.'
    )
    parser.add_argument(
        '-d', '--directory',
        type=str,
        default=DEFAULT_SCORES_DIRECTORY,
        help=f'Directory containing MusicXML scores. Default: {DEFAULT_SCORES_DIRECTORY}'
    )
    parser.add_argument(
        '--midi-port',
        type=str,
        default=DEFAULT_MIDI_PORT_NAME,
        help='MIDI port name to use (for midi backend). Default: use first available port or create virtual port.'
    )
    args = parser.parse_args()

    # --- Initialization ---
    print("--- Piano Player Initializing ---")
    
    # Determine actual scores directory and get absolute path
    scores_dir = args.directory
    abs_scores_dir = os.path.abspath(scores_dir)
    print(f"Using scores directory: {abs_scores_dir}")
    
    # Scan for scores initially using the specified directory
    discovered_scores = scan_scores(scores_dir)

    # Initialize Playback Backend based on argument
    playback_backend = None
    if args.backend == 'pynput':
        playback_backend = PynputKeyboardBackend()
    elif args.backend == 'sample':
        try:
            from playback.sample_backend import SamplePlaybackBackend
            playback_backend = SamplePlaybackBackend()
        except ImportError as e:
            print(f"Error importing SamplePlaybackBackend: {e}", file=sys.stderr)
            print("Please ensure pygame is installed ('pip install pygame'). Falling back to pynput.", file=sys.stderr)
            playback_backend = PynputKeyboardBackend() # Fallback
        except Exception as e:
            print(f"Error initializing SamplePlaybackBackend: {e}", file=sys.stderr)
            print("Falling back to pynput backend.", file=sys.stderr)
            playback_backend = PynputKeyboardBackend() # Fallback
    elif args.backend == 'midi':
        try:
            from playback.midi_backend import MidiPlaybackBackend
            playback_backend = MidiPlaybackBackend(port_name=args.midi_port)
        except ImportError as e:
            print(f"Error importing MidiPlaybackBackend: {e}", file=sys.stderr)
            print("Please ensure python-rtmidi is installed ('pip install python-rtmidi'). Falling back to pynput.", file=sys.stderr)
            playback_backend = PynputKeyboardBackend() # Fallback
        except Exception as e:
            print(f"Error initializing MidiPlaybackBackend: {e}", file=sys.stderr)
            print("Falling back to pynput backend.", file=sys.stderr)
            playback_backend = PynputKeyboardBackend() # Fallback
    else: 
        # Should not happen due to argparse choices, but safety first
        print(f"Error: Unknown backend '{args.backend}'. Using pynput.", file=sys.stderr)
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
    print(f" Playback Backend: {args.backend}")
    if args.backend == 'midi' and args.midi_port:
        print(f" MIDI Port: {args.midi_port}")
    print(f" Score Tolerance: {args.tolerance}")
    print(f" Scores Directory: '{abs_scores_dir}'")
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