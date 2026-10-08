# ASRS Terminal Simulator — Design Document

## 1. Terminology & Formulae

**The racks.** Two N×N (default N = 4) matrices, `racks[0]` (Side 0) and `racks[1]` (Side 1). Each cell holds either `None` (empty slot) or a `Tray` object. Both racks start completely empty.

**The robot.** A single dict-like state: `{"side": 0|1, "row": int, "col": int, "carrying": Tray | None}`. It starts at the station, `(side=0, row=N-1, col=0)`, carrying nothing. While `carrying` is set, `main()` refuses Choices 1 and 2 and "Add new tray" (EC 10) so a carried tray can never be silently overwritten or lost.

**The station.** The shared dock at logical coordinate (N-1, 0) on both racks. A robot at either side's (N-1, 0) counts as "AT STATION". Station cells never hold a tray and are always excluded from placement, which leaves N×N − 1 = 15 usable storage slots per side and 30 in total.

**Tray IDs.** `next_tray_id` is a counter created inside `main()` at start-up, starting at 1, incremented on every new tray, and never reused — even after a tray is removed from the system.

**The tray invariant.** A tray's `item_id` is `None` exactly when its qty is 0. The invariant is enforced at every place a qty is assigned: creation (a tray added with quantity 0 is stored itemless), increase (an item id prompted this turn is only committed if the new qty is greater than 0), and reduce (reaching exactly 0 resets `item_id` to `None`).

**Simulated clock.** `sim_clock` is a running total of seconds, incremented by MOVE_SEC (1) per executed move and by TURN_SEC per turn. Turning between sides (TURN_SEC = 0) currently adds no time but is tracked as a separate constant for future tuning.

**Formulae**

- Distance (same side): |r1 − r2| + |c1 − c2|
- Distance (cross side): c1 + c2 + |r1 − r2| + TURN_SEC
- Move time for a path: the sum over steps — MOVE_SEC for every IN/OUT/UP/DOWN, plus TURN_SEC for every TURN. (With TURN_SEC = 0 this equals the number of non-TURN moves; counting `len(path) × MOVE_SEC` would overcount a cross-side trip that includes a TURN.)
- Nearest empty slot: the empty, non-station cell minimizing distance from the robot's current position. Ties are broken by scan order — Side 0 before Side 1, then row ascending, then column ascending.
- Increase items: new qty = current qty + amount; rejected if new qty > TRAY_CAPACITY (50)
- Reduce items: new qty = current qty − amount; rejected if new qty < 0. If new qty == 0, item_id is reset to `None`.

## 2. File Organization

The program is organised into two files, plus a test suite:

- **asrs_logic.py** — the functional core. Pure functions only. It defines the `Tray` class, the shared constants, and every function takes what it needs as arguments and returns a value. No `input`, no `print`, no `time.sleep`. This file never talks to a person or the clock. It also owns the two pure rack searches — `find_tray_location` (where is this tray?) and `find_nearest_empty_slot` (where should this tray go?) — plus the view builders that format strings for printing.
- **main.py** — the imperative shell. All `input`, `print`, and `time.sleep` calls live here, and it owns the two changing pieces of state: the racks (both matrices) and the robot dict, plus `sim_clock` and `next_tray_id`. It calls the pure functions in `asrs_logic.py` to validate input, compute distances and paths, search the racks, and format views.
- **test_asrs.py** — unit tests for the functional core only (39 tests). It is not part of the shipped program; `main.py` is the input/output shell, which is exercised by running the program manually.

## 3. Program Flow

1. Initialize both racks as empty N×N matrices, the robot at the station (side 0, N-1, 0) carrying nothing, sim_clock = 0, and next_tray_id = 1.
2. Loop: print the main menu — the header, a compact status block (empty-slot counts per side, robot position/carrying, sim time), and the 5 choices.
3. Read the user's choice.
4. If choice is 1 (Call robot WITH tray id):
   a. If the robot is already carrying a tray, print `Robot is already carrying tray N.` and return to step 2. (EC 10)
   b. Prompt for Tray ID; if it does not exist in either rack, print `Tray not found.` and return to step 2. (EC 2)
   c. Build the path from the robot's current position to the tray's slot; execute it (printing live position each second), print `-> PICK tray N`, pick up the tray, then build and execute the path back to the station.
   d. Loop the Station Menu (Tray): show tray id, item id, qty, capacity, and the 4 tray choices.
   e. Increase: if the tray's item id is `None`, prompt for a new item id first (EC 6); prompt amount; validate against capacity; if invalid, print `Exceeds tray capacity.` and `Remaining capacity: X` (EC 3) and re-loop the Station Menu; otherwise set the new qty and set the item id (None if the new qty is 0), preserving the tray invariant.
   f. Reduce: prompt amount; validate against 0; if invalid, print `Quantity cannot go below 0.` (EC 4) and re-loop the Station Menu; otherwise update qty, resetting item id to `None` if the result is exactly 0. (EC 5)
   g. Send tray back: find the nearest empty slot; if none exists, print `No empty slots available.` (EC 7) and re-loop the Station Menu; otherwise build and execute the path, print `-> PLACE tray N`, place the tray, print `Tray N placed at Side S (row,col)`, and return to step 2.
   h. Remove tray from system: discard the tray (id never reissued), the robot stays empty-handed, and return to step 2.
5. If choice is 2 (Call robot EMPTY):
   a. If the robot is already carrying a tray, print `Robot is already carrying tray N.` and return to step 2. (EC 10)
   b. Build the path from the robot's current position to the station (a zero-length path when already there) and execute it — the movement header is still printed, as `(0 sec)`.
   c. Show the Station Menu (Empty) with 2 choices.
   d. Add new tray: if the robot is somehow already carrying (a previous add failed with a full warehouse), print `Robot is already carrying tray N.` (EC 10) and re-loop the Station Menu; otherwise prompt item id and quantity; validate quantity against capacity; assign the next tray id (stored itemless when the quantity is 0); find the nearest empty slot; if none exists, print `No empty slots available.` (EC 7), keep the tray carried, and re-loop the Station Menu; otherwise build and execute the path, print `-> PLACE tray N`, place the tray, print `Tray N placed at Side S (row,col)`, and return to step 2.
   e. Send it back: perform no movement and no sim_clock change; return directly to step 2 (the robot keeps any tray it is still carrying — EC 10).
6. If choice is 3 (Print warehouse map / Admin): print both racks, empty-slot counts per side and overall (out of 15 per side, 30 total), and robot status; no movement or sim_clock change; return to step 2.
7. If choice is 4 (Robot status): print the robot's current slot (or AT STATION), carrying tray id or none, and sim_clock; return to step 2.
8. If choice is 5 (Exit): print `Goodbye!` and end the program.
9. If choice is invalid: print `Invalid choice.` and return to step 2. (EC 1)

The entry point wraps `main()` in a try/except for `EOFError`, so an input stream that ends without choosing 5 (piped or redirected input) exits cleanly with `Goodbye!` instead of a traceback. (EC 8)

## 4. Function Signatures

### asrs_logic.py (Functional core)

| Typed header line | What it's for |
|---|---|
| `class Tray` / `def __init__(self, tray_id: int, item_id: Optional[int], qty: int)` | A tray stored in a rack slot; holds items of a single item id (None when qty is 0). |
| `def is_valid_choice(choice_str: str, max_choice: int) -> bool` | Returns True if choice_str is a whole number from 1 to max_choice, otherwise False. |
| `def is_valid_amount(amount_str: str) -> bool` | Returns True if amount_str represents a non-negative whole number, otherwise False. |
| `def get_qty_after_increase(current_qty: int, amount: int, capacity: int) -> Optional[int]` | Returns the new quantity if it would not exceed capacity, otherwise None. |
| `def get_qty_after_reduce(current_qty: int, amount: int) -> Optional[int]` | Returns the new quantity if it would not go below 0, otherwise None. |
| `def distance(p_side: int, p_row: int, p_col: int, t_side: int, t_row: int, t_col: int, turn_sec: int) -> int` | Computes the same-side or cross-side travel time between two coordinates. |
| `def build_path(p_side: int, p_row: int, p_col: int, t_side: int, t_row: int, t_col: int, turn_sec: int) -> list` | Returns the canonical ordered move list (OUT/TURN → IN/OUT → UP/DOWN) between two coordinates. |
| `def find_tray_location(racks: list, tray_id: int) -> Optional[tuple]` | Scans both racks (Side 0 first, then Side 1, row by row) for the tray with tray_id; returns (side, row, col), or None if no stored tray has that id. |
| `def find_nearest_empty_slot(racks: list, p_side: int, p_row: int, p_col: int, n: int) -> Optional[tuple]` | Scans both racks (Side 0→1, row asc, col asc) for the empty, non-station cell with minimum distance from the robot. Returns None if no empty slot exists. |
| `def count_empty_slots(racks: list, side: int, n: int) -> int` | Counts the empty, non-station storage cells on one side (15 on a fresh side). |
| `def build_admin_view(racks: list, robot: dict, sim_clock: int, n: int) -> str` | Formats both racks (with adaptive column widths), empty-slot counts out of the usable totals, and robot status into the full admin print string. |
| `def build_station_tray_view(tray: Tray, capacity: int) -> str` | Formats the Station Menu (Tray) header showing tray id, item id, qty, and capacity. |
| `def build_movement_header(path: list) -> str` | Formats the `Robot is moving... please wait (X sec)` line; X is the per-step time sum (MOVE_SEC per move, TURN_SEC per turn). |

*(A private helper, `_render_cell`, formats a single map cell and is covered by the `build_admin_view` algorithm below.)*

### main.py (Imperative shell)

| Typed header line | What it's for |
|---|---|
| `def display_main_menu(racks: list, robot: dict, sim_clock: int, n: int) -> None` | Prints the ASRS header, a compact status block (empty-slot counts per side, robot position/carrying, sim time), and the 5 main choices. The full admin view is Choice 3's job. |
| `def validate_choice(prompt: str, max_choice: int) -> int` | Prompts the user until a valid whole-number choice from 1 to max_choice is entered, then returns it. |
| `def validate_tray_id(racks: list) -> Optional[int]` | Prompts once for a Tray ID, reprompting on non-integer input (EC 8). Returns the id if it is stored in a rack; otherwise returns None — `main()` then prints `Tray not found.` and returns to the main menu with no movement (EC 2). |
| `def validate_amount(prompt: str) -> int` | Prompts the user until a valid non-negative whole number is entered. |
| `def execute_path(path: list, robot: dict, sim_clock: int) -> int` | Applies each move in path to the robot, sleeping TURN_SEC for a TURN and MOVE_SEC for any other step, and printing the live position per step; returns the updated sim_clock. |
| `def main() -> None` | Initializes the racks, robot, sim_clock, and next_tray_id; runs the application loop; owns all state changes and triggers all output. The entry point calls it inside a try/except EOFError so ended input exits cleanly. |

## 5. Function-Level Algorithm

### asrs_logic.py

**class Tray**
1. Define `__init__(self, tray_id: int, item_id: int | None, qty: int)` to store the attributes.

**is_valid_choice(choice_str, max_choice)**
1. Try to convert choice_str to an integer.
2. If it fails, return False.
3. If the integer is less than 1 or greater than max_choice, return False.
4. Otherwise, return True.

**is_valid_amount(amount_str)**
1. Try to convert amount_str to an integer.
2. If it fails or is not a whole number, return False.
3. If the integer is negative, return False.
4. Otherwise, return True.

**get_qty_after_increase(current_qty, amount, capacity)**
1. Set new_qty to current_qty + amount.
2. If new_qty is greater than capacity, return None.
3. Otherwise, return new_qty.

**get_qty_after_reduce(current_qty, amount)**
1. Set new_qty to current_qty − amount.
2. If new_qty is less than 0, return None.
3. Otherwise, return new_qty.

**distance(p_side, p_row, p_col, t_side, t_row, t_col, turn_sec)**
1. If p_side == t_side, return |p_row − t_row| + |p_col − t_col|.
2. Otherwise, return p_col + t_col + |p_row − t_row| + turn_sec.

**build_path(p_side, p_row, p_col, t_side, t_row, t_col, turn_sec)**
1. Initialize an empty steps list.
2. If p_side != t_side: append OUT and decrement p_col until it reaches 0, then append TURN and set p_side to t_side.
3. While p_col != t_col: append IN (if p_col < t_col) or OUT (otherwise) and adjust p_col by one toward t_col.
4. While p_row != t_row: append DOWN (if p_row < t_row) or UP (otherwise) and adjust p_row by one toward t_row.
5. Return steps. (When the start equals the target, steps is the empty list — a zero-length trip.)

**find_tray_location(racks, tray_id)**
1. For side in 0..len(racks)-1, for row in 0..n-1, for col in 0..n-1:
   a. If the cell holds a Tray whose tray_id equals tray_id, return (side, row, col).
2. Return None.

**find_nearest_empty_slot(racks, p_side, p_row, p_col, n)**
1. Initialize best to None.
2. For side in (0, 1), for row in 0..n-1, for col in 0..n-1 (this triple loop order is the tie-break order):
   a. Skip the cell if it is a station cell (row == n-1 and col == 0).
   b. Skip the cell if racks[side][row][col] is not None.
   c. Compute d = distance(p_side, p_row, p_col, side, row, col, TURN_SEC).
   d. If best is None or d is strictly less than best's distance, set best to (side, row, col).
3. If best is still None, return None.
4. Otherwise, return (best.side, best.row, best.col).

**count_empty_slots(racks, side, n)**
1. Initialize count to 0.
2. For row in 0..n-1, for col in 0..n-1: skip the station cell; if the cell is None, add 1 to count.
3. Return count.

**build_admin_view(racks, robot, sim_clock, n)**
1. Render every cell of both sides into text first (see _render_cell), then set cell_w to max(14, longest cell + 1) so the map columns never run together, however long the ids get.
2. Start the output with the WAREHOUSE MAP divider.
3. For each row index from 0 to n-1, lay the Side 0 cells and the Side 1 cells side by side, each cell padded to cell_w, with a small gap between the two sides.
4. Count empty (non-station) cells for Side 0, Side 1, and overall; append the `Empty slots -> ...` line using the usable totals (n×n − 1 per side, 2×(n×n − 1) overall).
5. Append the robot line: current slot or AT STATION, carrying tray id or none.
6. Append the `Sim time: <sim_clock> sec` line.
7. Return the full formatted string.

**_render_cell(racks, side, row, col, n)**
1. If the cell is the station (row == n-1 and col == 0), return "STATION".
2. If the cell is None, return "EMPTY".
3. Otherwise return `T<tray_id>:I<item or ->(q<qty>)`.

**build_station_tray_view(tray, capacity)**
1. Format a header showing Tray ID, Item ID (or blank if None), Qty, and capacity.
2. Return the formatted string.

**build_movement_header(path)**
1. Set seconds to the per-step sum: TURN_SEC for each TURN step, MOVE_SEC for every other step.
2. Return the string `Robot is moving... please wait ({seconds} sec)`.

### main.py

**display_main_menu(racks, robot, sim_clock, n)**
1. Print the divider, ASRS TERMINAL SIMULATOR, and another divider.
2. Print the compact status block: the empty-slot counts per side (out of n×n − 1) and the robot line (position, AT STATION flag, carrying, sim time).
3. Print the 5 menu choices.

**validate_choice(prompt, max_choice)**
1. Start an infinite loop.
2. Read input with the prompt.
3. If is_valid_choice(input, max_choice) is True, return the converted integer.
4. Otherwise, print `Invalid choice.` and restart the loop.

**validate_tray_id(racks)**
1. Start an infinite loop.
2. Read input with the prompt `Tray ID: `.
3. If the input is not a valid non-negative whole number, print `Invalid input.` and restart the loop. (EC 8)
4. Convert to tray_id.
5. If find_tray_location(racks, tray_id) is not None, return tray_id.
6. Otherwise, return None — the caller prints `Tray not found.` and returns to the main menu. (EC 2)

**validate_amount(prompt)**
1. Start an infinite loop.
2. Read input with the prompt.
3. If is_valid_amount(input) is True, return the converted integer.
4. Otherwise, print `Invalid input.` and restart the loop.

**execute_path(path, robot, sim_clock)**
1. Call build_movement_header(path) and print the result (also for an empty path — `(0 sec)`).
2. For each step in path:
   a. Apply step to the robot (update side, row, or col accordingly; TURN only flips side).
   b. Increment sim_clock by TURN_SEC for a TURN, or MOVE_SEC for any other step.
   c. Print `[t={sim_clock}s] robot at Side {side} ({row},{col})`.
   d. Call time.sleep(TURN_SEC) for a TURN, or time.sleep(MOVE_SEC) otherwise.
3. Return the updated sim_clock.

**main()**
1. Initialize racks as two empty N×N matrices, robot at (side=0, row=N-1, col=0, carrying=None), sim_clock = 0, and next_tray_id = 1.
2. Loop forever:
3. Call display_main_menu(racks, robot, sim_clock, N).
4. Set choice to validate_choice("Enter choice: ", 5).
5. If choice == 1:
   a. If robot.carrying is not None, print `Robot is already carrying tray N.` and continue the loop. (EC 10)
   b. Set tray_id to validate_tray_id(racks); if None, print `Tray not found.` and continue the loop. (EC 2)
   c. Locate the tray's (side, row, col) with find_tray_location; build and execute the path there via execute_path; print `-> PICK tray N`; set the cell to None and set robot.carrying to the tray.
   d. Build and execute the path back to the station.
   e. Loop the Station Menu (Tray): print build_station_tray_view(tray, TRAY_CAPACITY) and the 4 choices; read sub_choice.
   f. If sub_choice == 1: set item_id to tray.item_id, or to a newly prompted item id when tray.item_id is None (EC 6); set amount to validate_amount("Add quantity: "); call get_qty_after_increase; if None, print `Exceeds tray capacity.` and `Remaining capacity: {TRAY_CAPACITY − tray.qty}` (EC 3) and re-loop the station menu; otherwise update tray.qty and set tray.item_id to item_id if the new qty is greater than 0, else None.
   g. If sub_choice == 2: set amount to validate_amount("Reduce quantity: "); call get_qty_after_reduce; if None, print `Quantity cannot go below 0.` (EC 4) and re-loop the station menu; otherwise update tray.qty, resetting tray.item_id to None if the new qty is 0. (EC 5)
   h. If sub_choice == 3: call find_nearest_empty_slot; if None, print `No empty slots available.` (EC 7) and re-loop the station menu; otherwise build and execute the path, print `-> PLACE tray N`, place the tray in that cell, print `Tray N placed at Side S (row,col)`, set robot.carrying to None, and return to step 3.
   i. If sub_choice == 4: discard the tray (do not add it back to any rack, do not reuse its id), set robot.carrying to None, and return to step 3.
6. If choice == 2:
   a. If robot.carrying is not None, print `Robot is already carrying tray N.` and continue the loop. (EC 10)
   b. Build and execute the path to the station — including when the robot is already there (a zero-length path that prints `(0 sec)`).
   c. Print the Station Menu (Empty) and read sub_choice.
   d. If sub_choice == 1: if robot.carrying is not None (a previous add failed), print `Robot is already carrying tray N.` (EC 10) and re-loop the station menu; otherwise prompt for item id; set amount to validate_amount("Quantity (%): "); if amount > TRAY_CAPACITY, print `Exceeds tray capacity.` and re-prompt; otherwise create Tray(next_tray_id, item_id if amount > 0 else None, amount), increment next_tray_id, and call find_nearest_empty_slot; if None, print `No empty slots available.` (EC 7) and re-loop the station menu with the tray still carried; otherwise build and execute the path, print `-> PLACE tray N`, place the tray in that cell, print `Tray N placed at Side S (row,col)`, and return to step 3.
   e. If sub_choice == 2: perform no movement, do not change sim_clock, and return to step 3.
7. If choice == 3: call build_admin_view and print it; return to step 3 (no movement, no sim_clock change).
8. If choice == 4: print the robot's current slot (or AT STATION), carrying tray id or none, and sim_clock; return to step 3.
9. If choice == 5: print `Goodbye!` and break the loop.

**Entry point**
1. Run main() inside try/except EOFError; on EOF, print `Goodbye!` and exit cleanly (no traceback). (EC 8)
