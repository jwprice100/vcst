import os
import sys
import types

from pathlib import Path
from collections import OrderedDict
from importlib.machinery import SourceFileLoader
from dataclasses import dataclass

from cocotb.decorators import test as Test
from ..decorators import test as vcst_Test

from vunit.test.bench import TestBench, TestConfigurationVisitor, FileLocation
from vunit.configuration import ConfigurationVisitor, Configuration, DEFAULT_NAME

from .suites import IndependentCocoSimTestCase
from ..utils.mod_utils import import_mod

class CocoTestBench(TestBench):
    def __init__(self, design_unit, cocotb_module, cocotb_module_location, database=None):
        
        ConfigurationVisitor.__init__(self)
        self.design_unit = design_unit
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
        Discover tests defined in a cocotb module and 
        """
        self._cocotb_module = cocotb_module        
        tests = []
        #Iterate every value in the module looking for cocotb tests
        for obj_name in dir(cocotb_module):
            obj = getattr(cocotb_module, obj_name)
            if isinstance(obj, Test):
                coco_test = CocoTest(obj.__name__, self.design_unit, cocotb_module, cocotb_module_location)
                if isinstance(obj, vcst_Test):
                    for attr in obj.attributes:
                        coco_test.add_attribute(CocoTestAttribute(attr, None))
                tests.append(coco_test)

        default_config = Configuration(DEFAULT_NAME, self.design_unit)                  
        self._test_cases = [
            CocoTestConfigurationVisitor(test, self.design_unit, True, default_config.copy())
            for test in tests
        ]

        self._configs = OrderedDict({default_config.name: default_config})

    def create_tests(self, simulator_if, elaborate_only, test_list=None):
        """
        Create all test cases from this test bench
        """

        self._check_architectures(self.design_unit)

        if test_list is None:
            test_list = TestList()

        for test_case in self._test_cases:
            test_case.create_tests(simulator_if, elaborate_only, test_list)

        return test_list


class CocoTest(object):
    """
    TODO: Describe
    """

    def __init__(self, name, design_unit, cocotb_module, cocotb_module_location):
        self._name = name
        self._top_level = cocotb_module.top_level
        self._vhdl = design_unit.is_entity
        self._location = FileLocation(design_unit.file_name, None, None, None) #offset, length, lineno set to None
        self._cocotb_module = cocotb_module
        self._cocotb_module_location = cocotb_module_location
        self._attributes = []

    @property
    def name(self):
        return self._name

    @property
    def location(self):
        return self._location

    @property
    def is_explicit(self):
        return True

    def add_attribute(self, attr):
        self._attributes.append(attr)

    @property
    def attributes(self):
        return list(self._attributes)

    @property
    def attribute_names(self):
        return set((attr.name for attr in self._attributes))

    def _to_tuple(self):
        return (self._name, self._location, tuple(self._attributes))

    def __repr__(self):
        return "Test" + repr(self._to_tuple())

    def __eq__(self, other):
        return self._to_tuple() == other._to_tuple()  # pylint: disable=protected-access

    def __hash__(self):
        return hash(self._to_tuple())


class CocoTestConfigurationVisitor(TestConfigurationVisitor):
    """
    Override VUnit's TestConfigurationVisitor to create CocoIndependentSimTestCase objects
    """
    def create_tests(self, simulator_if, elaborate_only, test_list=None):
        for config in self._get_configurations_to_run():
            test_list.add_test(
                IndependentCocoSimTestCase(
                    test=self._test,
                    config=config,
                    simulator_if=simulator_if,
                    elaborate_only=elaborate_only,
                )
            )        


@dataclass
class CocoTestAttribute:
    name: str
    value: str

