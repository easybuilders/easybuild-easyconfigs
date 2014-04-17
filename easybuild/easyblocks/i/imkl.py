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
EasyBuild support for installing the Intel Math Kernel Library (MKL), implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Ward Poelmans (Ghent University)
"""

import os
import shutil
import tempfile
from distutils.version import LooseVersion

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import rmtree2, run_cmd
from easybuild.tools.modules import get_software_root


class EB_imkl(IntelBase):
    """
    Class that can be used to install mkl
    - tested with 10.2.1.017
    -- will fail for all older versions (due to newer silent installer)
    """

    @staticmethod
    def extra_options():
        """Add easyconfig parameters custom to imkl (e.g. interfaces)."""
        extra_vars = {
            'interfaces': [True, "Indicates whether interfaces should be built", CUSTOM],
        }
        return IntelBase.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        super(EB_imkl, self).__init__(*args, **kwargs)
        # make sure $MKLROOT isn't set, it's known to cause problems with the installation
        self.cfg.update('unwanted_env_vars', ['MKLROOT'])

    def install_step(self):
        """
        Actual installation
        - create silent cfg file
        - execute command
        """
        silent_cfg_names_map = None
        silent_cfg_extras = None

        if LooseVersion(self.version) < LooseVersion('11.1'):
            # since imkl v11.1, silent.cfg has been slightly changed to be 'more standard'

            silent_cfg_names_map = {
                'activation_name': ACTIVATION_NAME_2012,
                'license_file_name': LICENSE_FILE_NAME_2012,
            }

        if LooseVersion(self.version) >= LooseVersion('11.1'):
            silent_cfg_extras = {
                'COMPONENTS': 'ALL',
            }

        super(EB_imkl, self).install_step(silent_cfg_names_map=silent_cfg_names_map, silent_cfg_extras=silent_cfg_extras)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        if LooseVersion(self.version) >= LooseVersion('10.3'):
            if self.cfg['m32']:
                self.log.error("32-bit not supported yet for IMKL v%s (>= 10.3)" % self.version)
            return {
                'PATH': ['bin', 'mkl/bin', 'mkl/bin/intel64', 'composerxe-2011/bin'],
                'LD_LIBRARY_PATH': ['lib/intel64', 'mkl/lib/intel64'],
                'LIBRARY_PATH': ['lib/intel64', 'mkl/lib/intel64'],
                'MANPATH': ['man', 'man/en_US'],
                'CPATH': ['mkl/include', 'mkl/include/fftw'],
                'FPATH': ['mkl/include', 'mkl/include/fftw'],
            }
        else:
            if self.cfg['m32']:
                return {
                    'PATH': ['bin', 'bin/ia32', 'tbb/bin/ia32'],
                    'LD_LIBRARY_PATH': ['lib', 'lib/32'],
                    'LIBRARY_PATH': ['lib', 'lib/32'],
                    'MANPATH': ['man', 'share/man', 'man/en_US'],
                    'CPATH': ['include'],
                    'FPATH': ['include']
                }

            else:
                return {
                    'PATH': ['bin', 'bin/intel64', 'tbb/bin/em64t'],
                    'LD_LIBRARY_PATH': ['lib', 'lib/em64t'],
                    'LIBRARY_PATH': ['lib', 'lib/em64t'],
                    'MANPATH': ['man', 'share/man', 'man/en_US'],
                    'CPATH': ['include'],
                    'FPATH': ['include'],
                }

    def make_module_extra(self):
        """Overwritten from Application to add extra txt"""
        txt = super(EB_imkl, self).make_module_extra()
        txt += "prepend-path\t%s\t\t%s\n" % (self.license_env_var, self.license_file)
        if self.cfg['m32']:
            txt += "prepend-path\t%s\t\t$root/%s\n" % ('NLSPATH', 'idb/32/locale/%l_%t/%N')
        else:
            txt += "prepend-path\t%s\t\t$root/%s\n" % ('NLSPATH', 'idb/intel64/locale/%l_%t/%N')
        txt += "setenv\t%s\t\t$root\n" % 'MKLROOT'

        return txt

    def post_install_step(self):
        """
        The mkl directory structure has thoroughly changed as from version 10.3.
        Hence post processing is quite different in both situations
        """
        # reload the dependencies
        self.load_dependency_modules()

        if LooseVersion(self.version) >= LooseVersion('10.3'):
            # Add convenient wrapper libs
            # - form imkl 10.3

            if self.cfg['m32']:
                self.log.error("32-bit not supported yet for IMKL v%s (>=10.3)" % self.version)

            extra = {
                'libmkl.so': 'GROUP (-lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core)',
                'libmkl_em64t.a': 'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                'libmkl_solver.a': 'GROUP (libmkl_solver_lp64.a)',
                'libmkl_scalapack.a': 'GROUP (libmkl_scalapack_lp64.a)',
                'libmkl_lapack.a': 'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                'libmkl_cdft.a': 'GROUP (libmkl_cdft_core.a)'
            }
            for fil, txt in extra.items():
                dest = os.path.join(self.installdir, 'mkl/lib/intel64', fil)
                if not os.path.exists(dest):
                    try:
                        f = open(dest, 'w')
                        f.write(txt)
                        f.close()
                        self.log.info("File %s written" % dest)
                    except:
                        self.log.exception("Can't write file %s" % (dest))

            # build the mkl interfaces (pic and no-pic)

            if not self.cfg['interfaces']:
                return

            # build the interfaces
            # - blas95 and lapack95 need more work, ignore for now

            # lis1=['blas95','fftw2xc','fftw2xf','lapack95']
            # blas95 and lapack also need include/.mod to be processed
            lis1 = ['fftw2xc', 'fftw2xf']
            lis2 = ['fftw3xc', 'fftw3xf']
            lis3 = []
            if LooseVersion(self.version) < LooseVersion('11.1'):
                lis3 = ['fftw2x_cdft', 'fftw3x_cdft']

            interfacedir = os.path.join(self.installdir, 'mkl/interfaces')
            try:
                os.chdir(interfacedir)
                self.log.info("Changed to interfaces directory %s" % interfacedir)
            except:
                self.log.exception("Can't change to interfaces directory %s" % interfacedir)

            # compiler defaults to icc, but we could be using gcc to create gimkl.
            makeopts = ''
            if get_software_root('GCC'):  # can't use toolchain.comp_family, because of dummy toolchain
                makeopts = 'compiler=gnu '

            for i in lis1 + lis2 + lis3:
                if i in lis1:
                    # use INSTALL_DIR and CFLAGS and COPTS
                    cmd = "make -f makefile libintel64"
                if i in lis2:
                    # use install_to and CFLAGS
                    cmd = "make -f makefile libintel64 install_to=$INSTALL_DIR"
                if i in lis3:
                    # use INSTALL_DIR and SPEC_OPT
                    extramakeopts = ''
                    # can't use toolchain.mpi_family, because of dummy toolchain
                    if get_software_root('MPICH2') or get_software_root('MVAPICH2'):
                        extramakeopts = 'mpi=mpich2'
                    elif get_software_root('OpenMPI'):
                        extramakeopts = 'mpi=openmpi'
                    cmd = "make -f makefile libintel64 %s" % extramakeopts

                # add other make options as well
                cmd = ' '.join([cmd, makeopts])

                for opt in ['', '-fPIC']:
                    try:
                        tmpbuild = tempfile.mkdtemp()
                        self.log.debug("Created temporary directory %s" % tmpbuild)
                    except:
                        self.log.exception("Creating temporary directory failed")

                    # always set INSTALL_DIR, SPEC_OPT, COPTS and CFLAGS
                    env.setvar('INSTALL_DIR', tmpbuild)
                    env.setvar('SPEC_OPT', opt)
                    env.setvar('COPTS', opt)
                    env.setvar('CFLAGS', opt)

                    try:
                        intdir = os.path.join(interfacedir, i)
                        os.chdir(intdir)
                        self.log.info("Changed to interface %s directory %s" % (i, intdir))
                    except:
                        self.log.exception("Can't change to interface %s directory %s" % (i, intdir))

                    if not run_cmd(cmd, log_all=True, simple=True):
                        self.log.error("Building %s (opt: %s) failed" % (i, opt))

                    for fil in os.listdir(tmpbuild):
                        if opt == '-fPIC':
                            # add _pic to filename
                            ff = fil.split('.')
                            newfil = '.'.join(ff[:-1]) + '_pic.' + ff[-1]
                        else:
                            newfil = fil
                        dest = os.path.join(self.installdir, 'mkl/lib/intel64', newfil)
                        try:
                            src = os.path.join(tmpbuild, fil)
                            if os.path.isfile(src):
                                shutil.move(src, dest)
                                self.log.info("Moved %s to %s" % (src, dest))
                        except:
                            self.log.exception("Failed to move %s to %s" % (src, dest))

                    try:
                        rmtree2(tmpbuild)
                        self.log.debug('Removed temporary directory %s' % tmpbuild)
                    except:
                        self.log.exception("Removing temporary directory %s failed" % tmpbuild)
        else:
            # Follow this procedure for mkl version lower than 10.3
            # Extra
            # - build the mkl interfaces (pic and no-pic)
            # - add wrapper libs
            #            Add convenient libs
            # - form imkl 10.1
            if self.cfg['m32']:
                extra = {
                    'libmkl.so': 'GROUP (-lmkl_intel -lmkl_intel_thread -lmkl_core)',
                    'libmkl_em64t.a': 'GROUP (libmkl_intel.a libmkl_intel_thread.a libmkl_core.a)',
                    'libmkl_solver.a': 'GROUP (libmkl_solver.a)',
                    'libmkl_scalapack.a': 'GROUP (libmkl_scalapack_core.a)',
                    'libmkl_lapack.a': 'GROUP (libmkl_intel.a libmkl_intel_thread.a libmkl_core.a)',
                    'libmkl_cdft.a': 'GROUP (libmkl_cdft_core.a)'
                }
            else:
                extra = {
                    'libmkl.so': 'GROUP (-lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core)',
                    'libmkl_em64t.a': 'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                    'libmkl_solver.a': 'GROUP (libmkl_solver_lp64.a)',
                    'libmkl_scalapack.a': 'GROUP (libmkl_scalapack_lp64.a)',
                    'libmkl_lapack.a': 'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                    'libmkl_cdft.a': 'GROUP (libmkl_cdft_core.a)'
                }
            for fil, txt in extra.items():
                if self.cfg['m32']:
                    dest = os.path.join(self.installdir, 'lib/32', fil)
                else:
                    dest = os.path.join(self.installdir, 'lib/em64t', fil)
                if not os.path.exists(dest):
                    try:
                        f = open(dest, 'w')
                        f.write(txt)
                        f.close()
                        self.log.info("File %s written" % dest)
                    except:
                        self.log.exception("Can't write file %s" % (dest))

            if not self.cfg['interfaces']:
                return

            # build the interfaces
            # - blas95 and lapack95 need more work, ignore for now
            # lis1=['blas95','fftw2xc','fftw2x_cdft','fftw2xf','lapack95']
            # blas95 and lapack also need include/.mod to be processed
            lis1 = ['fftw2xc', 'fftw2x_cdft', 'fftw2xf']
            lis2 = ['fftw3xc', 'fftw3xf']

            interfacedir = os.path.join(self.installdir, 'interfaces')
            try:
                os.chdir(interfacedir)
            except:
                self.log.exception("Can't change to interfaces directory %s" % interfacedir)

            interfacestarget = "libem64t"
            if self.cfg['m32']:
                interfacestarget = "lib32"

            for i in lis1 + lis2:
                if i in lis1:
                    # use INSTALL_DIR and SPEC_OPT
                    cmd = "make -f makefile %s" % interfacestarget
                if i in lis2:
                    # use install_to and CFLAGS
                    cmd = "make -f makefile %s install_to=$INSTALL_DIR" % interfacestarget

                for opt in ['', '-fPIC']:
                    try:
                        tmpbuild = tempfile.mkdtemp()
                        self.log.debug("Created temporary directory %s" % tmpbuild)
                    except:
                        self.log.exception("Creating temporary directory failed")

                    # always set INSTALL_DIR, SPEC_OPT and CFLAGS
                    env.setvar('INSTALL_DIR', tmpbuild)
                    env.setvar('SPEC_OPT', opt)
                    env.setvar('CFLAGS', opt)

                    try:
                        intdir = os.path.join(interfacedir, i)
                        os.chdir(intdir)
                    except:
                        self.log.exception("Can't change to interface %s directory %s" % (i, intdir))

                    if not run_cmd(cmd, log_all=True, simple=True):
                        self.log.error("Building %s (opt: %s) failed" % (i, opt))

                    for fil in os.listdir(tmpbuild):
                        if opt == '-fPIC':
                            # add _pic to filename
                            ff = fil.split('.')
                            newfil = '.'.join(ff[:-1]) + '_pic.' + ff[-1]
                        else:
                            newfil = fil
                        if self.cfg['m32']:
                            dest = os.path.join(self.installdir, 'lib/32', newfil)
                        else:
                            dest = os.path.join(self.installdir, 'lib/em64t', newfil)
                        try:
                            src = os.path.join(tmpbuild, fil)
                            shutil.move(src, dest)
                            self.log.debug("Moved %s to %s" % (src, dest))
                        except:
                            self.log.exception("Failed to move %s to %s" % (src, dest))

                    try:
                        rmtree2(tmpbuild)
                        self.log.debug('Removed temporary directory %s' % tmpbuild)
                    except:
                        self.log.exception("Removing temporary directory %s failed" % (tmpbuild))

    def sanity_check_step(self):
        """Custom sanity check paths for Intel MKL."""
        mklfiles = None
        mkldirs = None
        ver = LooseVersion(self.version)
        libnames = ["libmkl_core.so", "libmkl_gnu_thread.so", "libmkl_intel_thread.so", "libmkl_sequential.so"]
        libnames_extra = ["libmkl_blacs_intelmpi_%(suff)s.so", "libmkl_scalapack_%(suff)s.so"]

        if ver >= LooseVersion('10.3'):
            if self.cfg['m32']:
                self.log.error("Sanity check for 32-bit not implemented yet for IMKL v%s (>= 10.3)" % self.version)
            else:
                mkldirs = ["bin", "mkl/bin", "mkl/bin/intel64", "mkl/lib/intel64", "mkl/include"]
                libnames += [lib % {'suff': suff} for lib in libnames_extra for suff in ['lp64', 'ilp64']]
                mklfiles = ["mkl/lib/intel64/libmkl.so", "mkl/include/mkl.h"] + \
                           ["mkl/lib/intel64/%s" % lib for lib in libnames]
                if ver >= LooseVersion('10.3.4') and ver < LooseVersion('11.1'):
                    mkldirs += ["compiler/lib/intel64"]
                else:
                    mkldirs += ["lib/intel64"]

        else:
            if self.cfg['m32']:
                mklfiles = ["lib/32/libmkl.so", "include/mkl.h"] + \
                           ["lib/32/%s" % lib for lib in libnames]
                mkldirs = ["lib/32", "include/32", "interfaces"]
            else:
                libnames += [lib % {'suff': suff} for lib in libnames_extra for suff in ['lp64', 'ilp64']]
                mklfiles = ["lib/em64t/libmkl.so", "include/mkl.h"] + \
                           ["lib/em64t/%s" % lib for lib in libnames]
                mkldirs = ["lib/em64t", "include/em64t", "interfaces"]

        custom_paths = {
            'files': mklfiles,
            'dirs': mkldirs,
        }

        super(EB_imkl, self).sanity_check_step(custom_paths=custom_paths)
