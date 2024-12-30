# worldalpha/core/constants.py

VIEW_DISTANCE = 10
CHUNK_SIZE = 4
PLAYER_HEIGHT = 2
PLAYER_SPEED = 8
PLAYER_JUMP_HEIGHT = 2
PLAYER_JUMP_DURATION = 0.5
PLAYER_MOUSE_SENSITIVITY = (40, 40)


# Physics settings
GRAVITY = 9.81

class WorldAlphaGame:
    def __init__(self):
        self.app = Ursina()
        self.biome_manager = BiomeManager()
        self.chunks = {}
        self.setup_game()
        
    def setup_game(self):
        self._setup_lighting()
        self._setup_chunks()
        self._spawn_player()
        self._setup_ui()
        self._setup_camera()
        
    def _setup_lighting(self):
        DirectionalLight(y=2, z=3, rotation=(45, -45, 45))
        AmbientLight(color=color.rgba(0.6, 0.6, 0.6, 1))
        
    def _setup_chunks(self):
        for x in range(-VIEW_DISTANCE, VIEW_DISTANCE + 1):
            for z in range(-VIEW_DISTANCE, VIEW_DISTANCE + 1):
                chunk = TerrainChunk(
                    position=Vec3(x * CHUNK_SIZE, 0, z * CHUNK_SIZE),
                    chunk_size=CHUNK_SIZE,
                    biome_manager=self.biome_manager
                )
                self.chunks[(x, z)] = chunk
                
    def _spawn_player(self):
        center_chunk = self.chunks.get((0, 0))
        if center_chunk:
            spawn_height = center_chunk.generate_heightmap(0, 0)[CHUNK_SIZE//2][CHUNK_SIZE//2]
        else:
            spawn_height = 100
            
        self.player = CustomFirstPersonController(
            position=Vec3(0, spawn_height + 2, 0),
        )
        
    def _setup_ui(self):
        self.fps_text = Text(text='FPS: 0', position=(-.85, .45))
        
    def _setup_camera(self):
        camera.clip_plane_near = 1
        camera.clip_plane_far = CHUNK_SIZE * VIEW_DISTANCE
        scene.fog_density = 0.02
        scene.fog_color = color.rgb(0.7, 0.7, 0.8)
        mouse.locked = True
        
    def update(self):
        self.fps_text.text = f'FPS: {int(1/time.dt)}'
        self._update_chunks()
        
    def _update_chunks(self):
        player_chunk_x = int(self.player.x // CHUNK_SIZE)
        player_chunk_z = int(self.player.z // CHUNK_SIZE)
        
        # Load new chunks
        for x in range(player_chunk_x - VIEW_DISTANCE, player_chunk_x + VIEW_DISTANCE + 1):
            for z in range(player_chunk_z - VIEW_DISTANCE, player_chunk_z + VIEW_DISTANCE + 1):
                if (x, z) not in self.chunks:
                    chunk = TerrainChunk(
                        position=Vec3(x * CHUNK_SIZE, 0, z * CHUNK_SIZE),
                        chunk_size=CHUNK_SIZE,
                        biome_manager=self.biome_manager
                    )
                    self.chunks[(x, z)] = chunk
        
        # Remove distant chunks
        chunks_to_remove = []
        for chunk_pos, chunk in self.chunks.items():
            dx = abs(chunk_pos[0] - player_chunk_x)
            dz = abs(chunk_pos[1] - player_chunk_z)
            if dx > VIEW_DISTANCE or dz > VIEW_DISTANCE:
                chunks_to_remove.append(chunk_pos)
        
        for pos in chunks_to_remove:
            self.chunks[pos].disable()
            del self.chunks[pos]
            
    def run(self):
        self.app.run()

def main():
    game = WorldAlphaGame()
    game.run()

if __name__ == "__main__":
    main()
