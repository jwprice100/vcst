from pathlib import Path
import os
from vunit.sim_if.ghdl import GHDLInterface
from vunit.ostools import write_file, Process

def simulate(self, output_path, test_suite_name, config, elaborate_only, env=None):
    """
    Simulate with entity as top level using generics
    """

    if env is None:
        env = os.environ.copy()

    script_path = str(Path(output_path) / self.name)

    if not Path(script_path).exists():
        os.makedirs(script_path)

    ghdl_e = elaborate_only and config.sim_options.get("ghdl.elab_e", False)

    if self._gtkwave_fmt is not None:
        data_file_name = str(Path(script_path) / ("wave.%s" % self._gtkwave_fmt))
        if Path(data_file_name).exists():
            remove(data_file_name)
    else:
        data_file_name = None

    cmd = self._get_command(
        config, script_path, elaborate_only, ghdl_e, data_file_name
    )

    status = True
    if config.sim_options.get("enable_coverage", False):
        # Set environment variable to put the coverage output in the test_output folder
        coverage_dir = str(Path(output_path) / "coverage")
        env["GCOV_PREFIX"] = coverage_dir
        self._coverage_test_dirs.add(coverage_dir)

    try:
        proc = Process(cmd, env=env)
        proc.consume_output()
    except Process.NonZeroExitCode:
        status = False

    if self._gui and not elaborate_only:
        cmd = ["gtkwave"] + shlex.split(self._gtkwave_args) + [data_file_name]

        init_file = config.sim_options.get(self.name + ".gtkwave_script.gui", None)
        if init_file is not None:
            cmd += ["--script", "{}".format(str(Path(init_file).resolve()))]

        stdout.write("%s\n" % " ".join(cmd))
        subprocess.call(cmd)

    return status

GHDLInterface.simulate = simulate