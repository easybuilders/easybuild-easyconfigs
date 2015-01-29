##
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
##
"""
EasyBuild support for GAMESS-US

@author: Benjamin Roberts (The University of Auckland)
"""

import sys, os
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.icc import get_icc_version
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
import easybuild.tools.toolchain as toolchain

class EB_GAMESS_minus_US(ConfigureMake):

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to WRF."""
        super(EB_GAMESS_minus_US, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

    def extract_step(self):
        self.cfg['unpack_options'] = "--strip-components=1"
        super(EB_GAMESS_minus_US, self).extract_step()

    def configure_step(self, cmd_prefix=''):

        if self.cfg['configure_cmd_prefix']:
            if cmd_prefix:
                tup = (cmd_prefix, self.cfg['configure_cmd_prefix'])
                self.log.debug("Specified cmd_prefix '%s' is overridden by configure_cmd_prefix '%s'" % tup)
            cmd_prefix = self.cfg['configure_cmd_prefix']

        if self.toolchain.comp_family() == toolchain.INTELCOMP:
            compiler = 'ifort'
            compver = '.'.join(get_icc_version().split('.')[:1])
        elif self.toolchain.comp_family() == toolchain.GCC:
            compiler = 'gfortran'
            compver = '.'.join(get_software_version('GCC').split('.')[:2])

        # Still need support for ACML and ATLAS.
        if get_software_root('imkl'):
            mathlib = 'mkl'
            mathlibdir = os.path.join(os.getenv('EBROOTIMKL'),'mkl')
        else:
            self.log.error("Only the Intel MKL is currently supported by this EasyBlock.")
            mathlib = 'none'

        # Still need support for MVAPICH2 and MPT.
        # "Sockets" is the non-MPI option at this point.
        if get_software_root('impi'):
            mpiimpl = 'impi'
            mpidir = os.getenv('EBROOTIMPI')
        else:
            self.log.error("Only the Intel MPI is currently supported by this EasyBlock.")
            mpiimpl = 'sockets'
        
        print 'start_dir: ' + self.cfg['start_dir']
        print 'installdir: ' + self.installdir

        configanswers = """<< EOF

linux64
{0}
{1}
00
{2}
{3}

{4}
{5}
skip


mpi
{6}
{7}
no

EOF"""
        configopts = self.cfg['configopts'] + configanswers.format(self.cfg['start_dir'],self.installdir,compiler,compver,mathlib,mathlibdir,mpiimpl,mpidir)
        cmd = "%(preconfigopts)s %(cmd_prefix)s./config %(configopts)s" % {
            'preconfigopts': self.cfg['preconfigopts'],
            'cmd_prefix': cmd_prefix,
            'configopts': configopts,
        }

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

    def build_step(self, verbose=False, path=None):
        """
        Start the actual build
        - typical: make -j X
        """
        
        compall = os.path.join(self.cfg['start_dir'], 'compall')
        cmd = "%s %s %s" % (self.cfg['prebuildopts'], compall, self.cfg['buildopts'])

        (out, _) = run_cmd(cmd, path=path, log_all=True, simple=False, log_output=verbose)

        return out

    def test_step(self):
        """
        Test the compilation
        - default: None
        """

        if self.cfg['runtest']:
            cmd = "make %s" % (self.cfg['runtest'])
            (out, _) = run_cmd(cmd, log_all=True, simple=False)

            return out

    def install_step(self):
        """
        Create the installation in correct location
        - typical: make install
        """

        cmd = "%s make install %s" % (self.cfg['preinstallopts'], self.cfg['installopts'])

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out
