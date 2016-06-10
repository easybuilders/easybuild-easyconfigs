##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for building and installing Xmipp, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
@author: Pablo Escobar (sciCORE, SIB, University of Basel)
@author: Kenneth Hoste (Ghent University)
"""
import fileinput
import os
import re
import stat
import sys

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.pythonpackage import det_pylibdir
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, mkdir, write_file
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_Xmipp(EasyBlock):
    """
    easyblock to install Xmipp
    """

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, enable building in installation directory."""
        super(EB_Xmipp, self).__init__(*args, **kwargs)
        self.build_in_installdir = True
        self.xmipp_pythonpaths = []

    def extract_step(self):
        """Extract Xmipp sources."""
        # strip off 'xmipp' part to avoid having everything in a 'xmipp' subdirectory
        self.cfg.update('unpack_options', '--strip-components=1')
        super(EB_Xmipp, self).extract_step()

    def configure_step(self):
        """Set configure options."""
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
            # pass $CXXFLAGS in Python list syntax and avoid spaces, e.g.: ['-O2','-march=native']
            'CXXFLAGS=%s' % str(os.getenv('CXXFLAGS').split(' ')).replace(' ', ''),
            'CXX=%s' % os.getenv('CXX'),
            'MPI_CC=%s' % os.getenv('MPICC'),
            # pass $CFLAGS in Python list syntax and avoid spaces, e.g.: ['-O2','-march=native']
            'CCFLAGS=%s' % str(os.getenv('CFLAGS').split(' ')).replace(' ', ''),
            'MPI_CXX=%s' % os.getenv('MPICXX'),
            'MPI_INCLUDE=%s' % os.getenv('MPI_INC_DIR'),
            'MPI_LIBDIR=%s' % os.getenv('MPI_LIB_DIR'),
            'MPI_LINKERFORPROGRAMS=%s' % os.getenv('MPICXX'),
            'LIBPATH=%s' % os.getenv('LD_LIBRARY_PATH'),
        ])

        # define list of configure options, which will be passed to Xmipp's install.sh script via --configure-args
        self.cfg['configopts'] = configure_args
        self.log.info("Configure arguments for Xmipp install.sh script: %s", self.cfg['configopts'])

    def build_step(self):
        """No custom build step (see install step)."""
        pass

    def install_step(self):
        """Build/install Xmipp using provided install.sh script."""
        pylibdir = det_pylibdir()

        self.xmipp_pythonpaths = [
            # location where Python packages will be installed by Xmipp installer
            pylibdir,
            'protocols',
            os.path.join('libraries', 'bindings', 'python'),
        ]

        python_root = get_software_root('Python')
        if python_root:
            # extend $PYTHONPATH
            all_pythonpaths = [os.path.join(self.installdir, p) for p in self.xmipp_pythonpaths]
            # required so packages installed as extensions in Pythpn dep are picked up
            all_pythonpaths.append(os.path.join(python_root, pylibdir))
            all_pythonpaths.append(os.environ.get('PYTHONPATH', ''))

            env.setvar('PYTHONPATH', os.pathsep.join(all_pythonpaths))

            # location where Python packages will be installed by Xmipp installer must exist already (setuptools)
            mkdir(os.path.join(self.installdir, pylibdir), parents=True)

            # put dummy xmipp_python script in place if Python is used as a dependency
            bindir = os.path.join(self.installdir, 'bin')
            mkdir(bindir)

            xmipp_python = os.path.join(bindir, 'xmipp_python')
            xmipp_python_script_body = '\n'.join([
                '#!/bin/sh',
                '%s/bin/python "$@"' % python_root,
            ])
            write_file(xmipp_python, xmipp_python_script_body)
            adjust_permissions(xmipp_python, stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

            pyshortver = '.'.join(get_software_version('Python').split('.')[:2])

            # make sure Python.h and numpy header are found
            env.setvar('CPATH', os.pathsep.join([
                os.path.join(python_root, 'include', 'python%s' % pyshortver),
                os.path.join(python_root, pylibdir, 'numpy', 'core', 'include'),
                os.environ.get('CPATH', ''),
            ]))

        cmd_opts = []

        # disable (re)building of supplied dependencies
        dep_names = [dep['name'] for dep in self.cfg['dependencies']]
        for dep in ['FFTW', 'HDF5', ('libjpeg-turbo', 'jpeg'), ('LibTIFF', 'tiff'), 'matplotlib', 'Python', 'SQLite',
                    'Tcl', 'Tk']:
            if isinstance(dep, tuple):
                dep, opt = dep
            else:
                opt = dep.lower()
            # don't check via get_software_root, check listed dependencies directly (relevant for FFTW)
            if dep in dep_names:
                cmd_opts.append('--%s=false' % opt)
                # Python should also provide numpy/mpi4py
                if dep == 'Python':
                    cmd_opts.extend(['--numpy=false', '--mpi4py=false'])

        if '--tcl=false' in cmd_opts and '--tk=false' in cmd_opts:
            cmd_opts.append('--tcl-tk=false')

        # patch install.sh script to inject configure options
        # setting $CONFIGURE_ARGS or using --configure-args doesn't work...
        for line in fileinput.input('install.sh', inplace=1, backup='.orig.eb'):
            line = re.sub(r"^CONFIGURE_ARGS.*$", 'CONFIGURE_ARGS="%s"' % self.cfg['configopts'], line)
            sys.stdout.write(line)

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
        txt += self.module_generator.prepend_paths('PYTHONPATH', self.xmipp_pythonpaths)
        return txt
