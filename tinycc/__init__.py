r"""
tinycc compiler
===============

tinycc (or tcc) is a small, fast C compiler capable of producing DLLs that can
be loaded via ctypes. See `https://pypi.python.org/pypi/tinycc`_ for details.
"""

__version__ = "1.1"
TCC_VERSION = "0.9.26"  # compiler version returned by tcc -v

def compile(source, target=None):
    """
    Compile *source* into target, returning the path to target.

    If *target* is not specified, replace the source extension with ".dll"
    and use that as the target. This function does not check that source
    ends with ".c".

    Raises RuntimeError if compile fails.  The exception contains the
    compiler output.
    """
    import os, logging, subprocess

    if target is None:
        target = os.path.splitext(source)[0] + ".dll"

    command = [TCC, "-shared", "-rdynamic", "-Wall", source, "-o", target]
    command_str = " ".join('"%s"'%p if ' ' in p else p for p in command)
    logging.info(command_str)
    try:
        # need shell=True on windows to keep console box from popping up
        shell = (os.name == 'nt')
        subprocess.check_output(command, shell=shell, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("compile failed.\n%s\n%s"%(command_str, exc.output))
    if not os.path.exists(target):
        raise RuntimeError("compile failed.  File is in %r"%source)
    return target


def data_files():
    """
    Return the data files required to run tcc.
    """
    from os.path import dirname, join as joinpath
    import os
    from glob import glob

    ROOT = dirname(find_tcc_path())
    def _find_files(path, patterns):
        target = joinpath('tinycc-data', path) if path else 'tinycc-data'
        files = []
        for pattern in patterns.split(','):
            files.extend(glob(joinpath(ROOT, path, pattern)))
        return (target, files)
    result = []
    result.append(_find_files('include', '*.h'))
    for path, dirs, _ in os.walk(joinpath(ROOT, 'include')):
        relative_path = path[len(ROOT)+1:]
        for d in dirs:
            result.append(_find_files(joinpath(relative_path, d), '*.h'))
    result.append(_find_files('lib', '*'))
    result.append(_find_files('libtcc', '*'))
    result.append(_find_files('', '*.exe,*.dll'))
    return result


def find_tcc_path():
    """
    Return the path to the tcc executable.
    """
    import sys
    from os import environ
    from os.path import join as joinpath, dirname, realpath, exists
    EXE = 'tcc.exe'

    # Look for the TCC_PATH environment variable
    KEY = 'TCC_ROOT'
    if KEY in environ:
        path = joinpath(environ[KEY], EXE)
        if not exists(path):
            raise RuntimeError("%s %r does not contain %s"
                               % (KEY, environ[KEY], EXE))
        return path

    # Check in the tinycc package
    path = joinpath(dirname(realpath(__file__)), EXE)
    if exists(path):
        return path

    # Check next to exe/zip file
    path = joinpath(realpath(dirname(sys.executable)), 'tinycc-data', EXE)
    if exists(path):
        return path

    raise ImportError("Could not locate tcc.exe")


TCC = find_tcc_path()
