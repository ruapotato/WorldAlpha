# main.py
from ursina import *
from terrain.chunk import TerrainChunk
from terrain.biomes import BiomeManager
from entities.player import CustomFirstPersonController
from core.constants import VIEW_DISTANCE, CHUNK_SIZE
from terrain.chunk_manager import ChunkManager
import math
import time

class WorldAlpha(Entity):
    def __init__(self):
        super().__init__()
        print("Initializing WorldAlpha...")
        self.app = Ursina()
        self.biome_manager = BiomeManager()
        self.chunk_manager = ChunkManager(CHUNK_SIZE, self.biome_manager)
        self.frame_counter = 0
        self.last_time = time.time()
        self.setup_game()

    def setup_game(self):
        print("Setting up game...")
        self._setup_lighting()
        self._setup_initial_chunks()
        self._spawn_player()
        self._setup_ui()
        self._setup_camera()
        print("Game setup complete!")

    def _setup_lighting(self):
        DirectionalLight(y=2, z=3, rotation=(45, -45, 45))
        AmbientLight(color=color.rgba(0.6, 0.6, 0.6, 1))

    def _setup_initial_chunks(self):
        print("Setting up initial chunks...")
        # Load immediate vicinity for faster startup
        for x in range(-2, 3):
            for z in range(-2, 3):
                chunk_pos = (x, z)
                distance = math.sqrt(x*x + z*z)
                self.chunk_manager.request_chunk(chunk_pos, distance)
        
        # Process initial chunks
        for _ in range(10):  # Process a few frames worth of chunks immediately
            self.chunk_manager.process_queued_chunks()
        
        print("Initial chunks requested")

    def _spawn_player(self):
        print("Spawning player...")
        # Get center chunk height if available
        center_chunk = self.chunk_manager.chunks.get((0, 0))
        if center_chunk and hasattr(center_chunk, 'get_height_at'):
            spawn_height = center_chunk.get_height_at(CHUNK_SIZE//2, CHUNK_SIZE//2)
        else:
            spawn_height = 100
            
        self.player = CustomFirstPersonController(
            position=Vec3(0, spawn_height + 2, 0),
        )
        print(f"Player spawned at height: {spawn_height}")

    def _setup_ui(self):
        print("Setting up UI...")
        self.fps_text = Text(text='FPS: 0', position=(-.85, .45))
        self.chunk_text = Text(text='Chunk: (0, 0)', position=(-.85, .4))
        self.debug_text = Text(text='Debug: None', position=(-.85, .35))
        self.loading_text = Text(text='', position=(0, .45))

    def _setup_camera(self):
        camera.clip_plane_near = 1
        camera.clip_plane_far = CHUNK_SIZE * (VIEW_DISTANCE + 1)
        scene.fog_density = 0.03
        scene.fog_color = color.rgb(0.7, 0.7, 0.8)
        mouse.locked = True

    def _calculate_fps(self):
        current_time = time.time()
        dt = current_time - self.last_time
        self.frame_counter += 1
        
        if dt >= 1.0:
            fps = self.frame_counter / dt
            self.fps_text.text = f'FPS: {int(fps)}'
            self.frame_counter = 0
            self.last_time = current_time

    def _get_chunk_priority(self, chunk_pos, player_chunk):
        dx = chunk_pos[0] - player_chunk[0]
        dz = chunk_pos[1] - player_chunk[1]
        return math.sqrt(dx*dx + dz*dz)

    def update(self):
        self._calculate_fps()
        
        if not hasattr(self, 'player') or not self.player:
            self.debug_text.text = 'Debug: No player found'
            return

        # Update player position info
        x, y, z = self.player.position
        current_chunk_x = int(x // CHUNK_SIZE)
        current_chunk_z = int(z // CHUNK_SIZE)
        
        # Update UI
        self.debug_text.text = f'Debug: Pos({x:.1f}, {y:.1f}, {z:.1f})'
        self.chunk_text.text = f'Chunk: ({current_chunk_x}, {current_chunk_z})'
        
        # Get stats if available
        stats = self.chunk_manager.get_stats()
        if stats:
            self.loading_text.text = (f'Chunks: {stats["chunks_loaded"]} loaded, '
                                    f'{stats["chunks_in_generation"]} generating')
        
        # Request chunks in spiral pattern for more even loading
        chunk_requests = []
        for distance in range(VIEW_DISTANCE + 1):
            for dx in range(-distance, distance + 1):
                for dz in [-distance, distance]:
                    chunk_x = current_chunk_x + dx
                    chunk_z = current_chunk_z + dz
                    dist = math.sqrt(dx*dx + dz*dz)
                    if dist <= VIEW_DISTANCE:
                        chunk_requests.append((dist, (chunk_x, chunk_z)))
                        
            for dz in range(-distance + 1, distance):
                for dx in [-distance, distance]:
                    chunk_x = current_chunk_x + dx
                    chunk_z = current_chunk_z + dz
                    dist = math.sqrt(dx*dx + dz*dz)
                    if dist <= VIEW_DISTANCE:
                        chunk_requests.append((dist, (chunk_x, chunk_z)))
        
        # Sort by distance and request
        chunk_requests.sort()  # Sort by distance
        for dist, chunk_pos in chunk_requests:
            self.chunk_manager.request_chunk(chunk_pos, dist)
        
        # Process chunk updates
        self.chunk_manager.process_queued_chunks()
        
        # Remove distant chunks
        self.chunk_manager.remove_distant_chunks(current_chunk_x, current_chunk_z, VIEW_DISTANCE)

    def input(self, key):
        if key == 'escape':
            print("Escape pressed - exiting...")
            application.quit()

    def run(self):
        print("Starting game loop...")
        self.app.run()

if __name__ == "__main__":
    print("Starting WorldAlpha...")
    world = WorldAlpha()
    world.run()
