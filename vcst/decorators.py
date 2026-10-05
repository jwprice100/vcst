import cocotb


def test(func=None, *, attributes=(), **kwargs):
    """
    Wrapper around cocotb.test (https://docs.cocotb.org/en/stable/library_reference.html#cocotb.test) which
    adds support for an "attributes" keyword argument.

    Used as ``@vcst.test(..., attributes=['.long_running'])`` in lieu of ``@cocotb.test(...)``.
    Like ``@cocotb.test``, it can also be used without arguments.
    """

    def decorator(func):
        test_generator = cocotb.test(**kwargs)(func)
        test_generator.attributes = list(attributes)
        return test_generator

    return decorator if func is None else decorator(func)
