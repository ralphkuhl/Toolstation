import time
import threading
from typing import List, Optional
import uuid

from scene_manager import Scene, SceneManager
from fixture_manager import FixtureManager
from dmx_controller import DMXController


class Chaser:
    def __init__(self, name: str, scene_ids: List[uuid.UUID], step_duration: float = 1.0):
        self.id = uuid.uuid4()
        self.name = name
        self.scene_ids = scene_ids
        self.step_duration = step_duration
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.current_step = 0

    def start(self, scene_manager: SceneManager, fixture_manager: FixtureManager, dmx_controller: DMXController):
        if self.is_running:
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run, args=(scene_manager, fixture_manager, dmx_controller), daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        self.thread = None

    def _run(self, scene_manager: SceneManager, fixture_manager: FixtureManager, dmx_controller: DMXController):
        while self.is_running:
            if not self.scene_ids:
                break

            scene_id = self.scene_ids[self.current_step]
            scene = scene_manager.scenes.get(scene_id)

            if scene:
                scene_manager.apply_scene(scene, fixture_manager)
                fixture_manager.apply_patch_to_dmx_controller(dmx_controller)

            self.current_step = (self.current_step + 1) % len(self.scene_ids)
            time.sleep(self.step_duration)

class ChaserManager:
    def __init__(self, chaser_directory: str = "chasers"):
        self.chasers: List[Chaser] = []
        self.chaser_directory = chaser_directory
        # TODO: Add saving and loading chasers from files

    def create_chaser(self, name: str, scenes: List[Scene], step_duration: float) -> Chaser:
        scene_ids = [scene.id for scene in scenes]
        chaser = Chaser(name, scene_ids, step_duration)
        self.chasers.append(chaser)
        return chaser

    def get_chasers(self) -> List[Chaser]:
        return self.chasers
