import os
import sys

def import_mod(module_path):
    """Imports a module given a path to the module. Handles splitting the path off and changing
       directories, then changing back.
    """
    old_dir = os.getcwd()
    old_path = sys.path
    mod_dir, mod_name = os.path.split(module_path)

    if mod_dir != "":
        os.chdir(mod_dir)
        sys.path.append(os.getcwd())

    mod = __import__(mod_name)
    components = mod_name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)

    os.chdir(old_dir)    
    sys.path = old_path
    return mod

