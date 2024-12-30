# entities/player.py
from ursina import Vec3, Vec2, held_keys, mouse, time, clamp
from .base import GameEntity
from core.constants import (
    PLAYER_HEIGHT,
    PLAYER_SPEED,
    PLAYER_JUMP_HEIGHT,
    PLAYER_MOUSE_SENSITIVITY
)

class CustomFirstPersonController(GameEntity):
    def __init__(self, **kwargs):
        from ursina import Entity, camera
        super().__init__(**kwargs)
        
        # Create camera pivot
        self.camera_pivot = Entity(parent=self, y=2)
        # Reset camera
        camera.world_position = (0,0,0)
        camera.z = -5
        camera.y = 2
        camera.parent = self.camera_pivot
        camera.fov = 90
        mouse.locked = True
        self._setup_player()

    def _setup_player(self):
        self.speed = PLAYER_SPEED
        self.jump_height = PLAYER_JUMP_HEIGHT
        self.height = PLAYER_HEIGHT
        self.mouse_sensitivity = Vec2(*PLAYER_MOUSE_SENSITIVITY)
        self.jumping = False
        
    def update(self):
        self.handle_physics()
        self._handle_movement()
        self._handle_camera()
        
    def _handle_movement(self):
        self.direction = Vec3(
            self.forward * (held_keys['w'] - held_keys['s']) +
            self.right * (held_keys['d'] - held_keys['a'])
        ).normalized()
        
        if self.direction:
            self.move(self.direction, self.speed)
        
        if self.grounded and held_keys['space']:
            self.y += self.jump_height
            self.jumping = True
            
    def _handle_camera(self):
        self.rotation_y += mouse.velocity[0] * self.mouse_sensitivity[1]
        self.camera_pivot.rotation_x -= mouse.velocity[1] * self.mouse_sensitivity[0]
        self.camera_pivot.rotation_x = clamp(self.camera_pivot.rotation_x, -90, 90)
