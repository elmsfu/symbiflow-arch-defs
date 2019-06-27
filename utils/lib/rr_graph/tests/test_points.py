import unittest
from ..points import NamedPosition, StraightSegment, Position, NP, decompose_points_into_tracks


class NamedPositionTests(unittest.TestCase):
    def test_simple(self):
        namedpos = NamedPosition(Position(3, 42), ["testname"])
        self.assertEqual(namedpos.x, 3)
        self.assertEqual(namedpos.y, 42)
        self.assertEqual(namedpos.names, ["testname"])

    def test_nonstr(self):
        with self.assertRaises(TypeError):
            NamedPosition(Position(0, 1), ["name1", "name2", 2])

    def test_first(self):
        namedpos = NamedPosition(Position(0, 1), ["name1", "name2"])
        self.assertEqual(namedpos.first, "name1")


class StraightSegmentTests(unittest.TestCase):
    def test_straight_segment(self):
        ss = StraightSegment(StraightSegment.Type.S, [NP(0, 0)])
        ss.append(NP(0, 1))
        ss.append(NP(0, 2))
        self.assertEqual(ss.d, StraightSegment.Type.V)

        self.assertEqual(len(ss), 3)

    def test_segment_append(self):
        ss = StraightSegment(StraightSegment.Type.S, [NP(0, 0)])
        ss.append(NP(0, 1))
        # Add point in different direction
        with self.assertRaises(AssertionError):
            ss.append(NP(1, 0))

    def test_names(self):
        ss = StraightSegment(StraightSegment.Type.S, [NP(0, 0, "n1", "n3")])
        self.assertEqual(sorted(ss.names), ["n1", "n3"])

        ss.append(NP(0, 1, "n2", "n4"))
        self.assertEqual(sorted(ss.names), ["n1", "n2", "n3", "n4"])


class Decompose(unittest.TestCase):
    def test_basic(self):
        pos = [
            (1, 0),
            (1, 1),
            (2, 1),
        ]
        xs, ys = decompose_points_into_tracks(pos)
        self.assertListEqual(xs, [])
        self.assertListEqual(ys, [0])

    def test_top_right(self):
        pos = [
            (1, 0),
            (1, 1),
            (2, 1),
        ]
        xs, ys = decompose_points_into_tracks(pos, right_top=True)
        self.assertListEqual(xs, [2])
        self.assertListEqual(ys, [0, 1])

    def test_right_only(self):
        pos = [
            (2, 3),
            (3, 3),
            (3, 4),
        ]
        xs, ys = decompose_points_into_tracks(pos, right_only=True)
        self.assertListEqual(xs, [2, 3])
        self.assertListEqual(ys, [4])

    def test_right_only_assert(self):
        pos = [
            (1, 0),
            (1, 1),
            (2, 1),
        ]
        with self.assertRaises(AssertionError):
            xs, ys = decompose_points_into_tracks(pos, right_only=True)
