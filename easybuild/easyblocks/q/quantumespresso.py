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
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
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

    def patch_step(self):
        """Patch files from build dir (not start dir)."""
        super(EB_QuantumESPRESSO, self).patch_step(beginpath=self.builddir)

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
        libs = []
        for lib in ['BLAS', 'LAPACK', 'FFT', 'SCALAPACK']:
            val = os.getenv('LIB%s' % lib)
            repls.append(('%s_LIBS' % lib, val, False))
            libs.append(val)
        libs = ' '.join(libs)

        repls.append(('BLAS_LIBS_SWITCH', 'external', False))
        repls.append(('LAPACK_LIBS_SWITCH', 'external', False))
        repls.append(('LD_LIBS', os.getenv('LIBS'), False))

        self.log.debug("List of replacements to perform: %s" % repls)

        # patch make.sys file
        fn = os.path.join(self.cfg['start_dir'], 'make.sys')
        try:
            for line in fileinput.input(fn, inplace=1, backup='.orig.eb'):
                for (k, v, keep) in repls:
                    # need to use [ \t]* instead of \s*, because vars may be undefined as empty,
                    # and we don't want to include newlines
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

        self.log.debug("Contents of patched %s: %s" % (fn, open(fn, "r").read()))

        # patch default make.sys for wannier
        if LooseVersion(self.version) >= LooseVersion("5"):
            fn = os.path.join(self.cfg['start_dir'], 'install', 'make_wannier90.sys')
        else:
            fn = os.path.join(self.cfg['start_dir'], 'plugins', 'install', 'make_wannier90.sys')
        try:
            for line in fileinput.input(fn, inplace=1, backup='.orig.eb'):
                line = re.sub(r"^(LIBS\s*=\s*).*", r"\1%s" % libs, line)

                sys.stdout.write(line)

        except OSError, err:
            self.log.error("Failed to patch %s: %s" % (fn, err))

        self.log.debug("Contents of patched %s: %s" % (fn, open(fn, "r").read()))

        # patch Makefile of want plugin
        wantprefix = 'want-'
        wantdirs = [d for d in os.listdir(self.builddir) if d.startswith(wantprefix)]

        if len(wantdirs) > 1:
            self.log.error("Found more than one directory with %s prefix, help!" % wantprefix)

        if len(wantdirs) != 0:
            fn = os.path.join(self.builddir, wantdirs[0], 'conf', 'make.sys.in')
            try:
                for line in fileinput.input(fn, inplace=1, backup='.orig.eb'):
                    # fix preprocessing directives for .f90 files in make.sys if required
                    if self.toolchain.comp_family() in [toolchain.GCC]:
                        line = re.sub("@f90rule@",
                                      "$(CPP) -C $(CPPFLAGS) $< -o $*.F90\n" +
                                      "\t$(MPIF90) $(F90FLAGS) -c $*.F90 -o $*.o",
                                      line)

                    sys.stdout.write(line)
            except OSError, err:
                self.log.error("Failed to patch %s: %s" % (fn, err))

        # move non-espresso directories to where they're expected and create symlinks
        try:
            dirnames = [d for d in os.listdir(self.builddir) if not d.startswith('espresso')]
            targetdir = os.path.join(self.builddir, "espresso-%s" % self.version)
            for dirname in dirnames:
                shutil.move(os.path.join(self.builddir, dirname), os.path.join(targetdir, dirname))
                self.log.info("Moved %s into %s" % (dirname, targetdir))
                dirname_head = dirname.split('-')[0]
                if dirname_head == 'sax':
                    linkname = 'SaX'
                if dirname_head == 'wannier90':
                    linkname = 'W90'
                elif dirname_head in ['gipaw', 'plumed', 'want', 'yambo']:
                    linkname = dirname_head.upper()
                    os.symlink(os.path.join(targetdir, dirname), os.path.join(targetdir, linkname))

        except OSError, err:
            self.log.error("Failed to move non-espresso directories: %s" % err)

        # make sure we build most stuff
        if not 'all' in self.cfg['makeopts']:
            self.cfg.update('makeopts', 'all')

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

        bins = ["average.x", "band_plot.x", "bands_FS.x", "bands.x", "cppp.x", "cp.x", "d3.x",
                "dist.x", "dos.x", "dynmat.x", "epsilon.x", "ev.x", "gww_fit.x", "gww.x", "head.x",
                "initial_state.x", "iotk_print_kinds.x", "iotk", "iotk.x", "kpoints.x", "kvecs_FS.x",
                "lambda.x", "ld1.x", "matdyn.x", "path_int.x", "phcg.x", "ph.x", "plan_avg.x",
                "plotband.x", "plotproj.x", "plotrho.x", "pmw.x", "pp.x", "projwfc.x", "pw2casino.x",
                "pw2gw.x", "pw2wannier90.x", "pw4gww.x", "pwcond.x", "pw_export.x", "pwi2xsf.x",
                "pw.x", "q2r.x", "sumpdos.x", "vdw.x", "wannier_ham.x", "wannier_plot.x", "wfdd.x"]

        if 'gipaw' in self.cfg['makeopts'] or 'all' in self.cfg['makeopts']:
            bins.extend(["gipaw.x"])

        if 'w90' in self.cfg['makeopts']:
            bins.extend(["wannier90.x"])

        if 'xspectra' in self.cfg['makeopts']:
            bins.extend(["xspectra.x"])

        if 'yambo' in self.cfg['makeopts']:
            bins.extend(["yambo"])

        custom_paths = {
                        'files': ["bin/%s" % x for x in bins],
                        'dirs': []
                       }

        ConfigureMake.sanity_check_step(self, custom_paths=custom_paths)
