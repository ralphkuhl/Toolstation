import json
import os
from typing import Dict, List, Optional
import uuid

from fixture_manager import FixtureManager, PatchedFixture


class Scene:
    def __init__(self, name: str, fixture_states: Dict[uuid.UUID, bytearray]):
        self.id = uuid.uuid4()
        self.name = name
        self.fixture_states = fixture_states

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "fixture_states": {str(k): list(v) for k, v in self.fixture_states.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict):
        fixture_states = {uuid.UUID(k): bytearray(v) for k, v in data["fixture_states"].items()}
        scene = cls(data["name"], fixture_states)
        scene.id = uuid.UUID(data["id"])
        return scene


class SceneManager:
    def __init__(self, scene_directory: str = "scenes"):
        self.scenes: Dict[uuid.UUID, Scene] = {}
        if not os.path.isabs(scene_directory):
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.scene_directory = os.path.join(project_root, scene_directory)
            except NameError:
                self.scene_directory = os.path.abspath(scene_directory)
        else:
            self.scene_directory = scene_directory

        os.makedirs(self.scene_directory, exist_ok=True)
        self.load_scenes()

    def create_scene(self, name: str, fixture_manager: FixtureManager) -> Scene:
        fixture_states = {}
        for fixture in fixture_manager.get_all_patched_fixtures():
            fixture_states[fixture.id] = fixture.channel_values

        scene = Scene(name, fixture_states)
        self.scenes[scene.id] = scene
        self.save_scene(scene)
        return scene

    def save_scene(self, scene: Scene):
        filepath = os.path.join(self.scene_directory, f"{scene.id}.json")
        with open(filepath, "w") as f:
            json.dump(scene.to_dict(), f, indent=4)

    def load_scenes(self):
        if not os.path.isdir(self.scene_directory):
            return

        for filename in os.listdir(self.scene_directory):
            if filename.endswith(".json"):
                filepath = os.path.join(self.scene_directory, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        scene = Scene.from_dict(data)
                        self.scenes[scene.id] = scene
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error loading scene from {filepath}: {e}")

    def get_scenes(self) -> List[Scene]:
        return list(self.scenes.values())

    def apply_scene(self, scene: Scene, fixture_manager: FixtureManager):
        for fixture_id, channel_values in scene.fixture_states.items():
            fixture = fixture_manager.get_patched_fixture_by_id(fixture_id)
            if fixture:
                fixture.channel_values = channel_values
