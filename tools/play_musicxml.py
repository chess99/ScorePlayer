import os
import tempfile

import music21
import pygame


def play_musicxml(file_path):
    """
    Parses a MusicXML file, converts it to MIDI, and plays it using pygame.

    Args:
        file_path (str): The path to the MusicXML file (.mxl or .musicxml).
    """
    try:
        # Load the MusicXML file
        print(f"Loading MusicXML file: {file_path}...")
        score = music21.converter.parse(file_path)
        print("MusicXML file loaded successfully.")

        # Convert to MIDI
        print("Converting to MIDI...")
        # mf = music21.midi.translate.streamToMidiFile(score) # Old way

        # Use a temporary file for the MIDI data
        # Create a temporary file first
        # temp_midi_fd, temp_midi_path = tempfile.mkstemp(suffix='.mid')
        # os.close(temp_midi_fd) # Close the file descriptor, MidiFile handles opening/closing

        # print(f"Attempting to write MIDI to temporary file: {temp_midi_path}")
        # # Create a MidiFile object
        # mf = music21.midi.MidiFile()
        # mf.open(temp_midi_path, 'wb') # Open in binary write mode
        # mf.write(score) # Write the score stream to the MIDI file
        # mf.close()
        # midi_filename = temp_midi_path # Use the path from mkstemp
        # print(f"MIDI data written to temporary file: {midi_filename}")

        # Try streamToMidiFile again, but check the result and handle temp file correctly
        mf = music21.midi.translate.streamToMidiFile(score)
        if mf is None:
            print("Error: Failed to convert score to MIDI stream.")
            return

        # Get a temporary file path
        temp_midi_fd, temp_midi_path = tempfile.mkstemp(suffix='.mid')
        os.close(temp_midi_fd) # Close the descriptor, midiFile handles the file path

        try:
            mf.open(temp_midi_path, 'wb')
            mf.write()
            mf.close()
            midi_filename = temp_midi_path
            print(f"MIDI data written to temporary file: {midi_filename}")
        except Exception as e:
            print(f"Error writing MIDI data to temporary file: {e}")
            os.remove(temp_midi_path) # Clean up the temp file if writing failed
            return

        # Initialize pygame mixer
        print("Initializing pygame mixer...")
        pygame.mixer.init()
        print("Pygame mixer initialized.")

        # Load and play the MIDI file
        try:
            pygame.mixer.music.load(midi_filename)
            print(f"Playing MIDI file: {midi_filename}...")
            pygame.mixer.music.play()

            # Keep the script running while music plays
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10) # Check every 100ms

        except pygame.error as e:
            print(f"Error playing MIDI file: {e}")
            print("Please ensure you have a MIDI synthesizer configured for pygame.")
            print("On some systems (like Windows), this works out of the box.")
            print("On Linux, you might need to install timidity or fluidsynth.")
        finally:
            # Stop the music and quit the mixer
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            print("Playback finished.")

        # Clean up the temporary MIDI file
        os.remove(midi_filename)
        print(f"Temporary MIDI file {midi_filename} removed.")

    except music21.converter.ConverterException as e:
        print(f"Error loading or parsing MusicXML file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Specify the path to your MusicXML file here
    musicxml_file = r"scores3\Because_of_you__Kelly_Clarkson_Because_of_You_Kelly_Clarkson_flute.mxl"

    if not os.path.exists(musicxml_file):
        print(f"Error: File not found at {musicxml_file}")
    else:
        play_musicxml(musicxml_file) 