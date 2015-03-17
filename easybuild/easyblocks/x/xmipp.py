##
# Copyright 2009-2015 Ghent University
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

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import mkdir, extract_file
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_Xmipp(EasyBlock):
    """Support for building/installing Xmipp."""

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, enable building in installation directory."""
        super(self.__class__, self).__init__(*args, **kwargs)
        self.build_in_installdir = True

    def extract_step(self):
        """Extract sources."""
        # strip off 'xmipp' part to avoid having everything in a 'xmipp' subdirectory
        self.cfg['unpack_options'] = "--strip-components=1"
        super(self.__class__, self).extract_step()

    def configure_step(self):
        """Configure xmipp build via a provided wrapper around sconss."""
        # install step expects these to exist
        mkdir('lib')
        mkdir('bin')
        # run interactive 'config' script to generate install.info file
        try:
            # ln -s `which python` xmipp_python
            orig = os.path.join(get_software_root('Python'), 'bin', 'python')
            dest = 'xmipp_python'
            os.symlink(orig, dest)
            # ln -s $EBROOTPYTHON/lib/python2.7 lib/python2.7
            self.python_short_ver = ".".join(get_software_version('Python').split(".")[0:2])
            orig = os.path.join(get_software_root('Python'), 'lib', 'python%s' % self.python_short_ver)
            dest = os.path.join('lib', 'python%s' % self.python_short_ver)
            os.symlink(orig, dest)
        except OSError as err:
            self.log.error("Failed to symlink %s to %s: %s" % (orig, dest, err))

        # extract some dependencies that we really need and can't find anywhere else
        # alglib tarball has version in name, so lets find it with a glob
        alglib_tar = glob.glob(os.path.join(os.getcwd(), 'external', 'alglib*.tgz'))[0]
        for src in ['bilib.tgz', 'bilib.tgz', 'condor.tgz', alglib_tar]:
            external_path = os.path.join(os.getcwd(), 'external')
            extract_file(os.path.join(external_path, src), external_path)

        cmd = ('{preconfigopts} PATH=$PWD:$PATH xmipp_python external/scons/scons.py mode=configure -j {parallel}'
               ' --config=force  profile=no fast=yes warn=no release=yes gtest=no cuda=no debug=no matlab=no'
               ' java=no LINKERFORPROGRAMS="$CXX" MPI_BINDIR="$EBROOTIMPI" JAVA_HOME="$JAVA_HOME" JAVAC=javac CC="$CC"'
               ' CXXFLAGS="$CXXFLAGS -DMPICH_IGNORE_CXX_SEEK -I$EBROOTPYTHON/include/python{short_python_ver}"'
               ' CXX="$CXX" MPI_CC="$MPICC" MPI_CXX="$MPICXX" MPI_INCLUDE="$MPI_INC_DIR" MPI_LIBDIR="$MPI_LIB_DIR"'
               ' MPI_LINKERFORPROGRAMS="$MPICC" LIBPATH="$LD_LIBRARY_PATH" {configopts}').format(
                   parallel=self.cfg['parallel'], short_python_ver=self.python_short_ver,
                   preconfigopts=self.cfg['preconfigopts'], configopts=self.cfg['configopts']
                   )
        run_cmd(cmd, log_all=True, simple=True)

    def build_step(self):
        """Custom build procedure for Xmipp: call the scons wrapper with compile argument"""
        cmd = 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/lib PATH=$PWD:$PATH xmipp_python external/scons/scons.py' \
              'mode=compile -j {parallel}'.format(parallel=self.cfg['parallel'])

        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """install step for xmipp, this builds a local database and seems to do some tests?"""
        cmd = 'XMIPP_HOME=$PWD PATH=$PWD:$PWD/bin:$PATH PYTHONPATH=$PYTHONPATH:$PWD/protocols:' \
              '$PWD/libraries/bindings/python/:$EBROOTPYTHON/lib/python{short_python_ver}/lib-dynload/' \
              ' python setup.py install'.format(self.python_short_ver)
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for GAMESS-US."""
        custom_paths = {
            'files': ['xmipp_%s' % x for x in ['imagej', 'mpi_run', 'phantom_create', 'tomo_project', 'volume_align']],
            'dirs': ['lib/'],
        }
        super(self.__class__, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Define GAMESS-US specific variables in generated module file, i.e. $GAMESSUSROOT."""
        txt = super(self.__class__, self).make_module_extra()
        txt += self.module_generator.set_environment('XMIPP_HOME', '$root')
        return txt
