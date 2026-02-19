from __future__ import annotations

from build123d import (
    BuildPart,
    BuildSketch,
    Locations,
    Rectangle,
    Plane,
    Box,
    Cylinder,
    Mode,
    fillet,
    chamfer,
    Align,
    Axis,
    SlotOverall,
    extrude,
)

import os

try:
    from build123d import export_stl
except Exception:
    export_stl = None

"""
Sensor Chamber - Design G
- Sensor rails with electronics mounting on TOP
- Bottom sensor slot extended to full body length (but with end brackets)
"""

# -----------------------------
# Sensor parameters
# -----------------------------
SENSOR_WIDTH = 34.0
SENSOR_DEPTH = 34.0
SENSOR_THICKNESS = 2.6
CLEARANCE = 0.3  # Increased by 0.1mm for easier sensor sliding

# -----------------------------
# Main body parameters
# -----------------------------
BODY_WIDTH = 38.0
BODY_HEIGHT = 10.0  # Reduced height (another 2mm from bottom)

SENSOR_BLOCK_LENGTH = 32.0
GRIP_LENGTH = 30.0
SIDE_BRACKET_DEPTH = 6.0  # 6mm wall, cut 4mm deep = 2mm wall remaining

SENSOR_AREA_LENGTH = 2 * SENSOR_BLOCK_LENGTH + GRIP_LENGTH  # 94mm
ELECTRONICS_EXTENSION = 80.0  # Extended to accommodate longer layout and battery pocket
CORE_LENGTH = SENSOR_AREA_LENGTH + ELECTRONICS_EXTENSION  # 174mm

# Electronics platform on top
PLATFORM_LENGTH = CORE_LENGTH
PLATFORM_WIDTH = BODY_WIDTH
PLATFORM_HEIGHT = 5.0  # Increased by 2mm for more rigidity

# -----------------------------
# PCB Mounting Parameters
# -----------------------------
ESP32_HOLE_SPACING_X = 56.0
ESP32_HOLE_SPACING_Y = 22.0
ESP32_Y_OFFSET = 1.0  # Offset toward +Y so connectors have clearance
ESP32_CLEARANCE_EXTRA = 1.0  # Additional wall thickness matching final design
HX711_HOLE_SPACING_X = 26.0  # Rotated 90 degrees
HX711_HOLE_SPACING_Y = 18.0

STANDOFF_HEIGHT = 3.0
STANDOFF_DIA = 5.0
STANDOFF_BORE_DEPTH = STANDOFF_HEIGHT - 0.5
M2_PILOT = 2.2
M3_CLEARANCE = 4.0  # Wider than M3 for movement allowance
M3_PILOT = 2.5

# -----------------------------
# Top Cover Parameters
# -----------------------------
COVER_HEIGHT = 19.0  # 1mm taller for extra clearance
COVER_WALL = 1.5  # Bottom wall thickness
TOP_EXTRA_THICKNESS = 1.0  # Additional thickness on top roof
COVER_SCREW_INSET = 4.0  # Distance from edge to screw hole (clear of fillets)

# -----------------------------
# Battery Parameters
# -----------------------------
BATTERY_LENGTH = 60.0
BATTERY_WIDTH = 31.4
BATTERY_HEIGHT = 8.0
BATTERY_SLOT_WIDTH = 34.2  # Target clearance for battery space in base
BATTERY_COVER_CLEARANCE = max(BATTERY_SLOT_WIDTH - 2.0, BATTERY_WIDTH + 0.5)  # Thicker cover walls

# -----------------------------
# Channel parameters
# -----------------------------
INNER_COMPONENT_SIDE_INSET = 4.0
BOTTOM_LIP_HEIGHT = 3.0
SENSOR_Z_LIFT = 0.5  # Lowered so sensor sits 1.5mm lower

SENSOR_STOP_BUFFER = 26.0  # Length of wall extension from each outer edge
SENSOR_RAIL_DEPTH = 1.2  # Depth of the sensor slide rails
SENSOR_RAIL_WIDTH = 4.0  # Width of each rail nib

def create_sensor_chamber() -> object:
    """
    Sensor chamber with electronics platform on top.
    Bottom sensor slot runs full body length with end brackets.
    """
    
    channel_width = SENSOR_WIDTH + CLEARANCE
    channel_height = SENSOR_THICKNESS + CLEARANCE
    
    with BuildPart() as body:
        # 1) Main body
        Box(CORE_LENGTH, BODY_WIDTH, BODY_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        
        # 2) Electronics platform on top
        sensor_area_center = -(ELECTRONICS_EXTENSION / 2)
        
        with Locations((0, 0, BODY_HEIGHT)):
            Box(PLATFORM_LENGTH, PLATFORM_WIDTH, PLATFORM_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.ADD)

        # Fillet only vertical edges (corners in Y plane) EARLY on simple shape
        fillet_radius = 6.0

        # Vertical edges (corners) only - no top/bottom edge fillets
        vertical_edges = body.part.edges().filter_by(Axis.Z)
        fillet(vertical_edges, radius=fillet_radius)

        # Cable hole - positioned between HX711 and ESP32 (will be set after standoff positions)
        cable_hole_width = 12.0
        cable_hole_depth = 10.0
        
        # 3) Sensor channel - FULL BODY LENGTH (minus end brackets)
        INNER_COMPONENT_HEIGHT = 3.0  # Reduced space above sensor
        
        channel_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + channel_height / 2
        inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)
        inner_channel_height = channel_height + INNER_COMPONENT_HEIGHT
        inner_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + inner_channel_height / 2
        
        # Main channel length (full body minus end brackets on each side)
        main_channel_length = CORE_LENGTH - (2 * SIDE_BRACKET_DEPTH)
        
        # Full-width sensor channel (where sensors slide)
        with Locations((0, 0, channel_z_center)):
            Box(main_channel_length, channel_width, channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # Narrower inner channel above (for components/wires)
        with Locations((0, 0, inner_z_center)):
            Box(main_channel_length, inner_channel_width, inner_channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # Bottom opening (below sensor level) - narrower width
        with Locations((0, 0, (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2)):
            Box(main_channel_length, inner_channel_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # End openings for sensor insertion (sensors supported on 3 sides each)
        # Cut depth leaves 2mm wall at the outer edge
        bracket_cutout_height = channel_height
        bracket_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + bracket_cutout_height / 2
        end_cut_depth = SIDE_BRACKET_DEPTH - 2.0  # Leave 2mm wall
        
        # +X end opening (sensor 1)
        right_bracket_x = (CORE_LENGTH / 2) - 2.0 - (end_cut_depth / 2)  # Offset from outer edge by 2mm
        with Locations((right_bracket_x, 0, bracket_z_center)):
            Box(end_cut_depth, channel_width, bracket_cutout_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # -X end opening (sensor 2)
        left_bracket_x = -(CORE_LENGTH / 2) + 2.0 + (end_cut_depth / 2)  # Offset from outer edge by 2mm
        with Locations((left_bracket_x, 0, bracket_z_center)):
            Box(end_cut_depth, channel_width, bracket_cutout_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # 4) Middle section - thin walls between sensors (full sensor width cavity)
        # Centered on the full body length, double size (60mm)
        middle_section_length = GRIP_LENGTH * 2  # 60mm
        middle_cavity_width = SENSOR_WIDTH + CLEARANCE  # Full sensor width
        
        # Cut full-width cavity in middle section (above and below sensor level)
        # This makes the walls thinner in the grip area
        # Centered at 0 (body center)
        
        # Middle section - inner channel expanded to full sensor width
        with Locations((0, 0, inner_z_center)):
            Box(middle_section_length, middle_cavity_width, inner_channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # Middle section - bottom opening expanded to full sensor width
        with Locations((0, 0, (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2)):
            Box(middle_section_length, middle_cavity_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        
        # Extend walls from +X/-X sides to keep sensors away from edges
        if SENSOR_STOP_BUFFER > 0:
            extension_length = SENSOR_STOP_BUFFER
            wall_sections = [
                (channel_z_center, channel_width, channel_height),
                (inner_z_center, inner_channel_width, inner_channel_height),
                ((BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2, inner_channel_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT),
            ]
            # Anchor the stops against the inner face of the 2mm end wall
            end_wall_inner_face = (CORE_LENGTH / 2) - 2.0
            stop_center_from_edge = end_wall_inner_face - (extension_length / 2)

            for direction in (1, -1):
                stop_center_x = direction * stop_center_from_edge
                # Build solid wall extensions
                for z_center, width, height in wall_sections:
                    with Locations((stop_center_x, 0, z_center)):
                        Box(extension_length, width, height,
                            align=(Align.CENTER, Align.CENTER, Align.CENTER),
                            mode=Mode.ADD)

                # Cut sensor slide slot through the block (2.6mm height for sensor to slide in)
                with Locations((stop_center_x, 0, channel_z_center)):
                    Box(extension_length, channel_width, SENSOR_THICKNESS,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER),
                        mode=Mode.SUBTRACT)
        
        # 5) PCB Mounting standoffs on platform (full top is electronics area)
        platform_top_z = BODY_HEIGHT + PLATFORM_HEIGHT
        body_left_edge = -CORE_LENGTH / 2   # -72
        body_right_edge = CORE_LENGTH / 2   # +72
        
        # HX711 - on left side of platform (smaller board: 18mm x 26mm holes)
        hx711_center_x = body_left_edge + (HX711_HOLE_SPACING_X / 2) + 10.0  # -53
        hx711_center_y = 0.0
        
        hx711_positions = [
            (hx711_center_x - HX711_HOLE_SPACING_X/2, hx711_center_y - HX711_HOLE_SPACING_Y/2),
            (hx711_center_x - HX711_HOLE_SPACING_X/2, hx711_center_y + HX711_HOLE_SPACING_Y/2),
            (hx711_center_x + HX711_HOLE_SPACING_X/2, hx711_center_y - HX711_HOLE_SPACING_Y/2),
            (hx711_center_x + HX711_HOLE_SPACING_X/2, hx711_center_y + HX711_HOLE_SPACING_Y/2),
        ]
        
        for px, py in hx711_positions:
            with Locations((px, py, platform_top_z + STANDOFF_HEIGHT / 2)):
                Cylinder(radius=STANDOFF_DIA/2, height=STANDOFF_HEIGHT,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.ADD)
            with Locations((px, py, platform_top_z + STANDOFF_HEIGHT)):
                Cylinder(radius=M2_PILOT/2, height=STANDOFF_BORE_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)
        
        # ESP32 - on right side of platform (larger board: 56mm x 22mm holes)
        esp32_center_x = body_right_edge - (ESP32_HOLE_SPACING_X / 2) - 13.0  # Moved 3mm more to middle
        esp32_center_y = ESP32_Y_OFFSET
        
        esp32_positions = [
            (esp32_center_x - ESP32_HOLE_SPACING_X/2, esp32_center_y - ESP32_HOLE_SPACING_Y/2),
            (esp32_center_x - ESP32_HOLE_SPACING_X/2, esp32_center_y + ESP32_HOLE_SPACING_Y/2),
            (esp32_center_x + ESP32_HOLE_SPACING_X/2, esp32_center_y - ESP32_HOLE_SPACING_Y/2),
            (esp32_center_x + ESP32_HOLE_SPACING_X/2, esp32_center_y + ESP32_HOLE_SPACING_Y/2),
        ]
        
        for px, py in esp32_positions:
            with Locations((px, py, platform_top_z + STANDOFF_HEIGHT / 2)):
                Cylinder(radius=STANDOFF_DIA/2, height=STANDOFF_HEIGHT,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.ADD)
            with Locations((px, py, platform_top_z + STANDOFF_HEIGHT)):
                Cylinder(radius=M2_PILOT/2, height=STANDOFF_BORE_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)
        
        # Cable hole at ESP32's edge towards the middle
        hx711_right_edge = hx711_center_x + HX711_HOLE_SPACING_X / 2
        esp32_left_edge = esp32_center_x - ESP32_HOLE_SPACING_X / 2
        cable_hole_x = esp32_left_edge  # At ESP32's inner edge
        cable_hole_y = 0.0
        
        with Locations((cable_hole_x, cable_hole_y, BODY_HEIGHT + PLATFORM_HEIGHT / 2)):
            Box(cable_hole_depth, cable_hole_width, PLATFORM_HEIGHT + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        
        # Battery slot between HX711 and ESP32 - low stoppers retain the pack
        slot_spacing_margin = 3.0
        available_between_boards = esp32_left_edge - hx711_right_edge
        usable_slot_space = max(available_between_boards - (2 * slot_spacing_margin), 0.0)
        slot_inner_length = min(BATTERY_LENGTH + 6.0, usable_slot_space)
        if slot_inner_length <= 0:
            slot_inner_length = usable_slot_space
        slot_inner_width = BATTERY_SLOT_WIDTH  # Base clearance target
        slot_wall_height = 4.0
        battery_slot_center_x = (hx711_right_edge + esp32_left_edge) / 2
        
        if slot_inner_length > 0 and slot_inner_width > 0:
            # Only short stoppers on +X/-X so cover clearance is maintained
            stopper_thickness = 2.0
            stopper_width = min(slot_inner_width - 2.0, BATTERY_WIDTH)
            stopper_width = max(stopper_width, 4.0)
            stopper_offset_x = max((slot_inner_length / 2) - (stopper_thickness / 2), 0.0)
            
            for direction in (1, -1):
                with Locations((battery_slot_center_x + direction * stopper_offset_x, 0, platform_top_z)):
                    Box(
                        stopper_thickness,
                        stopper_width,
                        slot_wall_height,
                        align=(Align.CENTER, Align.CENTER, Align.MIN),
                        mode=Mode.ADD,
                    )
        
        # 6) Screw holes at 4 corners (shared by counterplate, sensor chamber, and top cover)
        # M3 clearance holes going all the way through
        cover_screw_x = (CORE_LENGTH / 2) - COVER_SCREW_INSET
        cover_screw_y = (BODY_WIDTH / 2) - COVER_SCREW_INSET

        cover_screw_positions = [
            (cover_screw_x, cover_screw_y),
            (cover_screw_x, -cover_screw_y),
            (-cover_screw_x, cover_screw_y),
            (-cover_screw_x, -cover_screw_y),
        ]

        for cx, cy in cover_screw_positions:
            with Locations((cx, cy, platform_top_z)):
                Cylinder(radius=M3_CLEARANCE/2, height=platform_top_z + 1.0,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

        # 7) Additional screws connecting sensor chamber to top cover (screw UP from chamber into cover)
        # M2 screws, positioned next to each corner hole
        upscrew_offset_y = 6.0  # Offset from corner holes in Y
        upscrew_offset_x = 1.0  # 1mm more towards X edge
        m2_clearance = 2.4  # M2 clearance hole
        m2_head_dia = 4.5  # M2 button head diameter
        m2_head_depth = 6.0  # Deeper counterbore so shorter screws can be used

        chamber_to_cover_positions = [
            (cover_screw_x + upscrew_offset_x, cover_screw_y - upscrew_offset_y),    # Next to +X,+Y corner
            (cover_screw_x + upscrew_offset_x, -cover_screw_y + upscrew_offset_y),   # Next to +X,-Y corner
            (-cover_screw_x - upscrew_offset_x, cover_screw_y - upscrew_offset_y),   # Next to -X,+Y corner
            (-cover_screw_x - upscrew_offset_x, -cover_screw_y + upscrew_offset_y),  # Next to -X,-Y corner
        ]

        for cx, cy in chamber_to_cover_positions:
            # Through hole for screw shaft (from bottom, going all the way through)
            with Locations((cx, cy, 0)):
                Cylinder(radius=m2_clearance/2, height=platform_top_z + 1.0,
                         align=(Align.CENTER, Align.CENTER, Align.MIN),
                         mode=Mode.SUBTRACT)
            # Counterbore for screw head (from BOTTOM face)
            with Locations((cx, cy, 0)):
                Cylinder(radius=m2_head_dia/2, height=m2_head_depth,
                         align=(Align.CENTER, Align.CENTER, Align.MIN),
                         mode=Mode.SUBTRACT)

    return body.part


def create_top_cover() -> object:
    """
    Rounded top cover for electronics.
    Screws onto the platform to protect ESP32 and HX711.
    Fully filleted on all edges (top, bottom, all corners).
    """
    
    fillet_radius = 6.0  # Radius for all fillets
    
    with BuildPart() as cover:
        # Main cover body - solid block first
        Box(CORE_LENGTH, BODY_WIDTH, COVER_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        
        # Fillet only the TOP edges (grip area) - not the bottom
        # Vertical edges (corners) first
        vertical_edges = cover.part.edges().filter_by(Axis.Z)
        fillet(vertical_edges, radius=fillet_radius)
        
        # Top horizontal edges
        top_edges = cover.part.edges().filter_by(
            lambda e: abs(e.center().Z - COVER_HEIGHT) < 0.5 and e.length > 1.0
        )
        fillet(top_edges, radius=fillet_radius)
        
        # Now hollow out the inside (corners thicker, middle walls thinner)
        corner_wall_reduction = 0.0  # Keep corners 1mm thicker than previous design
        middle_wall_reduction = 2.0  # More reduction in middle = thinner
        
        # Main cavity with corner thickness
        inner_length = CORE_LENGTH - (2 * COVER_WALL) - (2 * fillet_radius) + (2 * corner_wall_reduction)
        inner_width = BODY_WIDTH - (2 * COVER_WALL) - (2 * fillet_radius) + (2 * corner_wall_reduction)
        inner_height = COVER_HEIGHT - COVER_WALL - TOP_EXTRA_THICKNESS
        
        with Locations((0, 0, -0.1)):
            Box(inner_length, inner_width, inner_height + 0.1,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT)
        
        # Additional cuts from INSIDE to thin the middle walls (not corners)
        extra_cut = middle_wall_reduction - corner_wall_reduction  # 1mm more
        corner_keep = 8.0  # Keep this much at each corner (smaller)
        
        # Thin the +Y and -Y walls in the middle (cut from inside edge)
        middle_x_length = CORE_LENGTH - (2 * corner_keep)
        with Locations((0, inner_width/2, inner_height/2)):
            Box(middle_x_length, extra_cut * 2, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        with Locations((0, -inner_width/2, inner_height/2)):
            Box(middle_x_length, extra_cut * 2, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        
        # Thin the +X and -X walls in the middle (cut from inside edge)
        middle_y_length = BODY_WIDTH - (2 * corner_keep)
        with Locations((inner_length/2, 0, inner_height/2)):
            Box(extra_cut * 2, middle_y_length, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        with Locations((-inner_length/2, 0, inner_height/2)):
            Box(extra_cut * 2, middle_y_length, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        
        # Extra clearance around standoff positions (ESP32 and HX711 areas)
        # Keep cutouts away from corners (where screws are)
        
        # ESP32 area clearance (right side of platform) - wider for JST battery connector
        esp32_area_length = ESP32_HOLE_SPACING_X + 5.0  # Larger for more clearance
        esp32_area_width = 32.0 - ESP32_CLEARANCE_EXTRA  # Shrink clearance to thicken wall
        body_right_edge = CORE_LENGTH / 2
        esp32_center_x = body_right_edge - (ESP32_HOLE_SPACING_X / 2) - 13.0  # Original position
        esp32_center_y = ESP32_Y_OFFSET
        esp32_offset_y = esp32_center_y  # Match standoff offset so clearance aligns
        
        with Locations((esp32_center_x, esp32_offset_y, inner_height / 2)):
            Box(esp32_area_length, esp32_area_width, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        
        # HX711 area clearance (left side of platform) - smaller to avoid corners
        hx711_area_length = HX711_HOLE_SPACING_X - 5.0
        hx711_area_width = HX711_HOLE_SPACING_Y + 4.0
        body_left_edge = -CORE_LENGTH / 2
        hx711_center_x = body_left_edge + (HX711_HOLE_SPACING_X / 2) + 10.0
        
        with Locations((hx711_center_x, 0, inner_height / 2)):
            Box(hx711_area_length, hx711_area_width, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        
        # Battery clearance between HX711 and ESP32 so cover walls do not pinch the pack
        hx711_right_edge = hx711_center_x + HX711_HOLE_SPACING_X / 2
        esp32_left_edge = esp32_center_x - ESP32_HOLE_SPACING_X / 2
        battery_clear_length = (esp32_left_edge - hx711_right_edge) - 2.0
        battery_clear_width = BATTERY_COVER_CLEARANCE
        battery_clear_center_x = (hx711_right_edge + esp32_left_edge) / 2
        
        if battery_clear_length > 0:
            with Locations((battery_clear_center_x, 0, inner_height / 2)):
                Box(battery_clear_length, battery_clear_width, inner_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT)
        
        # USB charging port opening on ESP32 side (+X end) - stadium shaped
        usb_opening_width = 12.0  # Width for USB-C cables
        usb_opening_height = 6.0  # Height for various connectors
        usb_port_z = 6.0  # Lowered 2mm to align with ESP32 port stackup
        cut_depth = fillet_radius + 2.0
        
        # Stadium-shaped cutout (rounded rectangle) - shifted in Y to match ESP32 offset
        usb_offset_y = ESP32_Y_OFFSET  # Match ESP32 Y offset
        with BuildSketch(Plane.YZ.offset(CORE_LENGTH / 2 + 0.5)) as usb_slot:
            with Locations((usb_offset_y, usb_port_z)):
                SlotOverall(usb_opening_width, usb_opening_height)
        extrude(usb_slot.sketch, amount=-(cut_depth + 1.0), mode=Mode.SUBTRACT)
        
        # Screw holes with counterbore (clearance holes at corners)
        cover_screw_x = (CORE_LENGTH / 2) - COVER_SCREW_INSET
        cover_screw_y = (BODY_WIDTH / 2) - COVER_SCREW_INSET
        
        # Counterbore dimensions for M3 screw head
        screw_head_dia = 7.0  # M3 button head diameter
        counterbore_depth = 8.0  # Deeper so screw sits lower
        
        cover_screw_positions = [
            (cover_screw_x, cover_screw_y),
            (cover_screw_x, -cover_screw_y),
            (-cover_screw_x, cover_screw_y),
            (-cover_screw_x, -cover_screw_y),
        ]
        
        # Cut the screw holes (no solid bosses)
        for cx, cy in cover_screw_positions:
            # Through hole for screw shaft
            with Locations((cx, cy, COVER_HEIGHT)):
                Cylinder(radius=M3_CLEARANCE/2, height=COVER_HEIGHT + 1.0,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)
            # Counterbore for screw head (deeper)
            with Locations((cx, cy, COVER_HEIGHT)):
                Cylinder(radius=screw_head_dia/2, height=counterbore_depth,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

        # Additional screws from sensor chamber threading UP into top cover
        # M2 pilot holes in cover (screw threads into these from below)
        upscrew_offset_y = 6.0  # Must match sensor chamber offset
        upscrew_offset_x = 1.0  # Must match sensor chamber offset
        chamber_to_cover_positions = [
            (cover_screw_x + upscrew_offset_x, cover_screw_y - upscrew_offset_y),    # Next to +X,+Y corner
            (cover_screw_x + upscrew_offset_x, -cover_screw_y + upscrew_offset_y),   # Next to +X,-Y corner
            (-cover_screw_x - upscrew_offset_x, cover_screw_y - upscrew_offset_y),   # Next to -X,+Y corner
            (-cover_screw_x - upscrew_offset_x, -cover_screw_y + upscrew_offset_y),  # Next to -X,-Y corner
        ]

        for cx, cy in chamber_to_cover_positions:
            # M2 pilot hole for screw to thread into (from bottom of cover, going deep)
            with Locations((cx, cy, 0)):
                Cylinder(radius=M2_PILOT/2, height=15.0,
                         align=(Align.CENTER, Align.CENTER, Align.MIN),
                         mode=Mode.SUBTRACT)

    return cover.part


def create_counterplate() -> object:
    """
    Counterplate matching sensor chamber and top cover dimensions.
    - Same footprint as sensor chamber (CORE_LENGTH x BODY_WIDTH)
    - Shares corner screw holes with top cover (one screw holds all 3 parts)
    - Screw holes with hex nut pockets for clearance
    - Pressing parts for sensors
    """
    # Counterplate dimensions (match sensor chamber / top cover)
    counterplate_height = 8.0  # Thicker for more rigidity
    plate_length = CORE_LENGTH
    plate_width = BODY_WIDTH

    # Sensor area positioning (for pressing parts)
    sensor_area_center = -(ELECTRONICS_EXTENSION / 2)

    # Screw positions (match top cover - 4 corners)
    cover_screw_x = (CORE_LENGTH / 2) - COVER_SCREW_INSET
    cover_screw_y = (BODY_WIDTH / 2) - COVER_SCREW_INSET

    screw_positions = [
        (cover_screw_x, cover_screw_y),
        (cover_screw_x, -cover_screw_y),
        (-cover_screw_x, cover_screw_y),
        (-cover_screw_x, -cover_screw_y),
    ]

    # Nut dimensions (M3 hex nut: 5.5mm across flats, 2.4mm thick)
    M3_NUT_ACROSS_FLATS = 5.5
    M3_NUT_ACROSS_CORNERS = 6.35  # For clearance, use this
    M3_NUT_THICKNESS = 2.4
    NUT_CLEARANCE = 0.3
    NUT_POCKET_WIDTH = M3_NUT_ACROSS_CORNERS + NUT_CLEARANCE
    NUT_POCKET_DEPTH = M3_NUT_THICKNESS + 1.0  # Extra depth for nut + washer

    # Channel dimensions for pressing parts
    channel_width = SENSOR_WIDTH + CLEARANCE
    inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)

    with BuildPart() as plate:
        # 1) Main plate body (centered at origin, same as sensor chamber)
        Box(plate_length, plate_width, counterplate_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        # 2) Fillet edges FIRST on solid shape (like top cover)
        fillet_radius = 6.0
        top_fillet_radius = 2.5  # Smaller for top edges (plate is only 6mm tall)

        # Vertical edges (corners)
        vertical_edges = plate.part.edges().filter_by(Axis.Z)
        fillet(vertical_edges, radius=fillet_radius)

        # Top horizontal edges
        top_edges = plate.part.edges().filter_by(
            lambda e: abs(e.center().Z - counterplate_height) < 0.5 and e.length > 1.0
        )
        fillet(top_edges, radius=top_fillet_radius)

        # 3) Screw holes with nut pockets (after fillets)
        SCREW_HOLE_DIA = M3_CLEARANCE  # Wider for movement allowance

        for sx, sy in screw_positions:
            # Through hole for screw
            with Locations((sx, sy, counterplate_height)):
                Cylinder(radius=SCREW_HOLE_DIA / 2, height=counterplate_height + 1.0,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

            # Hex nut pocket from top (using circular approximation for simplicity)
            with Locations((sx, sy, counterplate_height)):
                Cylinder(radius=NUT_POCKET_WIDTH / 2, height=NUT_POCKET_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

        # 4) Pressing parts (extend down into sensor channels)
        # Middle section is centered at 0 with length = GRIP_LENGTH * 2 = 60mm
        # Sensor blocks are on either side of the middle section
        FITTING_CLEARANCE = 1.5  # Increased for wiggle room
        PRESSING_HEIGHT = 3.0  # Slightly shorter

        middle_section_length = GRIP_LENGTH * 2  # 60mm, same as sensor chamber
        pressing_width = inner_channel_width - (2 * FITTING_CLEARANCE)  # Smaller in Y
        pressing_length = SENSOR_BLOCK_LENGTH - 12.0  # Much shorter in X for more give (20mm instead of 29mm)

        # 1 cent euro coin dimensions (for metal stability)
        COIN_DIAMETER = 16.25
        COIN_THICKNESS = 1.67
        COIN_POCKET_DEPTH = COIN_THICKNESS + 0.3  # Slight extra for glue

        # Left pressing part (sensor 1) - just outside middle section on -X side
        left_pressing_x = -(middle_section_length / 2) - (SENSOR_BLOCK_LENGTH / 2)
        with Locations((left_pressing_x, 0, -PRESSING_HEIGHT / 2)):
            Box(pressing_length, pressing_width, PRESSING_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.ADD)

        # Coin pocket in left pressing part (from bottom)
        with Locations((left_pressing_x, 0, -PRESSING_HEIGHT)):
            Cylinder(radius=COIN_DIAMETER / 2, height=COIN_POCKET_DEPTH,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

        # Right pressing part (sensor 2) - just outside middle section on +X side
        right_pressing_x = (middle_section_length / 2) + (SENSOR_BLOCK_LENGTH / 2)
        with Locations((right_pressing_x, 0, -PRESSING_HEIGHT / 2)):
            Box(pressing_length, pressing_width, PRESSING_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.ADD)

        # Coin pocket in right pressing part (from bottom)
        with Locations((right_pressing_x, 0, -PRESSING_HEIGHT)):
            Cylinder(radius=COIN_DIAMETER / 2, height=COIN_POCKET_DEPTH,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

    return plate.part


def export_all() -> None:
    if export_stl is None:
        print("export_stl not available")
        return

    parts = [
        ("sensor_chamber.stl", create_sensor_chamber),
        ("top_cover.stl", create_top_cover),
        ("counterplate.stl", create_counterplate),
    ]
    
    for filename, create_func in parts:
        try:
            part = create_func()
            export_stl(part, filename)
            print(f"Exported: {filename}")
        except Exception as e:
            print(f"Failed to export {filename}: {e}")


if __name__ == "__main__":
    export_all()
