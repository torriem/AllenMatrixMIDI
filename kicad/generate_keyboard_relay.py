#!/usr/bin/env python3
"""
Generate KiCad 8 project for keyboard matrix relay switching board.

Switches 29 keyboard matrix lines (from an 11x18 matrix) between a
built-in computer and an external Teensy 4.1 using 16 DPDT relays.

Board features:
- Female 0.125" pitch 44-position card edge socket (keyboard input) on top edge
- Male 0.125" pitch 44-position card edge fingers (computer output) on bottom edge
- 16 DPDT signal relays (12V DC coil) with flyback diodes
- 2x24 pin header for Teensy 4.1 connection (J3 left, J4 right)
- 2-pin screw terminal for 12V DC relay power
- Toggle switch controls all relays simultaneously

Default state (relays unpowered): keyboard -> computer (NC contacts)
Switched state (12V applied): keyboard -> Teensy (NO contacts)

Only the 29 used card edge pins are connected. The 15 unused pins
have no pads/connections on either card edge connector.

Usage: python3 generate_keyboard_switch.py
Output: keyboard_relay/ directory with KiCad 8 project files
"""

import json
import os
import uuid as _uuid

# ============================================================
# Configuration
# ============================================================
PROJECT = "keyboard_relay"
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

# Card edge pin -> Teensy 4.1 pin mapping
CE_TO_TEENSY = {
    11: 20,
    13: 21,
    9: 22,
    5: 23,
    7: 24,
    3: 25,
    1: 26,
    8: 27,
    10: 28,
    12: 29,
    14: 30,
    22: 2,
    23: 3,
    26: 4,
    25: 5,
    24: 6,
    21: 7,
    28: 8,
    29: 9,
    32: 10,
    31: 11,
    30: 12,
    27: 13,
    40: 14,
    41: 15,
    44: 16,
    43: 17,
    42: 18,
    39: 19,
}

# Teensy pins used, sorted for header layout
TEENSY_PINS = sorted(CE_TO_TEENSY.values())  # [2,3,4,...,30]

# Board dimensions
BOARD_W = 155.0
BOARD_H = 90.0

# Relay config (HK19F-12V)
RELAY_COUNT = 16
RELAY_ROW_SPACING = 7.62   # 0.3" between the two rows
RELAY_COIL_GAP = 7.62      # 0.3" from coil pin to first signal pin
RELAY_SIG_PITCH = 5.08     # 0.2" between signal pins


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

# Signal nets: keyboard (male card edge)->relay COM, relay NC->computer (female card edge)
for ce_pin in USED_PINS:
    nets.add(f"KB_{ce_pin}")
    nets.add(f"COMP_{ce_pin}")

# Teensy nets: relay NO->Teensy pin
for ce_pin in USED_PINS:
    teensy_pin = CE_TO_TEENSY[ce_pin]
    nets.add(f"TEEN_{teensy_pin}")

# Power nets
nets.add("COIL_12V")      # unswitched 12V from screw terminal
nets.add("COIL_12V_SW")   # switched 12V after external switch jumper
nets.add("COIL_GND")

# Spare relay channels (32 channels - 29 used = 3 spare)
SPARE_COUNT = RELAY_COUNT * 2 - SIGNAL_COUNT
for i in range(1, SPARE_COUNT + 1):
    nets.add(f"SPARE_{i}")


# ============================================================
# Relay channel -> signal mapping
# ============================================================
def relay_pin_nets(relay_idx):
    """Return dict of pin_number -> net_name for relay relay_idx (0-based)."""
    ch1 = relay_idx * 2  # 0-based channel index
    ch2 = relay_idx * 2 + 1

    pn = {1: "COIL_12V_SW", 8: "COIL_GND"}

    # Channel 1: pins 2=COM1, 3=NC1, 4=NO1
    if ch1 < SIGNAL_COUNT:
        ce_pin = USED_PINS[ch1]
        teensy_pin = CE_TO_TEENSY[ce_pin]
        pn[2] = f"KB_{ce_pin}"
        pn[3] = f"COMP_{ce_pin}"
        pn[4] = f"TEEN_{teensy_pin}"
    else:
        # Unused channel — leave pins unconnected
        pn[2] = ""
        pn[3] = ""
        pn[4] = ""

    # Channel 2: pins 7=COM2, 6=NC2, 5=NO2
    if ch2 < SIGNAL_COUNT:
        ce_pin = USED_PINS[ch2]
        teensy_pin = CE_TO_TEENSY[ce_pin]
        pn[7] = f"KB_{ce_pin}"
        pn[6] = f"COMP_{ce_pin}"
        pn[5] = f"TEEN_{teensy_pin}"
    else:
        # Unused channel — leave pins unconnected
        pn[7] = ""
        pn[6] = ""
        pn[5] = ""

    return pn


# ============================================================
# PCB generation helpers
# ============================================================
def thru_pad(num, x, y, net_name, drill=1.0, size=1.7):
    nid = nets.id(net_name)
    return (
        f'    (pad "{num}" thru_hole circle\n'
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
    """Male card edge fingers at bottom board edge (plugs into computer).

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
    """Female card edge pads at top edge (receives keyboard cable).

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


def relay_fp(ref, x, y, pin_nets):
    """HK19F-12V DPDT relay footprint.

    Pin mapping:
      1=Coil+, 8=Coil-
      2=COM1, 3=NC1, 4=NO1
      7=COM2, 6=NC2, 5=NO2

    HK19F pin spacing (centered vertically):
      0.3" between rows, 0.3" coil-to-signal gap, 0.2" between signal pins.
      Total height: 0.3" + 0.2" + 0.2" = 0.7" (17.78mm)
    """
    # Y positions centered: total span = COIL_GAP + 2*SIG_PITCH = 17.78mm
    total_h = RELAY_COIL_GAP + 2 * RELAY_SIG_PITCH
    y_top = -total_h / 2  # pin 1 / pin 8 y position

    pin_pos = {
        1: (-RELAY_ROW_SPACING / 2, y_top),
        2: (-RELAY_ROW_SPACING / 2, y_top + RELAY_COIL_GAP),
        3: (-RELAY_ROW_SPACING / 2, y_top + RELAY_COIL_GAP + RELAY_SIG_PITCH),
        4: (-RELAY_ROW_SPACING / 2, y_top + RELAY_COIL_GAP + 2 * RELAY_SIG_PITCH),
        5: (RELAY_ROW_SPACING / 2, y_top + RELAY_COIL_GAP + 2 * RELAY_SIG_PITCH),
        6: (RELAY_ROW_SPACING / 2, y_top + RELAY_COIL_GAP + RELAY_SIG_PITCH),
        7: (RELAY_ROW_SPACING / 2, y_top + RELAY_COIL_GAP),
        8: (RELAY_ROW_SPACING / 2, y_top),
    }

    pads = []
    for pnum, (px, py) in pin_pos.items():
        net_name = pin_nets.get(pnum, "")
        pads.append(thru_pad(pnum, px, py, net_name))

    pad_str = "\n".join(pads)
    body_w = RELAY_ROW_SPACING / 2 + 2.0
    body_h = total_h / 2 + 1.5

    return (
        f'  (footprint "custom:Relay_HK19F_DIP8"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid()}")\n'
        f"    (at {x:.3f} {y:.3f})\n"
        f"{fp_text('Reference', ref, 0, -body_h - 0.5, size=0.8)}\n"
        f"{fp_text('Value', 'HK19F-12V', 0, body_h + 0.5, 'F.Fab', size=0.8)}\n"
        f"{fp_rect(-body_w, -body_h, body_w, body_h, 'F.Fab')}\n"
        f"{fp_rect(-body_w, -body_h, body_w, body_h, 'F.SilkS')}\n"
        f"    (fp_circle\n"
        f"      (center {-body_w + 1:.3f} {-body_h + 1:.3f})\n"
        f"      (end {-body_w + 1.3:.3f} {-body_h + 1:.3f})\n"
        f"      (stroke (width 0.12) (type solid))\n"
        f"      (fill none)\n"
        f'      (layer "F.SilkS")\n'
        f'      (uuid "{uid()}")\n'
        f"    )\n"
        f"{pad_str}\n"
        f"  )"
    )


def diode_fp(ref, x, y, cathode_net, anode_net):
    """1N4148 diode, DO-35 horizontal, 7.62mm pad spacing."""
    spacing = 7.62 / 2
    pads = [
        thru_pad("K", -spacing, 0, cathode_net, drill=0.8, size=1.4),
        thru_pad("A", spacing, 0, anode_net, drill=0.8, size=1.4),
    ]
    pad_str = "\n".join(pads)
    return (
        f'  (footprint "custom:D_DO35_Horizontal"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid()}")\n'
        f"    (at {x:.3f} {y:.3f})\n"
        f"{fp_text('Reference', ref, 0, -2.5, size=0.7)}\n"
        f"{fp_text('Value', '1N4148', 0, 2.5, 'F.Fab', size=0.7)}\n"
        f"{fp_line(-spacing + 1, -1, spacing - 1, -1)}\n"
        f"{fp_line(-spacing + 1, 1, spacing - 1, 1)}\n"
        f"{fp_line(-spacing + 1, -1, -spacing + 1, 1)}\n"
        f"{fp_line(spacing - 1, -1, spacing - 1, 1)}\n"
        f"{fp_line(-spacing + 1.5, -1, -spacing + 1.5, 1)}\n"
        f"{pad_str}\n"
        f"  )"
    )


def header_fp(ref, x, y, rows, cols, pin_nets, pitch=2.54):
    """Pin header footprint. pin_nets maps pin number (1-based) to net name.
    Silkscreen labels show Teensy pin numbers next to each pad."""
    pads = []
    silk_labels = []
    for r in range(rows):
        for c in range(cols):
            pin_num = r * cols + c + 1
            px = (c - (cols - 1) / 2) * pitch
            py = (r - (rows - 1) / 2) * pitch
            net_name = pin_nets.get(pin_num, "")
            pads.append(thru_pad(pin_num, px, py, net_name))

    pad_str = "\n".join(pads)
    hw = (cols - 1) / 2 * pitch + pitch / 2 + 0.5
    hh = (rows - 1) / 2 * pitch + pitch / 2 + 0.5

    return (
        f'  (footprint "custom:PinHeader_{rows}x{cols}"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid()}")\n'
        f"    (at {x:.3f} {y:.3f})\n"
        f"{fp_text('Reference', ref, 0, -hh - 1, size=0.8)}\n"
        f"{fp_text('Value', f'Teensy_Header_{rows}x{cols}', 0, hh + 1, 'F.Fab', size=0.8)}\n"
        f"{fp_rect(-hw, -hh, hw, hh, 'F.Fab')}\n"
        f"{fp_rect(-hw, -hh, hw, hh, 'F.SilkS')}\n"
        f"{pad_str}\n"
        f"  )"
    )


def screw_terminal_fp(ref, x, y, net1, net2, pitch=5.08, label1=None, label2=None):
    """2-pin screw terminal block with optional per-pin silkscreen labels."""
    pads = [
        thru_pad(1, -pitch / 2, 0, net1, drill=1.2, size=2.4),
        thru_pad(2, pitch / 2, 0, net2, drill=1.2, size=2.4),
    ]
    pad_str = "\n".join(pads)
    pin_labels = ""
    if label1:
        pin_labels += f"\n{fp_text('user_pin1', label1, -pitch / 2, 4, 'F.SilkS', size=0.6)}"
    if label2:
        pin_labels += f"\n{fp_text('user_pin2', label2, pitch / 2, 4, 'F.SilkS', size=0.6)}"
    return (
        f'  (footprint "custom:ScrewTerminal_2P"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid()}")\n'
        f"    (at {x:.3f} {y:.3f})\n"
        f"{fp_text('Reference', ref, 0, -5)}\n"
        f"{fp_text('Value', '12V_Input', 0, 5, 'F.Fab')}\n"
        f"{fp_rect(-pitch / 2 - 2.5, -3.5, pitch / 2 + 2.5, 3.5, 'F.Fab')}\n"
        f"{fp_rect(-pitch / 2 - 2.5, -3.5, pitch / 2 + 2.5, 3.5, 'F.SilkS')}\n"
        f"{pad_str}{pin_labels}\n"
        f"  )"
    )


# ============================================================
# Board outline
# ============================================================
def board_outline():
    """Board outline with a protruding tab at the bottom for the male card edge.

    The tab is narrower than the main board, centered, and extends down
    for the card edge finger length. Small chamfers on the tab's leading
    corners aid insertion into the mating connector.
    """
    lines = []

    # Tab dimensions
    total_finger_w = (CE_POS - 1) * CE_PITCH  # 66.675mm
    tab_w = 72.0  # fixed width to match keyboard connector slot
    tab_h = CE_PAD_H + 2.0  # tab extends 2mm beyond the finger pads
    chamfer = 1.0  # 45-degree chamfer on leading corners

    center_x = BOARD_W / 2
    tab_left = center_x - tab_w / 2
    tab_right = center_x + tab_w / 2
    step_y = BOARD_H - tab_h  # where main board meets tab

    # Outline corners, clockwise from top-left
    corners = [
        (0, 0),                                    # top-left
        (BOARD_W, 0),                              # top-right
        (BOARD_W, step_y),                         # right side down to step
        (tab_right, step_y),                       # step inward right
        (tab_right, BOARD_H - chamfer),            # tab right side down
        (tab_right - chamfer, BOARD_H),            # chamfer bottom-right
        (tab_left + chamfer, BOARD_H),             # bottom edge to chamfer
        (tab_left, BOARD_H - chamfer),             # chamfer bottom-left
        (tab_left, step_y),                        # tab left side up
        (0, step_y),                               # step outward left
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


# ============================================================
# Generate PCB file
# ============================================================
def generate_pcb():
    footprints = []

    ce_center_x = BOARD_W / 2

    # Male card edge at bottom edge (y = BOARD_H)
    footprints.append(card_edge_male_fp(ce_center_x, BOARD_H - 1))

    # Female card edge socket at top edge (y ~ 8mm from top)
    footprints.append(card_edge_female_fp(ce_center_x, 4.0))

    # 16 DPDT relays in 2 rows of 8
    relay_x_start = 12.0
    relay_x_spacing = 14.0
    relay_row1_y = 35.0
    relay_row2_y = 58.0

    # Sort relays by the average card edge position of their signals.
    # Card edge pin p is at position: CE_POS - 1 - (p - 1) // 2
    # where position 0 is leftmost (pins 43/44) and 21 is rightmost (pins 1/2).
    def relay_avg_ce_pos(relay_idx):
        """Average card edge x-position for a relay's signals (lower = more left)."""
        ch1 = relay_idx * 2
        ch2 = relay_idx * 2 + 1
        positions = []
        for ch in [ch1, ch2]:
            if ch < SIGNAL_COUNT:
                p = USED_PINS[ch]
                positions.append(CE_POS - 1 - (p - 1) // 2)
        if not positions:
            return 999  # spare relay, put at far right
        return sum(positions) / len(positions)

    # Build list of (relay_index, avg_position), sort left to right
    relay_order = sorted(range(RELAY_COUNT), key=relay_avg_ce_pos)

    # Place sorted relays: first 8 in row 1, next 8 in row 2
    for slot, ri in enumerate(relay_order[:8]):
        rx = relay_x_start + slot * relay_x_spacing
        pn = relay_pin_nets(ri)
        footprints.append(relay_fp(f"K{ri + 1}", rx, relay_row1_y, pn))

    for slot, ri in enumerate(relay_order[8:]):
        rx = relay_x_start + slot * relay_x_spacing
        pn = relay_pin_nets(ri)
        footprints.append(relay_fp(f"K{ri + 1}", rx, relay_row2_y, pn))

    # Single flyback diode across coil power (all relays driven in parallel)
    # Placed above the top row of relays, near the screw terminal
    power_y = relay_row1_y - 15.0
    footprints.append(
        diode_fp("D1", 8.0, power_y, "COIL_12V_SW", "COIL_GND")
    )

    # Teensy 4.1 socket: two 1x24 female headers
    # USB port toward bottom of PCB, component side up
    # 0.6" (15.24mm) center-to-center spacing between left and right headers
    # Left header (J3) top->bottom: 33,34,35,36,37,38,39,40,41,GND,13,14,15,16,17,18,19,20,21,22,23,3.3V,GND,Vin
    # Right header (J4) top->bottom: 32,31,30,29,28,27,26,25,24,3.3V,12,11,10,9,8,7,6,5,4,3,2,1,0,GND
    # None = power/ground pin (no signal net)
    LEFT_PINS = [33, 34, 35, 36, 37, 38, 39, 40, 41, None, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, None, None, None]
    RIGHT_PINS = [32, 31, 30, 29, 28, 27, 26, 25, 24, None, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, None]

    # Build set of Teensy pins that have nets
    teensy_pin_to_net = {}
    for ce_pin in USED_PINS:
        tp = CE_TO_TEENSY[ce_pin]
        teensy_pin_to_net[tp] = f"TEEN_{tp}"

    teen_nets_left = {}
    for pad_num, tp in enumerate(LEFT_PINS, start=1):
        if tp is not None and tp in teensy_pin_to_net:
            teen_nets_left[pad_num] = teensy_pin_to_net[tp]

    teen_nets_right = {}
    for pad_num, tp in enumerate(RIGHT_PINS, start=1):
        if tp is not None and tp in teensy_pin_to_net:
            teen_nets_right[pad_num] = teensy_pin_to_net[tp]

    teensy_x = BOARD_W - 20
    teensy_y = BOARD_H / 2
    row_spacing = 15.24  # 0.6"
    footprints.append(
        header_fp("J3", teensy_x - row_spacing / 2, teensy_y, 24, 1, teen_nets_left)
    )
    footprints.append(
        header_fp("J4", teensy_x + row_spacing / 2, teensy_y, 24, 1, teen_nets_right)
    )

    # 12V screw terminal (left side)
    # 12V screw terminal above top row of relays
    # 12V screw terminal (+12V and GND)
    footprints.append(screw_terminal_fp("+12V", 8.0, power_y - 10.0, "COIL_12V", "COIL_GND", label1="+12V", label2="GND"))
    # Switch jumper: connects unswitched 12V to switched 12V via external switch
    footprints.append(screw_terminal_fp("Switch", 20.0, BOARD_H - 15.0, "COIL_12V", "COIL_12V_SW"))
    # Switched power output jumper (next to +12V input)
    footprints.append(screw_terminal_fp("12V_SW", 20.0, power_y - 10.0, "COIL_12V_SW", "COIL_GND", label1="+12V", label2="GND"))

    fp_str = "\n".join(footprints)
    outline = board_outline()

    pcb = f"""\
(kicad_pcb
  (version 20240108)
  (generator "keyboard_switch_gen")
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

    # DPDT Relay symbol
    lib_syms.append(f"""\
    (symbol "custom:Relay_DPDT"
      (pin_names (offset 1.016))
      (in_bom yes)
      (on_board yes)
      (property "Reference" "K"
        (at 0 10.16 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Relay_DPDT"
        (at 0 -10.16 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "custom:Relay_DPDT_DIP8"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" ""
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "Relay_DPDT_0_1"
        (rectangle
          (start -5.08 8.89)
          (end 5.08 -8.89)
          (stroke (width 0) (type default))
          (fill (type background))
        )
      )
      (symbol "Relay_DPDT_1_1"
        (pin passive line (at -7.62 6.35 0) (length 2.54)
          (name "Coil+" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at -7.62 3.81 0) (length 2.54)
          (name "COM1" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 7.62 3.81 180) (length 2.54)
          (name "NC1" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 7.62 1.27 180) (length 2.54)
          (name "NO1" (effects (font (size 1.27 1.27))))
          (number "4" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 7.62 -1.27 180) (length 2.54)
          (name "NO2" (effects (font (size 1.27 1.27))))
          (number "5" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 7.62 -3.81 180) (length 2.54)
          (name "NC2" (effects (font (size 1.27 1.27))))
          (number "6" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at -7.62 -3.81 0) (length 2.54)
          (name "COM2" (effects (font (size 1.27 1.27))))
          (number "7" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at -7.62 -6.35 0) (length 2.54)
          (name "Coil-" (effects (font (size 1.27 1.27))))
          (number "8" (effects (font (size 1.27 1.27))))
        )
      )
    )""")

    # 1N4148 diode symbol
    lib_syms.append(f"""\
    (symbol "custom:D_1N4148"
      (pin_names (offset 1.016))
      (in_bom yes)
      (on_board yes)
      (property "Reference" "D"
        (at 0 2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "1N4148"
        (at 0 -2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "custom:D_DO35_Horizontal"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" ""
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "D_1N4148_0_1"
        (polyline
          (pts (xy -1.27 1.27) (xy -1.27 -1.27))
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
        (polyline
          (pts (xy 1.27 0) (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0))
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
      )
      (symbol "D_1N4148_1_1"
        (pin passive line (at -3.81 0 0) (length 2.54)
          (name "A" (effects (font (size 1.27 1.27))))
          (number "A" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "K" (effects (font (size 1.27 1.27))))
          (number "K" (effects (font (size 1.27 1.27))))
        )
      )
    )""")

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
    lib_syms.append(conn_symbol("Conn_1x24_Left", "J", 24, "PinHeader_1x24_Left"))
    lib_syms.append(conn_symbol("Conn_1x24_Right", "J", 24, "PinHeader_1x24_Right"))
    lib_syms.append(conn_symbol("Conn_1x2", "J", 2, "ScrewTerminal_2P"))

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

    # Place 16 relays in 4 columns x 4 rows
    sch_relay_x_start = 80
    sch_relay_y_start = 40
    sch_relay_x_sp = 55
    sch_relay_y_sp = 30

    for i in range(RELAY_COUNT):
        col = i % 4
        row = i // 4
        sx = sch_relay_x_start + col * sch_relay_x_sp
        sy = sch_relay_y_start + row * sch_relay_y_sp
        pn = relay_pin_nets(i)

        pin_labels = {
            "1": (pn[1], -7.62, 6.35),
            "2": (pn[2], -7.62, 3.81),
            "3": (pn[3], 7.62, 3.81),
            "4": (pn[4], 7.62, 1.27),
            "5": (pn[5], 7.62, -1.27),
            "6": (pn[6], 7.62, -3.81),
            "7": (pn[7], -7.62, -3.81),
            "8": (pn[8], -7.62, -6.35),
        }
        place_symbol("Relay_DPDT", f"K{i + 1}", "DPDT_12V", sx, sy, pin_labels)

    # Place 16 diodes near their relays
    for i in range(RELAY_COUNT):
        col = i % 4
        row = i // 4
        sx = sch_relay_x_start + col * sch_relay_x_sp
        sy = sch_relay_y_start + row * sch_relay_y_sp + 15

        pin_labels = {
            "A": ("COIL_GND", -3.81, 0),
            "K": ("COIL_12V", 3.81, 0),
        }
        place_symbol("D_1N4148", f"D{i + 1}", "1N4148", sx, sy, pin_labels)

    # Place power connector
    place_symbol(
        "Conn_1x2",
        "J4",
        "12V_Input",
        30,
        60,
        {
            "1": ("COIL_12V", -7.62, 0),
            "2": ("COIL_GND", -7.62, -2.54),
        },
    )

    inst_str = "\n".join(instances)
    wire_str = "\n".join(wires)
    label_str = "\n".join(labels)

    sch = f"""\
(kicad_sch
  (version 20231120)
  (generator "keyboard_switch_gen")
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
                {
                    "bus_width": 12,
                    "clearance": 0.2,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Power",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.5,
                    "via_diameter": 0.8,
                    "via_drill": 0.4,
                    "wire_width": 6,
                },
            ],
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": {
                "COIL_12V": "Power",
                "COIL_12V_SW": "Power",
                "COIL_GND": "Power",
            },
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
    print(f"\nComplete signal path (card edge pin -> relay -> Teensy pin):")
    for i, ce_pin in enumerate(USED_PINS):
        relay_num = i // 2 + 1
        ch = "A" if i % 2 == 0 else "B"
        teensy_pin = CE_TO_TEENSY[ce_pin]
        print(
            f"  CE pin {ce_pin:2d} -> K{relay_num:2d} ch {ch} -> Teensy pin {teensy_pin:2d}"
        )

    LEFT_PINS = [33, 34, 35, 36, 37, 38, 39, 40, 41, None, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, None, None, None]
    RIGHT_PINS = [32, 31, 30, 29, 28, 27, 26, 25, 24, None, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, None]

    print(f"\nTeensy 4.1 socket pin layout (J3 left 1x24, J4 right 1x24, USB at bottom):")
    for pad_idx in range(24):
        lp = LEFT_PINS[pad_idx]
        rp = RIGHT_PINS[pad_idx]
        l_str = f"Teensy {lp:2d}" if lp is not None else "PWR/GND  "
        r_str = f"Teensy {rp:2d}" if rp is not None else "PWR/GND  "
        print(f"  J3 pad {pad_idx + 1:2d}: {l_str}    J4 pad {pad_idx + 1:2d}: {r_str}")

    print(
        f"\nUnused card edge positions (no connection): "
        f"{sorted(set(range(1, 45)) - USED_SET)}"
    )
    print(f"\nNOTES:")
    print(f"  - Relay footprint is generic DIP-8. Adjust for your specific relay.")
    print(f"  - Female card edge socket row spacing may need adjustment.")
    print(f"  - Board is {BOARD_W}x{BOARD_H}mm.")
    print(f"  - No trace routing included - route in KiCad.")


if __name__ == "__main__":
    main()
