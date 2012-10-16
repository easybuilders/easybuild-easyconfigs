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
from easybuild.framework.application import ApplicationPackage
from easybuild.tools.filetools import run_cmd, parselogForError

def mkInstallOptionR(opt, xs):
    """
    Make option list for install.packages, to specify in R environment. 
    """
    s = ""
    if xs:
        s = "%s=c(\"%s" % (opt, xs[0])
        for x in xs[1:]:
            s += " %s" % x
        s += "\")"
    return s

def mkInstallOptionCmdLine(opt, xs):
    """
    Make option list for "R CMD INSTALL", to specify on command line.
    """
    s = ""
    if xs:
        s = " --%s=\"%s" % (opt, xs[0])
        for x in xs[1:]:
            s += " %s" % x
        s += "\""
    return s

class EB_RPackage(ApplicationPackage):
    def __init__(self, mself, pkg, pkginstalldeps):
        ApplicationPackage.__init__(self, mself, pkg, pkginstalldeps)
        self.log.debug("using EB_RPackage")
        self.configurevars = []
        self.configureargs = []

    def setconfigureargs(self, a):
        self.configureargs = a

    def setconfigurevars(self, a):
        self.configurevars = a

    def makeRCmd(self):
        confvars = "confvars"
        confargs = "confargs"
        confvarsList = mkInstallOptionR(confvars, self.configurevars)
        confargsList = mkInstallOptionR(confargs, self.configureargs)
        confvarsStr = ""
        if confvarsList:
            confvarsList = confvarsList + "; names(%s)=\"%s\"" % (confvars, self.name)
            confvarsStr = ", configure.vars=%s" % confvars
        confargsStr = ""
        if confargsList:
            confargsList = confargsList + "; names(%s)=\"%s\"" % (confargs, self.name)
            confargsStr = ", configure.args=%s" % confargs

        if self.pkginstalldeps:
            installdeps = "TRUE"
        else:
            installdeps = "FALSE"

        Rcmd = """
        options(repos=c(CRAN="http://www.freestatistics.org/cran"))
        %s
        %s
        install.packages("%s",dependencies = %s%s%s)
        """ % (confvarsList, confargsList, self.name, installdeps, confvarsStr, confargsStr)
        cmd = "R -q --no-save"

        self.log.debug("makeRCmd returns %s with input %s" % (cmd, Rcmd))

        return (cmd, Rcmd)

    def makeCmdLineCmd(self):

        confvars = ""
        if self.configurevars:
            confvars = "--configure-vars='%s'" % ' '.join(self.configurevars)
        confargs = ""
        if self.configureargs:
            confargs = "--configure-args='%s'" % ' '.join(self.configureargs)

        cmd = "R CMD INSTALL %s %s %s" % (self.src, confargs, confvars)
        self.log.debug("makeCmdLineCmd returns %s" % cmd)

        return cmd, None

    def run(self):
        if self.src:
            self.log.debug("Installing package %s version %s." % (self.name, self.version))
            cmd, stdin = self.makeCmdLineCmd()
        else:
            self.log.debug("Installing most recent version of package %s (source not found)." % self.name)
            cmd, stdin = self.makeRCmd()

        cmdttdouterr, _ = run_cmd(cmd, log_all=True, simple=False, inp=stdin, regexp=False)

        cmderrors = parselogForError(cmdttdouterr, regExp="^ERROR:", stdout=True)
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


class EB_bioconductor(EB_RPackage):
    """
    The Bioconductor package extends DefaultRPackage to use a different source
    And using the biocLite package to do the installation.
    """
    def makeCmdLineCmd(self):
        self.log.error("bioconductor.run: Don't know how to install a specific version of a bioconductor package.")

    def makeRCmd(self):
        name = self.pkg['name']
        self.log.debug("Installing bioconductor package %s." % name)
        blName = "\"%s\"" % name

        Rcmd = """
        source("http://bioconductor.org/biocLite.R")
        biocLite(%s)
        """ % (blName)
        cmd = "R -q --no-save"

        return cmd, Rcmd

## special cases of bioconductor packages
# handled by class aliases
EB_BSgenome = EB_GenomeGraphs = EB_ShortRead = EB_bioconductor
EB_Biobase = EB_IRanges = EB_AnnotationDbi = EB_bioconductor
# exonmap doesn't seem to be available trought biocLite anymore...
EB_exonmap = EB_bioconductor

class EB_Rserve(EB_RPackage):
    def run(self):
        self.setconfigurevars(['LIBS="$LIBS -lpthread"'])
        EB_RPackage.run(self)

#class EB_rsprng(EB_RPackage):
#    def run(self):
#        self.log.debug("Setting configure args for %s" % self.name)
#        self.setconfigurevars(['LIBS=\\"%s %s\\"' % (os.environ["LIBS"], os.environ["LDFLAGS"])])
#        self.setconfigureargs(["--with-sprng=%s" % os.environ["EBROOTSPRNG"]])
#        EB_RPackage.run(self)
#
#
#class rgdal(EB_RPackage):
#    def run(self):
#        self.log.debug("Setting configure args for %s" % self.name)
#        softrootproj = os.environ["SOFTROOTPROJ"]
#        self.setconfigureargs(["--with-proj-include=%s/include --with-proj-lib=%s/lib" % (softrootproj, softrootproj)])
#        EB_RPackage.run(self)

#class EB_Rmpi(EB_Rpackage):
#    def run(self):
#        if os.environ.has_key('SOFTROOTICTCE'):
#            self.log.debug("Setting configure args for Rmpi")
#            self.setconfigureargs(["--with-Rmpi-include=%s/intel64/include" % os.environ["SOFTROOTIMPI"],
#                                   "--with-Rmpi-libpath=%s/intel64/lib" % os.environ["SOFTROOTIMPI"],
#                                   "--with-Rmpi-type=MPICH"])
#            DefaultRpackage.run(self)
#        elif os.environ.has_key('SOFTROOTIQACML'):
#            self.log.debug("Installing most recent version of package %s (iqacml toolkit)." % self.name)
#            self.setconfigureargs(["--with-Rmpi-include=%s/include" % os.environ["SOFTROOTQLOGICMPI"],
#                                   "--with-Rmpi-libpath=%s/lib64" % os.environ["SOFTROOTQLOGICMPI"],
#                                   "--with-mpi=%s" % os.environ["SOFTROOTQLOGICMPI"],
#                                   "--with-Rmpi-type=MPICH"])
#            cmd, inp = self.makeRCmd()
#
#            fn = os.path.join("/tmp", "inputRmpi_install.R")
#            f = open(fn, "w")
#            f.write(inp)
#            f.close()
#            cmd = "mpirun -np 1 -H localhost %s -f %s" % (cmd, fn)
#            run_cmd(cmd, log_all=True, simple=False)
#            os.remove(fn)
#        else:
#            self.log.error("Unknown toolkit, don't know how to install Rmpi with this toolkit! Giving up...")

### Just add VIM's dependencies to the list of dependencies, we don't really wanna 
## build with dependencies enabled
##class EB_VIM(EB_Rpackage):
##    def makeCmdLineCmd(self):
##         fancy trick to install VIM dependencies first, without installing VIM
##         then install source of VIM with specified version 
##        Rcmd = """
##        options(repos=c(CRAN="http://www.freestatistics.org/cran"))
##        install.packages("%s", dependencies="Depends", INSTALL_opts="--fake")
##        install.packages("%s")
##        """ % (self.name, self.src)
##        cmd = "R -q --no-save"
##
##        self.log.debug("makeRCmd returns %s with input %s" % (cmd, Rcmd))
##
##        return (cmd, Rcmd)
#
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
