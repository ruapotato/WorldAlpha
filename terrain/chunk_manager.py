# terrain/chunk_manager.py
from threading import Thread, Lock
from queue import PriorityQueue
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from ursina import *
from noise import snoise2
import time
import math

class ChunkManager:
    def __init__(self, chunk_size, biome_manager):
        self.chunk_size = chunk_size
        self.biome_manager = biome_manager
        self.chunks = {}
        self.generation_queue = PriorityQueue()
        self.ready_meshes = PriorityQueue()
        self.processing_lock = Lock()
        
        # Generation state tracking
        self.currently_generating = set()
        # Increased worker count since chunks are smaller
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        
        # Performance settings - increased for smaller chunks
        self.max_mesh_per_frame = 2  # Create more meshes per frame since they're smaller
        self.max_concurrent_gen = 4   # Generate more chunks concurrently
        
        # Stats tracking
        self.chunks_generated = 0
        self.last_stats_update = time.time()
        self.generation_times = []
        
    def get_stats(self):
        """Get generation statistics"""
        current_time = time.time()
        if current_time - self.last_stats_update >= 1.0:
            stats = {
                'chunks_generated': self.chunks_generated,
                'chunks_in_generation': len(self.currently_generating),
                'chunks_pending': self.generation_queue.qsize(),
                'chunks_loaded': len(self.chunks),
                'avg_generation_time': np.mean(self.generation_times) if self.generation_times else 0
            }
            self.last_stats_update = current_time
            self.generation_times = []
            return stats
        return None

    def process_queued_chunks(self):
        """Process chunks with priority"""
        try:
            # Handle completed meshes
            meshes_handled = 0
            while meshes_handled < self.max_mesh_per_frame and not self.ready_meshes.empty():
                priority, (chunk_pos, vertices, triangles, colors) = self.ready_meshes.get_nowait()
                
                if chunk_pos not in self.chunks:
                    # Create mesh directly
                    mesh = Mesh(vertices=vertices, triangles=triangles, colors=colors, mode='triangle')
                    chunk_x, chunk_z = chunk_pos
                    
                    # Create entity
                    self.chunks[chunk_pos] = Entity(
                        position=Vec3(chunk_x * self.chunk_size, 0, chunk_z * self.chunk_size),
                        model=mesh,
                        collider='mesh'
                    )
                    self.chunks_generated += 1
                    
                self.currently_generating.discard(chunk_pos)
                meshes_handled += 1
                
            # Start new generations if needed
            while (len(self.currently_generating) < self.max_concurrent_gen and 
                   not self.generation_queue.empty()):
                priority, chunk_pos = self.generation_queue.get_nowait()
                if chunk_pos not in self.chunks and chunk_pos not in self.currently_generating:
                    self.currently_generating.add(chunk_pos)
                    self.thread_pool.submit(self._generate_chunk, priority, chunk_pos)
                    
        except Exception as e:
            print(f"Error in process_queued_chunks: {e}")

    def request_chunk(self, chunk_pos, priority):
        """Request a chunk with distance-based priority"""
        if (chunk_pos not in self.chunks and 
            chunk_pos not in self.currently_generating):
            # Use priority for sorting (lower number = higher priority)
            self.generation_queue.put((priority, chunk_pos))

    def remove_distant_chunks(self, center_x, center_z, view_distance):
        """Remove chunks outside view distance with border"""
        border = 2  # Keep a border of chunks beyond view distance
        max_distance = view_distance + border
        
        for chunk_pos in list(self.chunks.keys()):
            chunk_x, chunk_z = chunk_pos
            dx = abs(chunk_x - center_x)
            dz = abs(chunk_z - center_z)
            if dx > max_distance or dz > max_distance:
                self.remove_chunk(chunk_pos)

    def _generate_chunk(self, priority, chunk_pos):
        """Generate a single chunk in background thread"""
        try:
            start_time = time.time()
            
            chunk_x, chunk_z = chunk_pos
            world_x_start = chunk_x * self.chunk_size
            world_z_start = chunk_z * self.chunk_size
            
            # Generate heightmap
            heightmap = self._generate_heightmap(chunk_x, chunk_z)
            
            # Generate mesh data
            vertices = []
            triangles = []
            colors = []
            
            vertices_row = self.chunk_size + 1
            for z in range(self.chunk_size + 1):
                world_z = world_z_start + z
                for x in range(self.chunk_size + 1):
                    world_x = world_x_start + x
                    height = heightmap[z][x]
                    
                    params = self.biome_manager.get_blended_params(world_x, world_z)
                    
                    vertices.append(Vec3(x, height, z))
                    colors.append(params.color)
                    
                    if x < self.chunk_size and z < self.chunk_size:
                        base_idx = z * vertices_row + x
                        triangles.extend([
                            base_idx, base_idx + 1, base_idx + vertices_row,
                            base_idx + 1, base_idx + vertices_row + 1, base_idx + vertices_row
                        ])
            
            # Use original priority for consistent loading order
            self.ready_meshes.put((priority, (chunk_pos, vertices, triangles, colors)))
            
            generation_time = time.time() - start_time
            self.generation_times.append(generation_time)
            
        except Exception as e:
            print(f"Error generating chunk {chunk_pos}: {e}")
            self.currently_generating.discard(chunk_pos)

    def _generate_heightmap(self, chunk_x, chunk_z):
        """Generate heightmap for small chunk"""
        heightmap = []
        world_x_start = chunk_x * self.chunk_size
        world_z_start = chunk_z * self.chunk_size
        
        for z in range(self.chunk_size + 1):
            row = []
            world_z = world_z_start + z
            for x in range(self.chunk_size + 1):
                world_x = world_x_start + x
                params = self.biome_manager.get_blended_params(world_x, world_z)
                
                # Simplified noise calculation
                height = snoise2(
                    world_x * 0.02,
                    world_z * 0.02,
                    octaves=4
                ) * params.height_variation + params.base_height
                
                row.append(height)
            heightmap.append(row)
            
        return heightmap

    def remove_chunk(self, chunk_pos):
        """Remove a chunk safely"""
        if chunk_pos in self.chunks:
            try:
                self.chunks[chunk_pos].disable()
                del self.chunks[chunk_pos]
            except Exception as e:
                print(f"Error removing chunk {chunk_pos}: {e}")

    def cleanup(self):
        """Clean up resources"""
        self.thread_pool.shutdown(wait=False)
        for chunk_pos in list(self.chunks.keys()):
            self.remove_chunk(chunk_pos)
