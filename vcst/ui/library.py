import logging
from vunit.ui.library import Library
from ..test.bench import CocoTestBench
from ..utils.mod_utils import import_mod

LOGGER = logging.getLogger(__name__)


class VCSTLibrary(Library):
    
    def add_cocotb_testbench(self, design_unit, cocotb_module):
        """
        """
        test_bench = CocoTestBench(design_unit, cocotb_module, database=None)
        self._test_bench_list._add_test_bench(test_bench)
        return self.test_bench(design_unit.name)

    def entity(self, name, test_bench=True):
        """
        Get an entity of name within the library. Returns a TestBench object if test_bench is true
        otherwise returns a DesignUnit.
        """
        name = name.lower()
        library = self._project.get_library(self._library_name)
        if not library.has_entity(name):
            raise KeyError(name)

        if test_bench:
            return self.test_bench(name)

        return library._entities[name]

    def module(self, name, test_bench=True):
        """
        Get a module of name within the library. Returns a TestBench object if test_bench is true
        otherwise returns a DesignUnit.
        """
        library = self._project.get_library(self._library_name)
        if name not in library.modules:
            raise KeyError(name)

        if test_bench:
            return self.test_bench(name)        

        return library.modules[name]

        