##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
# Copyright 2012 Toon Willems
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
Generic EasyBuild support for software extensions (e.g. Python packages).
The Extension class should serve as a base class for all extensions.
"""

from easybuild.tools.filetools import run_cmd

class Extension(object):
    """
    Support for installing extensions.
    """
    def __init__(self, mself, ext, exts_installdeps):
        """
        mself has the logger
        """
        self.master = mself
        self.log = self.master.log
        self.cfg = self.master.cfg
        self.ext = ext
        self.exts_installdeps = exts_installdeps

        if not 'name' in self.ext:
            self.log.error("")

        self.name = self.ext.get('name', None)
        self.version = self.ext.get('version', None)
        self.src = self.ext.get('src', None)
        self.patches = self.ext.get('patches', None)

    def prerun(self):
        """
        Stuff to do before installing a extension.
        """
        pass

    def run(self):
        """
        Actual installation of a extension.
        """
        pass

    def postrun(self):
        """
        Stuff to do after installing a extension.
        """
        pass

    @property
    def toolchain(self):
        """
        Toolchain used to build this extension.
        """
        return self.master.toolchain

    def sanity_check_step(self):
        """
        sanity check to run after installing
        """
        try:
            cmd, inp = self.master.cfg['exts_filter']
        except:
            self.log.debug("no exts_filter setting found, skipping sanitycheck")
            return

        if self.name in self.master.cfg['exts_modulenames']:
            modname = self.master.cfg['exts_modulenames'][self.name]
        else:
            modname = self.name
        template = {'name': modname,
                    'version': self.version,
                    'src': self.src
                   }
        cmd = cmd % template

        if inp:
            stdin = inp % template
            # set log_ok to False so we can catch the error instead of run_cmd
            (output, ec) = run_cmd(cmd, log_ok=False, simple=False, inp=stdin, regexp=False)
        else:
            (output, ec) = run_cmd(cmd, log_ok=False, simple=False, regexp=False)
        if ec:
            self.log.warn("Extension: %s failed to install! (output: %s)" % (self.name, output))
            return False
        else:
            return True
