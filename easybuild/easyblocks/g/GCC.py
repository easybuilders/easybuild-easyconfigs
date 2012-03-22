import os, shutil
from copy import copy
from distutils.version import LooseVersion

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd

class GCC(Application):
    """
    Self-contained build of GCC.
    Uses system compiler for initial build, then bootstraps (by default).
    """
    def __init__(self, *args, **kwargs):
        Application.__init__(self, *args, **kwargs)

        self.cfg.update({'languages':[[], "List of languages to build GCC for (--enable-languages) [default: []]"],
                         'bootstrap':[True, "Enable bootstrapping (--enable-bootstrap)."],
                         'withcloog':[False, "Build GCC with CLooG support (default: False)."],
                         'withppl':[False, "Build GCC with PPL support (default: False)."],
                         }
                        )

        self.stagedbuild = False

    def create_obj_dir(self):
        """
        Create an obj dir to build in.
        """
        
        objdir=os.path.join(self.getcfg('startfrom'),'obj')
        try:
            while os.path.exists(objdir):
                # for 2-staged build, create a separate obj dir
                objdir = "%s_" % objdir
            os.mkdir(objdir)
            #self.setcfg('startfrom', objdir)
            #os.chdir(self.getcfg('startfrom'))
            os.chdir(objdir)
        except OSError, err:
            self.log.exception("Can't use obj dir %s to build in: %s"%(objdir, err))

    def prep_extra_src_dirs(self, stage="stage1"):
        """
        Prepare extra (optional) source directories, so GCC will build these as well. 
        """

        configopts = ''
        extra_src_dirs = ["gmp", "mpfr", "mpc"]

        ## add optional ones that were selected (e.g. CLooG, PPL, ...)
        for x in ["cloog", "ppl"]:
            if self.getcfg('with%s'%x):
                extra_src_dirs.append(x)

        ## see if modules are loaded
        ## if module is available, just use the --with-X GCC configure option
        for extra in copy(extra_src_dirs):
            envvar = os.getenv('SOFTROOT%s' % extra.upper())
            if envvar:
                configopts += " --with-%s=%s" % (extra, envvar)
                extra_src_dirs.remove(extra)
            elif extra in ["cloog", "ppl"] and stage == "stage1":
                ## building CLooG or PPL requires a recent compiler
                ## our best bet is to do a 2-staged build of GCC, and
                ## build CLooG/PPL with the GCC we're building in stage 2
                self.stagedbuild=True
                extra_src_dirs.remove(extra)

        # try and find source directories with given prefixes
        # these sources should be included in list of sources in .eb spec file,
        # so EasyBuild can unpack them in the build dir
        found_src_dirs = []
        all_dirs = os.listdir(self.builddir)
        for d in all_dirs:
            for sd in extra_src_dirs:
                if d.startswith(sd):
                    found_src_dirs.append({'source_dir':d,
                                           'target_dir':sd
                                           })

        # we need to find all dirs specified, or else...
        if not len(found_src_dirs) == len(extra_src_dirs):
            self.log.error("Couldn't find all source dirs %s: found %s from %s"%(extra_src_dirs, found_src_dirs, all_dirs))

        # copy to a dir with name as expected by GCC build framework
        for d in found_src_dirs:
            src = os.path.join(self.builddir, d['source_dir'])
            dst = os.path.join(self.getcfg('startfrom'), d['target_dir'])
            if not os.path.exists(dst):
                try:
                    shutil.copytree(src, dst)
                except OSError, err:
                    self.log.error("Failed to copy src %s to dst %s: %s"%(src, dst, err))
                self.log.debug("Copied %s to %s, so GCC can build %s" % (src, dst, d['target_dir']))
            else:
                self.log.debug("No need to copy %s to %s, it's already there." % (src, dst))

        self.log.debug("Prepared extra src dirs for %s: %s (configopts: %s)" % (stage, found_src_dirs, configopts))

        return configopts

    def configure(self):
        """
        Configure for GCC build:
        - prepare extra source dirs (GMP, MPFR, MPC, ...)
        - create obj dir to build in (GCC doesn't like to be built in source dir)
        - add configure and make options, according to .eb spec file
        """

        self.lv = LooseVersion(self.version())
        if self.lv <= LooseVersion("4.6.3") or self.lv >= LooseVersion("4.7"):
            self.log.warning("\n\nWARNING: This build procedure has only been well tested for GCC v4.6.x.\n" +
                             "If you run into any problems, please contact the EasyBuild developers.\n")

        # self.configopts will be reused in a 2-staged build,
        # configopts is only used in first configure
        self.configopts = self.getcfg('configopts')

        #
        # I) prepare extra source dirs, e.g. for GMP, MPFR, MPC (if required), so GCC can build them
        #

        configopts = self.prep_extra_src_dirs()

        #
        # II) create obj dir to build in, and change to it
        #     GCC doesn't like to be built in the source dir
        #
        self.create_obj_dir()

        # III) update config options

        ## enable specified language support
        if self.getcfg('languages'):
            self.configopts += " --enable-languages=%s" % ','.join(self.getcfg('languages'))

        ## enable bootstrapping if desired
        if self.getcfg('bootstrap') and not self.stagedbuild:
            configopts += " --enable-bootstrap"
        else:
            if not self.stagedbuild:
                self.log.info("WARNING: Building without bootstrapping, " + 
                              "so this GCC build will be dependent on system libraries!")
            configopts += " --disable-bootstrap"

        ## configure for a release build
        self.configopts += " --enable-checking=release "
        ## enable C++ support (required for GMP build), disable multilib (???)
        self.configopts += " --enable-cxx --disable-multilib"
        ## build both static and dynamic libraries (???)
        self.configopts += " --enable-shared=yes --enable-static=yes "
        ## use POSIX threads, enable link-time-optimization (LTO) support
        self.configopts += " --enable-threads=posix --enable-lto"
        ## use GOLD as default linker, enable plugin support
        self.configopts += " --enable-gold=default --enable-plugins "
        ##
        self.configopts += " --enable-ld --with-plugin-ld=ld.gold"

        if self.stagedbuild:
            self.log.info("Starting with stage 1 of 2-staged build to enable CLooG and/or PPL support...")
            self.stage1dir = os.path.join(self.builddir, 'GCC_stage1_eb')
            configopts += " --prefix=%(p)s --with-local-prefix=%(p)s" % {'p' : self.stage1dir}

        else:
            # unstaged build, so just run standard configure/make/make install
            ## set prefixes
            self.log.info("Performing regular GCC build...")
            configopts += " --prefix=%(p)s --with-local-prefix=%(p)s" % {'p' : self.installdir }

        # IV) actual configure, but not on default path
        cmd = "%s ../configure  %s %s" % (
                                           self.getcfg('preconfigopts'),
                                           self.configopts,
                                           configopts
                                          )
        run_cmd(cmd, log_all=True, simple=True)

    def make(self):

        if self.stagedbuild:

            # make and install stage 1 build of GCC
            paracmd = ''
            if self.getcfg('parallel'):
                paracmd = "-j %s" % self.getcfg('parallel')

            cmd = "%s make %s %s" % (self.getcfg('premakeopts'), paracmd, self.getcfg('makeopts'))
            run_cmd(cmd, log_all=True, simple=True)

            cmd = "make install %s" % (self.getcfg('installopts'))
            run_cmd(cmd, log_all=True, simple=True)

            # register built GCC as compiler to use for stage 2
            path = "%s/bin:%s"%(self.stage1dir, os.getenv('PATH'))
            os.putenv('PATH', path)

            ld_lib_path = "%(dir)s/lib64:%(dir)s/lib:%(val)s"% {
                                      'dir':self.stage1dir, 
                                      'val':os.getenv('LD_LIBRARY_PATH')
                                      }
            os.putenv('LD_LIBRARY_PATH', ld_lib_path)

            # create new obj dir and change into it
            self.create_obj_dir()

            # reconfigure for stage 2 build
            self.log.info("Stage 1 of 2-staged build completed, continuing with stage 2 (with CLooG and/or PPL support enabled)...")

            configopts = self.prep_extra_src_dirs(stage="stage2")
            configopts += " --prefix=%(p)s --with-local-prefix=%(p)s" % {'p' : self.installdir }

            if self.getcfg('bootstrap'):
                configopts += " --enable-bootstrap"
            else:   
                self.log.info("WARNING: Building without bootstrapping, " + 
                      "so this GCC build will be dependent on system libraries!")
                configopts += " --disable-bootstrap"

            cmd = "%s ../configure %s %s" % (
                                             self.getcfg('preconfigopts'),
                                             self.configopts,
                                             configopts
                                             )
            run_cmd(cmd, log_all=True, simple=True)

        else:
            # unstaged build, so just run standard configure/make/make install

            if self.getcfg('bootstrap'):
                self.setcfg('makeopts', '%s bootstrap' % self.getcfg('makeopts'))

        # call original make
        Application.make(self)

    # make install is just default makeInstall, nothing special there

    def sanitycheck(self):
        """
        Custom sanity check for GCC
        """
        if not self.getcfg('sanityCheckPaths'):

            common_infix = 'gcc/x86_64-unknown-linux-gnu/%s' % self.version()

            bin_files = ["gcov"]
            lib64_files = ["libgcc_s.so", "libgomp.so", "libgomp.a", "libmudflap.so", "libmudflap.a"]
            libexec_files = []
            dirs = ['lib/%s' % common_infix,
                           'lib64']

            if not self.getcfg('languages'):
                # default languages are c, c++, fortran
                bin_files = ["c++","cpp","g++","gcc","gcov","gfortran"]
                lib64_files.extend(["libstdc++.so", "libstdc++.a"])
                libexec_files = ['cc1', 'cc1plus', 'collect2', 'f951']

            if 'c' in self.getcfg('languages'):
                bin_files.extend(['cpp', 'gcc'])

            if 'c++' in self.getcfg('languages'):
                bin_files.extend(['c++', 'g++'])
                dirs.append('include/c++/%s' % self.version())
                lib64_files.extend(["libstdc++.so", "libstdc++.a"])

            if 'fortran' in self.getcfg('languages'):
                bin_files.append('gfortran')
                lib64_files.extend(['libgfortran.so', 'libgfortran.a'])

            if 'lto' in self.getcfg('languages'):
                libexec_files.extend(['liblto_plugin.so', 'lto1', 'lto-wrapper'])

            if self.getcfg('withcloog') or self.getcfg('withppl'):
                self.log.error("Sanity check needs to be updated for CLooG/PPL?!?")

            bin_files = ["bin/%s"%x for x in bin_files]
            lib64_files = ["lib64/%s/%s" % (common_infix, x) for x in lib64_files]
            libexec_files = ["libexec/%s/%s" % (common_infix, x) for x in libexec_files]

            self.setcfg('sanityCheckPaths',{'files':bin_files + lib64_files + libexec_files,
                                            'dirs':dirs
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

    def makeModuleReqGuess(self):
        """
        Make sure all GCC libs are in LD_LIBRARY_PATH
        """
        return {
                'PATH':['bin'],
                'LD_LIBRARY_PATH':['lib','lib64',
                                   'lib/gcc/x86_64-unknown-linux-gnu/%s'%self.getcfg('version')],
                'MANPATH':['man','share/man']
               }
