"""Generate the Lowrails HX711 M3 v3 sensor chamber in millimeters."""

from argparse import ArgumentParser
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Cylinder,
    Location,
    Locations,
    Mode,
    Plane,
    Polygon,
    RectangleRounded,
    SlotOverall,
    add,
    export_stl,
    extrude,
    fillet,
)

SENSOR_WIDTH = 34.0
SENSOR_DEPTH = 34.0
SENSOR_THICKNESS = 2.64
CLEARANCE = 0.5
BODY_WIDTH = 38.0
SENSOR_BLOCK_LENGTH = 32.0
GRIP_LENGTH = 30.0
SIDE_BRACKET_DEPTH = 6.0
SENSOR_AREA_LENGTH = 2 * SENSOR_BLOCK_LENGTH + GRIP_LENGTH
ELECTRONICS_EXTENSION = 71.0
CORE_LENGTH = SENSOR_AREA_LENGTH + ELECTRONICS_EXTENSION
PLATFORM_LENGTH = CORE_LENGTH
PLATFORM_WIDTH = BODY_WIDTH
PLATFORM_HEIGHT = 3.0
ESP32_HOLE_SPACING_X = 56.5
ESP32_HOLE_SPACING_Y = 22.0
ESP32_Y_OFFSET = 1.0
FIREBEETLE_BOARD_LENGTH = 60.0
ESP32_CENTER_X = (CORE_LENGTH / 2) - (ESP32_HOLE_SPACING_X / 2) - 8.0 - 5.0
ESP32_BOARD_KEEP_OUT_X_MIN = ESP32_CENTER_X - FIREBEETLE_BOARD_LENGTH / 2 - 4.0
STANDOFF_HEIGHT = 3.0
STANDOFF_DIA = 3.5
STANDOFF_BORE_DEPTH = STANDOFF_HEIGHT - 0.5
M2_PILOT = 1.7
M3_CLEARANCE = 3.4
M3_PILOT = 2.5
BRASS_INSERT_PILOT_DIA = 4.0
BRASS_INSERT_DEPTH = 6.0
COVER_WALL = 0.5
M3_SCREW_INSET = 5.0
COVER_HOLLOW_END_INSET = COVER_WALL + 6.0 - 2.5
COVER_HOLLOW_HALF_WIDTH = 14.65
ELECTRONICS_CAVITY_END_INSET = COVER_HOLLOW_END_INSET + 5.0
ELECTRONICS_CAVITY_HALF_LENGTH = CORE_LENGTH / 2 - ELECTRONICS_CAVITY_END_INSET
INNER_COMPONENT_SIDE_INSET = 4.0
BOTTOM_LIP_HEIGHT = 1.0
SENSOR_Z_LIFT_ORIGINAL = 1.0
RAIL_DROP = 0.5
ROOF_RELIEF_DEPTH = 1.0
ROOF_RELIEF_LAND = 4.0
SENSOR_Z_LIFT = SENSOR_Z_LIFT_ORIGINAL - RAIL_DROP
SENSOR_STOP_BUFFER = 24.0
RAIL_STOP_DEPTH = 4.0
PLAN_CORNER_ROUND_RADIUS = 5.0
REINFORCEMENT_WALL_CLEARANCE = 0.1
REINFORCEMENT_WALL_LENGTH = 14.0
REINFORCEMENT_WALL_THICKNESS = 2.4
REINFORCEMENT_WALL_HEIGHT = 3.0
REINFORCEMENT_WALL_LEAD_IN_HEIGHT = 0.5
REINFORCEMENT_WALL_LEAD_IN_RELIEF = 0.35
REINFORCEMENT_WALL_OUTER_Y = COVER_HOLLOW_HALF_WIDTH - REINFORCEMENT_WALL_CLEARANCE
REINFORCEMENT_CAVITY_END_CLEARANCE = 0.5
REINFORCEMENT_ESP32_X_CLEARANCE = 0.25
REINFORCEMENT_WALL_CENTERS_X = (
    (
        -ELECTRONICS_CAVITY_HALF_LENGTH
        + REINFORCEMENT_CAVITY_END_CLEARANCE
        + REINFORCEMENT_WALL_LENGTH / 2
    ),
    (
        ESP32_BOARD_KEEP_OUT_X_MIN
        - REINFORCEMENT_ESP32_X_CLEARANCE
        - REINFORCEMENT_WALL_LENGTH / 2
    ),
)
HX711_CENTER_Y = 0.0
HX711M3_HOLE_SPACING = 15.5
HX711M3_STANDOFF_DIA = 5.8
HX711M3_MIN_MATERIAL = 1.5
HX711M3_HOLE_X = (-ELECTRONICS_CAVITY_HALF_LENGTH + HX711M3_MIN_MATERIAL
                  + HX711M3_STANDOFF_DIA / 2)
HX711M3_HOLE_Y = HX711_CENTER_Y
HX711M3_STANDOFF_HEIGHT = 3.0
HX711M3_PILOT_DIA = M3_PILOT
HX711M3_BORE_DEPTH = HX711M3_STANDOFF_HEIGHT - 0.5
SENSOR_PASS_SLOT_CORNER_R = 1.0
CABLE_SLOT_CENTER_X = 0.0
SENSOR_PASS_SLOT_X_MARGIN = 2.0
SENSOR_PASS_SLOT_Y_WIDTH = 10.0
CABLE_SLOT_LENGTH = SENSOR_DEPTH + 2 * SENSOR_PASS_SLOT_X_MARGIN
CABLE_SLOT_WIDTH = SENSOR_PASS_SLOT_Y_WIDTH
BODY_HEIGHT = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT_ORIGINAL + SENSOR_THICKNESS


def slot_prism(
    center_x: float,
    center_y: float,
    center_z: float,
    length: float,
    width: float,
    height: float,
    mode: Mode,
) -> None:
    """Extrude a slot profile into a prism at a 3D center point."""
    z_min = center_z - height / 2
    slot_length = max(length, width)
    slot_width = min(length, width)
    with BuildSketch(Plane.XY.offset(z_min)) as profile:
        with Locations((center_x, center_y)):
            SlotOverall(slot_length, slot_width)
    extrude(profile.sketch, amount=height, mode=mode)


def _move_min_to(part: object, x: float, y: float, z: float) -> object:
    bb = part.bounding_box()
    return part.moved(Location((x - bb.min.X, y - bb.min.Y, z - bb.min.Z)))


def _yz_prism(points: list[tuple[float, float]], length: float) -> object:
    with BuildPart() as prism:
        with BuildSketch(Plane.YZ) as profile:
            Polygon(*points)
        extrude(profile.sketch, amount=length)
    return _move_min_to(
        prism.part,
        -length / 2,
        min(point[0] for point in points),
        min(point[1] for point in points),
    )


def _add_sensor_chamber_reinforcement_walls(platform_top_z: float) -> None:
    for side in (-1, 1):
        inner_y = side * (
            REINFORCEMENT_WALL_OUTER_Y - REINFORCEMENT_WALL_THICKNESS
        )
        outer_y = side * REINFORCEMENT_WALL_OUTER_Y
        lead_in_outer_y = side * (
            REINFORCEMENT_WALL_OUTER_Y - REINFORCEMENT_WALL_LEAD_IN_RELIEF
        )
        lead_in_base_z = (
            platform_top_z
            + REINFORCEMENT_WALL_HEIGHT
            - REINFORCEMENT_WALL_LEAD_IN_HEIGHT
        )
        wall_top_z = platform_top_z + REINFORCEMENT_WALL_HEIGHT

        wall_profile = [
            (inner_y, platform_top_z),
            (outer_y, platform_top_z),
            (outer_y, lead_in_base_z),
            (lead_in_outer_y, wall_top_z),
            (inner_y, wall_top_z),
        ]
        for center_x in REINFORCEMENT_WALL_CENTERS_X:
            add(
                _yz_prism(
                    wall_profile,
                    REINFORCEMENT_WALL_LENGTH,
                ).moved(Location((center_x, 0, 0))),
                mode=Mode.ADD,
            )


def create_sensor_chamber():
    """Build the Lowrails HX711 M3 v3 sensor chamber."""
    channel_width = SENSOR_WIDTH + CLEARANCE
    channel_height = SENSOR_THICKNESS + RAIL_DROP  # play above sensor

    with BuildPart() as body:
        # 1) Main body
        Box(CORE_LENGTH, BODY_WIDTH, BODY_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        # 2) Electronics platform on top
        with Locations((0, 0, BODY_HEIGHT)):
            Box(PLATFORM_LENGTH, PLATFORM_WIDTH, PLATFORM_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.ADD)

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

        slot_prism(
            center_x=0.0,
            center_y=0.0,
            center_z=channel_z_center,
            length=middle_section_length,
            width=middle_cavity_width,
            height=channel_height,
            mode=Mode.SUBTRACT,
        )

        slot_prism(
            center_x=0.0,
            center_y=0.0,
            center_z=(BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT) / 2,
            length=middle_section_length,
            width=middle_cavity_width,
            height=BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT,
            mode=Mode.SUBTRACT,
        )

        # Pass the 34 mm sensor through edge-first. Cut above the rails.
        slot_base_z = BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT
        slot_height = BODY_HEIGHT + PLATFORM_HEIGHT + 1.0 - slot_base_z
        with BuildSketch(Plane.XY.offset(slot_base_z)) as slot:
            with Locations((CABLE_SLOT_CENTER_X, 0)):
                RectangleRounded(CABLE_SLOT_LENGTH, CABLE_SLOT_WIDTH,
                                 SENSOR_PASS_SLOT_CORNER_R)
        extrude(slot.sketch, amount=slot_height, mode=Mode.SUBTRACT)

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

        # 4b) Roof relief over each sensor's deflecting centre
        if ROOF_RELIEF_DEPTH > 0:
            s_outer = CORE_LENGTH / 2 - 2.0 - SENSOR_STOP_BUFFER + RAIL_STOP_DEPTH
            s_center = s_outer - SENSOR_DEPTH / 2
            rl = SENSOR_DEPTH - 2 * ROOF_RELIEF_LAND
            rw = SENSOR_WIDTH - 2 * ROOF_RELIEF_LAND
            for direction in (1, -1):
                with Locations((direction * s_center, 0, BODY_HEIGHT)):
                    Box(rl, rw, ROOF_RELIEF_DEPTH,
                        align=(Align.CENTER, Align.CENTER, Align.MIN),
                        mode=Mode.SUBTRACT)

        # 5) PCB Mounting
        platform_top_z = BODY_HEIGHT + PLATFORM_HEIGHT
        # ESP32 (right side, offset to preserve +X end wall)
        esp32_center_x = ESP32_CENTER_X
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

        hx711_positions = [
            (HX711M3_HOLE_X, HX711M3_HOLE_Y - HX711M3_HOLE_SPACING / 2),
            (HX711M3_HOLE_X, HX711M3_HOLE_Y + HX711M3_HOLE_SPACING / 2),
        ]
        for px, py in hx711_positions:
            with Locations((px, py, platform_top_z + HX711M3_STANDOFF_HEIGHT / 2)):
                Cylinder(
                    radius=HX711M3_STANDOFF_DIA / 2,
                    height=HX711M3_STANDOFF_HEIGHT,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.ADD,
                )
        for px, py in hx711_positions:
            with Locations((px, py, platform_top_z + HX711M3_STANDOFF_HEIGHT)):
                Cylinder(
                    radius=HX711M3_PILOT_DIA / 2,
                    height=HX711M3_BORE_DEPTH,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                    mode=Mode.SUBTRACT,
                )

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

        _add_sensor_chamber_reinforcement_walls(platform_top_z)

        # Round the four vertical corner edges (plan-view / XY rounding)
        corner_edges = (
            body.part.edges()
            .filter_by(Axis.Z)
            .filter_by(
                lambda e: abs(abs(e.center().X) - CORE_LENGTH / 2) < 0.01
                and abs(abs(e.center().Y) - BODY_WIDTH / 2) < 0.01
            )
        )
        fillet(corner_edges, radius=PLAN_CORNER_ROUND_RADIUS)

    return body.part


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path(__file__).with_name("sensor_chamber.stl"))
    output = parser.parse_args().output
    chamber = create_sensor_chamber()
    if not chamber.is_valid:
        raise RuntimeError("Sensor chamber geometry is invalid")
    if not export_stl(chamber, output):
        raise RuntimeError(f"Could not export {output}")
    print(f"Exported {output}")


if __name__ == "__main__":
    main()
