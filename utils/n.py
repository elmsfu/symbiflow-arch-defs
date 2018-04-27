#! /usr/bin/env python3

"""
Generate file from template file by substituting {N} with a replacemnt value
"""

import argparse
import os
import sys

from lib.asserts import assert_eq

TEMPLATE_PREFIX = 'ntemplate.'

def main(argv):
    """
    Main for template processing
    """

    parser = argparse.ArgumentParser(
        description=__doc__,
        fromfile_prefix_chars='@',
        prefix_chars='-'
    )
    parser.add_argument('replacement', help='Value to put in for placeholder')
    parser.add_argument('template', help='file to use as the template')
    parser.add_argument('out', help='file name to output template with replacements substitutes')
    args = parser.parse_args(argv[1:])

    replacement = args.replacement

    templatepath = args.template
    templatefile = os.path.basename(templatepath)
    templatedir = os.path.dirname(templatepath)
    assert templatefile.startswith(TEMPLATE_PREFIX), templatefile

    outname_template = templatefile[len(TEMPLATE_PREFIX):]
    outname_value = outname_template.replace('N', replacement)

    outpath = args.out
    outfile = os.path.basename(outpath)
    outdir = os.path.dirname(outpath)

    assert_eq(templatedir, outdir)
    assert_eq(outname_value, outfile)

    template = open(templatepath, 'r').read()
    open(outpath, 'w').write(template.format(N=replacement.upper()))
    print('Generated {} from {}'.format(os.path.relpath(outpath), templatefile))


if __name__ == '__main__':
    main(sys.argv)
