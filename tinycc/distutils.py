"""tinycc compiler for distutils

Provides the TinyCCompiler class, a subclass of UnixCCompiler that
handles the TinyCC compiler in Windows.  By importing this model,
the list of compilers is extended to include "tinycc".

Usage:

    # add the following to setup.py
    try:
        import tinycc.distutils
    except ImportError:
        pass  # platform doesn't have tinycc available

    # then you can do the following:
    $ python setup.py build_ext --compiler=tinycc

If you want to make tinycc available for all packages then you will
need to import tinycc.distutils as part of your site.py, or maybe
using .pth magic.
"""
from __future__ import absolute_import

import os
import sys
import copy
from subprocess import Popen, PIPE, check_output
import re

from distutils.unixccompiler import UnixCCompiler
from distutils.ccompiler import gen_lib_options, CCompiler
from distutils.errors import (DistutilsPlatformError, DistutilsExecError,
    CompileError, LinkError)
from distutils import log
from distutils.version import LooseVersion
import distutils.ccompiler

def get_msvcr():
    """Include the appropriate MSVC runtime library if Python was built
    with MSVC 7.0 or later.
    """
    msc_pos = sys.version.find('MSC v.')
    if msc_pos != -1:
        msc_ver = sys.version[msc_pos+6:msc_pos+10]
        if msc_ver == '1300':
            # MSVC 7.0
            return ['msvcr70']
        elif msc_ver == '1310':
            # MSVC 7.1
            return ['msvcr71']
        elif msc_ver == '1400':
            # VS2005 / MSVC 8.0
            return ['msvcr80']
        elif msc_ver == '1500':
            # VS2008 / MSVC 9.0
            return ['msvcr90']
        elif msc_ver == '1600':
            # VS2010 / MSVC 10.0
            return ['msvcr100']
        else:
            raise ValueError("Unknown MS Compiler version %s " % msc_ver)

class TinyCCompiler(UnixCCompiler):
    """ Handles the TinyCC compiler in Windows.
    """
    compiler_type = 'tinycc'
    obj_extension = ".o"
    static_lib_extension = ".a"
    shared_lib_extension = ".dll"
    static_lib_format = "lib%s%s"
    shared_lib_format = "%s%s"
    exe_extension = ".exe"

    def __init__(self, verbose=0, dry_run=0, force=0):
        try:
            import tinycc
        except ImportError:
            DistutilsPlatformError("tinycc not installed or not supported for this platform")


        UnixCCompiler.__init__(self, verbose, dry_run, force)

        status, details = check_config_h()
        self.debug_print("Python's GCC status: %s (details: %s)" %
                         (status, details))
        if status is not CONFIG_H_OK:
            self.warn(
                "Python's pyconfig.h doesn't seem to support your compiler. "
                "Reason: %s. "
                "Compiling may fail because of undefined preprocessor macros."
                % details)

        self.tcc_version = _find_exe_version([tinycc.TCC, '-v'])
        self.debug_print(self.compiler_type + ": tcc %s\n" % self.tcc_version)

        self.set_executables(
            compiler=[tinycc.TCC, '-DMS_WIN64', '-D__TINYCC__', '-Wall'],
            compiler_so=[tinycc.TCC, '-DMS_WIN64', '-D__TINYCC__', '-Wall'],
            compiler_cxx=[],
            linker_exe=[tinycc.TCC],
            linker_so=[tinycc.TCC, '-shared'],
        )

        # Include the appropriate MSVC runtime library if Python was built
        # with MSVC 7.0 or later.
        if os.name == 'nt':
            self.dll_libraries = get_msvcr()
        else:
            self.dll_libraries = []

    def _compile(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
        # os x
        #extra_inc = ['-I/usr/include']
        extra_inc = []
        try:
            self.spawn(self.compiler_so + extra_inc + cc_args + [src, '-o', obj]
                       + extra_postargs)
        except DistutilsExecError as msg:
            raise CompileError(msg)

    def link(self, target_desc, objects, output_filename, output_dir=None,
             libraries=None, library_dirs=None, runtime_library_dirs=None,
             export_symbols=None, debug=0, extra_preargs=None,
             extra_postargs=None, build_temp=None, target_lang=None):
        """Link the objects."""
        # use separate copies, so we can modify the lists
        libraries = copy.copy(libraries or [])
        libraries.extend(self.dll_libraries)
        if os.name == 'nt':
            sysroot = os.path.dirname(os.path.realpath(sys.executable))
            library_dirs = copy.copy(library_dirs or [])
            library_dirs.append(sysroot)

        UnixCCompiler.link(self, target_desc, objects, output_filename,
            output_dir, libraries, library_dirs, runtime_library_dirs,
            None, # export_symbols, we do this in our def-file
            debug, extra_preargs, extra_postargs, build_temp, target_lang)

    def link_osx(self, target_desc, objects, output_filename, output_dir=None,
             libraries=None, library_dirs=None, runtime_library_dirs=None,
             export_symbols=None, debug=0, extra_preargs=None,
             extra_postargs=None, build_temp=None, target_lang=None):
        """Link the objects."""
        # use separate copies, so we can modify the lists
        libraries = copy.copy(libraries or [])
        libraries.extend(self.dll_libraries)

        # Copy of unix link so we can remove the darwin test
        #UnixCCompiler.link(self, target_desc, objects, output_filename,
        #    output_dir, libraries, library_dirs, runtime_library_dirs,
        #    None, # export_symbols, we do this in our def-file
        #    debug, extra_preargs, extra_postargs, build_temp, target_lang)

        objects, output_dir = self._fix_object_args(objects, output_dir)
        libraries, library_dirs, runtime_library_dirs = \
            self._fix_lib_args(libraries, library_dirs, runtime_library_dirs)

        lib_opts = gen_lib_options(self, library_dirs, runtime_library_dirs,
                                   libraries)
        #if type(output_dir) not in (StringType, NoneType):
        #    raise TypeError("'output_dir' must be a string or None")
        if output_dir is not None:
            output_filename = os.path.join(output_dir, output_filename)

        if self._need_link(objects, output_filename):
            ld_args = (objects + self.objects +
                       lib_opts + ['-o', output_filename])
            if debug:
                ld_args[:0] = ['-g']
            if extra_preargs:
                ld_args[:0] = extra_preargs
            if extra_postargs:
                ld_args.extend(extra_postargs)
            self.mkpath(os.path.dirname(output_filename))
            try:
                if target_desc == CCompiler.EXECUTABLE:
                    linker = self.linker_exe[:]
                else:
                    linker = self.linker_so[:]
                if target_lang == "c++" and self.compiler_cxx:
                    # skip over environment variable settings if /usr/bin/env
                    # is used to set up the linker's environment.
                    # This is needed on OSX. Note: this assumes that the
                    # normal and C++ compiler have the same environment
                    # settings.
                    i = 0
                    if os.path.basename(linker[0]) == "env":
                        i = 1
                        while '=' in linker[i]:
                            i = i + 1

                    linker[i] = self.compiler_cxx[i]

                #if sys.platform == 'darwin':
                #    linker = _osx_support.compiler_fixup(linker, ld_args)
                #    ld_args = ['-arch', 'x86_64'] + ld_args

                self.spawn(linker + ld_args)
            except DistutilsExecError as msg:
                raise LinkError(msg)
        else:
            log.debug("skipping %s (up-to-date)", output_filename)




# Because these compilers aren't configured in Python's pyconfig.h file by
# default, we should at least warn the user if he is using an unmodified
# version.

CONFIG_H_OK = "ok"
CONFIG_H_NOTOK = "not ok"
CONFIG_H_UNCERTAIN = "uncertain"

def check_config_h():
    """Check if the current Python installation appears amenable to building
    extensions with TinyCC.

    Returns a tuple (status, details), where 'status' is one of the following
    constants:

    - CONFIG_H_OK: all is well, go ahead and compile
    - CONFIG_H_NOTOK: doesn't look good
    - CONFIG_H_UNCERTAIN: not sure -- unable to read pyconfig.h

    'details' is a human-readable string explaining the situation.

    Note there are two ways to conclude "OK": either 'sys.version' contains
    the string "GCC" (implying that this Python was built with GCC), or the
    installed "pyconfig.h" contains the string "__GNUC__".
    """

    # XXX since this function also checks sys.version, it's not strictly a
    # "pyconfig.h" check -- should probably be renamed...

    from distutils import sysconfig

    # if sys.version contains GCC then python was compiled with GCC, and the
    # pyconfig.h file should be OK
    if "GCC" in sys.version:
        return CONFIG_H_OK, "sys.version mentions 'GCC'"

    # let's see if __GNUC__ is mentioned in python.h
    fn = sysconfig.get_config_h_filename()
    try:
        config_h = open(fn)
        try:
            if "__GNUC__" in config_h.read():
                return CONFIG_H_OK, "'%s' mentions '__GNUC__'" % fn
            else:
                return CONFIG_H_NOTOK, "'%s' does not mention '__GNUC__'" % fn
        finally:
            config_h.close()
    except OSError as exc:
        return (CONFIG_H_UNCERTAIN,
                "couldn't read '%s': %s" % (fn, exc.strerror))

RE_VERSION = re.compile(br'(\d+\.\d+(\.\d+)*)')

def _find_exe_version(cmd):
    """Find the version of an executable by running `cmd` in the shell.

    If the command is not found, or the output does not match
    `RE_VERSION`, returns None.
    """
    out = Popen(cmd, shell=True, stdout=PIPE).stdout
    try:
        out_string = out.read()
    finally:
        out.close()
    result = RE_VERSION.search(out_string)
    if result is None:
        return None
    # LooseVersion works with strings
    # so we need to decode our bytes
    return LooseVersion(result.group(1).decode())

def add_compiler():
    distutils.ccompiler.TinyCCompiler = TinyCCompiler
    distutils.ccompiler.compiler_class['tinycc'] \
        = ('ccompiler', 'TinyCCompiler', 'TinyCC C compiler')
add_compiler()
