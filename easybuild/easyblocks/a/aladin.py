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
EasyBuild support for building and installing ALADIN, implemented as an easyblock
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
from easybuild.tools.filetools import run_cmd, run_cmd_qa
from easybuild.tools.modules import get_software_root
from easybuild.tools.ordereddict import OrderedDict


class EB_ALADIN(EasyBlock):
    """Support for building/installing ALADIN."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for ALADIN."""
        super(EB_ALADIN, self).__init__(*args, **kwargs)

        self.conf_file = None
        self.conf_filepath = None
        self.comp_stamp = None
        self.rootpack_dir = None

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for ALADIN."""

        extra_vars = [
                      ('optional_extra_param', ['default value', "short description", CUSTOM]),
                     ]
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration procedure for ALADIN."""
        
        # build auxiliary libraries
        auxlibs_dir = None

        my_gnu = None
        if self.toolchain.comp_family() == toolchain.GCC:
            my_gnu = 'y'  # gfortran
        elif self.toolchain.comp_family() == toolchain.INTELCOMP:
            my_gnu = 'i'  # icc/ifort
        else:
            self.log.error("Don't know how to set 'my_gnu' variable in auxlibs build script.")
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
            self.log.error("Failed to build ALADIN: %s" % err)

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
            self.log.error("Failed to build gmkpack: %s" % err)

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
            self.log.error("Failed to remove existing file %s: %s" % (self.conf_filepath, err))

        mpich = 'n'
        if self.toolchain.mpi_family() in [toolchain.MPICH2, toolchain.INTELMPI]:
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
            self.log.error("Don't know which grib lib dir to use for compiler %s" % comp_fam)

        aux_lib_gribex = os.path.join(tmp_installroot, gribdir, 'lib', 'libgribex.a')
        grib_api_lib = os.path.join(get_software_root('grib_api'), 'lib', 'libgrib_api_f90.a')
        grib_api_inc = os.path.join(get_software_root('grib_api'), 'include')
        jasperlib = os.path.join(get_software_root('JasPer'), 'lib', 'libjasper.a')
        netcdflib = os.path.join(get_software_root('netCDF'), 'lib', 'libnetcdf.a')
        netcdfinc = os.path.join(get_software_root('netCDF'), 'include')
        lapacklib = ' '.join([os.path.join(os.getenv('LAPACK_LIB_DIR'), x) for x in os.getenv('LAPACK_STATIC_LIBS').split(',')])
        blaslib = ' '.join([os.path.join(os.getenv('BLAS_LIB_DIR'), x) for x in os.getenv('BLAS_STATIC_LIBS').split(',')])
        mpilib = os.path.join(os.getenv('MPI_LIB_DIR'), os.getenv('MPI_LIB_SHARED'))

        qa = {
              'Do you want to run the configuration file maker assistant now (y) or later [n] ?': 'y',
              'Do you want to setup your configuration file for MPICH (y/n) [n] ?': mpich,
              'Please type the directory name where to find a dummy file mpif.h or ignore :': os.getenv('MPI_INC_DIR'),
              '%sthe library gribex or emos%s' % (qpref, qsuff2): aux_lib_gribex,
              '%sthe library grib_api_f90%s' % (qpref, qsuff): grib_api_lib,
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

        env.setvar('GMKTMP', self.builddir)
        env.setvar('GMKFILE', self.conf_file)

        (out, _) = run_cmd_qa("gmkfilemaker", qa, std_qa=stdqa, simple=False)

        # figure out compiler stamp
        stamp_regexp = re.compile('The compiler will be stamped "(.*)"')
        res = stamp_regexp.search(out)
        if res:
            self.comp_stamp = res.group(1)
            self.log.info("Compiler stamp: %s" % self.comp_stamp)
        else:
            self.log.error("Failed to determine compiler stamp.")

        # set rootpack dir
        if self.toolchain.options['usempi']:
            verstr = '%s.01.MPI%s.x' % (self.version, self.comp_stamp)
        else:
            verstr = '%s.01.%s.x' % (self.version, self.comp_stamp)
        self.rootpack_dir = os.path.join(self.installdir, 'rootpack', verstr)

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
            self.log.error("Failed to create rootpack dir in %s: %s" % err)

        # create rootpack
        [v1, v2] = self.version.split('_')
        run_cmd("source $GMKROOT/util/berootpack && gmkpack -p master -a -r %s -b %s" % (v1, v2))

        # copy ALADIN sources to right directory
        try:
            src_dirs = [d for d in os.listdir(self.builddir) if not (d.startswith('auxlib') or d.startswith('gmk'))]
            target = os.path.join(self.rootpack_dir, 'src', 'local')
            self.log.info("Copying sources from %s to %s" % (self.builddir, target))
            for srcdir in src_dirs:
                shutil.copytree(os.path.join(self.builddir, srcdir), os.path.join(target, srcdir))
                self.log.info("Copied %s" % srcdir)
        except OSError, err:
            self.log.error("Failed to copy ALADIN sources: %s" % err)

        if self.cfg['parallel']:
            env.setvar('GMK_THREADS', self.cfg['parallel'])

        # build rootpack
        run_cmd(os.path.join(self.rootpack_dir, 'ics_master'))

    def sanity_check_step(self):
        """Custom sanity check for ALADIN."""

        custom_paths = {
                        'files': [os.path.join(self.rootpack_dir, 'bin', x) for x in ['MASTER']] +
                                 [os.path.join(self.rootpack_dir, 'lib', 'lib%s.a' % x) for x in ['arp.local']],
                        'dirs': ['dir1', 'dir2'],
                       }

        super(EB_ALADIN, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guesses for environment variables (PATH, ...) for ALADIN."""

        guesses = super(EB_ALADIN, self).make_module_req_guess()

        guesses.update({
                        'VARIABLE': ['value1', 'value2'],
                       })

        return guesses

    def make_module_extra(self):
        """Custom extra module file entries for ALADIN."""

        txt = super(EB_ALADIN, self).make_module_extra()

        txt += self.moduleGenerator.set_environment("VARIABLE", 'value')
        txt += self.moduleGenerator.prepend_paths("PATH_VAR", ['path1', 'path2'])

        return txt
