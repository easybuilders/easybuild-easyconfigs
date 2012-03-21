import os, shutil
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
                         'clooguseisl':[False, ""],
                         'pplwatchdog':[False, ""]
                         }
                        )

        self.stagedbuild = False

    def prep_extra_src_dirs(self, src_dirs):
        """
        Prepare extra (optional) source directories, so GCC will build these as well. 
        """
        # try and find source directories with given prefixes
        # these sources should be included in list of sources in .eb spec file,
        # so EasyBuild can unpack them in the build dir
        found_src_dirs = []
        all_dirs=os.listdir(self.builddir)
        for d in all_dirs:
            for sd in src_dirs:
                if d.startswith(sd):
                    found_src_dirs.append({'source_dir':d,
                                           'target_dir':sd
                                           })

        # we need to find all dirs specified, or else...
        if not len(found_src_dirs) == len(src_dirs):
            self.log.error("Couldn't find all source dirs %s: found %s from %s"%(src_dirs, found_src_dirs, all_dirs))

        # copy to a dir with name as expected by GCC build framework
        for d in found_src_dirs:
            src = os.path.join(self.builddir, d['source_dir'])
            dst = os.path.join(self.getcfg('startfrom'), d['target_dir'])
            try:
                shutil.copytree(src, dst)
            except OSError, err:
                self.log.error("Failed to copy src %s to dst %s: %s"%(src, dst, err))

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

        configopts = self.getcfg('configopts')

        #
        # I) prepare extra source dirs, e.g. for GMP, MPFR, MPC (if required)
        #

        extra_src_dirs = ["gmp", "mpfr", "mpc"]

        ## add optional ones that were selected (e.g. CLooG, PPL, ...)
        for x in ["cloog","ppl"]:
            if self.getcfg('with%s'%x):
                extra_src_dirs.append(x)

        ## see if modules are loaded
        ## if module is available, just use the --with-X GCC configure option
        for extra in extra_src_dirs:
            envvar = os.getenv('SOFTROOT%s' % extra.upper())
            if envvar:
                configopts += " --with-%s=%s" % (extra, envvar)
                extra_src_dirs.remove(extra)
            elif extra == "cloog" or extra == "ppl":
                ## building CLooG or PPL requires a recent compiler
                ## our best bet is to do a 2-staged build of GCC, and
                ## build CLooG/PPL with the GCC we're building in stage 2
                self.stagedbuild=True

        ## try and prepare source dirs for others, so GCC can build them
        self.prep_extra_src_dirs(extra_src_dirs)

        #
        # II) create obj dir to build in 
        #     GCC doesn't like to be built in the source dir
        #
        objdir=os.path.join(self.getcfg('startfrom'),'obj')
        try:
            os.mkdir(objdir)
            self.setcfg('startfrom', objdir)
            os.chdir(self.getcfg('startfrom'))
        except OSError, err:
            self.log.exception("Can't use obj dir %s to build in: %s"%(objdir, err))

        # III) update config options

        ## enable specified language support
        if self.getcfg('languages'):
            configopts += " --enable-languages=%s" % ','.join(self.getcfg('languages'))

        ## enable bootstrapping if desired
        if self.getcfg('bootstrap'):
            configopts += " --enable-bootstrap"
        else:
            self.log.info("WARNING: Building without bootstrapping, " + 
                          "so this GCC build will be dependent on system libraries!")
            configopts += " --disable-bootstrap"

        ## configure for a release build
        configopts += " --enable-checking=release "
        ## enable C++ support (required for GMP build), disable multilib (???)
        configopts += " --enable-cxx --disable-multilib"
        ## build both static and dynamic libraries (???)
        configopts += " --enable-shared=yes --enable-static=yes "
        ## use POSIX threads, enable link-time-optimization (LTO) support
        configopts += " --enable-threads=posix --enable-lto"
        ## use GOLD as default linker, enable plugin support
        configopts += " --enable-gold=default --enable-plugins "
        ##
        configopts += " --enable-ld --with-plugin-ld=ld.gold"


        if stagedbuild:
            self.log.error("Staged build not fully implemented yet")

            configopts += " --with-prefix=%(p)s --with-local-prefix=%(p)s" % {'p' : 'FOO' }

        else:
            # unstaged build, so just run standard configure/make/make install
            ## set prefixes
            configopts += " --with-prefix=%(p)s --with-local-prefix=%(p)s" % {'p' : self.installdir }

        # IV) actual configure, but not on default path
        cmd = "%s ../configure --prefix=%s %s" % (
                                                  self.getcfg('preconfigopts'),
                                                  self.installdir,
                                                  configopts
                                                  )
        run_cmd(cmd, log_all=True, simple=True)

    def make(self):

        if stagedbuild:
            self.log.error("Staged build not fully implemented yet")

        else:
            # unstaged build, so just run standard configure/make/make install

            if self.getcfg('bootstrap'):
                self.setcfg('makeopts', '%s bootstrap' % self.getcfg('makeopts'))

            Application.make(self)

    def makeInstall(self):

        if stagedbuild:


        else:
            # unstaged build, so just run standard configure/make/make install
            Application.makeInstall(self)

    def sanityCheck(self):
        """
        Custom sanity check for GCC
        """
        if not self.getCfg('sanityCheckPaths'):

            common_infix = 'gcc/x86_64-unknown-linux-gnu/%s' % self.version()

            bin_files = ["gcov"]
            lib64_files = ["libgcc_s.so", "libgomp.so", "libgomp.a", "libmudflap.so", "libmudflap.a"]
            libexec_files = []
            dirs = ['lib/%s' % common_infix,
                           'lib64']

            if not self.getcfg('languages'):
                # default languages are c, c++, fortran
                bin_files = ["c++","cpp","g++","gcc","gcov","gfortran"]
                lib64_files.append(["libstdc++.so", "libstdc++.a"])
                libexec_files = ['cc1', 'cc1plus', 'collect2', 'f951']

            if 'c' in self.getcfg('languages'):
                bin_files.append(['cpp', 'gcc'])

            if 'c++' in self.getcfg('languages'):
                bin_files.append(['c++', 'g++'])
                dirs.append('include/c++/%s' % self.version())
                lib64_files.append(["libstdc++.so", "libstdc++.a"])

            if 'fortran' in self.getcfg('languages'):
                bin_files.append('gfortran')
                lib64_files.append(['libgfortran.so', 'libgfortran.a'])

            if 'lto' in self.getcfg('languages'):
                libexec_files.append(['liblto_plugin.so', 'lto1', 'lto-wrapper'])

            bin_files = ["bin/%s"%x for x in bin_files]
            lib64_files = ["lib64/%s/%s" % (common_infix, x) for x in lib64_files]
            libexec_files = ["libexec/%s/%s" % (common_infix, x) for x in libexec_files]

            self.setCfg('sanityCheckPaths',{'files':bin_files + lib64_files + libexec_files,
                                            'dirs':dirs
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)


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

# OLD STUFF
# need to port steps to enable CLooG/PPL support in build (3-step build)

#class Gccv2(Application):
#    """
#    Install GCC with lots of bells and whistles
#    - tested with GCC4.5.2
#    
#    2 staged build
#    - 1 local no PPL/CLooG
#    - 2 real build with PPL/CLooG
#    """
#    def extraCfg(self,locs):
#        """
#        Parse some extra variables
#        """
##        self.languages=['c','c++','fortran','lto']
##        if locs.has_key('languages'):
##            self.languages=locs['languages']
##        self.log.info("Using languages %s"%self.languages)
#
#        self.clooguseisl=True
#        if locs.has_key('clooguseisl'):
#            self.clooguseisl=locs['clooguseisl']
#        self.log.info("Using cloog with isl %s"%self.clooguseisl)
#
#        ## warning: enable-gold requires c++ in stage1 language (4.6.0) 
##        self.bootstrap=False
##        if locs.has_key('bootstrap'):
##            self.bootstrap=locs['bootstrap']
##        self.log.info("Using bootstrap %s"%self.bootstrap)
#
##        self.werror=True
##        if locs.has_key('werror'):
##            self.werror=locs['werror']
##        self.log.info("Using werror %s"%self.werror)
#
#        self.pplwatchdog=True
#        if locs.has_key('pplwatchdog'):
#            self.pplwatchdog=locs['pplwatchdog']
#        self.log.info("Using pplwatchdog %s"%self.pplwatchdog)
#
#    
#    def prep(self,extra,skipcleanup=False,nooverride=True):
#        self.prefix=os.path.join(self.builddir,'tmpbuild')
#        
#        found=[]
#        bus=['bfd','binutils','ld','gold','cpu','gas','gprof','elfcpp','intl','opcodes','include']
#        lenbu=0
#        alldirs=os.listdir(self.builddir)
#        for d in alldirs:
#            for ex in extra:
#                if d.find(ex) == 0:
#                    if ex == 'binutils':
#                        """
#                        If not all binutil subdirs are found, this will generate error
#                        - -1 for the binutils entry in extra
#                        """
#                        lenbu=len(bus)-1
#                        for bud in bus:
#                            budir=os.path.join(d,bud)
#                            if os.path.isdir(os.path.join(self.builddir,budir)):
#                                found.append([budir,bud])
#                            else:
#                                self.log.debug("Not found binutils %s in %s"%(bud,d))
#                    else:
#                        found.append([d,ex])
#        
#        if not len(found) == len(extra)+lenbu:
#            self.log.error("prep: Couldn't find %s: found %s from %s (lenbu %s)"%(extra,found,alldirs,lenbu))
#        
#        regbin=re.compile(r"binutils.*/(include|intl)")
#        for d in found:
#            src=os.path.join(self.builddir,d[0])
#            dst=os.path.join(self.getCfg('startfrom'),d[1])
#            try:
#                r=regbin.search(src)
#                if nooverride and r:
#                    """
#                    the binutils include/intl dir
#                    - copy all files that are missing
#                    """
#                    listdst=os.listdir(dst)
#                    self.log.debug("binutils %s dst files %s"%(r.group(1),listdst))
#                    for f in os.listdir(src):
#                        if not f in listdst:
#                            nsrc=os.path.join(src,f)
#                            self.log.debug("binutils %s src file to be copied %s (%s)"%(r.group(1),f, nsrc))
#                            if os.path.isdir(nsrc):
#                                shutil.copytree(nsrc,os.path.join(dst,f))
#                            else:
#                                shutil.copy(nsrc,dst)
#                else:
#                    if os.path.isdir(dst):
#                        shutil.rmtree(dst)
#                        self.log.debug("prep: Removed existing dir %s"%dst)
#                    
#                    shutil.copytree(src,dst)
#            except:
#                self.log.exception("prep: Failed to copy src %s to dst %s"%(src,dst))
#
#        oldpwd=os.getcwd()
#        objname='objtmpbuild'
#        if self.getCfg('startfrom').endswith(objname):
#            newstart=self.getCfg('startfrom')
#        else:
#            newstart=os.path.join(self.getCfg('startfrom'),objname)
#        try:
#            if os.path.isdir(newstart):
#                if skipcleanup:
#                    self.log.debug("prep: skipcleanup %s Not removing existing dir %s"%(skipcleanup,newstart))
#                else:
#                    ## new obj dir
#                    shutil.rmtree(newstart)
#                    self.log.debug("prep: Removed existing dir %s"%newstart)
#            ## could be removed or not existing, or existing and skipcleanup
#            if not os.path.isdir(newstart):
#                os.mkdir(newstart)
#            self.setcfg('startfrom', newstart)
#            os.chdir(self.getCfg('startfrom'))
#            self.log.debug("prep: Created and changed to dir %s"%newstart)
#        except:
#            self.log.exception("Can't use new start dir %s"%(newstart))
#
#        return oldpwd
#    
#    def configure(self):
#        """
#        Prep + Stage 1
#        """
#        self.log.info("configure: stage 1")
#        
#        ## libelf static build with PIC (libelf needed for LTO)
#        os.environ['XCFLAGS']='-fPIC -DPIC'
#        os.putenv('XCFLAGS','-fPIC -DPIC')
#
#        ## fix CPP for GMP issues (gmpxx.h not found)
#        cpf='CPPFLAGS'
#        cpp="%s -I%s"%(os.environ.get(cpf,''),os.path.join(os.getcwd(),'gmp'))
#        os.environ[cpf]=cpp
#        os.putenv(cpf,cpp)
#
#        extra=['binutils','gmp','mpfr','mpc','libelf']
#        oldpwd=self.prep(extra,nooverride=False)
#        
#        ## ../configure
#        cmd="../configure --prefix=%(pref)s --with-local-prefix=%(pref)s --with-build-time-tools=%(pref)s/bin "%{'pref':self.prefix}
##        cmd+="--enable-languages=%s "%','.join(self.languages)
#        cmd+="--disable-multilib "
#        cmd+="--enable-shared=yes --enable-static=yes "
#        cmd+="--enable-threads=posix --enable-checking=release "
#        cmd+="--enable-lto "
#        cmd+="--enable-gold=default --enable-plugins "
#        cmd+="--enable-ld " 
#        ## gcc option for gold
#        cmd+="--with-plugin-ld=ld.gold "
#
##        if self.werror:
##            cmd+="--enable-werror "
##        else:
##            cmd+="--disable-werror "
#
#
#        if self.bootstrap:
#            ## not for stage 1 
#            cmd+="--enable-bootstrap "
#            bootstrap='bootstrap'
#        else:
#            cmd+="--disable-bootstrap "
#            bootstrap=''
#
#        ## for GMP build
#        cmd+="--enable-cxx "
#        cmd+="%s"%self.getCfg('configopts')
#
#        runrun(cmd,logall=True,simple=True)
#        paracmd=''
#        if self.getCfg('parallel'):
#            paracmd="-j %s"%self.getCfg('parallel')
#        cmd="make %s %s"%(paracmd,bootstrap)
#        runrun(cmd,logall=True,simple=True)
#
#        cmd="make install"
#        runrun(cmd,logall=True,simple=True)
#
#        ## new GCC
#        p='PATH'
#        pp="%s/bin:%s"%(self.prefix,os.environ.get(p,''))
#        os.environ[p]=pp
#        os.putenv(p,pp)
#
#        p='LD_LIBRARY_PATH'
#        pp="%s/lib64:%s/lib:%s"%(self.prefix,self.prefix,os.environ.get(p,''))
#        os.environ[p]=pp
#        os.putenv(p,pp)
#
#
#        ## go back
#        try:
#            os.chdir(oldpwd)
#            self.log.debug("configure: changed back to %s"%oldpwd)
#        except:
#            self.log.exception("configure: failed to change back to %s"%oldpwd)
#        
#    def make(self):
#        """
#        Prep PPL/CLooG
#        """
#        self.log.info("make: stage 2")
#        
#        """
#        Rebuild+install GMP and build+install PPL and CLooG
#        """
#        extra=['gmp','ppl','cloog']
#        oldpwd=self.prep(extra,skipcleanup=True)
#
#        paracmd=''
#        if self.getCfg('parallel'):
#            paracmd="-j %s"%self.getCfg('parallel')
#
#        currdir=os.getcwd()
#
#        """
#        GMP
#        """
#        try:
#            np=os.path.join(currdir,'gmp')
#            os.chdir(np)
#            self.log.debug("configure: changed to %s"%np)
#        except:
#            self.log.exception("configure: failed to change to %s"%np)
#                
#        cmd="./configure --prefix=%s "%self.prefix
#        cmd+="--with-pic "
#        cmd+="--disable-shared "
#        cmd+="--enable-cxx "
#        
#        
#        runrun(cmd,logall=True,simple=True)
#            
#        cmd="make %s install"%paracmd
#        runrun(cmd,logall=True,simple=True)
#
#        ## force correct -L
#        cpf='CPPFLAGS'
#        cpp="%s -L%s"%(os.environ[cpf],os.path.join(self.prefix,'lib'))
#        os.environ[cpf]=cpp
#        os.putenv(cpf,cpp)
#
#        """
#        PPL
#        """
#        try:
#            np=os.path.join(currdir,'ppl')
#            os.chdir(np)
#            self.log.debug("configure: changed to %s"%np)
#        except:
#            self.log.exception("configure: failed to change to %s"%np)
#                
#        cmd="./configure --prefix=%s "%self.prefix
#        cmd+="--with-pic "
#        cmd+="--disable-shared "
#        ## for PPL build and CLooG-PPL linking
#        cmd+="--with-host-libstdcxx='-static-libgcc %s/lib64/libstdc++.a -lm' "%self.prefix
#
#        if self.pplwatchdog:
#            cmd+="--enable-watchdog "
#        else:
#            cmd+="--disable-watchdog "
#
#        cmd+="--with-gmp-prefix=%s "%self.prefix
#        
#        
#        runrun(cmd,logall=True,simple=True)
#            
#        cmd="make %s install"%paracmd
#        runrun(cmd,logall=True,simple=True)
#
#        """
#        CLooG
#        """
#        try:
#            np=os.path.join(currdir,'cloog')
#            os.chdir(np)
#            self.log.debug("configure: changed to %s"%np)
#        except:
#            self.log.exception("configure: failed to change to %s"%np)
#                
#        cmd="./configure --prefix=%s "%self.prefix
#        cmd+="--with-pic "
#        cmd+="--disable-shared "
#
#        if self.clooguseisl:
#            cmd+="--with-isl=bundled "
#        else:
#            cmd+="--with-ppl=%s "%self.prefix
#
#        cmd+="--with-gmp-prefix=%s "%self.prefix
#
#
#        runrun(cmd,logall=True,simple=True)
#            
#        cmd="make %s install"%(paracmd)
#        runrun(cmd,logall=True,simple=True)
#
#        ## go back
#        try:
#            os.chdir(oldpwd)
#            self.log.debug("configure: changed back to %s"%oldpwd)
#        except:
#            self.log.exception("configure: failed to change back to %s"%oldpwd)
#        
#    
#    def makeInstall(self):
#        """
#        Stage 3
#        """ 
#        self.log.info("makeInstall: stage 3")
#        oldpwd=self.prep([])
#        
#        ## ../configure
#        cmd="../configure --prefix=%(pref)s --with-local-prefix=%(pref)s --with-build-time-tools=%(pref)s/bin "%{'pref':self.installdir}
#        cmd+="--enable-languages=%s "%','.join(self.languages)
#        cmd+="--disable-multilib "
#        
#        cmd+="--enable-bootstrap "
#        cmd+="--enable-shared=yes --enable-static=yes "
#        cmd+="--enable-threads=posix --enable-checking=release "
#        cmd+="--enable-lto "
#        cmd+="--enable-gold=default --enable-plugins "
#        cmd+="--enable-ld " 
#        ## gcc option for gold
#        cmd+="--with-plugin-ld=ld.gold "
#        
#        
#        cmd+="--with-ppl=%s "%self.prefix
#        cmd+="--with-host-libstdcxx='-static-libgcc %s/lib64/libstdc++.a -lm' "%self.prefix
#
#        cmd+="--with-cloog=%s "%self.prefix
#        if self.clooguseisl:
#            cmd+="--enable-cloog-backend=isl "
#        
#        ## for GMP build
#        cmd+="--enable-cxx "
#
#        if self.werror:
#            cmd+="--enable-werror "
#        else:
#            cmd+="--disable-werror "
#
#        if self.bootstrap:
#            ## not for stage 1 
#            cmd+="--enable-bootstrap "
#            bootstrap='bootstrap'
#        else:
#            cmd+="--disable-bootstrap "
#            bootstrap=''
#
#        if self.pplwatchdog:
#            cmd+="--enable-watchdog "
#        else:
#            cmd+="--disable-watchdog "
#
#        cmd+="%s"%self.getCfg('configopts')
#        runrun(cmd,logall=True,simple=True)
#        
#        """
#        fix the Makefile
#        OLD CODE from manual attempt that didn't work
#
#
#        ## fixes for PPL 0.11
#        sed -i "s/with-libgmpx*-prefix/with-gmp-build/g" Makefile
#        ## fix PPLIBS path
#        ## no more PPL with cloog-0.16
#        ## 4.5.2 only has cloog-parma
#        ## still needs gmp refs
#        sed -i 's/HOST_PPLLIBS = /HOST_PPLLIBS = $(HOST_GMPLIBS) /' Makefile
#        sed -i 's/HOST_PPLINC = /HOST_PPLINC = $(HOST_GMPINC) /' Makefile
#        
#        reggmpbuild=re.compile(r'with-libgmpx*-prefix')
#        regpplinc=re.compile(r'^\s*HOST_PPLINC\s+=\s+',re.M)
#        regppllibs=re.compile(r'^\s*HOST_PPLLIBS\s+=\s+',re.M)
#        
#        oldmkf='Makefile'
#        newmkf="%s.new"%oldmkf
#        try:
#            mk=open(oldmkf).read()
#            mk=reggmpbuild.sub('with-gmp-build',mk)
#            mk=regpplinc.sub('HOST_PPLINC = $(HOST_GMPINC) ',mk)
#            mk=regppllibs.sub('HOST_PPLLIBS = $(HOST_GMPLIBS) ',mk)
#            open(newmkf,'w').write(mk)
#        except:
#            self.log.exception("Failed to adapt Makefile")
#
#        paracmd=''
#        if self.getCfg('parallel'):
#            paracmd="-j %s"%self.getCfg('parallel')
#        cmd="make -f %s %s bootstrap"%(newmkf,paracmd)
#        """
#            
#        paracmd=''
#        if self.getCfg('parallel'):
#            paracmd="-j %s"%self.getCfg('parallel')
#        cmd="make %s %s"%(paracmd,bootstrap)
#        runrun(cmd,logall=True,simple=True)
#
#        cmd="make install"
#        runrun(cmd,logall=True,simple=True)
#
#        ## go back
#        try:
#            os.chdir(oldpwd)
#            self.log.debug("make: changed back to %s"%oldpwd)
#        except:
#            self.log.exception("make: failed to change back to %s"%oldpwd)
#
#
#    def makeModuleReqGuess(self):
#        """
#        A dictionary of possible directories to look for
#        - bizarre long one is for libgfortranbegin.a, which is actually not needed anymore
#        -- MAIN vs main issue
#        """
#        return {
#                'PATH':['bin'],
#                'LD_LIBRARY_PATH':['lib64','lib/gcc/x86_64-unknown-linux-gnu/%s'%self.getCfg('version'),'lib'],
#                'MANPATH':['man','share/man']
#               }
#        