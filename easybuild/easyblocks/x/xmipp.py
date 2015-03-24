##
# Copyright 2015-2015 Ghent University
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
EasyBuild support for building and installing Xmipp, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
"""
import glob
import os

import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import mkdir, extract_file
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd

from easybuild.easyblocks.generic.pythonpackage import det_pylibdir


class EB_Xmipp(EasyBlock):
    """Support for building/installing Xmipp."""

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, enable building in installation directory."""
        super(EB_Xmipp, self).__init__(*args, **kwargs)
        self.build_in_installdir = True

    def extract_step(self):
        """Extract Xmipp sources."""
        # strip off 'xmipp' part to avoid having everything in a 'xmipp' subdirectory
        self.cfg.update('unpack_options', '--strip-components=1')
        super(EB_Xmipp, self).extract_step()

    def configure_step(self):
        """Configure Xmipp build via a provided wrapper around scons."""
        # check if all our dependencies are in place
        self.python_root = get_software_root('Python')
        if not self.python_root:
            self.log.error("Python not loaded as a dependency, which is required for %s" % self.name)
        python_libdir = det_pylibdir()
        self.python_short_ver = '.'.join(get_software_version('Python').split('.')[:2])

        java_root = get_software_root('Java')
        if not java_root:
            self.log.error("Java not loaded as a dependency, which is required for %s" % self.name)

        # extract some dependencies that we really need and can't find anywhere else
        # alglib tarball has version in name, so lets find it with a glob
        # we can't do this in extract step before these are in the original sources tarball, so we need to know
        # startdir first
        external_path = os.path.join(self.cfg['start_dir'], 'external')
        alglib_tar = glob.glob(os.path.join(external_path, 'alglib*.tgz'))[0]
        for src in ['bilib.tgz', 'bilib.tgz', 'condor.tgz', alglib_tar, 'scons.tgz']:
            extract_file(os.path.join(external_path, src), external_path)

        # make sure we are back in the start dir
        os.chdir(self.cfg['start_dir'])

        # build step expects these to exist
        mkdir(os.path.join(self.cfg['start_dir'], 'bin'))
        mkdir(os.path.join(self.cfg['start_dir'], 'lib'))

        python_inc_dir = os.path.join(self.python_root, 'include', 'python%s' % self.python_short_ver)
        numpy_inc_dir = os.path.join(self.python_root, python_libdir, 'numpy', 'core', 'include')
        if self.toolchain.mpi_family() == toolchain.INTELMPI:
            mpi_bindir = os.path.join(get_software_root('impi'), 'intel64', 'bin')
        else:
            mpi_bindir = os.path.join(get_software_root(self.toolchain.MPI_MODULE_NAME[0]), 'bin')

        if not os.path.exists(numpy_inc_dir):
            self.log.error("numpy 'include' directory %s not found" % numpy_inc_dir)

        if not os.path.exists(mpi_bindir):
            self.log.error("MPI 'bin' subdir %s does not exist" % mpi_bindir)

        cmd = ' '.join([
            self.cfg['preconfigopts'],
            'python external/scons/scons.py',
            'mode=configure',
            '-j %s' % self.cfg['parallel'],
            '--config=force',
            'profile=no',
            'fast=yes',
            'warn=no',
            'release=yes',
            'gtest=no',
            'cuda=no',
            'debug=no',
            'matlab=no',
            'java=no',
            'LINKERFORPROGRAMS="$CXX"',
            'MPI_BINDIR=%s' % mpi_bindir,
            'JAVA_HOME=%s' % java_root,
            'JAVAC=javac',
            'CC="$CC"',
            'CXXFLAGS="$CXXFLAGS -DMPICH_IGNORE_CXX_SEEK -I%s -I%s"' % (python_inc_dir, numpy_inc_dir),
            'CXX="$CXX"',
            'MPI_CC="$MPICC"',
            'MPI_CXX="$MPICXX"',
            'MPI_INCLUDE="$MPI_INC_DIR"',
            'MPI_LIBDIR="$MPI_LIB_DIR"',
            'MPI_LINKERFORPROGRAMS="$MPICC"',
            'LIBPATH="$LD_LIBRARY_PATH"',
            self.cfg['configopts'],
        ])
        run_cmd(cmd, log_all=True, simple=True)

    def build_step(self):
        """Custom build procedure for Xmipp: call the scons wrapper with compile argument"""
        cmd = ' '.join([
            self.cfg['prebuildopts'],
            'LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/lib',
            'python external/scons/scons.py',
            'mode=compile',
            '-j %s' % self.cfg['parallel'],
            self.cfg['buildopts'],
        ])
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """install step for Xmipp, this builds a local database and seems to do some tests?"""
        python_dynlib_dir = os.path.join(self.python_root, 'lib', 'python%s' % self.python_short_ver, 'lib-dynload')

        if not os.path.exists(python_dynlib_dir):
            self.log.error("Python lib-dynload dir %s not found" % python_dynlib_dir)

        extra_pythonpaths = [
            os.path.join(self.cfg['start_dir'], 'protocols'),
            os.path.join(self.cfg['start_dir'], 'libraries', 'bindings', 'python'),
            python_dynlib_dir,
        ]
        cmd = ' '.join([
            self.cfg['preinstallopts'],
            'XMIPP_HOME=%s' % self.cfg['start_dir'],
            'PATH=%s:$PATH' % os.path.join(self.cfg['start_dir'], 'bin'),
            'PYTHONPATH="%s"' % os.pathsep.join(['$PYTHONPATH'] + extra_pythonpaths),
            'python setup.py install',
            self.cfg['installopts'],
        ])
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for Xmipp."""
        custom_paths = {
            'files': ['xmipp_%s' % x for x in ['imagej', 'mpi_run', 'phantom_create', 'tomo_project', 'volume_align']],
            'dirs': ['lib'],
        }
        super(EB_Xmipp, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Define Xmipp specific variables in generated module file, i.e. XMIPP_HOME."""
        txt = super(EB_Xmipp, self).make_module_extra()
        txt += self.module_generator.set_environment('XMIPP_HOME', self.installdir)
        return txt
