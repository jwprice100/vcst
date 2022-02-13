from typing import Optional, Set, Union
from pathlib import Path
from fnmatch import fnmatch
from types import ModuleType

from vunit import VUnit 
from vunit.color_printer import COLOR_PRINTER, NO_COLOR_PRINTER
from vunit.database import PickledDataBase, DataBase
from vunit.sim_if.factory import SIMULATOR_FACTORY
from vunit.sim_if import SimulatorInterface
from vunit.vhdl_standard import VHDL, VHDLStandard
from vunit.ui.common import LOGGER, TEST_OUTPUT_PATH, select_vhdl_standard, check_not_empty
from vunit.test.bench_list import TestBenchList
from vunit.builtins import Builtins

from .library import VCSTLibrary
from ..project import VCSTProject
from ..utils.mod_utils import import_mod

class VCST(VUnit):
    def __init__(
        self,
        args,
        compile_builtins: Optional[bool] = True,
        vhdl_standard: Optional[str] = None,
    ):
        self._args = args
        self._configure_logging(args.log_level)
        self._output_path = str(Path(args.output_path).resolve())

        if args.no_color:
            self._printer = NO_COLOR_PRINTER
        else:
            self._printer = COLOR_PRINTER

        def test_filter(name, attribute_names):
            keep = any(fnmatch(name, pattern) for pattern in args.test_patterns)

            if args.with_attributes is not None:
                keep = keep and set(args.with_attributes).issubset(attribute_names)

            if args.without_attributes is not None:
                keep = keep and set(args.without_attributes).isdisjoint(attribute_names)
            return keep

        self._test_filter = test_filter
        self._vhdl_standard: VHDLStandard = select_vhdl_standard(vhdl_standard)

        self._external_preprocessors = []  # type: ignore
        self._location_preprocessor = None
        self._check_preprocessor = None

        self._simulator_class = SIMULATOR_FACTORY.select_simulator()

        # Use default simulator options if no simulator was present
        if self._simulator_class is None:
            simulator_class = SimulatorInterface
            self._simulator_output_path = str(Path(self._output_path) / "none")
        else:
            simulator_class = self._simulator_class
            self._simulator_output_path = str(
                Path(self._output_path) / simulator_class.name
            )

        self._create_output_path(args.clean)

        database = self._create_database()
        self._project = VCSTProject(
            database=database,
            depend_on_package_body=simulator_class.package_users_depend_on_bodies,
        )

        self._test_bench_list = TestBenchList(database=database)

        self._builtins = Builtins(self, self._vhdl_standard, simulator_class)
        if compile_builtins:
            self.add_builtins()
    
    def library(self, library_name: str):
        """
        Get a library

        :param library_name: The name of the library
        :returns: A :class:`.Library` object
        """
        if not self._project.has_library(library_name):
            raise KeyError(library_name)
        return VCSTLibrary(library_name, self, self._project, self._test_bench_list)


    def add_cocotb_testbench(self, cocotb_module_location, cocotb_module=None):        
        """Adds a cocotb module to a library based on variables defined in the cocotb module."""
        top_level = None
        top_level_type = None
        top_level_library = None

        if cocotb_module is None:
           cocotb_module = import_mod(cocotb_module_location)

        if hasattr(cocotb_module, "top_level"):
            top_level = getattr(cocotb_module, "top_level")
        else:
            raise RunTimeError(f"top_level not defined in cocotb module {cocotb_module}")

        if hasattr(cocotb_module, "top_level_type"):
            top_level_type = getattr(cocotb_module, "top_level_type")
        else:
            raise RunTimeError(f"top_level not defined in cocotb module {cocotb_module}")

        if hasattr(cocotb_module, "top_level_library"):
            top_level_library = getattr(cocotb_module, "top_level_library")
        else:
            raise RunTimeError(f"top_level_library not defined in cocotb module {cocotb_module}")            

        if not isinstance(top_level, str):
            raise RunTimeError(f"top_level defined in cocotb module should be a string {cocotb_module}")

        if not isinstance(top_level_type, str):
            raise RunTimeError(f"top_level_type defined in cocotb module should be a string {cocotb_module}")

        if not isinstance(top_level_library, str):
            raise RunTimeError(f"top_level_library defined in cocotb module should be a string {cocotb_module}")

        if top_level_type != "entity" or not top_level_type != "module":
            raise RunTimeError(f"Invalid top level type {top_level_type} in cocotb module {cocotb_module} specified. Please specify either entity or module.")
        
        library = self.library(top_level_library)
        top_level_design_unit = None
        
        if top_level_type == "entity":
            top_level_design_unit = library.entity(top_level, test_bench=False)
        else:
            top_level_design_unit = library.modlue(top_level, test_bench=False)

        return library.add_cocotb_testbench(top_level_design_unit, cocotb_module, cocotb_module_location)
