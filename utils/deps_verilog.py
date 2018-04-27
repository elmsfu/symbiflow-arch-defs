#!/usr/bin/env python3
"""
Generate a Makefile .d fragment for the Verilog includes.
"""

import argparse
import os
import re
import sys

from io import StringIO

from lib.deps import add_dependency
from lib.deps import write_deps

def generate_dependency(inputfile, fmt=None):
    """
    Generate dependency for verilog input file.

    Option format parameter passed to dep.add_dependency()
    """
    v_include = re.compile('`include[ ]*"([^"]*)"')

    inputpath = os.path.abspath(inputfile.name)
    inputdir = os.path.dirname(inputpath)

    data = StringIO()
    matches = set(v_include.findall(inputfile.read()))
    for includefile in matches:
        includefile_path = os.path.abspath(os.path.join(inputdir, includefile))
        add_dependency(data, inputpath, includefile_path, fmt)

    return data

def main(argv):
    """
    main to write dependency to file
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "inputfile",
        type=argparse.FileType('r'),
        help="Input Verilog file")

    args = parser.parse_args(argv[1:])
    data = generate_dependency(args.inputfile)
    write_deps(args.inputfile.name, data)


if __name__ == "__main__":
    main(sys.argv)
