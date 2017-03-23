##
# Copyright 2009-2017 Ghent University
# Copyright 2015-2016 Stanford University
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
EasyBuild support for VMD, implemented as an easyblock

@author: Stephane Thiell (Stanford University)
@author: Kenneth Hoste (HPC-UGent)
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.pythonpackage import det_pylibdir
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import change_dir
from easybuild.tools.run import run_cmd
from easybuild.tools.modules import get_software_root, get_software_version
import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain


class EB_VMD(ConfigureMake):
    """Easyblock for building and installing VMD"""

    def configure_step(self):
        """
        Configure VMD for building.
        """
        # make sure required dependencies are available
        deps = {}
        for dep in ['FLTK', 'Mesa', 'netCDF', 'Python', 'Tcl', 'Tk']:
            deps[dep] = get_software_root(dep)
            if deps[dep] is None:
                raise EasyBuildError("Required dependency %s is missing", dep)

        # optional dependencies
        for dep in ['ACTC', 'CUDA', 'OptiX']:
            deps[dep] = get_software_root(dep)

        # specify Tcl/Tk locations & libraries
        tclinc = os.path.join(deps['Tcl'], 'include')
        tcllib = os.path.join(deps['Tcl'], 'lib')
        env.setvar('TCL_INCLUDE_DIR', tclinc)
        env.setvar('TCL_LIBRARY_DIR', tcllib)

        env.setvar('TK_INCLUDE_DIR', os.path.join(deps['Tk'], 'include'))
        env.setvar('TK_LIBRARY_DIR', os.path.join(deps['Tk'], 'lib'))

        tclshortver = '.'.join(get_software_version('Tcl').split('.')[:2])
        self.cfg.update('buildopts', 'TCLLDFLAGS="-ltcl%s"' % tclshortver)

        # Python locations
        pyshortver = '.'.join(get_software_version('Python').split('.')[:2])
        env.setvar('PYTHON_INCLUDE_DIR', os.path.join(deps['Python'], 'include/python%s' % pyshortver))
        pylibdir = det_pylibdir()
        python_libdir = os.path.join(deps['Python'], os.path.dirname(pylibdir))
        env.setvar('PYTHON_LIBRARY_DIR', python_libdir)

        # numpy include location, easiest way to determine it is via numpy.get_include()
        out, ec = run_cmd("python -c 'import numpy; print numpy.get_include()'", simple=False)
        if ec:
            raise EasyBuildError("Failed to determine numpy include directory: %s", out)
        else:
            env.setvar('NUMPY_INCLUDE_DIR', out.strip())

        # compiler commands
        self.cfg.update('buildopts', 'CC="%s"' % os.getenv('CC'))
        self.cfg.update('buildopts', 'CCPP="%s"' % os.getenv('CXX'))

        # source tarballs contains a 'plugins' and 'vmd-<version>' directory
        vmddir = os.path.join(self.cfg['start_dir'], '%s-%s' % (self.name.lower(), self.version))

        # plugins need to be built first (see http://www.ks.uiuc.edu/Research/vmd/doxygen/compiling.html)
        change_dir(os.path.join(self.cfg['start_dir'], 'plugins'))
        cmd = "make LINUXAMD64 TCLLIB='-F%s' TCLINC='-I%s' %s" % (tcllib, tclinc, self.cfg['buildopts'])
        run_cmd(cmd, log_all=True, simple=False)

        # create plugins distribution
        plugindir = os.path.join(vmddir, 'plugins')
        env.setvar('PLUGINDIR', plugindir)
        self.log.info("Generating VMD plugins in %s", plugindir)
        run_cmd("make distrib %s" % self.cfg['buildopts'], log_all=True, simple=False)

        # explicitely mention whether or not we're building with CUDA/OptiX support
        if deps['CUDA']:
            self.log.info("Building with CUDA %s support", get_software_version('CUDA'))
            if deps['OptiX']:
                self.log.info("Building with Nvidia OptiX %s support", get_software_version('OptiX'))
            else:
                self.log.warn("Not building with Nvidia OptiX support!")
        else:
            self.log.warn("Not building with CUDA nor OptiX support!")

        # see http://www.ks.uiuc.edu/Research/vmd/doxygen/configure.html
        # LINUXAMD64: Linux 64-bit
        # LP64: build VMD as 64-bit binary
        # IMD: enable support for Interactive Molecular Dynamics (e.g. to connect to NAMD for remote simulations)
        # PTHREADS: enable support for POSIX threads
        # COLVARS: enable support for collective variables (related to NAMD/LAMMPS)
        # NOSILENT: verbose build command
        self.cfg.update('configopts', "LINUXAMD64 LP64 IMD PTHREADS COLVARS NOSILENT")

        # add additional configopts based on available dependencies
        for key in deps:
            if deps[key]:
                if key == 'Mesa':
                    self.cfg.update('configopts', "OPENGL MESA")
                elif key == 'OptiX':
                    self.cfg.update('configopts', "LIBOPTIX")
                elif key == 'Python':
                    self.cfg.update('configopts', "PYTHON NUMPY")
                else:
                    self.cfg.update('configopts', key.upper())

        # configure for building with Intel compilers specifically
        if self.toolchain.comp_family() == toolchain.INTELCOMP:
            self.cfg.update('configopts', 'ICC')

        # specify install location using environment variables
        env.setvar('VMDINSTALLBINDIR', os.path.join(self.installdir, 'bin'))
        env.setvar('VMDINSTALLLIBRARYDIR', os.path.join(self.installdir, 'lib'))

        # configure in vmd-<version> directory
        change_dir(vmddir)
        run_cmd("%s ./configure %s" % (self.cfg['preconfigopts'], self.cfg['configopts']))

        # change to 'src' subdirectory, ready for building
        change_dir(os.path.join(vmddir, 'src'))

    def sanity_check_step(self):
        """Custom sanity check for VMD."""
        custom_paths = {
            'files': ['bin/vmd'],
            'dirs': ['lib'],
        }
        super(EB_VMD, self).sanity_check_step(custom_paths=custom_paths)
