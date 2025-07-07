import json
import os
from typing import List, Optional, Dict, Any, Union

class FixtureChannelCapability:
    def __init__(self, description: str, value: Optional[int] = None,
                 range_min: Optional[int] = None, range_max: Optional[int] = None):
        self.description = description
        self.value = value
        self.range_min = range_min
        self.range_max = range_max

        if self.value is None and (self.range_min is None or self.range_max is None):
            raise ValueError("Capability must have a 'value' or both 'range_min' and 'range_max'.")
        if self.value is not None and (self.range_min is not None or self.range_max is not None):
            raise ValueError("Capability cannot have both 'value' and range ('range_min'/'range_max').")

    def __repr__(self):
        if self.value is not None:
            return f"Capability(value={self.value}, desc='{self.description}')"
        else:
            return f"Capability(range=({self.range_min}-{self.range_max}), desc='{self.description}')"

class FixtureChannel:
    def __init__(self, name: str, type: str, dmx_channel_offset: int,
                 default_value: int = 0, min_value: int = 0, max_value: int = 255,
                 capabilities: Optional[List[FixtureChannelCapability]] = None):
        self.name = name
        self.type = type
        self.dmx_channel_offset = dmx_channel_offset
        self.default_value = default_value
        self.min_value = min_value
        self.max_value = max_value
        self.capabilities: List[FixtureChannelCapability] = capabilities if capabilities else []

    def __repr__(self):
        return f"Channel(name='{self.name}', offset={self.dmx_channel_offset}, type='{self.type}')"

class FixtureDefinition:
    def __init__(self, name: str, manufacturer: str, fixture_type: str,
                 total_channels: int, channels: List[FixtureChannel],
                 schema_version: str = "1.0", filepath: Optional[str] = None):
        self.name = name
        self.manufacturer = manufacturer
        self.type = fixture_type
        self.total_channels = total_channels
        self.channels: List[FixtureChannel] = channels
        self.schema_version = schema_version
        self.filepath = filepath

    def __repr__(self):
        return f"FixtureDef(name='{self.name}', type='{self.type}', channels={self.total_channels})"

    @classmethod
    def from_json_file(cls, filepath: str) -> 'FixtureDefinition':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Fixture definition file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in fixture definition file: {filepath} - {e}")

        schema_version = data.get("schema_version", "1.0")

        parsed_channels: List[FixtureChannel] = []
        raw_channels = data.get("channels", [])
        if not isinstance(raw_channels, list):
            raise ValueError(f"Error in {filepath}: 'channels' must be a list.")

        for ch_data in raw_channels:
            if not isinstance(ch_data, dict):
                raise ValueError(f"Error in {filepath}: Each item in 'channels' must be a dictionary.")

            caps_data = ch_data.get("capabilities", [])
            if not isinstance(caps_data, list):
                raise ValueError(f"Error in {filepath}, channel '{ch_data.get('name')}': 'capabilities' must be a list.")

            parsed_caps: List[FixtureChannelCapability] = []
            for cap_data in caps_data:
                if not isinstance(cap_data, dict):
                    raise ValueError(f"Error in {filepath}, channel '{ch_data.get('name')}': Each capability must be a dictionary.")
                try:
                    parsed_caps.append(FixtureChannelCapability(
                        description=cap_data["description"], # Required
                        value=cap_data.get("value"),
                        range_min=cap_data.get("range_min"),
                        range_max=cap_data.get("range_max")
                    ))
                except KeyError as e:
                    raise ValueError(f"Missing required key 'description' in capability for channel '{ch_data.get('name')}' in {filepath}.")
                except ValueError as e: # Catch errors from FixtureChannelCapability constructor
                    raise ValueError(f"Error parsing capability in file {filepath}, channel '{ch_data.get('name')}': {e}")

            try:
                parsed_channels.append(FixtureChannel(
                    name=ch_data["name"], # Required
                    type=ch_data.get("type", "generic"),
                    dmx_channel_offset=int(ch_data["dmx_channel_offset"]), # Required and must be int
                    default_value=int(ch_data.get("default_value", 0)),
                    min_value=int(ch_data.get("min_value", 0)),
                    max_value=int(ch_data.get("max_value", 255)),
                    capabilities=parsed_caps
                ))
            except KeyError as e:
                raise ValueError(f"Missing required key {e} for a channel in {filepath}.")
            except ValueError as e: # Catch int conversion errors
                 raise ValueError(f"Invalid numeric value for a channel property in {filepath}: {e}")

        fixture_name = data.get("name")
        if not fixture_name:
            raise ValueError(f"Fixture 'name' is missing or empty in {filepath}")

        try:
            total_channels = int(data["total_channels"]) # Required
        except KeyError:
            raise ValueError(f"Fixture 'total_channels' is missing in {filepath}")
        except ValueError:
            raise ValueError(f"Fixture 'total_channels' must be an integer in {filepath}")

        # Stricter validation: if "channels" array is present, its length must match total_channels.
        # If "channels" is not present (or empty), total_channels can be > 0 (e.g. a bank of generic dimmers not individually defined)
        if data.get("channels") is not None: # Check if the key 'channels' exists
            if len(parsed_channels) != total_channels:
                raise ValueError(
                    f"In {filepath}, when 'channels' array is defined, its length ({len(parsed_channels)}) "
                    f"must match 'total_channels' ({total_channels})."
                )
        elif total_channels <= 0 : # If no channels defined, total_channels must be > 0
             raise ValueError(
                    f"In {filepath}, if 'channels' array is not defined or empty, "
                    f"'total_channels' ({total_channels}) must be greater than 0."
                )


        return cls(
            name=fixture_name,
            manufacturer=data.get("manufacturer", "Unknown"),
            fixture_type=data.get("type", "Generic"),
            total_channels=total_channels,
            channels=parsed_channels, # This will be empty if "channels" was not in JSON but total_channels > 0
            schema_version=schema_version,
            filepath=filepath
        )

if __name__ == '__main__':
    # Determine the correct base directory whether running as script or part of a larger project
    try:
        # Assumes the script is in /src and fixtures are in /fixtures at the same level as /src
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        # __file__ is not defined, e.g. in interactive interpreter. Fallback for simple cases.
        base_dir = os.path.abspath(".") # Should resolve to the root when run with `python src/fixture_models.py`
        if not os.path.isdir(os.path.join(base_dir, 'fixtures')): # If 'fixtures' is not in current dir, try one level up
            base_dir_parent = os.path.dirname(base_dir)
            if os.path.isdir(os.path.join(base_dir_parent, 'fixtures')):
                base_dir = base_dir_parent

    fixture_dir = os.path.join(base_dir, 'fixtures')

    print(f"Looking for fixtures in: {os.path.abspath(fixture_dir)}")

    test_files = ['generic_dimmer.json', 'basic_led_par.json']
    loaded_definitions: Dict[str, FixtureDefinition] = {}

    for filename in test_files:
        file_path = os.path.join(fixture_dir, filename)
        print(f"\n--- Loading: {file_path} ---")
        try:
            fixture_def = FixtureDefinition.from_json_file(file_path)
            loaded_definitions[filename] = fixture_def
            print(fixture_def)
            if fixture_def.channels:
                for channel in fixture_def.channels:
                    print(f"  - {channel}")
                    if channel.capabilities:
                        for cap in channel.capabilities:
                            print(f"    - {cap}")
                    else:
                        print(f"    - No capabilities defined for channel '{channel.name}'.")
            else:
                print(f"  - No individual channels defined in JSON (total_channels: {fixture_def.total_channels}).")

            print(f"Successfully loaded {filename}")
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            import traceback
            traceback.print_exc()

    print("\n--- Summary of loaded fixtures ---")
    if loaded_definitions:
        for name, f_def in loaded_definitions.items():
            print(f"'{name}': {f_def.name} by {f_def.manufacturer} ({f_def.total_channels} channels)")
    else:
        print("No fixtures were loaded successfully from the predefined list.")

    print("\n--- Testing edge cases ---")
    # Test loading a non-existent file
    try:
        print("\nAttempting to load a non-existent file:")
        non_existent_file = os.path.join(fixture_dir, "non_existent_fixture.json")
        FixtureDefinition.from_json_file(non_existent_file)
    except FileNotFoundError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"Caught unexpected error for non-existent file: {e}")

    # Test loading a malformed JSON
    malformed_json_path = os.path.join(fixture_dir, "malformed.json")
    with open(malformed_json_path, "w", encoding='utf-8') as f:
        f.write("{'name': 'test',, 'total_channels': 1}") # Invalid JSON: single quotes, extra comma
    try:
        print("\nAttempting to load a malformed JSON file:")
        FixtureDefinition.from_json_file(malformed_json_path)
    except ValueError as e: # Expecting JSONDecodeError which is a subclass or wrapped in ValueError
        print(f"Caught expected error for malformed JSON: {e}")
    except Exception as e:
        print(f"Caught unexpected error for malformed JSON: {e}")
    finally:
        if os.path.exists(malformed_json_path):
            os.remove(malformed_json_path)

    # Test loading JSON with missing required fields (e.g. total_channels)
    missing_fields_path = os.path.join(fixture_dir, "missing_fields.json")
    with open(missing_fields_path, "w", encoding='utf-8') as f:
        f.write(json.dumps({"name": "Incomplete Fixture", "manufacturer": "Test Co"})) # Missing total_channels
    try:
        print("\nAttempting to load JSON with missing required fields:")
        FixtureDefinition.from_json_file(missing_fields_path)
    except ValueError as e:
        print(f"Caught expected error for missing fields: {e}")
    except Exception as e:
        print(f"Caught unexpected error for missing fields: {e}")
    finally:
        if os.path.exists(missing_fields_path):
            os.remove(missing_fields_path)

    # Test JSON with total_channels mismatch vs channels array length
    mismatch_channels_path = os.path.join(fixture_dir, "mismatch_channels.json")
    mismatch_data = {
        "name": "Mismatch Fixture",
        "manufacturer": "Test Co",
        "total_channels": 2, # Stated 2
        "channels": [ # But only 1 defined
            {"name": "Channel 1", "dmx_channel_offset": 0, "type": "generic"}
        ]
    }
    with open(mismatch_channels_path, "w", encoding='utf-8') as f:
        f.write(json.dumps(mismatch_data))
    try:
        print("\nAttempting to load JSON with channel count mismatch:")
        FixtureDefinition.from_json_file(mismatch_channels_path)
    except ValueError as e:
        print(f"Caught expected error for channel count mismatch: {e}")
    except Exception as e:
        print(f"Caught unexpected error for channel count mismatch: {e}")
    finally:
        if os.path.exists(mismatch_channels_path):
            os.remove(mismatch_channels_path)

    print("\nFixture model tests complete.")
