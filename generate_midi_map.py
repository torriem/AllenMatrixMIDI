#!/usr/bin/env python3
"""Generate the midiNoteMap C array from the wire assignments."""

from generate_schematic import WIRE_ASSIGNMENTS, OUTPUT_ASSIGNMENTS, NUM_KEYS

MIDI_BASE = 36
NUM_INPUTS = 6
NUM_OUTPUTS = 11

# Build the map: grid[input_wire-1][output_wire-1] = MIDI note
grid = [[0] * NUM_OUTPUTS for _ in range(NUM_INPUTS)]
for i in range(NUM_KEYS):
    in_w = WIRE_ASSIGNMENTS[i]
    out_w = OUTPUT_ASSIGNMENTS[i]
    midi = MIDI_BASE + i
    grid[in_w - 1][out_w - 1] = midi

# Print as C array rows
for row_idx, row in enumerate(grid):
    comma = "," if row_idx < NUM_INPUTS - 1 else " "
    vals = ", ".join(f"{v:3d}" for v in row)
    print(f"  {{{vals}}}{comma}  // IN{row_idx + 1}")
