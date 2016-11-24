# #
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
# #
"""
EasyBuild support for installing the Intel MPI library, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import fileinput
import os
import re
import sys
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_impi(IntelBase):
    """
    Support for installing Intel MPI library
    """
    @staticmethod
    def extra_options():
        extra_vars = {
            'set_mpi_wrappers_compiler': [False, 'Override default compiler used by MPI wrapper commands', CUSTOM],
            'set_mpi_wrapper_aliases_gcc': [False, 'Set compiler for mpigcc/mpigxx via aliases', CUSTOM],
            'set_mpi_wrapper_aliases_intel': [False, 'Set compiler for mpiicc/mpiicpc/mpiifort via aliases', CUSTOM],
            'set_mpi_wrappers_all': [False, 'Set (default) compiler for all MPI wrapper commands', CUSTOM],
        }
        return IntelBase.extra_options(extra_vars)

    def install_step(self):
        """
        Actual installation
        - create silent cfg file
        - execute command
        """
        impiver = LooseVersion(self.version)
        if impiver >= LooseVersion('4.0.1'):
            # impi starting from version 4.0.1.x uses standard installation procedure.

            silent_cfg_names_map = {}

            if impiver < LooseVersion('4.1.1'):
                # since impi v4.1.1, silent.cfg has been slightly changed to be 'more standard'
                silent_cfg_names_map.update({
                    'activation_name': ACTIVATION_NAME_2012,
                    'license_file_name': LICENSE_FILE_NAME_2012,
                })

            super(EB_impi, self).install_step(silent_cfg_names_map=silent_cfg_names_map)

            # impi v4.1.1 and v5.0.1 installers create impi/<version> subdir, so stuff needs to be moved afterwards
            if impiver == LooseVersion('4.1.1.036') or impiver >= LooseVersion('5.0.1.035'):
                super(EB_impi, self).move_after_install()
        else:
            # impi up until version 4.0.0.x uses custom installation procedure.
            silent = \
"""
[mpi]
INSTALLDIR=%(ins)s
LICENSEPATH=%(lic)s
INSTALLMODE=NONRPM
INSTALLUSER=NONROOT
UPDATE_LD_SO_CONF=NO
PROCEED_WITHOUT_PYTHON=yes
AUTOMOUNTED_CLUSTER=yes
EULA=accept
[mpi-rt]
INSTALLDIR=%(ins)s
LICENSEPATH=%(lic)s
INSTALLMODE=NONRPM
INSTALLUSER=NONROOT
UPDATE_LD_SO_CONF=NO
PROCEED_WITHOUT_PYTHON=yes
AUTOMOUNTED_CLUSTER=yes
EULA=accept

""" % {'lic': self.license_file, 'ins': self.installdir}

            # already in correct directory
            silentcfg = os.path.join(os.getcwd(), "silent.cfg")
            try:
                f = open(silentcfg, 'w')
                f.write(silent)
                f.close()
            except:
                raise EasyBuildError("Writing silent cfg file %s failed.", silent)
            self.log.debug("Contents of %s: %s" % (silentcfg, silent))

            tmpdir = os.path.join(os.getcwd(), self.version, 'mytmpdir')
            try:
                os.makedirs(tmpdir)
            except:
                raise EasyBuildError("Directory %s can't be created", tmpdir)

            cmd = "./install.sh --tmp-dir=%s --silent=%s" % (tmpdir, silentcfg)
            run_cmd(cmd, log_all=True, simple=True)

    def post_install_step(self):
        """Custom post install step for IMPI, fix broken env scripts after moving installed files."""
        super(EB_impi, self).post_install_step()

        impiver = LooseVersion(self.version)
        if impiver == LooseVersion('4.1.1.036') or impiver >= LooseVersion('5.0.1.035'):
            # fix broken env scripts after the move
            for script in [os.path.join('intel64', 'bin', 'mpivars.csh'), os.path.join('mic', 'bin', 'mpivars.csh')]:
                for line in fileinput.input(os.path.join(self.installdir, script), inplace=1, backup='.orig.easybuild'):
                    line = re.sub(r"^setenv I_MPI_ROOT.*", "setenv I_MPI_ROOT %s" % self.installdir, line)
                    sys.stdout.write(line)
            for script in [os.path.join('intel64', 'bin', 'mpivars.sh'), os.path.join('mic', 'bin', 'mpivars.sh')]:
                for line in fileinput.input(os.path.join(self.installdir, script), inplace=1, backup='.orig.easybuild'):
                    line = re.sub(r"^I_MPI_ROOT=.*", "I_MPI_ROOT=%s; export I_MPI_ROOT" % self.installdir, line)
                    sys.stdout.write(line)

    def sanity_check_step(self):
        """Custom sanity check paths for IMPI."""

        suff = "64"
        if self.cfg['m32']:
            suff = ""

        mpi_mods = ['mpi.mod']
        if LooseVersion(self.version) > LooseVersion('4.0'):
            mpi_mods.extend(["mpi_base.mod", "mpi_constants.mod", "mpi_sizeofs.mod"])

        custom_paths = {
            'files': ["bin%s/mpi%s" % (suff, x) for x in ["icc", "icpc", "ifort"]] +
                     ["include%s/mpi%s.h" % (suff, x) for x in ["cxx", "f", "", "o", "of"]] +
                     ["include%s/%s" % (suff, x) for x in ["i_malloc.h"] + mpi_mods] +
                     ["lib%s/libmpi.%s" % (suff, get_shared_lib_ext()), "lib%s/libmpi.a" % suff],
            'dirs': [],
        }

        super(EB_impi, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        if self.cfg['m32']:
            lib_dirs = ['lib', 'lib/ia32', 'ia32/lib']
            include_dirs = ['include']
            return {
                'PATH': ['bin', 'bin/ia32', 'ia32/bin'],
                'LD_LIBRARY_PATH': lib_dirs,
                'LIBRARY_PATH': lib_dirs,
                'CPATH': include_dirs,
                'MIC_LD_LIBRARY_PATH' : ['mic/lib'],
            }
        else:
            lib_dirs = ['lib/em64t', 'lib64']
            include_dirs = ['include64']
            return {
                'PATH': ['bin/intel64', 'bin64'],
                'LD_LIBRARY_PATH': lib_dirs,
                'LIBRARY_PATH': lib_dirs,
                'CPATH': include_dirs,
                'MIC_LD_LIBRARY_PATH' : ['mic/lib'],
            }

    def make_module_extra(self):
        """Overwritten from Application to add extra txt"""
        txt = super(EB_impi, self).make_module_extra()
        txt += self.module_generator.set_environment('I_MPI_ROOT', self.installdir)
        if self.cfg['set_mpi_wrappers_compiler'] or self.cfg['set_mpi_wrappers_all']:
            for var in ['CC', 'CXX', 'F77', 'F90', 'FC']:
                if var == 'FC':
                    # $FC isn't defined by EasyBuild framework, so use $F90 instead
                    src_var = 'F90'
                else:
                    src_var = var

                target_var = 'I_MPI_%s' % var

                val = os.getenv(src_var)
                if val:
                    txt += self.module_generator.set_environment(target_var, val)
                else:
                    raise EasyBuildError("Environment variable $%s not set, can't define $%s", src_var, target_var)

        if self.cfg['set_mpi_wrapper_aliases_gcc'] or self.cfg['set_mpi_wrappers_all']:
            # force mpigcc/mpigxx to use GCC compilers, as would be expected based on their name
            txt += self.module_generator.set_alias('mpigcc', 'mpigcc -cc=gcc')
            txt += self.module_generator.set_alias('mpigxx', 'mpigxx -cc=g++')

        if self.cfg['set_mpi_wrapper_aliases_intel'] or self.cfg['set_mpi_wrappers_all']:
            # do the same for mpiicc/mpiipc/mpiifort to be consistent, even if they may not exist
            txt += self.module_generator.set_alias('mpiicc', 'mpiicc -cc=icc')
            txt += self.module_generator.set_alias('mpiicpc', 'mpiicpc -cc=icpc')
            txt += self.module_generator.set_alias('mpiifort', 'mpiifort -cc=ifort')

        return txt
