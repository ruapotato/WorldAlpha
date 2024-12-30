# worldalpha/entities/base.py
from ursina import Entity, Vec3
from typing import Dict, Tuple

class GameEntity(Entity):
    """Base class for all game entities with physics and collision handling"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.velocity = Vec3(0, 0, 0)
        self.grounded = False
        self.collision_shape = 'box'  # or 'sphere', 'capsule', etc.
        self.collision_height = 1
        self.collision_radius = 0.5

    def check_collision(self, direction: Vec3, distance: float) -> bool:
        """Check for collision in given direction"""
        hit_info = raycast(
            self.position + Vec3(0, self.collision_height/2, 0),
            direction,
            distance=distance,
            ignore=[self]
        )
        return hit_info.hit

    def move(self, direction: Vec3, speed: float):
        """Move entity with collision detection"""
        if direction.length() > 0:
            direction = direction.normalized()
            intended_pos = self.position + direction * speed * time.dt
            
            if not self.check_collision(direction, speed * time.dt):
                self.position = intended_pos
            else:
                # Try sliding along walls
                for axis in ['x', 'z']:
                    dir_component = Vec3(0, 0, 0)
                    setattr(dir_component, axis, getattr(direction, axis))
                    if dir_component.length() > 0 and not self.check_collision(
                        dir_component.normalized(),
                        speed * time.dt
                    ):
                        self.position += dir_component.normalized() * speed * time.dt * 0.7
