import sys # Voor sys.path aanpassing
import os
import uuid
from typing import List, Dict, Optional

# Voeg src map toe aan sys.path voor directe uitvoering
_SCRIPT_DIR_FM = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR_FM not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR_FM)

from fixture_models import FixtureDefinition # Directe import

class PatchedFixture:
    def __init__(self, definition: FixtureDefinition, start_address: int, name: Optional[str] = None):
        self.id = uuid.uuid4()
        self.definition = definition
        self.name = name if name else definition.name

        if not (1 <= start_address <= (513 - definition.total_channels)):
            raise ValueError(f"Invalid start_address {start_address} for fixture '{definition.name}' "
                             f"with {definition.total_channels} channels. "
                             f"Max start_address is {513 - definition.total_channels}.")
        self.start_address = start_address

        self.channel_values = bytearray(definition.total_channels)
        # Als FixtureDefinition.channels leeg is maar total_channels > 0 (bv. generieke dimmer bank),
        # dan blijven de waarden 0. Anders, gebruik default_value.
        if definition.channels: # Alleen als er daadwerkelijk channel definities zijn
            for i, ch_def in enumerate(definition.channels):
                # Zorg ervoor dat we niet buiten de grenzen van channel_values schrijven
                # als total_channels in JSON kleiner is dan het aantal channel entries (zou niet mogen door validatie)
                if i < len(self.channel_values):
                    self.channel_values[i] = ch_def.default_value
        # else: all channel_values remain 0, which is a safe default.

    def get_dmx_channel_abs(self, fixture_channel_offset: int) -> int:
        if not (0 <= fixture_channel_offset < self.definition.total_channels):
            raise ValueError("Fixture channel offset out of range.")
        return self.start_address + fixture_channel_offset

    def get_channel_value_by_offset(self, fixture_channel_offset: int) -> int:
        if not (0 <= fixture_channel_offset < self.definition.total_channels):
            raise ValueError("Fixture channel offset out of range for getting value.")
        return self.channel_values[fixture_channel_offset]

    def set_channel_value_by_offset(self, fixture_channel_offset: int, value: int):
        if not (0 <= fixture_channel_offset < self.definition.total_channels):
            raise ValueError(f"Fixture channel offset {fixture_channel_offset} out of range for setting value. Max offset: {self.definition.total_channels -1}")
        if not (0 <= value <= 255):
            raise ValueError("DMX value must be between 0 and 255.")
        self.channel_values[fixture_channel_offset] = value

    def get_dmx_values(self) -> Dict[int, int]:
        output_values = {}
        for i in range(self.definition.total_channels):
            abs_address = self.start_address + i
            if abs_address > 512:
                break
            output_values[abs_address] = self.channel_values[i]
        return output_values

    def __repr__(self):
        return (f"PatchedFixture(id={self.id}, name='{self.name}', definition='{self.definition.name}', "
                f"address={self.start_address}, channels={self.definition.total_channels})")


class FixtureManager:
    def __init__(self, fixture_directory: str = "fixtures"):
        self.fixture_definitions: Dict[str, FixtureDefinition] = {}
        self.patched_fixtures: Dict[uuid.UUID, PatchedFixture] = {}

        if not os.path.isabs(fixture_directory):
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.fixture_directory = os.path.join(project_root, fixture_directory)
            except NameError:
                self.fixture_directory = os.path.abspath(fixture_directory)
        else:
            self.fixture_directory = fixture_directory

        self.load_definitions()

    def load_definitions(self):
        self.fixture_definitions.clear()
        if not os.path.isdir(self.fixture_directory):
            print(f"FixtureManager: Directory not found: {self.fixture_directory}")
            return

        print(f"FixtureManager: Loading fixture definitions from {self.fixture_directory}...")
        loaded_count = 0
        potential_files = 0
        for filename in os.listdir(self.fixture_directory):
            if filename.endswith(".json") and not filename.startswith("_"):
                potential_files +=1
                filepath = os.path.join(self.fixture_directory, filename)
                try:
                    definition = FixtureDefinition.from_json_file(filepath)
                    self.fixture_definitions[filepath] = definition
                    print(f"  Loaded: {definition.name} (by {definition.manufacturer}) from {filename}")
                    loaded_count +=1
                except Exception as e:
                    print(f"  Error loading {filename}: {e}")
        print(f"FixtureManager: {loaded_count} of {potential_files} JSON files loaded successfully.")


    def get_available_definitions(self) -> List[FixtureDefinition]:
        return sorted(list(self.fixture_definitions.values()), key=lambda x: (x.manufacturer.lower(), x.name.lower()))


    def get_definition_by_identity(self, identifier: str) -> Optional[FixtureDefinition]:
        # Probeer eerst als een volledig pad (genormaliseerd)
        norm_identifier_path = os.path.normpath(identifier)
        if norm_identifier_path in self.fixture_definitions:
            return self.fixture_definitions[norm_identifier_path]

        # Probeer als een bestandsnaam binnen de fixture_directory
        potential_path = os.path.join(self.fixture_directory, identifier)
        norm_potential_path = os.path.normpath(potential_path)
        if norm_potential_path in self.fixture_definitions:
            return self.fixture_definitions[norm_potential_path]

        # Zoek op naam (minder specifiek)
        for definition in self.fixture_definitions.values():
            if definition.name.lower() == identifier.lower():
                return definition

        # Zoek op "Fabrikant - Naam" (robuuster)
        for definition in self.fixture_definitions.values():
            if f"{definition.manufacturer} - {definition.name}".lower() == identifier.lower():
                return definition
        return None


    def add_fixture_to_patch(self, definition_identifier: str, start_address: int, custom_name: Optional[str] = None) -> Optional[PatchedFixture]:
        definition = self.get_definition_by_identity(definition_identifier)

        if not definition:
            print(f"FixtureManager: Definition not found for '{definition_identifier}'.")
            return None

        new_fixture_end_address = start_address + definition.total_channels - 1
        if new_fixture_end_address > 512:
             print(f"FixtureManager: Cannot patch '{definition.name}'. "
                   f"It requires {definition.total_channels} channels, "
                   f"starting at {start_address} would exceed DMX address 512 (ends at {new_fixture_end_address}).")
             return None

        for pf in self.patched_fixtures.values():
            pf_end_address = pf.start_address + pf.definition.total_channels - 1
            if (start_address <= pf_end_address) and (new_fixture_end_address >= pf.start_address):
                print(f"FixtureManager: Address conflict. Cannot patch '{definition.name}' at {start_address}. "
                      f"Conflicts with '{pf.name}' (Def: {pf.definition.name}) at {pf.start_address}-{pf_end_address}.")
                return None

        try:
            patched_fixture = PatchedFixture(definition, start_address, name=custom_name)
            self.patched_fixtures[patched_fixture.id] = patched_fixture
            print(f"FixtureManager: Patched '{patched_fixture.name}' (Def: {definition.name}) "
                  f"at address {start_address} (ID: {patched_fixture.id}).")
            return patched_fixture
        except ValueError as e:
            print(f"FixtureManager: Error creating PatchedFixture for '{definition.name}': {e}")
            return None

    def remove_fixture_from_patch(self, fixture_id: uuid.UUID) -> bool:
        if fixture_id in self.patched_fixtures:
            removed_fixture = self.patched_fixtures.pop(fixture_id)
            print(f"FixtureManager: Removed '{removed_fixture.name}' (ID: {fixture_id}) from patch.")
            return True
        print(f"FixtureManager: Fixture with ID {fixture_id} not found in patch.")
        return False

    def get_patched_fixture_by_id(self, fixture_id: uuid.UUID) -> Optional[PatchedFixture]:
        return self.patched_fixtures.get(fixture_id)

    def get_all_patched_fixtures(self) -> List[PatchedFixture]:
        return sorted(list(self.patched_fixtures.values()), key=lambda x: x.start_address)


    def apply_patch_to_dmx_controller(self, dmx_controller):
        if not dmx_controller:
            print("FixtureManager: DMXController instance not provided for update.")
            return

        desired_dmx_state = bytearray(512)

        for pf in self.patched_fixtures.values():
            fixture_abs_dmx_values = pf.get_dmx_values()
            for abs_address_1_based, value in fixture_abs_dmx_values.items():
                if 1 <= abs_address_1_based <= 512:
                    desired_dmx_state[abs_address_1_based - 1] = value

        dmx_controller.set_channels(1, list(desired_dmx_state))


if __name__ == '__main__':
    print("FixtureManager Test Script")

    class DummyDMXController:
        def __init__(self):
            self.values = bytearray(512)
            print("DummyDMXController initialized.")
        def set_channel(self, ch, val): self.values[ch-1] = val; print(f"DummyDMX: Ch {ch} set to {val}")
        def set_channels(self, start_ch, vals_list):
            # print(f"DummyDMX: Setting channels from {start_ch} with {len(vals_list)} values.")
            for i, v_val in enumerate(vals_list):
                if (start_ch + i -1) < 512: self.values[start_ch + i - 1] = v_val
        def get_all_values(self): return self.values[:]
        def get_channel(self, ch): return self.values[ch-1]
        def close(self): print("DummyDMXController closed.")

    dummy_controller = DummyDMXController()
    # Test met een expliciet pad voor de fixture directory voor robuustheid in __main__
    # Dit gaat ervan uit dat 'fixtures' in dezelfde map staat als 'src'
    current_script_path = os.path.dirname(os.path.abspath(__file__)) # /app/src
    project_root_path = os.path.dirname(current_script_path) # /app
    test_fixture_dir = os.path.join(project_root_path, "fixtures")
    manager = FixtureManager(fixture_directory=test_fixture_dir)

    print("\n--- Available Definitions ---")
    definitions = manager.get_available_definitions()
    if not definitions:
        print(f"No fixture definitions found in {manager.fixture_directory}. Ensure directory exists and contains .json files.")
    for i, definition in enumerate(definitions):
        print(f"{i+1}. {definition.manufacturer} - {definition.name} ({definition.total_channels} channels)")

    if not definitions:
        print("\nCannot proceed with patching tests as no definitions were loaded.")
        exit(1)

    print("\n--- Patching Fixtures ---")
    dimmer_def_identifier = "Generic Dimmer Channel"
    patched_dimmer1 = manager.add_fixture_to_patch(dimmer_def_identifier, 1, custom_name="Front Light")

    led_par_def_identifier = "basic_led_par.json"
    patched_led1 = manager.add_fixture_to_patch(led_par_def_identifier, 10, custom_name="Wash 1")

    print("\nAttempting to patch with address conflict:")
    manager.add_fixture_to_patch(dimmer_def_identifier, 10)

    print("\nAttempting to patch beyond address 512:")
    manager.add_fixture_to_patch(led_par_def_identifier, 511)

    print("\n--- Current Patch ---")
    for pf_item in manager.get_all_patched_fixtures():
        print(pf_item)

    if patched_dimmer1 and patched_led1:
        print("\n--- Modifying Patched Fixture Values & Updating Controller ---")
        patched_dimmer1.set_channel_value_by_offset(0, 128)
        patched_led1.set_channel_value_by_offset(0, 255)
        patched_led1.set_channel_value_by_offset(1, 100)

        print("Applying patch to Dummy DMX Controller...")
        manager.apply_patch_to_dmx_controller(dummy_controller)

        dimmer_abs_ch = patched_dimmer1.start_address
        led_r_abs_ch = patched_led1.start_address
        led_g_abs_ch = patched_led1.start_address + 1

        print(f"Dummy Controller - Dimmer (Ch {dimmer_abs_ch}): {dummy_controller.get_channel(dimmer_abs_ch)}")
        assert dummy_controller.get_channel(dimmer_abs_ch) == 128
        print(f"Dummy Controller - LED R (Ch {led_r_abs_ch}): {dummy_controller.get_channel(led_r_abs_ch)}")
        assert dummy_controller.get_channel(led_r_abs_ch) == 255
        print(f"Dummy Controller - LED G (Ch {led_g_abs_ch}): {dummy_controller.get_channel(led_g_abs_ch)}")
        assert dummy_controller.get_channel(led_g_abs_ch) == 100
        print(f"Dummy Controller - Unused Channel 5: {dummy_controller.get_channel(5)}")
        assert dummy_controller.get_channel(5) == 0


        print("\n--- Removing a fixture and updating controller ---")
        manager.remove_fixture_from_patch(patched_dimmer1.id)
        print("Applying patch to Dummy DMX Controller after removing dimmer...")
        manager.apply_patch_to_dmx_controller(dummy_controller)

        print(f"Dummy Controller - Dimmer (Ch {dimmer_abs_ch}) after unpatch and update: {dummy_controller.get_channel(dimmer_abs_ch)}")
        assert dummy_controller.get_channel(dimmer_abs_ch) == 0

        print(f"Dummy Controller - LED R (Ch {led_r_abs_ch}) after dimmer unpatch: {dummy_controller.get_channel(led_r_abs_ch)}")
        assert dummy_controller.get_channel(led_r_abs_ch) == 255

    print("\nFixtureManager Test Script Finished.")
