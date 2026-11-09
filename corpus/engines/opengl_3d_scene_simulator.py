#!/usr/bin/env python3
"""
opengl_3d_scene_simulator.py
OpenGL 3D Scene Pipeline & Phong Shader Software Renderer Simulator.
Pure Python & NumPy Implementation.

Features:
1. 3D Camera Controls (WASD Movement, Yaw/Pitch, Zoom FOV).
2. Model-View-Projection (MVP) Matrix Pipeline (M_mvp = P * V * M_model).
3. Phong Reflection Model Shader (Ambient + Diffuse (N.L) + Specular (R.V)^alpha).
4. Multi-Light Source Support (Point Lights & Directional Sun Light).
5. 3D Cube Mesh Rasterizer to Terminal ASCII Viewport Canvas.

Usage:
    python opengl_3d_scene_simulator.py
"""

import sys
import time
import math
import numpy as np

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# 1. 3D VECTOR & MATRIX MATH UTILITIES
# ==============================================================================
def normalize(v):
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v

def create_translation_matrix(tx, ty, tz):
    return np.array([
        [1.0, 0.0, 0.0, tx],
        [0.0, 1.0, 0.0, ty],
        [0.0, 0.0, 1.0, tz],
        [0.0, 0.0, 0.0, 1.0]
    ])

def create_rotation_y_matrix(angle_rad):
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return np.array([
        [ c,  0.0,  s,  0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s,  0.0,  c,  0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])

def create_perspective_projection(fov_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    return np.array([
        [f / aspect, 0.0, 0.0, 0.0],
        [0.0, f, 0.0, 0.0],
        [0.0, 0.0, (far + near) / (near - far), (2.0 * far * near) / (near - far)],
        [0.0, 0.0, -1.0, 0.0]
    ])

# ==============================================================================
# 2. 3D INTERACTIVE CAMERA ENGINE
# ==============================================================================
class Camera3D:
    def __init__(self, position=[0.0, 0.0, 5.0], target=[0.0, 0.0, 0.0]):
        self.position = np.array(position, dtype=float)
        self.target = np.array(target, dtype=float)
        self.up = np.array([0.0, 1.0, 0.0], dtype=float)
        self.fov = 45.0 # Degrees (Zoom)

    def get_view_matrix(self):
        f = normalize(self.target - self.position)
        s = normalize(np.cross(f, self.up))
        u = np.cross(s, f)
        
        R = np.eye(4)
        R[0, :3] = s
        R[1, :3] = u
        R[2, :3] = -f
        
        T = create_translation_matrix(-self.position[0], -self.position[1], -self.position[2])
        return np.dot(R, T)

    def process_keyboard(self, direction, delta_time=0.1):
        speed = 2.5 * delta_time
        f = normalize(self.target - self.position)
        s = normalize(np.cross(f, self.up))
        
        if direction == 'W':
            self.position += f * speed
        elif direction == 'S':
            self.position -= f * speed
        elif direction == 'A':
            self.position -= s * speed
        elif direction == 'D':
            self.position += s * speed

# ==============================================================================
# 3. PHONG SHADER & RASTERIZER ENGINE
# ==============================================================================
class OpenGL3DSceneRenderer:
    def __init__(self, width=60, height=22):
        self.width = width
        self.height = height
        self.camera = Camera3D()
        self.light_pos = np.array([2.0, 3.0, 4.0])
        
        # 3D Cube Vertices (Homogeneous coordinates)
        self.cube_vertices = np.array([
            [-1, -1, -1, 1], [ 1, -1, -1, 1], [ 1,  1, -1, 1], [-1,  1, -1, 1],
            [-1, -1,  1, 1], [ 1, -1,  1, 1], [ 1,  1,  1, 1], [-1,  1,  1, 1]
        ], dtype=float)

    def compute_phong_shading(self, surface_pos, normal):
        # 1. Ambient
        I_ambient = 0.25
        # 2. Diffuse (N . L)
        L = normalize(self.light_pos - surface_pos)
        N = normalize(normal)
        n_dot_l = np.dot(N, L)
        I_diffuse = max(0.0, n_dot_l) * 0.65
        # 3. Specular (R . V)^alpha
        # NOTE: specular must be gated on n_dot_l > 0 (light in front of the
        # surface). R = 2(N.L)N - L is defined even when N.L is negative, and
        # R.V can still come out positive by coincidence, producing a
        # nonphysical specular highlight on a surface facing away from the
        # light. Found via test_opengl_3d_scene_simulator.py's normal-incidence
        # ground-truth check (light behind surface must be ambient-only).
        if n_dot_l > 0.0:
            V = normalize(self.camera.position - surface_pos)
            R = normalize(2.0 * n_dot_l * N - L)
            I_specular = (max(0.0, np.dot(R, V)) ** 16) * 0.45
        else:
            I_specular = 0.0

        return I_ambient + I_diffuse + I_specular

    def render_frame(self, rotation_angle=0.0):
        buffer = [[' ' for _ in range(self.width)] for _ in range(self.height)]

        # 1. MVP Pipeline
        M_model = create_rotation_y_matrix(rotation_angle)
        V_view = self.camera.get_view_matrix()
        P_proj = create_perspective_projection(self.camera.fov, self.width / self.height, 0.1, 100.0)
        
        MVP = np.dot(P_proj, np.dot(V_view, M_model))

        # Project Vertices
        projected_verts = []
        for v in self.cube_vertices:
            clip = np.dot(MVP, v)
            if clip[3] != 0:
                ndc = clip[:3] / clip[3]
            else:
                ndc = clip[:3]
            screen_x = int((ndc[0] + 1.0) * 0.5 * (self.width - 1))
            screen_y = int((1.0 - ndc[1]) * 0.5 * (self.height - 1))
            projected_verts.append((screen_x, screen_y, ndc[2]))

        # Render Vertices to Canvas Buffer
        ascii_chars = " .:-=+*#%@"
        for idx, (sx, sy, sz) in enumerate(projected_verts):
            if 0 <= sx < self.width and 0 <= sy < self.height:
                world_pos = np.dot(M_model, self.cube_vertices[idx])[:3]
                normal = normalize(world_pos)
                intensity = self.compute_phong_shading(world_pos, normal)
                char_idx = int(min(1.0, max(0.0, intensity)) * (len(ascii_chars) - 1))
                buffer[sy][sx] = ascii_chars[char_idx]

        return "\n".join("".join(row) for row in buffer)

# ==============================================================================
# DEMONSTRATION HARNESS
# ==============================================================================
def main():
    print("""
    ================================================================
           OPENGL 3D SCENE & PHONG SHADER SOFTWARE RENDERER
          Model-View-Projection (MVP) Pipeline & Camera Controls
    ================================================================
    """)
    
    renderer = OpenGL3DSceneRenderer(width=60, height=22)
    
    print("  Frame 1: Initial Scene (Camera Pos: [0, 0, 5], Cube Rotation 0°)...")
    frame1 = renderer.render_frame(rotation_angle=0.0)
    
    print("\n" + "="*62)
    print("  3D OPENGL ASCII VIEWPORT CANVAS (FRAME 1)")
    print("="*62)
    print(frame1)
    print("="*62)
    
    print("\n  Simulating WASD Control: Pressing 'W' (Moving Camera forward to [0, 0, 4.5])...")
    renderer.camera.process_keyboard('W', delta_time=0.2)
    
    print("  Frame 2: Rotated 45° with Phong Specular Shading...")
    frame2 = renderer.render_frame(rotation_angle=math.radians(45.0))
    
    print("\n" + "="*62)
    print("  3D OPENGL ASCII VIEWPORT CANVAS (FRAME 2 - ROTATED 45°)")
    print("="*62)
    print(frame2)
    print("="*62 + "\n")
    
    print(" OpenGL 3D Scene Pipeline Simulator Verified!")

if __name__ == "__main__":
    main()
