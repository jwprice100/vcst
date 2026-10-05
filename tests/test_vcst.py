import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import cocotb
import find_libpython
import pytest
from vunit.test.report import FAILED, PASSED, SKIPPED

import vcst
from vcst import VCST
from vcst.test.bench import CocoTest, CocoTestBench
from vcst.test.suites import CocoTestRun, cocotb_run_env, get_cocotb_seed, get_sim_flags, simulation_env

EXAMPLES = Path(__file__).parent / "vhdl"


class FakeConfig:
    def __init__(self, sim_options=None):
        self.sim_options = dict(sim_options or {})

    def set_sim_option(self, name, value):
        self.sim_options[name] = value


def make_run(simulator_name, vhdl=True, top_level="ADDER"):
    return CocoTestRun(
        vhdl=vhdl,
        top_level=top_level,
        cocotb_module_location=str(Path("/tests/hdl/test_adder")),
        cocotb_fullnames=["common.basic"],
        simulator_if=SimpleNamespace(name=simulator_name),
        config=FakeConfig(),
        elaborate_only=False,
        test_suite_name="lib.adder.basic",
        test_cases=["basic"],
        seed="00000000000000ff",
    )


def test_nvc_flags_load_vhpi_plugin_at_run():
    flags = get_sim_flags("nvc", vhdl=True)
    assert list(flags) == ["nvc.sim_flags"]
    (load,) = flags["nvc.sim_flags"]
    assert load.startswith("--load=") and load.endswith("libcocotbvhpi_nvc.so")
    assert Path(load[len("--load=") :]).is_file()


def test_modelsim_vhdl_flags_use_fli():
    foreign, value = get_sim_flags("modelsim", vhdl=True)["modelsim.vsim_flags"]
    assert foreign == "-foreign"
    assert value.startswith("{cocotb_init ") and value.endswith("libcocotbfli_modelsim.so}")


def test_modelsim_verilog_flags_use_vpi():
    (lib,) = get_sim_flags("modelsim", vhdl=False)["pli"]  # VUnit's pli option quotes the path for Tcl
    assert lib.endswith("libcocotbvpi_modelsim.so")


def test_unsupported_simulator_is_an_error():
    with pytest.raises(RuntimeError, match="activehdl"):
        get_sim_flags("activehdl", vhdl=True)


def test_configure_simulator_keeps_user_flags_and_gui_flags():
    run = make_run("modelsim")
    config = FakeConfig({"modelsim.vsim_flags": ["-user"], "modelsim.vsim_flags.gui": ["-user_gui"]})
    run.configure_simulator(config)
    assert config.sim_options["modelsim.vsim_flags"][:2] == ["-user", "-foreign"]
    assert config.sim_options["modelsim.vsim_flags.gui"][:2] == ["-user_gui", "-foreign"]


@pytest.mark.parametrize("simulator_name", ["nvc", "modelsim"])
def test_create_environ(simulator_name, tmp_path, monkeypatch):
    monkeypatch.delenv("COCOTB_RANDOM_SEED", raising=False)
    monkeypatch.delenv("COCOTB_RESOLVE_X", raising=False)
    env = make_run(simulator_name).create_environ(str(tmp_path))
    assert env["COCOTB_TEST_MODULES"] == "test_adder"
    assert env["COCOTB_TOPLEVEL"] == "adder"
    assert env["COCOTB_TEST_FILTER"] == r"^(common\.basic)$"  # defined in another module than test_adder
    assert env["COCOTB_RANDOM_SEED"] == "255"
    assert env["COCOTB_RESULTS_FILE"] == str(tmp_path / "cocotb_results.xml")
    assert env["PYTHONPATH"].split(os.pathsep)[-1] == str(Path("/tests/hdl"))
    assert env["PYGPI_PYTHON_BIN"] == sys.executable
    assert env["TOPLEVEL_LANG"] == "vhdl"
    assert env["COCOTB_RESOLVE_X"] == "ZEROS"


def test_run_env_hook_only_applies_inside_simulation_env():
    base = {"PATH": "/bin"}
    assert cocotb_run_env(None, base) == base
    with simulation_env({"COCOTB_TEST_MODULES": "mod"}):
        assert cocotb_run_env(None, base) == {"PATH": "/bin", "COCOTB_TEST_MODULES": "mod"}
        # an inherited COCOTB_TESTCASE would make cocotb reject vcst's COCOTB_TEST_FILTER
        assert cocotb_run_env(None, {**base, "COCOTB_TESTCASE": "x"}) == {"PATH": "/bin", "COCOTB_TEST_MODULES": "mod"}
    assert cocotb_run_env(None, base) == base


@pytest.mark.parametrize("top_level_type", ["entity", "module"])
def test_add_cocotb_testbench_accepts_entity_and_module(top_level_type, tmp_path):
    ui = VCST.from_argv(argv=["--output-path", str(tmp_path)])
    module = SimpleNamespace(top_level="adder", top_level_type=top_level_type, top_level_library="missing")
    with pytest.raises(KeyError, match="missing"):  # got past the type check to the library lookup
        ui.add_cocotb_testbench("test_adder", module)


def test_add_cocotb_testbench_rejects_other_top_level_types(tmp_path):
    ui = VCST.from_argv(argv=["--output-path", str(tmp_path)])
    module = SimpleNamespace(top_level="adder", top_level_type="architecture", top_level_library="lib")
    with pytest.raises(RuntimeError, match="Invalid top level type 'architecture'"):
        ui.add_cocotb_testbench("test_adder", module)


@pytest.mark.parametrize("example", ["cocotb_examples", "parameterize_test", "vunit_and_cocotb"])
@pytest.mark.parametrize("simulator_name, executable", [("nvc", "nvc"), ("modelsim", "vsim")])
def test_example_runs(simulator_name, executable, example, tmp_path):
    if shutil.which(executable) is None:
        pytest.skip(f"{executable} not found")
    proc = subprocess.run(
        [sys.executable, str(EXAMPLES / example / "run.py"), "-p", "4", "-o", str(tmp_path)],
        env={**os.environ, "VUNIT_SIMULATOR": simulator_name},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout[-5000:] + proc.stderr[-5000:]


def test_read_test_results_maps_cocotb_outcomes(tmp_path):
    results_file = tmp_path / "cocotb_results.xml"
    results_file.write_text(
        "<testsuites><testsuite>"
        '<testcase name="passed"/>'
        '<testcase name="failed"><failure/></testcase>'
        '<testcase name="errored"><error/></testcase>'
        '<testcase name="skipped"><skipped/></testcase>'
        "</testsuite></testsuites>"
    )
    run = make_run("nvc")
    run._test_cases = ["passed", "failed", "errored", "skipped", "not_run"]
    assert run._read_test_results(str(results_file)) == {
        "passed": PASSED,
        "failed": FAILED,
        "errored": FAILED,
        "skipped": PASSED,
        "not_run": SKIPPED,
    }


def test_vcst_test_decorator_with_and_without_arguments():
    async def check(dut):
        pass

    assert vcst.test(check).attributes == []
    assert vcst.test(attributes=[".slow"])(check).attributes == [".slow"]


def test_create_environ_without_libpython_is_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.delenv("GPI_USERS", raising=False)
    monkeypatch.delenv("LIBPYTHON_LOC", raising=False)
    monkeypatch.setattr(find_libpython, "find_libpython", lambda: None)
    with pytest.raises(RuntimeError, match="libpython"):
        make_run("nvc").create_environ(str(tmp_path))


def test_cocotb_fullname_uses_simulator_module_name():
    design_unit = SimpleNamespace(file_name="adder.vhd", is_entity=True)
    module = SimpleNamespace(__name__="tests.hdl.test_adder", top_level="adder")

    def cocotb_test(module_name):
        return SimpleNamespace(name="basic", module=module_name, fullname=f"{module_name}.basic")

    own = CocoTest(cocotb_test("tests.hdl.test_adder"), design_unit, module, "/x/hdl/test_adder")
    imported = CocoTest(cocotb_test("common_tests"), design_unit, module, "/x/hdl/test_adder")
    assert own._cocotb_fullname == "test_adder.basic"
    assert imported._cocotb_fullname == "common_tests.basic"


def test_duplicate_cocotb_test_names_are_an_error():
    async def basic(dut):
        pass

    imported = cocotb.test(basic)
    imported.module = "common_tests"
    module = SimpleNamespace(__name__="test_adder", top_level="adder", basic=cocotb.test(basic), other=imported)
    design_unit = SimpleNamespace(file_name="adder.vhd", is_entity=True, name="adder")
    bench = CocoTestBench.__new__(CocoTestBench)
    bench.design_unit = design_unit
    with pytest.raises(RuntimeError, match="Duplicate cocotb test name"):
        bench.discover_cocotb_tests(module, "/x/hdl/test_adder")


def test_cocotb_seed_from_hex_and_free_form_vunit_seeds():
    assert get_cocotb_seed("00000000000000ff") == 255
    assert get_cocotb_seed("255") == 255
    assert get_cocotb_seed("nightly_run") == get_cocotb_seed("nightly_run")
    assert get_cocotb_seed("nightly_run") != get_cocotb_seed("weekly_run")


def test_user_cocotb_random_seed_is_kept(monkeypatch, tmp_path):
    monkeypatch.setenv("COCOTB_RANDOM_SEED", "255")
    assert "COCOTB_RANDOM_SEED" not in make_run("nvc").create_environ(str(tmp_path))


def test_riviera_generics_quote_strings_and_format_lists():
    from vcst.ui import format_riviera_generic

    assert format_riviera_generic(8) == "8"
    assert format_riviera_generic("fast") == '"fast"'
    assert format_riviera_generic([1, (2, 3), "a"]) == '(1,(2,3),"a")'
