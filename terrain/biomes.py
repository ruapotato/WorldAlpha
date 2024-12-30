# worldalpha/terrain/biomes.py
from dataclasses import dataclass
from enum import Enum, auto
from ursina import color, Vec3
from noise import snoise2
from typing import Dict, List, Tuple
import random

class BiomeType(Enum):
    MEADOWS = auto()
    BLACK_FOREST = auto()
    MOUNTAINS = auto()
    PLAINS = auto()

@dataclass
class BiomeParams:
    base_height: float
    height_variation: float
    roughness: float
    color: color.rgba
    # Additional biome parameters
    tree_density: float = 0.0
    rock_density: float = 0.0
    grass_density: float = 0.0
    snow_height: float = float('inf')  # Height at which snow appears
    # Initialize with a default empty list instead of None
    vegetation_types: List[str] = None
    temperature_range: Tuple[float, float] = (0.0, 1.0)
    rainfall_range: Tuple[float, float] = (0.0, 1.0)

    def __post_init__(self):
        # Ensure vegetation_types is always a list
        if self.vegetation_types is None:
            self.vegetation_types = []

class BiomeManager:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._setup_biome_params()
        self._setup_transition_params()
        
    def _setup_biome_params(self):
        """Initialize parameters for each biome"""
        self.biome_params = {
            BiomeType.MEADOWS: BiomeParams(
                base_height=64,
                height_variation=15,
                roughness=0.3,
                color=color.rgb(0.4, 0.8, 0.3),
                tree_density=0.2,
                rock_density=0.1,
                grass_density=0.8,
                vegetation_types=['oak_tree', 'birch_tree', 'bush'],
                temperature_range=(0.3, 0.7),
                rainfall_range=(0.3, 0.6)
            ),
            BiomeType.BLACK_FOREST: BiomeParams(
                base_height=70,
                height_variation=25,
                roughness=0.4,
                color=color.rgb(0.2, 0.4, 0.2),
                tree_density=0.6,
                rock_density=0.3,
                grass_density=0.4,
                vegetation_types=['pine_tree', 'fir_tree', 'mushroom'],
                temperature_range=(0.2, 0.5),
                rainfall_range=(0.6, 1.0)
            ),
            BiomeType.MOUNTAINS: BiomeParams(
                base_height=120,
                height_variation=60,
                roughness=0.6,
                color=color.rgb(0.7, 0.7, 0.7),
                tree_density=0.1,
                rock_density=0.7,
                snow_height=140,
                vegetation_types=['pine_tree', 'rock_formation'],
                temperature_range=(0.0, 0.3),
                rainfall_range=(0.0, 1.0)
            ),
            BiomeType.PLAINS: BiomeParams(
                base_height=68,
                height_variation=10,
                roughness=0.2,
                color=color.rgb(0.6, 0.8, 0.3),
                tree_density=0.05,
                rock_density=0.1,
                grass_density=1.0,
                vegetation_types=['oak_tree', 'grass_tall', 'flowers'],
                temperature_range=(0.5, 1.0),
                rainfall_range=(0.2, 0.5)
            ),
        }

    def _setup_transition_params(self):
        """Setup parameters for biome transitions"""
        self.transition_width = 20  # Width of transition zone in blocks
        self.blend_factor = 0.5     # How much to blend between biomes
        
    def get_biome_at(self, x: float, z: float) -> BiomeType:
        """
        Determine the biome type at given coordinates
        Returns: BiomeType
        """
        temperature = self._get_temperature(x, z)
        moisture = self._get_moisture(x, z)
        elevation = self._get_base_elevation(x, z)
        
        # Calculate biome scores based on environmental factors
        scores = {}
        for biome_type, params in self.biome_params.items():
            temp_score = self._calculate_range_score(
                temperature, 
                params.temperature_range[0],
                params.temperature_range[1]
            )
            rain_score = self._calculate_range_score(
                moisture,
                params.rainfall_range[0],
                params.rainfall_range[1]
            )
            # Combine scores with weights
            scores[biome_type] = temp_score * 0.4 + rain_score * 0.3 + elevation * 0.3
        
        # Return biome with highest score
        return max(scores.items(), key=lambda x: x[1])[0]
            
    def _get_temperature(self, x: float, z: float) -> float:
        """Get temperature value at coordinates"""
        return (snoise2(x * 0.002, z * 0.002,
                    octaves=4,
                    persistence=0.5,
                    lacunarity=2.0,
                    base=self.seed) + 1) * 0.5
                    
    def _get_moisture(self, x: float, z: float) -> float:
        """Get moisture value at coordinates"""
        return (snoise2(x * 0.002, z * 0.002 + 1000,
                    octaves=4,
                    persistence=0.5,
                    lacunarity=2.0,
                    base=self.seed + 1) + 1) * 0.5
                    
    def _get_base_elevation(self, x: float, z: float) -> float:
        """Get base elevation factor at coordinates"""
        return (snoise2(x * 0.001, z * 0.001,
                    octaves=2,
                    persistence=0.5,
                    lacunarity=2.0,
                    base=self.seed + 2) + 1) * 0.5
                    
    def _calculate_range_score(self, value: float, min_val: float, max_val: float) -> float:
        """Calculate how well a value fits within a range"""
        if value < min_val:
            return 1.0 - (min_val - value)
        elif value > max_val:
            return 1.0 - (value - max_val)
        else:
            return 1.0
            
    def get_blended_params(self, x: float, z: float) -> BiomeParams:
        """
        Get blended parameters between nearby biomes for smooth transitions
        Returns: BiomeParams with interpolated values
        """
        # Get primary biome and its parameters
        primary_biome = self.get_biome_at(x, z)
        primary_params = self.biome_params[primary_biome]
        
        # Check nearby points for different biomes
        nearby_biomes = {}
        for dx in [-self.transition_width, 0, self.transition_width]:
            for dz in [-self.transition_width, 0, self.transition_width]:
                if dx == 0 and dz == 0:
                    continue
                check_biome = self.get_biome_at(x + dx, z + dz)
                if check_biome != primary_biome:
                    nearby_biomes[check_biome] = self.biome_params[check_biome]
        
        # If no different nearby biomes, return primary params
        if not nearby_biomes:
            return primary_params
        
        # Blend parameters with nearby biomes
        blended_params = BiomeParams(
            base_height=primary_params.base_height,
            height_variation=primary_params.height_variation,
            roughness=primary_params.roughness,
            color=primary_params.color
        )
        
        for nearby_biome, params in nearby_biomes.items():
            distance = self._get_biome_distance(x, z, nearby_biome)
            blend = max(0, 1 - (distance / self.transition_width)) * self.blend_factor
            
            # Blend numerical parameters
            blended_params.base_height = self._lerp(
                blended_params.base_height, 
                params.base_height, 
                blend
            )
            blended_params.height_variation = self._lerp(
                blended_params.height_variation,
                params.height_variation,
                blend
            )
            blended_params.roughness = self._lerp(
                blended_params.roughness,
                params.roughness,
                blend
            )
            
            # Blend colors
            blended_params.color = self._blend_colors(
                blended_params.color,
                params.color,
                blend
            )
        
        return blended_params
    
    def _get_biome_distance(self, x: float, z: float, target_biome: BiomeType) -> float:
        """Calculate distance to nearest occurrence of target biome"""
        min_distance = float('inf')
        for dx in range(-self.transition_width, self.transition_width + 1, 5):
            for dz in range(-self.transition_width, self.transition_width + 1, 5):
                check_x, check_z = x + dx, z + dz
                if self.get_biome_at(check_x, check_z) == target_biome:
                    distance = (dx * dx + dz * dz) ** 0.5
                    min_distance = min(min_distance, distance)
        return min_distance
    
    def _lerp(self, a: float, b: float, t: float) -> float:
        """Linear interpolation between two values"""
        return a + (b - a) * t
    
    def _blend_colors(self, color1: color.rgba, color2: color.rgba, factor: float) -> color.rgba:
        """Blend two colors together"""
        return color.rgba(
            self._lerp(color1[0], color2[0], factor),
            self._lerp(color1[1], color2[1], factor),
            self._lerp(color1[2], color2[2], factor),
            1.0
        )
    
    def get_vegetation_at(self, x: float, z: float, biome_type: BiomeType) -> List[Dict]:
        """
        Get list of vegetation to spawn at coordinates
        Returns: List of dicts containing vegetation type and position
        """
        params = self.biome_params[biome_type]
        vegetation = []
        
        # Use deterministic random based on coordinates and seed
        rng = random.Random(hash((x, z, self.seed)))
        
        # Check tree spawning
        if params.vegetation_types and rng.random() < params.tree_density:
            tree_types = [t for t in params.vegetation_types if 'tree' in t]
            if tree_types:  # Only proceed if we found tree types
                tree_type = rng.choice(tree_types)
                vegetation.append({
                    'type': tree_type,
                    'position': Vec3(x, 0, z),
                    'scale': Vec3(1 + rng.random() * 0.5,
                                1 + rng.random() * 0.5,
                                1 + rng.random() * 0.5),
                    'rotation': Vec3(0, rng.random() * 360, 0)
                })
        
        # Check rock spawning
        if rng.random() < params.rock_density:
            vegetation.append({
                'type': 'rock',
                'position': Vec3(x, 0, z),
                'scale': Vec3(0.5 + rng.random() * 1.0,
                            0.3 + rng.random() * 0.5,
                            0.5 + rng.random() * 1.0),
                'rotation': Vec3(rng.random() * 30,
                            rng.random() * 360,
                            rng.random() * 30)
            })
        
        # Check grass/flora spawning
        if params.vegetation_types and rng.random() < params.grass_density:
            flora_types = [t for t in params.vegetation_types 
                        if any(keyword in t for keyword in ['grass', 'flower', 'mushroom'])]
            if flora_types:  # Only proceed if we found flora types
                flora_type = rng.choice(flora_types)
                vegetation.append({
                    'type': flora_type,
                    'position': Vec3(x, 0, z),
                    'scale': Vec3(0.8 + rng.random() * 0.4,
                                0.8 + rng.random() * 0.4,
                                0.8 + rng.random() * 0.4),
                    'rotation': Vec3(0, rng.random() * 360, 0)
                })
            
        return vegetation
