# ==============================================================================
# Authors:		Martin Zabel
#
# Cocotb Testbench:	For D flip-flop
#
# Description:
# ------------------------------------
# Automated testbench for simple D flip-flop.
#
# License:
# ==============================================================================
# Copyright 2016 Technische Universitaet Dresden - Germany
# Chair for VLSI-Design, Diagnostics and Architecture
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

from vcst.utils import set_top_level

#      dut
#    ________
#    |      |
#  --| d  q |--
#    |      |
#  --|>c    |
#    |______|


@cocotb.test()
async def dff_random_test(dut):
    """Apply random data to d and check that q captures it on the rising clock edge."""
    cocotb.start_soon(Clock(dut.c, 10, unit="us").start(start_high=False))

    for _ in range(100):
        bit = random.randint(0, 1)
        dut.d.value = bit
        await RisingEdge(dut.c)
        await FallingEdge(dut.c)
        assert dut.q.value == bit, f"q is {dut.q.value}, expected {bit}"


set_top_level("dff", "entity", "lib")
