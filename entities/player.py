from ursina import *
from .base import GameEntity
from core.constants import PLAYER_HEIGHT, PLAYER_SPEED, PLAYER_JUMP_HEIGHT
from math import cos, sin, radians, atan2, degrees

class CharacterController(GameEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create parent entity for camera system
        self.camera_anchor = Entity(parent=scene)  # Changed to scene parent for independent movement
        
        # Camera settings
        self.min_zoom = 2
        self.max_zoom = 12
        self.current_zoom = 6
        self.zoom_speed = 1
        self.camera_height = 2
        self.camera_angle = -20
        self.mouse_sensitivity = 1.8
        
        # Movement settings
        self.speed = PLAYER_SPEED
        self.sprint_multiplier = 1.6
        self.jump_height = PLAYER_JUMP_HEIGHT
        self.height = PLAYER_HEIGHT
        self.rotation_speed = 6
        
        # Ground check settings
        self.ground_offset = 1
        self.ground_ray_distance = 2
        
        # Movement state
        self.sprinting = False
        self.movement_state = 'idle'
        self.desired_rotation = 0
        
        self._setup_camera()
        self._setup_player_model()
        
        # Lock mouse and disable default camera controls
        mouse.locked = True
        camera.ignore_input = True

    def _setup_camera(self):
        camera.parent = self.camera_anchor
        camera.position = (0, 0, -self.current_zoom)
        camera.rotation = (self.camera_angle, 0, 0)
        camera.fov = 90

    def _setup_player_model(self):
        self.model = Entity(
            parent=self,
            model='cube',
            scale=(0.5, 1, 0.5),
            color=color.azure
        )

    def _handle_ground_check(self):
        ray_positions = [
            Vec3(0, 0.1, 0),
            Vec3(0.3, 0.1, 0.3),
            Vec3(-0.3, 0.1, 0.3),
            Vec3(0.3, 0.1, -0.3),
            Vec3(-0.3, 0.1, -0.3)
        ]
        
        min_ground_height = float('-inf')
        for offset in ray_positions:
            hit_info = raycast(
                self.position + offset,
                Vec3(0, -1, 0),
                distance=self.ground_ray_distance,
                ignore=[self]
            )
            if hit_info.hit:
                ground_height = hit_info.world_point.y
                min_ground_height = max(min_ground_height, ground_height)
        
        if min_ground_height > float('-inf'):
            target_y = min_ground_height + self.ground_offset
            self.y = lerp(self.y, target_y, time.dt * 8)
            self.grounded = True
        else:
            self.grounded = False

    def update(self):
        self._handle_ground_check()
        self.handle_physics()
        self._handle_movement()
        self._handle_camera()
        self._update_animation_state()
        
        # Update camera position to follow player
        self.camera_anchor.position = Vec3(
            self.position.x,
            self.position.y + self.camera_height,
            self.position.z
        )

    def _handle_movement(self):
        move_direction = Vec3(0, 0, 0)
        
        # Get input from both WASD and arrow keys
        forward = held_keys['w'] or held_keys['arrow up']
        backward = held_keys['s'] or held_keys['arrow down']
        left = held_keys['a'] or held_keys['arrow left']
        right = held_keys['d'] or held_keys['arrow right']
        
        # Calculate movement relative to camera direction
        # Only use camera's Y rotation for determining movement direction
        camera_y = self.camera_anchor.rotation_y
        
        # Build movement vector based on input
        if forward or backward or left or right:
            # Start with camera's forward vector
            forward_dir = Vec3(
                sin(radians(camera_y)),
                0,
                cos(radians(camera_y))
            )
            # Calculate right vector
            right_dir = Vec3(
                sin(radians(camera_y + 90)),
                0,
                cos(radians(camera_y + 90))
            )
            
            # Combine directions based on input
            if forward:
                move_direction += forward_dir
            if backward:
                move_direction -= forward_dir
            if right:
                move_direction += right_dir
            if left:
                move_direction -= right_dir
            
            # Normalize and apply movement
            if move_direction.length() > 0:
                move_direction = move_direction.normalized()
                
                # Set player rotation to face movement direction
                self.desired_rotation = degrees(atan2(move_direction.x, move_direction.z))
                
                # Apply movement with sprint multiplier if active
                current_speed = self.speed * (self.sprint_multiplier if self.sprinting else 1.0)
                self.move(move_direction, current_speed)
        
        # Smooth rotation to desired angle
        if self.rotation_y != self.desired_rotation:
            self.rotation_y = lerp_angle(self.rotation_y, self.desired_rotation, time.dt * self.rotation_speed)
        
        # Handle jumping
        if self.grounded and held_keys['space']:
            self.velocity.y = self.jump_height
            self.jumping = True
            self.grounded = False

    def _handle_camera(self):
        if mouse.locked:
            # Only rotate camera based on mouse movement
            self.camera_anchor.rotation_y += mouse.velocity[0] * self.mouse_sensitivity
            
            # Update camera pitch with clamping
            new_rotation_x = camera.world_rotation_x - mouse.velocity[1] * self.mouse_sensitivity
            camera.world_rotation_x = clamp(new_rotation_x, -60, -5)
            
            # Handle camera collision
            hit_info = raycast(
                self.camera_anchor.world_position,
                camera.back,
                distance=self.current_zoom,
                ignore=[self]
            )
            
            if hit_info.hit:
                camera.z = -hit_info.distance + 0.5
            else:
                camera.z = lerp(camera.z, -self.current_zoom, time.dt * 10)

    def _update_animation_state(self):
        if not self.grounded:
            self.movement_state = 'jumping'
        elif any([held_keys['w'], held_keys['s'], held_keys['a'], held_keys['d'],
                 held_keys['arrow up'], held_keys['arrow down'],
                 held_keys['arrow left'], held_keys['arrow right']]):
            self.movement_state = 'running' if self.sprinting else 'walking'
        else:
            self.movement_state = 'idle'

    def input(self, key):
        if key == 'scroll up':
            self.current_zoom = max(self.min_zoom, self.current_zoom - self.zoom_speed)
        elif key == 'scroll down':
            self.current_zoom = min(self.max_zoom, self.current_zoom + self.zoom_speed)
        elif key == 'left shift':
            self.sprinting = True
        elif key == 'left shift up':
            self.sprinting = False
        elif key == 'escape':
            mouse.locked = not mouse.locked

def lerp_angle(start, end, t):
    """Interpolate between angles, taking the shortest path."""
    diff = ((end - start + 180) % 360) - 180
    return start + diff * t
