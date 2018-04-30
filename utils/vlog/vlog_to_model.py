#!/usr/bin/env python3
"""
Convert a Verilog simulation model to a VPR `model.xml`

The following Verilog attributes are considered on ports:
    - `(* CLOCK *)` : force a given port to be a clock

    - `(* ASSOC_CLOCK="RDCLK" *)` : force a port's associated clock to a given value

The following Verilog attributes are considered on modules:
    - `(* MODEL_NAME="model" *)` : override the name used for <model> and for
    ".subckt name" in the BLIF model. Mostly intended for use with w.py, when several
    different pb_types implement the same model.

    - `(* CLASS="lut|routing|mux|flipflop|mem" *)` : specify the class of an given
    instance. A model will not be generated for the `lut`, `routing` or `flipflop`
    class.
"""

import argparse
import logging
import os
import re
import sys
import xmlinc

import lxml.etree as ET

import yosys.run
from yosys.json import YosysJSON

def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument(
        'infiles',
        metavar='input.v', type=str, nargs='+',
        help="""\
        One or more Verilog input files, that will be passed to Yosys internally.
        They should be enough to generate a flattened representation of the model,
        so that paths through the model can be determined.
        """)
    parser.add_argument(
        '--top',
        help="""\
        Top level module, will usually be automatically determined from the file name
        %.sim.v
        """)
    parser.add_argument(
        '-o',
        help="""\
        Output filename, default 'model.xml'
        """)

    args = parser.parse_args(argv[1:])

    iname = os.path.basename(args.infiles[0])

    outfile = "model.xml"
    if "o" in args and args.o is not None:
        outfile = args.o

    aig_json = yosys.run.vlog_to_json(args.infiles, flatten=True, aig=True)

    if args.top is not None:
        yj = YosysJSON(aig_json, args.top)
        top = yj.top
    else:
        wm = re.match(r"([A-Za-z0-9_]+)\.sim\.v", iname)
        if wm:
            top = wm.group(1).upper()
        else:
            logging.critical("File name not of format %%.sim.v (%s), cannot detect top level." +
                             " Manually specify the top level module using --top", iname)
        yj = YosysJSON(aig_json, top)

    if top is None:
        logging.critical("More than one module in design, cannot detect top level." +
                         " Manually specify the top level module using --top")

    tmod = yj.top_module
    models_xml = ET.Element("models", nsmap={'xi': xmlinc.xi_url})

    inc_re = re.compile(r'^\s*`include\s+"([^"]+)"')

    deps_files = set()
    # XML dependencies need to correspond 1:1 with Verilog includes, so we have
    # to do this manually rather than using Yosys
    with open(args.infiles[0], 'r') as f:
        for line in f:
            im = inc_re.match(line)
            if not im:
                continue
            deps_files.add(im.group(1))

    if len(deps_files) > 0:
        # Has dependencies, not a leaf model
        for df in sorted(deps_files):
            abs_base = os.path.dirname(os.path.abspath(args.infiles[0]))
            abs_dep = os.path.normpath(os.path.join(abs_base, df))
            module_path = os.path.dirname(abs_dep)
            module_basename = os.path.basename(abs_dep)
            wm = re.match(r"([A-Za-z0-9_]+)\.sim\.v", module_basename)
            if wm:
                model_path = "{}/{}.model.xml" .format(module_path, wm.group(1).lower())
            else:
                logging.critical("included Verilog file name %s does not follow pattern %%.sim.v",
                                 module_basename)
            xmlinc.include_xml(parent=models_xml,
                               href=model_path,
                               outfile=outfile,
                               xptr="xpointer(models/child::node())")
    else:
        # Is a leaf model
        topname = tmod.attr("MODEL_NAME", top)
        modclass = tmod.attr("CLASS", "")
        if modclass not in ("lut", "routing", "flipflop"):
            model_xml = ET.SubElement(models_xml, "model", {'name': topname})
            ports = tmod.ports

            inports_xml = ET.SubElement(model_xml, "input_ports")
            outports_xml = ET.SubElement(model_xml, "output_ports")

            clocks = yosys.run.list_clocks(args.infiles, top)
            clk_sigs = dict()
            for clk in clocks:
                clk_sigs[clk] = yosys.run.get_clock_assoc_signals(args.infiles, top, clk)

            for name, _, iodir in ports:
                attrs = dict(name=name)
                sinks = yosys.run.get_combinational_sinks(args.infiles, top, name)
                if len(sinks) > 0 and iodir == "input":
                    attrs["combinational_sink_ports"] = " ".join(sinks)
                if name in clocks:
                    attrs["is_clock"] = "1"
                for clk in clocks:
                    if name in clk_sigs[clk]:
                        attrs["clock"] = clk
                if iodir == "input":
                    ET.SubElement(inports_xml, "port", attrs)
                elif iodir == "output":
                    ET.SubElement(outports_xml, "port", attrs)
                else:
                    assert False, "bidirectional ports not permitted in VPR models"


    if len(models_xml) == 0:
        models_xml.insert(0, ET.Comment("this file is intentionally left blank"))

    with open(outfile, 'w') as f:
        f.write(ET.tostring(models_xml, pretty_print=True).decode('utf-8'))
    print("Generated {} from {}".format(outfile, iname))


if __name__ == '__main__':
    main(sys.argv)
