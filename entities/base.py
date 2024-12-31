# worldalpha/entities/base.py
from ursina import Entity, Vec3, raycast, time
from typing import Dict, Tuple, Optional

class GameEntity(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_physics()
        self._setup_collision()

    def _setup_physics(self):
        self.velocity = Vec3(0, 0, 0)
        self.gravity_acceleration = 20.0
        self.terminal_velocity = -50.0
        self.wind_resistance = 0.1  # Higher value = more resistance
        self.grounded = False
        self.collision_height = 1
        self.collision_radius = 0.5
        self.physics_enabled = False  # Flag to control when physics starts

    def _setup_collision(self):
        self.collision_rays = {
            'down': (Vec3(0, -1, 0), 2.1),
            'up': (Vec3(0, 1, 0), 1),
            'body': (Vec3(0, 0, 0), 0.5)
        }

    def check_collision(self, direction: Vec3, distance: float) -> Tuple[bool, Optional[Vec3]]:
        hit_info = raycast(
            self.position + Vec3(0, self.collision_height/2, 0),
            direction,
            distance=distance,
            ignore=[self]
        )
        return hit_info.hit, hit_info.normal if hit_info.hit else None

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
                ignore=[self]
            )
            if hit_info.hit:
                min_distance = min(min_distance, hit_info.distance)
        
        return min_distance if min_distance != float('inf') else None

    def check_head(self):
        hit_info = raycast(
            self.position + Vec3(0, 1, 0),
            self.collision_rays['up'][0],
            distance=self.collision_rays['up'][1],
            ignore=[self]
        )
        return hit_info.distance if hit_info.hit else None

    def handle_physics(self):
        if not self.physics_enabled:
            return

        ground_distance = self.check_ground()
        self.grounded = ground_distance is not None and ground_distance <= 1.1
        
        if not self.grounded:
            # Apply gravity with wind resistance
            drag_force = self.velocity.y * self.velocity.y * self.wind_resistance * (-1 if self.velocity.y > 0 else 1)
            net_acceleration = -self.gravity_acceleration + drag_force
            
            self.velocity.y += net_acceleration * time.dt
            self.velocity.y = max(self.velocity.y, self.terminal_velocity)
            self.y += self.velocity.y * time.dt
        else:
            self.velocity.y = 0
            if ground_distance < 1:
                self.y += (1 - ground_distance)
        
        head_distance = self.check_head()
        if head_distance is not None and head_distance < 0.5:
            self.y -= (0.5 - head_distance)
            self.velocity.y = min(self.velocity.y, 0)

    def move(self, direction: Vec3, speed: float):
        if direction.length() > 0:
            direction = direction.normalized()
            intended_pos = self.position + direction * speed * time.dt
            
            hit, normal = self.check_collision(direction, speed * time.dt)
            if not hit:
                self.position = intended_pos
            else:
                slide_direction = (direction - normal * direction.dot(normal)).normalized()
                if slide_direction.length() > 0:
                    self.position += slide_direction * speed * time.dt * 0.7
