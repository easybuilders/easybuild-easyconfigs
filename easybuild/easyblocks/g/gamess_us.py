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
import fileinput, re
import time
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
        self.gamess_build = time.strftime("%Y%m%d")
        self.connectivity = 'sockets'
        self.mpiimpl = ''
        self.mpidir = '' 

    def extract_step(self):
        self.cfg['unpack_options'] = "--strip-components=1"
        super(EB_GAMESS_minus_US, self).extract_step()

    def patch_step(self):
        """ Patch, then amend one of the patched files with values from the config. """

        super(EB_GAMESS_minus_US, self).patch_step()

        rungms = os.path.join(self.builddir, "rungms")
        try:
            for line in fileinput.input(rungms, inplace=1, backup='.orig'):
                line = re.sub(r"self.builddir", r"%s" % self.builddir, line)
                line = re.sub(r"self.connectivity", r"%s" % self.connectivity, line)
                line = re.sub(r"self.gamess_build", r"%s" % self.gamess_build, line)
                line = re.sub(r"self.installdir", r"%s" % self.installdir, line)
                line = re.sub(r"self.mpidir", r"%s" % self.mpidir, line)
                line = re.sub(r"self.mpiimpl", r"%s" % self.mpiimpl, line)
                sys.stdout.write(line)
        except IOError, err:
            self.log.error("Failed to patch %s: %s" % (fn, err))

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
            self.connectivity = 'mpi'
            self.mpiimpl = 'impi'
            self.mpidir = os.getenv('EBROOTIMPI')
        else:
            self.log.error("Only the Intel MPI is currently supported by this EasyBlock.")
        
        configanswers = """<< EOF

linux64
{builddir}
{installdir}
{gamess_build}
{compiler}
{compver}

{mathlib}
{mathlibdir}
skip


mpi
{mpiimpl}
{mpidir}
no

EOF"""
        configopts = self.cfg['configopts'] + configanswers.format(builddir=self.builddir,
                compiler=compiler,compver=compver,installdir=self.installdir,
                mathlib=mathlib,mathlibdir=mathlibdir,
                mpiimpl=self.mpiimpl,mpidir=self.mpidir,gamess_build=self.gamess_build)
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
        """

        compddi = os.path.join(self.builddir, 'ddi', 'compddi')
        (compddi_out, _) = run_cmd(compddi, path=path, log_all=True, simple=False, log_output=verbose)
        
        compall = os.path.join(self.builddir, 'compall')
        compall_cmd = "%s %s %s" % (self.cfg['prebuildopts'], compall, self.cfg['buildopts'])
        (compall_out, _) = run_cmd(compall_cmd, path=path, log_all=True, simple=False, log_output=verbose)

        lked = os.path.join(self.builddir, 'lked')
        lked_cmd = "%s %s %s" % (lked, 'gamess', self.gamess_build)
        (lked_out, _) = run_cmd(lked_cmd, path=path, log_all=True, simple=False, log_output=verbose)

        out = compddi_out + compall_out + lked_out
        return out

    def test_step(self):
        """
        Test the compilation
        """
        runall = os.path.join(self.builddir, 'runall')
        runall_cmd = "%s %s" % (runall, self.gamess_build)
        (out, _) = run_cmd(runall_cmd, path=self.builddir, log_all=True, simple=False)

        return out

    def install_step(self):
        """Skip install step, since we're building in the install directory."""
        pass

    def sanity_check_step(self):
        """Custom sanity check for XCrySDen."""

        custom_paths = {'files': [ "gamess.%s.x" % self.gamess_build ],
                        'dirs': []
                        }

        super(EB_GAMESS_minus_US, self).sanity_check_step(custom_paths=custom_paths)
