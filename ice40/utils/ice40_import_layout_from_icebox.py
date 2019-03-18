#!/usr/bin/env python3

import sys

try:
    import lxml.etree as ET
except ModuleNotFoundError:
    print("layout generation not supported due to lxml missing", file=sys.stderr)


# FIXME: Move this into icebox
PARTS = [
    # LP Series (Low Power)
    "lp384",
    "lp1k",
    "lp8k",
    # Unsupported: "lp640", "lp4k" (alias for lp8k),

    # LM Series (Low Power, Embedded IP)
    # Unsupported: "lm1k", "lm2k",
    "lm4k",

    # HX Series (High Performance)
    "hx1k",
    "hx8k",
    # Unsupported: "hx4k" (alias for hx8k)

    # iCE40 UltraLite
    # Unsupported: "ul640", "ul1k",

    # iCE40 Ultra
    # Unsupported: "ice5lp1k", "ice5lp2k", "ice5lp4k",

    # iCE40 UltraPLus
    # Unsupported: "up3k",
    "up5k",
]


class SkipTile(object):
    pass

def versions(part):
    return [p for p in PARTS if p.endswith(part)]

def vpr_pos(x, y):
    return x + 2, y + 2


def get_corner_tiles(max_x, max_y):
    corner_tiles = set()
    for x in (0, max_x):
        for y in (0, max_y):
            corner_tiles.add((x, y))
    return corner_tiles



def edge_blocks(x, y, max_x, max_y):
    res = []
    if x == 0:
        res.append((-1, 0))
    if x == max_x:
        res.append((1, 0))
    if y == 0:
        res.append((0, -1))
    if y == max_y:
        res.append((0, 1))
    if len(res) > 1:
        res.append((res[0][0], res[1][1]))
    return set(res)


def tile_type(ic, x, y):
    tt = ic.tile_type(x, y)

    if tt == "IO":
        fasm_prefix = ""
        for z in range(2):
            fasm_prefix += "{}_X{:d}_Y{:d}.IOB_{:d} ".format(tt, x, y, z)
    else:
        fasm_prefix = "{}_X{:d}_Y{:d}".format(tt, x, y)

    metadata = {"fasm_prefix": fasm_prefix}
    if (x, y) in get_corner_tiles(ic.max_x, ic.max_y):
        return None, {}
    if tt == "RAMB":
        return "BLK_TL-RAM", metadata
    if tt == "RAMT":
        return SkipTile, {}
    if tt.startswith("DSP"):
        if tt.endswith("0"):
            return "BLK_TL-DSP", metadata
        return SkipTile, {}
    if tt == "IO":
        return "BLK_TL-PIO", metadata
    if tt == "LOGIC":
        return "BLK_TL-PLB", metadata
    if tt == "IPCON":
        return None, {}
    assert False, tt

def tryint(x):
    try:
        return int(x)
    except ValueError:
        return x


class LayoutGenerator(object):
    def __init__(self, name, ic):
        # check it ET was imported
        assert "ET" in globals(), "lxml not imported, generation not supported"

        self.ic = ic

        self.layout_xml = ET.Element(
            "fixed_layout", {
                'name': name,
                'width': str(ic.max_x + 4 + 1),
                'height': str(ic.max_y + 4 + 1),
            })
        self.pin_map = {}


    def add_metadata(self, parent_xml, key, value):
        metadata_xml = parent_xml.find("./metadata")
        if metadata_xml is None:
            metadata_xml = ET.SubElement(parent_xml, "metadata")

        m = ET.SubElement(metadata_xml, "meta", {"name": str(key)})
        m.text = str(value)


    def add_tile(self, type_name, pos):
        return ET.SubElement(self.layout_xml, "single", {
            'type': type_name,
            'x': str(pos[0]),
            'y': str(pos[1]),
            'priority': '1'
        })

    def generate(self, pin_locs):
        for x in range(0, self.ic.max_x + 1):
            for y in range(0, self.ic.max_y + 1):
                ipos = (x, y)
                vpos = vpr_pos(*ipos)

                tt, metadata = tile_type(self.ic, *ipos)
                if tt is None:
                    tile_xml = self.add_tile("EMPTY", vpos)
                elif tt is not SkipTile:
                    tile_xml = self.add_tile(tt, vpos)

                for k, v in metadata.items():
                    self.add_metadata(tile_xml, k, str(v))

                # add extra two empty tiles around perimeter for actual pins
                eposes = edge_blocks(x, y, self.ic.max_x, self.ic.max_y)
                for e in eposes:
                    self.add_tile("EMPTY",
                        (vpos[0] + e[0] * 2, vpos[1] + e[1] * 2))

                    pin_pos = vpos[0] + e[0] * 1, vpos[1] + e[1] * 1
                    if ipos in pin_locs:
                        self.add_tile("EMPTY", pin_pos)
                        for z, name in pin_locs[ipos].items():
                            self.pin_map[(*vpos, z)] = name
                    else:
                        self.add_tile("EMPTY", pin_pos)

    def write_xml(self, stream):
        stream.write(ET.tostring(self.layout_xml, pretty_print=True))

    def write_pinmap(self, stream):
        lines = [(tryint(v), *k) for k, v in self.pin_map.items()]
        stream.write("name,x,y,z\n".encode("utf-8"))
        for i in sorted(lines):
            stream.write("{},{},{},{}\n".format(*i).encode("utf-8"))


def generate_layouts():
    import icebox

    for name, pins in icebox.pinloc_db.items():
        part, package = name.split('-')
        if ':' in package:
            continue

        pin_locs = {}
        for name, x, y, z in pins:
            if (x, y) not in pin_locs:
                pin_locs[(x, y)] = {}
            pin_locs[(x, y)][z] = name

        ic = icebox.iceconfig()
        getattr(ic, "setup_empty_{}".format(part))()

        for version in versions(part):
            layout_gen = LayoutGenerator('{}-{}'.format(version, package), ic)

            layout_gen.generate(pin_locs)

            with open("{}.{}.fixed_layout.xml".format(version, package), "wb+") as f:
                layout_gen.write_xml(f)

            with open("{}.{}.pinmap.csv".format(version, package), "wb+") as f:
                layout_gen.write_pinmap(f)


def list_layouts():
    import icebox

    for name, pins in icebox.pinloc_db.items():
        part, package = name.split('-')
        if ':' in package:
            continue
        for v in versions(part):
            device = "{}.{}".format(v, package)
            print(device)

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Get Icebox layout information or generate layouts"
        )
    cmd_group = parser.add_mutually_exclusive_group(required=True)

    cmd_group.add_argument("--list", help="list available layouts to stdout", action='store_true')
    if "ET" in globals():
        cmd_group.add_argument("--gen", help="generate <version>.<package>.fixed_layout.xml and <version>.<package>.pinmap.csv for all available layouts", action='store_true')

    args = parser.parse_args()
    if args.list:
        list_layouts()

    if getattr(args, "gen", False):
        generate_layouts()


if __name__ == '__main__':
    main()
