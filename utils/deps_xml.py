#!/usr/bin/env python3
"""
Generate a Makefile .d fragment for the XML includes.
"""

import argparse
import os
import re
import sys

from io import StringIO

from lib.deps import add_dependency
from lib.deps import write_deps


parser = argparse.ArgumentParser()
parser.add_argument(
    "inputfile",
    type=argparse.FileType('r'),
    help="Input XML file")


xi_include = re.compile('<xi:include[^>]*href="([^"]*)"')

def gen_deps(inputfile):
    inputpath = os.path.abspath(inputfile.name)
    inputdir = os.path.dirname(inputpath)

    data = StringIO()

    matches = set(xi_include.findall(inputfile.read()))
    for includefile in matches:
        includefile_path = os.path.abspath(os.path.join(inputdir, includefile))
        add_dependency(data, inputpath, includefile_path)

    return data

def main(argv):
    args = parser.parse_args(argv[1:])
    data = gen_deps(args.inputfile)
    write_deps(args.inputfile.name, data)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
