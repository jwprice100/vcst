
from pathlib import Path
from vcst import VCST
from glob import glob
import os

root = Path(os.path.abspath(Path(__file__).parent))
ui = VCST.from_argv()
lib = ui.add_library("lib")
lib.add_source_files(root / "hdl" / "*.vhd*", vhdl_standard="2008")
lib.add_compile_option("rivierapro.vcom_flags", ["-dbg","-relax"])   
#Configure the counter testbench
tb_counter = lib.test_bench("tb_counter")
tb_counter.add_config(name="width_8_wrap_200", generics={"COUNTER_WIDTH": 8, "COUNTER_WRAP": 200})
tb_counter.add_config(name="width_10_wrap_1000", generics={"COUNTER_WIDTH": 10, "COUNTER_WRAP": 1000})
tb_counter.add_config(name="width_12_wrap_2000", generics={"COUNTER_WIDTH": 12, "COUNTER_WRAP": 2000})

#Pair the counter  entity with it's cocotb module
cocotb_counter = ui.add_cocotb_testbench(root / "hdl/test_counter")
cocotb_counter.add_config(name="width_8_wrap_200", generics={"COUNTER_WIDTH": 8, "COUNTER_WRAP": 200})
cocotb_counter.add_config(name="width_10_wrap_1000", generics={"COUNTER_WIDTH": 10, "COUNTER_WRAP": 1000})
cocotb_counter.add_config(name="width_12_wrap_2000", generics={"COUNTER_WIDTH": 12, "COUNTER_WRAP": 2000})

ui.main()

