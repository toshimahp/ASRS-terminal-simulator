"""
test_asrs.py -- unit tests for the ASRS Terminal Simulator.

These tests cover the PURE logic in asrs_logic.py. We do NOT test main.py
here because main.py is the input/output shell (it talks to the user and
the clock), which we test by running the program manually.

Run with:
    python -m unittest test_asrs.py -v
or simply:
    python test_asrs.py
"""

import unittest

from asrs_logic import (
    N, MOVE_SEC, TURN_SEC, TRAY_CAPACITY, Tray,
    OUT, IN, UP, DOWN, TURN,
    is_valid_choice, is_valid_amount,
    get_qty_after_increase, get_qty_after_reduce,
    distance, build_path, find_nearest_empty_slot,
    build_admin_view, build_station_tray_view, build_movement_header,
    count_empty_slots,
)


def make_racks(n=N):
    """Build two empty n x n racks."""
    return [[[None for _ in range(n)] for _ in range(n)] for _ in range(2)]


class TestTray(unittest.TestCase):
    def test_tray_stores_attributes(self):
        tray = Tray(1, 101, 25)
        self.assertEqual(tray.tray_id, 1)
        self.assertEqual(tray.item_id, 101)
        self.assertEqual(tray.qty, 25)

    def test_tray_can_have_no_item(self):
        tray = Tray(2, None, 0)
        self.assertIsNone(tray.item_id)
        self.assertEqual(tray.qty, 0)


class TestIsValidChoice(unittest.TestCase):
    def test_accepts_valid_choice(self):
        self.assertTrue(is_valid_choice("1", 5))
        self.assertTrue(is_valid_choice("5", 5))

    def test_rejects_out_of_range(self):
        self.assertFalse(is_valid_choice("0", 5))
        self.assertFalse(is_valid_choice("6", 5))

    def test_rejects_non_integer(self):
        self.assertFalse(is_valid_choice("abc", 5))
        self.assertFalse(is_valid_choice("", 5))


class TestIsValidAmount(unittest.TestCase):
    def test_accepts_non_negative(self):
        self.assertTrue(is_valid_amount("0"))
        self.assertTrue(is_valid_amount("50"))

    def test_rejects_negative(self):
        self.assertFalse(is_valid_amount("-1"))

    def test_rejects_non_integer(self):
        self.assertFalse(is_valid_amount("abc"))
        self.assertFalse(is_valid_amount(""))


class TestQuantityRules(unittest.TestCase):
    def test_increase_within_capacity(self):
        self.assertEqual(get_qty_after_increase(25, 20, TRAY_CAPACITY), 45)

    def test_increase_exceeds_capacity_returns_none(self):
        # 45 + 40 = 85, which is greater than 50.
        self.assertIsNone(get_qty_after_increase(45, 40, TRAY_CAPACITY))

    def test_increase_exactly_to_capacity_is_allowed(self):
        self.assertEqual(get_qty_after_increase(30, 20, TRAY_CAPACITY), 50)

    def test_reduce_above_zero(self):
        self.assertEqual(get_qty_after_reduce(45, 20), 25)

    def test_reduce_below_zero_returns_none(self):
        self.assertIsNone(get_qty_after_reduce(45, 100))

    def test_reduce_exactly_to_zero_is_allowed(self):
        self.assertEqual(get_qty_after_reduce(45, 45), 0)


class TestDistance(unittest.TestCase):
    def test_same_side_manhattan(self):
        # (3,0) -> (0,3) on Side 0 = |3-0| + |0-3| = 6
        self.assertEqual(distance(0, 3, 0, 0, 0, 3, TURN_SEC), 6)

    def test_same_side_same_slot_is_zero(self):
        self.assertEqual(distance(0, 3, 0, 0, 3, 0, TURN_SEC), 0)

    def test_cross_side(self):
        # Side 0 (0,2) -> Side 1 (0,3): c1 + c2 + |r1-r2| + turn = 2+3+0+0 = 5
        self.assertEqual(distance(0, 0, 2, 1, 0, 3, TURN_SEC), 5)


class TestBuildPath(unittest.TestCase):
    def test_same_slot_gives_empty_path(self):
        path = build_path(0, 3, 0, 0, 3, 0, TURN_SEC)
        self.assertEqual(path, [])

    def test_same_side_path_length_matches_distance(self):
        path = build_path(0, 3, 0, 0, 0, 3, TURN_SEC)
        self.assertEqual(len(path), 6)

    def test_same_side_moves_columns_then_rows(self):
        # (3,0) -> (0,3): 3 IN (col 0->3), then 3 UP (row 3->0).
        path = build_path(0, 3, 0, 0, 0, 3, TURN_SEC)
        self.assertEqual(path, [IN, IN, IN, UP, UP, UP])

    def test_cross_side_includes_turn(self):
        # Side 0 (0,2) -> Side 1 (0,3): OUT OUT (to aisle), TURN, IN IN IN.
        path = build_path(0, 0, 2, 1, 0, 3, TURN_SEC)
        self.assertEqual(path, [OUT, OUT, TURN, IN, IN, IN])

    def test_cross_side_move_count_matches_distance(self):
        path = build_path(0, 0, 2, 1, 0, 3, TURN_SEC)
        moves = [s for s in path if s != TURN]
        self.assertEqual(len(moves), 5)  # distance was 5


class TestFindNearestEmptySlot(unittest.TestCase):
    def test_fresh_warehouse_picks_nearest_with_tie_break(self):
        racks = make_racks()
        # Robot at station Side 0 (3,0). Nearest empty slots are (2,0) and
        # (3,1), both 1 step away. Scan order visits row 2 before row 3,
        # so (0,2,0) wins the tie.
        slot = find_nearest_empty_slot(racks, 0, 3, 0, N)
        self.assertEqual(slot, (0, 2, 0))

    def test_skips_occupied_cells(self):
        racks = make_racks()
        racks[0][2][0] = Tray(1, 101, 25)  # block (0,2,0)
        slot = find_nearest_empty_slot(racks, 0, 3, 0, N)
        # Now the nearest remaining slot is (0,3,1), 1 step away.
        self.assertEqual(slot, (0, 3, 1))

    def test_never_returns_station_cell(self):
        racks = make_racks()
        slot = find_nearest_empty_slot(racks, 0, 3, 0, N)
        self.assertIsNotNone(slot)
        side, row, col = slot
        self.assertFalse(row == N - 1 and col == 0)

    def test_full_warehouse_returns_none(self):
        racks = make_racks()
        for side in (0, 1):
            for row in range(N):
                for col in range(N):
                    if row == N - 1 and col == 0:
                        continue  # leave the station cells empty
                    racks[side][row][col] = Tray(1, 101, 1)
        slot = find_nearest_empty_slot(racks, 0, 3, 0, N)
        self.assertIsNone(slot)


class TestCountEmptySlots(unittest.TestCase):
    def test_fresh_side_has_15_storage_slots(self):
        racks = make_racks()
        # 16 cells minus the station = 15 usable storage slots.
        self.assertEqual(count_empty_slots(racks, 0, N), 15)
        self.assertEqual(count_empty_slots(racks, 1, N), 15)

    def test_occupied_slot_not_counted(self):
        racks = make_racks()
        racks[0][0][0] = Tray(1, 101, 25)
        self.assertEqual(count_empty_slots(racks, 0, N), 14)


class TestMovementHeader(unittest.TestCase):
    def test_counts_only_moves_not_turns(self):
        # 6 moves, no turn -> 6 seconds.
        path = [IN, IN, IN, UP, UP, UP]
        self.assertEqual(build_movement_header(path),
                         "Robot is moving... please wait (6 sec)")

    def test_turn_adds_no_time_when_turn_sec_is_zero(self):
        # 5 moves + 1 turn (TURN_SEC=0) -> 5 seconds.
        path = [OUT, OUT, TURN, IN, IN, IN]
        self.assertEqual(build_movement_header(path),
                         "Robot is moving... please wait (5 sec)")


class TestStationTrayView(unittest.TestCase):
    def test_shows_tray_details(self):
        tray = Tray(7, 101, 25)
        view = build_station_tray_view(tray, TRAY_CAPACITY)
        self.assertIn("Tray ID: 7", view)
        self.assertIn("Item ID: 101", view)
        self.assertIn("Qty: 25 / 50", view)

    def test_blank_item_id_when_none(self):
        tray = Tray(7, None, 0)
        view = build_station_tray_view(tray, TRAY_CAPACITY)
        self.assertIn("Item ID: \n", view)


class TestAdminView(unittest.TestCase):
    def test_contains_key_parts(self):
        racks = make_racks()
        racks[0][0][0] = Tray(1, 101, 25)
        robot = {"side": 0, "row": N - 1, "col": 0, "carrying": None}
        view = build_admin_view(racks, robot, 34, N)
        self.assertIn("WAREHOUSE MAP", view)
        self.assertIn("T1:I101(q25)", view)
        self.assertIn("STATION", view)
        self.assertIn("EMPTY", view)
        self.assertIn("AT STATION", view)
        self.assertIn("Sim time: 34 sec", view)

    def test_reports_carrying_tray(self):
        racks = make_racks()
        robot = {"side": 0, "row": N - 1, "col": 0, "carrying": Tray(9, 101, 5)}
        view = build_admin_view(racks, robot, 0, N)
        self.assertIn("carrying: tray 9", view)


if __name__ == "__main__":
    unittest.main(verbosity=2)