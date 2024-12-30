# worldalpha/physics/collision.py
from ursina import Vec3, raycast
from typing import List, Tuple, Optional

class CollisionSystem:
    @staticmethod
    def check_collision(
        position: Vec3,
        direction: Vec3,
        distance: float,
        ignore_entities: List = None
    ) -> Tuple[bool, Optional[Vec3]]:
        """
        Check for collision and return hit status and normal if hit
        """
        hit_info = raycast(
            position,
            direction,
            distance=distance,
            ignore=ignore_entities or []
        )
        return hit_info.hit, hit_info.normal if hit_info.hit else None

    @staticmethod
    def calculate_slide_vector(
        movement_direction: Vec3,
        surface_normal: Vec3
    ) -> Vec3:
        """
        Calculate sliding vector along a surface
        """
        return (movement_direction - 
                surface_normal * movement_direction.dot(surface_normal)).normalized()
