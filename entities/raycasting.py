# worldalpha/physics/raycasting.py
from ursina import Vec3, raycast
from typing import List, NamedTuple, Optional

class RaycastResult(NamedTuple):
    hit: bool
    point: Optional[Vec3]
    normal: Optional[Vec3]
    distance: float
    entity: Optional[object]

class RaycastSystem:
    @staticmethod
    def cast_ray(
        origin: Vec3,
        direction: Vec3,
        max_distance: float,
        ignore_list: List = None
    ) -> RaycastResult:
        """
        Cast a ray and return detailed hit information
        """
        hit_info = raycast(
            origin,
            direction,
            distance=max_distance,
            ignore=ignore_list or []
        )
        
        return RaycastResult(
            hit=hit_info.hit,
            point=hit_info.point if hit_info.hit else None,
            normal=hit_info.normal if hit_info.hit else None,
            distance=hit_info.distance,
            entity=hit_info.entity if hit_info.hit else None
        )

    @staticmethod
    def multi_raycast(
        origins: List[Vec3],
        direction: Vec3,
        max_distance: float,
        ignore_list: List = None
    ) -> List[RaycastResult]:
        """
        Cast multiple rays from different origins in the same direction
        """
        return [
            RaycastSystem.cast_ray(origin, direction, max_distance, ignore_list)
            for origin in origins
        ]
