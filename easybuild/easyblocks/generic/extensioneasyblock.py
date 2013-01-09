##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing extensions as actual extensions or as stand-alone modules,
implemented as an easyblock

@authors: Kenneth Hoste (Ghent University)
"""
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.framework.extension import Extension


class ExtensionEasyBlock(EasyBlock, Extension):
    """
    Install an extension as a separate module, or as an extension.
    """

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to ExtensionEasyBlock."""

        # using [] as default value is a bad idea, so we handle it this way
        if extra_vars is None:
            extra_vars = []

        extra_vars.extend([
                           ('options', [{}, "Dictionary with extension options.", CUSTOM]),
                          ])
        return EasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initliaze either as EasyBlock or as Extension."""

        if isinstance(args[0], EasyBlock):
            Extension.__init__(self, *args, **kwargs)
            # name and version properties of EasyBlock are used, so make sure name and version are correct
            self.cfg['name'] = self.ext.get('name', None)
            self.cfg['version'] = self.ext.get('version', None)
        else:
            EasyBlock.__init__(self, *args, **kwargs)
            self.options = self.cfg['options']  # we need this for Extension.sanity_check_step

        self.configurevars = []
        self.configureargs = []

    # deriving classes should implement the following functions:
    # required EasyBlock functions:
    # * configure_step
    # * build_step
    # * install_step
    # required Extension functions
    # * run

    def sanity_check_step(self, exts_filter):
        """
        Custom sanity check for extensions, whether installed as stand-alone module or not
        """
        if not self.cfg['exts_filter']:
            self.cfg['exts_filter'] = exts_filter

        return Extension.sanity_check_step(self)

    def make_module_extra(self, extra):
        """Add custom entries to module."""

        txt = EasyBlock.make_module_extra(self)
        txt += extra
        return txt
