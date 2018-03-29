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


parser = argparse.ArgumentParser()
parser.add_argument(
    "inputfile",
    type=argparse.FileType('r'),
    help="Input XML file")
parser.add_argument(
    "--verbose",
    action=ActionStoreBool, default=os.environ.get('V', '')=='1',
    help="Be Verbose. Print lots of information.")

def gen_deps(inputfile, fmt=None):
    inputpath = os.path.abspath(inputfile.name)
    inputdir = os.path.dirname(inputpath)

    data = StringIO()
    tree = ET.parse(inputfile)
    for el in tree.iter():
        if str(el.tag).endswith('XInclude}include'):
          includefile_path = os.path.abspath(os.path.join(inputdir, el.get('href')))
          logging.info('Adding dep: %s %s', inputpath, includefile_path)
          add_dependency(data, inputpath, includefile_path, fmt)

    return data

def main(argv):
    args = parser.parse_args(argv[1:])
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    data = gen_deps(args.inputfile)
    write_deps(args.inputfile.name, data)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
