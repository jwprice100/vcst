
from pathlib import Path
from vcst import VCST
from glob import glob

root = Path(__file__).parent 
ui = VCST.from_argv()
lib = ui.add_library("lib")
lib.add_source_files(root / "hdl" / "*.vhd*", vhdl_standard="2008")

#Pair the DFF entity with it's cocotb module
dff = lib.entity("dff", test_bench=False)
lib.add_cocotb_testbench(dff, root / "hdl/dff_cocotb")

#Add configurations for the adder
adder = lib.entity("adder", test_bench=False)
lib.add_cocotb_testbench(adder, root / "hdl/test_adder")
adder_tb = lib.test_bench("adder")
adder_tb.add_config(name="data_width_8", generics={"DATA_WIDTH": 8})
adder_tb.add_config(name="data_width_16", generics={"DATA_WIDTH": 16})

ui.main()

