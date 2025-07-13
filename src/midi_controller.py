import rtmidi
from typing import Optional

class MidiController:
    def __init__(self, app):
        self.app = app
        self.midi_in = rtmidi.MidiIn()
        self.port: Optional[str] = None
        self.open_port()

    def open_port(self):
        ports = self.midi_in.get_ports()
        if ports:
            try:
                self.midi_in.open_port(0)
                self.port = ports[0]
                self.midi_in.set_callback(self.on_midi_message)
                print(f"MIDI: Opened port '{self.port}'")
            except (rtmidi.InvalidPortError, rtmidi.NoDevicesError) as e:
                print(f"MIDI: Could not open MIDI port: {e}")
        else:
            print("MIDI: No MIDI input devices found.")

    def on_midi_message(self, event, data=None):
        message, deltatime = event
        message_type, note, velocity = message

        # This is a simple mapping for demonstration purposes.
        # A real application would have a more sophisticated mapping system.

        # Map MIDI notes to fixture channels
        if message_type == 0x90: # Note On
            # Map note to fixture and channel
            # This is a very basic example, mapping note to channel 1 of the first fixture
            if self.app.fixture_manager and self.app.fixture_manager.get_all_patched_fixtures():
                fixture = self.app.fixture_manager.get_all_patched_fixtures()[0]
                fixture.set_channel_value_by_offset(0, velocity)
                self.app.update_patched_fixtures_display()
                self.app.apply_patch_to_dmx()

    def close_port(self):
        if self.midi_in.is_port_open():
            self.midi_in.close_port()
            print("MIDI: Closed MIDI port.")
