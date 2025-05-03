import abc
import sys

try:
    from music21 import pitch
except ImportError:
    print("Error: music21 library not found.", file=sys.stderr)
    print("Please install it using: pip install music21", file=sys.stderr)
    sys.exit(1)

class PlaybackBackend(abc.ABC):
    """Abstract base class for different playback mechanisms."""

    @abc.abstractmethod
    def start(self):
        """Initialize the backend (if necessary)."""
        pass

    @abc.abstractmethod
    def stop(self):
        """Clean up the backend (if necessary)."""
        pass

    @abc.abstractmethod
    def play_note(self, note_pitch: pitch.Pitch, duration_sec: float, apply_octave_shift: bool, volume: float):
        """Play a single note.

        Args:
            note_pitch: The music21 pitch object to play.
            duration_sec: The duration to hold the note (backend specific interpretation).
            apply_octave_shift: Whether the backend should attempt to shift the octave
                                if the pitch is outside its ideal range.
            volume: The volume level (0.0 to 1.0).
        """
        pass

    @abc.abstractmethod
    def play_chord(self, chord_pitches: list[pitch.Pitch], duration_sec: float, apply_octave_shift: bool, volume: float):
        """Play a chord (multiple notes simultaneously).

        Args:
            chord_pitches: A list of music21 pitch objects in the chord.
            duration_sec: The duration to hold the chord (backend specific interpretation).
            apply_octave_shift: Whether the backend should attempt to shift the octave
                                for pitches outside its ideal range.
            volume: The volume level (0.0 to 1.0).
        """
        pass

    @abc.abstractmethod
    def rest(self, duration_sec: float):
        """Pause for a specified duration (rest)."""
        pass 