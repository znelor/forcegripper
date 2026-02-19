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
    RegularPolygon,
    extrude,
)

import os

try:
    from build123d import export_stl
except Exception:
    export_stl = None

"""
Sensor Chamber - Design H
- HX711 mounted on a shelf ABOVE the battery (stacked layout)
- Shorter total device length due to stacking
- ESP32 positioned next to battery/HX711 stack
- Smaller battery dimensions, sensors inset 10mm from X edges
"""

# -----------------------------
# Sensor parameters
# -----------------------------
SENSOR_WIDTH = 34.0
SENSOR_DEPTH = 34.0
SENSOR_THICKNESS = 2.44
CLEARANCE = 0.3

# -----------------------------
# Main body parameters
# -----------------------------
BODY_WIDTH = 38.0
BODY_HEIGHT = None  # Computed after channel parameters (flush with sensor channel top)

SENSOR_BLOCK_LENGTH = 32.0
GRIP_LENGTH = 30.0
SIDE_BRACKET_DEPTH = 6.0

SENSOR_AREA_LENGTH = 2 * SENSOR_BLOCK_LENGTH + GRIP_LENGTH  # 94mm

# REDUCED: Electronics extension shortened since HX711 stacks on battery
ELECTRONICS_EXTENSION = 52.0  # Reduced from 80mm (saved ~28mm by stacking)
CORE_LENGTH = SENSOR_AREA_LENGTH + ELECTRONICS_EXTENSION  # 146mm (was 174mm)

# Electronics platform on top
PLATFORM_LENGTH = CORE_LENGTH
PLATFORM_WIDTH = BODY_WIDTH
PLATFORM_HEIGHT = 5.0

# -----------------------------
# PCB Mounting Parameters
# -----------------------------
ESP32_HOLE_SPACING_X = 56.0
ESP32_HOLE_SPACING_Y = 22.0
ESP32_Y_OFFSET = 1.0
ESP32_CLEARANCE_EXTRA = 1.0
HX711_HOLE_SPACING_X = 15.5
HX711_HOLE_SPACING_Y = 18.0  # unused, only 2 standoffs along X now

STANDOFF_HEIGHT = 3.0
STANDOFF_DIA = 3.5
STANDOFF_BORE_DEPTH = STANDOFF_HEIGHT - 0.5
M2_PILOT = 1.7  # Pilot for M2 self-tapping into plastic
M3_CLEARANCE = 3.4  # Close-fit clearance for M3 shaft to float freely (no force absorption)
M3_PILOT = 2.5
BRASS_INSERT_PILOT_DIA = 4.0  # Pilot hole for M3 heat-set brass insert
BRASS_INSERT_DEPTH = 6.0      # Brass insert length

# -----------------------------
# Top Cover Parameters
# -----------------------------
COVER_HEIGHT = 23.0  # Adjusted for smaller battery in HX711 shelf stack (+3mm for thicker top)
COVER_WALL = 0.5
TOP_EXTRA_THICKNESS = 4.0  # Thick top for rigidity (5.5mm total top thickness)
COVER_SCREW_INSET = 4.0  # For M2 chamber-to-cover screws (tight to edges for thin cover walls)
M3_SCREW_INSET = 5.0     # For M3 assembly screws (moved inward to avoid cutting sides)

# -----------------------------
# Battery Parameters (smaller battery)
# -----------------------------
BATTERY_LENGTH = 35.0  # Reduced from 60mm
BATTERY_WIDTH = 24.0
BATTERY_HEIGHT = 8.4
BATTERY_SLOT_WIDTH = 27.0
BATTERY_COVER_CLEARANCE = max(BATTERY_SLOT_WIDTH - 2.0, BATTERY_WIDTH + 0.5)

# -----------------------------
# HX711 Shelf Parameters (NEW)
# -----------------------------
SHELF_CLEARANCE_ABOVE_BATTERY = 1.5  # Gap between battery top and shelf bottom
SHELF_THICKNESS = 1.5  # Thickness of the shelf platform
SHELF_HEIGHT = BATTERY_HEIGHT + SHELF_CLEARANCE_ABOVE_BATTERY  # Height from platform to shelf bottom

# -----------------------------
# Channel parameters
# -----------------------------
INNER_COMPONENT_SIDE_INSET = 4.0
BOTTOM_LIP_HEIGHT = 1.0
SENSOR_Z_LIFT = 2.0

SENSOR_STOP_BUFFER = 10.0  # Sensors inset 10mm from X edges (pushed toward ends)
SENSOR_RAIL_DEPTH = 1.2
SENSOR_RAIL_WIDTH = 4.0
RAIL_STOP_DEPTH = 4.0  # How far sensor slides into stop wall (U-shaped stop)

# Compute body height so sensor channel top is exactly flush with body top
BODY_HEIGHT = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + SENSOR_THICKNESS


def create_sensor_chamber() -> object:
    """
    Sensor chamber with electronics platform on top.
    HX711 is mounted on a shelf above the battery.
    """

    channel_width = SENSOR_WIDTH + CLEARANCE
    channel_height = SENSOR_THICKNESS  # press fit, slight resistance

    with BuildPart() as body:
        # 1) Main body
        Box(CORE_LENGTH, BODY_WIDTH, BODY_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        # 2) Electronics platform on top
        with Locations((0, 0, BODY_HEIGHT)):
            Box(PLATFORM_LENGTH, PLATFORM_WIDTH, PLATFORM_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.ADD)

        # Fillet vertical edges
        fillet_radius = 6.0
        vertical_edges = body.part.edges().filter_by(Axis.Z)
        fillet(vertical_edges, radius=fillet_radius)

        # Cable hole parameters
        cable_hole_width = 8.0
        cable_hole_depth = 6.0

        # 3) Sensor channel - FULL BODY LENGTH (minus end brackets)
        channel_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + channel_height / 2
        inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)

        main_channel_length = CORE_LENGTH - (2 * SIDE_BRACKET_DEPTH)

        # Full-width sensor channel (sensor slides in here)
        with Locations((0, 0, channel_z_center)):
            Box(main_channel_length, channel_width, channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # Bottom opening (for counterplate pressing parts to reach sensor)
        with Locations((0, 0, (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2)):
            Box(main_channel_length, inner_channel_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # End openings for sensor insertion
        bracket_cutout_height = channel_height
        bracket_z_center = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT + bracket_cutout_height / 2
        end_cut_depth = SIDE_BRACKET_DEPTH - 2.0

        # +X end opening
        right_bracket_x = (CORE_LENGTH / 2) - 2.0 - (end_cut_depth / 2)
        with Locations((right_bracket_x, 0, bracket_z_center)):
            Box(end_cut_depth, channel_width, bracket_cutout_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # -X end opening
        left_bracket_x = -(CORE_LENGTH / 2) + 2.0 + (end_cut_depth / 2)
        with Locations((left_bracket_x, 0, bracket_z_center)):
            Box(end_cut_depth, channel_width, bracket_cutout_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # 4) Middle section - full opening (thin side walls only)
        middle_section_length = GRIP_LENGTH * 2
        middle_cavity_width = SENSOR_WIDTH + CLEARANCE

        with Locations((0, 0, channel_z_center)):
            Box(middle_section_length, middle_cavity_width, channel_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        with Locations((0, 0, (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2)):
            Box(middle_section_length, middle_cavity_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

        # Sensor stop walls
        if SENSOR_STOP_BUFFER > 0:
            extension_length = SENSOR_STOP_BUFFER
            wall_sections = [
                (channel_z_center, channel_width, channel_height),
                ((BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2, inner_channel_width, BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT),
            ]
            end_wall_inner_face = (CORE_LENGTH / 2) - 2.0
            stop_center_from_edge = end_wall_inner_face - (extension_length / 2)

            for direction in (1, -1):
                stop_center_x = direction * stop_center_from_edge
                for z_center, width, height in wall_sections:
                    with Locations((stop_center_x, 0, z_center)):
                        Box(extension_length, width, height,
                            align=(Align.CENTER, Align.CENTER, Align.CENTER),
                            mode=Mode.ADD)

                # U-shaped rail stop: only cut RAIL_STOP_DEPTH into the stop wall
                rail_cut_x = stop_center_x - direction * (extension_length / 2 - RAIL_STOP_DEPTH / 2)
                with Locations((rail_cut_x, 0, channel_z_center)):
                    Box(RAIL_STOP_DEPTH, channel_width, channel_height,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER),
                        mode=Mode.SUBTRACT)

        # 5) PCB Mounting - STACKED LAYOUT (battery/HX711 next to ESP32)
        platform_top_z = BODY_HEIGHT + PLATFORM_HEIGHT
        body_left_edge = -CORE_LENGTH / 2
        body_right_edge = CORE_LENGTH / 2

        # ========================================
        # ESP32 (right side, offset to preserve +X end wall)
        # ========================================
        esp32_center_x = body_right_edge - (ESP32_HOLE_SPACING_X / 2) - 8.0 - 5.0
        esp32_center_y = ESP32_Y_OFFSET
        esp32_left_edge = esp32_center_x - ESP32_HOLE_SPACING_X / 2

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

        # ========================================
        # Battery/HX711 Shelf (next to ESP32, on its left)
        # ========================================
        shelf_wall_thickness = 1.0
        shelf_platform_width = BATTERY_WIDTH + 2.0
        shelf_platform_length = BATTERY_LENGTH + 2.0
        shelf_top_z = platform_top_z + SHELF_HEIGHT + SHELF_THICKNESS

        # Position battery/shelf to the left of ESP32, with gap for cover pillar
        battery_shelf_center_x = esp32_left_edge - 14.0 - (shelf_platform_length / 2)
        battery_shelf_center_y = 0.0

        # Left and right support walls for the shelf
        wall_height = SHELF_HEIGHT + SHELF_THICKNESS
        for y_direction in (1, -1):
            wall_y = battery_shelf_center_y + y_direction * (shelf_platform_width / 2 + shelf_wall_thickness / 2)
            with Locations((battery_shelf_center_x, wall_y, platform_top_z + wall_height / 2)):
                Box(shelf_platform_length, shelf_wall_thickness, wall_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.ADD)

        # Retaining wall on right side (toward ESP32), battery slides in from left
        lip_height = 4.0
        lip_thickness = 2.0
        lip_x = battery_shelf_center_x + (shelf_platform_length / 2 - lip_thickness / 2)
        with Locations((lip_x, battery_shelf_center_y, platform_top_z + lip_height / 2)):
            Box(lip_thickness, shelf_platform_width - 4.0, lip_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.ADD)

        # Shelf platform (where HX711 sits)
        with Locations((battery_shelf_center_x, battery_shelf_center_y, platform_top_z + SHELF_HEIGHT + SHELF_THICKNESS / 2)):
            Box(shelf_platform_length - 4.0, shelf_platform_width, SHELF_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.ADD)

        # HX711 standoffs on top of shelf
        hx711_center_x = battery_shelf_center_x
        hx711_center_y = 0.0

        HX711_STANDOFF_HEIGHT = 2.5
        HX711_BORE_DEPTH = HX711_STANDOFF_HEIGHT - 0.5

        hx711_edge_x = battery_shelf_center_x + shelf_platform_length / 2 - STANDOFF_DIA / 2 - 3.0
        hx711_positions = [
            (hx711_edge_x, hx711_center_y - HX711_HOLE_SPACING_X / 2),
            (hx711_edge_x, hx711_center_y + HX711_HOLE_SPACING_X / 2),
        ]

        for px, py in hx711_positions:
            with Locations((px, py, shelf_top_z + HX711_STANDOFF_HEIGHT / 2)):
                Cylinder(radius=STANDOFF_DIA/2, height=HX711_STANDOFF_HEIGHT,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.ADD)
            with Locations((px, py, shelf_top_z + HX711_STANDOFF_HEIGHT)):
                Cylinder(radius=M2_PILOT/2, height=HX711_BORE_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

        # ========================================
        # Cable hole (between battery shelf and ESP32)
        # ========================================
        battery_shelf_right_edge = battery_shelf_center_x + shelf_platform_length / 2
        cable_hole_x = (battery_shelf_right_edge + esp32_left_edge) / 2
        cable_hole_y = 0.0

        with Locations((cable_hole_x, cable_hole_y, BODY_HEIGHT + PLATFORM_HEIGHT / 2)):
            Box(cable_hole_depth, cable_hole_width, PLATFORM_HEIGHT + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)

        # 6) M3 corner screw holes with brass insert at top
        # Long M3 screws go from top cover, thread into brass insert in
        # sensor chamber (coupling cover to chamber), continue through
        # clearance hole to counterplate where a nut holds the assembly.
        m3_screw_x = (CORE_LENGTH / 2) - M3_SCREW_INSET
        m3_screw_y = (BODY_WIDTH / 2) - M3_SCREW_INSET

        m3_screw_positions = [
            (m3_screw_x, m3_screw_y),
            (m3_screw_x, -m3_screw_y),
            (-m3_screw_x, m3_screw_y),
            (-m3_screw_x, -m3_screw_y),
        ]

        for cx, cy in m3_screw_positions:
            # Through-hole for screw shaft (full height)
            with Locations((cx, cy, platform_top_z)):
                Cylinder(radius=M3_CLEARANCE/2, height=platform_top_z + 1.0,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)
            # Brass insert pilot hole from platform top
            with Locations((cx, cy, platform_top_z)):
                Cylinder(radius=BRASS_INSERT_PILOT_DIA/2, height=BRASS_INSERT_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

    return body.part


def create_top_cover() -> object:
    """
    Top cover for electronics - adjusted for HX711 shelf stack.
    """

    fillet_radius = 6.0

    with BuildPart() as cover:
        # Main cover body
        Box(CORE_LENGTH, BODY_WIDTH, COVER_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Fillet vertical edges
        vertical_edges = cover.part.edges().filter_by(Axis.Z)
        fillet(vertical_edges, radius=fillet_radius)

        # Top horizontal edges
        top_edges = cover.part.edges().filter_by(
            lambda e: abs(e.center().Z - COVER_HEIGHT) < 0.5 and e.length > 1.0
        )
        fillet(top_edges, radius=fillet_radius)

        # Hollow out the inside
        wall_inset = COVER_WALL + fillet_radius - 2.5  # accounts for outer fillet at corners
        inner_length = CORE_LENGTH - 2 * (wall_inset + 5.0)  # short end walls 10mm thick for M3 screws
        inner_width = BODY_WIDTH - 2 * wall_inset
        inner_height = COVER_HEIGHT - COVER_WALL - TOP_EXTRA_THICKNESS - 1.0

        with Locations((0, 0, -0.1)):
            Box(inner_length, inner_width, inner_height + 0.1,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT)

        # Calculate positions (must match sensor chamber)
        body_left_edge = -CORE_LENGTH / 2
        body_right_edge = CORE_LENGTH / 2

        # ESP32 position (offset to preserve +X end wall)
        esp32_center_x = body_right_edge - (ESP32_HOLE_SPACING_X / 2) - 8.0 - 5.0
        esp32_center_y = ESP32_Y_OFFSET
        esp32_left_edge = esp32_center_x - ESP32_HOLE_SPACING_X / 2

        # Battery/shelf position (next to ESP32)
        shelf_platform_width = BATTERY_WIDTH + 4.0
        shelf_platform_length = BATTERY_LENGTH + 4.0
        battery_shelf_center_x = esp32_left_edge - 14.0 - (shelf_platform_length / 2)

        # ESP32 area clearance (narrower to avoid cutting into corner screw areas)
        esp32_area_length = ESP32_HOLE_SPACING_X + 5.0
        esp32_area_width = 26.0  # Reduced to avoid Y corners at ±15mm

        with Locations((esp32_center_x, esp32_center_y, inner_height / 2)):
            Box(esp32_area_length, esp32_area_width, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)

        # Battery/HX711 shelf area clearance (narrower to avoid corner screw areas)
        shelf_area_length = shelf_platform_length + 8.0
        shelf_area_width = 26.0  # Reduced to avoid Y corners at ±15mm

        with Locations((battery_shelf_center_x, 0, inner_height / 2)):
            Box(shelf_area_length, shelf_area_width, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)

        # Gap clearance between battery shelf and ESP32 (cable hole area)
        battery_shelf_right_edge = battery_shelf_center_x + shelf_platform_length / 2
        gap_center_x = (battery_shelf_right_edge + esp32_left_edge) / 2
        gap_length = esp32_left_edge - battery_shelf_right_edge + 4.0

        if gap_length > 0:
            with Locations((gap_center_x, 0, inner_height / 2)):
                Box(gap_length, 20.0, inner_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT)

        # USB charging port opening
        usb_opening_width = 12.0
        usb_opening_height = 6.0
        usb_port_z = 6.0
        cut_depth = fillet_radius + 2.0

        usb_offset_y = ESP32_Y_OFFSET
        with BuildSketch(Plane.YZ.offset(CORE_LENGTH / 2 + 0.5)) as usb_slot:
            with Locations((usb_offset_y, usb_port_z)):
                SlotOverall(usb_opening_width, usb_opening_height)
        extrude(usb_slot.sketch, amount=-(cut_depth + 1.0), mode=Mode.SUBTRACT)

        # M3 corner screws: 4 screws at corners matching sensor chamber
        # Screw head in counterbore at top, shaft passes through to sensor chamber
        m3_screw_x = (CORE_LENGTH / 2) - M3_SCREW_INSET
        m3_screw_y = (BODY_WIDTH / 2) - M3_SCREW_INSET
        cover_screw_head_dia = 5.65
        cover_screw_head_depth = 12.0

        cover_screw_positions = [
            (m3_screw_x, m3_screw_y),
            (m3_screw_x, -m3_screw_y),
            (-m3_screw_x, m3_screw_y),
            (-m3_screw_x, -m3_screw_y),
        ]

        for cx, cy in cover_screw_positions:
            # M3 clearance through-hole
            with Locations((cx, cy, COVER_HEIGHT / 2)):
                Cylinder(radius=M3_CLEARANCE/2, height=COVER_HEIGHT + 2.0,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.SUBTRACT)
            # Counterbore for screw head from top
            with Locations((cx, cy, COVER_HEIGHT)):
                Cylinder(radius=cover_screw_head_dia/2, height=cover_screw_head_depth,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

    return cover.part


def create_counterplate() -> object:
    """
    Counterplate matching the shorter sensor chamber dimensions.
    """
    counterplate_height = 11.0
    plate_length = CORE_LENGTH
    plate_width = BODY_WIDTH

    m3_screw_x = (CORE_LENGTH / 2) - M3_SCREW_INSET
    m3_screw_y = (BODY_WIDTH / 2) - M3_SCREW_INSET

    screw_positions = [
        (m3_screw_x, m3_screw_y),
        (m3_screw_x, -m3_screw_y),
        (-m3_screw_x, m3_screw_y),
        (-m3_screw_x, -m3_screw_y),
    ]

    M3_NUT_ACROSS_CORNERS = 6.35
    M3_NUT_THICKNESS = 2.4
    NUT_CLEARANCE = 0.3
    NUT_POCKET_WIDTH = M3_NUT_ACROSS_CORNERS + NUT_CLEARANCE
    NUT_POCKET_DEPTH = M3_NUT_THICKNESS + 2.0  # +1mm extra for turning clearance

    channel_width = SENSOR_WIDTH + CLEARANCE
    inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)

    with BuildPart() as plate:
        Box(plate_length, plate_width, counterplate_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        fillet_radius = 6.0
        top_fillet_radius = 2.5

        vertical_edges = plate.part.edges().filter_by(Axis.Z)
        fillet(vertical_edges, radius=fillet_radius)

        top_edges = plate.part.edges().filter_by(
            lambda e: abs(e.center().Z - counterplate_height) < 0.5 and e.length > 1.0
        )
        fillet(top_edges, radius=top_fillet_radius)

        SCREW_HOLE_DIA = M3_CLEARANCE

        NUT_FLAT_DIA = 12.0  # Wide flat pocket so nut driver can reach the nut

        for sx, sy in screw_positions:
            with Locations((sx, sy, counterplate_height)):
                Cylinder(radius=SCREW_HOLE_DIA / 2, height=counterplate_height + 1.0,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

            # Single wide pocket - nut sits at bottom, driver fits in from top
            with Locations((sx, sy, counterplate_height)):
                Cylinder(radius=NUT_FLAT_DIA / 2, height=NUT_POCKET_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)

        # Pressing parts - extend down to reach sensor through bottom opening
        FITTING_CLEARANCE = 1.5
        PRESSING_HEIGHT = 1.5

        pressing_width = inner_channel_width - (2 * FITTING_CLEARANCE)
        pressing_length = SENSOR_BLOCK_LENGTH - 13.0

        # Sensor tip: 7.8mm diameter round active area
        SENSOR_TIP_DIA = 7.8
        SENSOR_TIP_PAD_DIA = SENSOR_TIP_DIA + 4.0  # 11.8mm pad with margin around tip

        COIN_DIAMETER = 16.25
        COIN_THICKNESS = 1.67
        COIN_POCKET_DEPTH = COIN_THICKNESS + 0.3

        # Pressing parts aligned with actual sensor stop position
        # Sensor outer edge = stop wall inner face + RAIL_STOP_DEPTH
        sensor_outer_edge = (plate_length / 2) - 2.0 - SENSOR_STOP_BUFFER + RAIL_STOP_DEPTH
        sensor_center_x = sensor_outer_edge - SENSOR_DEPTH / 2 - 5.0  # 5mm toward middle

        for direction in (1, -1):
            px = direction * sensor_center_x
            if PRESSING_HEIGHT > 0:
                with Locations((px, 0, -PRESSING_HEIGHT / 2)):
                    Box(pressing_length, pressing_width, PRESSING_HEIGHT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER),
                        mode=Mode.ADD)

            # Coin pocket on the pressing surface (bottom face)
            with Locations((px, 0, -PRESSING_HEIGHT)):
                Cylinder(radius=COIN_DIAMETER / 2, height=COIN_POCKET_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MIN),
                         mode=Mode.SUBTRACT)

    return plate.part


def create_test_hex_pin() -> object:
    """Single hex pin for fit testing."""
    hex_across_flats = 2.4
    pin_height = 10.0
    with BuildPart() as pin:
        with BuildSketch() as sk:
            RegularPolygon(radius=hex_across_flats / 2, side_count=6, major_radius=False)
        extrude(sk.sketch, amount=pin_height)
    return pin.part


def create_brass_insert_test() -> object:
    """
    Small test block to verify brass insert fit.
    Matches the sensor chamber corner geometry:
    - Brass insert pilot hole from top
    - M3 clearance hole below
    And a matching cover piece next to it:
    - Counterbore for screw head
    - M3 clearance hole through
    """
    block_size = 12.0
    chamber_height = PLATFORM_HEIGHT + BRASS_INSERT_DEPTH + 2.0  # enough for insert + clearance

    with BuildPart() as test:
        # Sensor chamber test block (left)
        Box(block_size, block_size, chamber_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Brass insert pilot hole from top
        with Locations((0, 0, chamber_height)):
            Cylinder(radius=BRASS_INSERT_PILOT_DIA / 2, height=BRASS_INSERT_DEPTH,
                     align=(Align.CENTER, Align.CENTER, Align.MAX),
                     mode=Mode.SUBTRACT)

        # M3 clearance hole through the rest
        with Locations((0, 0, chamber_height)):
            Cylinder(radius=M3_CLEARANCE / 2, height=chamber_height + 1.0,
                     align=(Align.CENTER, Align.CENTER, Align.MAX),
                     mode=Mode.SUBTRACT)

        # Cover test block (right, next to chamber block)
        cover_top_thickness = COVER_HEIGHT - (COVER_HEIGHT - COVER_WALL - TOP_EXTRA_THICKNESS - 1.0)
        cover_block_height = cover_top_thickness + 3.5 + 2.0  # top + counterbore + margin
        spacing = block_size + 2.0

        with Locations((spacing, 0, 0)):
            Box(block_size, block_size, cover_block_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.ADD)

        # M3 clearance through-hole
        with Locations((spacing, 0, cover_block_height / 2)):
            Cylinder(radius=M3_CLEARANCE / 2, height=cover_block_height + 1.0,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER),
                     mode=Mode.SUBTRACT)

        # Counterbore for screw head from top
        cover_screw_head_dia = 5.65
        cover_screw_head_depth = 12.0
        with Locations((spacing, 0, cover_block_height)):
            Cylinder(radius=cover_screw_head_dia / 2, height=cover_screw_head_depth,
                     align=(Align.CENTER, Align.CENTER, Align.MAX),
                     mode=Mode.SUBTRACT)

    return test.part


def create_test_standoff() -> object:
    """Small test platform with one standoff to verify M2 screw fit."""
    base_size = 10.0
    base_height = 2.0

    with BuildPart() as test:
        # Base platform
        Box(base_size, base_size, base_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Standoff on top
        with Locations((0, 0, base_height + STANDOFF_HEIGHT / 2)):
            Cylinder(radius=STANDOFF_DIA / 2, height=STANDOFF_HEIGHT,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER),
                     mode=Mode.ADD)

        # Pilot hole
        with Locations((0, 0, base_height + STANDOFF_HEIGHT)):
            Cylinder(radius=M2_PILOT / 2, height=STANDOFF_BORE_DEPTH,
                     align=(Align.CENTER, Align.CENTER, Align.MAX),
                     mode=Mode.SUBTRACT)

    return test.part


def export_all() -> None:
    if export_stl is None:
        print("export_stl not available")
        return

    parts = [
        ("sensor_chamber.stl", create_sensor_chamber),
        ("top_cover.stl", create_top_cover),
        ("counterplate.stl", create_counterplate),
        ("test_hex_pin.stl", create_test_hex_pin),
        ("test_brass_insert.stl", create_brass_insert_test),
        ("test_standoff.stl", create_test_standoff),
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
