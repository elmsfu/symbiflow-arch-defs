import unittest

from ..ice40_import_layout_from_icebox import edge_blocks, tile_type, LayoutGenerator


def edge_blocks_old(x, y, max_x, max_y):
    p = [[0, 0], [0, 0], [0, 0]]
    if x == 0:
        p[0][0] -= 1
        p[1][0] -= 1
    if x == max_x:
        p[0][0] += 1
        p[1][0] += 1
    if y == 0:
        p[1][1] -= 1
        p[2][1] -= 1
    if y == max_y:
        p[1][1] += 1
        p[2][1] += 1
    p = set(tuple(x) for x in p)
    try:
        p.remove((0, 0))
    except KeyError:
        pass
    return tuple(p)

class TestEdge(unittest.TestCase):
    def test_interior(self):
        res = edge_blocks(2, 2 , 4, 4)
        self.assertEqual(res, set())

    def test_corners(self):
        res = edge_blocks(0, 0, 4, 4)
        self.assertEqual(res, set(((-1, 0), (0, -1), (-1, -1))))
        res = edge_blocks(0, 4, 4, 4)
        self.assertEqual(res, set(((-1, 0), (0,1), (-1, 1))))
        res = edge_blocks(4, 4, 4, 4)
        self.assertEqual(res, set(((1, 0), (0, 1), (1, 1))))
        res = edge_blocks(4, 0, 4, 4)
        self.assertEqual(res, set(((1, 0), (0, -1), (1, -1))))

    def test_comp(self):
        mx = 4
        my = 6
        for x in range(mx):
            for y in range(my):
                r1 = edge_blocks(x, y, mx, my)
                r2 = edge_blocks_old(x, y, mx, my)
                self.assertEqual(r1, set(r2))

class mockIc(object):
    def __init__(self, ttype, mx, my):
        self.ttype = ttype
        self.max_x = mx
        self.max_y = my

    def tile_type(self, x, y):
        return self.ttype

class TestType(unittest.TestCase):

    def test_none_type(self):
        ic = mockIc("blah", 4, 6)
        self.assertEqual(tile_type(ic, 0, 0), (None, {}))
        self.assertEqual(tile_type(ic, 4, 0), (None, {}))
        self.assertEqual(tile_type(ic, 4, 6), (None, {}))
        self.assertEqual(tile_type(ic, 0, 6), (None, {}))

        with self.assertRaises(AssertionError):
            tile_type(ic, 1, 1)

    def test_ramb(self):
        ic = mockIc("RAMB", 4, 6)
        self.assertEqual(tile_type(ic, 1, 1), ("BLK_TL-RAM", {"fasm_prefix": "RAMB_X1_Y1"}))

    def test_ramt(self):
        ic = mockIc("RAMT", 4, 6)
        self.assertEqual(tile_type(ic, 1, 1), ([], {}))

    def test_dsp(self):
        ic = mockIc("DSP", 4, 6)
        self.assertEqual(tile_type(ic, 1, 1), ([], {}))

        ic = mockIc("DSP0", 4, 6)
        self.assertEqual(tile_type(ic, 1, 1), ("BLK_TL-DSP", {"fasm_prefix": "DSP0_X1_Y1"}))

    def test_logic(self):
        ic = mockIc("LOGIC", 4, 6)
        self.assertEqual(tile_type(ic, 1, 1), ("BLK_TL-PLB", {"fasm_prefix": "LOGIC_X1_Y1"}))

    def test_io(self):
        ic = mockIc("IO", 4, 6)
        self.assertEqual(tile_type(ic, 1, 1), ("BLK_TL-PIO", {"fasm_prefix": "IO_X1_Y1.IOB_0 IO_X1_Y1.IOB_1 "}))

class TestPinmap(unittest.TestCase):
    def test_simple(self):
        ic = mockIc("IO", 1, 3)

        pin_locs = {(1,0): {0: "100"}, (0,3): {0: "030", 1:"031"}}
        import lxml.etree as ET
        gen = LayoutGenerator("test1", ic)
        gen.generate(pin_locs)

        self.assertEqual(gen.pin_map, {(3,2,0): "100", (2,5,0): "030", (2,5,1):"031"})

        #print(ET.tostring(gen.layout_xml, pretty_print=True).decode("utf-8"))
        #self.maxDiff = None
        expected_xml = """<fixed_layout height="8" name="test1" width="6">
  <single priority="1" type="EMPTY" x="2" y="2"/>
  <single priority="1" type="EMPTY" x="2" y="0"/>
  <single priority="1" type="EMPTY" x="2" y="1"/>
  <single priority="1" type="EMPTY" x="0" y="2"/>
  <single priority="1" type="EMPTY" x="1" y="2"/>
  <single priority="1" type="EMPTY" x="0" y="0"/>
  <single priority="1" type="EMPTY" x="1" y="1"/>
  <single priority="1" type="BLK_TL-PIO" x="2" y="3">
    <metadata>
      <meta name="fasm_prefix">IO_X0_Y1.IOB_0 IO_X0_Y1.IOB_1 </meta>
    </metadata>
  </single>
  <single priority="1" type="EMPTY" x="0" y="3"/>
  <single priority="1" type="EMPTY" x="1" y="3"/>
  <single priority="1" type="BLK_TL-PIO" x="2" y="4">
    <metadata>
      <meta name="fasm_prefix">IO_X0_Y2.IOB_0 IO_X0_Y2.IOB_1 </meta>
    </metadata>
  </single>
  <single priority="1" type="EMPTY" x="0" y="4"/>
  <single priority="1" type="EMPTY" x="1" y="4"/>
  <single priority="1" type="EMPTY" x="2" y="5"/>
  <single priority="1" type="EMPTY" x="2" y="7"/>
  <single priority="1" type="EMPTY" x="2" y="6"/>
  <single priority="1" type="EMPTY" x="0" y="7"/>
  <single priority="1" type="EMPTY" x="1" y="6"/>
  <single priority="1" type="EMPTY" x="0" y="5"/>
  <single priority="1" type="EMPTY" x="1" y="5"/>
  <single priority="1" type="EMPTY" x="3" y="2"/>
  <single priority="1" type="EMPTY" x="3" y="0"/>
  <single priority="1" type="EMPTY" x="3" y="1"/>
  <single priority="1" type="EMPTY" x="5" y="2"/>
  <single priority="1" type="EMPTY" x="4" y="2"/>
  <single priority="1" type="EMPTY" x="5" y="0"/>
  <single priority="1" type="EMPTY" x="4" y="1"/>
  <single priority="1" type="BLK_TL-PIO" x="3" y="3">
    <metadata>
      <meta name="fasm_prefix">IO_X1_Y1.IOB_0 IO_X1_Y1.IOB_1 </meta>
    </metadata>
  </single>
  <single priority="1" type="EMPTY" x="5" y="3"/>
  <single priority="1" type="EMPTY" x="4" y="3"/>
  <single priority="1" type="BLK_TL-PIO" x="3" y="4">
    <metadata>
      <meta name="fasm_prefix">IO_X1_Y2.IOB_0 IO_X1_Y2.IOB_1 </meta>
    </metadata>
  </single>
  <single priority="1" type="EMPTY" x="5" y="4"/>
  <single priority="1" type="EMPTY" x="4" y="4"/>
  <single priority="1" type="EMPTY" x="3" y="5"/>
  <single priority="1" type="EMPTY" x="3" y="7"/>
  <single priority="1" type="EMPTY" x="3" y="6"/>
  <single priority="1" type="EMPTY" x="5" y="5"/>
  <single priority="1" type="EMPTY" x="4" y="5"/>
  <single priority="1" type="EMPTY" x="5" y="7"/>
  <single priority="1" type="EMPTY" x="4" y="6"/>
</fixed_layout>
"""
        self.assertEqual(ET.tostring(gen.layout_xml, pretty_print=True).decode("utf-8"), expected_xml)


if __name__ == "__main__":
    unittest.main()
