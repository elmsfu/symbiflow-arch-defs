BOARD ?= hx8k-b-env
ARCH = ice40
#YOSYS_SCRIPT  ?= synth_ice40 -nocarry; ice40_opt -unlut; abc -lut 4; opt_clean; write_blif -attr -cname -param $@
YOSYS_SCRIPT = synth_ice40 -nocarry -top hx8kdemo; ice40_opt -unlut; abc -lut 4; opt_clean; write_blif -attr -cname -param $@
SOURCE_V = \
	hx8kdemo.v \
	picosoc.v \
	picorv32.v \
	simpleuart.v \
	spimemio.v
include ../../../make/tests.mk
