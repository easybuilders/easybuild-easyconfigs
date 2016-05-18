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
EasyBuild support for building and installing ALADIN, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import fileinput
import os
import re
import shutil
import sys
import tempfile

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root, get_software_libdir
from easybuild.tools.ordereddict import OrderedDict
from easybuild.tools.run import run_cmd, run_cmd_qa


class EB_ALADIN(EasyBlock):
    """Support for building/installing ALADIN."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for ALADIN."""
        super(EB_ALADIN, self).__init__(*args, **kwargs)

        self.conf_file = None
        self.conf_filepath = None
        self.rootpack_dir = 'UNKNOWN'

        self.orig_library_path = None

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for ALADIN."""

        extra_vars = {
            'optional_extra_param': ['default value', "short description", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration procedure for ALADIN."""

        # unset $LIBRARY_PATH set by modules of dependencies, because it may screw up linking
        if 'LIBRARY_PATH' in os.environ:
            self.log.debug("Unsetting $LIBRARY_PATH (was: %s)" % os.environ['LIBRARY_PATH'])
            self.orig_library_path = os.environ.pop('LIBRARY_PATH')
        
        # build auxiliary libraries
        auxlibs_dir = None

        my_gnu = None
        if self.toolchain.comp_family() == toolchain.GCC:
            my_gnu = 'y'  # gfortran
            for var in ['CFLAGS', 'CXXFLAGS', 'F90FLAGS', 'FFLAGS']:
                flags = os.getenv(var)
                env.setvar(var, "%s -fdefault-real-8 -fdefault-double-8" % flags)
                self.log.info("Updated %s to '%s'" % (var, os.getenv(var)))
        elif self.toolchain.comp_family() == toolchain.INTELCOMP:
            my_gnu = 'i'  # icc/ifort
        else:
            raise EasyBuildError("Don't know how to set 'my_gnu' variable in auxlibs build script.")
        self.log.info("my_gnu set to '%s'" % my_gnu)

        tmp_installroot = tempfile.mkdtemp(prefix='aladin_auxlibs_')

        try:
            cwd = os.getcwd()

            os.chdir(self.builddir)
            builddirs = os.listdir(self.builddir)

            auxlibs_dir = [x for x in builddirs if x.startswith('auxlibs_installer')][0]

            os.chdir(auxlibs_dir)

            auto_driver = 'driver_automatic'
            for line in fileinput.input(auto_driver, inplace=1, backup='.orig.eb'):

                line = re.sub(r"^(my_gnu\s*=\s*).*$", r"\1%s" % my_gnu, line)
                line = re.sub(r"^(my_r32\s*=\s*).*$", r"\1n", line)  # always 64-bit real precision
                line = re.sub(r"^(my_readonly\s*=\s*).*$", r"\1y", line)  # make libs read-only after build
                line = re.sub(r"^(my_installroot\s*=\s*).*$", r"\1%s" % tmp_installroot, line)

                sys.stdout.write(line)

            run_cmd("./%s" % auto_driver)

            os.chdir(cwd)

        except OSError, err:
            raise EasyBuildError("Failed to build ALADIN: %s", err)

        # build gmkpack, update PATH and set GMKROOT
        # we build gmkpack here because a config file is generated in the gmkpack isntall path
        try:
            gmkpack_dir = [x for x in builddirs if x.startswith('gmkpack')][0]
            os.chdir(os.path.join(self.builddir, gmkpack_dir))

            qa = {
                  'Do you want to run the configuration file maker assistant now (y) or later [n] ?': 'n',
                 }

            run_cmd_qa("./build_gmkpack", qa)
 
            os.chdir(cwd)

            paths = os.getenv('PATH').split(':')
            paths.append(os.path.join(self.builddir, gmkpack_dir, 'util'))
            env.setvar('PATH', ':'.join(paths))

            env.setvar('GMKROOT', os.path.join(self.builddir, gmkpack_dir))

        except OSError, err:
            raise EasyBuildError("Failed to build gmkpack: %s", err)

        # generate gmkpack configuration file
        self.conf_file = 'ALADIN_%s' % self.version
        self.conf_filepath = os.path.join(self.builddir, 'arch', '%s.x' % self.conf_file)

        try:
            if os.path.exists(self.conf_filepath):
                os.remove(self.conf_filepath)
                self.log.info("Removed existing gmpack config file %s" % self.conf_filepath)

            archdir = os.path.join(self.builddir, 'arch')
            if not os.path.exists(archdir):
                os.makedirs(archdir)

        except OSError, err:
            raise EasyBuildError("Failed to remove existing file %s: %s", self.conf_filepath, err)

        mpich = 'n'
        known_mpi_libs = [toolchain.MPICH, toolchain.MPICH2, toolchain.INTELMPI]
        if self.toolchain.options.get('usempi', None) and self.toolchain.mpi_family() in known_mpi_libs:
            mpich = 'y'

        qpref = 'Please type the ABSOLUTE name of '
        qsuff = ', or ignore (environment variables allowed) :'
        qsuff2 = ', or ignore : (environment variables allowed) :'

        comp_fam = self.toolchain.comp_family()
        if comp_fam == toolchain.GCC:
            gribdir = 'GNU'
        elif comp_fam == toolchain.INTELCOMP:
            gribdir = 'INTEL'
        else:
            raise EasyBuildError("Don't know which grib lib dir to use for compiler %s", comp_fam)

        aux_lib_gribex = os.path.join(tmp_installroot, gribdir, 'lib', 'libgribex.a')
        aux_lib_ibm = os.path.join(tmp_installroot, gribdir, 'lib', 'libibmdummy.a')
        grib_api_lib = os.path.join(get_software_root('grib_api'), 'lib', 'libgrib_api.a')
        grib_api_f90_lib = os.path.join(get_software_root('grib_api'), 'lib', 'libgrib_api_f90.a')
        grib_api_inc = os.path.join(get_software_root('grib_api'), 'include')
        jasperlib = os.path.join(get_software_root('JasPer'), 'lib', 'libjasper.a')
        mpilib = os.path.join(os.getenv('MPI_LIB_DIR'), os.getenv('MPI_LIB_SHARED'))

        # netCDF
        netcdf = get_software_root('netCDF')
        netcdf_fortran = get_software_root('netCDF-Fortran')
        if netcdf:
            netcdfinc = os.path.join(netcdf, 'include')
            if netcdf_fortran:
                netcdflib = os.path.join(netcdf_fortran, get_software_libdir('netCDF-Fortran'), 'libnetcdff.a')
            else:
                netcdflib = os.path.join(netcdf, get_software_libdir('netCDF'), 'libnetcdff.a')
            if not os.path.exists(netcdflib):
                raise EasyBuildError("%s does not exist", netcdflib)
        else:
            raise EasyBuildError("netCDF(-Fortran) not available")

        ldpaths = [ldflag[2:] for ldflag in os.getenv('LDFLAGS').split(' ')]  # LDFLAGS have form '-L/path/to'

        lapacklibs = []
        for lib in os.getenv('LAPACK_STATIC_LIBS').split(','):
            libpaths = [os.path.join(ldpath, lib) for ldpath in ldpaths]
            lapacklibs.append([libpath for libpath in libpaths if os.path.exists(libpath)][0])
        lapacklib = ' '.join(lapacklibs)
        blaslibs = []
        for lib in os.getenv('BLAS_STATIC_LIBS').split(','):
            libpaths = [os.path.join(ldpath, lib) for ldpath in ldpaths]
            blaslibs.append([libpath for libpath in libpaths if os.path.exists(libpath)][0])
        blaslib = ' '.join(blaslibs)

        qa = {
            'Do you want to run the configuration file maker assistant now (y) or later [n] ?': 'y',
            'Do you want to setup your configuration file for MPICH (y/n) [n] ?': mpich,
            'Please type the directory name where to find a dummy file mpif.h or ignore :': os.getenv('MPI_INC_DIR'),
            '%sthe library gribex or emos%s' % (qpref, qsuff2): aux_lib_gribex,
            '%sthe library ibm%s' % (qpref, qsuff): aux_lib_ibm,
            '%sthe library grib_api%s' % (qpref, qsuff): grib_api_lib,
            '%sthe library grib_api_f90%s' % (qpref, qsuff): grib_api_f90_lib,
            '%sthe JPEG auxilary library if enabled by Grib_api%s' % (qpref, qsuff2): jasperlib,
            '%sthe library netcdf%s' % (qpref, qsuff): netcdflib,
            '%sthe library lapack%s' % (qpref, qsuff): lapacklib,
            '%sthe library blas%s' % (qpref, qsuff): blaslib,
            '%sthe library mpi%s' % (qpref, qsuff): mpilib,
            '%sa MPI dummy library for serial executions, or ignore :' % qpref: '',
            'Please type the directory name where to find grib_api headers, or ignore :': grib_api_inc,
            'Please type the directory name where to find fortint.h or ignore :': '',
            'Please type the directory name where to find netcdf headers, or ignore :': netcdfinc,
            'Do you want to define CANARI (y/n) [y] ?': 'y',
            'Please type the name of the script file used to generate a preprocessed blacklist file, or ignore :': '',
            'Please type the name of the script file used to recover local libraries (gget), or ignore :': '',
            'Please type the options to tune the gnu compilers, or ignore :': os.getenv('F90FLAGS'),
        }

        f90_seq = os.getenv('F90_SEQ')
        if not f90_seq:
            # F90_SEQ is only defined when usempi is enabled
            f90_seq = os.getenv('F90')

        stdqa = OrderedDict([
            (r'Confirm library .* is .*', 'y'),  # this one needs to be tried first!
            (r'.*fortran 90 compiler name .*\s*:\n\(suggestions\s*: .*\)', os.getenv('F90')),
            (r'.*fortran 90 compiler interfaced with .*\s*:\n\(suggestions\s*: .*\)', f90_seq),
            (r'Please type the ABSOLUTE name of .*library.*, or ignore\s*[:]*\s*[\n]*.*', ''),
            (r'Please .* to save this draft configuration file :\n.*', '%s.x' % self.conf_file),
        ])

        no_qa = [
            ".*ignored.",
        ]

        env.setvar('GMKTMP', self.builddir)
        env.setvar('GMKFILE', self.conf_file)

        run_cmd_qa("gmkfilemaker", qa, std_qa=stdqa, no_qa=no_qa)

        # set environment variables for installation dirs
        env.setvar('ROOTPACK', os.path.join(self.installdir, 'rootpack'))
        env.setvar('ROOTBIN', os.path.join(self.installdir, 'rootpack'))
        env.setvar('HOMEPACK', os.path.join(self.installdir, 'pack'))
        env.setvar('HOMEBIN', os.path.join(self.installdir, 'pack'))

    def build_step(self):
        """No separate build procedure for ALADIN (see install_step)."""

        pass

    def test_step(self):
        """Custom built-in test procedure for ALADIN."""

        if self.cfg['runtest']:
            cmd = "test-command"
            run_cmd(cmd, simple=True, log_all=True, log_output=True)

    def install_step(self):
        """Custom install procedure for ALADIN."""

        try:
            os.mkdir(os.getenv('ROOTPACK'))
            os.mkdir(os.getenv('HOMEPACK'))
        except OSError, err:
            raise EasyBuildError("Failed to create rootpack dir in %s: %s", err)

        # create rootpack
        [v1, v2] = self.version.split('_')
        (out, _) = run_cmd("source $GMKROOT/util/berootpack && gmkpack -p master -a -r %s -b %s" % (v1, v2), simple=False)

        packdir_regexp = re.compile("Creating main pack (.*) \.\.\.")
        res = packdir_regexp.search(out)
        if res:
            self.rootpack_dir = os.path.join('rootpack', res.group(1))
        else:
            raise EasyBuildError("Failed to determine rootpack dir.")

        # copy ALADIN sources to right directory
        try:
            src_dirs = [d for d in os.listdir(self.builddir) if not (d.startswith('auxlib') or d.startswith('gmk'))]
            target = os.path.join(self.installdir, self.rootpack_dir, 'src', 'local')
            self.log.info("Copying sources from %s to %s" % (self.builddir, target))
            for srcdir in src_dirs:
                shutil.copytree(os.path.join(self.builddir, srcdir), os.path.join(target, srcdir))
                self.log.info("Copied %s" % srcdir)
        except OSError, err:
            raise EasyBuildError("Failed to copy ALADIN sources: %s", err)

        if self.cfg['parallel']:
            env.setvar('GMK_THREADS', str(self.cfg['parallel']))

        # build rootpack
        run_cmd(os.path.join(self.installdir, self.rootpack_dir, 'ics_master'))

        # restore original $LIBRARY_PATH
        if self.orig_library_path is not None:
            os.environ['LIBRARY_PATH'] = self.orig_library_path

    def sanity_check_step(self):
        """Custom sanity check for ALADIN."""
        bindir = os.path.join(self.rootpack_dir, 'bin')
        libdir = os.path.join(self.rootpack_dir, 'lib')
        custom_paths = {
            'files': [os.path.join(bindir, x) for x in ['MASTER']] +
                     [os.path.join(libdir, 'lib%s.local.a' % x) for x in ['aeo', 'ald', 'arp', 'bip',
                                                                          'bla', 'mpa', 'mse', 'obt',
                                                                          'odb', 'sat', 'scr', 'sct',
                                                                          'sur', 'surfex', 'tal', 'tfl',
                                                                          'uti', 'xla', 'xrd']],
            'dirs': [],
        }
        super(EB_ALADIN, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guesses for environment variables (PATH, ...) for ALADIN."""
        guesses = super(EB_ALADIN, self).make_module_req_guess()
        guesses.update({
            'PATH': [os.path.join(self.rootpack_dir, 'bin')],
        })
        return guesses
