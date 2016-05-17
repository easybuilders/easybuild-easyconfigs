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
EasyBuild support for building and installing FSL, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""

import difflib
import os
import re
import shutil

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_FSL(EasyBlock):
    """Support for building and installing FSL."""

    def __init__(self,*args,**kwargs):
        """Specify building in install dir, initialize custom variables."""

        super(EB_FSL, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

        self.fsldir = None

    def configure_step(self):
        """Configure FSL build: set FSLDIR env var."""

        self.fsldir = self.cfg['start_dir']
        env.setvar('FSLDIR', self.fsldir)

        # determine FSL machine type
        cmd = ". %s/etc/fslconf/fslmachtype.sh" % self.fsldir
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
            raise EasyBuildError("Failed to copy closest matching config dir: %s", err)

    def build_step(self):
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
            raise EasyBuildError("Error detected in build log %s.", buildlog)

    def install_step(self):
        """Building was performed in install dir, no explicit install step required."""
        pass

    def make_module_req_guess(self):
        """Set correct PATH and LD_LIBRARY_PATH variables."""

        guesses = super(EB_FSL, self).make_module_req_guess()

        guesses.update({
            'PATH': ["fsl/bin"],
            'LD_LIBRARY_PATH': ["fsl/lib"],
        })

        return guesses

    def make_module_extra(self):
        """Add setting of FSLDIR in module."""

        txt = super(EB_FSL, self).make_module_extra()

        txt += self.module_generator.set_environment("FSLDIR", os.path.join(self.installdir, 'fsl'))

        return txt

    def sanity_check_step(self):
        """Custom sanity check for FSL"""

        custom_paths =  {'files':[],
                         'dirs':["fsl/%s" % x for x in ["bin", "data", "etc", "extras", "include", "lib"]]
                        }

        super(EB_FSL, self).sanity_check_step(custom_paths=custom_paths)
