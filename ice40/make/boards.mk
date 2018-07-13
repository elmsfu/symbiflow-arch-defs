# Lattice iCEstick
# http://www.latticesemi.com/icestick
# ---------------------------------------------
ifeq ($(BOARD),icestick)
DEVICE=hx1k
PACKAGE=tq144
PROG_TOOL=$(ICEPROG_TOOL)
endif

# Lattice iCEblink40-LP1K Evaluation Kit
# **HX** version is different!
# ---------------------------------------------
ifeq ($(BOARD),iceblink40-lp1k)
DEVICE=lp1k
PACKAGE=qn84

ifeq ($(PROG_TOOL),)
PROG_TOOL ?= $(CONDA_DIR)/bin/iCEburn
PROG_CMD ?= $(PROG_TOOL) -ew

$(PROG_TOOL):
	pip install -e git+https://github.com/davidcarne/iceBurn.git#egg=iceBurn

endif
endif

# TinyFPGA B2
# iCE40-LP8K-CM81
# ---------------------------------------------
ifeq ($(BOARD),tinyfpga-b2)
DEVICE=hx8k
PACKAGE=cm81

ifeq ($(PROG_TOOL),)
PROG_TOOL=$(CONDA_DIR)/bin/tinyfpgab
PROG_CMD ?= $(PROG_TOOL) --program

$(PROG_TOOL):
	pip install tinyfpgab

endif
endif

# DPControl icevision board
# iCE40UP5K-SG48
# ---------------------------------------------
ifeq ($(BOARD),icevision)
DEVICE=up5k
PACKAGE=sg48
PROG_TOOL=$(ICEPROG_TOOL)
endif

# Default dummy
# iCE40 hx1k-tq144 (same as icestick)
# ---------------------------------------------
ifeq ($(BOARD),none)
DEVICE=hx1k
PACKAGE=tq144
PROG_TOOL=true
endif

ifeq ($(DEVICE),)
$(error No $$DEVICE set.)
endif
ifeq ($(PACKAGE),)
$(error No $$PACKAGE set.)
endif
ifeq ($(PROG_TOOL),)
$(error No $$PROG_TOOL set.)
endif
