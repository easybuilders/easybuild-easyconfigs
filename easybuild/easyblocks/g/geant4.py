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
Geant4 support, implemented as an easyblock.

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import shutil
import re
from distutils.version import LooseVersion

import easybuild.tools.environment as env
from easybuild.framework.easyconfig import CUSTOM
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd, run_cmd_qa
from easybuild.tools.filetools import mkdir

class EB_Geant4(CMakeMake):
    """
    Support for building Geant4.
    Note: Geant4 moved to a CMake-based build system as of version 9.4.
    """

    @staticmethod
    def extra_options():
        """
        Define extra options needed by Geant4
        """
        extra_vars = {
            'G4ABLAVersion': [None, "G4ABLA version", CUSTOM],
            'G4NDLVersion': [None, "G4NDL version", CUSTOM],
            'G4EMLOWVersion': [None, "G4EMLOW version", CUSTOM],
            'PhotonEvaporationVersion': [None, "PhotonEvaporation version", CUSTOM],
            'G4RadioactiveDecayVersion': [None, "G4RadioactiveDecay version", CUSTOM],
        }
        return CMakeMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for Geant4."""
        super(EB_Geant4, self).__init__(*args, **kwargs)
        self.g4system = 'UNKNOWN'
        self.datadst = 'UNKNOWN'

    def configure_step(self):
        """
        Configure Geant4 build, either via CMake for versions more recent than 9.4,
        or using an interactive configuration procedure otherwise.
        """

        # Geant4 switched to a CMake build system in version 9.4
        if LooseVersion(self.version) >= LooseVersion("9.4"):
            mkdir('configdir')
            os.chdir('configdir')
            super(EB_Geant4, self).configure_step(srcdir="..")

        else:
            pwd = self.cfg['start_dir']
            dst = self.installdir
            clhepdir = get_software_root('CLHEP')
            cmd = "%s/Configure -E -build" % pwd

            self.qanda = {
                # questions and answers for version 9.1.p03
                "There exists a config.sh file. Shall I use it to set the defaults? [y]": "n",
                "Would you like to see the instructions? [n]": "",
                "[Type carriage return to continue]": "",
                "Definition of G4SYSTEM variable is Linux-g++. That stands for: 1) OS : Linux" \
                    "2) Compiler : g++ To modify default settings, select number above (e.g. 2) " \
                    "[Press [Enter] for default settings]": "2",
                "Which C++ compiler? [g++]": "$(GPP)",
                "Confirm your selection or set recommended 'g++'! [*]": "",
                "Definition of G4SYSTEM variable is Linux-icc. That stands for: 1) OS : Linux 2)" \
                    "Compiler : icc To modify default settings, select number above (e.g. 2) " \
                    "[Press [Enter] for default settings]": "",
                "Do you expect to run these scripts and binaries on multiple machines? [n]": "y",
                "Where is Geant4 source installed? [%s]" % pwd: "",
                "Specify the path where Geant4 libraries and source files should be installed." \
                    " [%s]" % pwd: dst,
                "Do you want to copy all Geant4 headers in one directory? [n]": "y",
                "Please, specify default directory where ALL the Geant4 data is installed:" \
                    "G4LEVELGAMMADATA: %(pwd)s/data/PhotonEvaporation2.0 G4RADIOACTIVEDATA: " \
                    "%(pwd)s/data/RadioactiveDecay3.2 G4LEDATA: %(pwd)s/data/G4EMLOW5.1 G4NEUTRONHPDATA:    " \
                    "%(pwd)s/data/G4NDL3.12 G4ABLADATA: %(pwd)s/data/G4ABLA3.0 You will be asked about " \
                    "customizing these next. [%(pwd)s/data]" % {'pwd': pwd}: "%s/data" % dst,
                "Directory %s/data doesn't exist. Use that name anyway? [n]" % dst: "y",
                "Please, specify default directory where the Geant4 data is installed: " \
                    "1) G4LEVELGAMMADATA: %(dst)s/data/PhotonEvaporation2.0 2) G4RADIOACTIVEDATA: " \
                    "%(dst)s/data/RadioactiveDecay3.2 3) G4LEDATA: %(dst)s/data/G4EMLOW5.1 4) G4NEUTRONHPDATA: " \
                    "%(dst)s/data/G4NDL3.12 5) G4ABLADATA: %(dst)s/data/G4ABLA3.0 To modify default settings, " \
                    "select number above (e.g. 2) [Press [Enter] for default settings]" % {'dst': dst}: "",
                "Please, specify where CLHEP is installed: CLHEP_BASE_DIR: ": clhepdir,
                "Please, specify where CLHEP is installed: CLHEP_BASE_DIR: [%s]" % clhepdir: "",
                "You can customize paths and library name of you CLHEP installation: 1) CLHEP_INCLUDE_DIR: " \
                    "%(clhepdir)s/include 2) CLHEP_LIB_DIR: %(clhepdir)s/lib 3) CLHEP_LIB: CLHEP To modify " \
                    "default settings, select number above (e.g. 2) [Press [Enter] for default settings]" % 
                    {'clhepdir': clhepdir}: "",
                "By default 'static' (.a) libraries are built. Do you want to build 'shared' (.so) " \
                    "libraries? [n]": "y",
                "You selected to build 'shared' (.so) libraries. Do you want to build 'static' (.a) " \
                    "libraries too? [n]": "y",
                "Do you want to build 'global' compound libraries? [n]": "",
                "Do you want to compile libraries in DEBUG mode (-g)? [n]": "",
                "G4UI_NONE If this variable is set, no UI sessions nor any UI libraries are built. " \
                    "This can be useful when running a pure batch job or in a user framework having its own " \
                    "UI system. Do you want to set this variable ? [n]": "",
                "G4UI_BUILD_XAW_SESSION G4UI_USE_XAW Specifies to include and use the XAW interfaces in " \
                    "the application to be built. The XAW (X11 Athena Widget set) extensions are required to " \
                    "activate and build this driver. [n]": "",
                "G4UI_BUILD_XM_SESSION G4UI_USE_XM Specifies to include and use the XM Motif based user " \
                    "interfaces. The XM Motif extensions are required to activate and build this driver. [n]": "",
                "G4VIS_NONE If this variable is set, no visualization drivers will be built or used. Do " \
                    "you want to set this variable ? [n]": "n",
                "G4VIS_BUILD_OPENGLX_DRIVER G4VIS_USE_OPENGLX It is an interface to the de facto standard " \
                    "3D graphics library, OpenGL. It is well suited for real-time fast visualization and " \
                    "prototyping. The X11 version of the OpenGL libraries is required. [n]": "",
                "G4VIS_BUILD_OPENGLXM_DRIVER G4VIS_USE_OPENGLXM It is an interface to the de facto " \
                    "standard 3D graphics library, OpenGL. It is well suited for real-time fast visualization " \
                    "and prototyping. The X11 version of the OpenGL libraries and the Motif Xm extension is " \
                    "required. [n]": "",
                "G4VIS_BUILD_DAWN_DRIVER G4VIS_USE_DAWN DAWN drivers are interfaces to the Fukui Renderer " \
                    "DAWN. DAWN is a vectorized 3D PostScript processor suited to prepare technical high " \
                    "quality outputs for presentation and/or documentation. [n]": "",
                "G4VIS_BUILD_OIX_DRIVER G4VIS_USE_OIX The OpenInventor driver is based on OpenInventor tech" \
                    "nology for scientific visualization. The X11 version of OpenInventor is required. [n]": "",
                "G4VIS_BUILD_RAYTRACERX_DRIVER G4VIS_USE_RAYTRACERX Allows for interactive ray-tracing " \
                    "graphics through X11. The X11 package is required. [n]": "",
                "G4VIS_BUILD_VRML_DRIVER G4VIS_USE_VRML These driver generate VRML files, which describe " \
                    "3D scenes to be visualized with a proper VRML viewer. [n]": "",
                "G4LIB_BUILD_GDML Setting this variable will enable building of the GDML plugin module " \
                    "embedded in Geant4 for detector description persistency. It requires your system to have " \
                    "the XercesC library and headers installed. Do you want to set this variable? [n]": "",
                "G4LIB_BUILD_G3TOG4 The utility module 'g3tog4' will be built by setting this variable. " \
                    "NOTE: it requires a valid FORTRAN compiler to be installed on your system and the " \
                    "'cernlib' command in the path, in order to build the ancillary tools! Do you want to " \
                    "build 'g3tog4' ? [n]": "",
                "G4LIB_BUILD_ZLIB Do you want to activate compression for output files generated by the " \
                    "HepRep visualization driver? [n]": "y",
                "G4ANALYSIS_USE Activates the configuration setup for allowing plugins to analysis tools " \
                    "based on AIDA (Astract Interfaces for Data Analysis). In order to use AIDA features and " \
                    "compliant analysis tools, the proper environment for these tools will have to be set " \
                    "(see documentation for the specific analysis tools). [n]": "",
                "Press [Enter] to start installation or use a shell escape to edit config.sh: ": "",
                # extra questions and answers for version 9.2.p03
                "Directory %s doesn't exist. Use that name anyway? [n]" % dst: "y",
                "Specify the path where the Geant4 data libraries PhotonEvaporation%s " \
                    "RadioactiveDecay%s G4EMLOW%s G4NDL%s G4ABLA%s are " \
                    "installed. For now, a flat directory structure is assumed, and this can be customized " \
                    "at the next step if needed. [%s/data]" % (self.cfg['PhotonEvaporationVersion'],
                            self.cfg['G4RadioactiveDecayVersion'],
                            self.cfg['G4EMLOWVersion'],
                            self.cfg['G4NDLVersion'],
                            self.cfg['G4ABLAVersion'],
                            pwd
                            ): "%s/data" % dst,
                "Please enter 1) Another path to search in 2) 'f' to force the use of the path " \
                    "you entered previously (the data libraries are not needed to build Geant4, but " \
                    "are needed to run applications later). 3) 'c' to customize the data paths, e.g. " \
                    "if you have the data libraries installed in different locations. [f]": "",
                    "G4UI_BUILD_QT_SESSION G4UI_USE_QT Setting these variables will enable the building " \
                    "of the G4 Qt based user interface module and the use of this module in your " \
                    "applications respectively. The Qt3 or Qt4 headers, libraries and moc application are " \
                    "required to enable the building of this module. Do you want to enable build and use of " \
                    "this module? [n]": "",
                # extra questions and answers for version 9.4.po1
                "What is the path to the Geant4 source tree? [%s]" % pwd: "",
                "Where should Geant4 be installed? [%s]" % pwd: dst,
                "Do you want to install all Geant4 headers in one directory? [n]": "y",
                "Do you want to build shared libraries? [y]": "",
                "Do you want to build static libraries too? [n]": "",
                "Do you want to build global libraries? [y]": "",
                "Do you want to build granular libraries as well? [n]": "",
                "Do you want to build libraries with debugging information? [n]": "",
                "Specify the path where the Geant4 data libraries are installed: [%s/data]" % pwd: "%s/data" % dst,
                "How many parallel jobs should make launch? [1]": "%s" % self.cfg['parallel'],
                "Please enter 1) Another path to search in 2) 'f' to force the use of the path you entered " \
                    "previously (the data libraries are NOT needed to build Geant4, but are needed to run " \
                    "applications later). 3) 'c' to customize the data paths, e.g. if you have the data " \
                    "libraries installed in different locations. [f]": "",
                "Enable building of User Interface (UI) modules? [y]": "",
                "Enable building of the XAW (X11 Athena Widget set) UI module? [n]": "",
                "Enable building of the X11-Motif (Xm) UI module? [n]": "",
                "Enable building of the Qt UI module? [n]": "",
                "Enable building of visualization drivers? [y]": "n",
                "Enable the Geometry Description Markup Language (GDML) module? [n]": "",
                "Enable build of the g3tog4 utility module? [n]": "",
                "Enable internal zlib compression for HepRep visualization? [n] ": "",
            }

            self.noqanda = [
                r"Compiling\s+.*?\s+\.\.\.",
                r"Making\s+dependency\s+for\s+file\s+.*?\s+\.\.\.",
                r"Making\s+libname\.map\s+starter\s+file\s+\.\.\.",
                r"Making\s+libname\.map\s+\.\.\.",
                r"Reading\s+library\s+get_name\s+map\s+file\s*\.\.\.",
                r"Reading\s+dependency\s+files\s*\.\.\.",
                r"Creating\s+shared\s+library\s+.*?\s+\.\.\.",
            ]

            run_cmd_qa(cmd, self.qanda, self.noqanda, log_all=True, simple=True)

            # determining self.g4system
            try:
                scriptdirbase = os.path.join(pwd, '.config', 'bin')
                filelist = os.listdir(scriptdirbase)
            except OSError, err:
                raise EasyBuildError("Failed to determine self.g4system: %s", err)
    
            if len(filelist) != 1:
                raise EasyBuildError("Exactly one directory is expected in %s; found back: %s", scriptdirbase, filelist)
            else:
                self.g4system = filelist[0]
    
            self.scriptdir = os.path.join(scriptdirbase, self.g4system)
            if not os.path.isdir(self.scriptdir):
                raise EasyBuildError("Something went wrong. Dir: %s doesn't exist.", self.scriptdir)
            self.log.info("The directory containing several important scripts to be copied was found: %s" % self.scriptdir)

            # copying config.sh to pwd
            try:
                self.log.info("copying config.sh to %s" % pwd)
                shutil.copy2(os.path.join(self.scriptdir, 'config.sh'), pwd)
            except IOError, err:
                raise EasyBuildError("Failed to copy config.sh to %s", pwd)

            # creating several scripts containing environment variables
            cmd = "%s/Configure -S -f config.sh -D g4conf=%s -D abssrc=%s" % (pwd, self.scriptdir, pwd)
            run_cmd(cmd, log_all=True, simple=True)

    def build_step(self):
        """Build Geant4."""
        if LooseVersion(self.version) >= LooseVersion("9.4"):
            super(EB_Geant4, self).build_step()
        else:
            pwd = self.cfg['start_dir']
            cmd = "%s/Configure -build" % pwd
            run_cmd_qa(cmd, self.qanda, no_qa=self.noqanda, log_all=True, simple=True)

    def install_step(self):
        """Install Geant4."""

        if LooseVersion(self.version) >= LooseVersion("9.4"):
            super(EB_Geant4, self).install_step()
            self.datadst = os.path.join(self.installdir,
                                        'share',
                                        '%s-%s' % (self.name, self.version.replace("p0", "")),
                                        'data',
                                        )

            if LooseVersion(self.version) < LooseVersion("9.5"):
                version_parts = self.version.split('.')
                name = 'geant4-%s' % '.'.join(version_parts[:2] + [version_parts[-1][-1]])
                for (source, target) in [("%s.sh" % name, "env.sh"), ("%s.csh" % name, "env.csh")]:
                    source = os.path.join(self.installdir, 'share', name, 'config', source)
                    target = os.path.join(self.installdir, target)
                    try:
                        os.symlink(source, target)
                    except OSError, err:
                        raise EasyBuildError("Failed to symlink %s to %s: %s", source, target, err)
        else:
            pwd = self.cfg['start_dir']

            try:
                datasrc = os.path.join(pwd, '..')
                self.datadst = os.path.join(self.installdir, 'data')
                os.mkdir(self.datadst)
            except OSError, err:
                raise EasyBuildError("Failed to create data destination file %s: %s", self.datadst, err)

            datalist = ['G4ABLA%s' % self.cfg['G4ABLAVersion'],
                        'G4EMLOW%s' % self.cfg['G4EMLOWVersion'],
                        'G4NDL%s' % self.cfg['G4NDLVersion'],
                        'PhotonEvaporation%s' % self.cfg['PhotonEvaporationVersion'],
                        'RadioactiveDecay%s' % self.cfg['G4RadioactiveDecayVersion'],
                       ]
            try:
                for dat in datalist:
                    self.log.info("Copying %s to %s" % (dat, self.datadst))
                    shutil.copytree(os.path.join(datasrc, dat), os.path.join(self.datadst, dat))
            except IOError, err:
                raise EasyBuildError("Something went wrong during data copying (%s) to %s: %s", dat, self.datadst, err)

            try:
                for fil in ['config', 'environments', 'examples']:
                    self.log.info("Copying %s to %s" % (fil, self.installdir))
                    if not os.path.exists(os.path.join(pwd, fil)):
                        raise EasyBuildError("No such file or directory: %s", fil)
                    if os.path.isdir(os.path.join(pwd, fil)):
                        shutil.copytree(os.path.join(pwd, fil), os.path.join(self.installdir, fil))
                    elif os.path.isfile(os.path.join(pwd, fil)):
                        shutil.copy2(os.path.join(pwd, fil), os.path.join(self.installdir, fil))
            except IOError, err:
                raise EasyBuildError("Something went wrong during copying of %s to %s: %s", fil, self.installdir, err)

            try:
                for fil in ['config.sh', 'env.sh', 'env.csh']:
                    self.log.info("Copying %s to %s" % (fil, self.installdir))
                    if not os.path.exists(os.path.join(self.scriptdir, fil)):
                        raise EasyBuildError("No such file or directory: %s", fil)
                    if os.path.isdir(os.path.join(self.scriptdir, fil)):
                        shutil.copytree(os.path.join(self.scriptdir, fil), os.path.join(self.installdir, fil))
                    elif os.path.isfile(os.path.join(self.scriptdir, fil)):
                        shutil.copy2(os.path.join(self.scriptdir, fil), os.path.join(self.installdir, fil))
            except IOError, err:
                raise EasyBuildError("Something went wrong during copying of (%s) to %s: %s", fil, self.installdir, err)

            cmd = "%(pwd)s/Configure -f %(pwd)s/config.sh -d -install" % {'pwd': pwd}
            run_cmd(cmd, log_all=True, simple=True)

            mpiuidir = os.path.join(self.installdir, "examples/extended/parallel/MPI/mpi_interface")
            os.chdir(mpiuidir)

            # tweak config file as needed
            f = open("G4MPI.gmk", "r")
            G4MPItxt = f.read()
            f.close()

            root_re = re.compile("(.*G4MPIROOT\s+=\s+).*", re.MULTILINE)
            cxx_re = re.compile("(.*CXX\s+:=\s+).*", re.MULTILINE)
            cppflags_re = re.compile("(.*CPPFLAGS\s+\+=\s+.*)", re.MULTILINE)

            G4MPItxt = root_re.sub(r"\1%s/intel64" % get_software_root('IMPI'), G4MPItxt)
            G4MPItxt = cxx_re.sub(r"\1mpicxx -cxx=icpc", G4MPItxt)
            G4MPItxt = cppflags_re.sub(r"\1 -I$(G4INCLUDE) -I%s)/include" % get_software_root('CLHEP'), G4MPItxt)

            self.log.debug("contents of G4MPI.gmk: %s" % G4MPItxt)

            shutil.copyfile("G4MPI.gmk", "G4MPI.gmk.ORIG")
            f = open("G4MPI.gmk", "w")
            f.write(G4MPItxt)
            f.close()

            # make sure the required environment variables are there
            env.setvar("G4INSTALL", self.installdir)
            env.setvar("G4SYSTEM", self.g4system)
            env.setvar("G4LIB", "%s/lib/geant4/" % self.installdir)
            env.setvar("G4INCLUDE", "%s/include/geant4/" % self.installdir)

            run_cmd("make", log_all=True, simple=True)
            run_cmd("make includes", log_all=True, simple=True)

    def make_module_extra(self):
        """Define Geant4-specific environment variables in module file."""
        g4version = '.'.join(self.version.split('.')[:2])

        txt = super(EB_Geant4, self).make_module_extra()
        txt += self.module_generator.set_environment('G4INSTALL', self.installdir)
        #no longer needed in > 9.5, but leave it there for now.
        txt += self.module_generator.set_environment('G4VERSION', g4version)

        incdir = os.path.join(self.installdir, 'include')
        libdir = os.path.join(self.installdir, 'lib')
        if LooseVersion(self.version) >= LooseVersion("9.5"):
            txt += self.module_generator.set_environment('G4INCLUDE', os.path.join(incdir, 'Geant4'))
            txt += self.module_generator.set_environment('G4LIB', os.path.join(self.installdir, 'lib64', 'Geant4'))
        elif LooseVersion(self.version) >= LooseVersion("9.4"):
            txt += self.module_generator.set_environment('G4INCLUDE', os.path.join(incdir, 'geant4'))
            txt += self.module_generator.set_environment('G4LIB', libdir)
        else:
            txt += self.module_generator.set_environment('G4INCLUDE', os.path.join(incdir, 'geant4'))
            txt += self.module_generator.set_environment('G4LIB', os.path.join(libdir, 'geant4'))
            txt += self.module_generator.set_environment('G4SYSTEM', self.g4system)
            txt += self.module_generator.set_environment('G4ABLADATA',
                                                        "%s/G4ABLA%s" % (self.datadst, self.cfg['G4ABLAVersion']))

        txt += self.module_generator.set_environment('G4LEVELGAMMADATA',
                                                    "%s/PhotonEvaporation%s" % (self.datadst,
                                                                                self.cfg['PhotonEvaporationVersion']))
        txt += self.module_generator.set_environment('G4RADIOACTIVEDATA',
                                                    "%s/RadioactiveDecay%s" % (self.datadst,
                                                                               self.cfg['G4RadioactiveDecayVersion']))
        txt += self.module_generator.set_environment('G4LEDATA',
                                                    "%s/G4EMLOW%s" % (self.datadst, self.cfg['G4EMLOWVersion']))
        txt += self.module_generator.set_environment('G4NEUTRONHPDATA', "%s/G4NDL%s" % (self.datadst,
                                                                                       self.cfg['G4NDLVersion']))

        return txt

    def sanity_check_step(self):
        """
        Custom sanity check for Geant4
        """
        bin_files = ["bin/geant4-config"]
        if LooseVersion(self.version) >= LooseVersion("9.5"):
            bin_files.extend(["bin/geant4.sh", "bin/geant4.csh"])
            lib_files = ["lib64/libG4%s.so" % x for x in ['analysis', 'event', 'GMocren', 'materials',
                                                          'persistency', 'readout', 'Tree', 'VRML']]
            include_dir = 'include/Geant4'
        else:
            # paths for v9.4, untested for prior versions
            lib_files = ["lib/libG4%s.so" % x for x in ['event', 'GMocren', 'materials', 'persistency',
                                                        'readout', 'Tree', 'VRML']]
            include_dir = 'include/geant4'

        custom_paths = {
            'files': bin_files + lib_files,
            'dirs': [include_dir],
        }

        super(EB_Geant4, self).sanity_check_step(custom_paths)
