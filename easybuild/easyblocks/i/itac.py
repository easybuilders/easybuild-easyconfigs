##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
EasyBuild support for installing the Intel Trace Analyzer and Collector (ITAC), implemented as an easyblock
"""

import os

from easybuild.framework.easyconfig import CUSTOM
from easybuild.easyblocks.intelbase import EB_IntelBase
from easybuild.tools.filetools import run_cmd


class EB_itac(EB_IntelBase):
    """
    Class that can be used to install itac
    - tested with Intel Trace Analyzer and Collector 7.2.1.008
    """

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra config options"""
        EB_IntelBase.__init__(self, *args, **kwargs)

    @staticmethod
    def extra_options():
        extra_vars = [('preferredmpi', ['impi3', "Preferred MPI type (default: 'impi3')", CUSTOM])]
        return EB_IntelBase.extra_options(extra_vars)

    def make_install(self):
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
""" % {'lic': self.license, 'ins': self.installdir, 'mpi': self.getcfg('preferredmpi')}

        # already in correct directory
        silentcfg = os.path.join(os.getcwd(), "silent.cfg")
        f = open(silentcfg, 'w')
        f.write(silent)
        f.close()

        tmpdir = os.path.join(os.getcwd(), self.version(), 'mytmpdir')
        try:
            os.makedirs(tmpdir)
        except:
            self.log.exception("Directory %s can't be created" % (tmpdir))

        cmd = "./install.sh --tmp-dir=%s --silent=%s" % (tmpdir, silentcfg)

        run_cmd(cmd, log_all=True, simple=True)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        preferredmpi = self.getcfg("preferredmpi")
        guesses = {
                   'MANPATH': ['man'],
                   'CLASSPATH': ['itac/lib_%s' % preferredmpi],
                   'VT_LIB_DIR': ['itac/lib_%s' % preferredmpi],
                   'VT_SLIB_DIR': ['itac/lib_s%s' % preferredmpi]
                  }

        if self.getcfg('m32'):
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
        """Overwritten from EB_IntelBase to add extra txt"""
        txt = EB_IntelBase.make_module_extra(self)
        txt += "prepend-path\t%s\t\t%s\n" % ('INTEL_LICENSE_FILE', self.license)
        txt += "setenv\t%s\t\t$root\n" % 'VT_ROOT'
        txt += "setenv\t%s\t\t%s\n" % ('VT_MPI', self.getcfg('preferredmpi'))
        txt += "setenv\t%s\t\t%s\n" % ('VT_ADD_LIBS', '"-ldwarf -lelf -lvtunwind -lnsl -lm -ldl -lpthread"')

        return txt
