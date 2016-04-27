"""
tinycc compiler
===============

tinycc (or tcc) is a small, fast C compiler capable of producing DLLs that can
be loaded via ctypes.

*__version__* is the compiler version, not the version of the package.

*TCC_PATH* is the full path to the compiler executable.

*TCC* wraps *TCC_PATH* in quotes so it can be used even if it contains spaces.

Usage example::

    import os
    from tinycc import TCC

    COMPILE = TCC + " -shared -rdynamic -Wall %(source)s -o %(output)s"
    command = COMPILE%{"source":filename, "output":dll}
    status = os.system(command)
    if status != 0 or not os.path.exists(dll):
        raise RuntimeError("compile failed.  File is in %r"%filename)
    else:
        ## comment the following to keep the generated c file
        os.unlink(filename)
        #print("saving compiled file in %r"%filename)
"""
from os.path import join as joinpath, dirname, realpath

__version__ = "0.9.26"

TCC_PATH = joinpath(dirname(realpath(__file__)), 'tcc.exe')
TCC = '"%s"' % TCC_PATH
