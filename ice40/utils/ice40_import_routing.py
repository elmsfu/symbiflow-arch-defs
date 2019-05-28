"""
Import routing from chip db files

This is a full graph import from a fully described graph.

TODO: import SDF timing
"""

import logging
from enum import Enum
from collections import namedtuple

from lib.rr_graph import Position
from lib.rr_graph import points
from lib.rr_graph import tracks
from lib.rr_graph.points import NamedPosition, NodeClassification
import lib.rr_graph.graph2
import lib.rr_graph_xml.graph2 as xml_graph2
from lib.rr_graph_xml.utils import read_xml_file

import datetime
now = datetime.datetime.now

class IceSwitchType(Enum):
    """IceBox buffers and routing switches are both generalized as VPR switches
    """
    BUFFER = 0
    ROUTING = 1


class IceSwitch(namedtuple("IceSwitch", "sw_type pos dst_net bits switch_map")):
    """Captures routing and buffer switch bits and how they connect net to another net
    """


class IceNode(namedtuple("IceNode", "node_class track_model track_ids")):
    """Represent an icestorm net as an rr_graph node classification and track model.
    The track_ids capture the ids of the VPR nodes corresponding to the track segments
    """

def parse_chip_db(chip_db):
    """Parse an icestorm chip db file
    """

    DIRECTIVES = [
        "device", "pins", "gbufin", "gbufpin", "iolatch", "ieren", "colbuf",
        "io_tile", "logic_tile", "ramb_tile", "ramt_tile", "dsp0_tile",
        "dsp1_tile", "dsp2_tile", "dsp3_tile", "ipcon_tile", "io_tile_bits",
        "logic_tile_bits", "ramb_tile_bits", "ramt_tile_bits",
        "dsp0_tile_bits", "dsp1_tile_bits", "dsp2_tile_bits", "dsp3_tile_bits",
        "ipcon_tile_bits", "extra_cell", "extra_bits", "net", "buffer",
        "routing"
    ]

    nets = {}
    switches = []

    directive = None
    for line in chip_db:
        toks = line.split("#")[0].strip().split()
        if len(toks) == 0:
            continue

        if toks[0].startswith("."):
            directive = toks[0][1:]
            if directive == "net":
                current_net = []
                nets[int(toks[1])] = current_net
            elif directive in ["buffer", "routing"]:
                pos = Position(int(toks[1]), int(toks[2]))
                current_switch = IceSwitch(
                    IceSwitchType[directive.upper()], pos, int(toks[3]), toks[4:], {}
                )
                switches.append(current_switch)
            else:
                assert directive in DIRECTIVES, "invalid directive {} in line '{}'".format(
                    directive, line
                )
        else:
            assert directive in DIRECTIVES, "invalid directive '{}'".format(
                directive
            )
            if directive == "net":
                pos = Position(int(toks[0]), int(toks[1]))
                current_net.append(NamedPosition(pos, [toks[2]]))
            elif directive in ["buffer", "routing"]:
                key = toks[0]
                assert key not in current_switch.switch_map
                current_switch.switch_map[key] = int(toks[1])
            else:
                print(
                    "skipping directive {} line '{}'".format(directive, line.strip())
                )
    return nets, switches


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="verbose output"
    )
    parser.add_argument(
        "--chip_db",
        type=argparse.FileType("r"),
        required=True,
        help="location of input chip_db file from icestorm"
    )
    parser.add_argument(
        "--read_rr_graph",
        type=argparse.FileType("r"),
        required=True,
        help="input 'virtual' rr_graph to add import routing into"
    )
    parser.add_argument(
        "--write_rr_graph",
        type=argparse.FileType("w"),
        required=True,
        help="output file to write complete routing graph"
    )

    args = parser.parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel)

    nets, switches = parse_chip_db(args.chip_db)
    input_rr_graph = read_xml_file(args.read_rr_graph.name)
    xml_graph = xml_graph2.Graph(
        input_rr_graph,
        output_file_name=args.write_rr_graph.name,
    )
    nodes, edges = import_routing(xml_graph.graph, nets, switches)

    # for node in nodes:
    #     for track in node.track_model.tracks:
    #         if track.direction == 'X':
    #             assert track.y_low == track.y_high
    #             if y_low not in x_tracks:
    #                 x_tracks[y_low] = []
    #             x_tracks[y_low].append((x_low, x_high))
    #         elif track.direction == 'Y':
    #             assert track.x_low == track.x_high
    #             if x_low not in y_tracks:
    #                 y_tracks[x_low] = []
    #             y_tracks[x_low].append((y_low, y_high))

    # x_list = []
    # y_list = []

    # x_channel_models = {}
    # y_channel_models = {}

    # for y in x_tracks:
    #     x_channel_models[y] = pool.apply_async(
    #         graph2.process_track, (x_tracks[y], )
    #     )

    # for x in y_tracks:
    #     y_channel_models[x] = pool.apply_async(
    #         graph2.process_track, (y_tracks[x], )
    #     )



    print('{} Serializing to disk.'.format(now()))

    tool_version = input_rr_graph.getroot().attrib['tool_version']
    tool_comment = input_rr_graph.getroot().attrib['tool_comment']
    xml_graph.serialize_to_xml(tool_version, tool_comment, 0)

    """
    with xml_graph:
        xml_graph.start_serialize_to_xml(
            tool_version=tool_version,
            tool_comment=tool_comment + __file__,
            channels_obj=xml_graph.graph.create_channels(0),
        )

        xml_graph.serialize_nodes(nodes)
        xml_graph.serialize_edges(edges)
    """

def create_tracks(nets):
    """Create tracks from chip_db nets

    Parameters
    ----------
    dict
        icestorm chip_db nets from parse_chip_db
        {int:  [NamedPosition,..] }

    Yields
    -------
    IceNode
        Nodes corresponding to nets
    """

    for idx, net in nets.items():
        pts = list((pos.x, pos.y) for pos in net)
        unique_pts = list(set(pts))
        _, _, model = tracks.create_track(unique_pts)

        if len(pts) < 2:
            node_class = NodeClassification.NULL
        elif len(pts) > 2:
            node_class = NodeClassification.CHANNEL
        else:
            # TODO: correctly ID point to point. Is this just if they are in the same tile or not?
            if len(unique_pts) > 1:
                node_class = NodeClassification.EDGE_WITH_MUX
            else:
                node_class = NodeClassification.EDGES_TO_CHANNEL

        yield IceNode(node_class, model, [])



def connect_tracks(graph, nets):
    """
    """
    nodes = []
    segment_id = graph.get_delayless_switch_id()

    for ice_node in create_tracks(nets):
        nodes.append(ice_node)
        model = ice_node.track_model
        for ii, track in enumerate(model.tracks):
            tid = graph.add_track(track,
                            segment_id,
                            capacity=1,
                            timing=None,
                            name=None,
                            ptc=None,
                            # direction=NodeDirection.BI_DIR
                            )

            assert tid >= 0, "track index must be a positive number"
            assert ii == len(ice_node.track_ids), "length of track_ids should match the enumerated track being added"
            # add VPR node index
            ice_node.track_ids.append(tid)

        # Create connection between tracks for IceNode/net
        for connection in model.track_connections:
            graph.add_edge(
                src_node=ice_node.track_ids[connection[0]],
                sink_node=ice_node.track_ids[connection[1]],
                switch_id=graph.delayless_switch,
            )
    return nodes

def _find_track_by_position(tracks, pos):
    return [track for track in tracks if track.x == pos.x and track.y == pos.y]

def create_edges(nets, switches, nodes):
    """Create edges from icestorm buffer and routing switches

    Edges shall be compatible with serialize_edges in rr_graph_xml

    Parameters
    ----------
    nets
        icestorm chip_db nets from parse_chip_db
    switches
        icestorm chip_db switches from parse_chip_db
    nodes
        IceNodes generated from create_nodes

    Yields
    ------
    tuple
        (src, sink, switch_id, metadata)

    """
    for switch in switches:
        dst = switch.dst_net
        pos = switch.pos
        for bits, src in switch.switch_map.items():
            dst_nodes = _find_track_by_position(nodes[dst].track_model.tracks, pos)
            src_nodes = _find_track_by_position(nodes[src].track_model.tracks, pos)
            assert len(dst_nodes) == 1 and len(src_nodes) == 1,\
                "Expected only a single dst({}) and src({}) node".format(len(dst_nodes),
                                                                         len(src_nodes))

            # TODO: get fasm feature "type_Xx_Yy.sw_type.dst.src"
            tile_type = "LOGIC"
            feature_name = "{}_X{}_Y{}.{}.{}.{}".format(tile_type, x, y, sw_type, dst_name, src_name)
            yield (
                src_node, sink_node, switch_id,
                (('fasm_features', feature_name)), )


def import_routing(graph, nets, switches):
    """Importing routing from chip_db into the a virtual routing graph

     * Create nodes for SINK/SRC and IPIN/OPINs as well as connecting edges
     * Generate tracks from nets
     * Connect tracks with shorts to represent icestorm nets
     * Generate VPR edges from icestorm buffer and routing switches
    """

    # create SINK/SRC to IPIN/OPIN is done by rr_graph xml

    # Convert to VPR nodes and shorts
    nodes = connect_tracks(graph, nets)

    edges = create_edges(nets, switches, nodes)

    """
    graph2.Channels(
        chan_width_max=chan_width_max,
        x_min=x_min,
        y_min=y_min,
        x_max=x_max,
        y_max=y_max,
        x_list=x_list,
        y_list=y_list,
    )
    """

    return nodes, edges


if __name__ == "__main__":
    main()
