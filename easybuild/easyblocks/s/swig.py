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
EasyBuild support for SWIG, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_SWIG(ConfigureMake):
    """Support for building SWIG."""

    def configure_step(self):
        """Set some extra environment variables before configuring."""

        # disable everything by default
        for x in ["r", "clisp", "allegrocl", "lua", "csharp", "chicken", "pike ",
                  "ocaml","php", "ruby", "mzscheme", "guile", "gcj", "java",
                  "octave", "perl5", "python3", "tcl"]:
            self.cfg.update('configopts', "--without-%s" % x)

        python = get_software_root('Python')
        if python:
            self.cfg.update('configopts', "--with-python=%s/bin/python" % python)
        else:
            raise EasyBuildError("Python module not loaded?")

        super(EB_SWIG, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for SWIG."""

        custom_paths = {
                        'files':["bin/ccache-swig","bin/swig"],
                        'dirs':[]
                       }

        super(EB_SWIG, self).sanity_check_step(custom_paths=custom_paths)
