"""Export the full Lowrails HX711 M3 v3 assembly and its component models."""

from argparse import ArgumentParser
from pathlib import Path

from build123d import (
    Align, Box, Color, Compound, Cylinder, Pos, RectangleRounded, RegularPolygon, Rot,
    export_step, export_stl, extrude,
)

import enclosure as shell
import sensor_chamber as chamber


def block(length, width, height):
    return Box(length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN))


def pcb(length, width, holes, hole_diameter):
    board = block(length, width, 1.6)
    for x, y in holes:
        board -= Pos(x, y, 0.8) * Cylinder(hole_diameter / 2, 3)
    return board


def load_cell():
    """Photo-based sensor reference with the v3 fit dimensions and tip pointing down."""
    plate = extrude(RectangleRounded(chamber.SENSOR_DEPTH, chamber.SENSOR_WIDTH, 1.5),
                    amount=chamber.SENSOR_THICKNESS)
    # Approximate the stamped U-shaped relief. Leave the tongue joined at +X.
    outer = RectangleRounded(25, 22, 5)
    inner = RectangleRounded(21, 18, 4)
    relief = extrude(outer - inner, amount=chamber.SENSOR_THICKNESS + 1)
    relief = relief & (Pos(-9, 0, 0) * block(36, 36, chamber.SENSOR_THICKNESS + 1))
    plate -= relief
    tip = Pos(-shell.SENSOR_TIP_OFFSET_FROM_CENTER, 0, -shell.SENSOR_TIP_PROTRUSION / 2)
    return plate + tip * Cylinder(5, shell.SENSOR_TIP_PROTRUSION + 0.02)


def hx711():
    """Reference board sized for the v3 two-hole mounting pattern."""
    holes = [(-8, sign * chamber.HX711M3_HOLE_SPACING / 2) for sign in (-1, 1)]
    board = pcb(22, 22, holes, 3.2)
    return board + Pos(-1, 0, 1.59) * block(10, 4, 1.4) + Pos(8, 0, 1.59) * block(3, 16, 2.7)


def firebeetle():
    """DFR1075 envelope with the USB-C end and onboard module represented."""
    holes = [(sx * chamber.ESP32_HOLE_SPACING_X / 2, sy * chamber.ESP32_HOLE_SPACING_Y / 2)
             for sx in (-1, 1) for sy in (-1, 1)]
    board = pcb(chamber.FIREBEETLE_BOARD_LENGTH, shell.FIREBEETLE_BOARD_WIDTH, holes, 2.2)
    return (board + Pos(-13, 0, 1.59) * block(19, 16, 2.6)
            + Pos(27, 0, 1.59) * block(8, 9, 3.2)
            + Pos(5, 9, 1.59) * block(8, 5, 4.1))


def battery():
    return extrude(RectangleRounded(46, 24, 2.0), amount=8.4)


def socket_screw(length, shaft_dia, head_dia, head_height, socket_width):
    """Fastener reference with the bearing face at Z=0 and shaft pointing down."""
    head = Cylinder(head_dia / 2, head_height, align=(Align.CENTER, Align.CENTER, Align.MIN))
    shaft = Pos(0, 0, 0.01) * Cylinder(
        shaft_dia / 2, length + 0.01, align=(Align.CENTER, Align.CENTER, Align.MAX)
    )
    socket = Pos(0, 0, head_height / 2) * extrude(
        RegularPolygon(socket_width / 2, 6, major_radius=False), amount=head_height
    )
    return (head + shaft) - socket


def corner_hardware(platform_z):
    head_seat = platform_z + shell.COVER_HEIGHT - shell.COVER_SCREW_HEAD_DEPTH
    nut_height = 2.4
    nut_top = -shell.COUNTERPLATE_NUT_SEAT_Z
    screw = socket_screw(head_seat - nut_top + nut_height + 0.5, 3, 5.5, 3, 2.5)
    nut = extrude(RegularPolygon(6.35 / 2, 6), amount=nut_height) - Cylinder(1.5, 6)
    insert = Cylinder(chamber.BRASS_INSERT_PILOT_DIA / 2, chamber.BRASS_INSERT_DEPTH)
    insert -= Cylinder(1.5, chamber.BRASS_INSERT_DEPTH + 1)
    positions = [
        (sx * (chamber.CORE_LENGTH / 2 - chamber.M3_SCREW_INSET),
         sy * (chamber.BODY_WIDTH / 2 - chamber.M3_SCREW_INSET))
        for sx in (-1, 1) for sy in (-1, 1)
    ]
    for index, (x, y) in enumerate(positions, start=1):
        yield f"Corner screw {index}", screw, Pos(x, y, head_seat), "#657684"
        yield f"Heat-set insert {index}", insert, Pos(x, y, platform_z - chamber.BRASS_INSERT_DEPTH / 2), "#c29443"
        yield f"M3 nylon nut {index}", nut, Pos(x, y, nut_top - nut_height), "#ded6be"


def board_hardware(platform_z):
    hx_screw = socket_screw(3.8, chamber.HX711M3_PILOT_DIA, 5.2, 1.8, 2)
    esp_screw = socket_screw(3.8, chamber.M2_PILOT, 3.7, 1.5, 1.5)
    # Represent the screw cores where they engage the printed pilot holes.
    for index, sign in enumerate((-1, 1), start=1):
        yield (
            f"HX711 screw {index}", hx_screw,
            Pos(chamber.HX711M3_HOLE_X,
                chamber.HX711M3_HOLE_Y + sign * chamber.HX711M3_HOLE_SPACING / 2,
                platform_z + chamber.HX711M3_STANDOFF_HEIGHT + 1.6),
            "#657684",
        )
    for index, (sx, sy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1)), start=1):
        yield (
            f"FireBeetle screw {index}", esp_screw,
            Pos(chamber.ESP32_CENTER_X + sx * chamber.ESP32_HOLE_SPACING_X / 2,
                chamber.ESP32_Y_OFFSET + sy * chamber.ESP32_HOLE_SPACING_Y / 2,
                platform_z + chamber.STANDOFF_HEIGHT + 1.6),
            "#657684",
        )


def parts():
    platform_z = chamber.BODY_HEIGHT + chamber.PLATFORM_HEIGHT
    rail_z = chamber.BOTTOM_LIP_HEIGHT + chamber.SENSOR_Z_LIFT
    sensor_x = (chamber.CORE_LENGTH / 2 - 2 - chamber.SENSOR_STOP_BUFFER
                + chamber.RAIL_STOP_DEPTH - chamber.SENSOR_DEPTH / 2)
    hx_x = chamber.HX711M3_HOLE_X + 8
    battery_x = hx_x + 11 + 1 + 46 / 2
    return [
        ("Top cover", shell.create_top_cover(), Pos(0, 0, platform_z), "#6987a4"),
        ("HX711 breakout", hx711(), Pos(hx_x, 0, platform_z + chamber.HX711M3_STANDOFF_HEIGHT), "#239276"),
        ("LiPo battery", battery(), Pos(battery_x, 0, platform_z), "#d98c37"),
        ("FireBeetle ESP32-C6", firebeetle(),
         Pos(chamber.ESP32_CENTER_X, chamber.ESP32_Y_OFFSET, platform_z + chamber.STANDOFF_HEIGHT), "#3167ad"),
        ("Sensor chamber", chamber.create_sensor_chamber(), Pos(), "#a6bace"),
        ("Load cell +X", load_cell(), Pos(sensor_x, 0, rail_z), "#b785b5"),
        ("Load cell -X", load_cell(), Pos(-sensor_x, 0, rail_z) * Rot(0, 0, 180), "#b785b5"),
        *[
            (f"Contact disc {sign:+d}", Cylinder(shell.COIN_DIAMETER / 2, shell.COIN_THICKNESS),
             Pos(sign * (sensor_x - shell.SENSOR_TIP_OFFSET_FROM_CENTER), 0,
                 -shell.COIN_POCKET_DEPTH + shell.COIN_THICKNESS / 2), "#bd8761")
            for sign in (1, -1)
        ],
        ("Counterplate", shell.create_counterplate(), Rot(0, 180, 0), "#6987a4"),
        *corner_hardware(platform_z),
        *board_hardware(platform_z),
    ]


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path(__file__).parent)
    output = parser.parse_args().output
    references = output / "components"
    references.mkdir(parents=True, exist_ok=True)
    files = {
        "Top cover": output / "top_cover.stl",
        "Sensor chamber": output / "sensor_chamber.stl",
        "Counterplate": output / "counterplate.stl",
        "Load cell +X": references / "load_cell.stl",
        "HX711 breakout": references / "hx711.stl",
        "FireBeetle ESP32-C6": references / "firebeetle.stl",
        "LiPo battery": references / "battery.stl",
    }
    placed = []
    for name, shape, transform, color in parts():
        if not shape.is_valid or len(shape.solids()) != 1:
            raise RuntimeError(f"Invalid solid: {name}")
        if name in files and not export_stl(shape, files[name]):
            raise RuntimeError(f"Could not export {files[name]}")
        item = transform * shape
        item.label = name
        item.color = Color(color)
        placed.append(item)
    if not export_step(Compound(label="ForceGripper v3", children=placed), output / "forcegripper_v3.step"):
        raise RuntimeError("Could not export the full assembly")


if __name__ == "__main__":
    main()
