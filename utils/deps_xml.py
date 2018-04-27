#!/usr/bin/env python3
"""
Generate a Makefile .d fragment for the XML includes.
"""

import argparse
import logging
import os
import sys

from io import StringIO
from lxml import etree as ET

from lib.argparse_extra import ActionStoreBool
from lib.deps import add_dependency
from lib.deps import write_deps


def generate_dependency(inputfile, fmt=None):
    """
    Generate dependency for xml input file.

    Option format parameter passed to dep.add_dependency()
    """
    inputpath = os.path.abspath(inputfile.name)
    inputdir = os.path.dirname(inputpath)

    data = StringIO()
    tree = ET.parse(inputfile)
    for elem in tree.iter():
        if str(elem.tag).endswith('XInclude}include'):
            includefile_path = os.path.abspath(os.path.join(inputdir, elem.get('href')))
            logging.info('Adding dep: %s %s', inputpath, includefile_path)
            add_dependency(data, inputpath, includefile_path, fmt)

    return data

def main(argv):
    """
    main to generate xml dependencies and write to file
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "inputfile",
        type=argparse.FileType('r'),
        help="Input XML file")
    parser.add_argument(
        "--verbose",
        action=ActionStoreBool, default=(os.environ.get('V', '') == '1'),
        help="Be Verbose. Print lots of information.")


    args = parser.parse_args(argv[1:])
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    data = generate_dependency(args.inputfile)
    write_deps(args.inputfile.name, data)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
