##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for building and installing Python, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import copy
import os
import re
import fileinput
import sys
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_libdir, get_software_libdir, get_software_root, get_software_version
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


EXTS_FILTER_PYTHON_PACKAGES = ('python -c "import %(ext_name)s"', "")


class EB_Python(ConfigureMake):
    """Support for building/installing Python
    - default configure/build_step/make install works fine

    To extend Python by adding extra packages there are two ways:
    - list the packages in the exts_list, this will include the packages in this Python installation
    - create a seperate easyblock, so the packages can be loaded with module load

    e.g., you can include numpy and scipy in a default Python installation
    but also provide newer updated numpy and scipy versions by creating a PythonPackage-derived easyblock for it.
    """

    def prepare_for_extensions(self):
        """
        Set default class and filter for Python packages
        """
        # build and install additional packages with PythonPackage easyblock
        self.cfg['exts_defaultclass'] = "PythonPackage"
        self.cfg['exts_filter'] = EXTS_FILTER_PYTHON_PACKAGES

        # don't pass down any build/install options that may have been specified
        # 'make' options do not make sense for when building/installing Python libraries (usually via 'python setup.py')
        msg = "Unsetting '%s' easyconfig parameter before building/installing extensions: %s"
        for param in ['buildopts', 'installopts']:
            if self.cfg[param]:
                self.log.debug(msg, param, self.cfg[param])
            self.cfg[param] = ''

    def configure_step(self):
        """Set extra configure options."""
        self.cfg.update('configopts', "--with-threads --enable-shared")

        # Need to be careful to match the unicode settings to the underlying python
        if sys.maxunicode == 1114111:
            self.cfg.update('configopts', "--enable-unicode=ucs4")
        elif sys.maxunicode == 65535:
            self.cfg.update('configopts', "--enable-unicode=ucs2")
        else:
            raise EasyBuildError("Unknown maxunicode value for your python: %d" % sys.maxunicode)

        modules_setup_dist = os.path.join(self.cfg['start_dir'], 'Modules', 'Setup.dist')

        libreadline = get_software_root('libreadline')
        if libreadline:
            ncurses = get_software_root('ncurses')
            if ncurses:
                readline_libdir = get_software_libdir('libreadline')
                ncurses_libdir = get_software_libdir('ncurses')
                readline_static_lib = os.path.join(libreadline, readline_libdir, 'libreadline.a')
                ncurses_static_lib = os.path.join(ncurses, ncurses_libdir, 'libncurses.a')
                readline = "readline readline.c %s %s" % (readline_static_lib, ncurses_static_lib)
                for line in fileinput.input(modules_setup_dist, inplace='1', backup='.readline'):
                    line = re.sub(r"^#readline readline.c.*", readline, line)
                    sys.stdout.write(line)
            else:
                raise EasyBuildError("Both libreadline and ncurses are required to ensure readline support")

        openssl = get_software_root('OpenSSL')
        if openssl:
            for line in fileinput.input(modules_setup_dist, inplace='1', backup='.ssl'):
                line = re.sub(r"^#SSL=.*", "SSL=%s" % openssl, line)
                line = re.sub(r"^#(\s*-DUSE_SSL -I)", r"\1", line)
                line = re.sub(r"^#(\s*-L\$\(SSL\)/lib )", r"\1 -L$(SSL)/lib64 ", line)
                sys.stdout.write(line)

        tcl = get_software_root('Tcl')
        tk = get_software_root('Tk')
        if tcl and tk:
            tclver = get_software_version('Tcl')
            tkver = get_software_version('Tk')
            tcltk_maj_min_ver = '.'.join(tclver.split('.')[:2])
            if tcltk_maj_min_ver != '.'.join(tkver.split('.')[:2]):
                raise EasyBuildError("Tcl and Tk major/minor versions don't match: %s vs %s", tclver, tkver)

            self.cfg.update('configopts', "--with-tcltk-includes='-I%s/include -I%s/include'" % (tcl, tk))

            tcl_libdir = os.path.join(tcl, get_software_libdir('Tcl'))
            tk_libdir = os.path.join(tk, get_software_libdir('Tk'))
            tcltk_libs = "-L%(tcl_libdir)s -L%(tk_libdir)s -ltcl%(maj_min_ver)s -ltk%(maj_min_ver)s" % {
                'tcl_libdir': tcl_libdir,
                'tk_libdir': tk_libdir,
                'maj_min_ver': tcltk_maj_min_ver,
            }
            self.cfg.update('configopts', "--with-tcltk-libs='%s'" % tcltk_libs)

        super(EB_Python, self).configure_step()

    def install_step(self):
        """Extend make install to make sure that the 'python' command is present."""
        super(EB_Python, self).install_step()

        python_binary_path = os.path.join(self.installdir, 'bin', 'python')
        if not os.path.isfile(python_binary_path):
            pythonver = '.'.join(self.version.split('.')[0:2])
            srcbin = "%s%s" % (python_binary_path, pythonver)
            try:
                os.symlink(srcbin, python_binary_path)
            except OSError, err:
                raise EasyBuildError("Failed to symlink %s to %s: %s", srcbin, python_binary_path, err)

    def sanity_check_step(self):
        """Custom sanity check for Python."""

        pyver = "python%s" % '.'.join(self.version.split('.')[0:2])

        try:
            fake_mod_data = self.load_fake_module()
        except EasyBuildError, err:
            raise EasyBuildError("Loading fake module failed: %s", err)

        abiflags = ''
        if LooseVersion(self.version) >= LooseVersion("3"):
            run_cmd("which python", log_all=True, simple=False)
            cmd = 'python -c "import sysconfig; print(sysconfig.get_config_var(\'abiflags\'));"'
            (abiflags, _) = run_cmd(cmd, log_all=True, simple=False)
            if not abiflags:
                raise EasyBuildError("Failed to determine abiflags: %s", abiflags)
            else:
                abiflags = abiflags.strip()

        custom_paths = {
            'files': ["bin/%s" % pyver, "lib/lib%s%s.%s" % (pyver, abiflags, get_shared_lib_ext())],
            'dirs': ["include/%s%s" % (pyver, abiflags), "lib/%s" % pyver],
        }

        # cleanup
        self.clean_up_fake_module(fake_mod_data)

        custom_commands = [
            ('python', '--version'),
            ('python', '-c "import _ctypes"'),  # make sure that foreign function interface (libffi) works
            ('python', '-c "import _ssl"'),  # make sure SSL support is enabled one way or another
            ('python', '-c "import readline"'),  # make sure readline support was built correctly
        ]

        super(EB_Python, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)
