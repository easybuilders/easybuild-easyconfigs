##
# Copyright 2009-2013 Ghent University
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
EasyBuild support for building and installing R packages, implemented as an easyblock

@authors: Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Jens Timmerman, Toon Willems (Ghent University)
"""
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.extension import Extension
from easybuild.tools.filetools import run_cmd, parse_log_for_error


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


class RPackage(EasyBlock, Extension):
    """
    Install an R package as a separate module, or as an extension.
    """
    def __init__(self, arg1, *args, **kwargs):
        """Initliaze RPackage-specific class variables."""

        if isinstance(arg1, EasyBlock):
            Extension.__init__(self, arg1, *args, **kwargs)
        else:
            EasyBlock.__init__(self, arg1, *args, **kwargs)
        self.configurevars = []
        self.configureargs = []

    def make_r_cmd(self):
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

        r_cmd = """
        options(repos=c(CRAN="http://www.freestatistics.org/cran"))
        %s
        %s
        install.packages("%s",dependencies = FALSE %s%s)
        """ % (confvarslist, confargslist, self.name, confvarsstr, confargsstr)
        cmd = "R -q --no-save"

        self.log.debug("make_r_cmd returns %s with input %s" % (cmd, r_cmd))

        return (cmd, r_cmd)

    def make_cmdline_cmd(self, prefix=None):
        """Create a command line to install an R package."""
        confvars = ""
        if self.configurevars:
            confvars = make_R_install_option("--configure-vars", self.configurevars, cmdline=True)
        confargs = ""
        if self.configureargs:
            confargs = make_R_install_option("--configure-args", self.configureargs, cmdline=True)

        if prefix:
            prefix = '--library=%s' % prefix
        else:
            prefix = ''

        cmd = "R CMD INSTALL %s %s %s %s" % (self.src, confargs, confvars, prefix)
        self.log.debug("make_cmdline_cmd returns %s" % cmd)

        return cmd, None

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
            self.log.error("Errors detected during installation of R package %s!" % self.name)
        else:
            self.log.debug("R package %s installed succesfully" % self.name)

    def install_step(self):
        """Install procedure for R packages."""

        cmd = self.make_cmdline_cmd(prefix=self.installdir)
        self.install_R_package(cmd)

    def run(self):
        """Install R package as an extension."""
        if self.src:
            self.log.debug("Installing R package %s version %s." % (self.name, self.version))
            cmd, stdin = self.make_cmdline_cmd()
        else:
            self.log.debug("Installing most recent version of R package %s (source not found)." % self.name)
            cmd, stdin = self.make_r_cmd()

        self.install_R_package(cmd, inp=stdin)

    def sanity_check_step(self, custom_paths=None, custom_commands=None):
        """
        Custom sanity check for Python packages
        """
        if not custom_paths:
            custom_paths = {
                            'files': [],
                            'dirs': ["%s/%s" % ("foo", self.name.lower())]
                           }

        EasyBlock.sanity_check_step(self, custom_paths=custom_paths, custom_commands=custom_commands)

    def make_module_extra(self):
        """Add install path to R_LIBS"""

        txt = EasyBlock.make_module_extra(self)

        txt += self.moduleGenerator.prepend_path("R_LIBS", self.installdir)

        return txt
