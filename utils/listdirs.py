#!/usr/bin/env python3

"""
Find all source files in the repo.

Excludes the files in the top level .excludes file.
"""

import fnmatch
import logging
import os.path
import sys

from lib.list_utils import normpath, make_list_argparser, parse_excludes

MYFILE = os.path.abspath(__file__)
MYDIR = os.path.dirname(MYFILE)
TOPDIR = os.path.abspath(os.path.join(MYDIR, ".."))

def listdirs(directory, exclude_patterns):
    """
    Generateor that produces directories under given directory
    """
    for path in directory:
        logging.info("Looking in: %s", path)
        for root, dirs, _ in os.walk(path, topdown=True):
            for pattern in exclude_patterns:
                # Filter out the directories we want to ignore
                for d in fnmatch.filter(dirs, pattern):
                    logging.info(" -dir %s", normpath(root, d))
                    dirs.remove(d)

            for d in dirs:
                yield os.path.normpath(os.path.join(root, d))


def main(argv):
    """
    List directories
    """
    parser = make_list_argparser(TOPDIR)
    args = parser.parse_args(argv[1:])

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    logging.info("Top level directory: %s", TOPDIR)

    exclude_patterns = args.exclude + parse_excludes(os.path.join(TOPDIR, ".excludes"))

    logging.info("Exclude patterns: %s", exclude_patterns)
    logging.info("Will search: %s", args.directory)
    for item in listdirs(args.directory, exclude_patterns):
        print(item)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
