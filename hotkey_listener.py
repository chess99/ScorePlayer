import sys
import threading

from pynput import keyboard

from config import (
    EXIT_HOTKEY_COMBINATION,
    NEXT_SCORE_HOTKEY_COMBINATION,
    PAUSE_RESUME_HOTKEY_COMBINATION,
    PREV_SCORE_HOTKEY_COMBINATION,
    START_HOTKEY_COMBINATION,
    STOP_HOTKEY_COMBINATION,
)
from player import Player


class HotkeyListener:
    def __init__(self, player: Player):
        self.player = player
        self.current_pressed_keys = set()
        self.listener_thread: threading.Thread | None = None
        self._stop_listening = threading.Event()
        self._listener_instance: keyboard.Listener | None = None

    def _on_press(self, key):
        """Callback for key press events."""
        self.current_pressed_keys.add(key)

    def _on_release(self, key):
        """Callback for key release events. Handles hotkey logic."""
        pressed_combination = frozenset(self.current_pressed_keys)

        action_taken = False
        if pressed_combination == PREV_SCORE_HOTKEY_COMBINATION:
            print("Hotkey: Previous Track")
            self.player.prev_track()
            action_taken = True
        elif pressed_combination == NEXT_SCORE_HOTKEY_COMBINATION:
            print("Hotkey: Next Track")
            self.player.next_track()
            action_taken = True
        elif pressed_combination == START_HOTKEY_COMBINATION:
            # Player's start_or_resume handles both starting and resuming
            print("Hotkey: Start/Resume")
            self.player.start_or_resume()
            action_taken = True
        elif pressed_combination == STOP_HOTKEY_COMBINATION:
            print("Hotkey: Stop")
            self.player.stop()
            action_taken = True
        elif pressed_combination == PAUSE_RESUME_HOTKEY_COMBINATION:
            print("Hotkey: Pause/Resume Toggle")
            self.player.pause_resume()
            action_taken = True
        elif pressed_combination == EXIT_HOTKEY_COMBINATION:
            print("Hotkey: Exit")
            self.stop() # Signal the listener loop to stop
            action_taken = True

        # Cleanup the released key
        try:
            self.current_pressed_keys.remove(key)
        except KeyError:
            # Key might have been released programmatically or missed
            pass
        # Optional: If an action was taken, clear all pressed keys
        # This prevents issues if modifier keys were part of the combo
        # and weren't released exactly simultaneously.
        # if action_taken:
        #    self.current_pressed_keys.clear()


    def _run_listener(self):
        """Internal method to run the listener loop."""
        print("Starting pynput listener...")
        try:
            self._listener_instance = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self._listener_instance.start()
            print("pynput listener started.")
            # Keep this thread alive until stop is called
            self._listener_instance.join()
        except Exception as e:
            print(f"Error in hotkey listener thread: {e}", file=sys.stderr)
            # Attempt to stop gracefully if instance exists
            if self._listener_instance:
                try:
                    self._listener_instance.stop()
                except Exception as stop_e:
                     print(f"Error trying to stop listener after error: {stop_e}", file=sys.stderr)
        finally:
            print("pynput listener stopped.")
            # Signal player cleanup if listener stops unexpectedly or normally
            print("Requesting player cleanup...")
            self.player.cleanup() # Request player cleanup when listener stops

    def start(self):
        """Starts the keyboard listener in a separate thread."""
        if self.listener_thread and self.listener_thread.is_alive():
            print("Listener already running.")
            return
        self._stop_listening.clear()
        self.listener_thread = threading.Thread(target=self._run_listener, daemon=True)
        self.listener_thread.start()

    def stop(self):
        """Stops the keyboard listener thread."""
        if not self.listener_thread or not self.listener_thread.is_alive():
            print("Listener not running.")
            return

        print("Stopping hotkey listener...")
        self._stop_listening.set()
        if self._listener_instance:
             try:
                # This is the correct way to stop a pynput listener from another thread
                keyboard.Listener.stop(self._listener_instance)
             except Exception as e:
                 print(f"Error sending stop signal to pynput listener: {e}")
        # Wait briefly for the thread to potentially exit after stop signal
        # self.listener_thread.join(timeout=0.5)
        # Don't join here, let the finally block in _run_listener handle cleanup

    def join(self):
        """Waits for the listener thread to complete."""
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join() 