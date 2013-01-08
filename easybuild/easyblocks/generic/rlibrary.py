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
EasyBuild support for building and installing R libraries, implemented as an easyblock

@authors: Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Jens Timmerman, Toon Willems (Ghent University)
"""
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


class RLibrary(Extension):
    """
    Install an R extension with this EasyBlock Extension
    """
    def __init__(self, mself, pkg):
        """Initliaze RLibrary-specific class variables."""
        super(RLibrary, self).__init__(mself, pkg)
        self.configurevars = []
        self.configureargs = []

    def make_r_cmd(self):
        """Create a command to run in R to install an R library."""
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

    def make_cmdline_cmd(self):
        """Create a command line to install an R library."""
        confvars = ""
        if self.configurevars:
            confvars = make_R_install_option("--configure-vars", self.configurevars, cmdline=True)
        confargs = ""
        if self.configureargs:
            confargs = make_R_install_option("--configure-args", self.configureargs, cmdline=True)

        cmd = "R CMD INSTALL %s %s %s" % (self.src, confargs, confvars)
        self.log.debug("make_cmdline_cmd returns %s" % cmd)

        return cmd, None

    def run(self):
        """Install R library."""
        if self.src:
            self.log.debug("Installing R library %s version %s." % (self.name, self.version))
            cmd, stdin = self.make_cmdline_cmd()
        else:
            self.log.debug("Installing most recent version of R library %s (source not found)." % self.name)
            cmd, stdin = self.make_r_cmd()

        cmdttdouterr, _ = run_cmd(cmd, log_all=True, simple=False, inp=stdin, regexp=False)

        cmderrors = parse_log_for_error(cmdttdouterr, regExp="^ERROR:")
        if cmderrors:
            cmd = "R -q --no-save"
            stdin = """
            remove.library(%s)
            """ % self.name
            # remove library if errors were detected
            # it's possible that some of the dependencies failed, but the library itself was installed
            run_cmd(cmd, log_all=False, log_ok=False, simple=False, inp=stdin, regexp=False)
            self.log.error("Errors detected during installation of R library %s!" % self.name)
        else:
            self.log.debug("R library %s installed succesfully" % self.name)
