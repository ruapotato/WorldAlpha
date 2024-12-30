# entities/player.py
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina import Vec3, Vec2, held_keys, mouse, time, raycast, clamp
import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.constants import (
    PLAYER_HEIGHT,
    PLAYER_SPEED,
    PLAYER_JUMP_HEIGHT,
    PLAYER_JUMP_DURATION,
    PLAYER_MOUSE_SENSITIVITY
)

class CustomFirstPersonController(FirstPersonController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_physics()
        self._setup_collision()
        self._setup_movement()
        
    def _setup_physics(self):
        self.gravity = 1
        self.jump_height = PLAYER_JUMP_HEIGHT
        self.jump_duration = PLAYER_JUMP_DURATION
        self.jumping = False
        self.grounded = False
        self.height = PLAYER_HEIGHT
        
    def _setup_collision(self):
        self.collision_rays = {
            'down': (Vec3(0, -1, 0), 2.1),    # Ground check
            'up': (Vec3(0, 1, 0), 1),         # Ceiling check
            'body': (Vec3(0, 0, 0), 0.5)      # Body collision sphere
        }
        
    def _setup_movement(self):
        self.speed = PLAYER_SPEED
        self.mouse_sensitivity = Vec2(*PLAYER_MOUSE_SENSITIVITY)
        
    def check_ground(self):
        positions = [
            self.position,
            self.position + Vec3(0.3, 0, 0.3),
            self.position + Vec3(-0.3, 0, 0.3),
            self.position + Vec3(0.3, 0, -0.3),
            self.position + Vec3(-0.3, 0, -0.3)
        ]
        
        min_distance = float('inf')
        for pos in positions:
            hit_info = raycast(
                pos + Vec3(0, 0.1, 0),
                self.collision_rays['down'][0],
                distance=self.collision_rays['down'][1],
                ignore=[self,]
            )
            if hit_info.hit:
                min_distance = min(min_distance, hit_info.distance)
        
        return min_distance if min_distance != float('inf') else None
    
    def check_head(self):
        hit_info = raycast(
            self.position + Vec3(0, 1, 0),
            self.collision_rays['up'][0],
            distance=self.collision_rays['up'][1],
            ignore=[self,]
        )
        return hit_info.distance if hit_info.hit else None
    
    def update(self):
        self._handle_physics()
        self._handle_movement()
        self._handle_camera()
        
    def _handle_physics(self):
        # Ground check and gravity
        ground_distance = self.check_ground()
        self.grounded = ground_distance is not None and ground_distance <= 1.1
        
        if not self.grounded:
            self.y -= self.gravity * time.dt
        else:
            if ground_distance < 1:
                self.y += (1 - ground_distance)
        
        # Ceiling collisions
        head_distance = self.check_head()
        if head_distance is not None and head_distance < 0.5:
            self.y -= (0.5 - head_distance)
            
    def _handle_movement(self):
        self.direction = Vec3(
            self.forward * (held_keys['w'] - held_keys['s']) +
            self.right * (held_keys['d'] - held_keys['a'])
        ).normalized()
        
        if self.direction:
            intended_pos = self.position + (self.direction * self.speed * time.dt)
            
            hit_info = raycast(
                self.position + Vec3(0, 0.5, 0),
                self.direction,
                distance=self.speed * time.dt + 0.5,
                ignore=[self,]
            )
            
            if hit_info.hit:
                wall_normal = hit_info.normal
                slide_direction = (self.direction - wall_normal * 
                                 self.direction.dot(wall_normal)).normalized()
                
                if slide_direction.length() > 0:
                    self.position += slide_direction * self.speed * time.dt * 0.7
            else:
                self.position = intended_pos
        
        # Jumping
        if self.grounded and held_keys['space']:
            self.y += self.jump_height
            self.jumping = True
            
    def _handle_camera(self):
        self.rotation_y += mouse.velocity[0] * self.mouse_sensitivity[1]
        self.camera_pivot.rotation_x -= mouse.velocity[1] * self.mouse_sensitivity[0]
        self.camera_pivot.rotation_x = clamp(self.camera_pivot.rotation_x, -90, 90)
