from pathlib import Path
from vcst import VCST
from glob import glob
import os

root = Path(os.path.abspath(Path(__file__).parent))
ui = VCST.from_argv()
lib = ui.add_library("lib")
lib.add_source_files(root / "hdl" / "*.vhd*", vhdl_standard="2008")

#Pair the DFF entity with it's cocotb module
ui.add_cocotb_testbench(root / "hdl/dff_cocotb")

#Add configurations for the adder
adder_tb = ui.add_cocotb_testbench(root / "hdl/test_adder")
adder_tb.add_config(name="data_width_8", generics={"DATA_WIDTH": 8})
adder_tb.add_config(name="data_width_16", generics={"DATA_WIDTH": 16})

ui.main()

