from pathlib import Path
import os
from os import makedirs, remove
import shlex
import subprocess
from sys import stdout
from vunit.sim_if.nvc import NVCInterface
from vunit.ostools import Process

def simulate(self, output_path, test_suite_name, config, elaborate_only, env=None):
    """
    Simulate with entity as top level using generics
    """
    if env is None:
        env = os.environ.copy()

    script_path = Path(output_path) / self.name

    if not script_path.exists():
        makedirs(script_path)

    libdir = self._project.get_library(config.library_name).directory
    cmd = self._get_command(self._vhdl_standard, config.library_name, libdir)

    if self._gui:
        wave_file = script_path / (f"{config.entity_name}.{self._viewer_fmt or 'fst'}")
        if wave_file.exists():
            remove(wave_file)
    else:
        wave_file = None

    if self._ieee_warnings_global and config.sim_options.get("disable_ieee_warnings", False):
        cmd += ["--ieee-warnings=off"]

    cmd += ["-H", config.sim_options.get("nvc.heap_size", "64m")]
    cmd += config.sim_options.get("nvc.global_flags", [])

    cmd += ["-e"]

    cmd += config.sim_options.get("nvc.elab_flags", [])

    if config.sim_options.get("enable_coverage", False):
        coverage_file_path = str(Path(output_path) / "coverage.ncdb")
        self._coverage_files.add(coverage_file_path)
        cmd += [f"--cover-file={coverage_file_path}"]

    if config.vhdl_configuration_name is not None:
        cmd += [config.vhdl_configuration_name]
    else:
        cmd += [f"{config.entity_name}-{config.architecture_name}"]

    for name, value in config.generics.items():
        cmd += [f"-g{name}={value}"]

    if not elaborate_only:
        cmd += ["--no-save"]
        if self._supports_jit:
            cmd += ["--jit"]
        cmd += ["-r"]

        cmd += config.sim_options.get("nvc.sim_flags", [])
        cmd += [f"--exit-severity={config.vhdl_assert_stop_level}"]

        if not self._ieee_warnings_global and config.sim_options.get("disable_ieee_warnings", False):
            cmd += ["--ieee-warnings=off"]

        if wave_file:
            cmd += [f"--wave={wave_file}"]

        if self._viewer_fmt:
            cmd += [f"--format={self._viewer_fmt}"]

    print(" ".join([f"'{word}'" if " " in word else word for word in cmd]))

    status = True

    try:
        proc = Process(cmd, env=env)
        proc.consume_output()
    except Process.NonZeroExitCode:
        status = False

    if self._gui and not elaborate_only:
        cmd = [self._get_viewer(config)] + shlex.split(self._viewer_args) + [str(wave_file)]

        init_file = config.sim_options.get(
            self.name + ".viewer_script.gui",
            config.sim_options.get(self.name + ".gtkwave_script.gui", None),
        )
        if init_file is not None:
            cmd += ["--script", str(Path(init_file).resolve())]

        stdout.write(f'{" ".join(cmd)}\n')
        subprocess.call(cmd)

    return status

NVCInterface.simulate = simulate
