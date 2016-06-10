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
EasyBuild support for building and installing VSC-tools, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import glob
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_VSC_minus_tools(PythonPackage):
    """Support for building/installing VSC-tools."""

    def build_step(self):
        """No build procedure for VSC-tools."""

        pass

    def install_step(self):
        """Custom install procedure for VSC-tools."""

        args = "install --prefix=%(path)s --install-lib=%(path)s/lib" % {'path': self.installdir}

        pylibdir = os.path.join(self.installdir, 'lib')
        env.setvar('PYTHONPATH', '%s:%s' % (pylibdir, os.getenv('PYTHONPATH')))

        try:
            os.mkdir(pylibdir)

            pwd = os.getcwd()

            pkg_list = ['-'.join(src['name'].split('-')[0:-1]) for src in self.src if src['name'].startswith('vsc')]
            for pkg in pkg_list:
                os.chdir(self.builddir)
                sel_dirs = [d for d in glob.glob("*%s-[0-9][0-9.]*" % pkg)]
                if not len(sel_dirs) == 1:
                    raise EasyBuildError("Found none or more than one %s dir in %s: %s", pkg, self.builddir, sel_dirs)

                os.chdir(os.path.join(self.builddir, sel_dirs[0]))
                cmd = "%s setup.py %s" % (self.python_cmd, args)
                run_cmd(cmd, log_all=True, simple=True, log_output=True)

            os.chdir(pwd)

        except OSError, err:
            raise EasyBuildError("Failed to install: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for VSC-tools."""

        custom_paths = {
            'files': ['bin/%s' % x for x in ['ihmpirun', 'impirun', 'logdaemon', 'm2hmpirun',
                                             'm2mpirun', 'mhmpirun', 'mmmpirun', 'mmpirun',
                                             'mympirun', 'mympisanity', 'myscoop', 'ompirun',
                                             'pbsssh', 'qmpirun', 'sshsleep', 'startlogdaemon',
                                             'fake/mpirun']],
            'dirs': ['lib'],
        }

        super(EB_VSC_minus_tools, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Add install path to PYTHONPATH"""

        txt = super(EB_VSC_minus_tools, self).make_module_extra()

        txt += self.module_generator.prepend_paths('PATH', ["bin/fake"])
        txt += self.module_generator.prepend_paths('PYTHONPATH', ["lib"])

        return txt
