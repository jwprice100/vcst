import os
from collections import OrderedDict
from dataclasses import dataclass

from cocotb.regression import Test as CocotbTest, TestGenerator

from vunit.test.bench import TestBench, TestConfigurationVisitor, FileLocation, Test, _get_historic_seed
from vunit.test.list import TestList
from vunit.configuration import ConfigurationVisitor, Configuration, DEFAULT_NAME

from .suites import IndependentCocoSimTestCase


class CocoTestBench(TestBench):
    def __init__(self, design_unit, cocotb_module, cocotb_module_location, database=None):
        ConfigurationVisitor.__init__(self, design_unit)
        self._database = database

        self._individual_tests = True
        self._configs = {}
        self._test_cases = []
        self._implicit_test = None
        self._cocotb_module = None

        if design_unit.is_entity:
            design_unit.set_add_architecture_callback(self._add_architecture_callback)
            if design_unit.architecture_names:
                self._add_architecture_callback()

        self.discover_cocotb_tests(cocotb_module, cocotb_module_location)
        self.set_attribute(".cocotb", None)

    def _add_architecture_callback(self):
        """
        Called when architectures have been added
        """
        self._check_architectures(self.design_unit)

    def discover_cocotb_tests(self, cocotb_module, cocotb_module_location):
        """
        Discover tests defined in a cocotb module, the same way cocotb's regression manager does.
        """
        self._cocotb_module = cocotb_module
        tests = []
        for obj in vars(cocotb_module).values():
            if isinstance(obj, CocotbTest):
                cocotb_tests = [obj]
            elif isinstance(obj, TestGenerator):
                cocotb_tests = obj.generate_tests()
            else:
                continue

            for cocotb_test in cocotb_tests:
                if any(test.name == cocotb_test.name for test in tests):
                    raise RuntimeError(f"Duplicate cocotb test name {cocotb_test.name!r} in {cocotb_module_location}")
                coco_test = CocoTest(cocotb_test, self.design_unit, cocotb_module, cocotb_module_location)
                for attr in getattr(obj, "attributes", []):
                    coco_test.add_attribute(CocoTestAttribute(attr, None))
                tests.append(coco_test)

        default_config = Configuration(DEFAULT_NAME, self.design_unit)
        self._test_cases = [
            CocoTestConfigurationVisitor(test, self.design_unit, True, default_config.copy()) for test in tests
        ]

        self._configs = OrderedDict({default_config.name: default_config})

    def create_tests(self, simulator_if, seed, elaborate_only, test_list=None):
        """
        Create all test cases from this test bench
        """
        self._check_architectures(self.design_unit)

        if test_list is None:
            test_list = TestList()

        test_history = {}
        if self._database and b"test_history" in self._database:
            test_history = self._database[b"test_history"]

        for test_case in self._test_cases:
            test_case.create_tests(simulator_if, seed, elaborate_only, test_list, test_history)

        return test_list


class CocoTest(Test):
    def __init__(self, cocotb_test, design_unit, cocotb_module, cocotb_module_location):
        # offset, length, lineno set to None
        Test.__init__(self, cocotb_test.name, FileLocation(design_unit.file_name, None, None, None))
        self._top_level = cocotb_module.top_level
        self._vhdl = design_unit.is_entity
        self._cocotb_module = cocotb_module
        self._cocotb_module_location = cocotb_module_location
        # The name cocotb matches tests by in the simulator, which imports cocotb_module by its file name
        # (COCOTB_TEST_MODULES). Tests imported from other modules keep the module they are defined in.
        if cocotb_test.module == cocotb_module.__name__:
            self._cocotb_fullname = f"{os.path.basename(cocotb_module_location)}.{cocotb_test.name}"
        else:
            self._cocotb_fullname = cocotb_test.fullname


class CocoTestConfigurationVisitor(TestConfigurationVisitor):
    """
    Override VUnit's TestConfigurationVisitor to create IndependentCocoSimTestCase objects
    """

    def create_tests(self, simulator_if, seed, elaborate_only, test_list=None, test_history=None):
        for config in self._get_configurations_to_run():
            actual_seed = seed
            if seed == "repeat":
                name = IndependentCocoSimTestCase.get_name(self._test, config)
                actual_seed = _get_historic_seed(test_history or {}, name, name)

            test_list.add_test(
                IndependentCocoSimTestCase(
                    test=self._test,
                    config=config,
                    simulator_if=simulator_if,
                    seed=actual_seed,
                    elaborate_only=elaborate_only,
                )
            )


@dataclass
class CocoTestAttribute:
    name: str
    value: str
