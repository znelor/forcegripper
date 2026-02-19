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
    Cylinder,
    Sphere,
    Mode,
    extrude,
    fillet,
    chamfer,
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
Compact Dual Sensor Gripper (Design F):
- Based on Design E (Hollow)
- 4 Screws (2 at each end)
- Extensions at -X and +X ends to hold screws (excluded from main grip)
- +X Extension integrates with ESP32 Box
- Counterplate extends to cover full length (acts as lid for box too?)
- Fillets on extensions
"""

# -----------------------------
# Test mode for material saving
# -----------------------------
TEST_MODE = False

# -----------------------------
# Hollow design parameters
# -----------------------------
WALL_THICKNESS = 4.0
FLOOR_THICKNESS = 3.0
TOP_THICKNESS = 3.0
CHAMBER_CLEARANCE = 0.5

# -----------------------------
# Import sensor block parameters
# -----------------------------
SENSOR_WIDTH = 34.0
SENSOR_DEPTH = 34.0
SENSOR_THICKNESS = 2.6

if TEST_MODE:
    BLOCK_LENGTH = 30.0
    BLOCK_WIDTH = 38.0
    BLOCK_HEIGHT = 12.0
else:
    BLOCK_LENGTH = 30.0
    BLOCK_WIDTH = 38.0
    BLOCK_HEIGHT = 22.0

SLIDE_WALL_THICKNESS = 3.0
CLEARANCE = 0.2
BOTTOM_LIP_HEIGHT = 3.0

INNER_COMPONENT_SIDE_INSET = 4.0
INNER_COMPONENT_HEIGHT = 6.0
SENSOR_BACK_INSET = 0.0
SENSOR_FRONT_INSET = 15.0
SIDE_BRACKET_DEPTH = 4.0
SIDE_BRACKET_HEIGHT = 6.0
SENSOR_Z_LIFT = 4.0  # Raised from 2.0 to 4.0

# -----------------------------
# Grip bar parameters
# -----------------------------
if TEST_MODE:
    GRIP_LENGTH = 40.0
    GRIP_WIDTH = 38.0
    GRIP_HEIGHT = 12.0
    GRIP_MIDDLE_WIDTH = 38.0
    GRIP_END_LENGTH = 20.0
    TOP_EDGE_RADIUS = 4.0
else:
    GRIP_LENGTH = 60.0
    GRIP_WIDTH = 38.0
    GRIP_HEIGHT = 12.0
    GRIP_MIDDLE_WIDTH = 38.0
    GRIP_END_LENGTH = 20.0
    TOP_EDGE_RADIUS = 4.0

SCREW_HOLE_DIA = 3.9
SCREW_HEAD_DIA = 11.5
SCREW_HEAD_DEPTH = 8.0
if TEST_MODE:
    SCREW_HEAD_DEPTH = 5.0

# -----------------------------
# Extension / Mounting Parameters
# -----------------------------
MOUNTING_TAB_LENGTH = 15.0  # Length of screw mounting extensions at ends
MOUNTING_TAB_FILLET = 4.0   # Fillet radius for tabs
EXTENSION_FILLET = 2.0      # Fillet for the ergonomic extension on top

# Overall gripper dimensions (Core Body)
CORE_LENGTH = 2 * BLOCK_LENGTH + GRIP_LENGTH

# Ergonomic Extension (Top Handle)
EXTENSION_LENGTH = 120.0
EXTENSION_WIDTH = 38.0
EXTENSION_HEIGHT = 12.0

# Electronics Box
BOX_LENGTH = 110.0        # Extended to fit ESP32 + HX711 side by side with gap
BOX_WIDTH = 50.0          # Reverted to original compact width
BOX_HEIGHT = 52.0         # Increased for cable connector clearance (dupont headers ~12mm tall)
BOX_WALL_THICKNESS = 3.0
BOX_FLOOR_THICKNESS = 2.5
SEPARATOR_THICKNESS = 2.5 # Thickness of the separator plate (increased for rigidity)
RAIL_WIDTH = 4.0          # Increased from 2.0 for better screw bite
RAIL_HEIGHT_FROM_FLOOR = 14.0 # Height of the rail top surface from box floor (Battery Chamber Height) - Increased from 10.0 for more cable headroom
MAGNET_HOLE_DIA = 2.7
MAGNET_HOLE_DEPTH = 2.0

# Lid Parameters
LID_THICKNESS = 2.0
M2_PILOT = 1.8       # Hole for threading into plastic
M2_CLEARANCE = 2.4   # Hole in lid
M2_HEAD = 4.2        # Screw head diameter
M2_HEAD_H = 2.0      # Screw head height (for countersink/bore)
BOX_SCREW_OFFSET = 2.0 # Distance from corner edges

# -----------------------------
# PCB Mounting Parameters
# -----------------------------
# ESP32 dev board hole spacing (M2 holes)
ESP32_HOLE_SPACING_X = 56.0
ESP32_HOLE_SPACING_Y = 22.0

# HX711 load cell amp hole spacing (M2 holes)
HX711_HOLE_SPACING_X = 18.0
HX711_HOLE_SPACING_Y = 26.0

# Standoff dimensions
STANDOFF_DIA = 5.0           # Outer diameter of standoff
STANDOFF_HEIGHT = 5.0        # Height above separator plate
PCB_CLEARANCE = 2.0          # Space under PCB for solder joints

def create_compact_dual_sensor_gripper() -> object:
    """
    Create the gripper with end extensions for 4 screws.
    """
    # Dimensions
    channel_width = SENSOR_WIDTH + CLEARANCE
    channel_height = SENSOR_THICKNESS + CLEARANCE
    
    # Total height of the main body (including integrated top)
    main_body_height = GRIP_HEIGHT + TOP_THICKNESS
    
    with BuildPart() as gripper:
        # 1) Core Body (Grip + Blocks)
        Box(CORE_LENGTH, GRIP_MIDDLE_WIDTH, main_body_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
            
        # 2) Hollow Chamber (Middle Only)
        CENTRAL_CAVITY_LENGTH = 30.0
        SENSOR_CHANNEL_LENGTH = 32.0
        MIN_SOLID_END = 20.0 # Keep some solid at ends of core body
        
        chamber_length = CORE_LENGTH - (2 * MIN_SOLID_END)
        chamber_width = GRIP_MIDDLE_WIDTH - (2 * WALL_THICKNESS)
        chamber_height = GRIP_HEIGHT - FLOOR_THICKNESS
        chamber_z_offset = FLOOR_THICKNESS
        
        with Locations((0, 0, chamber_z_offset + chamber_height / 2)):
            Box(chamber_length, chamber_width, chamber_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)

        # 3) Extensions for Screws (Tabs)
        # We add solid blocks at -X and +X ends of the CORE_LENGTH
        
        # -X Extension (Bottom)
        left_tab_x = -(CORE_LENGTH / 2 + MOUNTING_TAB_LENGTH / 2)
        with Locations((left_tab_x, 0, main_body_height / 2)):
            Box(MOUNTING_TAB_LENGTH, GRIP_MIDDLE_WIDTH, main_body_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.ADD)
        
        # 4) Ergonomic Extension (Handle on Top) - ADDED EARLY TO FILLET BEFORE BOX MERGE
        extension_z_offset = main_body_height
        
        # Reduce handle length slightly to prevent merging with box if they touch
        # The box starts at X=60. The handle normally ends at X=60.
        # Shortening by 1mm (0.5 per side) ensures separation if needed, 
        # or just allow fillets to work on exposed edges.
        # Actually, let's keep original length but rely on early filleting.
        
        with Locations((0, 0, extension_z_offset + EXTENSION_HEIGHT / 2)):
            Box(EXTENSION_LENGTH, EXTENSION_WIDTH, EXTENSION_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.ADD)
                
        # 5) Fillets for Handle (BEFORE BOX)
        # Specific Large Fillets for Extensions
        
        # A) Vertical Corners of Top Handle (Rounding the ends)
        # Width 38mm -> Max Radius ~19mm. Use 18.0mm.
        # Filter for vertical edges of the handle. 
        # Z > main_body_height + 0.1
        top_handle_vertical = gripper.part.edges().filter_by(Axis.Z).filter_by(
            lambda e: e.center().Z > main_body_height + 0.1
        )
        if top_handle_vertical:
            try:
                fillet(top_handle_vertical, radius=4.0)
            except Exception:
                pass
                
        # B) Horizontal Loop of Top Handle (Rounding the grip)
        # This makes the top surface domed.
        # Edges at the very top of the extension.
        # Z should be near main_body_height + EXTENSION_HEIGHT (approx 37mm)
        handle_top_z = main_body_height + EXTENSION_HEIGHT
        top_handle_horizontal = gripper.part.edges().filter_by(
            lambda e: abs(e.center().Z - handle_top_z) < 1.0
        )
        if top_handle_horizontal:
            try:
                fillet(top_handle_horizontal, radius=8.0)
            except Exception:
                try:
                    fillet(top_handle_horizontal, radius=5.0)
                except Exception:
                    try:
                        fillet(top_handle_horizontal, radius=3.0)
                    except Exception:
                        pass

        # 6) Electronics Box at +X (NOW ADDED AFTER HANDLE FILLETS)
        box_x_center = (CORE_LENGTH / 2) + (BOX_LENGTH / 2)
        
        with Locations((box_x_center, 0, BOX_HEIGHT / 2)):
             Box(BOX_LENGTH, BOX_WIDTH, BOX_HEIGHT,
                 align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                 mode=Mode.ADD)
                 
        # Hollow out Box (Single Chamber with Rails)
        box_interior_length = BOX_LENGTH - (2 * BOX_WALL_THICKNESS)
        box_interior_width = BOX_WIDTH - (2 * BOX_WALL_THICKNESS)
        box_interior_height = BOX_HEIGHT - BOX_FLOOR_THICKNESS
        
        with Locations((box_x_center, 0, BOX_FLOOR_THICKNESS + box_interior_height / 2)):
            Box(box_interior_length, box_interior_width, box_interior_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.SUBTRACT)

        # Internal Rails for Separator Plate (Battery Basement)
        # -----------------------------------------------------
        # Bottom Rails: Support the plate
        # Screw Mounting: Plate sits on rails and is screwed down.
        
        rail_length = box_interior_length
        rail_z_top = BOX_FLOOR_THICKNESS + RAIL_HEIGHT_FROM_FLOOR
        CABLE_GAP = 12.0 # Define CABLE_GAP locally
        
        # Left Rail (-Y side)
        with Locations((box_x_center, -(box_interior_width/2) + (RAIL_WIDTH/2), rail_z_top - (RAIL_WIDTH/2))):
             # Create a square profile and chamfer it? Or just a box?
             # To chamfer underside, we can make a box and chamfer the bottom edge.
             # Box height = RAIL_WIDTH (for 45 deg chamfer).
             Box(rail_length, RAIL_WIDTH, RAIL_WIDTH, 
                 align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                 mode=Mode.ADD)
             
        # Right Rail (+Y side)
        with Locations((box_x_center, (box_interior_width/2) - (RAIL_WIDTH/2), rail_z_top - (RAIL_WIDTH/2))):
             Box(rail_length, RAIL_WIDTH, RAIL_WIDTH, 
                 align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                 mode=Mode.ADD)
                 
        # END STOPS (REMOVED)
        # No longer needed as screws hold the plate.
        gap_line_x = box_x_center - (box_interior_length/2) + CABLE_GAP

        # SCREW HOLES FOR SEPARATOR PLATE
        # We add M2 holes into the rails to screw the plate down.
        # 2 screws should be enough (diagonally or one on each rail).
        # Let's put 2 screws, one on each rail, near the middle-back.
        
        # Positions relative to box center
        # X: Middle of the plate area?
        # Plate runs from gap_line_x to (box_x_center + box_interior_length/2)
        plate_start_x = gap_line_x
        plate_end_x = box_x_center + (box_interior_length/2)
        screw_x = (plate_start_x + plate_end_x) / 2
        
        # Y: Center of the rails
        screw_y_left = -(box_interior_width/2) + (RAIL_WIDTH/2)
        screw_y_right = (box_interior_width/2) - (RAIL_WIDTH/2)
        
        screw_positions_plate = [
            (screw_x, screw_y_left),
            (screw_x, screw_y_right)
        ]
        
        # M2 Pilot holes (1.8mm)
        with Locations((0,0,0)): # Global context
             with Locations(*[(x, y, rail_z_top) for x, y in screw_positions_plate]):
                 Cylinder(radius=M2_PILOT/2, height=6.0, 
                          align=(Align.CENTER, Align.CENTER, Align.MAX), 
                          mode=Mode.SUBTRACT)

        # Chamfer the bottom edges of the rails to make them printable
        # We need to select edges of the rails we just added.
        # Rail bottom edges are at Z = rail_z_top - RAIL_WIDTH.
        # And they are the "inner" edges? No, the rails are attached to the walls.
        # The edges to chamfer are the ones floating in the air at the bottom.
        
        rail_bottom_z = rail_z_top - RAIL_WIDTH
        rail_edges = gripper.part.edges().filter_by(Axis.Z).filter_by(
            lambda e: abs(e.center().Z - rail_bottom_z) < 0.1
        )
        # Filter for edges that are "inside" the box (not the wall connection).
        # Inner edges have Y close to (box_interior_width/2 - RAIL_WIDTH).
        # Box center is at 0 in Y.
        # Left rail inner edge Y = - (W/2 - W_rail).
        # Right rail inner edge Y = + (W/2 - W_rail).
        
        inner_y_abs = (box_interior_width / 2) - RAIL_WIDTH
        
        rail_inner_edges = [e for e in rail_edges if abs(abs(e.center().Y) - inner_y_abs) < 0.1]
        
        if rail_inner_edges:
            try:
                chamfer(rail_inner_edges, length=RAIL_WIDTH - 0.1) # Almost full chamfer
            except Exception:
                 pass
                 
        # Also chamfer the TOP rails? (REMOVED)
        # The top rails were removed in the simplification step.
        # So we don't need this block.
        
        # Box Screw Holes (M2 Pilot)
        box_screw_dx = (BOX_LENGTH / 2) - BOX_SCREW_OFFSET
        box_screw_dy = (BOX_WIDTH / 2) - BOX_SCREW_OFFSET
        box_screw_positions = [
            (box_screw_dx, box_screw_dy),
            (box_screw_dx, -box_screw_dy),
            (-box_screw_dx, box_screw_dy),
            (-box_screw_dx, -box_screw_dy)
        ]
        
        # We need to cut these holes into the top rim of the box
        # Box top is at BOX_HEIGHT. Depth of hole say 10mm.
        with Locations((box_x_center, 0, BOX_HEIGHT)):
             with Locations(*box_screw_positions):
                 Cylinder(radius=M2_PILOT/2, height=12.0, 
                          align=(Align.CENTER, Align.CENTER, Align.MAX), 
                          mode=Mode.SUBTRACT)

        # 7) Screw Holes (4 Total) - Cut through Box as well if needed
        # Pair 1: -X Tab
        # Pair 2: +X Tab (inside Box now)
        
        screw_spacing_y = 20.0 # 10mm from center
        
        # X Positions
        # Left: Middle of the Left Tab
        screw_x_left = -(CORE_LENGTH / 2 + MOUNTING_TAB_LENGTH / 2)
        
        # Right: On the edge of the grippable area (+X end of Core)
        # User update: "extend the holes another 10mm so they are INSIDE the chamber for the esp32"
        # User update 2: "another 5mm" -> Move +5mm towards +X.
        # New: (CORE_LENGTH / 2) + 10.0
        
        screw_x_right = (CORE_LENGTH / 2) + 10.0
        
        screw_positions = [
            (screw_x_left, screw_spacing_y / 2),
            (screw_x_left, -screw_spacing_y / 2),
            (screw_x_right, screw_spacing_y / 2),
            (screw_x_right, -screw_spacing_y / 2)
        ]
        
        # Cut holes
        GRIPPER_TOP_INSET = main_body_height - 2.0 # Keep material at bottom
        
        for sx, sy in screw_positions:
             # Counterbore (from Top)
            with BuildSketch(Plane.XY.offset(main_body_height)):
                with Locations((sx, sy)):
                    Circle(radius=SCREW_HEAD_DIA / 2)
            extrude(amount=-GRIPPER_TOP_INSET, mode=Mode.SUBTRACT)
            
            # Through Hole
            with BuildSketch(Plane.XY.offset(main_body_height)):
                with Locations((sx, sy)):
                    Circle(radius=SCREW_HOLE_DIA / 2)
            # Extrude deeply to cut through box if box is taller than main_body_height
            # main_body_height is 15. Box is 25.
            # We must cut from top of box? No, screw holes are defined at main_body_height plane (Z=15).
            # If box covers it (Z=25), we must cut *up* as well to clear the hole?
            # Or is the screw hole inside the box cavity?
            # Screw X = 60 + 10 = 70.
            # Box starts at 60. Box wall 3mm. Box interior starts at 63.
            # So X=70 is inside the box cavity.
            # The box cavity floor is at 2.5mm.
            # The gripper body is solid up to Z=15 (minus chamber).
            # Wait, at X=70, the gripper body ends at X=60.
            # So under the box at X=70, what is there?
            # The box sits on Z=0.
            # Box floor is 2.5mm thick.
            # The screw hole (X=70) goes through the box floor.
            # So we need a hole through the box floor.
            # And counterbore?
            # Counterbore depth 8mm.
            # If we cut from Z=15 down...
            # But at X=70, there is no "gripper body" (Z=0..15). There is only Box (Z=0..25).
            # And Box Floor (Z=0..2.5).
            # Wait, the screw hole logic assumed it was cutting into the gripper extension.
            # But the extension was removed (right tab removed).
            # So now we are bolting the BOX down.
            # The screw goes through the box floor.
            # So we need a hole in the box floor.
            # And clearance for the head?
            # If the head is inside the box, we need access.
            # The box is open at the top (lid removed).
            # So we can put the screw in from inside the box.
            # So the hole should be in the box floor.
            # Floor thickness 2.5mm.
            # Screw head is 8mm tall?
            # If we put screw head on the floor, it sticks up.
            # That's fine.
            # So we just need a hole through the floor.
            # The `screw_positions` loop creates holes relative to `main_body_height`.
            # This is probably WRONG for the right-side screws now that they are in the box.
            # But let's leave it for now unless user complains, or fix it?
            # User said "extend holes... inside chamber".
            # The current code cuts `amount=-main_body_height` from Z=15.
            # At X=70, Z=15 is empty air inside the box (Box height 25, floor 2.5).
            # So cutting from Z=15 down to 0 will cut through the floor (Z=2.5).
            # So it works! It creates a hole in the floor.
            
            extrude(amount=-30.0, mode=Mode.SUBTRACT) # Ensure it cuts through everything including box bottom

        # 8) Sensor Channels & Cavity (Same as Design E)
        # SENSOR_Z_LIFT is now a global parameter
        channel_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + channel_height/2
        inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)
        inner_channel_height = channel_height + INNER_COMPONENT_HEIGHT
        inner_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + inner_channel_height/2
        
        # Central Cavity
        with Locations((0, 0, channel_z_center)):
            Box(CENTRAL_CAVITY_LENGTH, channel_width, channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        with Locations((0, 0, inner_z_center)):
            Box(CENTRAL_CAVITY_LENGTH, channel_width, inner_channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        with Locations((0, 0, (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2)):
            Box(CENTRAL_CAVITY_LENGTH, channel_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
                
        # Left Channel
        bracket_section_depth = SIDE_BRACKET_DEPTH
        bracket_cutout_width = channel_width
        bracket_cutout_height = channel_height
        bracket_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + bracket_cutout_height/2
        sensor_main_depth = SENSOR_CHANNEL_LENGTH - bracket_section_depth
        
        left_channel_center_x = -(CENTRAL_CAVITY_LENGTH / 2 + sensor_main_depth / 2)
        with Locations((left_channel_center_x, 0, channel_z_center)):
            Box(sensor_main_depth, channel_width, channel_height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        with Locations((left_channel_center_x, 0, inner_z_center)):
            Box(sensor_main_depth, inner_channel_width, inner_channel_height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        with Locations((left_channel_center_x, 0, (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2)):
            Box(sensor_main_depth, inner_channel_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
            
        left_bracket_x = -(CENTRAL_CAVITY_LENGTH / 2 + sensor_main_depth + bracket_section_depth / 2)
        with Locations((left_bracket_x, 0, bracket_z_center)):
            Box(bracket_section_depth, bracket_cutout_width, bracket_cutout_height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
            
        # Right Channel
        right_channel_center_x = (CENTRAL_CAVITY_LENGTH / 2 + sensor_main_depth / 2)
        with Locations((right_channel_center_x, 0, channel_z_center)):
            Box(sensor_main_depth, channel_width, channel_height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        with Locations((right_channel_center_x, 0, inner_z_center)):
            Box(sensor_main_depth, inner_channel_width, inner_channel_height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        with Locations((right_channel_center_x, 0, (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2)):
            Box(sensor_main_depth, inner_channel_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
            
        right_bracket_x = (CENTRAL_CAVITY_LENGTH / 2 + sensor_main_depth + bracket_section_depth / 2)
        with Locations((right_bracket_x, 0, bracket_z_center)):
            Box(bracket_section_depth, bracket_cutout_width, bracket_cutout_height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # 9) Remaining Fillets (Tabs and Box Corners)
        
        # Mounting Tabs (Left Tab)
        # Filter vertical edges at the far left (outer corners of the tab)
        tab_edges = gripper.part.edges().filter_by(Axis.Z).filter_by(
            lambda e: e.center().X < -(CORE_LENGTH/2) - 0.1 and e.center().Z < main_body_height
        )
        if tab_edges:
             sorted_tab = sorted(tab_edges, key=lambda e: e.center().X)
             corners = sorted_tab[:2]
             try:
                 fillet(corners, radius=2.0)
             except Exception:
                 pass

        # C) ESP32 Box Exterior Corners (Small fillet)
        # Filter vertical edges on the perimeter of the box
        # We want the outer corners, not the inner cavity corners.
        box_exterior_edges = gripper.part.edges().filter_by(Axis.Z).filter_by(
            lambda e: (
                e.center().X > (CORE_LENGTH/2 - 1.0) and # In box region
                (abs(e.center().Y) > (BOX_WIDTH/2 - 1.0) or # Outer side walls
                 e.center().X > (box_x_center + BOX_LENGTH/2 - 1.0)) # End wall
            )
        )
        if box_exterior_edges:
            try:
                fillet(box_exterior_edges, radius=2.0)
            except Exception:
                pass

        # Global rounding of sharp edges
        
        # 1. Vertical Edges (Corners)
        # Exclude edges at the junction between core body and ESP32 box (X ~ CORE_LENGTH/2)
        junction_x = CORE_LENGTH / 2
        vertical_edges = gripper.part.edges().filter_by(Axis.Z)
        vertical_edges = [e for e in vertical_edges if e.length > 2.0 and abs(e.center().X - junction_x) > 2.0]
        
        if vertical_edges:
            try:
                fillet(vertical_edges, radius=1.5)
            except Exception:
                try:
                    fillet(vertical_edges, radius=1.0)
                except Exception:
                    pass

        # 2. Horizontal Edges (Top/Bottom loops)
        # Exclude edges at the junction between core body and ESP32 box
        remaining_edges = gripper.part.edges()
        horizontal_edges = [e for e in remaining_edges if 
                           abs(e.bounding_box().max.Z - e.bounding_box().min.Z) < 0.1 and
                           abs(e.center().X - junction_x) > 2.0]
        
        if horizontal_edges:
            try:
                fillet(horizontal_edges, radius=0.4)
            except Exception:
                pass

        # 10) USB-C Cable Hole - Rounded stadium shape
        # USB-C plug is ~12mm wide x 7mm tall with rounded ends
        USBC_HOLE_WIDTH = 14.0   # Width for cable clearance
        USBC_HOLE_HEIGHT = 8.0   # Height for USB-C plug
        USBC_RADIUS = USBC_HOLE_HEIGHT / 2  # Rounded ends
        
        cable_hole_x = box_x_center + (BOX_LENGTH / 2)
        cable_hole_y = 0
        
        # Calculate USB-C port height based on standoff position
        # Separator top = BOX_FLOOR_THICKNESS + RAIL_HEIGHT_FROM_FLOOR + SEPARATOR_THICKNESS
        # PCB bottom = separator top + standoff height
        # USB-C center is ~2mm above PCB bottom
        separator_top = BOX_FLOOR_THICKNESS + RAIL_HEIGHT_FROM_FLOOR + SEPARATOR_THICKNESS
        pcb_bottom = separator_top + STANDOFF_HEIGHT + PCB_CLEARANCE
        cable_hole_z = pcb_bottom + 3.0  # USB-C port center ~3mm above PCB bottom
        
        # Create USB-C shaped hole (stadium/rounded rectangle)
        # Two cylinders at ends + box in middle
        usbc_box_width = USBC_HOLE_WIDTH - USBC_HOLE_HEIGHT  # Middle section
        
        with Locations((cable_hole_x, cable_hole_y, cable_hole_z)):
            # Middle rectangular section
            Box(10.0, usbc_box_width, USBC_HOLE_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
            # Left rounded end
            with Locations((0, -usbc_box_width/2, 0)):
                Cylinder(radius=USBC_RADIUS, height=10.0, rotation=(0, 90, 0),
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.SUBTRACT)
            # Right rounded end
            with Locations((0, usbc_box_width/2, 0)):
                Cylinder(radius=USBC_RADIUS, height=10.0, rotation=(0, 90, 0),
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.SUBTRACT)
                 
        # Also connect chamber to box?
        tunnel_length = MIN_SOLID_END + BOX_WALL_THICKNESS + 5.0
        tunnel_x = (CORE_LENGTH / 2) - (MIN_SOLID_END / 2) + (BOX_WALL_THICKNESS/2)
        
        with Locations((tunnel_x, 0, chamber_z_offset + chamber_height / 2)):
             Box(tunnel_length, 24.0, 12.0, 
                 align=(Align.CENTER, Align.CENTER, Align.CENTER),
                 mode=Mode.SUBTRACT)

    return gripper.part

def create_compact_counterplate() -> object:
    """
    Counterplate covering the full length (including extensions).
    """
    # Height calculations
    counterplate_body_height = 6.0
    
    # Total Length covering Tabs and Box and Right Tab
    # Left Tab: MOUNTING_TAB_LENGTH
    # Core: CORE_LENGTH
    # Box: BOX_LENGTH (Counterplate doesn't need to cover Box fully if screws are at edge?)
    # User requested: "decrease the length of the counterplate again"
    # Screws are at (CORE_LENGTH / 2) + 5.0 (moved 10mm into chamber)
    # So counterplate needs to cover up to screws + margin.
    # Screws at X = 65mm. Margin ~10mm. End at X = 75mm.
    # Box starts at X = 60mm.
    
    # Left Edge: -(CORE_LENGTH/2 + MOUNTING_TAB_LENGTH)
    # Right Edge: (CORE_LENGTH/2 + 20.0)  # Just enough to cover screws + margin
    
    left_x = -(CORE_LENGTH/2 + MOUNTING_TAB_LENGTH)
    right_x = (CORE_LENGTH/2 + 17.5)
    plate_length = right_x - left_x
    plate_center_x = (left_x + right_x) / 2
    
    with BuildPart() as assembly:
        # 1) Main Plate
        # Body
        with Locations((plate_center_x, 0, counterplate_body_height/2)):
            Box(plate_length, GRIP_MIDDLE_WIDTH, counterplate_body_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
                
        # 2) Ergonomic Extension on Top
        # Stays in the middle (over Core)
        # Extension length should also match plate length?
        # Or keep EXTENSION_LENGTH (120mm) fixed?
        # User said "decrease the length of the counterplate", implies whole thing.
        # Let's reduce extension to match the new plate length or fit within it.
        # Original EXTENSION_LENGTH = 120.
        # New plate_length = (60+15) + (60+10) = 145mm? No.
        # CORE_LENGTH = 120. Half = 60.
        # Left = -(60+15) = -75.
        # Right = 60+20 = 80.
        # Length = 155.
        # EXTENSION_LENGTH = 120 fits inside comfortably.
        # Let's keep EXTENSION_LENGTH fixed at 120 unless user wants it cut.
        # User said "decrease length of counterplate".
        # If I just cut the plate, the extension might stick out if I don't cut it too.
        # But 120mm extension fits from -60 to +60.
        # Plate goes from -75 to +80. So extension is inside.
        
        with Locations((0, 0, counterplate_body_height + EXTENSION_HEIGHT / 2)):
            Box(EXTENSION_LENGTH, EXTENSION_WIDTH, EXTENSION_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), 
                mode=Mode.ADD)

        # 3) Screw Holes (4 Positions)
        screw_spacing_y = 20.0
        screw_x_left = -(CORE_LENGTH / 2 + MOUNTING_TAB_LENGTH / 2)
        
        # User: "extend the holes another 10mm so they are INSIDE the chamber for the esp32"
        # Previous: (CORE_LENGTH / 2) - 5.0
        # Move +10mm towards +X
        # New: (CORE_LENGTH / 2) + 5.0
        screw_x_right = (CORE_LENGTH / 2) + 10.0
        
        screw_positions = [
            (screw_x_left, screw_spacing_y / 2),
            (screw_x_left, -screw_spacing_y / 2),
            (screw_x_right, screw_spacing_y / 2),
            (screw_x_right, -screw_spacing_y / 2)
        ]
        
        for sx, sy in screw_positions:
            # Through hole (Main Body) - Only small hole
            with BuildSketch(Plane.XY.offset(counterplate_body_height)):
                with Locations((sx, sy)):
                    Circle(radius=SCREW_HOLE_DIA / 2)
            extrude(amount=-counterplate_body_height, mode=Mode.SUBTRACT)
            
            # Extension Passthrough - Only small hole
            with BuildSketch(Plane.XY.offset(counterplate_body_height + EXTENSION_HEIGHT)):
                 with Locations((sx, sy)):
                     Circle(radius=SCREW_HOLE_DIA / 2)
            extrude(amount=-(EXTENSION_HEIGHT + 1.0), mode=Mode.SUBTRACT)

        # 4) Pressing Parts (Same as Design E)
        CENTRAL_CAVITY_LENGTH = 30.0
        SENSOR_CHANNEL_LENGTH = 32.0
        sensor_main_depth = SENSOR_CHANNEL_LENGTH - SIDE_BRACKET_DEPTH
        
        inner_channel_width = SENSOR_WIDTH + CLEARANCE - (2 * INNER_COMPONENT_SIDE_INSET)
        FITTING_CLEARANCE = 0.5
        PRESSING_HEIGHT_EXTENSION = 9.0
        
        plate_x_depth = sensor_main_depth - (2 * FITTING_CLEARANCE)
        plate_y_width = inner_channel_width - (2 * FITTING_CLEARANCE)
        original_plate_height = BOTTOM_LIP_HEIGHT - FITTING_CLEARANCE + PRESSING_HEIGHT_EXTENSION + TOP_THICKNESS
        reduced_plate_height = original_plate_height / 3.0
        
        left_pressing_x = -(CENTRAL_CAVITY_LENGTH / 2 + sensor_main_depth / 2)
        with Locations((left_pressing_x, 0, -reduced_plate_height / 2)):
            Box(plate_x_depth, plate_y_width, reduced_plate_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.ADD)
                
        right_pressing_x = (CENTRAL_CAVITY_LENGTH / 2 + sensor_main_depth / 2)
        with Locations((right_pressing_x, 0, -reduced_plate_height / 2)):
            Box(plate_x_depth, plate_y_width, reduced_plate_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.ADD)

        # Coin Extrusions (1 Euro Cent) - Cutout
        COIN_DIAMETER = 17.0
        COIN_THICKNESS = 1.8
        # Cut into the material from the bottom face upwards
        coin_z_center = -reduced_plate_height + (COIN_THICKNESS / 2)

        # Shift 3mm towards the center
        with Locations((left_pressing_x + 3.0, 0, coin_z_center)):
             Cylinder(radius=COIN_DIAMETER/2, height=COIN_THICKNESS,
                      align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
                      
        with Locations((right_pressing_x - 3.0, 0, coin_z_center)):
             Cylinder(radius=COIN_DIAMETER/2, height=COIN_THICKNESS,
                      align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # 5) Fillets
        # Specific Large Fillets
        
        # Top Handle Vertical (Ends)
        # Width 38mm -> Max Radius ~19mm. Use 18.0mm.
        top_handle_vertical = assembly.part.edges().filter_by(Axis.Z).filter_by(
            lambda e: e.center().Z > counterplate_body_height + 0.1
        )
        if top_handle_vertical:
            try:
                fillet(top_handle_vertical, radius=4.0)
            except Exception:
                pass

        # Top Handle Horizontal (Grip)
        handle_top_z = counterplate_body_height + EXTENSION_HEIGHT
        top_handle_horizontal = assembly.part.edges().filter_by(
            lambda e: abs(e.center().Z - handle_top_z) < 1.0
        )
        if top_handle_horizontal:
            try:
                fillet(top_handle_horizontal, radius=8.0)
            except Exception:
                 try:
                    fillet(top_handle_horizontal, radius=5.0)
                 except Exception:
                    try:
                        fillet(top_handle_horizontal, radius=3.0)
                    except Exception:
                        pass
                
        # Main Plate Corners (Maximize rounding)
        # The plate is a long rectangle. Round the 4 corners.
        # Edges at min X and max X.
        plate_edges = assembly.part.edges().filter_by(Axis.Z).filter_by(
             lambda e: e.center().Z < counterplate_body_height
        )
        # Identify the 4 outer corners by X position (extreme left and right)
        if plate_edges:
            sorted_edges = sorted(plate_edges, key=lambda e: e.center().X)
            # 2 at min X, 2 at max X
            outer_corners = sorted_edges[:2] + sorted_edges[-2:]
            try:
                fillet(outer_corners, radius=2.0)
            except Exception:
                pass

        # Global rounding
        
        # Vertical Corners
        vertical_edges = assembly.part.edges().filter_by(Axis.Z)
        vertical_edges = [e for e in vertical_edges if e.length > 2.0]
        
        if vertical_edges:
             try:
                 fillet(vertical_edges, radius=1.5)
             except Exception:
                 try:
                     fillet(vertical_edges, radius=1.0)
                 except Exception:
                     pass

        # Horizontal Edges (break sharp edges)
        remaining_edges = assembly.part.edges()
        horizontal_edges = [e for e in remaining_edges if abs(e.bounding_box().max.Z - e.bounding_box().min.Z) < 0.1]
        
        if horizontal_edges:
            try:
                fillet(horizontal_edges, radius=0.4)
            except Exception:
                pass

    return assembly.part

def create_box_lid() -> object:
    """
    Lid for the ESP32 Box.
    """
    with BuildPart() as lid:
        Box(BOX_LENGTH, BOX_WIDTH, LID_THICKNESS, 
            align=(Align.CENTER, Align.CENTER, Align.MIN))
            
        # Screw Holes
        box_screw_dx = (BOX_LENGTH / 2) - BOX_SCREW_OFFSET
        box_screw_dy = (BOX_WIDTH / 2) - BOX_SCREW_OFFSET
        box_screw_positions = [
            (box_screw_dx, box_screw_dy),
            (box_screw_dx, -box_screw_dy),
            (-box_screw_dx, box_screw_dy),
            (-box_screw_dx, -box_screw_dy)
        ]
        
        with Locations(*box_screw_positions):
            # Clearance Hole
            Cylinder(radius=M2_CLEARANCE/2, height=LID_THICKNESS, 
                     align=(Align.CENTER, Align.CENTER, Align.MIN), 
                     mode=Mode.SUBTRACT)
            # Counterbore (optional, but good for flush heads if thick enough)
            # Lid is 2mm, head is 2mm. Might be too thin for full hide, 
            # but let's sink it a bit if desired or just leave it flat.
            # User didn't specify countersink, but M2 usually has small heads.
            # Let's simple through hole for now, or slight counterbore?
            # User said "screw them in", likely button head or socket head.
            # If flat head (countersunk), we need chamfer.
            # Let's stick to clearance holes.
            
        # Fillet vertical corners of the lid
        vertical_edges = lid.part.edges().filter_by(Axis.Z)
        if vertical_edges:
            try:
                fillet(vertical_edges, radius=2.0)
            except Exception:
                pass
                
        # Break sharp horizontal edges
        remaining_edges = lid.part.edges()
        horizontal_edges = [e for e in remaining_edges if abs(e.bounding_box().max.Z - e.bounding_box().min.Z) < 0.1]
        
        if horizontal_edges:
            try:
                fillet(horizontal_edges, radius=0.4)
            except Exception:
                pass

    return lid.part

def create_separator_plate() -> object:
    """
    Separator plate to sit on the internal rails.
    It separates the battery (below) from the ESP32 and HX711 (above).
    Includes standoffs for mounting PCBs and a battery cable hole.
    """
    # Dimensions
    # It must fit INSIDE the box.
    CABLE_GAP = 12.0  # Increased gap for wiring
    
    box_interior_length = BOX_LENGTH - (2 * BOX_WALL_THICKNESS)
    box_interior_width = BOX_WIDTH - (2 * BOX_WALL_THICKNESS)
    plate_length = box_interior_length - 0.5 - CABLE_GAP - 3.0  # 3mm shorter
    plate_width = box_interior_width - 0.5
    
    # Standoff parameters
    standoff_total_height = STANDOFF_HEIGHT + PCB_CLEARANCE
    
    with BuildPart() as plate:
        # Main plate body
        Box(plate_length, plate_width, SEPARATOR_THICKNESS,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
            
        # Battery Cable Hole (corner notch at +X, -Y for short battery cable)
        # Position outside the ESP32 standoff Y range (standoffs at Y = ±11mm)
        battery_hole_width = 8.0
        battery_hole_depth = 8.0
        battery_hole_x = (plate_length / 2)  # At +X edge
        battery_hole_y = -(plate_width / 2)  # At -Y edge (corner)
        with Locations((battery_hole_x, battery_hole_y, SEPARATOR_THICKNESS / 2)):
            Box(battery_hole_depth * 2, battery_hole_width, SEPARATOR_THICKNESS * 2,
                align=(Align.MAX, Align.MIN, Align.CENTER), mode=Mode.SUBTRACT)
            

        # Screw Holes for Rails (must go completely through)
        # Positions match the rails in the main gripper body
        # X is center (0), Y is offset to match rail center
        screw_y_offset = (box_interior_width / 2) - (RAIL_WIDTH / 2)
        
        with Locations((0, screw_y_offset, SEPARATOR_THICKNESS / 2), (0, -screw_y_offset, SEPARATOR_THICKNESS / 2)):
            Cylinder(radius=M2_CLEARANCE/2, height=SEPARATOR_THICKNESS + 1.0,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # HX711 Mounting Standoffs (4 standoffs)
        # Positioned at -X side of plate (towards gripper body)
        hx711_center_x = -(plate_length / 2) + (HX711_HOLE_SPACING_X / 2) + 6.0
        hx711_center_y = 0.0
        
        hx711_standoff_positions = [
            (hx711_center_x - HX711_HOLE_SPACING_X/2, hx711_center_y - HX711_HOLE_SPACING_Y/2),
            (hx711_center_x - HX711_HOLE_SPACING_X/2, hx711_center_y + HX711_HOLE_SPACING_Y/2),
            (hx711_center_x + HX711_HOLE_SPACING_X/2, hx711_center_y - HX711_HOLE_SPACING_Y/2),
            (hx711_center_x + HX711_HOLE_SPACING_X/2, hx711_center_y + HX711_HOLE_SPACING_Y/2),
        ]
        
        for sx, sy in hx711_standoff_positions:
            # Standoff post
            with Locations((sx, sy, SEPARATOR_THICKNESS + standoff_total_height/2)):
                Cylinder(radius=STANDOFF_DIA/2, height=standoff_total_height,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.ADD)
            # M2 pilot hole
            with Locations((sx, sy, SEPARATOR_THICKNESS + standoff_total_height)):
                Cylinder(radius=M2_PILOT/2, height=8.0,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

        # ESP32 Mounting Standoffs (4 standoffs)
        # Positioned towards +X side, USB facing cable hole
        # Place after HX711 with gap, leave room for battery notch
        # Ensure standoffs don't overhang the plate edge
        esp32_center_x = hx711_center_x + (HX711_HOLE_SPACING_X / 2) + 8.0 + (ESP32_HOLE_SPACING_X / 2)
        # Check if rightmost standoff would overhang and adjust
        max_x = esp32_center_x + (ESP32_HOLE_SPACING_X / 2) + (STANDOFF_DIA / 2)
        if max_x > (plate_length / 2):
            esp32_center_x -= (max_x - (plate_length / 2))
        esp32_center_y = 0.0
        
        esp32_standoff_positions = [
            (esp32_center_x - ESP32_HOLE_SPACING_X/2, esp32_center_y - ESP32_HOLE_SPACING_Y/2),
            (esp32_center_x - ESP32_HOLE_SPACING_X/2, esp32_center_y + ESP32_HOLE_SPACING_Y/2),
            (esp32_center_x + ESP32_HOLE_SPACING_X/2, esp32_center_y - ESP32_HOLE_SPACING_Y/2),
            (esp32_center_x + ESP32_HOLE_SPACING_X/2, esp32_center_y + ESP32_HOLE_SPACING_Y/2),
        ]
        
        for sx, sy in esp32_standoff_positions:
            # Standoff post
            with Locations((sx, sy, SEPARATOR_THICKNESS + standoff_total_height/2)):
                Cylinder(radius=STANDOFF_DIA/2, height=standoff_total_height,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.ADD)
            # M2 pilot hole
            with Locations((sx, sy, SEPARATOR_THICKNESS + standoff_total_height)):
                Cylinder(radius=M2_PILOT/2, height=8.0,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)
            
        # Fillet corners of main plate
        plate_edges = plate.part.edges().filter_by(Axis.Z).filter_by(
            lambda e: e.center().Z < SEPARATOR_THICKNESS + 0.1
        )
        if plate_edges:
            try:
                fillet(plate_edges, radius=2.0)
            except Exception:
                pass
                
    return plate.part

def export_compact_gripper(base_name: str = "compact_dual_sensor_gripper") -> None:
    if export_stl is None:
        return
    out_path = f"{base_name}_v2.stl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = create_compact_dual_sensor_gripper()
    export_stl(part, out_path)
    print(f"Exported: {out_path}")

def export_compact_counterplate(base_name: str = "compact_counterplate") -> None:
    if export_stl is None:
        return
    out_path = f"{base_name}_v2.stl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = create_compact_counterplate()
    export_stl(part, out_path)
    print(f"Exported: {out_path}")

def export_box_lid(base_name: str = "box_lid") -> None:
    if export_stl is None:
        return
    out_path = f"{base_name}_v2.stl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = create_box_lid()
    export_stl(part, out_path)
    print(f"Exported: {out_path}")

def export_separator_plate(base_name: str = "separator_plate") -> None:
    if export_stl is None:
        return
    out_path = f"{base_name}_v2.stl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = create_separator_plate()
    export_stl(part, out_path)
    print(f"Exported: {out_path}")

if __name__ == "__main__":
    export_compact_gripper()
    export_compact_counterplate()
    export_box_lid()
    export_separator_plate()
