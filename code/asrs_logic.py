"""
asrs_logic.py -- the FUNCTIONAL CORE of the ASRS Terminal Simulator.

This module contains ONLY pure functions and the Tray class.
"Pure" means: no input(), no print(), no time.sleep(), no hidden state.
Every function takes what it needs as arguments and returns a value.

Because nothing here talks to the user or the clock, every function can be
unit-tested in isolation (see test_asrs.py). The imperative shell (main.py)
owns all state and all I/O, and calls these functions to do the real work.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Constants (shared with main.py)
# ---------------------------------------------------------------------------
N = 4                # each rack is N x N (default 4 x 4)
MOVE_SEC = 1         # 1 simulated second per slot moved
TURN_SEC = 0         # turning between sides currently costs 0 seconds
TRAY_CAPACITY = 50   # a tray can hold at most 50 items

# Move tokens used by build_path / execute_path
OUT = "OUT"    # move toward the aisle (column decreases)
IN = "IN"      # move away from the aisle (column increases)
UP = "UP"      # move to a smaller row index
DOWN = "DOWN"  # move to a larger row index
TURN = "TURN"  # flip to the other side (at the aisle)


# ---------------------------------------------------------------------------
# Tray
# ---------------------------------------------------------------------------
class Tray:
    """A tray stored in a rack slot. Holds items of a single item id."""

    def __init__(self, tray_id: int, item_id: Optional[int], qty: int):
        self.tray_id = tray_id
        self.item_id = item_id   # None when the tray is empty (qty == 0)
        self.qty = qty

    def __repr__(self) -> str:
        return f"Tray(id={self.tray_id}, item={self.item_id}, qty={self.qty})"


# ---------------------------------------------------------------------------
# Input validation (pure predicates)
# ---------------------------------------------------------------------------
def is_valid_choice(choice_str: str, max_choice: int) -> bool:
    """True if choice_str is a whole number from 1 to max_choice."""
    try:
        value = int(choice_str)
    except (ValueError, TypeError):
        return False
    return 1 <= value <= max_choice


def is_valid_amount(amount_str: str) -> bool:
    """True if amount_str is a non-negative whole number."""
    try:
        value = int(amount_str)
    except (ValueError, TypeError):
        return False
    return value >= 0


# ---------------------------------------------------------------------------
# Quantity rules
# ---------------------------------------------------------------------------
def get_qty_after_increase(current_qty: int, amount: int, capacity: int) -> Optional[int]:
    """Return the new qty after adding, or None if it would exceed capacity."""
    new_qty = current_qty + amount
    if new_qty > capacity:
        return None
    return new_qty


def get_qty_after_reduce(current_qty: int, amount: int) -> Optional[int]:
    """Return the new qty after removing, or None if it would go below 0."""
    new_qty = current_qty - amount
    if new_qty < 0:
        return None
    return new_qty


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------
def distance(p_side: int, p_row: int, p_col: int,
             t_side: int, t_row: int, t_col: int,
             turn_sec: int) -> int:
    """
    Travel time (in seconds) between two slots.

      Same side : |r1-r2| + |c1-c2|             (Manhattan distance)
      Cross side: c1 + c2 + |r1-r2| + turn_sec  (out to aisle, turn, back out)
    """
    if p_side == t_side:
        return abs(p_row - t_row) + abs(p_col - t_col)
    return p_col + t_col + abs(p_row - t_row) + turn_sec


# ---------------------------------------------------------------------------
# Path building
# ---------------------------------------------------------------------------
def build_path(p_side: int, p_row: int, p_col: int,
               t_side: int, t_row: int, t_col: int,
               turn_sec: int) -> list:
    """
    Return the canonical list of move tokens from the robot position to the
    target slot.

    Order: cross the aisle if needed (OUT...OUT, TURN), then fix the column
    (IN/OUT), then fix the row (UP/DOWN).

    turn_sec affects TIMING (see distance / build_movement_header) but not the
    sequence of moves, so it is not used here.
    """
    steps = []
    side, row, col = p_side, p_row, p_col

    # 1) To change side: go out to the aisle (col 0), then TURN.
    if side != t_side:
        while col > 0:
            steps.append(OUT)
            col -= 1
        steps.append(TURN)
        side = t_side

    # 2) Fix the column.
    while col != t_col:
        if col < t_col:
            steps.append(IN)
            col += 1
        else:
            steps.append(OUT)
            col -= 1

    # 3) Fix the row.
    while row != t_row:
        if row < t_row:
            steps.append(DOWN)
            row += 1
        else:
            steps.append(UP)
            row -= 1

    return steps


# ---------------------------------------------------------------------------
# Nearest empty slot
# ---------------------------------------------------------------------------
def find_nearest_empty_slot(racks: list, p_side: int, p_row: int, p_col: int,
                            n: int) -> Optional[tuple]:
    """
    Find the empty, non-station slot closest to the robot.

    Scan order is Side 0 -> Side 1, then row ascending, then column ascending.
    We only replace the best when we find a STRICTLY smaller distance, so ties
    are automatically won by the earliest slot in scan order -- this is the
    required deterministic tie-break.

    Returns (side, row, col), or None if there is no empty slot.
    """
    best = None
    best_dist = None
    for side in (0, 1):
        for row in range(n):
            for col in range(n):
                if row == n - 1 and col == 0:      # station: never a target
                    continue
                if racks[side][row][col] is not None:
                    continue                        # occupied
                d = distance(p_side, p_row, p_col, side, row, col, TURN_SEC)
                if best is None or d < best_dist:   # strict < keeps ties in scan order
                    best = (side, row, col)
                    best_dist = d
    return best


# ---------------------------------------------------------------------------
# Counting helper
# ---------------------------------------------------------------------------
def count_empty_slots(racks: list, side: int, n: int) -> int:
    """Count empty, non-station storage cells on one side."""
    count = 0
    for row in range(n):
        for col in range(n):
            if row == n - 1 and col == 0:
                continue                       # the station is not a storage slot
            if racks[side][row][col] is None:
                count += 1
    return count


# ---------------------------------------------------------------------------
# View builders (return strings; they never print)
# ---------------------------------------------------------------------------
def _render_cell(racks: list, side: int, row: int, col: int, n: int) -> str:
    """Return the display text for one cell."""
    if row == n - 1 and col == 0:
        return "STATION"
    tray = racks[side][row][col]
    if tray is None:
        return "EMPTY"
    item = tray.item_id if tray.item_id is not None else "-"
    return f"T{tray.tray_id}:I{item}(q{tray.qty})"


def build_admin_view(racks: list, robot: dict, sim_clock: int, n: int) -> str:
    """Format the full warehouse map + counts + robot status as one string."""
    cell_w = 14
    lines = []
    lines.append("-" * 32)
    lines.append("WAREHOUSE MAP")
    lines.append("-" * 32)

    side_block = cell_w * n
    lines.append("SIDE 0".ljust(side_block) + "SIDE 1")

    for row in range(n):
        left = "".join(_render_cell(racks, 0, row, c, n).ljust(cell_w) for c in range(n))
        right = "".join(_render_cell(racks, 1, row, c, n).ljust(cell_w) for c in range(n))
        lines.append(left + right)

    lines.append("-" * 32)

    empty0 = count_empty_slots(racks, 0, n)
    empty1 = count_empty_slots(racks, 1, n)
    total = empty0 + empty1
    lines.append(
        f"Empty slots -> Side0: {empty0}/{n * n}, "
        f"Side1: {empty1}/{n * n} (total {total}/{2 * n * n})"
    )

    pos = f"Side {robot['side']} ({robot['row']},{robot['col']})"
    if robot["row"] == n - 1 and robot["col"] == 0:
        pos += " AT STATION"
    carrying = f"tray {robot['carrying'].tray_id}" if robot["carrying"] else "none"
    lines.append(f"Robot: {pos} | carrying: {carrying}")
    lines.append(f"Sim time: {sim_clock} sec")
    lines.append("-" * 32)
    return "\n".join(lines)


def build_station_tray_view(tray: Tray, capacity: int) -> str:
    """Format the Station Menu (Tray) header."""
    item = "" if tray.item_id is None else str(tray.item_id)
    lines = [
        "-" * 32,
        "STATION MENU (TRAY)",
        "-" * 32,
        f"Tray ID: {tray.tray_id}",
        f"Item ID: {item}",
        f"Qty: {tray.qty} / {capacity}",
        "-" * 32,
    ]
    return "\n".join(lines)


def build_movement_header(path: list) -> str:
    """Format the 'Robot is moving... please wait (X sec)' line."""
    seconds = sum(TURN_SEC if step == TURN else MOVE_SEC for step in path)
    return f"Robot is moving... please wait ({seconds} sec)"