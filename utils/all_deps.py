import argparse
import configparser
import sys

import deps_verilog
import deps_xml

def mux_gen_check_args(makefile, out_dir):
  parser = configparser.ConfigParser()
  with open(makefile, 'r') as ff:
    vars = ff.read()
    parser.read_string('[Mux]\n' + vars)

  MUX_TYPE_KEY = 'MUX_TYPE'
  MUX_SUBCKT_KEY = 'MUX_SUBCKT'
  MUX_COMMENT_KEY = 'MUX_COMMENT'
  MUX_TYPE_VALID_KEY = 'MUX_TYPE_VALID'
  MUX_NAME_KEY = 'MUX_NAME'
  MUX_WIDTH_KEY = 'MUX_WIDTH'
  MUX_INPUT_KEY = 'MUX_INPUT'
  MUX_INPUTS_KEY = 'MUX_INPUTS'
  MUX_SPLIT_INPUTS_KEY = 'MUX_SPLIT_INPUTS'
  MUX_SELECT_KEY = 'MUX_SELECT'
  MUX_SELECTS_KEY = 'MUX_SELECTS'
  MUX_SPLIT_SELECTS_KEY = 'MUX_SPLIT_SELECTS'
  MUX_OUTPUT_KEY = 'MUX_OUTPUT'
  MUX_OUTFILE_KEY = 'MUX_OUTFILE'

  MUX_TYPE_ROUTING = 'routing'
  MUX_TYPE_LOGIC = 'logic'

  opts = parser['Mux']
  errors = []
  args = []

  print({xx: opts.get(xx) for xx in opts})
  args.append('--outdir {}'.format(out_dir))

  # type and subckt
  mux_type = opts.get(MUX_TYPE_KEY)
  subckt = opts.get(MUX_SUBCKT_KEY)
  if mux_type == MUX_TYPE_ROUTING:
    if subckt is not None:
      errors.append('Can not use {} with {} mux'.format(MUX_SUBCKT_KEY, MUX_TYPE_ROUTING))
  elif mux_type == MUX_TYPE_LOGIC:
    pass
  else:
    errors.append('{} not set'.format(MUX_TYPE_KEY))

  args.append('--type {}'.format(mux_type))
  if subckt:
    args.append('--subckt {}'.format(subckt))

  # name
  name = opts.get(MUX_NAME_KEY)
  if not name:
    errors.append('{} must be specified'.format(MUX_NAME_KEY))

  args.append('--name-mux {}'.format(name))

  # width
  width = int(opts.get(MUX_WIDTH_KEY, 0))
  if width <= 0:
    errors.append('{} must be specified'.format(MUX_WIDTH_KEY))
  args.append('--width {}'.format(width))

  # inputs/selects and spliting them
  mux_input = opts.get(MUX_INPUT_KEY)
  inputs = opts.get(MUX_INPUTS_KEY)
  split_inputs = bool(opts.get(MUX_SPLIT_INPUTS_KEY, inputs is not None))
  mux_select = opts.get(MUX_SELECT_KEY)
  selects = opts.get(MUX_SELECTS_KEY)
  split_selects = bool(opts.get(MUX_SPLIT_SELECTS_KEY, selects is not None))

  if inputs and not split_inputs:
    errors.append('{} is specified so {} must be set to True'.format(MUX_INPUTS_KEY, MUX_SPLIT_INPUTS_KEY))
  if split_inputs and mux_input:
    errors.append('{} is specified so {} must be set to False'.format(MUX_SPLIT_INPUTS_KEY, MUX_INPUT_KEY))

  if selects and not split_selects:
    errors.append('{} is specified so {} must be set to True'.format(MUX_SELECTS_KEY, MUX_SPLIT_SELECTS_KEY))
  if split_selects and mux_select:
    errors.append('{} is specified so {} must be set to False'.format(MUX_SPLIT_SELECTS_KEY, MUX_SELECT_KEY))

  if mux_input:
    args.append('--name-input {}'.format(mux_input))
  if inputs:
    args.append('--name-inputs {}'.format(inputs))
  if split_inputs:
    args.append('--split-inputs {}'.format(split_inputs))

  if mux_select:
    args.append('--name-select {}'.format(mux_select))
  if selects:
    args.append('--name-selects {}'.format(selects))
  if split_selects:
    args.append('--split-selects {}'.format(split_selects))

  # output
  output = opts.get(MUX_OUTPUT_KEY)
  if output:
    args.append('--output {}'.format(output))

  # outfile
  outfile = opts.get(MUX_OUTFILE_KEY)
  args.append('--outfilename {}'.format(outfile))

  # comment
  comment = opts.get(MUX_COMMENT_KEY)
  if comment:
    args.append('--comment "{}"'.format(comment))

  if len(errors) > 0:
    raise Exception(', '.join(errors))

  return ' '.join(args)

def mux_gen_deps(makefile):
  """generate build rule for mux generation"""
  fmt = """{outputs}: {makefile}
        @cd {dir} && {cmd} {args}
"""

  return fmt.format()

def main():
  # find mux gen
  # generate template, verilog, and xml dependency ruls


  # find and expand N templates
  # generate template, verilog, and xml dependency rules

  # find all v files
  # generate verilog and xml dependency rules
  deps_verilog.gen_deps('', '{from_file}: {on_file}\n')

  # find all xml files
  # generate xml dependency rules
  deps_xml.gen_deps('', '{from_file}: {on_file}\n')

if __name__ == "__main__":
    sys.exit(main(sys.argv))
