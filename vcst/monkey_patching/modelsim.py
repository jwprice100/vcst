#Replaces some of VUnit's simulator logic for Moselsim in order to deal with environment variables.
from pathlib import Path
import vunit
from vunit.sim_if.rivierapro import RivieraProInterface
from vunit.sim_if.modelsim import ModelSimInterface
from vunit.persistent_tcl_shell import PersistentTclShell

# Just point functions back to Riviera, because modelsim works the same way basically
vunit.sim_if.modelsim.format_generic = vunit.sim_if.rivierapro.format_generic
ModelSimInterface._run_persistent = RivieraProInterface._run_persistent
ModelSimInterface._run_batch_file = RivieraProInterface._run_batch_file
ModelSimInterface.simulate = RivieraProInterface.simulate