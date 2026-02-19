from __future__ import annotations

# build123d
from build123d import (
    BuildPart,
    BuildSketch,
    Locations,
    Rectangle,      # kept for slot profile
    Circle,
    Axis,
    Mode,
    extrude,
    fillet,
    Text,
    Align,
)

# Try both common names for rounded rectangle in build123d
try:
    from build123d import RoundedRectangle  # >= some versions
    _RR_NAME = "RoundedRectangle"
except Exception:
    try:
        from build123d import RectangleRounded as RoundedRectangle  # alternative name
        _RR_NAME = "RectangleRounded"
    except Exception as _e:
        RoundedRectangle = None
        _RR_NAME = None

# Stdlib
import os

try:
    from build123d import export_stl  # type: ignore
except Exception:
    export_stl = None  # type: ignore

"""
Rectangular block with 4 corner screw holes and a cable slot on the middle of one short side.
Default size: 50 x 30 x 10 mm (X x Y x Z)

Changes:
- Base solid is made from a *rounded rectangle* (XY corners rounded).
- Top perimeter still gets a small fillet to soften the Z-edge.
"""

# -----------------------------
# Parameters (adjust as needed)
# -----------------------------
BLOCK_W = 100.0   # X (width)  mm
BLOCK_H = 38.0   # Y (height) mm
BLOCK_T = 14.0   # Z (thick)  mm

# Corner rounding in XY (plan view)
# This controls the *corner shape* of the top/bottom faces.
CORNER_R = 5.0   # mm  (set 0 for sharp rectangle)

PILOT_DIA = 4.3                          # through hole diameter
HEAD_CBORE_DIA = 12.2         # counterbore diameter for screw head
HEAD_CBORE_DEPTH = 12.0                   # counterbore depth (flat-bottom)
HOLE_MARGIN = 9.0                        # inset of hole center from each block edge (mm)

# Cable slot parameters
SLOT_W = 8.0       # along X (slot width)
SLOT_H = 2.5       # along Z (slot height)
SLOT_D = 5.0       # along Y (slot depth into the part)

CLEAR_TO_HOLE = 0.5  # safety clearance (mm) from the hole center line

# Edge softening along Z at the top/bottom perimeters
TOP_EDGE_R = 0.0      # z-edge fillet at top (mm)
BOTTOM_EDGE_R = 0.0   # z-edge fillet at bottom (mm, set >0 to enable)

# Grid pattern parameters (cut into bottom flat surface)
TOTAL_GRIDS = 2        # number of separate grid areas to create along X-axis
GRID_SPACING = 2.0     # spacing between grid sections (mm)
GRID_LINE_WIDTH = 5   # width of each grid line (mm)
GRID_COLUMN_COUNT = 1  # number of columns in EACH grid
GRID_ROW_COUNT = 1     # number of rows in EACH grid
GRID_WIDTH = 80.0      # total width of ALL grids along X-axis (mm)
GRID_HEIGHT = 30.0     # total height of grid pattern along Y-axis (mm)
GRID_DEPTH = 0.1       # how deep to cut the grid lines (mm)

# Cable channel parameters (one channel per grid extending to edge)
CABLE_CHANNEL_WIDTH = 5.0   # width along X (mm)
CABLE_CHANNEL_DEPTH = 3.0   # depth into surface along Z (mm)

def create_simple_block(grid_offset_x: float = 0.0, grid_offset_y: float = 0.0) -> object:
    W, H, T = BLOCK_W, BLOCK_H, BLOCK_T

    with BuildPart() as p:
        # 1) Base: circle → extrude along X-axis (horizontal cylinder)
        from build123d import Plane, Box
        with BuildSketch(Plane.YZ) as sk:  # Sketch on YZ plane
            Circle(radius=H / 2.0)  # Using height as diameter for circular cross-section
        extrude(amount=W)  # Extrude along X-axis

        # 2) Cut the cylinder in half - remove BOTTOM part to keep top half
        # Position cutting plane at Z=0 and cut everything below it
        with BuildSketch(Plane.XY):
            Rectangle(W * 2, H * 2)  # Make sure it covers the full length
        extrude(amount=-H * 2, mode=Mode.SUBTRACT)  # Extrude downward to remove bottom half

        # 3) Add cubes at both ends of the long (90mm) side
        from build123d import Align
        cube_size = 10.0  # 10mm cube
        # Left side box
        with Locations((W + cube_size / 2, 0, 3)):
            Box(cube_size, 15, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # Right side box
        with Locations((0 - cube_size / 2, 0, 3)):
            Box(cube_size, 15, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
        
        # Add 5mm x 5mm hole at edge of half cylinder
        with BuildSketch(Plane.XY.offset(2.5)):  # Sketch at Z=5 to match other holes
            with Locations((W/2, H/2)):  # Position at center of length, at the edge (Y = radius - half hole width)
                Rectangle(10, 5)  # 5mm square hole
        extrude(amount=-2.5, mode=Mode.SUBTRACT)  # Drill down 5mm
        
        # 4) Add 4mm holes in the boxes
        from build123d import Plane
        hole_diameter = 4.0
        
        # Hole in left box - create plane at top of box and drill down
        with BuildSketch(Plane.XY.offset(8)):  # Sketch at Z=5 (top of boxes)
            with Locations((W + cube_size / 2, 0)):  # Position at left box center (95, 0)
                Circle(radius=hole_diameter / 2)
        extrude(amount=-8, mode=Mode.SUBTRACT)  # Drill down through the box
        
        # Hole in right box
        with BuildSketch(Plane.XY.offset(8)):  # Sketch at Z=5 (top of boxes)
            with Locations((0 - cube_size / 2, 0)):  # Position at right box center (-5, 0)
                Circle(radius=hole_diameter / 2)
        extrude(amount=-8, mode=Mode.SUBTRACT)  # Drill down through the box
        
        # 5) Add circular groove around the handle at the middle
        groove_width = 3.0  # Width along X-axis (mm)
        groove_depth = 2.0  # How deep into the surface (mm)
        
        # Create a ring-shaped groove by subtracting an annular cylinder
        # The ring cuts from the surface (H/2) inward by groove_depth
        with BuildSketch(Plane.YZ.offset(W/2 - groove_width/2)):
            Circle(radius=H/2)  # Outer circle (at the surface)
            Circle(radius=H/2 - groove_depth, mode=Mode.SUBTRACT)  # Inner circle (groove depth inward)
        extrude(amount=groove_width, mode=Mode.SUBTRACT)
        
        # 6) Add grid pattern on the bottom flat surface
        # Divide the total area into TOTAL_GRIDS sections, each with its own grid
        # Account for spacing between grids
        total_spacing = GRID_SPACING * (TOTAL_GRIDS - 1) if TOTAL_GRIDS > 1 else 0
        available_width = GRID_WIDTH - total_spacing  # width available for actual grids
        section_width = available_width / max(TOTAL_GRIDS, 1)  # width of each grid section
        
        # Create grids in each section
        for grid_idx in range(TOTAL_GRIDS):
            # Calculate the center position for this grid section
            # Start from left edge, add section widths and spacings
            section_start = (W - GRID_WIDTH) / 2 + grid_idx * (section_width + GRID_SPACING)
            section_center_x = section_start + section_width / 2 + grid_offset_x  # Apply X offset
            
            # Within this section, calculate the column and row spacing
            column_width = section_width / max(GRID_COLUMN_COUNT, 1)  # width of each column division
            row_height = GRID_HEIGHT / max(GRID_ROW_COUNT, 1)         # height of each row division
            
            # Create vertical lines (columns) for this grid section
            with BuildSketch(Plane.XY):
                for col_idx in range(GRID_COLUMN_COUNT):
                    # Position relative to this section's start
                    x_offset_in_section = (col_idx + 0.5) * column_width - section_width / 2
                    x_pos = section_center_x + x_offset_in_section
                    with Locations((x_pos, grid_offset_y)):  # Apply Y offset
                        Rectangle(GRID_LINE_WIDTH, GRID_HEIGHT)
            extrude(amount=GRID_DEPTH, mode=Mode.SUBTRACT)
            
            # Create horizontal lines (rows) for this grid section
            with BuildSketch(Plane.XY):
                for row_idx in range(GRID_ROW_COUNT):
                    y_pos = -GRID_HEIGHT/2 + (row_idx + 0.5) * row_height + grid_offset_y  # Apply Y offset
                    # Position horizontally to span only this section
                    with Locations((section_center_x, y_pos)):
                        Rectangle(section_width, GRID_LINE_WIDTH)
            extrude(amount=GRID_DEPTH, mode=Mode.SUBTRACT)
            
            # Add cable channel extending from this grid section to the outside edge
            # Channel extends from the bottom edge of the grid all the way to the flat surface edge
            slot_start_y = -GRID_HEIGHT/2 + grid_offset_y  # bottom edge of the grid (with Y offset)
            # Calculate how far to extend (to the edge of the flat surface at -H/2)
            channel_length = slot_start_y - (-H/2)  # distance from grid edge to surface edge
            slot_center_y = slot_start_y - channel_length/2  # center of channel
            with BuildSketch(Plane.XY):
                with Locations((section_center_x, slot_center_y)):
                    Rectangle(CABLE_CHANNEL_WIDTH, channel_length)
            extrude(amount=CABLE_CHANNEL_DEPTH, mode=Mode.SUBTRACT)

    return p.part


def create_test_station(clearance: float = 1.0) -> object:
    """
    Create a test station piece to hold ONE half of the gripper.
    Print two: one for bottom (holds gripper_A), one for top (holds gripper_B).
    When stacked, the two gripper halves come together.
    End walls are removed so the screw cubes can fit through.
    
    Args:
        clearance: Extra space around the gripper for easy fitting (mm)
    """
    W, H, T = BLOCK_W, BLOCK_H, BLOCK_T
    
    # Station dimensions - should match half-cylinder height
    station_length = W + 20  # Extra 10mm on each side for screw cubes
    station_width = H + 20   # Width for one half-cylinder plus space
    base_raise = 5.0  # Raise the groove 5mm up for thicker bottom
    gap_clearance = 2.0  # 2mm lower so stations don't touch when stacked
    total_height = H / 2 + clearance + base_raise - gap_clearance  # Reduced for gap
    
    # Weight plate dimensions
    plate_thickness = 5.0  # Thickness of the weight-stacking plate
    plate_extension = 40.0  # How much the plate extends beyond the station
    
    with BuildPart() as station:
        from build123d import Plane, Box, Align
        
        # 1) Add weight-stacking plate at the bottom
        plate_length = station_length + plate_extension
        plate_width = station_width + plate_extension
        
        with Locations((station_length / 2, 0, plate_thickness / 2)):
            Box(plate_length, plate_width, plate_thickness,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # 2) Create the station body on top of the plate
        body_z = plate_thickness + total_height / 2
        
        with Locations((station_length / 2, 0, body_z)):
            Box(station_length, station_width, total_height, 
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # 3) Cut semicircular groove for ONE half-cylinder
        # The semicircle matches the flat-bottom shape of each gripper half
        # Cut through the ENTIRE length (no end walls) so screw cubes fit
        # Raised 5mm up for thicker, more stable bottom, plus plate thickness
        cylinder_radius = H / 2 + clearance
        groove_z = cylinder_radius + base_raise + plate_thickness
        
        with BuildSketch(Plane.YZ):  # Start at X=0, no offset
            with Locations((0, groove_z)):  # Position raised up including plate
                Circle(radius=cylinder_radius)
        extrude(amount=station_length, mode=Mode.SUBTRACT)  # Cut all the way through
    
    return station.part


def export_block(base_name: str = "gripper") -> None:
    if export_stl is None:
        raise RuntimeError(
            "STL export is not available. Ensure your build123d version supports `export_stl`."
        )
    
    # Export first version with no offset (standard grid)
    out_path_1 = f"{base_name}_A.stl"
    os.makedirs(os.path.dirname(out_path_1) or ".", exist_ok=True)
    part_1 = create_simple_block(grid_offset_x=0.0, grid_offset_y=0.0)
    export_stl(part_1, out_path_1)
    print(f"Exported: {out_path_1}")
    
    # Export second version with 2.5mm offset (half grid line width) in both X and Y
    offset = GRID_LINE_WIDTH / 2  # 2.5mm offset
    out_path_2 = f"{base_name}_B.stl"
    part_2 = create_simple_block(grid_offset_x=offset, grid_offset_y=offset)
    export_stl(part_2, out_path_2)
    print(f"Exported: {out_path_2} (offset by {offset}mm in X and Y)")
    
    # Export test station
    out_path_station = f"{base_name}_test_station.stl"
    station = create_test_station(clearance=0.5)
    export_stl(station, out_path_station)
    print(f"Exported: {out_path_station} (test/calibration station)")


if __name__ == "__main__":
    export_block()
