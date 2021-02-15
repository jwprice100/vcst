
from pathlib import Path
from vcst import VCST
from glob import glob

ui = VCST.from_argv()
lib = ui.add_library("lib")
lib.add_source_files("hdl/*.vhd*", vhdl_standard="2008")

#Configure the counter testbench
tb_counter = lib.entity("tb_counter")
tb_counter.add_config(name="width_8_wrap_200", generics={"COUNTER_WIDTH": 8, "COUNTER_WRAP": 200})
tb_counter.add_config(name="width_8_wrap_200", generics={"COUNTER_WIDTH": 10, "COUNTER_WRAP": 1000})

#Pair the counter  entity with it's cocotb module
counter = lib.entity("counter", test_bench=False)
lib.add_cocotb_testbench(counter, "hdl/test_counter")
cocotb_counter = lib.test_bench("counter")
cocotb_counter.add_config(name="width_8_wrap_200", generics={"COUNTER_WIDTH": 8, "COUNTER_WRAP": 200})
cocotb_counter.add_config(name="width_8_wrap_200", generics={"COUNTER_WIDTH": 10, "COUNTER_WRAP": 1000})

ui.main()

