import cocotb
from vcst.utils import set_top_level
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock

@cocotb.test()
async def reset_test(dut):
    clock = Clock(dut.clock, 4, unit="ns")
    cocotb.start_soon(clock.start())

    await RisingEdge(dut.clock)
    dut.reset.value = 1
    dut.enable.value = 0
    await RisingEdge(dut.clock)
    dut.reset.value = 0
    await RisingEdge(dut.clock)

    assert dut.counter_value.value == 0, "Counter value did not reset to 0."


@cocotb.test()
async def count_test(dut):
    clock = Clock(dut.clock, 4, unit="ns")
    cocotb.start_soon(clock.start())

    await RisingEdge(dut.clock)
    dut.reset.value = 1
    dut.enable.value = 0
    await RisingEdge(dut.clock)
    dut.reset.value = 0
    dut.enable.value = 1
    await RisingEdge(dut.clock)

    counter_wrap = dut.COUNTER_WRAP.value
    for i in range(counter_wrap):
        assert dut.counter_value.value == i, f"Counter value was incorrect. Expected: {i}. Actual: {dut.counter_value.value}"
        await RisingEdge(dut.clock)


@cocotb.test()
async def wrap_test(dut):
    clock = Clock(dut.clock, 4, unit="ns")
    cocotb.start_soon(clock.start())

    await RisingEdge(dut.clock)
    dut.reset.value = 1
    dut.enable.value = 0
    await RisingEdge(dut.clock)
    dut.reset.value = 0
    dut.enable.value = 1
    await RisingEdge(dut.clock)

    counter_wrap = dut.COUNTER_WRAP.value
    for i in range(counter_wrap):
        await RisingEdge(dut.clock)

    assert dut.counter_value.value == counter_wrap, "Counter value did not reach wrapping point."
    
    await RisingEdge(dut.clock)    
    assert dut.counter_value.value == 0, "Counter value did not wrap to 0."


########################
set_top_level("counter", "entity", "lib")




