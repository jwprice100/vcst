import cocotb
from vcst.utils import parameterize_test, set_top_level
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock
from cocotb.result import TestSuccess, TestFailure

from vcst.utils import set_top_level

@cocotb.coroutine
async def sum_values(dut, values):
    clock = Clock(dut.clock, 4, "ns")
    cocotb.fork(clock.start())
    
    await RisingEdge(dut.clock)
    for a,b in values:
        dut.input_a <= a
        dut.input_b <= b
        await RisingEdge(dut.clock)
        await RisingEdge(dut.clock)
        expected_result = a+b    
        if dut.sum.value.get_value_signed() != expected_result:
            raise TestFailure(f"Incorrect sum. Expected {expected_result}. Actual: {int(dut.sum.value)}")


#Show the alternate to test factory.
parameterize_test(sum_values, "positive_values", [(0, 1), (12, 13), (100, 200)])
parameterize_test(sum_values, "negative_values", [(-1, 10), (-111, -222), (-1111, -2222)])
parameterize_test(sum_values, "positive_and_negative_value", [(123, -456), (789, -12), (345, -678)])

########################
set_top_level("adder", "entity", "lib")




