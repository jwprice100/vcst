import os
from pathlib import Path
import xml.etree.ElementTree as ET

import cocotb

from vunit.test.report import PASSED, SKIPPED, FAILED
from vunit.test.suites import IndependentSimTestCase, TestRun
from multiprocessing import Process, Value


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
            simulator_if=simulator_if,
            config=config,
            elaborate_only=elaborate_only,
            cocotb_module=test._cocotb_module,
            test_suite_name=self._name,
            test_cases=[test.name],
        )

class CocoTestRun(TestRun):    
    def __init__(self, vhdl, simulator_if, config, elaborate_only, cocotb_module, test_suite_name, test_cases):        
        TestRun.__init__(self, simulator_if, config, elaborate_only, test_suite_name, test_cases)    
        self._cocotb_module = cocotb_module
        self._vhdl = vhdl

    def set_env(self, output_path):
        """Sets the environment variables for cocotb."""
        test_case_str = ",".join(self._test_cases)
        mod_dir, mod_name = os.path.split(self._cocotb_module)

        if "PYTHONPATH" not in os.environ:
            os.environ["PYTHONPATH"] = mod_dir
        else:
            os.environ["PYTHONPATH"] = environ["PYTHONPATH"] + f"{os.pathsep}{mod_dir}"

        os.environ["COCOTB_RESULTS_FILE"] = get_result_file_name(output_path)
        os.environ["MODULE"] = mod_name
        os.environ["TESTCASE"] = test_case_str

    def run(self, output_path, read_output):
        """
        Run selected test cases within the test suite

        Returns a dictionary of test results
        """

        #TODO: Add support for other simulators
        ghdl_cocotb_lib = get_cocotb_libs_path() / 'libcocotbvpi_ghdl.so'        
        append_sim_options(self._config, "ghdl.sim_flags", [f"--vpi={ghdl_cocotb_lib}"])

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
        #Don't assume the module is in the current working directory. Get
        #the module's path, and set the pythonpath environment variable
        #
        sim_result = Value('b', False)
        simulate_proc = Process(target=simulate_helper, args=(self, output_path, sim_result))
        simulate_proc.start()
        simulate_proc.join()

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

def simulate_helper(coco_test_run, output_path, sim_result):
    """
       Isolates simulation to a separate process to avoid issues with sharing environment variables
       across threads.
    """
    coco_test_run.set_env(output_path)
    sim_result.value = coco_test_run._simulator_if.simulate(output_path=output_path, test_suite_name=coco_test_run._test_suite_name, config=coco_test_run._config, elaborate_only=coco_test_run._elaborate_only)        
    
def append_sim_options(config, name, value):
    sim_flags  = config.sim_options.get(name, [])
    sim_flags  = sim_flags + value
    config.set_sim_option(name, sim_flags)    

def get_result_file_name(output_path):
    return str(Path(output_path) / "cocotb_results.xml")

def get_cocotb_libs_path():
    return Path(os.path.dirname(cocotb.__file__)) / "libs"    