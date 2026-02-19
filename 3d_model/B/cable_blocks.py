from __future__ import annotations

# build123d
from build123d import (
    BuildPart,
    BuildSketch,
    Locations,
    Rectangle,
    Circle,
    Plane,
    Box,
    Mode,
    extrude,
    Align,
)

# Stdlib
import os

try:
    from build123d import export_stl  # type: ignore
except Exception:
    export_stl = None  # type: ignore

"""
Cable management blocks for pressure testing: 200mm x 100mm x 3mm
- Version A: Block with extension cube, side walls for fitting, and grid grooves on top for electrode alignment
- Version B: Block with extension cube, 50mm diameter cylindrical bumper for dumbbell weights, and grid grooves on underside for electrode alignment
Both versions include configurable grid lines for precise electrode/copper tape positioning.
Version B is slightly smaller than A's inner cavity (by FIT_CLEARANCE on each side) so they fit together with a gap.
"""

# -----------------------------
# Parameters
# -----------------------------
BLOCK_LENGTH = 200.0  # X (length) mm
BLOCK_WIDTH = 100.0    # Y (width) mm
BLOCK_HEIGHT = 3.0    # Z (height) mm

# Cable extension cube (rectangular extrusion on one end)
EXTENSION_WIDTH = 6.0      # Width of the extension (mm)
EXTENSION_LENGTH = 10.0    # Length extending from the block (mm)
EXTENSION_HEIGHT = 3.0     # Height of the extension (same as block height)

# Side walls for fitting blocks together
WALL_THICKNESS = 3.0       # Thickness of the side walls (mm)
WALL_HEIGHT = 3.0          # Height of the side walls above the block (mm) - low so weights get caught
FIT_CLEARANCE = 0.5        # Clearance gap so blocks fit together easily (mm per side)
BLOCK_B_HEIGHT = 4.5      # Height of Block B base (mm) - thicker to raise weights closer to walls

# Weight bumper cylinder (for dumbbell weights - pressure testing)
BUMPER_DIAMETER = 49.0     # Diameter of the cylinder (mm)
BUMPER_HEIGHT = 50.0       # Height of the cylinder extending upward (mm)

# Grid lines for electrode/copper tape alignment
GRID_LINES_X = 2          # Number of grid lines along X direction (length) - set to 1 for single centerline
GRID_LINES_Y = 1          # Number of grid lines along Y direction (width) - set to 1 for single centerline
GROOVE_WIDTH = 5.0         # Width of each groove line (mm)
GROOVE_DEPTH = 0.1         # Depth of the grooves (mm)
CABLE_HOLE_DIAMETER = 7.0  # Diameter of holes in walls for cable exit (mm)
HOLE_EXTENSION_LENGTH = 3.0  # Length of rectangular extension at hole entrance (mm)
HOLE_EXTENSION_WIDTH = 6.0  # Width of extension for Block B to fit into Block A holes (mm)


def create_cable_block() -> object:
    """
    Create rectangular block (100mm x 50mm x 3mm) with one extension cube on one end.
    This version has side walls for fitting with the bumper version and grid grooves on top.
    """
    with BuildPart() as p:
        # Create basic rectangular box - extended to include wall thickness
        base_length = BLOCK_LENGTH + 2 * WALL_THICKNESS
        base_width = BLOCK_WIDTH + 2 * WALL_THICKNESS
        with Locations((0, 0, BLOCK_HEIGHT / 2)):
            Box(base_length, base_width, BLOCK_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Add side walls around the perimeter (extending upward from the extended base)
        wall_z = BLOCK_HEIGHT + WALL_HEIGHT / 2
        
        # Left wall (-Y side)
        wall_y_pos = BLOCK_WIDTH / 2 + WALL_THICKNESS / 2
        with Locations((0, -wall_y_pos, wall_z)):
            Box(BLOCK_LENGTH + 2 * WALL_THICKNESS, WALL_THICKNESS, WALL_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Right wall (+Y side)
        with Locations((0, wall_y_pos, wall_z)):
            Box(BLOCK_LENGTH + 2 * WALL_THICKNESS, WALL_THICKNESS, WALL_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Back wall (-X side)
        wall_x_pos = BLOCK_LENGTH / 2 + WALL_THICKNESS / 2
        with Locations((-wall_x_pos, 0, wall_z)):
            Box(WALL_THICKNESS, BLOCK_WIDTH + 2 * WALL_THICKNESS, WALL_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Add 6mm wide x 3mm tall hole in back wall for electrode cable (only in wall portion)
        ELECTRODE_HOLE_WIDTH = 6.0
        electrode_hole_z = BLOCK_HEIGHT + WALL_HEIGHT / 2
        with Locations((-wall_x_pos, 0, electrode_hole_z)):
            Box(WALL_THICKNESS + 1, ELECTRODE_HOLE_WIDTH, WALL_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # Front wall (+X side) - skip the area where extension is
        # We'll add walls on either side of the extension (with 1mm clearance)
        extension_opening = EXTENSION_WIDTH + 1.0  # Add 1mm clearance
        front_wall_y_offset = (BLOCK_WIDTH / 2 - extension_opening / 2) / 2 + extension_opening / 2
        with Locations((wall_x_pos, front_wall_y_offset, wall_z)):
            Box(WALL_THICKNESS, BLOCK_WIDTH / 2 - extension_opening / 2, WALL_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        with Locations((wall_x_pos, -front_wall_y_offset, wall_z)):
            Box(WALL_THICKNESS, BLOCK_WIDTH / 2 - extension_opening / 2, WALL_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Add rectangular extension on ONE side (+X direction)
        extension_x_pos = BLOCK_LENGTH / 2 + EXTENSION_LENGTH / 2
        with Locations((extension_x_pos, 0, EXTENSION_HEIGHT / 2)):
            Box(EXTENSION_LENGTH, EXTENSION_WIDTH, EXTENSION_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Add grid grooves on the TOP surface (inside the walls)
        # Grid lines running along X direction (length) - parallel to X axis
        if GRID_LINES_Y > 0:
            if GRID_LINES_Y == 1:
                # Single centerline
                y_positions = [0]
            else:
                # Multiple lines distributed at quarters (e.g., 2 lines at 1/4 and 3/4)
                # Divide width into 2n sections, place lines at odd multiples
                spacing_y = BLOCK_WIDTH / (2 * GRID_LINES_Y)
                y_positions = [(2 * i + 1) * spacing_y - BLOCK_WIDTH / 2 for i in range(GRID_LINES_Y)]
            
            for y_pos in y_positions:
                with Locations((0, y_pos, BLOCK_HEIGHT)):
                    Box(BLOCK_LENGTH, GROOVE_WIDTH, GROOVE_DEPTH,
                        align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
        
        # Grid lines running along Y direction (width) - parallel to Y axis
        if GRID_LINES_X > 0:
            if GRID_LINES_X == 1:
                # Single centerline
                x_positions = [0]
            else:
                # Multiple lines distributed at quarters (e.g., 2 lines at 1/4 and 3/4)
                # Divide length into 2n sections, place lines at odd multiples
                spacing_x = BLOCK_LENGTH / (2 * GRID_LINES_X)
                x_positions = [(2 * i + 1) * spacing_x - BLOCK_LENGTH / 2 for i in range(GRID_LINES_X)]
            
            for x_pos in x_positions:
                with Locations((x_pos, 0, BLOCK_HEIGHT)):
                    Box(GROOVE_WIDTH, BLOCK_WIDTH, GROOVE_DEPTH,
                        align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
        
        # Add 6mm holes in walls where grooves end, with rectangular extensions
        # For Y grooves (running along X direction), add holes in back and front walls (-X and +X)
        if GRID_LINES_Y > 0:
            if GRID_LINES_Y == 1:
                y_positions = [0]
            else:
                spacing_y = BLOCK_WIDTH / (2 * GRID_LINES_Y)
                y_positions = [(2 * i + 1) * spacing_y - BLOCK_WIDTH / 2 for i in range(GRID_LINES_Y)]
            
            for y_pos in y_positions:
                # Back wall (-X side) - add holes and extensions at each Y groove position
                # Hole only in wall portion, not through the base plate
                wall_x_neg = -BLOCK_LENGTH / 2 - WALL_THICKNESS / 2
                hole_z = BLOCK_HEIGHT + WALL_HEIGHT / 2
                with Locations((wall_x_neg, y_pos, hole_z)):
                    Box(WALL_THICKNESS + 1, CABLE_HOLE_DIAMETER, WALL_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
                # Add rectangular extension on outer side of back wall (flush with plate)
                ext_x_neg = -BLOCK_LENGTH / 2 - WALL_THICKNESS - HOLE_EXTENSION_LENGTH / 2
                with Locations((ext_x_neg, y_pos, BLOCK_HEIGHT / 2)):
                    Box(HOLE_EXTENSION_LENGTH, CABLE_HOLE_DIAMETER, BLOCK_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
                # Add rectangular extension on inner side of back wall to fill gap (flush with plate)
                ext_x_neg_inner = -BLOCK_LENGTH / 2 + HOLE_EXTENSION_LENGTH / 2
                with Locations((ext_x_neg_inner, y_pos, BLOCK_HEIGHT / 2)):
                    Box(HOLE_EXTENSION_LENGTH, CABLE_HOLE_DIAMETER, BLOCK_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
                
                # Front wall (+X side) - add holes where there are walls (not at extension)
                # Hole only in wall portion, not through the base plate
                wall_x_pos = BLOCK_LENGTH / 2 + WALL_THICKNESS / 2
                # Check if position is not blocked by extension opening (with clearance)
                extension_opening = EXTENSION_WIDTH + 1.0
                if abs(y_pos) > extension_opening / 2:
                    with Locations((wall_x_pos, y_pos, hole_z)):
                        Box(WALL_THICKNESS + 1, CABLE_HOLE_DIAMETER, WALL_HEIGHT,
                            align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
                    # Add rectangular extension on outer side of front wall (flush with plate)
                    ext_x_pos = BLOCK_LENGTH / 2 + WALL_THICKNESS + HOLE_EXTENSION_LENGTH / 2
                    with Locations((ext_x_pos, y_pos, BLOCK_HEIGHT / 2)):
                        Box(HOLE_EXTENSION_LENGTH, CABLE_HOLE_DIAMETER, BLOCK_HEIGHT,
                            align=(Align.CENTER, Align.CENTER, Align.CENTER))
                    # Add rectangular extension on inner side of front wall to fill gap (flush with plate)
                    ext_x_pos_inner = BLOCK_LENGTH / 2 - HOLE_EXTENSION_LENGTH / 2
                    with Locations((ext_x_pos_inner, y_pos, BLOCK_HEIGHT / 2)):
                        Box(HOLE_EXTENSION_LENGTH, CABLE_HOLE_DIAMETER, BLOCK_HEIGHT,
                            align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # For X grooves (running along Y direction), add holes in left and right walls (-Y and +Y)
        if GRID_LINES_X > 0:
            if GRID_LINES_X == 1:
                x_positions = [0]
            else:
                spacing_x = BLOCK_LENGTH / (2 * GRID_LINES_X)
                x_positions = [(2 * i + 1) * spacing_x - BLOCK_LENGTH / 2 for i in range(GRID_LINES_X)]
            
            for x_pos in x_positions:
                # Left wall (-Y side)
                # Hole only in wall portion, not through the base plate
                wall_y_neg = -BLOCK_WIDTH / 2 - WALL_THICKNESS / 2
                hole_z = BLOCK_HEIGHT + WALL_HEIGHT / 2
                with Locations((x_pos, wall_y_neg, hole_z)):
                    Box(CABLE_HOLE_DIAMETER, WALL_THICKNESS + 1, WALL_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
                # Add rectangular extension on outer side of left wall (flush with plate)
                ext_y_neg = -BLOCK_WIDTH / 2 - WALL_THICKNESS - HOLE_EXTENSION_LENGTH / 2
                with Locations((x_pos, ext_y_neg, BLOCK_HEIGHT / 2)):
                    Box(CABLE_HOLE_DIAMETER, HOLE_EXTENSION_LENGTH, BLOCK_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
                # Add rectangular extension on inner side of left wall to fill gap (flush with plate)
                ext_y_neg_inner = -BLOCK_WIDTH / 2 + HOLE_EXTENSION_LENGTH / 2
                with Locations((x_pos, ext_y_neg_inner, BLOCK_HEIGHT / 2)):
                    Box(CABLE_HOLE_DIAMETER, HOLE_EXTENSION_LENGTH, BLOCK_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
                
                # Right wall (+Y side)
                # Hole only in wall portion, not through the base plate
                wall_y_pos = BLOCK_WIDTH / 2 + WALL_THICKNESS / 2
                with Locations((x_pos, wall_y_pos, hole_z)):
                    Box(CABLE_HOLE_DIAMETER, WALL_THICKNESS + 1, WALL_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
                # Add rectangular extension on outer side of right wall (flush with plate)
                ext_y_pos = BLOCK_WIDTH / 2 + WALL_THICKNESS + HOLE_EXTENSION_LENGTH / 2
                with Locations((x_pos, ext_y_pos, BLOCK_HEIGHT / 2)):
                    Box(CABLE_HOLE_DIAMETER, HOLE_EXTENSION_LENGTH, BLOCK_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
                # Add rectangular extension on inner side of right wall to fill gap (flush with plate)
                ext_y_pos_inner = BLOCK_WIDTH / 2 - HOLE_EXTENSION_LENGTH / 2
                with Locations((x_pos, ext_y_pos_inner, BLOCK_HEIGHT / 2)):
                    Box(CABLE_HOLE_DIAMETER, HOLE_EXTENSION_LENGTH, BLOCK_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
    
    return p.part


def create_cable_block_with_bumper() -> object:
    """
    Create rectangular block with extension cube and a cylindrical bumper 
    for holding dumbbell weights (pressure testing).
    Grid grooves on the underside for electrode alignment.
    This block is slightly smaller than Block A to fit inside with clearance,
    and thicker to raise weights closer to Block A's walls.
    """
    with BuildPart() as p:
        # Create basic rectangular box - slightly smaller to fit inside Block A
        # and thicker to raise the weights
        block_b_length = BLOCK_LENGTH - 2 * FIT_CLEARANCE
        block_b_width = BLOCK_WIDTH - 2 * FIT_CLEARANCE
        with Locations((0, 0, BLOCK_B_HEIGHT / 2)):
            Box(block_b_length, block_b_width, BLOCK_B_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Add rectangular extension on ONE side (+X direction)
        extension_x_pos = block_b_length / 2 + EXTENSION_LENGTH / 2
        with Locations((extension_x_pos, 0, BLOCK_B_HEIGHT / 2)):
            Box(EXTENSION_LENGTH, EXTENSION_WIDTH, BLOCK_B_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Add cylindrical bumper in the center for dumbbell weights
        # Position it at the center of the block, extending upward
        bumper_z = BLOCK_B_HEIGHT + BUMPER_HEIGHT / 2
        with BuildSketch(Plane.XY.offset(BLOCK_B_HEIGHT)):
            Circle(radius=BUMPER_DIAMETER / 2)
        extrude(amount=BUMPER_HEIGHT, mode=Mode.ADD)
        
        # Add grid grooves on the BOTTOM surface (underside)
        # Grid lines running along X direction (length) - parallel to X axis
        if GRID_LINES_Y > 0:
            if GRID_LINES_Y == 1:
                # Single centerline
                y_positions = [0]
            else:
                # Multiple lines distributed at quarters (e.g., 2 lines at 1/4 and 3/4)
                # Divide width into 2n sections, place lines at odd multiples
                spacing_y = block_b_width / (2 * GRID_LINES_Y)
                y_positions = [(2 * i + 1) * spacing_y - block_b_width / 2 for i in range(GRID_LINES_Y)]
            
            for y_pos in y_positions:
                with Locations((0, y_pos, 0)):
                    Box(block_b_length, GROOVE_WIDTH, GROOVE_DEPTH,
                        align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        
        # Grid lines running along Y direction (width) - parallel to Y axis
        if GRID_LINES_X > 0:
            if GRID_LINES_X == 1:
                # Single centerline
                x_positions = [0]
            else:
                # Multiple lines distributed at quarters (e.g., 2 lines at 1/4 and 3/4)
                # Divide length into 2n sections, place lines at odd multiples
                spacing_x = block_b_length / (2 * GRID_LINES_X)
                x_positions = [(2 * i + 1) * spacing_x - block_b_length / 2 for i in range(GRID_LINES_X)]
            
            for x_pos in x_positions:
                with Locations((x_pos, 0, 0)):
                    Box(GROOVE_WIDTH, block_b_width, GROOVE_DEPTH,
                        align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        
        # Add 5mm solid extensions on top surface (to fit into Block A's 6mm wall holes)
        # These align with Block A's wall hole positions - no holes, just solid blocks
        # For Y grooves in Block A (which have holes in back/front walls), add extensions on back/front of Block B
        if GRID_LINES_Y > 0:
            if GRID_LINES_Y == 1:
                y_positions = [0]
            else:
                spacing_y = BLOCK_WIDTH / (2 * GRID_LINES_Y)
                y_positions = [(2 * i + 1) * spacing_y - BLOCK_WIDTH / 2 for i in range(GRID_LINES_Y)]
            
            for y_pos in y_positions:
                # Back extension (-X side) - aligns with Block A back wall hole
                ext_x_neg = -block_b_length / 2 - HOLE_EXTENSION_LENGTH / 2
                with Locations((ext_x_neg, y_pos, BLOCK_B_HEIGHT / 2)):
                    Box(HOLE_EXTENSION_LENGTH, HOLE_EXTENSION_WIDTH, BLOCK_B_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
                
                # Front extension (+X side) - avoid cable extension area (with clearance)
                extension_opening = EXTENSION_WIDTH + 1.0
                if abs(y_pos) > extension_opening / 2:
                    ext_x_pos = block_b_length / 2 + HOLE_EXTENSION_LENGTH / 2
                    with Locations((ext_x_pos, y_pos, BLOCK_B_HEIGHT / 2)):
                        Box(HOLE_EXTENSION_LENGTH, HOLE_EXTENSION_WIDTH, BLOCK_B_HEIGHT,
                            align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # For X grooves in Block A (which have holes in left/right walls), add extensions on left/right of Block B
        if GRID_LINES_X > 0:
            if GRID_LINES_X == 1:
                x_positions = [0]
            else:
                spacing_x = BLOCK_LENGTH / (2 * GRID_LINES_X)
                x_positions = [(2 * i + 1) * spacing_x - BLOCK_LENGTH / 2 for i in range(GRID_LINES_X)]
            
            for x_pos in x_positions:
                # Left extension (-Y side)
                ext_y_neg = -block_b_width / 2 - HOLE_EXTENSION_LENGTH / 2
                with Locations((x_pos, ext_y_neg, BLOCK_B_HEIGHT / 2)):
                    Box(HOLE_EXTENSION_WIDTH, HOLE_EXTENSION_LENGTH, BLOCK_B_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
                
                # Right extension (+Y side)
                ext_y_pos = block_b_width / 2 + HOLE_EXTENSION_LENGTH / 2
                with Locations((x_pos, ext_y_pos, BLOCK_B_HEIGHT / 2)):
                    Box(HOLE_EXTENSION_WIDTH, HOLE_EXTENSION_LENGTH, BLOCK_B_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))
    
    return p.part


def export_cable_blocks(base_name: str = "cable_block") -> None:
    """
    Export both versions of cable blocks as STL files.
    - Version A: Block with extension, side walls, and grid grooves on top
    - Version B: Block with extension, cylindrical bumper, and grid grooves on underside
    """
    if export_stl is None:
        raise RuntimeError(
            "STL export is not available. Ensure your build123d version supports `export_stl`."
        )
    
    # Export Version A - Block with side walls and grid grooves on top
    out_path_a = f"{base_name}_A.stl"
    os.makedirs(os.path.dirname(out_path_a) or ".", exist_ok=True)
    part_a = create_cable_block()
    export_stl(part_a, out_path_a)
    print(f"Exported: {out_path_a} (with side walls and grid grooves on top)")
    
    # Export Version B - Block with bumper and grid grooves on underside
    out_path_b = f"{base_name}_B.stl"
    part_b = create_cable_block_with_bumper()
    export_stl(part_b, out_path_b)
    print(f"Exported: {out_path_b} (with cylindrical bumper and grid grooves on underside)")


if __name__ == "__main__":
    export_cable_blocks()

