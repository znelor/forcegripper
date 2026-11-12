"""Export the full Lowrails HX711 M3 v3 assembly and its component models."""

from argparse import ArgumentParser
from pathlib import Path

from build123d import (
    Align, Box, Color, Compound, Cylinder, Pos, RectangleRounded, Rot,
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
    """Envelope of the square sensor, with the load tip pointing down."""
    plate = extrude(RectangleRounded(chamber.SENSOR_DEPTH, chamber.SENSOR_WIDTH, 1.5),
                    amount=chamber.SENSOR_THICKNESS)
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
