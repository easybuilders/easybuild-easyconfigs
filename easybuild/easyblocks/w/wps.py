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
EasyBuild support for building and installing WPS, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import fileinput
import os
import re
import shutil
import sys
import tempfile
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.netcdf import set_netcdf_env_vars  #@UnresolvedImport
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import extract_file, patch_perl_script_autoflush, rmtree2
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd, run_cmd_qa


class EB_WPS(EasyBlock):
    """Support for building/installing WPS."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to WPS."""

        super(EB_WPS, self).__init__(*args, **kwargs)

        self.build_in_installdir = True
        self.comp_fam = None
        self.wrfdir = None
        self.compile_script = None

    @staticmethod
    def extra_options():
        testdata_urls = [
            "http://www.mmm.ucar.edu/wrf/src/data/avn_data.tar.gz",
            "http://www.mmm.ucar.edu/wrf/src/wps_files/geog.tar.gz",  # 697MB download, 16GB unpacked!
        ]
        extra_vars = {
            'buildtype': [None, "Specify the type of build (smpar: OpenMP, dmpar: MPI).", MANDATORY],
            'runtest': [True, "Build and run WPS tests", CUSTOM],
            'testdata': [testdata_urls, "URL to test data required to run WPS test", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Configure build:
        - set required environment variables (for netCDF, JasPer)
        - patch compile script and ungrib Makefile for non-default install paths of WRF and JasPer
        - run configure script and figure how to select desired build option
        - patch configure.wps file afterwards to fix 'serial compiler' setting
        """

        # netCDF dependency check + setting env vars (NETCDF, NETCDFF)
        set_netcdf_env_vars(self.log)

        # WRF dependency check
        wrf = get_software_root('WRF')
        if wrf:
            majver = get_software_version('WRF').split('.')[0]
            self.wrfdir = os.path.join(wrf, "WRFV%s" % majver)
        else:
            raise EasyBuildError("WRF module not loaded?")

        # patch compile script so that WRF is found
        self.compile_script = "compile"
        try:
            for line in fileinput.input(self.compile_script, inplace=1, backup='.orig.wrf'):
                line = re.sub(r"^(\s*set\s*WRF_DIR_PRE\s*=\s*)\${DEV_TOP}(.*)$", r"\1%s\2" % self.wrfdir, line)
                sys.stdout.write(line)
        except IOError, err:
            raise EasyBuildError("Failed to patch %s script: %s", self.compile_script, err)

        # libpng dependency check
        libpng = get_software_root('libpng')
        zlib = get_software_root('zlib')
        if libpng:
            paths = [libpng]
            if zlib:
                paths.insert(0, zlib)
            libpnginc = ' '.join(['-I%s' % os.path.join(path, 'include') for path in paths])
            libpnglib = ' '.join(['-L%s' % os.path.join(path, 'lib') for path in paths])
        else:
            raise EasyBuildError("libpng module not loaded?")

        # JasPer dependency check + setting env vars
        jasper = get_software_root('JasPer')
        if jasper:
            env.setvar('JASPERINC', os.path.join(jasper, "include"))
            jasperlibdir = os.path.join(jasper, "lib")
            env.setvar('JASPERLIB', jasperlibdir)
            jasperlib = "-L%s" % jasperlibdir
        else:
            raise EasyBuildError("JasPer module not loaded?")

        # patch ungrib Makefile so that JasPer is found
        fn = os.path.join("ungrib", "src", "Makefile")
        jasperlibs = "%s -ljasper %s -lpng" % (jasperlib, libpnglib)
        try:
            for line in fileinput.input(fn, inplace=1, backup='.orig.JasPer'):
                line = re.sub(r"^(\s*-L\.\s*-l\$\(LIBTARGET\))(\s*;.*)$", r"\1 %s\2" % jasperlibs, line)
                line = re.sub(r"^(\s*\$\(COMPRESSION_LIBS\))(\s*;.*)$", r"\1 %s\2" % jasperlibs, line)
                sys.stdout.write(line)
        except IOError, err:
            raise EasyBuildError("Failed to patch %s: %s", fn, err)

        # patch arch/Config.pl script, so that run_cmd_qa receives all output to answer questions
        patch_perl_script_autoflush(os.path.join("arch", "Config.pl"))

        # configure

        # determine build type option to look for
        self.comp_fam = self.toolchain.comp_family()
        build_type_option = None

        if LooseVersion(self.version) >= LooseVersion("3.4"):

            knownbuildtypes = {
                               'smpar': 'serial',
                               'dmpar': 'dmpar'
                              }

            if self.comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
                build_type_option = " Linux x86_64, Intel compiler"

            elif self.comp_fam == toolchain.GCC:  #@UndefinedVariable
                build_type_option = "Linux x86_64 g95 compiler"

            else:
                raise EasyBuildError("Don't know how to figure out build type to select.")

        else:

            knownbuildtypes = {
                               'smpar': 'serial',
                               'dmpar': 'DM parallel'
                              }

            if self.comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
                build_type_option = "PC Linux x86_64, Intel compiler"

            elif self.comp_fam == toolchain.GCC:  #@UndefinedVariable
                build_type_option = "PC Linux x86_64, gfortran compiler,"
                knownbuildtypes['dmpar'] = knownbuildtypes['dmpar'].upper()

            else:
                raise EasyBuildError("Don't know how to figure out build type to select.")

        # check and fetch selected build type
        bt = self.cfg['buildtype']

        if not bt in knownbuildtypes.keys():
            raise EasyBuildError("Unknown build type: '%s'. Supported build types: %s", bt, knownbuildtypes.keys())

        # fetch option number based on build type option and selected build type
        build_type_question = "\s*(?P<nr>[0-9]+).\s*%s\s*\(?%s\)?\s*\n" % (build_type_option, knownbuildtypes[bt])

        cmd = "./configure"
        qa = {}
        no_qa = [".*compiler is.*"]
        std_qa = {
                  # named group in match will be used to construct answer
                  r"%s(.*\n)*Enter selection\s*\[[0-9]+-[0-9]+\]\s*:" % build_type_question: "%(nr)s",
                 }

        run_cmd_qa(cmd, qa, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

        # make sure correct compilers and compiler flags are being used
        comps = {
                 'SCC': "%s -I$(JASPERINC) %s" % (os.getenv('CC'), libpnginc),
                 'SFC': os.getenv('F90'),
                 'DM_FC': os.getenv('MPIF90'),
                 'DM_CC': os.getenv('MPICC'),
                 'FC': os.getenv('MPIF90'),
                 'CC': os.getenv('MPICC'),
                }
        fn = 'configure.wps'
        for line in fileinput.input(fn, inplace=1, backup='.orig.comps'):
            for (k, v) in comps.items():
                line = re.sub(r"^(%s\s*=\s*).*$" % k, r"\1 %s" % v, line)
            sys.stdout.write(line)

    def build_step(self):
        """Build in install dir using compile script."""

        cmd = "./%s" % self.compile_script
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
        """Run WPS test (requires large dataset to be downloaded). """

        wpsdir = None

        def run_wps_cmd(cmdname, mpi_cmd=True):
            """Run a WPS command, and check for success."""

            cmd = os.path.join(wpsdir, "%s.exe" % cmdname)
            
            if mpi_cmd:
                cmd = self.toolchain.mpi_cmd_for(cmd, 1)
            
            (out, _) = run_cmd(cmd, log_all=True, simple=False)

            re_success = re.compile("Successful completion of %s" % cmdname)
            if not re_success.search(out):
                raise EasyBuildError("%s.exe failed (pattern '%s' not found)?", cmdname, re_success.pattern)

        if self.cfg['runtest']:
            if not self.cfg['testdata']:
                raise EasyBuildError("List of URLs for testdata not provided.")

            wpsdir = os.path.join(self.builddir, "WPS")

            try:
                # create temporary directory
                tmpdir = tempfile.mkdtemp()
                os.chdir(tmpdir)

                # download data
                testdata_paths = []
                for testdata in self.cfg['testdata']:
                    path = self.obtain_file(testdata)
                    if not path:
                        raise EasyBuildError("Downloading file from %s failed?", testdata)
                    testdata_paths.append(path)

                # unpack data
                for path in testdata_paths:
                    extract_file(path, tmpdir)

                # copy namelist.wps file
                fn = "namelist.wps"
                shutil.copy2(os.path.join(wpsdir, fn), tmpdir)
                namelist_file = os.path.join(tmpdir, fn)

                # GEOGRID

                # setup directories and files
                for d in os.listdir(os.path.join(tmpdir, "geog")):
                    os.symlink(os.path.join(tmpdir, "geog", d), os.path.join(tmpdir, d))

                # patch namelist.wps file for geogrib
                for line in fileinput.input(namelist_file, inplace=1, backup='.orig.geogrid'):
                    line = re.sub(r"^(\s*geog_data_path\s*=\s*).*$", r"\1 '%s'" % tmpdir, line)
                    sys.stdout.write(line)

                # GEOGRID.TBL
                geogrid_dir = os.path.join(tmpdir, "geogrid")
                os.mkdir(geogrid_dir)
                os.symlink(os.path.join(wpsdir, "geogrid", "GEOGRID.TBL.ARW"),
                           os.path.join(geogrid_dir, "GEOGRID.TBL"))

                # run geogrid.exe
                run_wps_cmd("geogrid")

                # UNGRIB

                # determine start and end time stamps of grib files
                grib_file_prefix = "fnl_"
                k = len(grib_file_prefix)
                fs = [f for f in sorted(os.listdir('.')) if f.startswith(grib_file_prefix)]
                start = "%s:00:00" % fs[0][k:]
                end = "%s:00:00" % fs[-1][k:]

                # patch namelist.wps file for ungrib
                shutil.copy2(os.path.join(wpsdir, "namelist.wps"), tmpdir)

                for line in fileinput.input(namelist_file, inplace=1, backup='.orig.ungrib'):
                    line = re.sub(r"^(\s*start_date\s*=\s*).*$", r"\1 '%s','%s'," % (start, start), line)
                    line = re.sub(r"^(\s*end_date\s*=\s*).*$", r"\1 '%s','%s'," % (end, end), line)
                    sys.stdout.write(line)

                # copy correct Vtable
                shutil.copy2(os.path.join(wpsdir, "ungrib", "Variable_Tables", "Vtable.ARW"),
                             os.path.join(tmpdir, "Vtable"))

                # run link_grib.csh script
                cmd = "%s %s*" % (os.path.join(wpsdir, "link_grib.csh"), grib_file_prefix)
                run_cmd(cmd, log_all=True, simple=True)

                # run ungrib.exe
                run_wps_cmd("ungrib", mpi_cmd=False)

                # METGRID.TBL

                metgrid_dir = os.path.join(tmpdir, "metgrid")
                os.mkdir(metgrid_dir)
                os.symlink(os.path.join(wpsdir, "metgrid", "METGRID.TBL.ARW"),
                           os.path.join(metgrid_dir, "METGRID.TBL"))

                # run metgrid.exe
                run_wps_cmd('metgrid')

                # clean up
                rmtree2(tmpdir)

                os.chdir(self.builddir)

            except OSError, err:
                raise EasyBuildError("Failed to run WPS test: %s", err)

    # installing is done in build_step, so we can run tests
    def install_step(self):
        """Building was done in install dir, so just do some cleanup here."""

        # make sure JASPER environment variables are unset
        env_vars = ['JASPERINC', 'JASPERLIB']

        for env_var in env_vars:
            if os.environ.has_key(env_var):
                os.environ.pop(env_var)

    def sanity_check_step(self):
        """Custom sanity check for WPS."""
        custom_paths = {
            'files': ['WPS/%s' % x for x in ['geogrid.exe', 'metgrid.exe', 'ungrib.exe']],
            'dirs': [],
        }
        super(EB_WPS, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Make sure PATH and LD_LIBRARY_PATH are set correctly."""
        return {
            'PATH': [self.name],
            'LD_LIBRARY_PATH': [self.name],
            'MANPATH': [],
        }

    def make_module_extra(self):
        """Add netCDF environment variables to module file."""
        txt = super(EB_WPS, self).make_module_extra()
        for var in ['NETCDF', 'NETCDFF']:
            # check whether value is defined for compatibility with --module-only
            if os.getenv(var) is not None:
                txt += self.module_generator.set_environment(var, os.getenv(var))
        return txt
