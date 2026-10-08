"""
main.py -- the IMPERATIVE SHELL of the ASRS Terminal Simulator.

This file owns ALL state and ALL input/output:
  - the two racks, the robot, sim_clock, next_tray_id
  - every input(), print(), and time.sleep()

It never does any "thinking" itself. It calls the pure functions in
asrs_logic.py to validate input, compute distances/paths, and format views.
"""

import time

from asrs_logic import (
    N, MOVE_SEC, TURN_SEC, TRAY_CAPACITY, Tray,
    OUT, IN, UP, DOWN, TURN,
    is_valid_choice, is_valid_amount,
    get_qty_after_increase, get_qty_after_reduce,
    build_path, find_nearest_empty_slot,
    build_admin_view, build_station_tray_view, build_movement_header,
    count_empty_slots,
)


# ---------------------------------------------------------------------------
# I/O helpers (the ONLY functions that talk to the user)
# ---------------------------------------------------------------------------
def validate_choice(prompt: str, max_choice: int) -> int:
    """Keep asking until the user enters a whole number from 1 to max_choice."""
    while True:
        raw = input(prompt)
        if is_valid_choice(raw, max_choice):
            return int(raw)
        print("Invalid choice.")


def validate_amount(prompt: str) -> int:
    """Keep asking until the user enters a non-negative whole number."""
    while True:
        raw = input(prompt)
        if is_valid_amount(raw):
            return int(raw)
        print("Invalid input.")


def validate_tray_id(racks: list):
    """
    Read one Tray ID.
      - non-integer input  -> 'Invalid input.' and reprompt          (EC8)
      - integer not found  -> return None (main prints 'Tray not found.'
        and goes back to the main menu with no movement)             (EC2)
    """
    while True:
        raw = input("Tray ID: ")
        if not is_valid_amount(raw):
            print("Invalid input.")
            continue
        tray_id = int(raw)
        if _find_tray_location(racks, tray_id) is not None:
            return tray_id
        return None


def _find_tray_location(racks: list, tray_id: int):
    """Return (side, row, col) of the tray, or None if it is not stored."""
    for side in range(len(racks)):
        for row in range(len(racks[side])):
            for col in range(len(racks[side][row])):
                tray = racks[side][row][col]
                if tray is not None and tray.tray_id == tray_id:
                    return (side, row, col)
    return None


def display_main_menu(racks: list, robot: dict, sim_clock: int, n: int) -> None:
    """Print the menu header, a compact status line, and the 5 choices."""
    print("-" * 32)
    print("ASRS TERMINAL SIMULATOR")
    print("-" * 32)
    empty0 = count_empty_slots(racks, 0, n)
    empty1 = count_empty_slots(racks, 1, n)
    print(f"Empty slots -> Side0: {empty0}/{n*n}, Side1: {empty1}/{n*n}")
    pos = f"Side {robot['side']} ({robot['row']},{robot['col']})"
    if robot["row"] == n - 1 and robot["col"] == 0:
        pos += " AT STATION"
    carrying = f"tray {robot['carrying'].tray_id}" if robot["carrying"] else "none"
    print(f"Robot: {pos} | carrying: {carrying} | Sim time: {sim_clock} sec")
    print("-" * 32)
    print("1) Call robot WITH tray id")
    print("2) Call robot EMPTY")
    print("3) Print warehouse map / Admin")
    print("4) Robot status")
    print("5) Exit")


def execute_path(path: list, robot: dict, sim_clock: int) -> int:
    """
    Move the robot step by step along path, printing its live position and
    sleeping per move. Returns the updated sim_clock.
    """
    print(build_movement_header(path))
    for step in path:
        if step == TURN:
            robot["side"] = 1 - robot["side"]
            sim_clock += TURN_SEC
        elif step == IN:
            robot["col"] += 1
            sim_clock += MOVE_SEC
        elif step == OUT:
            robot["col"] -= 1
            sim_clock += MOVE_SEC
        elif step == UP:
            robot["row"] -= 1
            sim_clock += MOVE_SEC
        elif step == DOWN:
            robot["row"] += 1
            sim_clock += MOVE_SEC
        print(f"[t={sim_clock}s] robot at Side {robot['side']} "
              f"({robot['row']},{robot['col']})")
        time.sleep(TURN_SEC if step == TURN else MOVE_SEC)
    return sim_clock


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------
def main() -> None:
    # ---- Initialize state ------------------------------------------------
    racks = [[[None for _ in range(N)] for _ in range(N)] for _ in range(2)]
    robot = {"side": 0, "row": N - 1, "col": 0, "carrying": None}
    sim_clock = 0
    next_tray_id = 1

    # ---- Main loop -------------------------------------------------------
    while True:
        display_main_menu(racks, robot, sim_clock, N)
        choice = validate_choice("Enter choice: ", 5)

        # ------------------------------------------------------------------
        # Choice 1: call the robot WITH a tray id
        # ------------------------------------------------------------------
        if choice == 1:
            tray_id = validate_tray_id(racks)
            if tray_id is None:
                print("Tray not found.")
                continue  # back to main menu, no movement  [EC2]

            side, row, col = _find_tray_location(racks, tray_id)

            # Go to the tray and pick it up.
            path = build_path(robot["side"], robot["row"], robot["col"],
                              side, row, col, TURN_SEC)
            sim_clock = execute_path(path, robot, sim_clock)
            tray = racks[side][row][col]
            racks[side][row][col] = None
            robot["carrying"] = tray

            # Carry it back to the station (same side).
            path = build_path(robot["side"], robot["row"], robot["col"],
                              robot["side"], N - 1, 0, TURN_SEC)
            sim_clock = execute_path(path, robot, sim_clock)

            # Station Menu (Tray) -- loops until send-back or remove.
            while True:
                print(build_station_tray_view(tray, TRAY_CAPACITY))
                print("1) Increase items")
                print("2) Reduce items")
                print("3) Send tray back")
                print("4) Remove tray from system")
                sub = validate_choice("Enter choice: ", 4)

                if sub == 1:  # Increase items
                    if tray.item_id is None:                    # [EC6]
                        tray.item_id = validate_amount("Item ID: ")
                    amount = validate_amount("Add quantity: ")
                    new_qty = get_qty_after_increase(tray.qty, amount, TRAY_CAPACITY)
                    if new_qty is None:
                        print("Exceeds tray capacity.")        # [EC3]
                    else:
                        tray.qty = new_qty

                elif sub == 2:  # Reduce items
                    amount = validate_amount("Reduce quantity: ")
                    new_qty = get_qty_after_reduce(tray.qty, amount)
                    if new_qty is None:
                        print("Quantity cannot go below 0.")   # [EC4]
                    else:
                        tray.qty = new_qty
                        if new_qty == 0:
                            tray.item_id = None                # [EC5]

                elif sub == 3:  # Send tray back
                    slot = find_nearest_empty_slot(
                        racks, robot["side"], robot["row"], robot["col"], N)
                    if slot is None:
                        print("No empty slots available.")     # [EC7]
                    else:
                        s, r, c = slot
                        path = build_path(robot["side"], robot["row"], robot["col"],
                                          s, r, c, TURN_SEC)
                        sim_clock = execute_path(path, robot, sim_clock)
                        racks[s][r][c] = tray
                        robot["carrying"] = None
                        break  # back to main menu

                elif sub == 4:  # Remove tray from system
                    robot["carrying"] = None  # id is retired, never reused
                    break  # back to main menu

        # ------------------------------------------------------------------
        # Choice 2: call the robot EMPTY
        # ------------------------------------------------------------------
        elif choice == 2:
            # Move to the station if not already there.
            if not (robot["row"] == N - 1 and robot["col"] == 0):
                path = build_path(robot["side"], robot["row"], robot["col"],
                                  robot["side"], N - 1, 0, TURN_SEC)
                sim_clock = execute_path(path, robot, sim_clock)

            # Station Menu (Empty).
            while True:
                print("-" * 32)
                print("STATION MENU (EMPTY)")
                print("-" * 32)
                print("1) Add new tray")
                print("2) Send it back")
                sub = validate_choice("Enter choice: ", 2)

                if sub == 1:  # Add new tray
                    item_id = validate_amount("Item ID: ")
                    while True:
                        amount = validate_amount("Quantity (%): ")
                        if amount > TRAY_CAPACITY:
                            print("Exceeds tray capacity.")
                        else:
                            break
                    tray = Tray(next_tray_id, item_id, amount)
                    next_tray_id += 1

                    slot = find_nearest_empty_slot(
                        racks, robot["side"], robot["row"], robot["col"], N)
                    if slot is None:
                        print("No empty slots available.")     # [EC7]
                        robot["carrying"] = tray  # tray remains carried
                    else:
                        s, r, c = slot
                        path = build_path(robot["side"], robot["row"], robot["col"],
                                          s, r, c, TURN_SEC)
                        sim_clock = execute_path(path, robot, sim_clock)
                        racks[s][r][c] = tray
                        robot["carrying"] = None
                        break  # back to main menu

                elif sub == 2:  # Send it back: no movement, no clock change
                    break  # back to main menu

        # ------------------------------------------------------------------
        # Choice 3: print the warehouse admin view
        # ------------------------------------------------------------------
        elif choice == 3:
            print(build_admin_view(racks, robot, sim_clock, N))

        # ------------------------------------------------------------------
        # Choice 4: robot status
        # ------------------------------------------------------------------
        elif choice == 4:
            pos = f"Side {robot['side']} ({robot['row']},{robot['col']})"
            if robot["row"] == N - 1 and robot["col"] == 0:
                pos += " AT STATION"
            carrying = f"tray {robot['carrying'].tray_id}" if robot["carrying"] else "none"
            print(f"Robot: {pos} | carrying: {carrying} | Sim time: {sim_clock} sec")

        # ------------------------------------------------------------------
        # Choice 5: exit
        # ------------------------------------------------------------------
        elif choice == 5:
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()