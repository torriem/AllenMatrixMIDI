#!/usr/bin/env python3
"""
Generate KiCad 8 project for keyboard matrix passthrough board.

Passes 29 keyboard matrix lines (from an 11x18 matrix) directly through
from card edge connectors to pin headers for debugging/testing.

Board features:
- Female 0.125" pitch 44-position card edge socket (computer side) on top edge
- Male 0.125" pitch 44-position card edge fingers (keyboard input) on bottom edge
- 2x15 pin header for keyboard signals (KB Header)
- 2x15 pin header for computer signals (COMP Header)

No relays, Teensy, diodes, or power circuitry.

Usage: python3 generate_keyboard_passthrough.py
Output: keyboard_passthrough/ directory with KiCad 8 project files
"""

import json
import os
import uuid as _uuid

# ============================================================
# Configuration
# ============================================================
PROJECT = "keyboard_passthrough"
OUT = PROJECT

# Card edge: 0.125" pitch, 44 positions (22 per side), double-sided
CE_PITCH = 3.175  # 0.125" in mm
CE_POS = 22  # positions per side
CE_PAD_W = 2.0  # finger width
CE_PAD_H = 6.0  # finger length along edge

# Pins actually used for keyboard matrix (29 of 44)
USED_PINS = [
    1,
    3,
    5,
    7,
    9,
    11,
    13,
    8,
    10,
    12,
    14,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    39,
    40,
    41,
    42,
    43,
    44,
]
USED_SET = set(USED_PINS)
SIGNAL_COUNT = len(USED_PINS)  # 29

# Board dimensions — width matches the 72mm tongue
BOARD_W = 72.0
BOARD_H = 55.0


def uid():
    return str(_uuid.uuid4())


# ============================================================
# Net management
# ============================================================
class Nets:
    def __init__(self):
        self._map = {"": 0}
        self._rmap = {0: ""}
        self._n = 1

    def add(self, name):
        if name not in self._map:
            self._map[name] = self._n
            self._rmap[self._n] = name
            self._n += 1
        return self._map[name]

    def id(self, name):
        return self._map.get(name, 0)

    def pcb_defs(self):
        lines = []
        for i in sorted(self._rmap):
            lines.append(f'  (net {i} "{self._rmap[i]}")')
        return "\n".join(lines)


nets = Nets()

# Signal nets: keyboard (male card edge) and computer (female card edge)
for ce_pin in USED_PINS:
    nets.add(f"KB_{ce_pin}")
    nets.add(f"COMP_{ce_pin}")


# ============================================================
# PCB generation helpers
# ============================================================
def thru_pad(num, x, y, net_name, drill=1.0, size=1.7, shape="circle"):
    nid = nets.id(net_name)
    return (
        f'    (pad "{num}" thru_hole {shape}\n'
        f"      (at {x:.3f} {y:.3f})\n"
        f"      (size {size} {size})\n"
        f"      (drill {drill})\n"
        f'      (layers "*.Cu" "*.Mask")\n'
        f'      (net {nid} "{net_name}")\n'
        f'      (uuid "{uid()}")\n'
        f"    )"
    )


def smd_pad(num, x, y, w, h, layer, net_name):
    nid = nets.id(net_name)
    if layer == "F":
        layers = '"F.Cu" "F.Mask"'
    else:
        layers = '"B.Cu" "B.Mask"'
    return (
        f'    (pad "{num}" smd rect\n'
        f"      (at {x:.3f} {y:.3f})\n"
        f"      (size {w:.3f} {h:.3f})\n"
        f"      (layers {layers})\n"
        f'      (net {nid} "{net_name}")\n'
        f'      (uuid "{uid()}")\n'
        f"    )"
    )


def fp_text(kind, text, x, y, layer="F.SilkS", size=1.0):
    return (
        f'    (property "{kind}" "{text}"\n'
        f"      (at {x:.3f} {y:.3f})\n"
        f'      (layer "{layer}")\n'
        f'      (uuid "{uid()}")\n'
        f"      (effects (font (size {size} {size}) (thickness 0.15)))\n"
        f"    )"
    )


def fp_rect(x1, y1, x2, y2, layer="F.SilkS", width=0.12):
    return (
        f"    (fp_rect\n"
        f"      (start {x1:.3f} {y1:.3f})\n"
        f"      (end {x2:.3f} {y2:.3f})\n"
        f"      (stroke (width {width}) (type solid))\n"
        f"      (fill none)\n"
        f'      (layer "{layer}")\n'
        f'      (uuid "{uid()}")\n'
        f"    )"
    )


def fp_line(x1, y1, x2, y2, layer="F.SilkS", width=0.12):
    return (
        f"    (fp_line\n"
        f"      (start {x1:.3f} {y1:.3f})\n"
        f"      (end {x2:.3f} {y2:.3f})\n"
        f"      (stroke (width {width}) (type solid))\n"
        f'      (layer "{layer}")\n'
        f'      (uuid "{uid()}")\n'
        f"    )"
    )


# ============================================================
# Footprint generators
# ============================================================


def card_edge_male_fp(x, y):
    """Male card edge fingers at bottom board edge (plugs into keyboard).

    44 physical positions. Only the 29 used pins get pads with nets.
    Unused positions have pads with no net (unconnected).

    Pin numbering: even pins (2,4,...,44) on front (F.Cu),
                   odd pins (1,3,...,43) on back (B.Cu).
    """
    pads = []
    total_w = (CE_POS - 1) * CE_PITCH
    start_x = -total_w / 2

    for pos in range(CE_POS):
        px = start_x + pos * CE_PITCH
        odd_pin = (CE_POS - 1 - pos) * 2 + 1  # back:  43,41,...,1 (right to left)
        even_pin = (CE_POS - 1 - pos) * 2 + 2  # front: 44,42,...,2 (right to left)

        odd_net = f"KB_{odd_pin}" if odd_pin in USED_SET else ""
        even_net = f"KB_{even_pin}" if even_pin in USED_SET else ""

        pads.append(
            smd_pad(even_pin, px, -CE_PAD_H / 2, CE_PAD_W, CE_PAD_H, "F", even_net)
        )
        pads.append(
            smd_pad(odd_pin, px, -CE_PAD_H / 2, CE_PAD_W, CE_PAD_H, "B", odd_net)
        )

    # Silkscreen pin labels for pins 1, 2, 43, 44
    labels = []
    LABEL_PINS = {1, 2, 43, 44}
    for pos in range(CE_POS):
        px = start_x + pos * CE_PITCH
        odd_pin = (CE_POS - 1 - pos) * 2 + 1
        even_pin = (CE_POS - 1 - pos) * 2 + 2
        if even_pin in LABEL_PINS:
            labels.append(fp_text(f"user_{even_pin}", str(even_pin), px, -CE_PAD_H - 2, "F.SilkS", size=0.6))
        if odd_pin in LABEL_PINS:
            labels.append(fp_text(f"user_{odd_pin}", str(odd_pin), px, -CE_PAD_H - 2, "B.SilkS", size=0.6))
    label_str = "\n".join(labels)

    pad_str = "\n".join(pads)
    return (
        f'  (footprint "custom:CardEdge_Male_44"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid()}")\n'
        f"    (at {x:.3f} {y:.3f})\n"
        f"{fp_text('Reference', 'Keyboard Matrix', 0, -10)}\n"
        f"{fp_text('Value', 'Card_Edge_Male_44', 0, -8, 'F.Fab')}\n"
        f"{fp_rect(-total_w / 2 - 2, -CE_PAD_H - 1, total_w / 2 + 2, 1, 'F.Fab')}\n"
        f"{pad_str}\n"
        f"{label_str}\n"
        f"  )"
    )


def card_edge_female_fp(x, y):
    """Female card edge pads at top edge (receives computer cable).

    SMD pads on both sides of the board at 0.125" pitch, 0.25" tall.
    Same side assignment as male card edge: even pins on front (F.Cu),
    odd pins on back (B.Cu). A socket with dual-side contacts solders
    onto these pads.
    """
    pads = []
    total_w = (CE_POS - 1) * CE_PITCH
    start_x = -total_w / 2
    fem_pad_h = 6.35  # 0.25"

    for pos in range(CE_POS):
        px = start_x + pos * CE_PITCH
        odd_pin = (CE_POS - 1 - pos) * 2 + 1  # back:  43,41,...,1 (right to left)
        even_pin = (CE_POS - 1 - pos) * 2 + 2  # front: 44,42,...,2 (right to left)

        odd_net = f"COMP_{odd_pin}" if odd_pin in USED_SET else ""
        even_net = f"COMP_{even_pin}" if even_pin in USED_SET else ""

        pads.append(
            smd_pad(even_pin, px, fem_pad_h / 2, CE_PAD_W, fem_pad_h, "F", even_net)
        )
        pads.append(
            smd_pad(odd_pin, px, fem_pad_h / 2, CE_PAD_W, fem_pad_h, "B", odd_net)
        )

    # Silkscreen pin labels for pins 1, 2, 43, 44
    labels = []
    LABEL_PINS = {1, 2, 43, 44}
    for pos in range(CE_POS):
        px = start_x + pos * CE_PITCH
        odd_pin = (CE_POS - 1 - pos) * 2 + 1
        even_pin = (CE_POS - 1 - pos) * 2 + 2
        if even_pin in LABEL_PINS:
            labels.append(fp_text(f"user_{even_pin}", str(even_pin), px, fem_pad_h + 2, "F.SilkS", size=0.6))
        if odd_pin in LABEL_PINS:
            labels.append(fp_text(f"user_{odd_pin}", str(odd_pin), px, fem_pad_h + 2, "B.SilkS", size=0.6))
    label_str = "\n".join(labels)

    pad_str = "\n".join(pads)
    return (
        f'  (footprint "custom:CardEdge_Female_44"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid()}")\n'
        f"    (at {x:.3f} {y:.3f})\n"
        f"{fp_text('Reference', 'SDDSMUX', 0, fem_pad_h + 4)}\n"
        f"{fp_text('Value', 'Card_Edge_Socket_44', 0, fem_pad_h + 6, 'F.Fab')}\n"
        f"{fp_rect(-total_w / 2 - 2, 0, total_w / 2 + 2, fem_pad_h + 1, 'F.Fab')}\n"
        f"{pad_str}\n"
        f"{label_str}\n"
        f"  )"
    )


def header_fp(ref, x, y, rows, cols, pin_nets, pitch=2.54, label="Header", angle=0):
    """Pin header footprint. pin_nets maps pin number (1-based) to net name.
    angle rotates the entire footprint (0 or 180)."""
    pads = []
    for c in range(cols):
        for r in range(rows):
            pin_num = c * rows + r + 1  # zigzag: column-first
            px = (c - (cols - 1) / 2) * pitch
            py = (r - (rows - 1) / 2) * pitch
            net_name = pin_nets.get(pin_num, "")
            pad_shape = "rect" if pin_num == 1 else "circle"
            pads.append(thru_pad(pin_num, px, py, net_name, shape=pad_shape))

    pad_str = "\n".join(pads)
    hw = (cols - 1) / 2 * pitch + pitch / 2 + 0.5
    hh = (rows - 1) / 2 * pitch + pitch / 2 + 0.5

    # Pin 1 marker: small circle just outside the footprint outline
    p1_x = -hw - 1.0
    p1_y = -(rows - 1) / 2 * pitch
    pin1_marker = (
        f"    (fp_circle\n"
        f"      (center {p1_x:.3f} {p1_y:.3f})\n"
        f"      (end {p1_x + 0.3:.3f} {p1_y:.3f})\n"
        f"      (stroke (width 0.12) (type solid))\n"
        f"      (fill solid)\n"
        f'      (layer "F.SilkS")\n'
        f'      (uuid "{uid()}")\n'
        f"    )"
    )

    at_str = f"    (at {x:.3f} {y:.3f})" if angle == 0 else f"    (at {x:.3f} {y:.3f} {angle})"

    return (
        f'  (footprint "custom:PinHeader_{rows}x{cols}"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid()}")\n'
        f"{at_str}\n"
        f"{fp_text('Reference', ref, 0, -hh - 1, size=0.8)}\n"
        f"{fp_text('Value', label, 0, hh + 1, 'F.Fab', size=0.8)}\n"
        f"{fp_rect(-hw, -hh, hw, hh, 'F.Fab')}\n"
        f"{fp_rect(-hw, -hh, hw, hh, 'F.SilkS')}\n"
        f"{pin1_marker}\n"
        f"{pad_str}\n"
        f"  )"
    )


# ============================================================
# Board outline
# ============================================================
def board_outline():
    """Board outline — simple rectangle with chamfered bottom corners for
    card edge insertion. The full board width matches the tongue width.
    """
    lines = []
    chamfer = 1.0  # 45-degree chamfer on bottom corners

    corners = [
        (0, 0),                          # top-left
        (BOARD_W, 0),                    # top-right
        (BOARD_W, BOARD_H - chamfer),    # right side down
        (BOARD_W - chamfer, BOARD_H),    # chamfer bottom-right
        (chamfer, BOARD_H),              # bottom edge
        (0, BOARD_H - chamfer),          # chamfer bottom-left
    ]

    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        lines.append(
            f"  (gr_line\n"
            f"    (start {x1:.3f} {y1:.3f})\n"
            f"    (end {x2:.3f} {y2:.3f})\n"
            f"    (stroke (width 0.1) (type solid))\n"
            f'    (layer "Edge.Cuts")\n'
            f'    (uuid "{uid()}")\n'
            f"  )"
        )
    return "\n".join(lines)


def edge_keepout(inset=3.0):
    """Generate trace keepout zones as four rectangular strips along each
    board edge. This prevents Freerouting from placing traces near the
    board edges.
    """
    zones = []

    # Four edge strips: top, bottom, left, right
    strips = [
        ("top", [(0, 0), (BOARD_W, 0), (BOARD_W, inset), (0, inset)]),
        ("bottom", [(0, BOARD_H - inset), (BOARD_W, BOARD_H - inset), (BOARD_W, BOARD_H), (0, BOARD_H)]),
        ("left", [(0, 0), (inset, 0), (inset, BOARD_H), (0, BOARD_H)]),
        ("right", [(BOARD_W - inset, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (BOARD_W - inset, BOARD_H)]),
    ]

    def pts_str(pts):
        return " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in pts)

    for name, poly in strips:
        for layer in ["F.Cu", "B.Cu"]:
            layer_suffix = "F" if layer == "F.Cu" else "B"
            zones.append(
                f"  (zone\n"
                f"    (net 0)\n"
                f'    (net_name "")\n'
                f'    (layer "{layer}")\n'
                f'    (uuid "{uid()}")\n'
                f'    (name "keepout_{name}_{layer_suffix}")\n'
                f"    (hatch edge 0.5)\n"
                f"    (connect_pads (clearance 0))\n"
                f"    (min_thickness 0.25)\n"
                f"    (keepout\n"
                f"      (tracks not_allowed)\n"
                f"      (vias not_allowed)\n"
                f"      (pads allowed)\n"
                f"      (copperpour not_allowed)\n"
                f"      (footprints allowed)\n"
                f"    )\n"
                f"    (fill (thermal_gap 0.5) (thermal_bridge_width 0.5))\n"
                f"    (polygon\n"
                f"      (pts {pts_str(poly)})\n"
                f"    )\n"
                f"  )"
            )

    return "\n".join(zones)


# ============================================================
# Generate PCB file
# ============================================================
def generate_pcb():
    footprints = []

    ce_center_x = BOARD_W / 2

    # Male card edge at bottom edge (y = BOARD_H)
    footprints.append(card_edge_male_fp(ce_center_x, BOARD_H - 1))

    # Female card edge socket at top edge
    footprints.append(card_edge_female_fp(ce_center_x, 4.0))

    # Two 2x15 headers in the middle of the board
    # 29 used pins + 1 unused = 30 positions per header (2x15)
    # Sort used pins for a logical header layout
    sorted_pins = sorted(USED_PINS)

    # KB Header (J3): keyboard signals from male card edge
    kb_nets = {}
    for i, ce_pin in enumerate(sorted_pins):
        pad_num = i + 1  # 1-based pad number
        # 2x15 layout: odd pads in left column, even pads in right column
        kb_nets[pad_num] = f"KB_{ce_pin}"
    # Pad 30 is unused (filler to complete 2x15)

    # COMP Header (J4): computer signals from female card edge
    comp_nets = {}
    for i, ce_pin in enumerate(sorted_pins):
        pad_num = i + 1
        comp_nets[pad_num] = f"COMP_{ce_pin}"
    # Pad 30 is unused (filler to complete 2x15)

    # Place headers horizontally (2 rows x 15 cols), stacked vertically
    header_x = ce_center_x
    header_spacing_y = 12.0  # vertical gap between the two headers
    mid_y = BOARD_H / 2 - 1  # vertical center of usable area

    footprints.append(
        header_fp("J3", header_x, mid_y + header_spacing_y / 2,
                  2, 15, kb_nets, label="KB_Header", angle=180)
    )
    footprints.append(
        header_fp("J4", header_x, mid_y - header_spacing_y / 2,
                  2, 15, comp_nets, label="COMP_Header", angle=180)
    )

    fp_str = "\n".join(footprints)
    outline = board_outline()
    keepout = edge_keepout(1.5)

    pcb = f"""\
(kicad_pcb
  (version 20240108)
  (generator "keyboard_passthrough_gen")
  (generator_version "1.0")
  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )
  (setup
    (pad_to_mask_clearance 0)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions no)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (svgprecision 4)
      (excludeedgelayer yes)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (pdf_front_fp_property_popups yes)
      (pdf_back_fp_property_popups yes)
      (dxfpolygonmode yes)
      (dxfimperialunits yes)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotfptext yes)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk no)
      (outputformat 1)
      (mirror no)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "")
    )
  )

{nets.pcb_defs()}

{outline}

{keepout}

{fp_str}

)
"""
    return pcb


# ============================================================
# Generate schematic file
# ============================================================
def generate_schematic():
    """Generate a KiCad schematic with global labels for connectivity."""

    lib_syms = []

    # Generic connector symbol
    def conn_symbol(name, ref_prefix, pins, fp_name):
        pin_defs = []
        body_h = max(pins * 2.54, 5.08)
        for i in range(pins):
            py = body_h / 2 - 1.27 - i * 2.54
            pin_defs.append(
                f"        (pin passive line (at -7.62 {py:.2f} 0) (length 2.54)\n"
                f'          (name "Pin_{i + 1}" (effects (font (size 1.27 1.27))))\n'
                f'          (number "{i + 1}" (effects (font (size 1.27 1.27))))\n'
                f"        )"
            )
        pin_str = "\n".join(pin_defs)
        return f'''\
    (symbol "custom:{name}"
      (pin_names (offset 1.016))
      (in_bom yes)
      (on_board yes)
      (property "Reference" "{ref_prefix}"
        (at 0 {body_h / 2 + 2:.2f} 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "{name}"
        (at 0 {-body_h / 2 - 2:.2f} 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "custom:{fp_name}"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" ""
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "{name}_0_1"
        (rectangle
          (start -5.08 {body_h / 2:.2f})
          (end 5.08 {-body_h / 2:.2f})
          (stroke (width 0) (type default))
          (fill (type background))
        )
      )
      (symbol "{name}_1_1"
{pin_str}
      )
    )'''

    lib_syms.append(conn_symbol("Conn_CE_44", "J", 44, "CardEdge_Female_44"))
    lib_syms.append(conn_symbol("Conn_CE_44_Male", "J", 44, "CardEdge_Male_44"))
    lib_syms.append(conn_symbol("Conn_2x15", "J", 30, "PinHeader_15x2"))

    lib_symbols_str = "\n".join(lib_syms)

    instances = []
    wires = []
    labels = []

    root_uuid = uid()

    def place_symbol(lib_id, ref, value, x, y, pin_labels):
        pin_lines = []
        for pnum in pin_labels:
            pin_lines.append(f'    (pin "{pnum}" (uuid "{uid()}"))')
        pin_str = "\n".join(pin_lines)

        inst = f'''\
  (symbol
    (lib_id "custom:{lib_id}")
    (at {x:.2f} {y:.2f} 0)
    (unit 1)
    (exclude_from_sim no)
    (in_bom yes)
    (on_board yes)
    (dnp no)
    (uuid "{uid()}")
    (property "Reference" "{ref}"
      (at {x:.2f} {y - 2:.2f} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{value}"
      (at {x:.2f} {y + 2:.2f} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" ""
      (at {x:.2f} {y:.2f} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" ""
      (at {x:.2f} {y:.2f} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
{pin_str}
    (instances
      (project "{PROJECT}"
        (path "/{root_uuid}"
          (reference "{ref}")
          (unit 1)
        )
      )
    )
  )'''
        instances.append(inst)

        for pnum, (net_name, px_off, py_off) in pin_labels.items():
            if not net_name:
                continue
            lx = x + px_off
            ly = y + py_off
            wire_ext = 5.08
            if px_off < 0:
                wlx = lx - wire_ext
                angle = 0
            else:
                wlx = lx + wire_ext
                angle = 180

            wires.append(
                f"  (wire (pts (xy {lx:.2f} {ly:.2f}) (xy {wlx:.2f} {ly:.2f}))\n"
                f"    (stroke (width 0) (type default))\n"
                f'    (uuid "{uid()}")\n'
                f"  )"
            )
            labels.append(
                f'  (global_label "{net_name}"\n'
                f"    (shape passive)\n"
                f"    (at {wlx:.2f} {ly:.2f} {angle})\n"
                f"    (effects (font (size 1.0 1.0)))\n"
                f'    (uuid "{uid()}")\n'
                f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n'
                f"      (at 0 0 0)\n"
                f"      (effects (font (size 1.27 1.27)) hide)\n"
                f"    )\n"
                f"  )"
            )

    # Place card edge connectors in schematic
    sorted_pins = sorted(USED_PINS)

    # KB Header (J3)
    kb_pin_labels = {}
    for i, ce_pin in enumerate(sorted_pins):
        pad_num = i + 1
        body_h = max(30 * 2.54, 5.08)
        py = body_h / 2 - 1.27 - (pad_num - 1) * 2.54
        kb_pin_labels[str(pad_num)] = (f"KB_{ce_pin}", -7.62, py)

    place_symbol("Conn_2x15", "J3", "KB_Header", 60, 100, kb_pin_labels)

    # COMP Header (J4)
    comp_pin_labels = {}
    for i, ce_pin in enumerate(sorted_pins):
        pad_num = i + 1
        body_h = max(30 * 2.54, 5.08)
        py = body_h / 2 - 1.27 - (pad_num - 1) * 2.54
        comp_pin_labels[str(pad_num)] = (f"COMP_{ce_pin}", -7.62, py)

    place_symbol("Conn_2x15", "J4", "COMP_Header", 160, 100, comp_pin_labels)

    inst_str = "\n".join(instances)
    wire_str = "\n".join(wires)
    label_str = "\n".join(labels)

    sch = f"""\
(kicad_sch
  (version 20231120)
  (generator "keyboard_passthrough_gen")
  (generator_version "1.0")
  (uuid "{root_uuid}")
  (paper "A2")

  (lib_symbols
{lib_symbols_str}
  )

{inst_str}

{wire_str}

{label_str}

)
"""
    return sch


# ============================================================
# Generate project file
# ============================================================
def generate_project():
    proj = {
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
        "board": {
            "design_settings": {
                "rules": {
                    "min_copper_edge_clearance": 2.0,
                },
            },
        },
        "schematic": {
            "drawing": {},
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "page_layout_descr_file": "",
        },
        "boards": [],
        "text_variables": {},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "net_settings": {
            "classes": [
                {
                    "bus_width": 12,
                    "clearance": 0.2,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Default",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.25,
                    "via_diameter": 0.6,
                    "via_drill": 0.3,
                    "wire_width": 6,
                },
            ],
            "meta": {"version": 3},
            "net_colors": None,
        },
    }
    return json.dumps(proj, indent=2)


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(OUT, f"{PROJECT}.kicad_pro"), "w") as f:
        f.write(generate_project())
    print(f"  Written: {PROJECT}.kicad_pro")

    with open(os.path.join(OUT, f"{PROJECT}.kicad_sch"), "w") as f:
        f.write(generate_schematic())
    print(f"  Written: {PROJECT}.kicad_sch")

    with open(os.path.join(OUT, f"{PROJECT}.kicad_pcb"), "w") as f:
        f.write(generate_pcb())
    print(f"  Written: {PROJECT}.kicad_pcb")

    print(f"\nProject generated in {OUT}/")

    sorted_pins = sorted(USED_PINS)
    print(f"\nHeader pin mapping (sorted by card edge pin number):")
    print(f"  {'Pad':>4s}  {'CE Pin':>6s}  {'KB Net':>10s}  {'COMP Net':>10s}")
    for i, ce_pin in enumerate(sorted_pins):
        pad = i + 1
        print(f"  {pad:4d}  {ce_pin:6d}  {'KB_' + str(ce_pin):>10s}  {'COMP_' + str(ce_pin):>10s}")

    if len(sorted_pins) < 30:
        print(f"\n  Pad 30: unused (filler for 2x15 layout)")

    print(
        f"\nUnused card edge positions (no connection): "
        f"{sorted(set(range(1, 45)) - USED_SET)}"
    )
    print(f"\nNOTES:")
    print(f"  - Board is {BOARD_W}x{BOARD_H}mm.")
    print(f"  - No trace routing included - route in KiCad.")
    print(f"  - J3 = KB Header (keyboard/male card edge signals)")
    print(f"  - J4 = COMP Header (computer/female card edge signals)")


if __name__ == "__main__":
    main()
