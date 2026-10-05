import hashlib
import os
import re
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
import xml.etree.ElementTree as ET

import find_libpython
from cocotb_tools.config import lib_entry, lib_name_path, pygpi_entry_point

from vunit.test.report import PASSED, SKIPPED, FAILED
from vunit.ostools import write_file
from vunit.sim_if.vsim_simulator_mixin import fix_path
from vunit.test.suites import IndependentSimTestCase, TestRun, get_result_file_name as get_vunit_result_file_name

# VUnit's run_env hooks are registered per simulator, not per test, and tests run in threads.
# The cocotb environment of the test running in the current thread is kept here for the hook.
_thread_local = threading.local()


def cocotb_run_env(simulator_interface, env):
    """VUnit run_env hook merging the current test's cocotb environment into the simulator's."""
    cocotb_env = getattr(_thread_local, "env", None)
    if not cocotb_env:
        return env
    # vcst selects tests with COCOTB_TEST_FILTER, and cocotb refuses to run if COCOTB_TESTCASE is also set
    return {**{name: value for name, value in env.items() if name != "COCOTB_TESTCASE"}, **cocotb_env}


@contextmanager
def simulation_env(env):
    """Pass env to every simulator process started by this thread inside the with block."""
    _thread_local.env = env
    try:
        yield
    finally:
        _thread_local.env = None


class IndependentCocoSimTestCase(IndependentSimTestCase):
    def __init__(self, test, config, simulator_if, seed, *, elaborate_only=False):
        self._name = self.get_name(test, config)
        self._configuration = config
        self._test = test

        self._run = CocoTestRun(
            vhdl=test._vhdl,
            top_level=test._top_level,
            simulator_if=simulator_if,
            config=config,
            elaborate_only=elaborate_only,
            cocotb_module_location=test._cocotb_module_location,
            cocotb_fullnames=[test._cocotb_fullname],
            test_suite_name=self._name,
            test_cases=[test.name],
            seed=seed,
        )


class CocoTestRun(TestRun):
    def __init__(self, *, vhdl, top_level, cocotb_module_location, cocotb_fullnames, **kwargs):
        TestRun.__init__(self, **kwargs)
        self._cocotb_module_location = cocotb_module_location
        self._cocotb_fullnames = cocotb_fullnames
        self._top_level = top_level
        self._vhdl = vhdl

    def create_environ(self, output_path):
        """Environment variables cocotb needs inside the simulator process."""
        mod_dir, mod_name = os.path.split(self._cocotb_module_location)
        python_path = os.environ.get("PYTHONPATH")
        test_filter = "|".join(re.escape(fullname) for fullname in self._cocotb_fullnames)

        environ = {
            "PYTHONPATH": str(mod_dir) if not python_path else f"{python_path}{os.pathsep}{mod_dir}",
            "PYGPI_PYTHON_BIN": sys.executable,
            "COCOTB_RESULTS_FILE": get_result_file_name(output_path),
            "COCOTB_TEST_MODULES": mod_name,
            "COCOTB_TEST_FILTER": f"^({test_filter})$",
            "COCOTB_TOPLEVEL": self._top_level.lower() if self._vhdl else self._top_level,
            "TOPLEVEL_LANG": "vhdl" if self._vhdl else "verilog",
            "COCOTB_RESOLVE_X": os.environ.get("COCOTB_RESOLVE_X", "ZEROS"),
        }

        # A seed set by the user, as cocotb's failure report suggests, wins over VUnit's
        if "COCOTB_RANDOM_SEED" not in os.environ:
            environ["COCOTB_RANDOM_SEED"] = str(get_cocotb_seed(self.get_seed()))

        if "GPI_USERS" not in os.environ:
            libpython = os.environ.get("LIBPYTHON_LOC") or find_libpython.find_libpython()
            if libpython is None:
                raise RuntimeError("Unable to find libpython, install it or set LIBPYTHON_LOC")
            environ["GPI_USERS"] = f"{libpython};{pygpi_entry_point()}"

        return environ

    def configure_simulator(self, config):
        """Add the simulator flags that load cocotb's VPI/VHPI/FLI library."""
        for name, flags in get_sim_flags(self._simulator_if.name, self._vhdl).items():
            config.set_sim_option(name, config.sim_options.get(name, []) + flags)
            # vsim_flags.gui replaces vsim_flags in GUI mode when set, so it needs the cocotb flags too.
            if f"{name}.gui" in config.sim_options:
                config.set_sim_option(f"{name}.gui", config.sim_options[f"{name}.gui"] + flags)

    def run(self, output_path, read_output, run_script_path=None):
        """
        Run selected test cases within the test suite

        Returns a dictionary of test results
        """
        results = {name: FAILED for name in self._test_cases}

        if not self._config.call_pre_config(output_path, self._simulator_if.output_path, self.get_seed()):
            return results

        # VUnit's vsim run script reads its own results file and reports a failure unless the test suite
        # is marked done. The cocotb results file decides the outcome, so mark it done up front.
        write_file(get_vunit_result_file_name(output_path), "test_suite_done\n")

        sim_ok = self._simulate(output_path)

        if self._elaborate_only:
            status = PASSED if sim_ok else FAILED
            return dict((name, status) for name in self._test_cases)

        results = self._read_test_results(file_name=get_result_file_name(output_path))

        done, results = self._check_results(results, sim_ok)
        if done:
            return results

        if not self._config.call_post_check(output_path, read_output):
            for name in self._test_cases:
                results[name] = FAILED

        return results

    def _simulate(self, output_path):
        print(f"Seed for {self._test_suite_name}: {self.get_seed()}")
        config = self._config.copy()
        self.configure_simulator(config)
        with simulation_env(self.create_environ(output_path)):
            return self._simulator_if.simulate(
                output_path=output_path,
                test_suite_name=self._test_suite_name,
                config=config,
                elaborate_only=self._elaborate_only,
            )

    def _read_test_results(self, file_name):
        results = {name: FAILED for name in self._test_cases}

        if not os.path.exists(file_name):
            return results

        results_tests = []
        for result in ET.parse(file_name).getroot().iter("testcase"):
            test_name = result.attrib["name"]
            results_tests.append(test_name)
            # A test skipped at runtime (pytest.skip) counts as passed: VUnit turns SKIPPED into FAILED here
            if result.find("failure") is not None or result.find("error") is not None:
                results[test_name] = FAILED
            else:
                results[test_name] = PASSED

        for test_name in self._test_cases:
            if test_name not in results_tests:
                results[test_name] = SKIPPED

        return results


def get_sim_flags(simulator_name, vhdl):
    """Simulator options that load cocotb into the given VUnit simulator."""
    if simulator_name == "ghdl":
        return {"ghdl.sim_flags": [f"--vpi={lib_name_path('vpi', 'ghdl')}"]}

    if simulator_name == "nvc":
        # --load is a run (-r) option, so it goes in sim_flags rather than global_flags.
        return {"nvc.sim_flags": [f"--load={lib_name_path('vhpi', 'nvc')}"]}

    if simulator_name == "modelsim":
        if vhdl:
            # VUnit space-joins vsim_flags into a Tcl eval, so the -foreign value needs Tcl braces and
            # forward slashes. The VPI library goes through VUnit's pli option, which quotes it for Tcl.
            fli_lib = lib_name_path("fli", "questa").as_posix()
            return {"modelsim.vsim_flags": ["-foreign", f"{{cocotb_init {fli_lib}}}"]}
        return {"pli": [lib_name_path("vpi", "questa").as_posix()]}

    if simulator_name == "rivierapro":
        flags = ["+access", "+w", "-interceptcoutput", "-O2"]
        if vhdl:
            # needs lib:entry_function; quoted for Tcl like VUnit's own Riviera-Pro pli option
            return {"rivierapro.vsim_flags": flags + [f'-loadvhpi "{fix_path(lib_entry("vhpi", "riviera"))}"']}
        return {"rivierapro.vsim_flags": flags, "pli": [lib_name_path("vpi", "riviera").as_posix()]}

    raise RuntimeError(f"vcst does not support cocotb tests on simulator {simulator_name!r}")


def get_cocotb_seed(seed):
    """cocotb needs an integer seed; VUnit's is 16 hex digits, or any string set with the seed sim option."""
    if re.fullmatch("[0-9a-fA-F]{16}", seed):
        return int(seed, 16)
    if seed.isdecimal():  # e.g. the COCOTB_RANDOM_SEED from a cocotb failure report
        return int(seed)
    return int(hashlib.blake2b(seed.encode(), digest_size=8).hexdigest(), 16)


def get_result_file_name(output_path):
    return str(Path(output_path) / "cocotb_results.xml")
