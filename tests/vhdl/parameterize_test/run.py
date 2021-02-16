
from pathlib import Path
from vcst import VCST
from glob import glob

ui = VCST.from_argv()
lib = ui.add_library("lib")
lib.add_source_files("hdl/*.vhd*", vhdl_standard="2008")

#Pair the counter  entity with it's cocotb module
cocotb_adder = ui.add_cocotb_testbench("hdl/test_adder")
cocotb_adder.add_config(name="width_16", generics={"ADDER_WIDTH": 16})
cocotb_adder.add_config(name="width_32", generics={"ADDER_WIDTH": 32})

ui.main()

