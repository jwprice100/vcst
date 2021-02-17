import cocotb
from .mod_utils import get_calling_module

def set_top_level(top_level, top_level_type, top_level_library):
    """
        Used to set the top level, top level type and top level library
        associated with a particular cocotb module.
    """
    mod = get_calling_module()
    setattr(mod, "top_level", top_level)
    setattr(mod, "top_level_type", top_level_type)
    setattr(mod, "top_level_library", top_level_library)

def parameterize_test(coroutine, test_name, *args, **kwargs):
    """
        An alternative to test factory. A single coroutine with multiple arguments can be turned
        into a test using this function. Such coroutines must accept the dut as their first 
        arguments. 
    """
    mod = get_calling_module()
    def test_maker(*args, **kwargs):
        async def test_helper(dut):
            await coroutine(dut, *args, **kwargs)
        test_helper.__name__ = test_name
        
        #Cocotb uses the __qualname__ for it's results, but test_name to execute.
        #This makes them the same.
        test_helper.__qualname__ = test_name
        
        test_helper.__doc__ = "None"
        test_helper.__module__ = mod.__name__
        return cocotb.test()(test_helper)

    test = test_maker(*args, **kwargs)
    
    if hasattr(mod, test_name):
        raise Exception(f"{test_name} is already defined on cocotb module {mod.__name__}")
    
    setattr(mod, test_name, test)
    return test
