# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
# Simple tests for an adder module
import cocotb
from cocotb.triggers import Timer
from adder_model import adder_model
import random

from vcst.utils import set_top_level

@cocotb.test()
async def adder_basic_test(dut):
    """Test for 5 + 10"""

    A = 5
    B = 10

    dut.A <= A
    dut.B <= B

    await Timer(2, units='ns')

    assert dut.X.value == adder_model(A, B), f"Adder result is incorrect: {dut.X.value} != 15"


@cocotb.test()
async def adder_randomised_test(dut):
    """Test for adding 2 random numbers multiple times"""
    width = dut.DATA_WIDTH.value
    max_val = 2**width-1
    for i in range(10):
        A = random.randint(0, max_val)
        B = random.randint(0, max_val)

        dut.A <= A
        dut.B <= B

        await Timer(2, units='ns')
        assert dut.X.value == adder_model(A, B), f"Randomised test failed with: {dut.A.value} + {dut.B.value} = {dut.X.value}"


set_top_level("adder", "entity", "lib")