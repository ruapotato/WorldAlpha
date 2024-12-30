# terrain/chunk.py
from ursina import *
from typing import List, Tuple
import numpy as np
from noise import snoise2

class TerrainChunk(Entity):
    def __init__(self, position, chunk_size, biome_manager, **kwargs):
        super().__init__(
            position=position,
            scale=(1, 1, 1),
            model=None,
            **kwargs
        )
        
        self.chunk_size = chunk_size
        self.biome_manager = biome_manager
        self.chunk_x = int(position[0] / chunk_size)
        self.chunk_z = int(position[2] / chunk_size)
        
        # Pre-calculate chunk boundaries for optimization
        self.world_x_start = self.chunk_x * chunk_size
        self.world_z_start = self.chunk_z * chunk_size
        
        # Use a single Entity for all vegetation in chunk
        self.vegetation_container = Entity(parent=scene)
        
        # Generate terrain with optimizations
        self._generate_terrain()
    
    def _generate_terrain(self):
        vertices, triangles, colors = self._generate_chunk_mesh()
        
        # Create mesh in one operation
        mesh = Mesh(
            vertices=vertices,
            triangles=triangles,
            colors=colors,
            mode='triangle'
        )
        
        self.model = mesh
        self.collider = 'mesh'
        
        # Batch create vegetation after terrain is generated
        self._batch_generate_vegetation()
    
    def _generate_chunk_mesh(self) -> Tuple[List[Vec3], List[int], List[color.rgba]]:
        # Pre-allocate arrays for better performance
        vertices = []
        triangles = []
        colors = []
        
        # Generate heightmap once
        heightmap = self._fast_generate_heightmap()
        
        # Pre-calculate vertex count for triangle indexing
        vertex_count = (self.chunk_size + 1) * (self.chunk_size + 1)
        vertices_row = self.chunk_size + 1
        
        # Pre-calculate triangle indices pattern
        triangle_pattern = np.array([
            0, 1, vertices_row,
            1, vertices_row + 1, vertices_row
        ])
        
        # Generate vertices and colors in a single pass
        for z in range(self.chunk_size + 1):
            world_z = self.world_z_start + z
            for x in range(self.chunk_size + 1):
                world_x = self.world_x_start + x
                
                # Get height and color efficiently
                height = heightmap[z][x]
                color = self.biome_manager.get_blended_params(world_x, world_z).color
                
                vertices.append(Vec3(x, height, z))
                colors.append(color)
                
                # Generate triangles efficiently
                if x < self.chunk_size and z < self.chunk_size:
                    base_idx = z * vertices_row + x
                    triangles.extend(triangle_pattern + base_idx)
        
        return vertices, triangles, colors
    
    def _fast_generate_heightmap(self) -> List[List[float]]:
        chunk_size_with_overflow = self.chunk_size + 1
        heightmap = [[0 for _ in range(chunk_size_with_overflow)] 
                    for _ in range(chunk_size_with_overflow)]
        
        # Calculate noise at a lower resolution first
        base_resolution = 4  # Sample every 4 blocks
        base_samples = chunk_size_with_overflow // base_resolution + 1
        
        # Generate base heightmap at lower resolution
        base_heightmap = [[0 for _ in range(base_samples)] 
                         for _ in range(base_samples)]
        
        for z in range(base_samples):
            world_z = self.world_z_start + z * base_resolution
            for x in range(base_samples):
                world_x = self.world_x_start + x * base_resolution
                
                params = self.biome_manager.get_blended_params(world_x, world_z)
                
                # Simplified noise calculation
                base = snoise2(world_x * 0.02, world_z * 0.02, octaves=4)
                detail = snoise2(world_x * 0.1, world_z * 0.1, octaves=2)
                
                base_heightmap[z][x] = (base * params.height_variation +
                                      detail * params.roughness +
                                      params.base_height)
        
        # Interpolate to full resolution
        for z in range(chunk_size_with_overflow):
            for x in range(chunk_size_with_overflow):
                # Find the four nearest base sample points
                base_x = x // base_resolution
                base_z = z // base_resolution
                next_x = min(base_x + 1, base_samples - 1)
                next_z = min(base_z + 1, base_samples - 1)
                
                # Calculate interpolation factors
                fx = (x % base_resolution) / base_resolution
                fz = (z % base_resolution) / base_resolution
                
                # Bilinear interpolation
                h00 = base_heightmap[base_z][base_x]
                h10 = base_heightmap[base_z][next_x]
                h01 = base_heightmap[next_z][base_x]
                h11 = base_heightmap[next_z][next_x]
                
                h0 = lerp(h00, h10, fx)
                h1 = lerp(h01, h11, fx)
                
                heightmap[z][x] = lerp(h0, h1, fz)
        
        return heightmap
    
    def _batch_generate_vegetation(self):
        # Reduce vegetation density for performance
        vegetation_density = 0.01  # 1% chance per block
        spacing = 4  # Check every 4 blocks
        
        for z in range(0, self.chunk_size, spacing):
            world_z = self.world_z_start + z
            for x in range(0, self.chunk_size, spacing):
                world_x = self.world_x_start + x
                
                if random.random() < vegetation_density:
                    biome = self.biome_manager.get_biome_at(world_x, world_z)
                    height = self.get_height_at(x, z)
                    
                    # Simplified vegetation - only trees and rocks
                    if random.random() < 0.5:  # 50% chance for tree vs rock
                        self._add_simple_tree(Vec3(x, height, z))
                    else:
                        self._add_simple_rock(Vec3(x, height, z))
    
    def _add_simple_tree(self, pos):
        tree = Entity(
            model='cube',
            color=color.rgb(0.2, 0.5, 0.2),
            scale=(2, 3, 2),
            position=pos + Vec3(0, 1.5, 0),
            parent=self.vegetation_container
        )
    
    def _add_simple_rock(self, pos):
        rock = Entity(
            model='cube',
            color=color.rgb(0.5, 0.5, 0.5),
            scale=(1, 0.5, 1),
            position=pos + Vec3(0, 0.25, 0),
            parent=self.vegetation_container
        )
    
    def get_height_at(self, local_x: float, local_z: float) -> float:
        heightmap = self._fast_generate_heightmap()
        
        x0 = int(min(max(local_x, 0), self.chunk_size))
        z0 = int(min(max(local_z, 0), self.chunk_size))
        
        return heightmap[z0][x0]
    
    def disable(self):
        self.vegetation_container.disable()
        super().disable()
