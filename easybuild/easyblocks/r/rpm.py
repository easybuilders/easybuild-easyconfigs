import os, shutil, re, stat, glob, fileinput, sys
from easybuild.apps.Application import Application
from easybuild.buildsoft.fileTools import runrun, runqanda, unpack

class Tarball(Application):
    """
    Precompiled package: will unpack binary and copy it to the installdir
    """
    def configure(self): pass

    def make(self): pass

    def makeInstall(self):
        src=self.getCfg('startfrom')
        # shutil.copytree cannot handle destination dirs that exist already. On the other hand, Python2.4 cannot create entire paths during copytree.
        # Therefore, only the final directory is deleted.
        shutil.rmtree(self.installdir)
        try:
            # self.getCfg('keepsymlinks') is False by default except when explicitly put to True in .eb file
            shutil.copytree(src,self.installdir, symlinks=self.getCfg('keepsymlinks'))
        except:
            self.log.exception("Copying %s to installation dir %s failed"%(src,self.installdir))


class Scripts(Tarball):

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):
            self.setCfg('sanityCheckPaths',{'files':["bin/%s"%x for x in ["csub","moab_client_wrapper.sh","mympirun.py","myshowq.py",
                                                                          "pbsssh","show_quota.py","showsoft.py"]],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)

    def makeModuleExtra(self):
        """Overwritten from Tarball to add extra txt"""
        txt=Tarball.makeModuleExtra(self)
        path = "$root/bin/fake"
        txt+="prepend-path\tPATH\t\t%s\n"%path
        return txt


class Binary(Application):
    """
    Precompiled package: this class will do nothing except generate modulefiles
    """
    def unpackSrc(self): pass

    def configure(self): pass

    def startFrom(self): pass

    def make(self): pass

    def makeInstall(self): pass

class Rpm(Binary):
    """
    Use Rpms as installer
    - sources is a list of rpms
    - installation is with --nodeps (so the sources list has to be complete)
    - pretty easy
    """
    
    def __init__(self,*args,**kwargs):
        """constructor, overwritten from Binary to add extra config options"""
        Binary.__init__(self, args,kwargs)
        self.makesymlinks=[]
        self.rebuildRPM=False
        
        self.cfg.update({'force':[False,"(default: False)"],
                         'preinstall':[False,"(default: False)"],
                         'postinstall':[False,"(default: False)"],
                         'makesymlinks':[[],"(default: [])"], # Supports glob
                         'modincprefix':['',"(default: '')"],
                         })

    def configure(self):
        cmd="rpm --version"
        (out,_)=runrun(cmd,logall=True,simple=False)
        regexp=re.compile("^RPM\s+version\s+(?P<major>[0-9]+).(?P<minor>[0-9]+).*")
        r=regexp.match(out)
        self.log.debug("r: %s"%(r.group()))
        if r:
            major=int(r.groupdict()['major'])
            minor=int(r.groupdict()['minor'])
            if major >= 4 and minor >= 8:
                self.rebuildRPM=True
                self.log.debug("Enabling rebuild of RPMs to make relocation work...")
        else:
            self.log.debug("WARNING: Checking RPM version failed, so just carrying on with the default behavior...")

        if self.rebuildRPM:
            self.rebuildRPMs()

        
    def importCfg(self,fn):
        """Overwritten from Binary
        
        Parse some extra variables
        """
        locs = Application.importCfg(self, fn)
        #TODO: check this somewhere else?
        if self.rebuildRPM:
            if locs.has_key('osdependencies') and 'rpmrebuild' in locs['osdependencies']:
                self.log.debug('osdependency for rpmrebuild already checked')
            else:
                self.log.debug('Checking osdependency for rpmrebuild')
                self.checkOsdeps(['rpmrebuild'])


        self.log.info("Using force %s" % self.getCfg('force'))
        return locs
    
    # installing RPMs under a non-default path for e.g. SL6
    # --relocate doesn't seem to work (error: Unable to change root directory: Operation not permitted)
    def rebuildRPMs(self):
        rpmmacros=os.path.join(os.environ['HOME'],'.rpmmacros')
        if os.path.exists(rpmmacros):
            self.log.error("rpmmacros file %s found. This will override any other settings."%rpmmacros)

        rpmrebuildtmpdir=os.path.join(self.builddir,"rpmrebuild")
        os.putenv("RPMREBUILD_TMPDIR",rpmrebuildtmpdir)
        try:
            os.makedirs(rpmrebuildtmpdir)
            self.log.debug("Created RPMREBUILD_TMPDIR dir %s"%rpmrebuildtmpdir)
        except Exception:
            self.log.error("Failed to create RPMREBUILD_TMPDIR dir %s"%rpmrebuildtmpdir)

        rpmsPath=os.path.join(self.builddir,'rebuiltRPMs')
        for rpm in self.src:
            cmd="""rpmrebuild -v --change-spec-whole='sed -e "s/^BuildArch:.*/BuildArch:    x86_64/"' --change-spec-whole='sed -e "s/^Prefix:.*/Prefix:    \//"' --change-spec-whole='sed -e "s/^\(.*:[ ]\+\..*\)/#ERROR \1/"' -p -d %s %s"""%(rpmsPath,rpm['path'])

            runrun(cmd,logall=True,simple=True)

        self.oldsrc=self.src
        self.src=[]
        for rpm in os.listdir(os.path.join(rpmsPath,'x86_64')):
            self.src.append({'name':rpm,'path':os.path.join(rpmsPath,'x86_64',rpm)})
        self.log.debug("self.oldsrc: %s"%str(self.oldsrc))
        self.log.debug("self.src: %s"%str(self.src))

    def makeInstall(self):
        """
        Init rpmdb
        """
        try:
            os.chdir(self.installdir)
            os.mkdir('rpm')
        except:
            self.log.exception("Can't create rpm dir in install dir %s"%self.installdir)

        cmd="rpm --initdb --dbpath /rpm --root %s"%self.installdir

        runrun(cmd,logall=True,simple=True)

        force=''
        if self.getCfg('force'):
            force='--force'

        postinstall='--nopost'
        if self.getCfg('postinstall'):
            postinstall=''
        preinstall='--nopre'
        if self.getCfg('preinstall'):
            preinstall=''

        if self.rebuildRPM:
            cmdtmpl="rpm -i --dbpath %(inst)s/rpm %(force)s --relocate /=%(inst)s %(pre)s %(post)s --nodeps %(rpm)s"
        else:
            cmdtmpl="rpm -i --dbpath /rpm %(force)s --root %(inst)s --relocate /=%(inst)s %(pre)s %(post)s --nodeps %(rpm)s"
        # Exception for user root:
        # --relocate is not necesarry -> --root will relocate more then enough
        # cmdtmpl="rpm -i --dbpath /rpm %(force)s --root %(inst)s %(pre)s %(post)s --nodeps %(rpm)s"

        for rpm in self.src:
            cmd=cmdtmpl%{'inst':self.installdir,'rpm':rpm['path'],'force':force,'pre':preinstall,'post':postinstall}
            runrun(cmd,logall=True,simple=True)

        for d in self.makesymlinks:
            """
            Allow globs, always use first hit.
            - also verify links existince
            """
            realdirs=glob.glob(d)
            if realdirs:
                if len(realdirs) > 1:
                    self.log.debug("More then one match found for symlink glob %s. using first). All %s"%(d,realdirs))
                os.symlink(realdirs[0],os.path.join(self.installdir,os.path.basename(d)))

            else:
                self.log.debug("No match found for symlink glob %s."%(d))

    def makeModuleReqGuess(self):
        """
        A dictionary of possible directories to look for
        """
        return {
                'PATH':['usr/bin','sbin','usr/sbin','bin'],
                'LD_LIBRARY_PATH':['lib','lib64','usr/lib','usr/lib64'],
                'MANPATH':['usr/share/man']
               }


class Open64RPM(Rpm):

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):

            subdir="opt/x86_open64-%s/"%self.version()

            self.setCfg('sanityCheckPaths',{'files':["%s/bin/%s"%(subdir,x) for x in ["opencc","openCC","openf90","openf95"]],
                                            'dirs':["%s/lib/gcc-lib/x86_64-open64-linux/%s"%(subdir,self.version()),
                                                    "%s/include/%s"%(subdir,self.version())]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)

    def makeModuleReqGuess(self):
        oldmap=Rpm.makeModuleReqGuess(self)
        ## add possible open64 glob prefix
        newmap={}
        for k,vs in oldmap.items():
            newmap[k]=[]
            for v in vs:
                newmap[k].append("opt/x86_open64*/%s"%v)
        return newmap

class PostgreSQLRPM(Rpm):

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):

            v='.'.join(self.version().split('.')[0:2])

            self.setCfg('sanityCheckPaths',{'files':["usr/pgsql-%s/bin/psql"%v],
                                            'dirs':["usr/lib64","usr/pgsql-%s/lib"%v]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)

    def makeModuleReqGuess(self):
        oldmap=Rpm.makeModuleReqGuess(self)
        ## add possible pgsql glob prefix to usr (eg 9.0 support)
        newmap={}
        for k,vs in oldmap.items():
            newmap[k]=[]
            for v in vs:
                newmap[k].append(v)
                pref='usr'
                if v.startswith(pref):
                    v2="%s/pgsql*%s"%(pref,v[len(pref):])
                    newmap[k].append(v2)

        return newmap

class OracleJDK(Tarball):

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):

            self.setCfg('sanityCheckPaths',{'files':["bin/%s"%x for x in ["jar","java","javac"]],
                                            'dirs':["lib"]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)

    def makeModuleReqGuess(self):
        """
        A dictionary of possible directories to look for
        """
        return {
                'JAVA_HOME':'',
                'PATH':['bin'],
                'LD_LIBRARY_PATH':['lib'],
                'MANPATH':['lib']
               }

class SunJDK(Rpm):
    """
    Special class for Sun RPM
    """

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):


            prefix="usr/java/jdk%s"%self.version()

            self.setCfg('sanityCheckPaths',{'files':["%s/bin/%s"%(prefix,x) for x in ["jar","java","javac"]],
                                            'dirs':["%s/lib"%prefix]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)

    def makeModuleReqGuess(self):
        """
        A dictionary of possible directories to look for
        """

        javahome='usr'

        while os.path.isdir(os.path.join(self.installdir,javahome)) and (len(os.listdir(os.path.join(self.installdir,javahome))) == 1):
            javahome=os.path.join(javahome,os.listdir(javahome)[0])
        self.log.info("JAVA_HOME found %s relative to %s"%(javahome,self.installdir))

        return {
                'JAVA_HOME':[javahome],
                'PATH':['%s/bin'%javahome],
                'LD_LIBRARY_PATH':['%s/lib'%javahome],
                'MANPATH':['%s/lib'%javahome]
               }

    def postProc(self):
        """
        Set JAVA_HOME and PATH
        - unpack from postinstall script section
        """
        self.log.info("Start postProc")
        dirmap=self.makeModuleReqGuess()
        k='PATH'
        unpack=os.path.join(self.installdir,dirmap[k][0],'unpack200')

        k='JAVA_HOME'
        jh=os.path.join(self.installdir,dirmap[k][0])

        jars=['jre/lib/rt','jre/lib/jsse','jre/lib/charsets','lib/tools','jre/lib/ext/localedata','jre/lib/plugin','jre/lib/javaws','jre/lib/deploy']
        for jar in jars:
            src=os.path.join(jh,"%s.pack"%jar)
            dst=os.path.join(jh,"%s.jar"%jar)
            cmd="%s %s %s"%(unpack,src,dst)
            runrun(cmd,logall=True,simple=True)


        self.log.info("End postProc")

class ABAQUS(Binary):

    def unpackSrc(self):
        Application.unpackSrc(self)

    def configure(self):
        try:
            installpropsfn="installer.properties"
            self.replayfile=os.path.join(self.builddir,installpropsfn)
            f=file(self.replayfile, "w")
            txt="""INSTALLER_UI=SILENT
USER_INSTALL_DIR=%s
MAKE_DEF_VER=true
DOC_ROOT=UNDEFINED
DOC_ROOT_TYPE=false
DOC_ROOT_ESCAPED=UNDEFINED
ABAQUSLM_LICENSE_FILE=@abaqusfea
PRODUCT_NAME=Abaqus %s
TMPDIR=%s
INSTALL_MPI=1
"""%(self.installdir,self.version(),self.builddir)
            f.write(txt)
            f.close()
        except Exception:
            self.log.error("Failed to create install properties file used for replaying installation")

    def make(self):
        pass

    def makeInstall(self):
        cmd="%s/%s-%s/setup -nosystemcheck -replay %s"%(self.builddir,self.name(),self.version().split('-')[0],self.replayfile)

        runrun(cmd,logall=True,simple=True)

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):
            verparts=self.version().split('-')[0].split('.')

            self.setCfg('sanityCheckPaths',{'files':[os.path.join("Commands","abaqus")],
                                'dirs':["%s-%s"%('.'.join(verparts[0:2]),verparts[2])]
                              })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Binary.sanityCheck(self)

    def makeModuleReqGuess(self):
        """
        A dictionary of possible directories to look for
        """
        return {
                'PATH':['Commands'],
               }

class LSDYNA(Binary):
    """
    LS-DYNA has gzipped binaries
    """

    def makeInstall(self):
        """
        Make the bin directory and copy the unpacked files
        """
        dest=os.path.join(self.installdir,'bin')
        try:
            os.makedirs(dest)
            os.chdir(dest)
            for tmp in self.src:
                self.log.info("Unpacking source %s"%tmp['name'])
                shutil.copy2(tmp['path'],dest)
                unpack(tmp['name'],dest)
        except:
            self.log.exception("Unpacking source in dir %s failed"%(dest))

        try:
            for tmp in glob.glob('*'):
                os.chmod(os.path.join(dest,tmp),stat.S_IRWXU|stat.S_IXOTH|stat.S_IXGRP|stat.S_IROTH|stat.S_IRGRP)
        except:
            self.log.exception("Setting permissions in dir %s failed"%(dest))

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):

            (ver1, ver2, _) = self.version().split('-')
            self.setCfg('sanityCheckPaths',{'files':["bin/ls%s_%s_%s_amd64_redhat46" % (ver1, x, ver2.replace('.','_')) for x in ["d", "s"]],
                                            'dirs':[]
                                            })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Binary.sanityCheck(self)

class CPLEXjre(Binary):
    """
    Version 12.2 has a self-extratcing package with a java installer
    """

    def makeInstall(self):
        tmpdir=os.path.join(self.builddir,'tmp')
        try:
            os.chdir(self.builddir)
            os.makedirs(tmpdir)

            os.putenv('IATEMPDIR',tmpdir)
            os.environ['IATEMPDIR']=tmpdir

        except:
            self.log.exception("Failed to change directory to %s"%self.builddir)

        """
        Run the source
        - self.src: first one is source. others ignored
        """
        src=self.src[0]['path']
        dst=os.path.join(self.builddir,self.src[0]['name'])
        try:
            shutil.copy2(src,self.builddir)
            os.chmod(dst,stat.S_IRWXU)
        except:
            self.log.exception("Couldn't copy %s to %s"%(src,self.builddir))

        cmd="%s -i console"%dst

        qanda={"PRESS <ENTER> TO CONTINUE:":"",
               'Press Enter to continue viewing the license agreement, or enter "1" to accept the agreement, "2" to decline it, "3" to print it, or "99" to go back to the previous screen.:':'1',
               'ENTER AN ABSOLUTE PATH, OR PRESS <ENTER> TO ACCEPT THE DEFAULT :':self.installdir,
               'IS THIS CORRECT? (Y/N):':'y',
               'PRESS <ENTER> TO INSTALL:':"",
               "PRESS <ENTER> TO EXIT THE INSTALLER:":"",
               "CHOOSE LOCALE BY NUMBER:":"",
               "Choose Instance Management Option:":""
                }
        noqanda=[r'Installing\.\.\..*\n.*------.*\n\n.*============.*\n.*$']

        runqanda(cmd,qanda,noqanda=noqanda,logall=True,simple=True)

        try:
            os.chmod(self.installdir,stat.S_IRWXU|stat.S_IXOTH|stat.S_IXGRP|stat.S_IROTH|stat.S_IRGRP)
        except:
            self.log.exception("Can't set permissions on %s"%self.installdir)

        os.chdir(self.installdir)
        binglob='cplex/bin/x86-64*'
        bins=glob.glob(binglob)
        if len(bins):
            if len(bins) > 1:
                self.log.error("More then one possible path for bin found: %s"%bins)
            else:
                self.bindir=bins[0]
        else:
            self.log.error("No bins found using %s in %s"%(binglob,self.installdir))

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):
            subdir=os.path.basename(self.bindir)

            binsubdir="cplex/bin/%s"%subdir
            ver=''.join(self.version().split('.'))
            libsubdir="cplex/lib/%s/static_pic"%subdir
            
            self.setCfg('sanityCheckPaths',{'files':["concert/lib/%s/static_pic/libconcert.a"%subdir,
                                                     "%s/convert"%binsubdir,
                                                     "%s/cplex"%binsubdir,
                                                     "%s/cplexamp"%binsubdir,
                                                     "%s/libcplex%s.so"%(binsubdir,ver),
                                                     "cplex/lib/cplex.jar",
                                                     "%s/libcplex.a"%libsubdir,
                                                     "%s/libilocplex.a"%libsubdir,
                                                     ],
                                            'dirs':["cpoptimizer","licenses","opl"]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)

    def makeModuleExtra(self):
        """Overwritten from Tarball to add extra txt"""
        txt=Binary.makeModuleExtra(self)

        txt+="prepend-path\tPATH\t\t$root/%s\n"%self.bindir
        txt+="setenv\tCPLEX_HOME\t\t$root/cplex"

        return txt

class EKOPath(Binary):
    def makeInstall(self):

        for f in self.src:
            shutil.copy2(f['path'],self.builddir)
            os.chmod(os.path.join(self.builddir,f['name']), 0755)

        installerpath=os.path.join(self.builddir,"%s-%s-installer.run"%(self.name().lower(),self.version()))

        cmd="%s --prefix %s --mode unattended"%(installerpath,self.installdir)

        runrun(cmd,logall=True,simple=True)

class QLogicMPI(Rpm):

    def makeModuleExtra(self):
        """Overwritten from Rpm to add extra txt"""
        txt=Rpm.makeModuleExtra(self)

        txt+="setenv\tMPICH_ROOT\t%s\n"%self.installdir

        return txt

class MVAPICH2QLogic(Rpm):
    def postProc(self):
        """
        Change prefix value to SOFTROOTMVAPICH2 in copmiler wrapper (mpicc and friends)
        """
        prefix='/usr/mpi/*/*/bin/'
        for f in ['mpicc','mpicxx','mpif77','mpif90']:
            g=self.installdir+prefix+f
            fns=glob.glob(g)
            if fns:
                fn=fns[0]
                for line in fileinput.input(fn, inplace=1,backup='.orig'):
                    ## no print, adds newline
                    line=re.sub(r"^prefix=.*", "prefix=%s"%self.installdir,line)
                    ## ? bug in rpm?
                    line=re.sub(r'^(MPI_OTHERLIBS=".*?\s)(\s*")$',r'\1 -lrt"',line)
                    sys.stdout.write(line)
            else:
                self.log.error("postProc file %s not found"%g)

class Treefinder(Tarball):

    def makeInstall(self):
        Tarball.makeInstall(self)

        # patch script to fix install path
        regexp=re.compile("^export\s*TFDIR=.*",re.M)
        for x in ["tf","treefinder"]:
            f=open(os.path.join(self.installdir,x),"r")
            txt=f.read()
            f.close()

            txt=regexp.sub("export TFDIR=%s"%self.installdir,txt)

            f=open(os.path.join(self.installdir,x),"w")
            f.write(txt)
            f.close()

        # make binaries/scripts executable
        for x in ["tf","tf.bin","treefinder"]:
            os.chmod(os.path.join(self.installdir,x),
                    stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|
                    stat.S_IWUSR|stat.S_IWGRP|
                    stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

    def sanityCheck(self):

        if not self.getCfg('sanityCheckPaths'):
            self.setCfg('sanityCheckPaths',{'files':["tf","tf.bin","treefinder"],
                                            'dirs':["Classes","Kernel"]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getCfg('sanityCheckPaths'))

        Application.sanityCheck(self)

    def makeModuleExtra(self):
        """Overwritten from Tarball to add extra txt"""
        txt=Tarball.makeModuleExtra(self)
        txt+="prepend-path\tPATH\t\t$root\n"
        return txt

class FlatTarball(Tarball):
    """
    Specialized extra entries in module file for software that is packaged
    in a 'flat' tarball (no bin or lib dirs)
    """

    def makeModuleExtra(self):
        """Overwritten from Tarball to add extra txt"""
        txt=Tarball.makeModuleExtra(self)

        txt+="""prepend-path\tPATH\t\t$root\n
prepend-path\tLD_LIBRARY_PATH\t\t$root\n
"""

        self.log.debug("makeModuleExtra in FlatTarball, adding this to module file: %s"%txt)

        return txt

class Maple(Binary):

    def unpackSrc(self):
        for f in self.src:
            shutil.copy(f['path'],os.path.join(self.builddir,f['name']))

    def makeInstall(self):
        cmd="%s/Maple%sLinuxX86_64Installer.bin"%(self.builddir,self.getCfg('version'))

        qanda={'PRESS <ENTER> TO CONTINUE:':'',
               'DO YOU ACCEPT THE TERMS OF THIS LICENSE AGREEMENT? (Y/N):':'Y',
               'ENTER AN ABSOLUTE PATH, OR PRESS <ENTER> TO ACCEPT THE DEFAULT :':self.installdir,
               'IS THIS CORRECT? (Y/N):':'Y',
               'Do you wish to have a shortcut installed on your desktop? ->1- Yes 2- No ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::':'2',
               '->1- Single User License 2- Network License ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::':'2',
               'PRESS <ENTER> TO EXIT THE INSTALLER:':'',
               'License server (DEFAULT: ):':self.getCfg('licenseServer'),
               'Port number (optional) (DEFAULT: ):':''}

        noqanda=['Graphical installers are not supported by the VM. The console mode will be used instead...',
                 'Extracting the JRE from the installer archive...',
                 'Launching installer...',
                 "Configuring the installer for this system's environment...",
                 'Unpacking the JRE...',
                 '\[[-|]*']

        runqanda(cmd,qanda,noqanda=noqanda,logall=True,simple=True)

class DIANA(Binary):

    def unpackSrc(self):
        Application.unpackSrc(self)

    def makeInstall(self):

        cmd="./install"

        qanda = {'Where do you want to install Diana ? [/usr1/diana]':self.installdir,
                 '%s does NOT exist, Create ? [Yes/No] '%self.installdir:'Yes',
                 'Do you want a complete installation ? [Yes/No] Y\x08':'Yes',
                 'Cleanup existing directory %s ? [Yes/No] Y\x08'%self.installdir:'Yes'}

        noqanda = ['[0-9]+K bytes required for Installation']

        runqanda(cmd,qanda,noqanda=noqanda,logall=True,simple=True)

class iSight(Application):

    def configure(self):
        txt="""-P installLocation="%s"
-P common.active=true
-P platform.active=true
-P windows.active=false
-P win64.active=false
-P aix.active=false
-P linux.active=false
-P linux64.active=true
-P hpux.active=false
-P solaris.active=false
-P gateway.active=true
-P station.active=false
-P commonLicense.active=false
-P licenseserver.active=false
-P documentation.active=true
-P docsEn.active=true
-P docsJa.active=true
-P components.active=false
-W win3264.bits="win64"
-W platformSelection.platform="linux64"
-W licenseType.licenseType="server"
-W licenseFile.file=""
-W licenseServer.serverName="use_LM_LICENSE_FILE"
-W licenseServer.licensePort=""
-W cprPanel.serverName=
-W cprPanel.serverType=
-W cprPanel.serverPort=
-W acsConfig.acsDrmMode="fiper"
-W acsConfig.rootFilePath=""
-W acsConfig.tempDir="$D(temp)"
-W acsConfig2.security=""
-W acsConfig2.domain=""
-W lsfConfig.bsub=""
-W stationConfig.affinity=""
-W stationConfig.loglevel="info"
-W stationConfig.tempdir="$D(temp)"
-W stationConfig.service=""
-W stationService.logonUser=""
-W stationService.logonPw=""
-W stationService.runUser=""
-W stationPassword.password=
-W startGatewayPanel.startGateway=""
"""%self.installdir

        self.cfgFile=os.path.join(self.builddir,"isight.cfg")
        try:
            f=open(self.cfgFile,"w")
            f.write(txt)
            f.close()
        except Exception,err:
            self.log.error("Failed to write config file %s: %s"%(self.cfgFile,err))

    def make(self):
        pass

    def makeInstall(self):

        cmd="./setuplinux -silent -options %s"%self.cfgFile

        runrun(cmd,logall=True,simple=True)

class JAR(Binary):

    def makeInstall(self):
        for s in self.src:
            shutil.copy(s['path'],self.installdir)

    def makeModuleExtra(self):

        txt=Binary.makeModuleExtra(self)

        for s in self.src:
            self.log.debug('Checking %s...'%s['name'])
            if s['name'].endswith('.jar'):
                self.log.debug('Adding %s to classpath'%s['name'])
                txt+="prepend-path CLASSPATH $root/%s\n"%s['name']

        self.log.debug("JAR.makeModuleExtra returned: %s"%txt)
        return txt