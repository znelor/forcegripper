"""Cover and 11 mm counterplate from the Lowrails v3 enclosure design."""

from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Cylinder, Locations,
                       Mode, Plane, RectangleRounded, SlotOverall, add, extrude, fillet)

from sensor_chamber import (
    BODY_WIDTH,
    BOTTOM_LIP_HEIGHT,
    CLEARANCE,
    CORE_LENGTH,
    COVER_HOLLOW_END_INSET,
    COVER_HOLLOW_HALF_WIDTH,
    COVER_WALL,
    ELECTRONICS_CAVITY_HALF_LENGTH,
    ESP32_CENTER_X,
    ESP32_Y_OFFSET,
    FIREBEETLE_BOARD_LENGTH,
    HX711_CENTER_Y,
    INNER_COMPONENT_SIDE_INSET,
    M3_CLEARANCE,
    M3_SCREW_INSET,
    PLAN_CORNER_ROUND_RADIUS,
    RAIL_STOP_DEPTH,
    SENSOR_DEPTH,
    SENSOR_STOP_BUFFER,
    SENSOR_WIDTH,
    SENSOR_Z_LIFT,
    STANDOFF_DIA,
    _yz_prism,
)

FIREBEETLE_BOARD_WIDTH = 25.4
ESP32_COVER_END_CLEARANCE = 2.0
ESP32_COVER_SIDE_CLEARANCE = 2.0
ESP32_COVER_CLEARANCE_WIDTH = FIREBEETLE_BOARD_WIDTH + 2 * ESP32_COVER_SIDE_CLEARANCE
COVER_HEIGHT = 18.0
TOP_EXTRA_THICKNESS = 4.0
USB_C_OPENING_WIDTH = 16.0
USB_C_OPENING_HEIGHT = 8.0
USB_C_PORT_Z = 6.0
TOP_COVER_TOP_ROUND_RADIUS = 12.4
COUNTERPLATE_TOP_ROUND_RADIUS = 10.0
TOP_COVER_SIDE_ROUND_RADIUS = 2.0
COUNTERPLATE_SIDE_ROUND_RADIUS = 2.0
COVER_ENTRY_CHAMFER_HEIGHT = 0.35
COVER_ENTRY_CHAMFER_DEPTH = 0.3
HX711_BOARD_LENGTH = 25.0
HX711_BOARD_WIDTH = 17.5
HX711_HOLE_SPACING_X = 22.0
HX711_COVER_END_CLEARANCE = 2.0
HX711_COVER_SIDE_CLEARANCE = 2.0
HX711_WALL_CLEARANCE = 1.0
HX711_CENTER_X = (
    -ELECTRONICS_CAVITY_HALF_LENGTH
    + HX711_WALL_CLEARANCE
    + HX711_HOLE_SPACING_X / 2
    + STANDOFF_DIA / 2
)
COUNTERPLATE_THIN_HEIGHT = 11.0
COUNTERPLATE_HEIGHT = COUNTERPLATE_THIN_HEIGHT
COUNTERPLATE_NUT_SEAT_Z = 6.6
SENSOR_TIP_PROTRUSION = 3.0
SENSOR_TIP_OFFSET_FROM_CENTER = 5.0
COIN_DIAMETER = 16.25
COIN_THICKNESS = 1.67
COIN_FIT_CLEARANCE = 0.3
COIN_REST_GAP = 1.0
COIN_POCKET_DEPTH = (
    SENSOR_TIP_PROTRUSION
    - (BOTTOM_LIP_HEIGHT + SENSOR_Z_LIFT)
    + COIN_REST_GAP
    + COIN_THICKNESS
)


def _cut_top_cover_entry_chamfers(inner_length: float) -> None:
    for side in (-1, 1):
        inner_y = side * COVER_HOLLOW_HALF_WIDTH
        entry_y = side * (
            COVER_HOLLOW_HALF_WIDTH + COVER_ENTRY_CHAMFER_DEPTH
        )
        add(
            _yz_prism(
                [
                    (inner_y, 0),
                    (entry_y, 0),
                    (inner_y, COVER_ENTRY_CHAMFER_HEIGHT),
                ],
                inner_length,
            ),
            mode=Mode.SUBTRACT,
        )


def _trim_to_plan_rounded_outline(height: float) -> None:
    """Trim the part being built to the shared rounded-corner plan outline.

    Used for the cover and counterplate, whose vertical corner edges are
    partially consumed by the large top-face fillets; intersecting with a
    rounded-rectangle prism yields the same silhouette as the chamber's
    corner fillets through the full part height.
    """
    # Start well below z=0 so features protruding downward (counterplate
    # pressing pads) are not clipped
    with BuildSketch(Plane.XY.offset(-5.0)) as outline:
        RectangleRounded(CORE_LENGTH, BODY_WIDTH, PLAN_CORNER_ROUND_RADIUS)
    extrude(outline.sketch, amount=height + 10.0, mode=Mode.INTERSECT)


def create_top_cover() -> object:
    """
    Top cover for electronics with hollow clearance over reinforcement walls.
    """

    with BuildPart() as cover:
        # Main cover body
        Box(CORE_LENGTH, BODY_WIDTH, COVER_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Round only the top-facing long edges.
        top_long_edges = (
            cover.part.edges()
            .filter_by(Axis.X)
            .filter_by(lambda e: abs(e.center().Z - COVER_HEIGHT) < 0.5)
        )
        top_cover_round = min(TOP_COVER_TOP_ROUND_RADIUS, COVER_HEIGHT - 0.4, BODY_WIDTH / 2 - 0.4)
        fillet(top_long_edges, radius=top_cover_round)
        top_side_edges = (
            cover.part.edges()
            .filter_by(Axis.Y)
            .filter_by(lambda e: abs(e.center().Z - COVER_HEIGHT) < 0.5)
        )
        top_cover_side_round = min(TOP_COVER_SIDE_ROUND_RADIUS, COVER_HEIGHT - 0.4, CORE_LENGTH / 2 - 0.4)
        fillet(top_side_edges, radius=top_cover_side_round)

        # Hollow out the inside
        # Match Design H wall thicknesses.
        inner_length = CORE_LENGTH - 2 * (COVER_HOLLOW_END_INSET + 5.0)
        inner_width = 2 * COVER_HOLLOW_HALF_WIDTH
        inner_height = COVER_HEIGHT - COVER_WALL - TOP_EXTRA_THICKNESS - 1.0

        with Locations((0, 0, -0.1)):
            Box(inner_length, inner_width, inner_height + 0.1,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT)

        _cut_top_cover_entry_chamfers(inner_length)

        # ESP32 position (offset to preserve +X end wall)
        esp32_center_x = ESP32_CENTER_X
        esp32_center_y = ESP32_Y_OFFSET

        # Local FireBeetle clearance. This is wider than the general hollow so
        # the side connector has room; reinforcement walls stay clear of this region.
        esp32_area_length = FIREBEETLE_BOARD_LENGTH + 2 * ESP32_COVER_END_CLEARANCE
        esp32_area_width = ESP32_COVER_CLEARANCE_WIDTH

        with Locations((esp32_center_x, esp32_center_y, inner_height / 2)):
            Box(esp32_area_length, esp32_area_width, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)

        # HX711 clearance in the battery bay (25mm along X)
        hx711_area_length = HX711_BOARD_LENGTH + 2 * HX711_COVER_END_CLEARANCE
        hx711_area_width = HX711_BOARD_WIDTH + 2 * HX711_COVER_SIDE_CLEARANCE

        with Locations((HX711_CENTER_X, HX711_CENTER_Y, inner_height / 2)):
            Box(hx711_area_length, hx711_area_width, inner_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)

        # USB charging port opening
        usb_opening_width = USB_C_OPENING_WIDTH
        usb_opening_height = USB_C_OPENING_HEIGHT
        usb_port_z = USB_C_PORT_Z
        cut_depth = top_cover_round + 1.5

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

        _trim_to_plan_rounded_outline(COVER_HEIGHT)

    return cover.part


def create_counterplate(
    counterplate_height: float = COUNTERPLATE_HEIGHT,
) -> object:
    """
    Counterplate matching the sensor chamber dimensions.

    The assembly-facing coin pockets and the internal nut-seat plane stay
    fixed for every height. Extra thickness is added only to the external
    grip surface, so sensor preload and required screw length do not change.
    """
    if counterplate_height < COUNTERPLATE_THIN_HEIGHT:
        raise ValueError(
            f"Counterplate height must be at least {COUNTERPLATE_THIN_HEIGHT}mm"
        )

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
    NUT_POCKET_DEPTH = counterplate_height - COUNTERPLATE_NUT_SEAT_Z
    if NUT_POCKET_DEPTH < M3_NUT_THICKNESS + 2.0:
        raise ValueError("Counterplate is too thin for the nut and driver pocket")

    channel_width = SENSOR_WIDTH + CLEARANCE
    inner_channel_width = channel_width - (2 * INNER_COMPONENT_SIDE_INSET)

    with BuildPart() as plate:
        Box(plate_length, plate_width, counterplate_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        plate_top_long_edges = (
            plate.part.edges()
            .filter_by(Axis.X)
            .filter_by(lambda e: abs(e.center().Z - counterplate_height) < 0.5)
        )
        plate_top_round = min(
            COUNTERPLATE_TOP_ROUND_RADIUS,
            counterplate_height - 0.4,
            plate_width / 2 - 0.4,
        )
        fillet(plate_top_long_edges, radius=plate_top_round)
        plate_top_side_edges = (
            plate.part.edges()
            .filter_by(Axis.Y)
            .filter_by(lambda e: abs(e.center().Z - counterplate_height) < 0.5)
        )
        plate_side_round = min(
            COUNTERPLATE_SIDE_ROUND_RADIUS,
            counterplate_height - 0.4,
            plate_length / 2 - 0.4,
        )
        fillet(plate_top_side_edges, radius=plate_side_round)

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

        # Recessed coin pockets at the sensor TIP positions (tips sit 5mm
        # off the sensor centers, toward the device middle). The plate
        # face is flush - no protruding pads. The 1-cent coin drops into
        # the pocket; the sensor tip (protruding 1mm past the chamber
        # bottom) presses onto the coin with a 0.3mm gap at rest.
        # Sensor outer edge = stop wall inner face + RAIL_STOP_DEPTH
        sensor_outer_edge = (plate_length / 2) - 2.0 - SENSOR_STOP_BUFFER + RAIL_STOP_DEPTH
        sensor_center_x = sensor_outer_edge - SENSOR_DEPTH / 2
        tip_x = sensor_center_x - SENSOR_TIP_OFFSET_FROM_CENTER

        for direction in (1, -1):
            with Locations((direction * tip_x, 0, 0)):
                Cylinder(radius=(COIN_DIAMETER + COIN_FIT_CLEARANCE) / 2,
                         height=COIN_POCKET_DEPTH,
                         align=(Align.CENTER, Align.CENTER, Align.MIN),
                         mode=Mode.SUBTRACT)

        _trim_to_plan_rounded_outline(counterplate_height)

    return plate.part
