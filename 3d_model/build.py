from __future__ import annotations

from build123d import (
    BuildPart,
    BuildSketch,
    Location,
    Rectangle,
    add,
    extrude,
    fillet,
)

# Prefer glTF export if available in build123d; otherwise, raise a helpful error at runtime
try:  # build123d >= version that includes export_gltf
    from build123d import export_gltf  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    export_gltf = None  # type: ignore

# Try to import a compound builder if provided by the installed build123d version
try:
    from build123d import make_compound  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    make_compound = None  # type: ignore


def create_rounded_block(
    length: float,
    width: float,
    thickness: float,
    corner_radius: float,
):
    """Create a single rectangular block with rounded top-view corners."""
    with BuildPart() as block:
        with BuildSketch() as face:
            Rectangle(width=length, height=width)
            fillet(face.vertices(), radius=corner_radius)
        extrude(amount=thickness)
    return block.part


def build_two_opposite_blocks(
    length: float = 20.0,
    width: float = 12.0,
    thickness: float = 6.0,
    corner_radius: float = 2.0,
    separation: float = 35.0,
):
    """
    Create two identical rounded-corner rectangular blocks placed opposite each
    other along the X axis, separated by the given center-to-center distance.
    Returns two separate parts so they import as distinct objects.
    """
    base_block = create_rounded_block(length, width, thickness, corner_radius)

    block_a = base_block.moved(Location((+separation / 2.0, 0.0, 0.0)))
    block_b = base_block.moved(Location((-separation / 2.0, 0.0, 0.0)))
    return block_a, block_b


def main(output_path: str = "two_rounded_blocks.gltf") -> None:
    block_a, block_b = build_two_opposite_blocks()
    if export_gltf is None:
        raise RuntimeError(
            "glTF export is not available. Ensure your build123d version supports `export_gltf`, "
            "or install a newer version."
        )
    # Prefer a real Compound if helper is available; otherwise export a part with two solids
    if make_compound is not None:
        scene = make_compound([block_a, block_b])
        export_gltf(scene, output_path)
    else:
        with BuildPart() as scene_part:
            add(block_a)
            add(block_b)
        export_gltf(scene_part.part, output_path)


if __name__ == "__main__":
    main()


