""" Assign pin directions to all tile pins.

Tile pins are defined by one of two methods:
 - Pins that are part of a direct connection (e.g. edge_with_mux) are assigned
   based on the direction relationship between the two tiles, e.g. facing each
   other.
 - Pins that connect to a routing track face a routing track.

Tile pins may end up with multiple edges if the routing tracks are formed
differently throughout the grid.

No connection database modifications are made in
prjxray_assign_tile_pin_direction.

"""
import argparse
from collections import namedtuple
import prjxray.db
import prjxray.tile
import simplejson as json
from lib.rr_graph import tracks
from lib.rr_graph.points import NodeClassification
from lib.connection_database import (
    yield_wire_info_from_node, get_track_model,
    node_to_site_pins, get_pin_name_of_wire
)
from prjxray_constant_site_pins import yield_ties_to_wire
import progressbar
import datetime

from prjxray_db_cache import DatabaseCache

now = datetime.datetime.now
DirectConnection = namedtuple(
    'DirectConnection', 'from_pin to_pin switch_name x_offset y_offset'
)


def handle_direction_connections(conn, direct_connections, edge_assignments):
    # Edges with mux should have one source tile and one destination_tile.
    # The pin from the source_tile should face the destination_tile.
    #
    # It is expected that all edges_with_mux will lies in a line (e.g. X only or
    # Y only).
    c = conn.cursor()
    for src_wire_pkey, dest_wire_pkey, pip_in_tile_pkey, switch_pkey in progressbar.progressbar(
            c.execute("""
SELECT src_wire_pkey, dest_wire_pkey, pip_in_tile_pkey, switch_pkey FROM edge_with_mux;"""
                      )):

        c2 = conn.cursor()

        # Get the node that is attached to the source.
        c2.execute(
            """
SELECT node_pkey FROM wire WHERE pkey = ?""", (src_wire_pkey, )
        )
        (src_node_pkey, ) = c2.fetchone()

        # Find the wire connected to the source.
        src_wire = list(node_to_site_pins(conn, src_node_pkey))
        assert len(src_wire) == 1
        source_wire_pkey, src_tile_pkey, src_wire_in_tile_pkey = src_wire[0]

        c2.execute(
            """
SELECT tile_type_pkey, grid_x, grid_y FROM tile WHERE pkey = ?""",
            (src_tile_pkey, )
        )
        src_tile_type_pkey, source_loc_grid_x, source_loc_grid_y = c2.fetchone(
        )

        c2.execute(
            """
SELECT name FROM tile_type WHERE pkey = ?""", (src_tile_type_pkey, )
        )
        (source_tile_type, ) = c2.fetchone()

        source_wire = get_pin_name_of_wire(conn, source_wire_pkey)

        # Get the node that is attached to the sink.
        c2.execute(
            """
SELECT node_pkey FROM wire WHERE pkey = ?""", (dest_wire_pkey, )
        )
        (dest_node_pkey, ) = c2.fetchone()

        # Find the wire connected to the sink.
        dest_wire = list(node_to_site_pins(conn, dest_node_pkey))
        assert len(dest_wire) == 1
        destination_wire_pkey, dest_tile_pkey, dest_wire_in_tile_pkey = dest_wire[
            0]

        c2.execute(
            """
SELECT tile_type_pkey, grid_x, grid_y FROM tile WHERE pkey = ?;""",
            (dest_tile_pkey, )
        )
        dest_tile_type_pkey, destination_loc_grid_x, destination_loc_grid_y = c2.fetchone(
        )

        c2.execute(
            """
SELECT name FROM tile_type WHERE pkey = ?""", (dest_tile_type_pkey, )
        )
        (destination_tile_type, ) = c2.fetchone()

        destination_wire = get_pin_name_of_wire(conn, destination_wire_pkey)

        c2.execute(
            "SELECT name FROM switch WHERE pkey = ?"
            "", (switch_pkey, )
        )
        switch_name = c2.fetchone()[0]

        direct_connections.add(
            DirectConnection(
                from_pin='{}.{}'.format(source_tile_type, source_wire),
                to_pin='{}.{}'.format(destination_tile_type, destination_wire),
                switch_name=switch_name,
                x_offset=destination_loc_grid_x - source_loc_grid_x,
                y_offset=destination_loc_grid_y - source_loc_grid_y,
            )
        )

        if destination_loc_grid_x == source_loc_grid_x:
            if destination_loc_grid_y > source_loc_grid_y:
                source_dir = tracks.Direction.TOP
                destination_dir = tracks.Direction.BOTTOM
            else:
                source_dir = tracks.Direction.BOTTOM
                destination_dir = tracks.Direction.TOP
        else:
            if destination_loc_grid_x > source_loc_grid_x:
                source_dir = tracks.Direction.RIGHT
                destination_dir = tracks.Direction.LEFT
            else:
                source_dir = tracks.Direction.LEFT
                destination_dir = tracks.Direction.RIGHT

        edge_assignments[(source_tile_type,
                          source_wire)].append((source_dir, ))
        edge_assignments[(destination_tile_type,
                          destination_wire)].append((destination_dir, ))


def handle_edges_to_channels(
        conn, null_tile_wires, edge_assignments, channel_wires_to_tracks
):
    c = conn.cursor()

    c.execute(
        """
SELECT vcc_track_pkey, gnd_track_pkey FROM constant_sources;
    """
    )
    vcc_track_pkey, gnd_track_pkey = c.fetchone()
    const_tracks = {
        0: gnd_track_pkey,
        1: vcc_track_pkey,
    }

    for node_pkey, classification in progressbar.progressbar(c.execute("""
SELECT pkey, classification FROM node WHERE classification != ?;
""", (NodeClassification.CHANNEL.value, ))):
        reason = NodeClassification(classification)

        if reason == NodeClassification.NULL:
            for (tile_type, wire) in yield_wire_info_from_node(conn,
                                                               node_pkey):
                null_tile_wires.add((tile_type, wire))

        if reason != NodeClassification.EDGES_TO_CHANNEL:
            continue

        c2 = conn.cursor()
        for wire_pkey, tile_pkey, wire_in_tile_pkey in c2.execute("""
SELECT
    pkey, tile_pkey, wire_in_tile_pkey
FROM
    wire
WHERE
    node_pkey = ?;
    """, (node_pkey, )):
            c3 = conn.cursor()
            c3.execute(
                """
SELECT grid_x, grid_y FROM tile WHERE pkey = ?;""", (tile_pkey, )
            )
            (grid_x, grid_y) = c3.fetchone()

            c3.execute(
                """
SELECT
  name
FROM
  tile_type
WHERE
  pkey = (
    SELECT
      tile_type_pkey
    FROM
      tile
    WHERE
      pkey = ?
  );
                """, (tile_pkey, )
            )
            (tile_type, ) = c3.fetchone()

            wire = get_pin_name_of_wire(conn, wire_pkey)
            if wire is None:
                # This node has no site pin, don't need to assign pin direction.
                continue

            for pip_pkey, pip, src_wire_in_tile_pkey, dest_wire_in_tile_pkey in c3.execute(
                    """
SELECT
  pkey,
  name,
  src_wire_in_tile_pkey,
  dest_wire_in_tile_pkey
FROM
  pip_in_tile
WHERE
  is_directional = 1 AND is_pseudo = 0 AND (
  src_wire_in_tile_pkey = ?
  OR dest_wire_in_tile_pkey = ?);""", (wire_in_tile_pkey, wire_in_tile_pkey)):
                assert (
                    src_wire_in_tile_pkey == wire_in_tile_pkey
                    or dest_wire_in_tile_pkey == wire_in_tile_pkey
                ), pip

                if src_wire_in_tile_pkey == wire_in_tile_pkey:
                    other_wire_in_tile_pkey = dest_wire_in_tile_pkey
                else:
                    other_wire_in_tile_pkey = src_wire_in_tile_pkey

                # Need to walk from the wire_in_tile table, to the wire table,
                # to the node table and get track_pkey.
                # other_wire_in_tile_pkey -> wire pkey -> node_pkey -> track_pkey
                c4 = conn.cursor()
                c4.execute(
                    """
SELECT
  track_pkey,
  classification
FROM
  node
WHERE
  pkey = (
    SELECT
      node_pkey
    FROM
      wire
    WHERE
      tile_pkey = ?
      AND wire_in_tile_pkey = ?
  );""", (tile_pkey, other_wire_in_tile_pkey)
                )
                result = c4.fetchone()
                assert result is not None, (
                    wire_pkey, pip_pkey, tile_pkey, wire_in_tile_pkey,
                    other_wire_in_tile_pkey
                )
                (track_pkey, classification) = result

                # Some pips do connect to a track at all, e.g. null node
                if track_pkey is None:
                    # TODO: Handle weird connections.
                    #other_node_class = NodeClassification(classification)
                    #assert other_node_class == NodeClassification.NULL, (
                    #        node_pkey, pip_pkey, pip, other_node_class)
                    continue

                tracks_model = channel_wires_to_tracks[track_pkey]
                available_pins = set(
                    pin_dir for _, pin_dir in tracks_model.
                    get_tracks_for_wire_at_coord((grid_x, grid_y))
                )
                edge_assignments[(tile_type, wire)].append(available_pins)

                for constant in yield_ties_to_wire(wire):
                    tracks_model = channel_wires_to_tracks[
                        const_tracks[constant]]
                    available_pins = set(
                        pin_dir for _, pin_dir in tracks_model.
                        get_tracks_for_wire_at_coord((grid_x, grid_y))
                    )
                    edge_assignments[(tile_type, wire)].append(available_pins)


def initialize_edge_assignments(db, conn):
    """ Create initial edge_assignments map. """
    c = conn.cursor()
    c2 = conn.cursor()

    edge_assignments = {}
    wires_in_tile_types = set()

    # First find out which tile types were split during VPR grid formation.
    # These tile types should not get edge assignments directly, instead
    # their sites will get edge assignements.
    sites_as_tiles = set()
    split_tile_types = set()
    for site_pkey, tile_type_pkey in c.execute("""
        SELECT site_pkey, tile_type_pkey FROM site_as_tile;
        """):
        c2.execute(
            "SELECT name FROM tile_type WHERE pkey = ?", (tile_type_pkey, )
        )
        split_tile_types.add(c2.fetchone()[0])

        c2.execute(
            """
SELECT name FROM site_type WHERE pkey = (
    SELECT site_type_pkey FROM site WHERE pkey = ?
    );""", (site_pkey, )
        )
        site_type_name = c2.fetchone()[0]
        sites_as_tiles.add(site_type_name)

    # Initialize edge assignments for split tiles
    for site_type in sites_as_tiles:
        site_obj = db.get_site_type(site_type)
        for site_pin in site_obj.get_site_pins():
            key = (site_type, site_pin)
            assert key not in edge_assignments, key

            edge_assignments[key] = []

    for tile_type in db.get_tile_types():
        # Skip tile types that are split tiles
        if tile_type in split_tile_types:
            continue

        type_obj = db.get_tile_type(tile_type)

        for wire in type_obj.get_wires():
            wires_in_tile_types.add((tile_type, wire))

        for site in type_obj.get_sites():
            for site_pin in site.site_pins:
                if site_pin.wire is None:
                    continue

                key = (tile_type, site_pin.wire)
                assert key not in edge_assignments, key
                edge_assignments[key] = []

    return edge_assignments, wires_in_tile_types


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--db_root', help='Project X-Ray Database', required=True
    )
    parser.add_argument(
        '--connection_database',
        help='Database of fabric connectivity',
        required=True
    )
    parser.add_argument(
        '--pin_assignments',
        help=
        'Output JSON assigning pins to tile types and direction connections',
        required=True
    )

    args = parser.parse_args()

    db = prjxray.db.Database(args.db_root)

    edge_assignments = {}

    with DatabaseCache(args.connection_database, read_only=True) as conn:
        c = conn.cursor()

        edge_assignments, wires_in_tile_types = initialize_edge_assignments(
            db, conn
        )

        direct_connections = set()
        print('{} Processing direct connections.'.format(now()))
        handle_direction_connections(
            conn, direct_connections, edge_assignments
        )

        wires_not_in_channels = {}
        c = conn.cursor()
        print('{} Processing non-channel nodes.'.format(now()))
        for node_pkey, classification in progressbar.progressbar(c.execute("""
    SELECT pkey, classification FROM node WHERE classification != ?;
    """, (NodeClassification.CHANNEL.value, ))):
            reason = NodeClassification(classification)

            for (tile_type, wire) in yield_wire_info_from_node(conn,
                                                               node_pkey):
                key = (tile_type, wire)

                # Sometimes nodes in particular tile instances are disconnected,
                # disregard classification changes if this is the case.
                if reason != NodeClassification.NULL:
                    if key not in wires_not_in_channels:
                        wires_not_in_channels[key] = reason
                    else:
                        other_reason = wires_not_in_channels[key]
                        assert reason == other_reason, (
                            tile_type, wire, reason, other_reason
                        )

                if key in wires_in_tile_types:
                    wires_in_tile_types.remove(key)

        # List of nodes that are channels.
        channel_nodes = []

        # Map of (tile, wire) to track.  This will be used to find channels for pips
        # that come from EDGES_TO_CHANNEL.
        channel_wires_to_tracks = {}

        # Generate track models and verify that wires are either in a channel
        # or not in a channel.
        print('{} Creating models from tracks.'.format(now()))
        for node_pkey, track_pkey in progressbar.progressbar(c.execute("""
    SELECT pkey, track_pkey FROM node WHERE classification = ?;
    """, (NodeClassification.CHANNEL.value, ))):
            assert track_pkey is not None

            tracks_model, _ = get_track_model(conn, track_pkey)
            channel_nodes.append(tracks_model)
            channel_wires_to_tracks[track_pkey] = tracks_model

            for (tile_type, wire) in yield_wire_info_from_node(conn,
                                                               node_pkey):
                key = (tile_type, wire)
                # Make sure all wires in channels always are in channels
                assert key not in wires_not_in_channels

                if key in wires_in_tile_types:
                    wires_in_tile_types.remove(key)

        # Make sure all wires appear to have been assigned.
        assert len(wires_in_tile_types) == 0

        # Verify that all tracks are sane.
        for node in channel_nodes:
            node.verify_tracks()

        null_tile_wires = set()

        # Verify that all nodes that are classified as edges to channels have at
        # least one site, and at least one live connection to a channel.
        #
        # If no live connections from the node are present, this node should've
        # been marked as NULL during channel formation.
        print('{} Handling edges to channels.'.format(now()))
        handle_edges_to_channels(
            conn, null_tile_wires, edge_assignments, channel_wires_to_tracks
        )

        print('{} Processing edge assignments.'.format(now()))
        final_edge_assignments = {}
        for key, available_pins in progressbar.progressbar(
                edge_assignments.items()):
            (tile_type, wire) = key
            if len(available_pins) == 0:
                if (tile_type, wire) not in null_tile_wires:
                    # TODO: Figure out what is going on with these wires.  Appear to
                    # tile internal connections sometimes?
                    print((tile_type, wire))

                final_edge_assignments[key] = [tracks.Direction.RIGHT]
                continue

            pins = set(available_pins[0])
            for p in available_pins[1:]:
                pins &= set(p)

            if len(pins) > 0:
                final_edge_assignments[key] = [list(pins)[0]]
            else:
                # More than 2 pins are required, final the minimal number of pins
                pins = set()
                for p in available_pins:
                    pins |= set(p)

                while len(pins) > 2:
                    pins = list(pins)

                    prev_len = len(pins)

                    for idx in range(len(pins)):
                        pins_subset = list(pins)
                        del pins_subset[idx]

                        pins_subset = set(pins_subset)

                        bad_subset = False
                        for p in available_pins:
                            if len(pins_subset & set(p)) == 0:
                                bad_subset = True
                                break

                        if not bad_subset:
                            pins = list(pins_subset)
                            break

                    # Failed to remove any pins, stop.
                    if len(pins) == prev_len:
                        break

                final_edge_assignments[key] = pins

        for key, available_pins in edge_assignments.items():
            (tile_type, wire) = key
            pins = set(final_edge_assignments[key])

            for required_pins in available_pins:
                assert len(pins & set(required_pins)) > 0, (
                    tile_type, wire, pins, required_pins
                )

        pin_directions = {}
        for key, pins in progressbar.progressbar(
                final_edge_assignments.items()):
            (tile_type, wire) = key
            if tile_type not in pin_directions:
                pin_directions[tile_type] = {}

            pin_directions[tile_type][wire] = [pin._name_ for pin in pins]

        with open(args.pin_assignments, 'w') as f:
            json.dump(
                {
                    'pin_directions':
                        pin_directions,
                    'direct_connections':
                        [d._asdict() for d in direct_connections],
                },
                f,
                indent=2
            )

        print(
            '{} Flushing database back to file "{}"'.format(
                now(), args.connection_database
            )
        )


if __name__ == '__main__':
    main()
