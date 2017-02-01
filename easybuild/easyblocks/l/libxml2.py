##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for building and installing libxml2 with python bindings,
implemented as an easyblock.

@author: Jens Timmerman (Ghent University)
@author: Alan O'Cais (Juelich Supercomputing Centre)
@author: Kenneth Hoste (Ghent University)
"""
from distutils.version import LooseVersion
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.systemtools import get_shared_lib_ext
from easybuild.tools.toolchain import DUMMY_TOOLCHAIN_NAME


class EB_libxml2(ConfigureMake, PythonPackage):
    """Support for building and installing libxml2 with python bindings"""

    @staticmethod
    def extra_options(extra_vars=None):
        """Easyconfig parameters specific to libxml2."""
        extra_vars = ConfigureMake.extra_options()
        return PythonPackage.extra_options(extra_vars=extra_vars)

    def __init__(self, *args, **kwargs):
        """
        Constructor: initialize via PythonPackage,
        to ensure everything is set up as needed to build with Python bindings
        """
        PythonPackage.__init__(self, *args, **kwargs)
        self.with_python_bindings = False

    def configure_step(self):
        """
        Configure libxml2 build
        """
        # only build with Python bindings if Python is listed as a dependency
        python = get_software_root('Python')
        if python:
            self.with_python_bindings = True

        if self.toolchain.name != DUMMY_TOOLCHAIN_NAME:
            self.cfg.update('configopts', "CC='%s' CXX='%s'" % (os.getenv('CC'), os.getenv('CXX')))

        if self.toolchain.options.get('pic', False):
            self.cfg.update('configopts', '--with-pic')

        zlib = get_software_root('zlib')
        if zlib:
            self.cfg.update('configopts', '--with-zlib=%s' % zlib)

        # enable building of Python bindings if Python is a dependency (or build them ourselves for old versions)
        # disable building of Python bindings if Python is not a dependency
        if self.with_python_bindings and LooseVersion(self.version) >= LooseVersion('2.9.2'):
                libxml2_pylibdir = os.path.join(self.installdir, self.pylibdir)
                self.cfg.update('configopts', "--with-python=%s" % os.path.join(python, 'bin', 'python'))
                self.cfg.update('configopts', "--with-python-install-dir=%s" % libxml2_pylibdir)
        else:
            self.cfg.update('configopts', '--without-python')

        ConfigureMake.configure_step(self)

        if self.with_python_bindings:
            # prepare for installing Python package
            PythonPackage.prepare_python(self)

        # test using 'make check' (done via test_step)
        self.cfg['runtest'] = 'check'

    def install_step(self):
        """
        Custom install step for libxml2;
        also build Python bindings ourselves if desired (only for older libxml2 versions
        """
        ConfigureMake.install_step(self)

        if self.with_python_bindings and LooseVersion(self.version) < LooseVersion('2.9.2'):
            try:
                # We can only do the Python bindings after the initial installation
                # since setup.py expects to find the include dir in the installation path
                # and that only exists after installation
                os.chdir('python')
                PythonPackage.configure_step(self)
                # set cflags to point to include folder for the compilation step to succeed
                env.setvar('CFLAGS', "-I../include")
                PythonPackage.build_step(self)
                PythonPackage.install_step(self)
                os.chdir('..')
            except OSError as err:
                raise EasyBuildError("Failed to install libxml2 Python bindings: %s", err)

    def make_module_extra(self):
        """
        Add python bindings to the pythonpath
        """
        if self.with_python_bindings:
            txt = PythonPackage.make_module_extra(self)
        else:
            txt = super(EB_libxml2, self).make_module_extra()

        txt += self.module_generator.prepend_paths('CPATH', [os.path.join('include', 'libxml2')])
        return txt

    def sanity_check_step(self):
        """Custom sanity check for libxml2"""
        shlib_ext = get_shared_lib_ext()
        custom_paths = {
            'files': [('lib/libxml2.a', 'lib64/libxml2.a'),
                      ('lib/libxml2.%s' % shlib_ext, 'lib64/libxml2.%s' % shlib_ext)],
            'dirs': ['bin', 'include/libxml2/libxml'],
        }

        if self.with_python_bindings:
            pyfiles = ['libxml2mod.%s' % shlib_ext, 'libxml2.py', 'drv_libxml2.py']
            custom_paths['files'].extend([os.path.join(self.pylibdir, f) for f in pyfiles])
            custom_paths['dirs'].append(self.pylibdir)

        ConfigureMake.sanity_check_step(self, custom_paths=custom_paths)
