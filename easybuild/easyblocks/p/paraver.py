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
# https://github.com/easybuilders/easybuild
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
EasyBuild support for building and installing Paraver, implemented as an easyblock

@author Kenneth Hoste (Ghent University)
@author Markus Geimer (Juelich Supercomputing Centre)
@author Bernd Mohr (Juelich Supercomputing Centre)
"""
import glob
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError, print_msg
from easybuild.tools.modules import get_software_libdir, get_software_root


class EB_Paraver(ConfigureMake):
    """Support for building/installing Paraver."""

    def run_all_steps(self, *args, **kwargs):
        """
        Put configure/build/install options in place for the 3 different components of Paraver.
        Each component lives in a separate subdirectory.
        """
        self.components = ['ptools_common_files', 'paraver-kernel', 'wxparaver']
        self.current_component = 0  # index is list above

        # initiate configopts with empty list
        self.cfg['configopts'] = []

        # first phase: build and install ptools
        # no specific configure options for the ptools component (but configopts list element must be there)
        self.cfg.update('configopts', [''])
        
        # second phase: build and install paraver-kernel
        self.cfg.update('configopts', ["--with-boost=%(boost)s --with-ptools-common-files=%(installdir)s"])
        
        # third phase: build and install wxparaver
        wxparaver_configopts = "--with-boost=%(boost)s --with-wxpropgrid=%(wxpropgrid)s --with-paraver=%(installdir)s"
        self.cfg.update('configopts', [wxparaver_configopts])

        return super(EB_Paraver, self).run_all_steps(*args, **kwargs)

    def prepare_step(self, *args, **kwargs):
        """Custom prepare step for Paraver: check required dependencies and collect information on them."""
        super(EB_Paraver, self).prepare_step(*args, **kwargs)

        # determine value to pass to --with-wxpropgrid (library name)
        self.wxpropgrid = None
        wxpropertygrid_root = get_software_root('wxPropertyGrid')
        if wxpropertygrid_root:
            wxpropertygrid_libdir = os.path.join(wxpropertygrid_root, get_software_libdir('wxPropertyGrid'))
            libname_pattern = 'libwxcode_*_propgrid-*.so'
            wxpropgrid_libs = glob.glob(os.path.join(wxpropertygrid_libdir, libname_pattern))
            if len(wxpropgrid_libs) == 1:
                # exclude the 'lib' prefix and '.so' suffix to determine value to be passed to --with-wxpropgrid
                self.wxpropgrid = os.path.basename(wxpropgrid_libs[0])[3:-3]
            else:
                tup = (libname_pattern, wxpropertygrid_libdir, wxpropgrid_libs)
                raise EasyBuildError("Expected to find exactly one %s library in %s, found %s" % tup)

    def configure_step(self):
        """Custom configuration procedure for Paraver: template configuration options before using them."""

        component = self.components[self.current_component]
        try:
            os.chdir(component)
        except OSError, err:
            raise EasyBuildError("Failed to move to %s: %s" % (component, err))

        self.log.info("Customized start directory for component %s: %s", component, os.getcwd())

        print_msg("starting with component %s" % component, log=self.log)

        # check for required Boost dependency
        boost = get_software_root('Boost')
        if not boost:
            raise EasyBuildError("Boost is not available as a dependency")

        if not self.wxpropgrid:
            raise EasyBuildError("wxPropertyGrid is not available as a dependency")

        self.cfg['configopts'] = self.cfg['configopts'] % {
            'boost': boost,
            'installdir': self.installdir,
            'wxpropgrid': self.wxpropgrid,
        }
        super(EB_Paraver, self).configure_step()

    def install_step(self):
        """Custom installation procedure for Paraver: put symlink in place for library subdirectory."""
        super(EB_Paraver, self).install_step()

        # link lib to lib64 if needed
        # this is a workaround for an issue with libtool which sometimes creates lib64 rather than lib
        if self.components[self.current_component] == self.components[0]:
            lib64dir = os.path.join(self.installdir, 'lib64')
            libdir = os.path.join(self.installdir, 'lib')

            if os.path.exists(lib64dir):
                try:
                    self.log.debug("Symlinking %s to %s", lib64dir, libdir)
                    os.symlink(lib64dir, libdir)
                except OSError, err:
                    raise EasyBuildError("Symlinking lib64 to lib failed: %s" % err)

        self.current_component += 1

    def sanity_check_step(self):
        """Custom sanity check for Paraver."""
        custom_paths = {
            'files': ['bin/wxparaver', 'include/paraverconfig.h', 'lib/paraver-kernel/libparaver-kernel.a'],
            'dirs': [],
        }
        super(EB_Paraver, self).sanity_check_step(custom_paths=custom_paths)
