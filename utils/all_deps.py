import argparse
import configparser
import io
import logging
import os.path
import sys

import deps_verilog
import deps_xml

import listfiles

from lib.asserts import assert_eq

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

SIMV_SUFFIX = 'sim.v'
PB_SUFFIX = 'pb_type.xml'
MODEL_SUFFIX = 'model.xml'
EXPAND_SUFFIXES = [SIMV_SUFFIX, PB_SUFFIX, MODEL_SUFFIX]

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
    args.append('--name-output {}'.format(opts[MUX_OUTPUT_KEY]))

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
  fmt = """# mux generation rul
{outputs}: {makefile} {cmd}
\t$(QUIET)cd {directory} && {cmd} {args}
MUX_OUTPUTS += {outputs}
"""
  out_dir = os.path.dirname(makefile)
  opts = mux_gen_check_args(makefile)
  outfile = opts[MUX_OUTFILE_KEY]
  outputs = [os.path.join(out_dir, outfile + '.' + suffix) for suffix in EXPAND_SUFFIXES]
  CMD = os.path.realpath('mux_gen.py')
  rule = fmt.format(target=outfile, outputs=' '.join(outputs), makefile=makefile, directory=out_dir, cmd=CMD, args=mux_gen_args(opts, out_dir))
  return rule, outputs

def gen_rules_Ntemplate(makefile, base):
  fmt = """#template expansion rule
{output}: {template} {makefile} {cmd}
\t$(QUIET){cmd} {template} {output}
N_OUTPUTS += {output}
"""
  CMD = os.path.realpath('n.py')
  in_dir = os.path.dirname(makefile)
  out_dir = os.path.dirname(makefile)
  values_str = open(makefile,'r').read().strip()
  eqn = [xx.strip() for xx in values_str.split('=')]
  assert_eq(eqn[0], 'NTEMPLATE_VALUES')
  nvalues = eqn[1].split(' ')
  logging.debug('%s-> %s', values_str, nvalues)
  res = ''
  outputs = []
  for n in nvalues:
    for ftype in EXPAND_SUFFIXES:
      template_name = base.format(N='N')
      outname = base.format(N=n)
      template = os.path.join(in_dir, 'ntemplate.{name}.{ftype}'.format(name=template_name, ftype=ftype))
      output = os.path.join(out_dir, '{name}.{ftype}'.format(name=outname, ftype=ftype))
      logging.debug('generating rule %s: %s', output, template)
      res += fmt.format(output=output, template=template, cmd=CMD, makefile=makefile)
      outputs.append(output)
  return res, outputs

def gen_rules_v2xml(makefile):
  fmt = """# verilog to xml expansion
{pb_output}: {simv} {pb_cmd} {makefile}
\t$(QUIET){pb_cmd} {extra_args} {pb_args} {simv}
{model_output}: {simv} {pb_cmd} {makefile}
\t$(QUIET){model_cmd} {extra_args} {model_args} {simv}
V2X_OUTPUTS += {pb_output} {model_output}
"""
  curdir = os.path.dirname(makefile)
  dict_args = {}
  dict_args['makefile'] = makefile
  dict_args['pb_cmd'] = os.path.realpath('vlog/vlog_to_pbtype.py')
  dict_args['model_cmd'] = os.path.realpath('vlog/vlog_to_model.py')

  simvlist = [xx for xx in os.listdir(curdir) if xx.endswith(SIMV_SUFFIX)]
  assert_eq(len(simvlist), 1)
  dict_args['simv'] = os.path.join(curdir, simvlist[0])
  base = dict_args['simv'][:-len(SIMV_SUFFIX)]

  extra_args = ''
  values_str = open(makefile,'r').read().strip()
  if len(values_str) > 0:
    eqn = [xx.strip() for xx in values_str.split('=')]
    assert_eq(eqn[0], 'TOP_MODULE')
    extra_args += '--top {}'.format(eqn[1])
  dict_args['extra_args'] = extra_args
  dict_args['pb_output'] = base + PB_SUFFIX
  dict_args['model_output'] = base + MODEL_SUFFIX
  dict_args['pb_args'] = '-o {pb_output}'.format(**dict_args)
  dict_args['model_args'] = '-o {model_output}'.format(**dict_args)

  rule = fmt.format(**dict_args)
  outputs = [dict_args['model_output'], dict_args['pb_output']]

  return rule, outputs

def clean_rules():
  clean_template = """# clean rules from Makefile.{type}
type{type}: $({type}_OUTPUTS)
type{type}-clean:
\t$(RM) $({type}_OUTPUTS)
clean: {type}-clean
.PHONY: {type} {type}-clean
"""
  res = ''
  for make_type in ['MUX', 'N', 'V2X']:
    res += clean_template.format(type=make_type)
  return res

def gen_deps(ff):
  # find mux gen
  mux_outputs = []
  muxes = [xx for xx in listfiles.listfiles([listfiles.TOPDIR],[]) if xx.endswith('Makefile.mux')]
  for mux in muxes:
    logging.debug('mux: %s', mux)
    rule, outputs = mux_gen_deps(mux)
    ff.write(rule)
    mux_outputs += outputs

  # generate template, verilog, and xml dependency ruls
  templates = [xx for xx in listfiles.listfiles([listfiles.TOPDIR],[]) if xx.endswith('Makefile.N')]
  v2xml = [xx for xx in listfiles.listfiles([listfiles.TOPDIR],[]) if xx.endswith('Makefile.v2x')]
  v2x_outputs = []
  for makefile in v2xml:
    logging.debug('generating rules for %s', makefile)
    rules, outputs = gen_rules_v2xml(makefile)
    ff.write(rules)
    v2x_outputs += outputs

  # generate and traditional are mutually exclusive
  gend = set(map(os.path.dirname, templates)).intersection(set([os.path.dirname(x) for x in muxes]))
  trad = set(map(os.path.dirname, templates)).difference(set([os.path.dirname(x) for x in muxes]))
  logging.debug('generated %s', gend)
  logging.debug('traditional %s', trad)

  # find and expand N templates
  N_outputs = []
  for dirname in trad:
    name = os.path.basename(dirname).replace('N', '{N}')
    logging.debug('expanding templates %s', name)
    rules, outputs = gen_rules_Ntemplate(os.path.join(dirname, 'Makefile.N'), name)
    ff.write(rules)
    N_outputs += outputs

  # find and expand N templates that will be generated by mux
  Ngen_outputs = []
  for dirname in gend:
    opts = mux_gen_check_args(os.path.join(dirname, 'Makefile.mux'))
    name = opts[MUX_OUTFILE_KEY].replace('N', '{N}')
    logging.debug('expanding generated templates %s', name)
    rules, outputs = gen_rules_Ntemplate(os.path.join(dirname, 'Makefile.N'), name)
    ff.write(rules)
    Ngen_outputs += outputs

  all_outputs = mux_outputs + v2x_outputs + N_outputs + Ngen_outputs
  logging.debug('.v outputs: %s', [xx for xx in all_outputs if xx.endswith(SIMV_SUFFIX)])

  # mux output .v files only depend on mux{width} which are not generated
  # N outputs sim.v depend on the template sim.v on which we can generate dependencies

  # find all v files and add Makefile.mux dirs
  # generate verilog dependency rules
  #deps_verilog.gen_deps('', '{from_file}: {on_file}\n')

  # generated xml files depend on a .v which should define the correct dependencies
  # unless there is an xml include that points to a non-generated .xml that sits next to a non-generated sim.v
  # we should check that all generated xml files only depend on other generated xml files

  # find all xml files
  # generate xml dependency rules
  #deps_xml.gen_deps('', '{from_file}: {on_file}\n')

  ff.write(clean_rules())

def main(argv):
  logging.basicConfig(level=logging.DEBUG)

  res = io.StringIO()
  gen_deps(res)
  print(res.getvalue())

if __name__ == "__main__":
    sys.exit(main(sys.argv))
