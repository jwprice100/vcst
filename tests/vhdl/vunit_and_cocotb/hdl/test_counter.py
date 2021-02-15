import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock
from cocotb.result import TestSuccess, TestFailure

@cocotb.test()
async def reset_test(dut):
    clock = Clock(dut.clock, 4, units="ns")
    cocotb.fork((clock.start()))

    await RisingEdge(dut.clock)
    dut.reset <= 1
    dut.enable <= 0
    await RisingEdge(dut.clock)
    dut.reset <= 0
    await RisingEdge(dut.clock)

    if dut.counter_value.value != 0:
       raise TestFailure(f"Counter value did not reset to 0.")

    raise TestSuccess("Test passed.")

@cocotb.test()
async def count_test(dut):
    clock = Clock(dut.clock, 4, units="ns")
    cocotb.fork((clock.start()))

    await RisingEdge(dut.clock)
    dut.reset <= 1
    dut.enable <= 0
    await RisingEdge(dut.clock)
    dut.reset <= 0
    dut.enable <= 1
    await RisingEdge(dut.clock)

    counter_wrap = dut.COUNTER_WRAP.value
    for i in range(counter_wrap):
        if dut.counter_value.value != i:
            raise TestFailure(f"Counter value was incorrect. Expected: {i}. Actual: {dut.counter_value.value}")
        await RisingEdge(dut.clock)

    raise TestSuccess("Test passed.")
