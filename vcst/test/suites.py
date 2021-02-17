import os
from pathlib import Path
import xml.etree.ElementTree as ET

import cocotb

from vunit.test.report import PASSED, SKIPPED, FAILED
from vunit.test.suites import IndependentSimTestCase, TestRun
from multiprocessing import Process, Value

from vcst.utils.mod_utils import import_mod

class IndependentCocoSimTestCase(IndependentSimTestCase):
    def __init__(self, test, config, simulator_if, elaborate_only=False):
        self._name = "%s.%s" % (config.library_name, config.design_unit_name)

        if not config.is_default:
            self._name += "." + config.name

        if test.is_explicit:
            self._name += "." + test.name
        elif config.is_default:
            # JUnit XML test reports wants three dotted name hierarchies
            self._name += ".all"

        self._configuration = config
        self._test = test

        self._run = CocoTestRun(
            vhdl=test._vhdl,
            top_level=test._top_level,
            simulator_if=simulator_if,
            config=config,
            elaborate_only=elaborate_only,
            cocotb_module=test._cocotb_module,
            test_suite_name=self._name,
            test_cases=[test.name],
        )

class CocoTestRun(TestRun):    
    def __init__(self, vhdl, top_level, simulator_if, config, elaborate_only, cocotb_module, test_suite_name, test_cases):        
        TestRun.__init__(self, simulator_if, config, elaborate_only, test_suite_name, test_cases)    
        self._cocotb_module = cocotb_module
        self._top_level = top_level
        self._vhdl = vhdl

    def create_environ(self, output_path):
        """Creates a set of virtual environment variables for cocotb."""
        environ = os.environ.copy()
        test_case_str = ",".join(self._test_cases)
        mod_dir, mod_name = os.path.split(self._cocotb_module)
        mod = import_mod(self._cocotb_module)

        if "PYTHONPATH" not in os.environ:
            environ["PYTHONPATH"] = mod_dir
        else:
            environ["PYTHONPATH"] = environ["PYTHONPATH"] + f"{os.pathsep}{mod_dir}"

        environ["COCOTB_RESULTS_FILE"] = get_result_file_name(output_path)        
        environ["MODULE"] = mod_name
        environ["TESTCASE"] = test_case_str

        if self._simulator_if.name == "ghdl":
            environ["TOPLEVEL"] = mod.top_level.lower()
        else:
            environ["TOPLEVEL"] = mod.top_level

        return environ

    def configure_simulator(self, environ):
        """
            Sets simulator flags to load the VPI/VHPI/FLI interfaces as appropriate. Also sets environment
            variables related to those interfaces.
            TODO: Support more simulators.
        """
        if self._simulator_if.name == "ghdl":
            ghdl_cocotb_lib = get_cocotb_libs_path() / 'libcocotbvpi_ghdl.so'        
            append_sim_options(self._config, "ghdl.sim_flags", [f"--vpi={ghdl_cocotb_lib}"])

        if self._simulator_if.name == "rivierapro":
            riviera_cocotb_vhpi_lib = get_cocotb_libs_path() / 'libcocotbvhpi_aldec.so'        
            riviera_cocotb_vpi_lib = get_cocotb_libs_path() / 'libcocotbvpi_aldec.so'        
            
            append_sim_options(self._config, "rivierapro.vsim_flags", ["+access", "+w", "-interceptcoutput", "-O2"])
            
            if self._vhdl:
                append_sim_options(self._config, "rivierapro.vsim_flags", [f"-loadvhpi {riviera_cocotb_vhpi_lib}"])
                environ["GPI_EXTRA"] = "cocotbvpi_aldec:cocotbvpi_entry_point"                 
            else:
                append_sim_options(self._config, "rivierapro.vsim_flags", [f"-pli {riviera_cocotb_vpi_lib}"])
                environ["GPI_EXTRA"] = "cocotbvhpi_aldec:cocotbvhpi_entry_point"

    def run(self, output_path, read_output):
        """
        Run selected test cases within the test suite

        Returns a dictionary of test results
        """
        results = {}
        for name in self._test_cases:
            results[name] = FAILED

        if not self._config.call_pre_config(output_path, self._simulator_if.output_path):
            return results
        
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
        """Due to the use of environment variables, we'll create a process to work around VUnit's multithreading for now."""
        env = self.create_environ(output_path)
        self.configure_simulator(env)
        sim_result = self._simulator_if.simulate(output_path=output_path, test_suite_name=self._test_suite_name, config=self._config, elaborate_only=self._elaborate_only, env=env)        
        return sim_result

    def _read_test_results(self, file_name):
        print("Reading results....")
        results = {}
        for name in self._test_cases:
            results[name] = FAILED

        if not os.path.exists(file_name):
            return results        

        tree = ET.parse(file_name)
        root = tree.getroot()

        test_suites = root.getchildren()[0]
        results_tests = []    
        for result in test_suites:
            if result.tag == "testcase":            
                test_name = result.attrib["name"]  
                results_tests.append(test_name)
                results[test_name] = PASSED
                for thing in result:
                    if thing.tag == "failure":
                        results[test_name] = FAILED

        for test_name in self._test_cases:
            if test_name not in results_tests:
                results[test_name] = SKIPPED

        return results

def append_sim_options(config, name, value):
    sim_flags  = config.sim_options.get(name, [])
    sim_flags  = sim_flags + value
    config.set_sim_option(name, sim_flags)    

def get_result_file_name(output_path):
    return str(Path(output_path) / "cocotb_results.xml")

def get_cocotb_libs_path():
    return Path(os.path.dirname(cocotb.__file__)) / "libs"    