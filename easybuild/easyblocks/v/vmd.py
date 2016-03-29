##
# Copyright 2009-2015 Ghent University
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
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM, MANDATORY, BUILD
from easybuild.tools.build_log import EasyBuildError
import easybuild.tools.environment as env
from easybuild.tools.run import run_cmd
from easybuild.tools.modules import get_software_root, get_software_version
import easybuild.tools.toolchain as toolchain


class EB_VMD(ConfigureMake):
    """Easyblock for building and installing VMD"""

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to ConfigureMake."""
        extra_vars = dict(ConfigureMake.extra_options(extra_vars))
        extra_vars.update({
            'actc_ver': ["1.1", "Version of the ACTC library.", CUSTOM],
        })
        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        super(EB_VMD, self).__init__(*args, **kwargs)
        self.already_extracted = False

    def prepare_step(self):
        """
        Pre-configure step.
        """
        super(EB_VMD, self).prepare_step()

        # Build shipped plugins as part of prepare_step

        tclroot = get_software_root('Tcl')
        if not tclroot:
            raise EasyBuildError("Tcl is required to build VMD")

        netcdfroot = get_software_root('netCDF')
        if not netcdfroot:
            raise EasyBuildError("netCDF is required to build VMD")

        env.setvar('TCLLIB', '-F"%s"' % os.path.join(tclroot, 'lib'))
        env.setvar('TCLINC', '-I"%s"' % os.path.join(tclroot, 'include'))

        vmddir = os.path.join(self.builddir, "%s-%s" % (self.name.lower(), self.version))
        plugindir = os.path.join(vmddir, 'plugins')

        os.mkdir(plugindir)
        env.setvar('PLUGINDIR', plugindir)

        self.log.info("Generating VMD plugins in %s" % plugindir)
        cmd = 'make LINUXAMD64 TCLLIB="%s" TCLINC="%s" && make distrib' % (os.getenv('TCLLIB'),
                                                                           os.getenv('TCLINC'))
        run_cmd(cmd, log_all=True, simple=False)

        # prepare for configure: change to vmd dir
        try:
            os.chdir(vmddir)
            self.log.debug("Changed to %s directory %s" % (self.name, vmddir))
        except OSError, err:
            raise EasyBuildError("Can't change to %s directory %s: %s", self.name, vmddir, err)

    def configure_step(self):

        tclroot = get_software_root('Tcl')
        if not tclroot:
            raise EasyBuildError("Tcl is required to build VMD")
        env.setvar('TCL_INCLUDE_DIR', os.path.join(tclroot, 'include'))
        env.setvar('TCL_LIBRARY_DIR', os.path.join(tclroot, 'lib'))

        tkroot = get_software_root('Tk')
        if not tkroot:
            raise EasyBuildError("Tk is required to build VMD")
        env.setvar('TK_INCLUDE_DIR', os.path.join(tkroot, 'include'))
        env.setvar('TK_LIBRARY_DIR', os.path.join(tkroot, 'lib'))

        pythonroot = get_software_root('Python')
        if not pythonroot:
            raise EasyBuildError("Python is required to build VMD")

        # not so nice...
        env.setvar('PYTHON_INCLUDE_DIR', os.path.join(pythonroot, 'include/python2.7'))
        python_libdir = os.path.join(pythonroot, 'lib/python2.7')
        env.setvar('PYTHON_LIBRARY_DIR', python_libdir)
        env.setvar('NUMPY_INCLUDE_DIR', os.path.join(python_libdir,
                                                     'site-packages/numpy/core/include/numpy'))

        fltk = get_software_root('FLTK')
        if not fltk:
            raise EasyBuildError("FLTK is required to build VMD")

        mesa = get_software_root('Mesa')
        if not mesa:
            raise EasyBuildError("Mesa is required to build VMD")

        cuda = get_software_root('CUDA')
        if cuda:
            self.log.info("Building with CUDA %s support" % get_software_version('CUDA'))
            optix = get_software_root('OptiX')
            if optix:
                self.log.info("Building with Nvidia OptiX %s support" % get_software_version('OptiX'))
            else:
                self.log.warn("Not building with Nvidia OptiX support!")
        else:
            if 'CUDA' in self.cfg['configopts'].split():
                raise EasyBuildError("CUDA defined in configopts but not loaded!")
            else:
                self.log.warn("Not building with CUDA nor OptiX support!")

        return super(EB_VMD, self).configure_step()

    def build_step(self):

        vmddir = os.path.join(self.builddir, "%s-%s" % (self.name.lower(), self.version))
        vmdlibdir = os.path.join(vmddir, 'lib')
        vmdsrcdir = os.path.join(vmddir, 'src')

        # actc extracts to "actc-1.1"
        actc_ver = self.cfg['actc_ver']
        actcdir = os.path.join(self.builddir, "actc-%s" % actc_ver)
        try:
            os.chdir(actcdir)
        except OSError, err:
            raise EasyBuildError("Could not chdir to {0}: {1}".format(actcdir, err))

        actclibdir = os.path.join(vmdlibdir, 'actc')
        shutil.rmtree(actclibdir, ignore_errors=True)
        shutil.copytree(actcdir, actclibdir)

        try:
            os.chdir(actclibdir)
            self.log.debug("Changed to actc directory %s" % actclibdir)
        except OSError, err:
            raise EasyBuildError("Can't change to actc directory %s: %s", actclibdir, err)

        cmd = 'make'
        run_cmd(cmd, log_all=True, simple=False)

        # build VMD: change to src dir
        try:
            os.chdir(vmdsrcdir)
            self.log.debug("Changed to %s src directory %s" % (self.name, vmdsrcdir))
        except OSError, err:
            raise EasyBuildError("Can't change to %s src directory %s: %s", self.name, vmdsrcdir, err)

        super(EB_VMD, self).build_step()

    def test_step(self):
        pass

    def sanity_check_step(self):
        """Custom sanity check for VMD."""

        custom_paths = {
                        'files': ['bin/vmd'],
                        'dirs': ['bin'],
                       }

        super(EB_VMD, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):

        guesses = super(EB_VMD, self).make_module_req_guess()

        guesses.update({
            'PATH': ['bin'],
        })

        return guesses

    def make_module_extra(self):
        """Add module entries specific to VMD"""
        txt = super(EB_VMD, self).make_module_extra()
        txt += self.module_generator.load_module("CUDA/%s" % get_software_version("CUDA"))
        return txt
