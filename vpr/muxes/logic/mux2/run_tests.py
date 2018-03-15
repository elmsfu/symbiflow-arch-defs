from os.path import join, dirname
from vunit.verilog import VUnit

ui = VUnit.from_argv()

src_path = dirname(__file__)

mux2 = ui.add_library("mux2")
mux2.add_source_files(join(src_path, "*.v"))

tb_mux2 = ui.add_library("tb_mux2")
tb_mux2.add_source_files(join(src_path, "tb", "*.sv"))

ui.main()
