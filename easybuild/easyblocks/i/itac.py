# #
# Copyright 2009-2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
# #
"""
EasyBuild support for installing the Intel Trace Analyzer and Collector (ITAC), implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os

from easybuild.framework.easyconfig import CUSTOM
from easybuild.easyblocks.generic.intelbase import IntelBase
from easybuild.tools.filetools import run_cmd


class EB_itac(IntelBase):
    """
    Class that can be used to install itac
    - tested with Intel Trace Analyzer and Collector 7.2.1.008
    """

    @staticmethod
    def extra_options():
        extra_vars = [('preferredmpi', ['impi3', "Preferred MPI type (default: 'impi3')", CUSTOM])]
        return IntelBase.extra_options(extra_vars)

    def install_step(self):
        """
        Actual installation
        - create silent cfg file
        - execute command
        """

        silent = \
"""
[itac]
INSTALLDIR=%(ins)s
LICENSEPATH=%(lic)s
INSTALLMODE=NONRPM
INSTALLUSER=NONROOT
INSTALL_ITA=YES
INSTALL_ITC=YES
DEFAULT_MPI=%(mpi)s
EULA=accept
""" % {'lic': self.license_file, 'ins': self.installdir, 'mpi': self.cfg['preferredmpi']}

        # already in correct directory
        silentcfg = os.path.join(os.getcwd(), "silent.cfg")
        f = open(silentcfg, 'w')
        f.write(silent)
        f.close()
        self.log.debug("Contents of %s: %s" % (silentcfg, silent))

        tmpdir = os.path.join(os.getcwd(), self.version, 'mytmpdir')
        try:
            os.makedirs(tmpdir)
        except:
            self.log.exception("Directory %s can't be created" % (tmpdir))

        cmd = "./install.sh --tmp-dir=%s --silent=%s" % (tmpdir, silentcfg)

        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check paths for ITAC."""

        custom_paths = {
                        'files': ["include/%s" % x for x in ["i_malloc.h", "VT_dynamic.h", "VT.h", "VT.inc"]],
                        'dirs': ["bin", "itac", "lib", "slib"]
                       }

        super(EB_itac, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        preferredmpi = self.cfg["preferredmpi"]
        guesses = {
                   'MANPATH': ['man'],
                   'CLASSPATH': ['itac/lib_%s' % preferredmpi],
                   'VT_LIB_DIR': ['itac/lib_%s' % preferredmpi],
                   'VT_SLIB_DIR': ['itac/lib_s%s' % preferredmpi]
                  }

        if self.cfg['m32']:
            guesses.update({
                            'PATH': ['bin', 'bin/ia32', 'ia32/bin'],
                            'LD_LIBRARY_PATH': ['lib', 'lib/ia32', 'ia32/lib'],
                           })
        else:
            guesses.update({
                            'PATH': ['bin', 'bin/intel64', 'bin64'],
                            'LD_LIBRARY_PATH': ['lib', 'lib/intel64', 'lib64'],
                           })
        return guesses

    def make_module_extra(self):
        """Overwritten from IntelBase to add extra txt"""
        txt = super(EB_itac, self).make_module_extra()
        txt += "prepend-path\t%s\t\t%s\n" % (self.license_env_var, self.license_file)
        txt += "setenv\t%s\t\t$root\n" % 'VT_ROOT'
        txt += "setenv\t%s\t\t%s\n" % ('VT_MPI', self.cfg['preferredmpi'])
        txt += "setenv\t%s\t\t%s\n" % ('VT_ADD_LIBS', '"-ldwarf -lelf -lvtunwind -lnsl -lm -ldl -lpthread"')

        return txt
