# ASRS Terminal Simulator PRD

## Problem Statement & Description

An ASRS (Automated Storage and Retrieval System) Terminal Simulator models a single robot that serves two square storage racks placed on either side of it. Trays holding items are stored in rack slots; the robot fetches a tray to a shared station, where the user can add or remove items, discard the tray, or store a brand-new tray. This command-line application manages both racks as N×N matrices, simulates robot travel in real time (1 second per slot moved), automatically places returned or new trays into the nearest empty slot, and prints an admin view of the full warehouse state on request.

## Interface

To run the app: `python main.py`

The app runs in a continuous loop, displaying the main menu before every choice. Robot movement is simulated with `time.sleep(1)` per slot, printing the robot's live position each second, so input is naturally blocked while the robot travels. If the input stream ends before the user chooses Exit, the app prints `Goodbye!` and terminates cleanly (no traceback).

**Inputs:**

- Choice: 1 (Call robot WITH tray id), 2 (Call robot EMPTY), 3 (Print warehouse map / Admin), 4 (Robot status), 5 (Exit)
- Tray ID: any tray id currently stored in a rack (for Choice 1)
- Item ID: any whole number (prompted when a tray's item id is currently `None`)
- Quantity to add / reduce: a whole number; the resulting quantity must stay between 0 and TRAY_CAPACITY (50)
- Station Menu (Tray) choice: 1 (Increase items), 2 (Reduce items), 3 (Send tray back), 4 (Remove tray from system)
- Station Menu (Empty) choice: 1 (Add new tray), 2 (Send it back)
- While the robot is carrying a tray, Choices 1 and 2 (and "Add new tray" in the Station Menu (Empty)) are refused — see EC 10

**Outputs:**

- Main Menu: the ASRS terminal header, a compact status block (empty-slot counts per side, robot position/carrying, and sim time), and the 5 choices.
- Movement Screen: `Robot is moving... please wait (X sec)`, then one line per second (`[t=Xs] robot at Side S (row,col)`) as the robot travels. When the robot arrives to fetch a tray it prints `-> PICK tray N`; when it arrives to store one it prints `-> PLACE tray N` followed by `Tray N placed at Side S (row,col)`.
- Station Menu (Tray): tray id, item id, qty, capacity, then the 4 tray choices.
- Station Menu (Empty): the 2 empty-handed choices.
- Admin Print: both N×N racks (`T<id>:I<item>(q<qty>)`, `EMPTY`, or `STATION` per cell), empty-slot counts per side and overall (usable slots: 15 per side, 30 total — the station is not a storage slot), robot position/carrying, and sim_clock.
- Error Messages: printed verbatim for invalid inputs, followed by returning to the main menu or reprompting.

## Functional Requirements

Here are the functional requirements that must be satisfied by the command-line app. An example interaction is provided along with each.

### FR 1: Call the robot with a tray id, then increase/reduce items, send the tray back, or discard it.

When choice 1 is selected, the app prompts for the Tray ID, validates it exists, then moves the robot to that slot and back to the station carrying the tray.

Distance (same side) = |r1−r2| + |c1−c2|. Distance (cross side) = c1 + c2 + |r1−r2| + TURN_SEC. Each unit of distance costs 1 second (a turn between sides costs TURN_SEC, currently 0) and is printed live as the robot moves. The canonical move order is defined in the Design Document: fix the column first (IN/OUT), then the row (UP/DOWN).

**Increase items:** prompts the quantity; rejects if it would exceed TRAY_CAPACITY (50), printing `Exceeds tray capacity.` and `Remaining capacity: X`; if the tray's item id is `None`, prompts for a new item id first. The newly prompted item id is only kept if the increase succeeds, so a rejected increase can never leave an item id on an empty tray (invariant: qty 0 ⇔ item id `None`).

**Reduce items:** prompts the quantity; rejects if the result would go below 0; if the result is exactly 0, the tray's item id is reset to `None`.

**Send tray back:** the robot carries the tray to the nearest empty slot (deterministic tie-break: side 0→1, then row ascending, then col ascending), places it, prints the placement, and returns to the main menu.

**Remove tray from system:** the tray id is retired and never reissued; the robot ends up empty-handed; the main menu is shown.

```text
$ python main.py
(Main menu prints)
Enter choice: 1
Tray ID: 7
Robot is moving... please wait (6 sec)
[t=1s] robot at Side 0 (3,1)
[t=2s] robot at Side 0 (3,2)
[t=3s] robot at Side 0 (3,3)
[t=4s] robot at Side 0 (2,3)
[t=5s] robot at Side 0 (1,3)
[t=6s] robot at Side 0 (0,3)
-> PICK tray 7
Robot is moving... please wait (6 sec)
[t=7s] robot at Side 0 (0,2)
[t=8s] robot at Side 0 (0,1)
[t=9s] robot at Side 0 (0,0)
[t=10s] robot at Side 0 (1,0)
[t=11s] robot at Side 0 (2,0)
[t=12s] robot at Side 0 (3,0)
--------------------------------
STATION MENU (TRAY)
--------------------------------
Tray ID: 7
Item ID: 101
Qty: 25 / 50
--------------------------------
1) Increase items
2) Reduce items
3) Send tray back
4) Remove tray from system
Enter choice: 1
Add quantity: 20
(Station Menu (TRAY) reprints, now showing Qty: 45 / 50)
```

*(Example premise: earlier activity stored tray 7 at Side 0 (0,3) with item 101, qty 25, and left the robot idle at the station.)*

### FR 2: Call the robot empty to store a brand-new tray, or send it back without moving.

When choice 2 is selected, the robot moves to the station empty-handed — the movement header is printed even when the robot is already there (`(0 sec)`) — and the Station Menu (Empty) is shown.

**Add new tray:** the system auto-assigns a unique tray id (monotonically increasing, never reused); prompts item id and quantity (must not exceed TRAY_CAPACITY); the robot then carries the new tray from the station to the nearest empty slot (same tie-break rule as FR 1) and places it. A tray added with quantity 0 is stored itemless, keeping the invariant qty 0 ⇔ item id `None`.

If no empty slot exists, the app prints `No empty slots available.`, the tray remains carried, and the user is returned to the station menu.

**While the robot is carrying a tray** (which can only happen after the warehouse filled up, because placement failed), Choices 1 and 2 and "Add new tray" are refused with `Robot is already carrying tray N.` (EC 10). A completely full warehouse is therefore a deliberate dead end: the only remaining actions are the admin view (3), robot status (4), and Exit (5), until the program is restarted.

**Send it back:** performs no movement and no sim_clock change; the main menu is simply re-shown (the robot keeps any tray it is still carrying).

```text
$ python main.py
(Main menu prints)
Enter choice: 2
Robot is moving... please wait (0 sec)
--------------------------------
STATION MENU (EMPTY)
--------------------------------
1) Add new tray
2) Send it back
Enter choice: 1
Item ID: 101
Quantity (%): 50
Robot is moving... please wait (1 sec)
[t=1s] robot at Side 0 (2,0)
-> PLACE tray 1
Tray 1 placed at Side 0 (2,0)
(Main menu reprints)
```

### FR 3: Print the warehouse admin view.

When choice 3 is selected, the app prints both racks cell-by-cell, empty-slot counts, and robot status — with no robot movement or sim_clock change.

Each cell prints as `T<tray>:I<item>(q<qty>)` (or `I-` for an itemless tray), `EMPTY`, or `STATION`. Column widths adapt to the longest cell so columns never run together.

Empty-slot counts are shown per side (empty/usable — 15 usable slots per side, 30 in total, because the station is not a storage slot) and overall. The robot line shows the current slot (or AT STATION), carrying tray id or none, and sim_clock in seconds.

```text
$ python main.py
(Main menu prints)
Enter choice: 3
--------------------------------
WAREHOUSE MAP
--------------------------------
SIDE 0                                    SIDE 1
T1:I101(q25)  EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY
EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY
EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY        EMPTY
STATION      EMPTY        EMPTY        EMPTY        STATION      EMPTY        EMPTY        EMPTY
--------------------------------
Empty slots -> Side0: 14/15, Side1: 15/15 (total 29/30)
Robot: Side 0 (3,0) AT STATION | carrying: none
Sim time: 34 sec
--------------------------------
```

## Edge Cases

| # | Input / Situation | Expected behaviour |
|---|-------------------|--------------------|
| EC 1 | Choice is not 1–5 | Print `Invalid choice.` and reprint the main menu |
| EC 2 | Tray ID (Choice 1) not found in either rack | Print `Tray not found.` and return to the main menu (no movement) |
| EC 3 | Increase pushes qty above TRAY_CAPACITY (50) | Print `Exceeds tray capacity.` and `Remaining capacity: X`, then re-show the Station Menu (Tray) |
| EC 4 | Reduce pushes qty below 0 | Print `Quantity cannot go below 0.` and re-show the Station Menu (Tray) |
| EC 5 | Reduce brings qty to exactly 0 | Allowed; the item id is automatically set to `None` |
| EC 6 | Increase attempted while tray's item id is `None` | Prompt for a new item id before accepting the quantity |
| EC 7 | No empty slot available when placing a tray (FR 1 send-back or FR 2 add) | Print `No empty slots available.`; the tray remains carried; return to the station menu |
| EC 8 | Non-integer or empty numeric input | Print `Invalid input.` (or `Invalid choice.` at a menu) and reprompt; never raises a traceback — the program also exits cleanly with `Goodbye!` if the input stream ends |
| EC 9 | Choice is 5 (Exit) | Print `Goodbye!` and terminate the program |
| EC 10 | Choice 1, Choice 2, or "Add new tray" while the robot is already carrying a tray (a previous placement failed because the warehouse was full) | Print `Robot is already carrying tray N.` and return to the main menu (Choices 1/2) or re-show the Station Menu (Empty); the tray stays carried. A full warehouse is a dead end until Exit |

## Test Cases

| Traces to | Inputs (choice, tray_id/coords, item_id, qty) | Expected output |
|---|---|---|
| FR 1 | 1, tray_id=7 at Side 0 (0,3), —, — | 6 sec out, 6 sec back; cell (0,3) becomes EMPTY; `-> PICK tray 7`; tray 7 carried and shown at station |
| FR 1 | 1, tray_id=7, increase qty=20 | Qty 25 → 45; capacity check passes (≤ 50) |
| FR 1 | 1, tray_id=7, send tray back | Tray placed in nearest empty slot per tie-break rule; `-> PLACE tray 7` and `Tray 7 placed at ...` printed; robot ends empty-handed |
| FR 2 | 2, add new tray, item_id=101, qty=50 | Auto-assigned tray id (1 on a fresh warehouse); placed in the nearest empty slot (Side 0 (2,0) from the station, 1 sec); qty capped at 50 |
| FR 2 | 2, send it back | Zero movement, zero sim_clock change, main menu re-shown |
| FR 3 | 3 | Both racks, empty-slot counts (out of 15 per side, 30 total), robot status, and sim_clock all printed and consistent with prior state |
| EC 1 | 9 | `Invalid choice.` |
| EC 2 | 1, tray_id=999 | `Tray not found.` |
| EC 3 | 1, tray_id=7, increase qty=40 (already at 45/50) | `Exceeds tray capacity.` and `Remaining capacity: 5` |
| EC 4 | 1, tray_id=7, reduce qty=100 (only 45 in tray) | `Quantity cannot go below 0.` |
| EC 5 | 1, tray_id=7, reduce qty=45 | Qty becomes 0; item id reset to `None` |
| EC 7 | 2, add new tray (all 30 usable slots already full) | `No empty slots available.`; tray remains carried |
| EC 9 | 5 | `Goodbye!`; program exits |
| EC 10 | 1 or 2, while robot carries tray N (full warehouse) | `Robot is already carrying tray N.`; no movement |
