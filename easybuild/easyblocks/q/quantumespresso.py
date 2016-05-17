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
EasyBuild support for Quantum ESPRESSO, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import fileinput
import os
import re
import shutil
import sys
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_QuantumESPRESSO(ConfigureMake):
    """Support for building and installing Quantum ESPRESSO."""

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for Quantum ESPRESSO."""
        extra_vars = {
            'hybrid': [False, "Enable hybrid build (with OpenMP)", CUSTOM],
            'with_scalapack': [True, "Enable ScaLAPACK support", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to Quantum ESPRESSO."""
        super(EB_QuantumESPRESSO, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

        self.install_subdir = "espresso-%s" % self.version

    def patch_step(self):
        """Patch files from build dir (not start dir)."""
        super(EB_QuantumESPRESSO, self).patch_step(beginpath=self.builddir)

    def configure_step(self):
        """Custom configuration procedure for Quantum ESPRESSO."""

        if self.cfg['hybrid']:
            self.cfg.update('configopts', '--enable-openmp')

        if not self.toolchain.options.get('usempi', None):
            self.cfg.update('configopts', '--disable-parallel')

        if not self.cfg['with_scalapack']:
            self.cfg.update('configopts', '--without-scalapack')

        repls = []

        if self.toolchain.comp_family() in [toolchain.INTELCOMP]:
            # set preprocessor command (-E to stop after preprocessing, -C to preserve comments)
            cpp = "%s -E -C" % os.getenv('CC')
            repls.append(('CPP', cpp, False))
            env.setvar('CPP', cpp)

            # also define $FCCPP, but do *not* include -C (comments should not be preserved when preprocessing Fortran)
            env.setvar('FCCPP', "%s -E" % os.getenv('CC'))

        super(EB_QuantumESPRESSO, self).configure_step()

        # compose list of DFLAGS (flag, value, keep_stuff)
        # for guidelines, see include/defs.h.README in sources
        dflags = []

        comp_fam_dflags = {
            toolchain.INTELCOMP: '-D__INTEL',
            toolchain.GCC: '-D__GFORTRAN -D__STD_F95',
        }
        dflags.append(comp_fam_dflags[self.toolchain.comp_family()])

        libfft = os.getenv('LIBFFT')
        if libfft:
            if "fftw3" in libfft:
                dflags.append('-D__FFTW3')
            else:
                dflags.append('-D__FFTW')
            env.setvar('FFTW_LIBS', libfft)

        if get_software_root('ACML'):
            dflags.append('-D__ACML')

        if self.toolchain.options.get('usempi', None):
            dflags.append('-D__MPI -D__PARA')

        if self.cfg['hybrid']:
            dflags.append(" -D__OPENMP")

        if self.cfg['with_scalapack']:
            dflags.append(" -D__SCALAPACK")

        # always include -w to supress warnings
        dflags.append('-w')

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
                    line = re.sub(r"\$\(MPIF90\) \$\(F90FLAGS\) -c \$<",
                                  "$(CPP) -C $(CPPFLAGS) $< -o $*.F90\n" +
                                  "\t$(MPIF90) $(F90FLAGS) -c $*.F90 -o $*.o",
                                  line)

                sys.stdout.write(line)
        except IOError, err:
            raise EasyBuildError("Failed to patch %s: %s", fn, err)

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

        except IOError, err:
            raise EasyBuildError("Failed to patch %s: %s", fn, err)

        self.log.debug("Contents of patched %s: %s" % (fn, open(fn, "r").read()))

        # patch Makefile of want plugin
        wantprefix = 'want-'
        wantdirs = [d for d in os.listdir(self.builddir) if d.startswith(wantprefix)]

        if len(wantdirs) > 1:
            raise EasyBuildError("Found more than one directory with %s prefix, help!", wantprefix)

        if len(wantdirs) != 0:
            wantdir = os.path.join(self.builddir, wantdirs[0])
            make_sys_in_path = None
            cand_paths = [os.path.join('conf', 'make.sys.in'), os.path.join('config', 'make.sys.in')]
            for path in cand_paths:
                full_path = os.path.join(wantdir, path)
                if os.path.exists(full_path):
                    make_sys_in_path = full_path
                    break
            if make_sys_in_path is None:
                raise EasyBuildError("Failed to find make.sys.in in want directory %s, paths considered: %s",
                                     wantdir, ', '.join(cand_paths))

            try:
                for line in fileinput.input(make_sys_in_path, inplace=1, backup='.orig.eb'):
                    # fix preprocessing directives for .f90 files in make.sys if required
                    if self.toolchain.comp_family() in [toolchain.GCC]:
                        line = re.sub("@f90rule@",
                                      "$(CPP) -C $(CPPFLAGS) $< -o $*.F90\n" +
                                      "\t$(MPIF90) $(F90FLAGS) -c $*.F90 -o $*.o",
                                      line)

                    sys.stdout.write(line)
            except IOError, err:
                raise EasyBuildError("Failed to patch %s: %s", fn, err)

        # move non-espresso directories to where they're expected and create symlinks
        try:
            dirnames = [d for d in os.listdir(self.builddir) if not d.startswith('espresso')]
            targetdir = os.path.join(self.builddir, "espresso-%s" % self.version)
            for dirname in dirnames:
                shutil.move(os.path.join(self.builddir, dirname), os.path.join(targetdir, dirname))
                self.log.info("Moved %s into %s" % (dirname, targetdir))

                dirname_head = dirname.split('-')[0]
                linkname = None
                if dirname_head == 'sax':
                    linkname = 'SaX'
                if dirname_head == 'wannier90':
                    linkname = 'W90'
                elif dirname_head in ['gipaw', 'plumed', 'want', 'yambo']:
                    linkname = dirname_head.upper()
                if linkname:
                    os.symlink(os.path.join(targetdir, dirname), os.path.join(targetdir, linkname))

        except OSError, err:
            raise EasyBuildError("Failed to move non-espresso directories: %s", err)

    def install_step(self):
        """Skip install step, since we're building in the install directory."""
        pass

    def sanity_check_step(self):
        """Custom sanity check for Quantum ESPRESSO."""

        # build list of expected binaries based on make targets
        bins = ["iotk", "iotk.x", "iotk_print_kinds.x"]

        if 'cp' in self.cfg['buildopts'] or 'all' in self.cfg['buildopts']:
            bins.extend(["cp.x", "cppp.x", "wfdd.x"])

        if 'gww' in self.cfg['buildopts']:  # only for v4.x, not in v5.0 anymore
            bins.extend(["gww_fit.x", "gww.x", "head.x", "pw4gww.x"])

        if 'ld1' in self.cfg['buildopts'] or 'all' in self.cfg['buildopts']:
            bins.extend(["ld1.x"])

        if 'gipaw' in self.cfg['buildopts']:
            bins.extend(["gipaw.x"])

        if 'neb' in self.cfg['buildopts'] or 'pwall' in self.cfg['buildopts'] or \
           'all' in self.cfg['buildopts']:
            if LooseVersion(self.version) > LooseVersion("5"):
                bins.extend(["neb.x", "path_interpolation.x"])

        if 'ph' in self.cfg['buildopts'] or 'all' in self.cfg['buildopts']:
            bins.extend(["d3.x", "dynmat.x", "lambda.x", "matdyn.x", "ph.x", "phcg.x", "q2r.x"])
            if LooseVersion(self.version) > LooseVersion("5"):
                bins.extend(["fqha.x", "q2qstar.x"])

        if 'pp' in self.cfg['buildopts'] or 'pwall' in self.cfg['buildopts'] or \
           'all' in self.cfg['buildopts']:
            bins.extend(["average.x", "bands.x", "dos.x", "epsilon.x", "initial_state.x",
                         "plan_avg.x", "plotband.x", "plotproj.x", "plotrho.x", "pmw.x", "pp.x",
                         "projwfc.x", "sumpdos.x", "pw2wannier90.x", "pw_export.x", "pw2gw.x",
                         "wannier_ham.x", "wannier_plot.x"])
            if LooseVersion(self.version) > LooseVersion("5"):
                bins.extend(["pw2bgw.x", "bgw2pw.x"])
            else:
                bins.extend(["pw2casino.x"])

        if 'pw' in self.cfg['buildopts'] or 'all' in self.cfg['buildopts']:
            bins.extend(["dist.x", "ev.x", "kpoints.x", "pw.x", "pwi2xsf.x"])
            if LooseVersion(self.version) > LooseVersion("5"):
                bins.extend(["generate_vdW_kernel_table.x"])
            else:
                bins.extend(["path_int.x"])
            if LooseVersion(self.version) < LooseVersion("5.3.0"):
                bins.extend(["band_plot.x", "bands_FS.x", "kvecs_FS.x"])

        if 'pwcond' in self.cfg['buildopts'] or 'pwall' in self.cfg['buildopts'] or \
           'all' in self.cfg['buildopts']:
            bins.extend(["pwcond.x"])

        if 'tddfpt' in self.cfg['buildopts'] or 'all' in self.cfg['buildopts']:
            if LooseVersion(self.version) > LooseVersion("5"):
                bins.extend(["turbo_lanczos.x", "turbo_spectrum.x"])

        upftools = []
        if 'upf' in self.cfg['buildopts'] or 'all' in self.cfg['buildopts']:
            upftools = ["casino2upf.x", "cpmd2upf.x", "fhi2upf.x", "fpmd2upf.x", "ncpp2upf.x",
                        "oldcp2upf.x", "read_upf_tofile.x", "rrkj2upf.x", "uspp2upf.x", "vdb2upf.x",
                        "virtual.x"]
            if LooseVersion(self.version) > LooseVersion("5"):
                upftools.extend(["interpolate.x", "upf2casino.x"])

        if 'vdw' in self.cfg['buildopts']:  # only for v4.x, not in v5.0 anymore
            bins.extend(["vdw.x"])

        if 'w90' in self.cfg['buildopts']:
            bins.extend(["wannier90.x"])

        want_bins = []
        if 'want' in self.cfg['buildopts']:
            want_bins = ["bands.x", "blc2wan.x", "conductor.x", "current.x", "disentangle.x",
                         "dos.x", "gcube2plt.x", "kgrid.x", "midpoint.x", "plot.x", "sumpdos",
                         "wannier.x", "wfk2etsf.x"]
            if LooseVersion(self.version) > LooseVersion("5"):
                want_bins.extend(["cmplx_bands.x", "decay.x", "sax2qexml.x", "sum_sgm.x"])

        if 'xspectra' in self.cfg['buildopts']:
            bins.extend(["xspectra.x"])


        yambo_bins = []
        if 'yambo' in self.cfg['buildopts']:
            yambo_bins = ["a2y", "p2y", "yambo", "ypp"]

        pref = self.install_subdir

        custom_paths = {
                        'files': [os.path.join(pref, 'bin', x) for x in bins] +
                                 [os.path.join(pref, 'upftools', x) for x in upftools] +
                                 [os.path.join(pref, 'WANT', 'bin', x) for x in want_bins] +
                                 [os.path.join(pref, 'YAMBO', 'bin', x) for x in yambo_bins],
                        'dirs': [os.path.join(pref, 'include')]
                       }

        super(EB_QuantumESPRESSO, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom path suggestions for Quantum ESPRESSO."""
        guesses = super(EB_QuantumESPRESSO, self).make_module_req_guess()

        # order matters here, 'bin' should be *last* in this list to ensure it gets prepended to $PATH last,
        # so it gets preference over the others
        # this is important since some binaries are available in two places (e.g. dos.x in both bin and WANT/bin)
        bindirs = ['upftools', 'WANT/bin', 'YAMBO/bin', 'bin']
        guesses.update({
            'PATH': [os.path.join(self.install_subdir, bindir) for bindir in bindirs],
            'CPATH': [os.path.join(self.install_subdir, 'include')],
        })
        return guesses
