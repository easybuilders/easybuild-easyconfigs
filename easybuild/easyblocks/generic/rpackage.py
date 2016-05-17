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
EasyBuild support for building and installing R packages, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
@author: Balazs Hajgato (Vrije Universiteit Brussel)
"""
import os
import shutil

from easybuild.easyblocks.r import EXTS_FILTER_R_PACKAGES, EB_R
from easybuild.framework.extensioneasyblock import ExtensionEasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd, parse_log_for_error


def make_R_install_option(opt, values, cmdline=False):
    """
    Make option list for install.packages, to specify in R environment.
    """
    txt = ""
    if values:
        if cmdline:
            txt = " --%s=\"%s" % (opt, values[0])
        else:
            txt = "%s=c(\"%s" % (opt, values[0])
        for i in values[1:]:
            txt += " %s" % i
        if cmdline:
            txt += "\""
        else:
            txt += "\")"
    return txt


class RPackage(ExtensionEasyBlock):
    """
    Install an R package as a separate module, or as an extension.
    """

    def __init__(self, *args, **kwargs):
        """Initliaze RPackage-specific class variables."""

        super(RPackage, self).__init__(*args, **kwargs)

        self.configurevars = []
        self.configureargs = []
        self.ext_src = None

    def make_r_cmd(self, prefix=None):
        """Create a command to run in R to install an R package."""
        confvars = "confvars"
        confargs = "confargs"
        confvarslist = make_R_install_option(confvars, self.configurevars)
        confargslist = make_R_install_option(confargs, self.configureargs)
        confvarsstr = ""
        if confvarslist:
            confvarslist = confvarslist + "; names(%s)=\"%s\"" % (confvars, self.name)
            confvarsstr = ", configure.vars=%s" % confvars
        confargsstr = ""
        if confargslist:
            confargslist = confargslist + "; names(%s)=\"%s\"" % (confargs, self.name)
            confargsstr = ", configure.args=%s" % confargs

        if prefix:
            prefix = '"%s", ' % prefix
        else:
            prefix = ''

        r_cmd = """
        options(repos=c(CRAN="http://www.freestatistics.org/cran"))
        %s
        %s
        install.packages("%s", %s dependencies = FALSE %s%s)
        """ % (confvarslist, confargslist, self.name, prefix, confvarsstr, confargsstr)
        cmd = "R -q --no-save"

        self.log.debug("make_r_cmd returns %s with input %s" % (cmd, r_cmd))

        return (cmd, r_cmd)

    def make_cmdline_cmd(self, prefix=None):
        """Create a command line to install an R package."""
        confvars = ""
        if self.configurevars:
            confvars = make_R_install_option("configure-vars", self.configurevars, cmdline=True)
        confargs = ""
        if self.configureargs:
            confargs = make_R_install_option("configure-args", self.configureargs, cmdline=True)

        if prefix:
            prefix = '--library=%s' % prefix
        else:
            prefix = ''

        if self.patches:
            loc = self.ext_dir
        else:
            loc = self.ext_src
        cmd = "R CMD INSTALL %s %s %s %s --no-clean-on-error" % (loc, confargs, confvars, prefix)

        self.log.debug("make_cmdline_cmd returns %s" % cmd)
        return cmd, None

    def extract_step(self):
        """Source should not be extracted."""
        pass
        if len(self.src) > 1:
            raise EasyBuildError("Don't know how to handle R packages with multiple sources.'")
        else:
            try:
                shutil.copy2(self.src[0]['path'], self.builddir)
            except OSError, err:
                raise EasyBuildError("Failed to copy source to build dir: %s", err)
            self.ext_src = self.src[0]['name']

            # set final path since it can't be determined from unpacked sources (used for guessing start_dir)
            self.src[0]['finalpath'] = self.builddir

    def configure_step(self):
        """No configuration for installing R packages."""
        pass

    def build_step(self):
        """No separate build step for R packages."""
        pass

    def install_R_package(self, cmd, inp=None):
        """Install R package as specified, and check for errors."""

        cmdttdouterr, _ = run_cmd(cmd, log_all=True, simple=False, inp=inp, regexp=False)

        cmderrors = parse_log_for_error(cmdttdouterr, regExp="^ERROR:")
        if cmderrors:
            cmd = "R -q --no-save"
            stdin = """
            remove.library(%s)
            """ % self.name
            # remove package if errors were detected
            # it's possible that some of the dependencies failed, but the package itself was installed
            run_cmd(cmd, log_all=False, log_ok=False, simple=False, inp=stdin, regexp=False)
            raise EasyBuildError("Errors detected during installation of R package %s!", self.name)
        else:
            self.log.debug("R package %s installed succesfully" % self.name)

    def install_step(self):
        """Install procedure for R packages."""

        cmd, stdin = self.make_cmdline_cmd(prefix=self.installdir)
        self.install_R_package(cmd, inp=stdin)

    def run(self):
        """Install R package as an extension."""

        # determine location
        if isinstance(self.master, EB_R):
            # extension is being installed as part of an R installation/module
            (out, _) = run_cmd("R RHOME", log_all=True, simple=False)
            rhome = out.strip()
            lib_install_prefix = os.path.join(rhome, 'library')
        else:
            # extension is being installed in a separate installation prefix
            lib_install_prefix = self.installdir

        if self.patches:
            super(RPackage, self).run(unpack_src=True)
        else:
            super(RPackage, self).run()

        if self.src:
            self.ext_src = self.src
            self.log.debug("Installing R package %s version %s." % (self.name, self.version))
            cmd, stdin = self.make_cmdline_cmd(prefix=lib_install_prefix)
        else:
            self.log.debug("Installing most recent version of R package %s (source not found)." % self.name)
            cmd, stdin = self.make_r_cmd(prefix=lib_install_prefix)

        self.install_R_package(cmd, inp=stdin)

    def sanity_check_step(self, *args, **kwargs):
        """
        Custom sanity check for R packages
        """
        return super(RPackage, self).sanity_check_step(EXTS_FILTER_R_PACKAGES, *args, **kwargs)

    def make_module_extra(self):
        """Add install path to R_LIBS"""
        extra = self.module_generator.prepend_paths("R_LIBS", [''])  # prepend R_LIBS with install path
        return super(RPackage, self).make_module_extra(extra)
