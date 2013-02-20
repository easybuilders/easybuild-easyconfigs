##
# Copyright 2012-2013 Ghent University
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
EasyBuild support for UFC, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.cmakepythonpackage import CMakePythonPackage
from easybuild.tools.modules import get_software_root, get_software_version


class EB_UFC(CMakePythonPackage):
    """Support for building UFC."""

    def __init__(self, *args, **kwargs):
        """Custom initialization for UFC: set correct module name."""
        super(EB_UFC, self).__init__(*args, **kwargs)

        self.options.update({'modulename': 'ufc_utils'})

    def configure_step(self):
        """Set some extra environment variables before configuring."""

        # make sure that required dependencies are loaded
        deps = ['Boost', 'Python', 'SWIG']
        depsdict = {}
        for dep in deps:
            deproot = get_software_root(dep)
            if not deproot:
                self.log.error("%s module not loaded?" % dep)
            else:
                depsdict.update({dep:deproot})

        # SWIG version more recent than 2.0.4 have a regression
        # which causes problems with e.g. DOLFIN if UFC was built with it
        # fixed in 2.0.7? see https://bugs.launchpad.net/dolfin/+bug/996398
        if LooseVersion(get_software_version('SWIG')) > '2.0.4':
            self.log.error("Using bad version of SWIG, expecting swig <= 2.0.4." \
                           " See https://bugs.launchpad.net/dolfin/+bug/996398")

        self.pyver = ".".join(get_software_version('Python').split(".")[:-1])

        self.cfg.update('configopts', "-DBoost_DIR=%s" % depsdict['Boost'])
        self.cfg.update('configopts', "-DBOOST_INCLUDEDIR=%s/include" % depsdict['Boost'])
        self.cfg.update('configopts', "-DBoost_DEBUG=ON -DBOOST_ROOT=%s" % depsdict['Boost'])

        self.cfg.update('configopts', '-DUFC_ENABLE_PYTHON:BOOL=ON')
        self.cfg.update('configopts', '-DSWIG_FOUND:BOOL=ON')
        self.cfg.update('configopts', '-DPYTHON_LIBRARY=%s/lib/libpython%s.so' % (depsdict['Python'],
                                                                                 self.pyver))
        self.cfg.update('configopts', '-DPYTHON_INCLUDE_PATH=%s/include/python%s' % (depsdict['Python'],
                                                                                    self.pyver))

        super(EB_UFC, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for UFC."""

        custom_paths = {
                        'files': ['include/ufc.h'],
                        'dirs': ['lib/python%s/site-packages/%s/' % (self.pyver, x) for x in ['ufc', 'ufc_utils']],
                       }

        super(EB_UFC, self).sanity_check_step(custom_paths=custom_paths)
