import os
import shutil
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd

class HPL(Application):
    """
    Support for building HPL (High Performance Linpack)
    - create Make.UNKNOWN
    - build with make and install 
    """

    def configure(self, subdir=None):
        """
        Create Make.UNKNOWN file to build from
        - provide subdir argument so this can be reused in HPCC easyblock
        """

        basedir = self.getcfg('startfrom')
        if subdir:
            makeincfile = os.path.join(basedir, subdir, 'Make.UNKNOWN')
            setupdir = os.path.join(basedir, subdir, 'setup')
        else:
            makeincfile = os.path.join(basedir, 'Make.UNKNOWN')
            setupdir = os.path.join(basedir, 'setup')

        try:
            os.chdir(setupdir)
        except OSError, err:
            self.log.exception("Failed to change to to dir %s: %s" % (setupdir, err))

        cmd = "/bin/bash make_generic"

        run_cmd(cmd, log_all=True, simple=True, log_output=True)

        try:
            os.symlink(os.path.join(setupdir, 'Make.UNKNOWN'), os.path.join(makeincfile))
        except OSError, err:
            self.log.exception("Failed to symlink Make.UNKNOWN from %s to %s: %s" % (setupdir, makeincfile, err))

        ## go back
        os.chdir(self.getcfg('startfrom'))

    def make(self):
        """
        Build with make and correct make options
        """

        for envvar in ['MPICC', 'LIBLAPACK_MT', 'CPPFLAGS', 'LDFLAGS', 'CFLAGS']:
            if not os.getenv(envvar):
                self.log.error("Required environment variable %s not found (no toolkit used?)." % envvar)

        # build dir
        extra_makeopts = 'TOPdir="%s" ' % self.getcfg('startfrom')

        # compilers
        extra_makeopts += 'CC="%(mpicc)s" MPICC="%(mpicc)s" LINKER="%(mpicc)s" ' % { 'mpicc':os.getenv('MPICC') }

        # libraries: LAPACK and FFTW
        extra_makeopts += 'LAlib="%s %s" ' % (os.getenv('LIBFFT'),
                                              os.getenv('LIBLAPACK_MT'))

        # HPL options
        extra_makeopts += 'HPL_OPTS="%s -DUSING_FFTW" ' % os.getenv('CPPFLAGS')

        # linker flags
        extra_makeopts += 'LINKFLAGS="%s" ' % os.getenv('LDFLAGS')

        # C compilers flags
        extra_makeopts += "CCFLAGS='$(HPL_DEFS) %s' " % os.getenv('CFLAGS')

        # set options and build
        self.updatecfg('makeopts', extra_makeopts)
        Application.make(self)

    def make_install(self):
        """
        Install by copying files to install dir
        """
        srcdir = os.path.join(self.getcfg('startfrom'), 'bin', 'UNKNOWN')
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ["xhpl", "HPL.dat"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

    def sanitycheck(self):
        """
        Custom sanity check for HPL
        """
        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths',{'files':["bin/xhpl"],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)