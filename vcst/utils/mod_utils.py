import inspect
import os
import sys

def get_module(stack_level):
    """
        Get a reference to the module at some level of the stack.
    """
    stack = inspect.stack()
    if stack_level >= len(stack):
        raise Exception("Stack level was to large.")

    #+1 because this function is on the stack!
    frame = inspect.stack()[stack_level+1]

    #Get the module from the right frame.
    
    mod = inspect.getmodule(frame[0])
    return mod

def get_calling_module():
    #This function is on the stack already, so we want to get the one who called this.
    mod = get_module(2)
    return mod

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

