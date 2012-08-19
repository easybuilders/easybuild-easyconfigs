# Copyright 2012 Kenneth Hoste
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
"""
from easybuild.framework.application import Application
from easybuild.tools.modules import get_software_root


class EB_SWIG(Application):
    """Support for building SWIG."""

    def configure(self):
        """Set some extra environment variables before configuring."""

        # disable everything by default
        for x in ["r", "clisp", "allegrocl", "lua", "csharp", "chicken", "pike ",
                  "ocaml","php", "ruby", "mzscheme", "guile", "gcj", "java",
                  "octave", "perl5", "python3", "tcl"]:
            self.updatecfg('configopts', "--without-%s" % x)

        python = get_software_root('Python')
        if python:
            self.updatecfg('configopts', "--with-python=%s/bin/python" % python)
        else:
            self.log.error("Python module not loaded?")

        Application.configure(self)

    def sanitycheck(self):
        """Custom sanity check for SWIG."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files':["bin/ccache-swig","bin/swig"],
                                             'dirs':[]
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
