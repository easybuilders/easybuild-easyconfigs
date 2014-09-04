##
# Copyright 2009-2014 Ghent University
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
EasyBuild support for building and installing GAMESS-US, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
"""
import fileinput
import os
import re
import shutil
import sys

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.filetools import mkdir
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_avail_core_count, get_platform_name
from easybuild.tools import toolchain


class EB_GAMESS_minus_US(EasyBlock):
    """Support for building/installing GAMESS-US."""

    @staticmethod
    def extra_options():
        """Define custom easyconfig parameters for GAMESS-US."""
        extra_vars = {
            'ddi_comm': ['mpi', "DDI communication layer to use", CUSTOM],
            'maxcpus': [None, "Maximum number of cores per node", MANDATORY],
            'maxnodes': [None, "Maximum number of nodes", MANDATORY],
        }
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Custom configure procedure for GAMESS-US."""

        # copy, edit and build the source code activator
        actvtecode = os.path.join(self.cfg['start_dir'], 'tools', 'actvte.code')
        actvtef = os.path.join(self.cfg['start_dir'], 'tools', 'actvte.f')
        try:
            shutil.copy2(actvtecode, actvtef)
            for line in fileinput.input(actvtef, inplace=1, backup='.orig'):
                # uncomment lines by replacing '*UNX' with 4 spaces
                line = re.sub(r"^\*UNX", ' '*4, line)
                sys.stdout.write(line)
        except (IOError, OSError), err:
            self.log.error("Failed to create %s: %s" % (actvtef, err))

        try:
            cmd = "%s -o tools/actvte.x tools/actvte.f" % os.environ['F77']
            run_cmd(cmd, log_all=True, simple=True)
        except Exception, err:
            self.log.error("Something went wrong during compilation of %s" % actvtef)

        # creating the install.info file
        platform_name = get_platform_name()
        x86_64_linux_re = re.compile('^x86_64-.*-linux$')
        if x86_64_linux_re.match(platform_name) or platform_name == 'x86_64-apple-darwin':  # FIXME
            machinetype = "linux64"
        else:
            self.log.error("Build target %s currently unsupported" % platform_name)

        # compiler config
        comp_fam = self.toolchain.comp_family()
        fortran_comp, fortran_ver = None, None
        if comp_fam == toolchain.INTELCOMP:
            fortran_comp = 'ifort'
            fortran_ver = get_software_version('ifort')
        elif comp_fam == toolchain.GCC:
            fortran_comp = 'gfortran'
            fortran_ver = '.'.join(get_software_version('GCC').split('.')[:2])
        else:
            self.log.error("Compiler family %s currently unsupported." % comp_fam)

        # math library config
        known_mathlibs = ['imkl', 'OpenBLAS', 'ATLAS', 'ACML']
        mathlib, mathlib_ver, mathlib_path = None, None, None
        for mathlib in known_mathlibs:
            mathlib_ver = get_software_version(mathlib)
            if mathlib_ver is not None:
                mathlib_path = os.environ['LAPACK_LIB_DIR'].split(os.pathsep)[0]
                break
        if mathlib_ver is None:
            self.log.error("None of the know math libraries (%s) available, giving up." % known_mathlibs)
        if mathlib == 'imkl':
            mathlib = 'mkl'
        elif mathlib == 'OpenBLAS':
            mathlib = 'blas'  # FIXME, only for old GAMESS-US versions?

        # MPI library config
        known_mpilibs = ['impi', 'OpenMPI', 'MVAPICH2', 'MPICH2']
        mpilib, mpilib_path = None, None
        for mpilib in known_mpilibs:
            mpilib_path = get_software_root(mpilib)
            if mpilib_path is not None:
                break
        if mpilib_path is None:
            self.log.error("None of the known MPI libraries (%s) available, giving up." % known_mpilibs)

        # verify selected DDI communication layer
        known_ddi_comms = ['mpi', 'mixed', 'shmem', 'sockets']
        if not self.cfg['ddi_comm'] in known_ddi_comms:
            tup = (known_ddi_comms, self.cfg['ddi_comm'])
            self.log.error("Unsupported DDI communication layer specified (known: %s): %s" % tup)

        install_info = {
            'GMS_BUILD_DIR': self.cfg['start_dir'],
            'GMS_PATH': self.cfg['start_dir'],
            'GMS_TARGET': machinetype,
            'GMS_FORTRAN': os.environ['F77'],
            #'GMS_%s_VERNO' % fortran_comp.upper(): fortran_ver,
            'GMS_%s_VERNO' % fortran_comp.upper(): "14",
            'GMS_MATHLIB': mathlib.lower(),
            'GMS_MATHLIB_PATH': mathlib_path,
            'GMS_DDI_COMM': self.cfg['ddi_comm'],
            'GMS_MPI_LIB': mpilib.lower(),
            'GMS_MPI_PATH': mpilib_path,
        }
        if mathlib == 'mkl':
            #install_info.update({'GMS_MKL_VERNO': mathlib_ver})
            install_info.update({'GMS_MKL_VERNO': "11"})

        install_info_lines = [
            "#!/bin/csh",
            "# Build configuration from GAMESS-US",
            "# generated by EasyBuild",
        ]
        for key, val in sorted(install_info.items()):
            setenv = "setenv %s\t\t%s" % (key, val)
            install_info_lines.append("setenv %s\t\t%s" % (key, val))
        install_info_txt = '\n'.join(install_info_lines) + '\n'  # each line *must* end with newline in a csh script

        install_info_fp = "install.info"
        tup = (install_info_fp, install_info_txt)
        self.log.info("The %s script used for this build has the following content:\n%s" % tup)
        try:
            f = open(install_info_fp, 'w')
            f.write(install_info_txt)
            f.close()
        except IOError, err:
            self.log.error("Failed to create %s: %s" % (install_info_fp, err))

        # adapt and execute the compddi file
        compddi = os.path.join(self.cfg['start_dir'], 'ddi', 'compddi')
        try:
            maxcpus_re = re.compile(r"^set MAXCPUS.*", re.M)
            set_maxcpus = "set MAXCPUS = %s" % self.cfg['maxcpus']
            maxnodes_re = re.compile(r"^set MAXNODES.*", re.M)
            set_maxnodes = "set MAXNODES = %s" % self.cfg['maxnodes']
            cc_re = re.compile(r"set CC = \S*")
            set_cc = "set CC = '%s'" % os.environ['MPICC']
            f77_re = re.compile(r"case %s\s*:" % os.environ['F77_SEQ'])
            case_f77 = "case %s:" % os.environ['F77']
            for line in fileinput.input(compddi, inplace=1, backup='.orig'):
                # set MAXCPUS/MAXNODES as configured
                line = maxcpus_re.sub(set_maxcpus, line)
                line = maxnodes_re.sub(set_maxnodes, line)
                # adjust hardcoded settings for C compiler
                line = cc_re.sub(set_cc, line)
                # make sure switch statements also work when $F77 is an MPI compiler wrapper
                if os.environ['F77'].startswith('mpi'):
                    line = f77_re.sub(case_f77, line)
                sys.stdout.write(line)
        except IOError, err:
            self.log.error("Failed to patch %s: %s" % (compddi, err))

        run_cmd(compddi, log_all=True, simple=True)

        # make sure the libddi.a library is present
        libddi = os.path.join(self.cfg['start_dir'], 'ddi', 'libddi.a')
        if not os.path.isfile(libddi):
            self.log.error("The libddi.a library (%s) was never built" % libddi)
        else:
            self.log.info("The libddi.a library (%s) was successfully built." % libddi)

    def build_step(self):
        """Custom build procedure for GAMESS-US."""
        # patch comp/lked scripts if required (if $F77 is an MPI command wrapper)
        comp = os.path.join(self.cfg['start_dir'], 'comp')
        lked = os.path.join(self.cfg['start_dir'], 'lked')
        if os.environ['F77'].startswith('mpi'):
            f77_re = re.compile(r"case %s\s*:" % os.environ['F77_SEQ'])
            case_f77 = "case %s:" % os.environ['F77']
            for line in fileinput.input(comp, inplace=1, backup='.orig'):
                line = f77_re.sub(case_f77, line)
                sys.stdout.write(line)
            for line in fileinput.input(lked, inplace=1, backup='.orig'):
                line = f77_re.sub(case_f77, line)
                sys.stdout.write(line)

        compall = os.path.join(self.cfg['start_dir'], 'compall')
        run_cmd(compall, log_all=True, simple=True)

        cmd = "%s gamess mpi" % lked
        run_cmd(cmd, log_all=True, simple=True)

        # sanity check for gamess executable
        executable = os.path.join(self.builddir, 'gamess', 'gamess.%s.x' % self.cfg['ddi_comm'])
        if not os.path.isfile(executable):
            self.log.error("the executable (%s) was never built" % executable)

    def install_step(self):
        """Custom install procedure for GAMESS-US (copy files/directories to install dir)."""
        try:
            for item in os.listdir(os.path.join(self.cfg['start_dir'])):
                srcpath = os.path.join(self.cfg['start_dir'], item)
                if os.path.isdir(item):
                    shutil.copytree(srcpath, os.path.join(self.installdir, item))
                else:
                    shutil.copy2(srcpath, os.path.join(self.installdir))
            #shutil.copytree(os.path.join(self.cfg['start_dir']), self.installdir)
            #for subdir in ['auxdata', 'graphics', 'mcpdata', 'misc', 'qmnuc', 'tests', 'tools']:
                #srcpath = os.path.join(self.cfg['start_dir'], subdir)
                #if os.path.exists(srcpath):
                #    shutil.copytree(srcpath, os.path.join(self.installdir, subdir))
                #bindir = os.path.join(self.installdir, 'bin')
                #mkdir(bindir)
                #shutil.copy2(os.path.join(self.cfg['start_dir'], 'gamess.%s.x' % self.cfg['ddi_comm']), bindir)
                #shutil.copy2(os.path.join(self.cfg['start_dir'], 'gamess.%s.x' % self.cfg['ddi_comm']), self.installdir)
                #for file in ['runall', 'rungms', 'gms-files.csh']:
                #    shutil.copy2(os.path.join(self.cfg['start_dir'], file), self.installdir)


        except OSError, err:
            self.log.error("Failed to install GAMESS-US by copying files/directories: %s" % err)

    def make_module_extra(self):
        """Define GAMESS-US specific variables in generated module file, i.e. $GAMESSUSROOT."""
        txt = super(EB_GAMESS_minus_US, self).make_module_extra()
        txt += self.moduleGenerator.set_environment('GAMESSUSROOT', '$root')
        #txt += self.moduleGenerator.set_environment('PATH', '$root')
        # add install directory to PATH
        txt += self.moduleGenerator.prepend_paths("PATH", [''])
        return txt
