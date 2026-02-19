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
    fillet,
    Align,
    Vector,
    Axis,
    Location,
)

# Stdlib
import os

try:
    from build123d import export_stl  # type: ignore
except Exception:
    export_stl = None  # type: ignore

"""
Dual sensor gripper: Integrated design with two sensor blocks embedded into a unified grip bar.
The sensor blocks slide in from ±X faces (facing each other toward the center).
Overall width is ~36mm with sensors integrated into the grip structure.

SENSOR_FRONT_INSET controls how deep the sensor sits from the outer face:
- Set to 0mm for sensors flush with outer face (default)
- Increase (e.g., 5mm, 10mm) to position force sensing point more toward the inside/center
- When > 0, entry channels are cut from outer faces so sensors can still slide in from outside
- Sensors stop at SENSOR_FRONT_INSET depth (wall acts as stop)
"""

# -----------------------------
# Test mode for material saving
# -----------------------------
TEST_MODE = False  # Set to True for smaller test prints, False for full size

# TEST MODE dimensions:
#   - Total length: 100mm (30+40+30)
#   - Block length: 30mm each end (channel depth 26mm with 4mm back wall)
#   - Heights: 10mm (vs 15mm full) - THIS is where we save material!
#   - Grip length: 40mm (vs 80mm full)
#   - Screw spacing: 20mm (vs 30mm full)
#   - Full size: 140mm (30+80+30) with 15mm height
#   - Saves ~35% material by reducing heights and grip length!

# -----------------------------
# Import sensor block parameters
# -----------------------------
# Sensor dimensions (the part that slides in)
SENSOR_WIDTH = 34.0    # Width of sensor (mm) = 3.4 cm
SENSOR_DEPTH = 34.0    # Depth of sensor (mm) = 3.4 cm
SENSOR_THICKNESS = 2.6 # Thickness of sensor (mm)

# Block dimensions
if TEST_MODE:
    BLOCK_LENGTH = 30.0    # X direction (mm) - total block section length
    BLOCK_WIDTH = 36.0     # Y direction (mm) - keep same for sensor fit
    BLOCK_HEIGHT = 10.0    # Z direction (mm) - REDUCED HEIGHT for testing (saves material!)
else:
    BLOCK_LENGTH = 30.0    # X direction (mm) - total block section length
    BLOCK_WIDTH = 36.0     # Y direction (mm) - overall width of plastic ~36mm
    BLOCK_HEIGHT = 15.0    # Z direction (mm) - taller than sensor + inner component + walls

# C-shaped slide mechanism parameters
SLIDE_WALL_THICKNESS = 3.0  # thickness of the C-walls (mm) - left/right/top walls
CLEARANCE = 0.2        # Extra clearance for easy sliding (mm)
BOTTOM_LIP_HEIGHT = 3.0  # Height of bottom lip to hold sensor from below (mm)

# Sensor inner component parameters (raised part on top of sensor)
INNER_COMPONENT_SIDE_INSET = 4.0  # Distance from each side where inner component starts (mm)
INNER_COMPONENT_HEIGHT = 6.0  # Additional height needed for inner component (mm)
SENSOR_BACK_INSET = 0.0  # Distance from back where sensor channel ends (mm) - NOW 0 for full depth
SENSOR_FRONT_INSET = 20.0  # Distance from outer face where sensor channel starts (mm) - controls how deep sensor sits
SIDE_BRACKET_DEPTH = 4.0  # Depth of side bracket section at the back (mm)
SIDE_BRACKET_HEIGHT = 6.0  # Height of side brackets (partial, not full height) (mm)

# -----------------------------
# Grip bar parameters
# -----------------------------
if TEST_MODE:
    GRIP_LENGTH = 40.0     # Length of grip bar - HALF LENGTH for testing (mm) → 80mm total
    GRIP_WIDTH = 36.0       # Width at the ends where it connects to blocks (matches BLOCK_WIDTH)
    GRIP_HEIGHT = 10.0       # Height/thickness of grip bar - REDUCED for testing (mm) → saves material!
    GRIP_MIDDLE_WIDTH = 36.0  # Width of middle section (mm) - matches BLOCK_WIDTH for unified design
    GRIP_END_LENGTH = 20.0    # Length of full-width sections at each end (mm) - same as full
    TOP_EDGE_RADIUS = 4.0     # Radius for rounding top edges (mm)
else:
    GRIP_LENGTH = 80.0     # Length of grip bar connecting the two sensor blocks (mm)
    GRIP_WIDTH = 36.0       # Width at the ends where it connects to blocks (matches BLOCK_WIDTH)
    GRIP_HEIGHT = 15.0       # Height/thickness of grip bar (mm)
    GRIP_MIDDLE_WIDTH = 36.0  # Width of middle section (mm) - matches BLOCK_WIDTH for unified design
    GRIP_END_LENGTH = 20.0    # Length of full-width sections at each end (mm)
    TOP_EDGE_RADIUS = 4.0     # Radius for rounding top edges (mm)

# Screw hole parameters for connecting counterplate
SCREW_HOLE_DIA = 3.9      # M3 through hole diameter (mm) - increased by 0.8mm for easier threading
SCREW_HEAD_DIA = 11.5     # Counterbore diameter for screw head/nut (mm) - fits 11mm
if TEST_MODE:
    SCREW_HEAD_DEPTH = 5.0    # Counterbore depth (mm) - REDUCED for thinner test parts
    SCREW_SPACING = 20.0      # Distance between screw holes (mm) - REDUCED for shorter test grip
else:
    SCREW_HEAD_DEPTH = 8.0    # Counterbore depth (mm) - very deep inset
    SCREW_SPACING = 30.0      # Distance between screw holes (mm)
NUM_SCREW_HOLES = 2       # Number of screw holes in grip

# Overall gripper dimensions
TOTAL_GRIPPER_LENGTH = 2 * BLOCK_LENGTH + GRIP_LENGTH  # Total span (mm)


def create_sensor_slide_block() -> object:
    """
    Create a sensor slide block with rounded top edges and corners.
    The sensor channel is recessed from the back by SENSOR_BACK_INSET (4mm)
    for a more compact, integrated design.
    """
    # Calculate channel dimensions with clearance
    channel_width = SENSOR_WIDTH + CLEARANCE
    channel_depth = SENSOR_DEPTH
    channel_height = SENSOR_THICKNESS + CLEARANCE
    
    with BuildPart() as p:
        # 1) Create the main block (solid base)
        Box(BLOCK_LENGTH, BLOCK_WIDTH, BLOCK_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        
        # 2) Cut the main C-shaped channel from the front
        # Position channel so it's recessed from the back by SENSOR_BACK_INSET
        # Channel opens at the front (negative Y), back wall at positive Y
        channel_y_offset = BLOCK_WIDTH/2 - SENSOR_BACK_INSET - channel_depth/2
        channel_z_center = BOTTOM_LIP_HEIGHT + channel_height/2
        
        with Locations((0, -channel_y_offset, channel_z_center)):
            Box(channel_width, channel_depth, channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # 3) Cut additional taller channel for sensor's raised inner component
        inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)
        inner_channel_depth = channel_depth
        inner_channel_height = channel_height + INNER_COMPONENT_HEIGHT
        inner_z_center = BOTTOM_LIP_HEIGHT + inner_channel_height/2
        
        with Locations((0, -channel_y_offset, inner_z_center)):
            Box(inner_channel_width, inner_channel_depth, inner_channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # 4) Cut out the center of the bottom lip
        bottom_cutout_width = inner_channel_width
        bottom_cutout_depth = channel_depth
        bottom_cutout_height = BOTTOM_LIP_HEIGHT
        bottom_cutout_z_center = bottom_cutout_height / 2
        
        with Locations((0, -channel_y_offset, bottom_cutout_z_center)):
            Box(bottom_cutout_width, bottom_cutout_depth, bottom_cutout_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # 5) Round the top edges (back and sides, not the front sensor opening)
        # Get the top edges that are not on the front (sensor opening is at Y negative)
        top_edges = p.part.edges().filter_by(
            lambda e: e.center().Z > BLOCK_HEIGHT - 0.1
        )
        
        # Filter to only back and side edges (not front where sensor opens)
        back_side_edges = [e for e in top_edges if e.center().Y > -BLOCK_WIDTH/4]
        
        if back_side_edges:
            try:
                fillet(back_side_edges, radius=TOP_EDGE_RADIUS)
            except ValueError:
                # If fails, try smaller radius
                try:
                    fillet(back_side_edges, radius=1.0)
                except ValueError:
                    pass
    
    return p.part


def create_grip_bar(add_screw_holes: bool = True) -> object:
    """
    Create a narrow rounded grip bar with optional counterbore screw holes.
    """
    with BuildPart() as part:
        # Create narrow grip bar (full length, no wider end sections)
        with Locations((0, 0, GRIP_HEIGHT / 2)):
            Box(GRIP_LENGTH, GRIP_MIDDLE_WIDTH, GRIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Add screw holes with counterbore if requested
        if add_screw_holes:
            # Calculate screw positions along X axis, centered
            if NUM_SCREW_HOLES == 2:
                screw_positions = [
                    -SCREW_SPACING / 2,
                    SCREW_SPACING / 2
                ]
            else:
                screw_positions = [0]  # Single hole at center
            
            # Create counterbore holes (with screw head insets)
            for screw_x in screw_positions:
                # Counterbore for screw head (from top)
                with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                    with Locations((screw_x, 0)):
                        Circle(radius=SCREW_HEAD_DIA / 2)
                extrude(amount=-SCREW_HEAD_DEPTH, mode=Mode.SUBTRACT)
                
                # Through hole for screw shaft
                with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                    with Locations((screw_x, 0)):
                        Circle(radius=SCREW_HOLE_DIA / 2)
                extrude(amount=-GRIP_HEIGHT, mode=Mode.SUBTRACT)
        
        # Round the long outer edges (parallel to X axis) on top
        # These are the edges on the sides of the grip that run lengthwise
        outer_edges = part.part.edges().filter_by(
            lambda e: e.center().Z > GRIP_HEIGHT - 0.1 and 
                     abs(abs(e.center().Y) - GRIP_MIDDLE_WIDTH/2) < 0.5
        )
        if outer_edges:
            try:
                fillet(outer_edges, radius=TOP_EDGE_RADIUS)
            except ValueError:
                # If fillet fails with large radius, try smaller
                try:
                    fillet(outer_edges, radius=1.0)
                except ValueError:
                    pass
    
    return part.part


def create_sensor_pressing_part() -> object:
    """
    Create a pressing part that fits into the sensor bottom cutout.
    """
    # Calculate dimensions for the pressing part (fits into bottom cutout)
    inner_channel_width = SENSOR_WIDTH + CLEARANCE - (2 * INNER_COMPONENT_SIDE_INSET)
    
    # Pressing plate dimensions (0.5mm smaller on all sides)
    FITTING_CLEARANCE = 0.5
    PRESSING_HEIGHT_EXTENSION = 2.0  # Extra height to ensure sensor is pressed (mm)
    plate_width = inner_channel_width - (2 * FITTING_CLEARANCE)
    plate_depth = SENSOR_DEPTH - (2 * FITTING_CLEARANCE)
    plate_height = BOTTOM_LIP_HEIGHT - FITTING_CLEARANCE + PRESSING_HEIGHT_EXTENSION
    
    with BuildPart() as p:
        # Create the pressing part that fits into the bottom cutout
        Box(plate_width, plate_depth, plate_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    
    return p.part


def create_dual_sensor_counterplate() -> object:
    """
    Create a counterplate with two pressing parts and a grip bar with screw holes.
    The pressing parts extend down below the grip bar to press on sensors.
    Now oriented to match sensors that slide in from X faces.
    """
    # Calculate pressing part dimensions - oriented for X-axis sensor insertion
    inner_channel_width = SENSOR_WIDTH + CLEARANCE - (2 * INNER_COMPONENT_SIDE_INSET)
    FITTING_CLEARANCE = 0.5
    PRESSING_HEIGHT_EXTENSION = 2.0
    
    # Pressing part dimensions (oriented for X-axis insertion)
    # X: depth of pressing part (how far it extends into channel, excluding bracket section)
    # Y: width of pressing part (fits between side insets)
    # Z: height extending down
    # Matches the front section depth (excluding the 4mm bracket section at back)
    plate_x_depth = (BLOCK_LENGTH - SENSOR_BACK_INSET - SIDE_BRACKET_DEPTH) - (2 * FITTING_CLEARANCE)
    plate_y_width = inner_channel_width - (2 * FITTING_CLEARANCE)
    plate_height = BOTTOM_LIP_HEIGHT - FITTING_CLEARANCE + PRESSING_HEIGHT_EXTENSION
    
    total_length = GRIP_LENGTH + (2 * BLOCK_LENGTH)
    
    with BuildPart() as assembly:
        # 1) Create the full-length grip bar (matching the gripper)
        Box(total_length, GRIP_MIDDLE_WIDTH, GRIP_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        
        # 2) Add screw holes in the center grip section
        if NUM_SCREW_HOLES == 2:
            screw_positions = [-SCREW_SPACING / 2, SCREW_SPACING / 2]
        else:
            screw_positions = [0]
        
        for screw_x in screw_positions:
            # Counterbore for screw head (from top)
            with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                with Locations((screw_x, 0)):
                    Circle(radius=SCREW_HEAD_DIA / 2)
            extrude(amount=-SCREW_HEAD_DEPTH, mode=Mode.SUBTRACT)
            
            # Through hole for screw shaft
            with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                with Locations((screw_x, 0)):
                    Circle(radius=SCREW_HOLE_DIA / 2)
            extrude(amount=-GRIP_HEIGHT, mode=Mode.SUBTRACT)
        
        # 3) Add pressing parts that extend DOWN from the end sections
        # These fit into the bottom cutouts and press the sensors from below
        # Positioned to match the channels (accounting for front inset, excluding bracket section)
        
        # Left pressing part (at -X end, extends downward from face + front inset)
        left_face_x = -(total_length / 2)
        actual_slide_depth = BLOCK_LENGTH - SENSOR_BACK_INSET
        front_depth_press = actual_slide_depth - SIDE_BRACKET_DEPTH  # Don't extend into bracket section
        left_pressing_x = left_face_x + SENSOR_FRONT_INSET + front_depth_press / 2
        
        with Locations((left_pressing_x, 0, -plate_height / 2)):
            Box(plate_x_depth, plate_y_width, plate_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.ADD)
        
        # Right pressing part (at +X end, extends downward from face + front inset)
        right_face_x = (total_length / 2)
        right_pressing_x = right_face_x - SENSOR_FRONT_INSET - front_depth_press / 2
        
        with Locations((right_pressing_x, 0, -plate_height / 2)):
            Box(plate_x_depth, plate_y_width, plate_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.ADD)
        
        # 4) Round the top outer edges (not screw holes)
        # Get edges at the top of the grip bar
        top_edges = assembly.part.edges().filter_by(
            lambda e: e.center().Z > GRIP_HEIGHT - 0.1 and
                     abs(e.center().Z - GRIP_HEIGHT) < 0.1  # Exactly at top surface
        )
        
        # Filter to get the long outer edges parallel to X (avoid screw hole circles)
        # These are the edges along Y = ±GRIP_MIDDLE_WIDTH/2
        outer_long_edges = [e for e in top_edges 
                           if abs(abs(e.center().Y) - GRIP_MIDDLE_WIDTH/2) < 0.5 and
                           e.length > 10]  # Long edges, not circular screw hole edges
        
        if outer_long_edges:
            try:
                fillet(outer_long_edges, radius=TOP_EDGE_RADIUS)
            except ValueError:
                try:
                    fillet(outer_long_edges, radius=1.0)
                except ValueError:
                    pass
    
    return assembly.part


def create_dual_sensor_gripper() -> object:
    """
    Create an integrated gripper with sensor channels cut directly into the grip bar ends.
    """
    # Calculate channel dimensions with clearance
    channel_width = SENSOR_WIDTH + CLEARANCE
    channel_depth = SENSOR_DEPTH
    channel_height = SENSOR_THICKNESS + CLEARANCE
    
    with BuildPart() as gripper:
        # 1) Create extended grip bar (includes sensor block sections at each end)
        total_length = GRIP_LENGTH + (2 * BLOCK_LENGTH)
        Box(total_length, GRIP_MIDDLE_WIDTH, GRIP_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        
        # 2) Add screw holes in the center grip section
        if NUM_SCREW_HOLES == 2:
            screw_positions = [-SCREW_SPACING / 2, SCREW_SPACING / 2]
        else:
            screw_positions = [0]
        
        for screw_x in screw_positions:
            # Counterbore for screw head (from top)
            with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                with Locations((screw_x, 0)):
                    Circle(radius=SCREW_HEAD_DIA / 2)
            extrude(amount=-SCREW_HEAD_DEPTH, mode=Mode.SUBTRACT)
            
            # Through hole for screw shaft
            with BuildSketch(Plane.XY.offset(GRIP_HEIGHT)):
                with Locations((screw_x, 0)):
                    Circle(radius=SCREW_HOLE_DIA / 2)
            extrude(amount=-GRIP_HEIGHT, mode=Mode.SUBTRACT)
        
        # 3) Cut sensor channels at both ends
        # Channels are cut FROM the end faces, sensor slides in along X-axis
        # Sensor dimensions when sliding in from X face:
        #   - X: depth sensor slides in (now full BLOCK_LENGTH with 0mm back inset)
        #   - Y: width of sensor (SENSOR_WIDTH)
        #   - Z: thickness of sensor (SENSOR_THICKNESS)
        # The last 4mm has side brackets (partial height) to hold sensor
        actual_slide_depth = BLOCK_LENGTH - SENSOR_BACK_INSET  # 30mm - 0mm = 30mm (test mode)
        
        # Y position: channel is centered in Y, no offset needed for slide-in from X
        # Z position: bottom of channel starts at BOTTOM_LIP_HEIGHT
        channel_z_center = BOTTOM_LIP_HEIGHT + channel_height/2
        
        # Inner component dimensions
        inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)
        inner_channel_height = channel_height + INNER_COMPONENT_HEIGHT
        inner_z_center = BOTTOM_LIP_HEIGHT + inner_channel_height/2
        
        # Side bracket dimensions (for the back 4mm section)
        # Uses same width and height as main channel for clean cutout
        bracket_section_depth = SIDE_BRACKET_DEPTH  # 4mm at the back
        bracket_cutout_width = channel_width  # Same as main channel (SENSOR_WIDTH + CLEARANCE)
        bracket_cutout_height = channel_height  # Same as main channel
        bracket_z_center = BOTTOM_LIP_HEIGHT + bracket_cutout_height/2
        
        # Left sensor channel (cut from -X face, extends inward in +X direction)
        # The -X face is at -(total_length/2), channel starts FROM the face + front inset
        left_face_x = -(total_length / 2)
        
        # Entry channels (left) - from outer face to sensor position (allows slide-in from outside)
        # Extend ALL cutouts (main, inner, bottom) through the entry section
        if SENSOR_FRONT_INSET > 0:
            left_entry_x = left_face_x + SENSOR_FRONT_INSET / 2
            
            # Main entry channel
            with Locations((left_entry_x, 0, channel_z_center)):
                Box(SENSOR_FRONT_INSET, channel_width, channel_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                    mode=Mode.SUBTRACT)
            
            # Inner component entry channel
            with Locations((left_entry_x, 0, inner_z_center)):
                Box(SENSOR_FRONT_INSET, inner_channel_width, inner_channel_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                    mode=Mode.SUBTRACT)
            
            # Bottom cutout entry channel
            with Locations((left_entry_x, 0, BOTTOM_LIP_HEIGHT / 2)):
                Box(SENSOR_FRONT_INSET, inner_channel_width, BOTTOM_LIP_HEIGHT,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                    mode=Mode.SUBTRACT)
        
        # Front section (full width channels) - most of the slide depth
        front_depth = actual_slide_depth - bracket_section_depth
        # Position channel starting at SENSOR_FRONT_INSET from the outer face
        left_front_x = left_face_x + SENSOR_FRONT_INSET + front_depth / 2
        
        # Main channel (left front) - sensor slides along X, width is in Y
        with Locations((left_front_x, 0, channel_z_center)):
            Box(front_depth, channel_width, channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # Inner component channel (left front)
        with Locations((left_front_x, 0, inner_z_center)):
            Box(front_depth, inner_channel_width, inner_channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # Bottom cutout (left front)
        with Locations((left_front_x, 0, BOTTOM_LIP_HEIGHT / 2)):
            Box(front_depth, inner_channel_width, BOTTOM_LIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # Back section (side brackets) - last 4mm with clean cutout
        # This leaves side walls to hold the sensor (same dimensions as front)
        left_bracket_x = left_face_x + SENSOR_FRONT_INSET + front_depth + bracket_section_depth / 2
        
        # Cut channel in back section with same width/height as front (leaving side brackets)
        with Locations((left_bracket_x, 0, bracket_z_center)):
            Box(bracket_section_depth, bracket_cutout_width, bracket_cutout_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # Right sensor channel (cut from +X face, extends inward in -X direction)
        # The +X face is at +(total_length/2), channel starts FROM the face + front inset
        right_face_x = (total_length / 2)
        
        # Entry channels (right) - from outer face to sensor position (allows slide-in from outside)
        # Extend ALL cutouts (main, inner, bottom) through the entry section
        if SENSOR_FRONT_INSET > 0:
            right_entry_x = right_face_x - SENSOR_FRONT_INSET / 2
            
            # Main entry channel
            with Locations((right_entry_x, 0, channel_z_center)):
                Box(SENSOR_FRONT_INSET, channel_width, channel_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                    mode=Mode.SUBTRACT)
            
            # Inner component entry channel
            with Locations((right_entry_x, 0, inner_z_center)):
                Box(SENSOR_FRONT_INSET, inner_channel_width, inner_channel_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                    mode=Mode.SUBTRACT)
            
            # Bottom cutout entry channel
            with Locations((right_entry_x, 0, BOTTOM_LIP_HEIGHT / 2)):
                Box(SENSOR_FRONT_INSET, inner_channel_width, BOTTOM_LIP_HEIGHT,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                    mode=Mode.SUBTRACT)
        
        # Front section (full width channels) - most of the slide depth
        # Position channel starting at SENSOR_FRONT_INSET from the outer face
        right_front_x = right_face_x - SENSOR_FRONT_INSET - front_depth / 2
        
        # Main channel (right front) - sensor slides along X, width is in Y
        with Locations((right_front_x, 0, channel_z_center)):
            Box(front_depth, channel_width, channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # Inner component channel (right front)
        with Locations((right_front_x, 0, inner_z_center)):
            Box(front_depth, inner_channel_width, inner_channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # Bottom cutout (right front)
        with Locations((right_front_x, 0, BOTTOM_LIP_HEIGHT / 2)):
            Box(front_depth, inner_channel_width, BOTTOM_LIP_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # Back section (side brackets) - last 4mm with clean cutout
        # This leaves side walls to hold the sensor (same dimensions as front)
        right_bracket_x = right_face_x - SENSOR_FRONT_INSET - front_depth - bracket_section_depth / 2
        
        # Cut channel in back section with same width/height as front (leaving side brackets)
        with Locations((right_bracket_x, 0, bracket_z_center)):
            Box(bracket_section_depth, bracket_cutout_width, bracket_cutout_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)
        
        # 4) Round the top outer edges (not screw holes)
        # Get edges at the top of the grip bar
        top_edges = gripper.part.edges().filter_by(
            lambda e: e.center().Z > GRIP_HEIGHT - 0.1 and
                     abs(e.center().Z - GRIP_HEIGHT) < 0.1  # Exactly at top surface
        )
        
        # Filter to get the long outer edges parallel to X (avoid screw hole circles)
        # These are the edges along Y = ±GRIP_MIDDLE_WIDTH/2
        outer_long_edges = [e for e in top_edges 
                           if abs(abs(e.center().Y) - GRIP_MIDDLE_WIDTH/2) < 0.5 and
                           e.length > 10]  # Long edges, not circular screw hole edges
        
        if outer_long_edges:
            try:
                fillet(outer_long_edges, radius=TOP_EDGE_RADIUS)
            except ValueError:
                try:
                    fillet(outer_long_edges, radius=1.0)
                except ValueError:
                    pass
    
    return gripper.part


def export_dual_gripper(base_name: str = "dual_sensor_gripper") -> None:
    """
    Export the dual sensor gripper as an STL file.
    """
    if export_stl is None:
        raise RuntimeError(
            "STL export is not available. Ensure your build123d version supports `export_stl`."
        )
    
    out_path = f"{base_name}.stl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = create_dual_sensor_gripper()
    export_stl(part, out_path)
    
    print(f"Exported: {out_path}")
    if TEST_MODE:
        print(f"\n*** TEST MODE ACTIVE - REDUCED DIMENSIONS FOR MATERIAL SAVING ***")
    print(f"\n=== Dual Sensor Gripper (Integrated Design) ===")
    print(f"  Total length: {TOTAL_GRIPPER_LENGTH}mm")
    print(f"  Overall width: {BLOCK_WIDTH}mm (~36mm unified design)")
    actual_slide_depth = BLOCK_LENGTH - SENSOR_BACK_INSET
    channel_width = SENSOR_WIDTH + CLEARANCE
    inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)
    front_depth = actual_slide_depth - SIDE_BRACKET_DEPTH
    print(f"\n  Sensor blocks (2x) - INTEGRATED into grip:")
    print(f"    Dimensions: {BLOCK_LENGTH}mm (L) x {BLOCK_WIDTH}mm (W) x {BLOCK_HEIGHT}mm (H)")
    print(f"    Openings: Face inward toward each other (from ±X)")
    if SENSOR_FRONT_INSET > 0:
        print(f"    Entry channel: {SENSOR_FRONT_INSET}mm (X) x {channel_width}mm (Y) - slide in from outer face")
        print(f"    Sensor final position: {SENSOR_FRONT_INSET}mm from outer face")
    else:
        print(f"    Sensor position: Flush with outer face")
    print(f"    Sensor slide depth: {actual_slide_depth}mm (channel depth)")
    print(f"    Front channel: {front_depth}mm (X) x {channel_width}mm (Y) x {SENSOR_THICKNESS + CLEARANCE}mm (H)")
    print(f"    Back bracket section: {SIDE_BRACKET_DEPTH}mm (X) x {channel_width}mm (Y) x {SENSOR_THICKNESS + CLEARANCE}mm (H)")
    print(f"      └─ Clean cutout with side brackets holding sensor in last 4mm")
    print(f"    Inner channel: {front_depth}mm (X) x {inner_channel_width}mm (Y)")
    print(f"    Sensor size: {SENSOR_WIDTH}mm x {SENSOR_DEPTH}mm x {SENSOR_THICKNESS}mm thick")
    print(f"    Side inset: {INNER_COMPONENT_SIDE_INSET}mm")
    print(f"    Rounded top edges: {TOP_EDGE_RADIUS}mm radius")
    print(f"\n  Grip bar:")
    print(f"    Length: {GRIP_LENGTH}mm")
    print(f"    Width: {GRIP_MIDDLE_WIDTH}mm (unified width with blocks)")
    print(f"    Height: {GRIP_HEIGHT}mm")
    print(f"    Screw holes: {NUM_SCREW_HOLES}x M3 with counterbore")
    print(f"      - Through hole: Ø{SCREW_HOLE_DIA}mm (increased for easier threading)")
    print(f"      - Counterbore: Ø{SCREW_HEAD_DIA}mm x {SCREW_HEAD_DEPTH}mm deep (for screw head)")
    print(f"      - Spacing: {SCREW_SPACING}mm")
    print(f"    Rounded edges: {TOP_EDGE_RADIUS}mm radius")


def export_dual_counterplate(base_name: str = "dual_sensor_counterplate") -> None:
    """
    Export the dual sensor counterplate as an STL file.
    """
    if export_stl is None:
        raise RuntimeError(
            "STL export is not available. Ensure your build123d version supports `export_stl`."
        )
    
    out_path = f"{base_name}.stl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = create_dual_sensor_counterplate()
    export_stl(part, out_path)
    
    # Calculate dimensions for display
    inner_channel_width = SENSOR_WIDTH + CLEARANCE - (2 * INNER_COMPONENT_SIDE_INSET)
    FITTING_CLEARANCE = 0.5
    PRESSING_HEIGHT_EXTENSION = 2.0
    plate_x_depth = (BLOCK_LENGTH - SENSOR_BACK_INSET - SIDE_BRACKET_DEPTH) - (2 * FITTING_CLEARANCE)
    plate_y_width = inner_channel_width - (2 * FITTING_CLEARANCE)
    plate_height = BOTTOM_LIP_HEIGHT - FITTING_CLEARANCE + PRESSING_HEIGHT_EXTENSION
    actual_slide_depth = BLOCK_LENGTH - SENSOR_BACK_INSET
    front_depth = actual_slide_depth - SIDE_BRACKET_DEPTH
    
    print(f"Exported: {out_path}")
    if TEST_MODE:
        print(f"\n*** TEST MODE ACTIVE - REDUCED DIMENSIONS FOR MATERIAL SAVING ***")
    print(f"\n=== Dual Sensor Counterplate (Integrated Design) ===")
    print(f"  Total length: {TOTAL_GRIPPER_LENGTH}mm")
    print(f"  Overall width: {GRIP_MIDDLE_WIDTH}mm (~36mm)")
    print(f"\n  Pressing parts (2x) - EXTEND DOWNWARD to press sensors:")
    print(f"    X (depth into channel): {plate_x_depth}mm (fits {front_depth}mm front channel section)")
    print(f"    Y (width): {plate_y_width}mm")
    print(f"    Z (height extending down): {plate_height}mm")
    print(f"    Clearance: {FITTING_CLEARANCE}mm on all sides")
    print(f"    Position: At left (-X) and right (+X) ends, {SENSOR_FRONT_INSET}mm from outer face")
    print(f"              Avoids {SIDE_BRACKET_DEPTH}mm bracket section at back")
    print(f"\n  Grip bar:")
    print(f"    Total length: {TOTAL_GRIPPER_LENGTH}mm")
    print(f"    Width: {GRIP_MIDDLE_WIDTH}mm")
    print(f"    Height: {GRIP_HEIGHT}mm")
    print(f"    Screw holes: {NUM_SCREW_HOLES}x M3 with counterbore")
    print(f"      - Through hole: Ø{SCREW_HOLE_DIA}mm (increased for easier threading)")
    print(f"      - Counterbore: Ø{SCREW_HEAD_DIA}mm x {SCREW_HEAD_DEPTH}mm deep")
    print(f"      - Spacing: {SCREW_SPACING}mm")
    print(f"    Rounded edges: {TOP_EDGE_RADIUS}mm radius")
    print(f"\n  Usage: Place counterplate on top of gripper, align screw holes")
    print(f"         Pressing parts fit into sensor cutouts and press from above")
    print(f"         Bolt through screw holes to clamp sensors securely")


if __name__ == "__main__":
    export_dual_gripper()
    print("\n" + "="*60 + "\n")
    export_dual_counterplate()

