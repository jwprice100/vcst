#Replaces some of VUnit's simulator logic for Riviera in order to deal with environment variables.
from pathlib import Path
import vunit
from vunit.sim_if.vsim_simulator_mixin import fix_path
from vunit.sim_if.rivierapro import RivieraProInterface
from vunit.sim_if.modelsim import ModelSimInterface
from vunit.persistent_tcl_shell import PersistentTclShell
from vunit.ostools import write_file, Process

def set_env_var(self, env):
    """Sets environment variables by setting them in tcl. This is accomplished by interacting with 
       the simulator via stdin.
    """
    #For some reason, there are times were writes to stdin are truncated if they are to long. Back to back writes seem to work, 
    #so chunk up those writes.
    
    C_MAX_CHARS = 1024
    process = self._process()    
    for var in env:
        var_value = env[var]
        var_value = env[var].replace('{', '\\{').replace('}', '\\}')
        
        if ';' in var_value or '\n' in var_value:
            continue
        
        #Initialize a temp variable to hold the intermediate value
        process.writeline('set vcst_env_var ""')
        #Figure out how many write chunks
        num_writes = len(var_value) // C_MAX_CHARS
        if len(var_value) % C_MAX_CHARS != 0:
            num_writes += 1
        
        #Append each chunk of the desired environment variable to the temp variable
        for i in range(num_writes):
            sub_str = var_value[i*C_MAX_CHARS:(i+1)*C_MAX_CHARS]
            process.writeline(f'append vcst_env_var "{sub_str}"')
        
        #Then set the environment variable to the temp value
        set_env_str = f"set ::env({var}) $vcst_env_var"
        process.writeline(set_env_str)        

def rivierapro_run_batch_file(self, batch_file_name, gui=False, env=None):
    """
    Run a test bench in batch by invoking a new vsim process from the command line
    """

    try:
        args = [
            str(Path(self._prefix) / "vsim"),
            "-gui" if gui else "-c",
            "-l",
            str(Path(batch_file_name).parent / "transcript"),
            "-do",
            'source "%s"' % fix_path(batch_file_name),
        ]

        proc = Process(args, cwd=str(Path(self._sim_cfg_file_name).parent), env=env)
        proc.consume_output()
    except Process.NonZeroExitCode:
        return False
    return True

def rivierapro_run_persistent(self, common_file_name, load_only=False, env=None):
    """
    Run a test bench using the persistent vsim process
    """
    try:
        if env is not None:
            self._persistent_shell.set_env_var(env)

        self._persistent_shell.execute('source "%s"' % fix_path(common_file_name))
        self._persistent_shell.execute("set failed [vunit_load]")
        if self._persistent_shell.read_bool("failed"):
            return False

        run_ok = True
        if not load_only:
            self._persistent_shell.execute("set failed [vunit_run]")
            run_ok = not self._persistent_shell.read_bool("failed")
        self._persistent_shell.execute("quit -sim")
        return run_ok
    except Process.NonZeroExitCode:
        return False    

def rivierapro_simulate(self, output_path, test_suite_name, config, elaborate_only, env=None):
    """
    Run a test bench
    """
    script_path = Path(output_path) / self.name

    common_file_name = script_path / "common.do"
    gui_file_name = script_path / "gui.do"
    batch_file_name = script_path / "batch.do"

    write_file(
        str(common_file_name),
        self._create_common_script(
            test_suite_name, config, script_path, output_path
        ),
    )
    write_file(
        str(gui_file_name), self._create_gui_script(str(common_file_name), config)
    )
    write_file(
        str(batch_file_name),
        self._create_batch_script(str(common_file_name), elaborate_only),
    )

    if self._gui:
        return self._run_batch_file(str(gui_file_name), gui=True, env=env)

    if self._persistent_shell is not None:
        return self._run_persistent(str(common_file_name), load_only=elaborate_only, env=env)

    return self._run_batch_file(str(batch_file_name), env=env)

def is_iterable(obj):
   try:
      iterator = iter(obj)
      return True
   except TypeError:
      return False

def format_generic(value):
   if not isinstance(value, str) and is_iterable(value):
      value_str = "("
      for item in value:
         value_str = value_str + format_generic(item) + ","         
      #Remove the comma at the end
      value_str = value_str[0:len(value_str)-1] + ")"
      return value_str
   else:
       value_str = str(value)
       if " " in value_str or type(value) is str:
           return f'"{value_str}"'
       return value_str    

class ReadVarOutputConsumer(object):
    """
    Consume output from modelsim and print with indentation
    """

    def __init__(self):
        self.var = None

    def __call__(self, line):
        if "#VUNIT_READVAR=" in line:
            self.var = line.split("#VUNIT_READVAR=")[-1].strip()
            return True

###############################################################
PersistentTclShell.set_env_var = set_env_var
vunit.persistent_tcl_shell.ReadVarOutputConsumer = ReadVarOutputConsumer
vunit.sim_if.rivierapro.format_generic = format_generic
RivieraProInterface._run_persistent = rivierapro_run_persistent
RivieraProInterface._run_batch_file = rivierapro_run_batch_file
RivieraProInterface.simulate = rivierapro_simulate    
