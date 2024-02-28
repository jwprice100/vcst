from cocotb.decorators import test as cocotb_test

class test(cocotb_test):
    """
    Subclass of cocotb.decorators.test (https://docs.cocotb.org/en/stable/_modules/cocotb/decorators.html) which
    adds support for an "attributes" keyword argument.

    Used as ``@vcst.test(..., attributes=['.long_running'])`` in lieu of ``@cocotb.test(...)``.
    """
    def __init__(self, *args, **kwargs):
        self.attributes = []
        if 'attributes' in kwargs:
            self.attributes = kwargs['attributes']
            del kwargs['attributes']  # don't pass attributes kwarg to cocotb's constructor - that would error
        super().__init__(*args, **kwargs)
