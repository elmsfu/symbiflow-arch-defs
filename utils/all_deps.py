import argparse
import configparser
import io
import logging
import os.path
import sys

import deps_verilog
import deps_xml

import listfiles

MUX_TYPE_KEY = 'MUX_TYPE'
MUX_SUBCKT_KEY = 'MUX_SUBCKT'
MUX_COMMENT_KEY = 'MUX_COMMENT'
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

mux_gen_keys = [MUX_TYPE_KEY,
                MUX_SUBCKT_KEY,
                MUX_COMMENT_KEY,
                MUX_NAME_KEY,
                MUX_WIDTH_KEY,
                MUX_INPUT_KEY,
                MUX_INPUTS_KEY,
                MUX_SPLIT_INPUTS_KEY,
                MUX_SELECT_KEY,
                MUX_SELECTS_KEY,
                MUX_SPLIT_SELECTS_KEY,
                MUX_OUTPUT_KEY,
                MUX_OUTFILE_KEY,]

MUX_TYPE_ROUTING = 'routing'
MUX_TYPE_LOGIC = 'logic'

def mux_gen_args(opts, out_dir):
  args = []
  args.append('--outdir {}'.format(out_dir))

  args.append('--type {}'.format(opts[MUX_TYPE_KEY]))
  if opts[MUX_SUBCKT_KEY]:
    args.append('--subckt {}'.format(opts[MUX_SUBCKT_KEY]))
  args.append('--name-mux {}'.format(opts[MUX_NAME_KEY]))
  args.append('--width {}'.format(opts[MUX_WIDTH_KEY]))

  if opts[MUX_INPUT_KEY]:
    args.append('--name-input {}'.format(opts[MUX_INPUT_KEY]))
  if opts[MUX_INPUTS_KEY]:
    args.append('--name-inputs {}'.format(opts[MUX_INPUTS_KEY]))
  if opts[MUX_SPLIT_INPUTS_KEY]:
    args.append('--split-inputs {}'.format(opts[MUX_SPLIT_INPUTS_KEY]))

  if opts[MUX_SELECT_KEY]:
    args.append('--name-select {}'.format(opts[MUX_SELECT_KEY]))
  if opts[MUX_SELECTS_KEY]:
    args.append('--name-selects {}'.format(opts[MUX_SELECTS_KEY]))
  if opts[MUX_SPLIT_SELECTS_KEY]:
    args.append('--split-selects {}'.format(opts[MUX_SPLIT_SELECTS_KEY]))

  if opts[MUX_OUTPUT_KEY]:
    args.append('--output {}'.format(opts[MUX_OUTPUT_KEY]))

  args.append('--outfilename {}'.format(opts[MUX_OUTFILE_KEY]))
  if opts[MUX_COMMENT_KEY]:
    args.append('--comment "{}"'.format(opts[MUX_COMMENT_KEY]))

  return ' '.join(args)


def mux_gen_check_args(makefile):
  parser = configparser.ConfigParser()
  with open(makefile, 'r') as ff:
    vars = ff.read()
    parser.read_string('[Mux]\n' + vars)

  muxargs = parser['Mux']
  errors = []
  opts = {key: muxargs.get(key) for key in mux_gen_keys}

  # type and subckt
  if opts[MUX_TYPE_KEY] == MUX_TYPE_ROUTING:
    if opts[MUX_SUBCKT_KEY] is not None:
      errors.append('Can not use {} with {} mux'.format(MUX_SUBCKT_KEY, MUX_TYPE_ROUTING))
  elif opts[MUX_TYPE_KEY] == MUX_TYPE_LOGIC:
    pass
  else:
    errors.append('{} not set'.format(MUX_TYPE_KEY))

  if not opts[MUX_NAME_KEY]:
    errors.append('{} must be specified'.format(MUX_NAME_KEY))

  # update width as int and check
  opts[MUX_WIDTH_KEY] = int(muxargs.get(MUX_WIDTH_KEY, 0))
  if opts[MUX_WIDTH_KEY] <= 0:
    errors.append('{} must be specified'.format(MUX_WIDTH_KEY))

  # inputs/selects and spliting them
  mux_input = muxargs.get(MUX_INPUT_KEY)
  inputs = muxargs.get(MUX_INPUTS_KEY)
  split_inputs = bool(muxargs.get(MUX_SPLIT_INPUTS_KEY, inputs is not None))
  mux_select = muxargs.get(MUX_SELECT_KEY)
  selects = muxargs.get(MUX_SELECTS_KEY)
  split_selects = bool(muxargs.get(MUX_SPLIT_SELECTS_KEY, selects is not None))

  if inputs and not split_inputs:
    errors.append('{} is specified so {} must be set to True'.format(MUX_INPUTS_KEY, MUX_SPLIT_INPUTS_KEY))
  if split_inputs and mux_input:
    errors.append('{} is specified so {} must be set to False'.format(MUX_SPLIT_INPUTS_KEY, MUX_INPUT_KEY))
  if inputs and len(inputs.split(',')) != opts[MUX_WIDTH_KEY]:
    errors.append('number of inputs doesn\'t match width'.format(inputs, opts[MUX_WIDTH_KEY]))

  if selects and not split_selects:
    errors.append('{} is specified so {} must be set to True'.format(MUX_SELECTS_KEY, MUX_SPLIT_SELECTS_KEY))
  if split_selects and mux_select:
    errors.append('{} is specified so {} must be set to False'.format(MUX_SPLIT_SELECTS_KEY, MUX_SELECT_KEY))

  # update values
  opts[MUX_SPLIT_INPUTS_KEY]  = split_inputs
  opts[MUX_SPLIT_SELECTS_KEY]  = split_selects

  if len(errors) > 0:
    raise Exception(', '.join(errors))

  return opts

def mux_gen_deps(makefile):
  """generate build rule for mux generation"""
  fmt = """{outputs}: {makefile}
\t@cd {directory} && {cmd} {args}
{target}: {outputs}
{target}-clean:
\t$(RM) {outputs}
.PHONY: {target} {target}-clean
clean: {target}-clean
"""
  out_dir = os.path.dirname(makefile)
  opts = mux_gen_check_args(makefile)
  outfile = opts[MUX_OUTFILE_KEY]
  outputs = '{base}.model.xml {base}.pb_type.xml {base}.sim.v'.format(base=outfile)
  CMD=os.path.realpath('mux_gen.py')
  return fmt.format(target=outfile, outputs=outputs, makefile=makefile, directory=out_dir, cmd=CMD, args=mux_gen_args(opts, out_dir))

def gen_deps(ff):
  # find mux gen
  muxes = [xx for xx in listfiles.listfiles([listfiles.TOPDIR],[]) if xx.endswith('Makefile.mux')]
  for mux in muxes:
    logging.debug('mux: %s', mux)
    opts = mux_gen_check_args(mux)
    logging.debug('opts %s', opts[MUX_OUTFILE_KEY])
    ff.write(mux_gen_deps(mux))
  # generate template, verilog, and xml dependency ruls

  templates = [xx for xx in listfiles.listfiles(['..'],[]) if xx.endswith('Makefile.N')]
  # find and expand N templates
  # generate template, verilog, and xml dependency rules

  # find all v files
  # generate verilog and xml dependency rules
  #deps_verilog.gen_deps('', '{from_file}: {on_file}\n')

  # find all xml files
  # generate xml dependency rules
  #deps_xml.gen_deps('', '{from_file}: {on_file}\n')

def main(argv):
  logging.basicConfig(level=logging.DEBUG)

  res = io.StringIO()
  gen_deps(res)
  print(res.getvalue())

if __name__ == "__main__":
    sys.exit(main(sys.argv))
