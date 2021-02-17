#Replaces some of VUnit's simulator logic for Riviera in order to deal with environment variables.
from pathlib import Path
from vunit.sim_if.vsim_simulator_mixin import fix_path
from vunit.sim_if.rivierapro import RivieraProInterface
from vunit.persistent_tcl_shell import PersistentTclShell
from vunit.ostools import write_file, Process

def set_env_var(self, env):
    process = self._process()
    for var in env:
        set_env_str = f"set ::env({var}) {env[var]}"
        set_env_str = set_env_str.replace("\n", "\\n")
        #print(set_env_str)
        #print(set_env_str.find("\n") != -1)
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

###############################################################
PersistentTclShell.set_env_var = set_env_var
RivieraProInterface._run_persistent = rivierapro_run_persistent
RivieraProInterface._run_batch_file = rivierapro_run_batch_file
RivieraProInterface.simulate = rivierapro_simulate    