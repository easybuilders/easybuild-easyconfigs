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
@author: Pablo Escobar (sciCORE, SIB, University of Basel)
@author: Kenneth Hoste (Ghent University)
"""
import os
import re
import stat

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, mkdir, write_file
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_Xmipp(EasyBlock):
    """
    easyblock to install Xmipp
    """

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
        """Configure by defining $CONFIGURE_ARGS"""
        if self.toolchain.mpi_family() == toolchain.INTELMPI:
            mpi_bindir = os.path.join(get_software_root('impi'), 'intel64', 'bin')
        else:
            mpi_bindir = os.path.join(get_software_root(self.toolchain.MPI_MODULE_NAME[0]), 'bin')

        root_java = get_software_root("Java")
        if not get_software_root("Java"):
            raise EasyBuildError("Module for dependency Java not loaded.")

        configure_args = ' '.join([
            'profile=no fast=yes warn=no release=yes gtest=yes static=no cuda=no debug=no matlab=no',
            'LINKERFORPROGRAMS=%s' % os.getenv('CXX'),
            'MPI_BINDIR=%s' % mpi_bindir,
            'MPI_LIB=mpi',
            'JAVA_HOME=%s' % os.getenv('JAVA_HOME'),
            'JAVAC=javac',
            'CC=%s' % os.getenv('CC'),
            'CXXFLAGS=',
            'CXX=%s' % os.getenv('CXX'),
            'MPI_CC=%s' % os.getenv('MPICC'),
            'CCFLAGS=',
            'MPI_CXX=%s' % os.getenv('MPICXX'),
            'MPI_INCLUDE=%s' % os.getenv('MPI_INC_DIR'),
            'MPI_LIBDIR=%s' % os.getenv('MPI_LIB_DIR'),
            'MPI_LINKERFORPROGRAMS=%s' % os.getenv('MPICC'),
            'LIBPATH=%s' % os.getenv('LD_LIBRARY_PATH'),
        ])

        # defining env var CONFIGURE_ARGS the install.sh script will fetch all the required paths
        # CONFIGURE_ARGS is inside install.sh and it's empty by default
        self.log.info("configure arguments to be picked up by Xmipp install.sh script: %s", configure_args)
        env.setvar('CONFIGURE_ARGS', configure_args)

    def build_step(self):
        """No custom build step (see install step)."""
        pass

    def install_step(self):
        """Build/install Xmipp using provided install.sh script."""

        # extend $PYTHONPATH
        pythonpath = os.environ.get('PYTHONPATH', '')
        pythonpaths = [
            os.path.join(self.installdir, 'protocols'),
            os.path.join(self.installdir, 'lib', 'python2.7', 'site-packages'),
            os.path.join(self.installdir, 'libraries', 'bindings', 'python'),
            pythonpath,
        ]
        mkdir(os.path.join(self.installdir, 'lib', 'python2.7', 'site-packages'), parents=True)

        # put dummy xmipp_python script in place if Python is used as a dependency
        bindir = os.path.join(self.installdir, 'bin')
        mkdir(bindir)
        python_root = get_software_root('Python')
        if python_root:
            xmipp_python = os.path.join(bindir, 'xmipp_python')
            xmipp_python_script_body = '\n'.join([
                '#!/bin/sh',
                '%s/bin/python "$@"' % python_root,
            ])
            write_file(xmipp_python, xmipp_python_script_body)
            adjust_permissions(xmipp_python, stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

            env.setvar('CPATH', os.pathsep.join([
                os.path.join(python_root, 'include', 'python2.7'),
                os.path.join(python_root, 'lib', 'python2.7', 'site-packages', 'numpy', 'core', 'include'),
                os.environ.get('CPATH', ''),
            ]))

            pythonpaths.append(os.path.join(python_root, 'lib', 'python2.7', 'site-packages'))

        env.setvar('PYTHONPATH', os.pathsep.join(pythonpaths))

        cmd_opts = []
        for dep in ['FFTW', 'HDF5', ('libjpeg-turbo', 'jpeg'), ('LibTIFF', 'tiff'), 'matplotlib', 'Python', 'SQLite',
                    'Tcl', 'Tk']:
            if isinstance(dep, tuple):
                dep, opt = dep
            else:
                opt = dep.lower()
            if get_software_root(dep):
                cmd_opts.append('--%s=false' % opt)
                # Python should also provide numpy/mpi4py
                if dep == 'Python':
                    cmd_opts.extend(['--numpy=false', '--mpi4py=false'])

        if '--tcl=false' in cmd_opts and '--tk=false' in cmd_opts:
            cmd_opts.append('--tcl-tk=false')

        cmd = './install.sh -j %s --unattended=true %s' % (self.cfg['parallel'], ' '.join(cmd_opts))
        out, _ = run_cmd(cmd, log_all=True, simple=False)

        if not re.search("Xmipp has been successfully compiled", out):
            raise EasyBuildError("Xmipp installation did not complete successfully?")

    def sanity_check_step(self):
        """Custom sanity check for Xmipp."""
        custom_paths = {
            # incomplete list, random picks, cfr. http://xmipp.cnb.csic.es/twiki/bin/view/Xmipp/ListOfProgramsv3
            'files': ['bin/xmipp_%s' % x for x in ['compile', 'imagej', 'mpi_run', 'phantom_create',
                                                   'transform_filter', 'tomo_project', 'volume_align']],
            'dirs': ['lib'],
        }
        super(EB_Xmipp, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Define Xmipp specific variables in generated module file, i.e. XMIPP_HOME."""
        txt = super(EB_Xmipp, self).make_module_extra()
        txt += self.module_generator.set_environment('XMIPP_HOME', self.installdir)
        return txt
