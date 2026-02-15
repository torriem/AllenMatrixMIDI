#!/usr/bin/env python3
"""Generate an SVG schematic of 61 organ key switches with diodes."""

import sys

# --- Configuration ---
NUM_KEYS = 61
STARTING_OCTAVE = 2  # C2 is the lowest note
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# --- Input wires (top) ---
NUM_INPUT_WIRES = 6
# Wire assignment: round-robin 1-6 across all 61 keys
WIRE_ASSIGNMENTS = [(i % NUM_INPUT_WIRES) + 1 for i in range(NUM_KEYS)]

# Colors for the 6 input wires
INPUT_WIRE_COLORS = {
    1: "#e6194b",  # red
    2: "#3cb44b",  # green
    3: "#4363d8",  # blue
    4: "#f58231",  # orange
    5: "#911eb4",  # purple
    6: "#42d4f4",  # cyan
}

# --- Output wires (bottom) ---
NUM_OUTPUT_WIRES = 11
# Output assignment: key 1 alone on wire 1, then groups of 6
# Key 0 -> wire 1, keys 1-6 -> wire 2, keys 7-12 -> wire 3, ...
def _build_output_assignments():
    assignments = [1]  # key 0 (C2) -> output wire 1
    for i in range(1, NUM_KEYS):
        wire = ((i - 1) // 6) + 2  # keys 1-6 -> 2, 7-12 -> 3, etc.
        assignments.append(wire)
    return assignments

OUTPUT_ASSIGNMENTS = _build_output_assignments()

# Colors for the 11 output wires
OUTPUT_WIRE_COLORS = {
    1:  "#800000",  # maroon
    2:  "#e6194b",  # red
    3:  "#f58231",  # orange
    4:  "#bfef45",  # lime
    5:  "#3cb44b",  # green
    6:  "#42d4f4",  # cyan
    7:  "#4363d8",  # blue
    8:  "#911eb4",  # purple
    9:  "#f032e6",  # magenta
    10: "#a9a9a9",  # grey
    11: "#469990",  # teal
}

# Layout dimensions (in SVG user units / pixels)
UNIT_SPACING = 45       # horizontal distance between key units
UNIT_WIDTH = 30         # width of each key unit's drawing area
MARGIN_LEFT = 30
MARGIN_TOP = 100        # room for input bus lines at top
MARGIN_BOTTOM = 160     # room for output bus lines at bottom

# Vertical positions within each unit (top to bottom, relative to key group)
LABEL_Y = 0
WIRE_IN_TOP = 15
WIRE_IN_BOTTOM = 35
SWITCH_TOP = 35
SWITCH_BOTTOM = 70
WIRE_MID_TOP = 70
WIRE_MID_BOTTOM = 85
DIODE_TOP = 85
DIODE_BOTTOM = 115
WIRE_OUT_TOP = 115
WIRE_OUT_BOTTOM = 135
UNIT_HEIGHT = 140

# Bus line configuration
INPUT_BUS_SPACING = 12    # vertical spacing between input bus lines
INPUT_BUS_START_Y = 10    # Y position of topmost input bus line

OUTPUT_BUS_SPACING = 12   # vertical spacing between output bus lines

# Stroke style
STROKE = "black"
STROKE_WIDTH = 1.5
BUS_STROKE_WIDTH = 2.0
TAP_STROKE_WIDTH = 1.2
FONT_SIZE = 10
BUS_FONT_SIZE = 11


def note_name(index):
    """Return the note name for key index (0-based)."""
    note = NOTE_NAMES[index % 12]
    octave = STARTING_OCTAVE + index // 12
    return f"{note}{octave}"


def input_bus_y(wire_num):
    """Return the Y coordinate for an input bus wire (1-based)."""
    return INPUT_BUS_START_Y + (wire_num - 1) * INPUT_BUS_SPACING


def output_bus_y(wire_num, key_group_y):
    """Return the Y coordinate for an output bus wire (1-based)."""
    output_bus_start = key_group_y + UNIT_HEIGHT + 15
    return output_bus_start + (wire_num - 1) * OUTPUT_BUS_SPACING


def svg_key_unit(index, cx, key_group_y):
    """Generate SVG elements for one key unit centered at horizontal position cx."""
    name = note_name(index)
    mid = cx
    in_wire = WIRE_ASSIGNMENTS[index]
    in_color = INPUT_WIRE_COLORS[in_wire]
    out_wire = OUTPUT_ASSIGNMENTS[index]
    out_color = OUTPUT_WIRE_COLORS[out_wire]

    lines = []
    lines.append(f'  <g id="key-{index + 1}-{name}" inkscape:label="{name}">')

    # Label
    lines.append(
        f'    <text x="{mid}" y="{key_group_y + LABEL_Y}" text-anchor="middle" '
        f'font-family="monospace" font-size="{FONT_SIZE}" fill="{STROKE}">'
        f'{name}</text>'
    )

    # --- Input tap (from input bus down to switch) ---
    tap_top_y = input_bus_y(in_wire)
    tap_bottom_y = key_group_y + WIRE_IN_TOP
    lines.append(
        f'    <circle cx="{mid}" cy="{tap_top_y}" r="2.5" fill="{in_color}"/>'
    )
    lines.append(
        f'    <line x1="{mid}" y1="{tap_top_y}" x2="{mid}" y2="{tap_bottom_y}" '
        f'stroke="{in_color}" stroke-width="{TAP_STROKE_WIDTH}"/>'
    )

    # Wire in (short segment into switch)
    lines.append(
        f'    <line x1="{mid}" y1="{key_group_y + WIRE_IN_TOP}" '
        f'x2="{mid}" y2="{key_group_y + WIRE_IN_BOTTOM}" '
        f'stroke="{in_color}" stroke-width="{STROKE_WIDTH}"/>'
    )

    # Switch: two terminals with an angled line (NO contact)
    lines.append(
        f'    <circle cx="{mid}" cy="{key_group_y + SWITCH_TOP}" r="2" fill="{STROKE}"/>'
    )
    lines.append(
        f'    <circle cx="{mid}" cy="{key_group_y + SWITCH_BOTTOM}" r="2" fill="{STROKE}"/>'
    )
    arm_dx = 8
    lines.append(
        f'    <line x1="{mid}" y1="{key_group_y + SWITCH_TOP}" '
        f'x2="{mid + arm_dx}" y2="{key_group_y + SWITCH_BOTTOM - 5}" '
        f'stroke="{STROKE}" stroke-width="{STROKE_WIDTH}"/>'
    )

    # Wire between switch and diode
    lines.append(
        f'    <line x1="{mid}" y1="{key_group_y + WIRE_MID_TOP}" '
        f'x2="{mid}" y2="{key_group_y + WIRE_MID_BOTTOM}" '
        f'stroke="{STROKE}" stroke-width="{STROKE_WIDTH}"/>'
    )

    # Diode (triangle pointing down + bar at cathode)
    tri_half_w = 8
    tri_h = DIODE_BOTTOM - DIODE_TOP - 6
    tri_top = key_group_y + DIODE_TOP
    tri_bottom = tri_top + tri_h
    bar_y_pos = tri_bottom

    lines.append(
        f'    <polygon points="{mid},{tri_bottom} '
        f'{mid - tri_half_w},{tri_top} '
        f'{mid + tri_half_w},{tri_top}" '
        f'fill="none" stroke="{STROKE}" stroke-width="{STROKE_WIDTH}"/>'
    )
    lines.append(
        f'    <line x1="{mid - tri_half_w}" y1="{bar_y_pos}" '
        f'x2="{mid + tri_half_w}" y2="{bar_y_pos}" '
        f'stroke="{STROKE}" stroke-width="{STROKE_WIDTH}"/>'
    )

    # Wire out (from diode down to output bus)
    wire_out_end = key_group_y + WIRE_OUT_BOTTOM
    out_bus_target = output_bus_y(out_wire, key_group_y)
    lines.append(
        f'    <line x1="{mid}" y1="{key_group_y + WIRE_OUT_TOP}" '
        f'x2="{mid}" y2="{out_bus_target}" '
        f'stroke="{out_color}" stroke-width="{TAP_STROKE_WIDTH}"/>'
    )
    # Connection dot on output bus line
    lines.append(
        f'    <circle cx="{mid}" cy="{out_bus_target}" r="2.5" fill="{out_color}"/>'
    )

    lines.append('  </g>')
    return "\n".join(lines)


def generate_svg(output_path):
    """Generate the full SVG file."""
    total_width = MARGIN_LEFT * 2 + (NUM_KEYS - 1) * UNIT_SPACING + UNIT_WIDTH
    key_group_y = MARGIN_TOP
    total_height = key_group_y + UNIT_HEIGHT + MARGIN_BOTTOM

    # Horizontal extent of bus lines
    first_cx = MARGIN_LEFT + UNIT_WIDTH / 2
    last_cx = MARGIN_LEFT + (NUM_KEYS - 1) * UNIT_SPACING + UNIT_WIDTH / 2
    bus_left = MARGIN_LEFT - 10
    bus_right = last_cx + 15

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'width="{total_width}" height="{total_height}" '
        f'viewBox="0 0 {total_width} {total_height}">'
    )
    parts.append('  <title>61-Key Organ Switch Matrix Schematic</title>')

    # Background
    parts.append(
        f'  <rect width="{total_width}" height="{total_height}" fill="white"/>'
    )

    # --- Input bus lines (top) ---
    parts.append('  <g id="input-bus-lines" inkscape:label="Input Bus Lines">')
    for wire_num in range(1, NUM_INPUT_WIRES + 1):
        y = input_bus_y(wire_num)
        color = INPUT_WIRE_COLORS[wire_num]
        parts.append(
            f'    <line x1="{bus_left}" y1="{y}" x2="{bus_right}" y2="{y}" '
            f'stroke="{color}" stroke-width="{BUS_STROKE_WIDTH}"/>'
        )
        parts.append(
            f'    <text x="{bus_left - 5}" y="{y + 4}" text-anchor="end" '
            f'font-family="monospace" font-size="{BUS_FONT_SIZE}" '
            f'fill="{color}" font-weight="bold">IN{wire_num}</text>'
        )
    parts.append('  </g>')

    # --- Key units ---
    for i in range(NUM_KEYS):
        cx = MARGIN_LEFT + i * UNIT_SPACING + UNIT_WIDTH / 2
        parts.append(svg_key_unit(i, cx, key_group_y))

    # --- Output bus lines (bottom, trimmed to last key in each group) ---
    # Find the last key index for each output wire
    output_last_key = {}
    for i in range(NUM_KEYS):
        w = OUTPUT_ASSIGNMENTS[i]
        output_last_key[w] = i  # keeps updating, so ends up with the last

    parts.append('  <g id="output-bus-lines" inkscape:label="Output Bus Lines">')
    for wire_num in range(1, NUM_OUTPUT_WIRES + 1):
        y = output_bus_y(wire_num, key_group_y)
        color = OUTPUT_WIRE_COLORS[wire_num]
        last_key_cx = MARGIN_LEFT + output_last_key[wire_num] * UNIT_SPACING + UNIT_WIDTH / 2
        parts.append(
            f'    <line x1="{bus_left}" y1="{y}" x2="{last_key_cx}" y2="{y}" '
            f'stroke="{color}" stroke-width="{BUS_STROKE_WIDTH}"/>'
        )
        parts.append(
            f'    <text x="{bus_left - 5}" y="{y + 4}" text-anchor="end" '
            f'font-family="monospace" font-size="{BUS_FONT_SIZE}" '
            f'fill="{color}" font-weight="bold">OUT{wire_num}</text>'
        )
    parts.append('  </g>')

    parts.append('</svg>')

    svg_content = "\n".join(parts)

    with open(output_path, "w") as f:
        f.write(svg_content)

    print(f"Generated {output_path} ({NUM_KEYS} keys, {total_width}x{total_height}px)")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "organ_keys_schematic.svg"
    generate_svg(output)
