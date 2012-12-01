##
# Copyright 2009-2012 Ghent University
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
EasyBuild support for Quantum ESPRESSO, implemented as an easyblock
"""
import fileinput
import os
import re
import shutil
import sys

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd_qa
from easybuild.tools.modules import get_software_root


class EB_QuantumESPRESSO(ConfigureMake):
    """Support for building and installing Quantum ESPRESSO."""

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for Quantum ESPRESSO."""
        extra_vars = [
                      ('hybrid', [False, "Enable hybrid build (with OpenMP)", CUSTOM]),
                      ('with_scalapack', [True, "Enable ScaLAPACK support", CUSTOM]),
                     ]
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration procedure for Quantum ESPRESSO."""

        # copy stuff in 'install' directory to 'install' directory for Quantum ESPRESSO
        # this comes from the IntelMKL*tar.gz tarball, that is custom for HPC-UGent
        # TODO: create patch files instead, and get rid of this crap below?
        #if self.toolchain().name == 'ictce':
        #oldextralibpath = os.path.join(self.builddir, 'install')
        #newextralibpath = os.path.join(self.cfg['start_dir'], 'install')
        #extralibs = os.listdir(oldextralibpath)
        #try:
            #for lib in extralibs:
                #shutil.copy2(os.path.join(oldextralibpath, lib), newextralibpath)
        #except Exception, err:
            #self.log.error("Failed to copy %s to %s, %s" % (lib, newextralibpath, err))

        if self.cfg['hybrid']:
            self.cfg.update('configopts', '--enable-openmp')

        if not self.toolchain.options['usempi']:
            self.cfg.update('configopts', '--disable-parallel')

        if not self.cfg['with_scalapack']:
            self.cfg.update('configopts', '--without-scalapack')

        super(EB_QuantumESPRESSO, self).configure_step()

        repls = []

        # compose list of DFLAGS (flag, value, keep_stuff)
        # for guidelines, see include/defs.h.README in sources
        dflags = []

        comp_fam_dflags = {
                           toolchain.INTELCOMP: '-D__INTEL',
                           toolchain.GCC: '-D__GFORTRAN -D__STD_F95',
                          }
        dflags.append(comp_fam_dflags[self.toolchain.comp_family()])

        if "fftw3" in os.getenv('LIBFFT'):
            dflags.append('-D__FFTW3')
        elif os.getenv('LIBFFT'):
            dflags.append('-D__FFTW')

        if get_software_root('ACML'):
            dflags.append('-D__ACML')

        if self.toolchain.options['usempi']:
            dflags.append('-D__MPI -D__PARA')

        if self.cfg['hybrid']:
            dflags.append(" -D__OPENMP")

        if self.cfg['with_scalapack']:
            dflags.append(" -D__SCALAPACK")

        repls.append(('DFLAGS', ' '.join(dflags), False))

        # complete C/Fortran compiler and LD flags
        if self.cfg['hybrid']:
            repls.append(('LDFLAGS', self.toolchain.get_flag('openmp'), True))
            repls.append(('(?:C|F90|F)FLAGS', self.toolchain.get_flag('openmp'), True))

        # obtain library settings
        repls.append(('BLAS_LIBS', os.getenv('LIBBLAS'), False))
        repls.append(('FFT_LIBS', os.getenv('LIBFFT'), False))
        repls.append(('LAPACK_LIBS', os.getenv('LIBLAPACK'), False))
        repls.append(('SCALAPACK_LIBS', os.getenv('LIBSCALAPACK'), False))
        repls.append(('LD_LIBS', os.getenv('LIBS'), False))

        self.log.debug("List of replacements to perform: %s" % repls)

        # patch make.sys file
        fn = os.path.join(self.cfg['start_dir'], 'make.sys')
        try:
            for line in fileinput.input(fn, inplace=1, backup='.orig.eb'):
                for (k, v, keep) in repls:
                    if keep:
                        line = re.sub(r"^(%s\s*=[ \t]*)(.*)$" % k, r"\1\2 %s" % v, line)
                    else:
                        line = re.sub(r"^(%s\s*=[ \t]*).*$" % k, r"\1%s" % v, line)

                    # fix preprocessing directives for .f90 files in make.sys if required
                if self.toolchain.comp_family() in [toolchain.GCC]:
                    line = re.sub("\$\(MPIF90\) \$\(F90FLAGS\) -c \$<",
                                  "$(CPP) -C $(CPPFLAGS) $< -o $*.F90\n" +
                                  "\t$(MPIF90) $(F90FLAGS) -c $*.F90 -o $*.o",
                                  line)

                sys.stdout.write(line)
        except OSError, err:
            self.log.error("Failed to patch %s: %s" % (fn, err))

        # move non-espresso directories to where they're expected
        try:
            dirnames = [d for d in os.listdir(self.builddir) if not d.startswith('espresso')]
            targetdir = os.path.join(self.builddir, "espresso-%s" % self.version)
            for dirname in dirnames:
                shutil.move(os.path.join(self.builddir, dirname), os.path.join(targetdir, dirname))
                self.log.info("Moved %s into %s" % (dirname, targetdir))

        except OSError, err:
            self.log.error("Failed to move non-espresso directories: %s" % err)

        self.cfg.update('makeopts', 'all gipaw vdw w90 want gww xspectra yambo')

    def install_step(self):
        """Custom install procedure for Quantum ESPRESSO: just copy the binaries."""
        # TODO: apperently the binaries are symlinked in the 'bin' directory to the build dir
        # do we need to make extra measures to make sure the actual binaries are copied, not the symlinks?
        try:
            shutil.copytree(os.path.join(self.cfg['start_dir'], 'bin'),
                            os.path.join(self.installdir, 'bin'))

        except OSError, err:
            self.log.error("Failed to copy binaries to install dir: %s" % err)

    def sanity_check_step(self):
        """Custom sanity check for Quantum ESPRESSO."""

        custom_paths = {
                        'files': ["bin/%s.x" % x for x in ["average", "band_plot", "bands_FS",
                                                           "bands", "cppp", "cp", "d3", "dist",
                                                           "dos", "dynmat", "epsilon", "ev",
                                                           "gipaw", "gww_fit", "gww", "head",
                                                           "initial_state", "iotk_print_kinds",
                                                           "iotk", "kpoints", "kvecs_FS", "lambda",
                                                           "ld1", "matdyn", "path_int", "phcg",
                                                           "ph", "plan_avg", "plotband", "plotproj",
                                                           "plotrho", "pmw", "pp", "projwfc",
                                                           "pw2casino", "pw2gw", "pw2wannier90",
                                                           "pw4gww", "pwcond", "pw_export",
                                                           "pwi2xsf", "pw", "q2r", "sumpdos", "vdw",
                                                           "wannier90", "wannier_ham",
                                                           "wannier_plot", "wfdd", "xspectra"]] +
                                 ["bin/iotk"],
                        'dirs': []
                       }

        ConfigureMake.sanity_check_step(self, custom_paths=custom_paths)
