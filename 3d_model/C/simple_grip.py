from __future__ import annotations

# build123d
from build123d import (
    BuildPart,
    BuildSketch,
    Locations,
    Rectangle,
    Circle,
    Mode,
    extrude,
    fillet,
    Plane,
    Box,
    Align,
)

import os

try:
    from build123d import export_stl
except Exception:
    export_stl = None

"""
Two grip designs with narrow middle sections:
- Type A: L-shaped grip with vertical block, narrow middle, and 2 screw holes at one end
- Type B: Straight bar with narrow middle and 4 screw holes (2 at each end)
Both have rounded top edges and counterbore screw holes.
"""

# -----------------------------
# Parameters (adjust as needed)
# -----------------------------
GRIP_LENGTH = 130.0     # X direction (mm)
GRIP_WIDTH = 30.0       # Y direction (mm)
GRIP_HEIGHT = 8.0      # Z direction (mm)

# Screw hole parameters
SCREW_HOLE_DIA = 6.2   # through hole diameter (mm)
SCREW_HEAD_DIA = 11.0    # counterbore diameter for screw head (mm)
SCREW_HEAD_DEPTH = 2.0  # counterbore depth (mm)
SCREW_SPACING = 15.0    # distance between screw centers (mm)

# Top edge rounding
TOP_EDGE_RADIUS = 2.0   # radius for rounding top edges and corners (mm)
# Vertical block under screws (creates L-shape - Type A only)
VERTICAL_BLOCK_HEIGHT = 1.0   # height of vertical block extending down (mm)
VERTICAL_BLOCK_LENGTH = 37.0   # length of vertical block (mm)
VERTICAL_BLOCK_WIDTH = GRIP_WIDTH  # width matches grip width for flush alignment (mm)

# Type B middle section narrowing
MIDDLE_WIDTH = 15.0     # width of the narrow middle section (mm)
END_SECTION_LENGTH = 37.0  # length of full-width sections at each end (mm)

def create_grip_a() -> object:
    """
    Create Type A grip - L-shaped with:
    - Full-width section at screw end
    - Narrower middle section  
    - Vertical block extending down from screw area (creates L-shape)
    - Rounded top edges and corners
    - Two screw holes with counterbore at one end
    """
    
    with BuildPart() as part:
        # 1) Create narrow middle section
        middle_length = GRIP_LENGTH - END_SECTION_LENGTH
        middle_x_offset = -END_SECTION_LENGTH / 2  # Offset toward negative X
        with Locations((middle_x_offset, 0, GRIP_HEIGHT / 2)):
            Box(middle_length, MIDDLE_WIDTH, GRIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # 2) Add full-width end section at positive X (where screws are)
        end_x_pos = GRIP_LENGTH / 2 - END_SECTION_LENGTH / 2
        with Locations((end_x_pos, 0, GRIP_HEIGHT / 2)):
            Box(END_SECTION_LENGTH, GRIP_WIDTH, GRIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # 3) Add vertical block under the screw area (creates L-shape)
        # Position flush with the top edge of horizontal grip
        block_x = GRIP_LENGTH / 2 - VERTICAL_BLOCK_LENGTH / 2  # Flush with top edge
        block_z = -VERTICAL_BLOCK_HEIGHT / 2  # Extends downward from Z=0
        
        with Locations((block_x, 0, block_z)):
            Box(VERTICAL_BLOCK_LENGTH, VERTICAL_BLOCK_WIDTH, VERTICAL_BLOCK_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # 4) Round the top edges
        # Get all edges at the top face (Z = GRIP_HEIGHT)
        top_edges = part.part.edges().filter_by(
            lambda e: e.center().Z > GRIP_HEIGHT - 0.1
        )
        if top_edges:
            fillet(top_edges, radius=TOP_EDGE_RADIUS)
        
        # 5) Add screw holes with counterbore
        # Position screws 12mm from the top edge (furthest X), spaced along Y
        screw_x = GRIP_LENGTH / 2 - 12  # 12mm from the top edge
        screw1_y = -SCREW_SPACING / 2
        screw2_y = SCREW_SPACING / 2
        
        # Total depth for screw holes (through horizontal part and into vertical block)
        total_screw_depth = GRIP_HEIGHT + VERTICAL_BLOCK_HEIGHT
        
        for screw_y in [screw1_y, screw2_y]:
            # Counterbore for screw head (from top)
            with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                with Locations((screw_x, screw_y)):
                    Circle(radius=SCREW_HEAD_DIA / 2)
            extrude(amount=-SCREW_HEAD_DEPTH, mode=Mode.SUBTRACT)
            
            # Through hole for screw shaft (through horizontal part and into vertical block)
            with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                with Locations((screw_x, screw_y)):
                    Circle(radius=SCREW_HOLE_DIA / 2)
            extrude(amount=-total_screw_depth, mode=Mode.SUBTRACT)
    
    return part.part


def create_grip_b() -> object:
    """
    Create Type B grip - Straight horizontal bar with:
    - Full-width sections at both ends (for screw mounting)
    - Narrower middle section
    - Rounded top edges and corners
    - Four screw holes with counterbore (two at each end along X direction)
    """
    
    with BuildPart() as part:
        # 1) Create narrow middle section
        middle_length = GRIP_LENGTH - 2 * END_SECTION_LENGTH
        with Locations((0, 0, GRIP_HEIGHT / 2)):
            Box(middle_length, MIDDLE_WIDTH, GRIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # 2) Add full-width end sections for screw mounting
        # Positive X end
        end_x_pos = GRIP_LENGTH / 2 - END_SECTION_LENGTH / 2
        with Locations((end_x_pos, 0, GRIP_HEIGHT / 2)):
            Box(END_SECTION_LENGTH, GRIP_WIDTH, GRIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Negative X end
        end_x_neg = -(GRIP_LENGTH / 2 - END_SECTION_LENGTH / 2)
        with Locations((end_x_neg, 0, GRIP_HEIGHT / 2)):
            Box(END_SECTION_LENGTH, GRIP_WIDTH, GRIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # 3) Round the top edges
        # Get all edges at the top face (Z = GRIP_HEIGHT)
        top_edges = part.part.edges().filter_by(
            lambda e: e.center().Z > GRIP_HEIGHT - 0.1
        )
        if top_edges:
            fillet(top_edges, radius=TOP_EDGE_RADIUS)
        
        # 4) Add screw holes with counterbore at both ends
        # Position screws 12mm from each edge (positive and negative X), spaced along Y
        screw_x_positions = [
            GRIP_LENGTH / 2 - 12,   # Near positive X edge
            -(GRIP_LENGTH / 2 - 12)  # Near negative X edge
        ]
        screw1_y = -SCREW_SPACING / 2
        screw2_y = SCREW_SPACING / 2
        
        for screw_x in screw_x_positions:
            for screw_y in [screw1_y, screw2_y]:
                # Counterbore for screw head (from top)
                with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                    with Locations((screw_x, screw_y)):
                        Circle(radius=SCREW_HEAD_DIA / 2)
                extrude(amount=-SCREW_HEAD_DEPTH, mode=Mode.SUBTRACT)
                
                # Through hole for screw shaft
                with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                    with Locations((screw_x, screw_y)):
                        Circle(radius=SCREW_HOLE_DIA / 2)
                extrude(amount=-GRIP_HEIGHT, mode=Mode.SUBTRACT)
    
    return part.part


def export_grips(base_name: str = "simple_grip") -> None:
    """Export both Type A and Type B grips to STL files"""
    if export_stl is None:
        raise RuntimeError(
            "STL export is not available. Ensure your build123d version supports `export_stl`."
        )
    
    # Export Type A (L-shaped with vertical block and narrow middle)
    out_path_a = f"{base_name}_A.stl"
    os.makedirs(os.path.dirname(out_path_a) or ".", exist_ok=True)
    part_a = create_grip_a()
    export_stl(part_a, out_path_a)
    print(f"Exported: {out_path_a}")
    print(f"  Type A - L-shaped grip with narrow middle:")
    print(f"    Overall length: {GRIP_LENGTH}mm, Height: {GRIP_HEIGHT}mm")
    print(f"    End section: {END_SECTION_LENGTH}mm x {GRIP_WIDTH}mm (full width, with vertical block)")
    print(f"    Middle section: {GRIP_LENGTH - END_SECTION_LENGTH}mm x {MIDDLE_WIDTH}mm (narrow)")
    print(f"    Vertical block: {VERTICAL_BLOCK_LENGTH}mm x {VERTICAL_BLOCK_WIDTH}mm x {VERTICAL_BLOCK_HEIGHT}mm")
    print(f"    2 screw holes at one end, spacing: {SCREW_SPACING}mm")
    print()
    
    # Export Type B (straight bar with narrower middle and screw holes at both ends)
    out_path_b = f"{base_name}_B.stl"
    part_b = create_grip_b()
    export_stl(part_b, out_path_b)
    print(f"Exported: {out_path_b}")
    print(f"  Type B - Bar with narrow middle:")
    print(f"    Overall length: {GRIP_LENGTH}mm, Height: {GRIP_HEIGHT}mm")
    print(f"    End sections: {END_SECTION_LENGTH}mm x {GRIP_WIDTH}mm (full width)")
    print(f"    Middle section: {GRIP_LENGTH - 2 * END_SECTION_LENGTH}mm x {MIDDLE_WIDTH}mm (narrow)")
    print(f"    4 screw holes (2 at each end, 12mm from edges)")
    print(f"    Screw spacing: {SCREW_SPACING}mm")


if __name__ == "__main__":
    export_grips()

