##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
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
EasyBuild support for R packages, implemented as an easyblock
"""
from easybuild.framework.extension import Extension
from easybuild.tools.filetools import run_cmd, parse_log_for_error
from easybuild.tools.modules import get_software_root


def make_install_option(opt, values):
    """
    Make option list for install.packages, to specify in R environment.
    """
    out = ""
    if values:
        out = "%s=c(\"%s" % (opt, values[0])
        for i in values[1:]:
            out += " %s" % i
        out += "\")"
    return out


def make_install_option_cmdline(opt, values):
    """
    Make option list for "R CMD INSTALL", to specify on command line.
    """
    out = ""
    if values:
        out = " --%s=\"%s" % (opt, values[0])
        for i in values[1:]:
            out += " %s" % i
        out += "\""
    return out


class EB_RExtension(Extension):
    """
    Install a R extension with this EasyBlock Extension
    """
    def __init__(self, mself, pkg):
        Extension.__init__(self, mself, pkg)
        self.log.debug("using EB_RPackage")
        self.configurevars = []
        self.configureargs = []

    def make_r_cmd(self):
        """Create a command to run in R to install this extension"""
        confvars = "confvars"
        confargs = "confargs"
        confvarslist = make_install_option(confvars, self.configurevars)
        confargslist = make_install_option(confargs, self.configureargs)
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

        confvars = ""
        if self.configurevars:
            confvars = "--configure-vars='%s'" % ' '.join(self.configurevars)
        confargs = ""
        if self.configureargs:
            confargs = "--configure-args='%s'" % ' '.join(self.configureargs)

        cmd = "R CMD INSTALL %s %s %s" % (self.src, confargs, confvars)
        self.log.debug("make_cmdline_cmd returns %s" % cmd)

        return cmd, None

    def run(self):
        if self.src:
            self.log.debug("Installing package %s version %s." % (self.name, self.version))
            cmd, stdin = self.make_cmdline_cmd()
        else:
            self.log.debug("Installing most recent version of package %s (source not found)." % self.name)
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
            self.log.error("Errors detected during installation of package %s!" % self.name)
        else:
            self.log.debug("Package %s installed succesfully" % self.name)


class EB_Bioconductor(EB_RExtension):
    """
    The Bioconductor package extends DefaultRPackage to use a different source
    And using the biocLite package to do the installation.
    """
    def make_cmdline_cmd(self):
        self.log.error("bioconductor.run: Don't know how to install a specific version of a bioconductor package.")

    def make_r_cmd(self):
        name = self.ext['name']
        self.log.debug("Installing bioconductor package %s." % name)
        bl_name = "\"%s\"" % name

        r_cmd = """
        source("http://bioconductor.org/biocLite.R")
        biocLite(%s)
        """ % (bl_name)
        cmd = "R -q --no-save"

        return cmd, r_cmd

## special cases of bioconductor packages
# handled by class aliases
EB_BSgenome = EB_GenomeGraphs = EB_ShortRead = EB_Bioconductor
EB_Biobase = EB_IRanges = EB_AnnotationDbi = EB_Bioconductor
# exonmap doesn't seem to be available trought biocLite anymore...
EB_exonmap = EB_Bioconductor


class EB_Rserve(EB_RExtension):
    """Install Rserve as an R extension"""
    def run(self):
        self.configurevars = ['LIBS="$LIBS -lpthread"']
        EB_RExtension.run(self)


# TODO: should be in it's own module, since it has a non rpackage dependency
class EB_rsprng(EB_RExtension):
    """Install rsprng as an R extension"""
    def run(self):
        tc = self.toolchain
        self.log.debug("Setting configure args for %s" % self.name)
        self.configurevars = ['LIBS=\\"%s %s\\"' % (tc.get_variable("LIBS"), tc.get_variable("LDFLAGS"))]
        self.configureargs = ["--with-sprng=%s" % get_software_root("SPRNG")]
        EB_RExtension.run(self)


class EB_rgdal(EB_RExtension):
    """Install rgdal as an R extension"""
    def run(self):
        self.log.debug("Setting configure args for %s" % self.name)
        softrootproj = get_software_root("PROJ")
        self.configureargs = ["--with-proj-include=%s/include --with-proj-lib=%s/lib" % (softrootproj, softrootproj)]
        EB_RExtension.run(self)


class EB_Rmpi(EB_RExtension):
    from easybuild.tools import toolchain
    """Install Rmpi as an R extension"""
    MPI_TYPES = {
        toolchain.MPI_TYPE_OPENMPI: "OPENMPI",
        toolchain.MPI_TYPE_MPICH: "MPICH",
        # No support for LAM yet toolchain.MPI_TYPE_LAM: "LAM",
    }

    def run(self):
        """Do the installation"""
        self.log.debug("Setting configure args for Rmpi")
        self.configureargs = [
            "--with-Rmpi-include=%s" % self.toolchain.get_variable('MPI_INC_DIR'),
            "--with-Rmpi-libpath=%s" % self.toolchain.get_variable('MPI_LIB_DIR'),
            "--with-mpi=%s" % self.toolchain.get_software_root(self.toolchain.MPI_MODULE_NAME)[0],
            "--with-Rmpi-type=%s" % EB_Rmpi.MPI_TYPES[self.toolchain.MPI_TYPE],
        ]
        EB_RExtension.run(self)  # it might be needed to get the r cmd and run it with mympirun...



#class EB_rJava(EB_Rpackage):
#
#    def run(self):
#
#        if not os.getenv('EBROOTJAVA'):
#            self.log.error("Java module not loaded, required as dependency for %s." % self.name())
#
#        java_home = os.getenv('JAVA_HOME')
#        if not java_home.endswith("jre"):
#            new_java_home = os.path.join(java_home, "jre")
#            os.putenv("JAVA_HOME", new_java_home)
#        else:
#            new_java_home = java_home
#
#        path = os.getenv('PATH')
#        os.putenv("PATH", "%s:%s/bin" % (path, new_java_home))
#
#        os.putenv("_JAVA_OPTIONS", "-Xmx512M")
#
#        txt = '# stuff required by rJava R package\n'
#        txt += 'setenv JAVA_HOME %s\n' % new_java_home
#        txt += 'setenv _JAVA_OPTIONS -Xmx512M\n'
#        txt += 'prepend-path PATH %s/bin\n' % new_java_home
#
#        DefaultRpackage.run(self)
#
#        return txt
