##
# Copyright 2009-2012 Kenneth Hoste
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
EasyBuild support for building and installing FSL, implemented as an easyblock
"""

import difflib
import os
import re
import shutil

import easybuild.tools.environment as env
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd


class FSL(Application):
    """Support for building and installing FSL."""

    def __init__(self,*args,**kwargs):
        """Specify building in install dir, initialize custom variables."""

        Application.__init__(self, *args, **kwargs)

        self.build_in_installdir = True

        self.fsldir = None

    def configure(self):
        """Configure FSL build: set FSLDIR env var."""

        self.fsldir = self.getcfg('startfrom')
        env.set('FSLDIR', self.fsldir)

        # determine FSL machine type
        cmd = ". %s/etc/fslconf/fsl.sh && echo $FSLMACHTYPE" % self.fsldir
        (out, _) = run_cmd(cmd, log_all=True, simple=False)
        fslmachtype = out.strip()
        self.log.debug("FSL machine type: %s" % fslmachtype)

        # prepare config
        # either using matching config, or copy closest match
        cfgdir = os.path.join(self.fsldir, "config")
        try:
            cfgs = os.listdir(cfgdir)
            best_cfg = difflib.get_close_matches(fslmachtype, cfgs)[0]

            self.log.debug("Best matching config dir for %s is %s" % (fslmachtype, best_cfg))

            if fslmachtype != best_cfg:
                srcdir = os.path.join(cfgdir, best_cfg)
                tgtdir = os.path.join(cfgdir, fslmachtype)
                shutil.copytree(srcdir, tgtdir)
                self.log.debug("Copied %s to %s" % (srcdir, tgtdir))
        except OSError, err:
            self.log.error("Failed to copy closest matching config dir: %s" % err)

    def make(self):
        """Build FSL using supplied script."""

        cmd = ". %s/etc/fslconf/fsl.sh && ./build" % self.fsldir
        run_cmd(cmd, log_all=True, simple=True)

        # check build.log file for success
        buildlog = os.path.join(self.installdir, "fsl", "build.log")
        f = open(buildlog, "r")
        txt = f.read()
        f.close()

        error_regexp = re.compile("ERROR in BUILD")
        if error_regexp.search(txt):
            self.log.error("Error detected in build log %s." % buildlog)

    def make_install(self):
        """Building was performed in install dir, no explicit install step required."""
        pass

    def make_module_req_guess(self):
        """Set correct PATH and LD_LIBRARY_PATH variables."""

        guesses = Application.make_module_req_guess(self)

        guesses.update({
            'PATH': ["fsl/bin"],
            'LD_LIBRARY_PATH': ["fsl/lib"],
        })

        return guesses

    def make_module_extra(self):
        """Add setting of FSLDIR in module."""

        txt = Application.make_module_extra(self)

        txt += self.moduleGenerator.setEnvironment("FSLDIR", "$root/fsl")

        return txt

    def sanitycheck(self):
        """Custom sanity check for FSL"""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {'files':[],
                                             'dirs':["fsl/%s" % x for x in ["bin", "data", "etc", "extras", "include", "lib"]]
                                            })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
