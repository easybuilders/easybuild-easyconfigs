##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild support for building and installing WIEN2k, implemented as an easyblock
"""

import fileinput
import os
import re
import sys
from distutils.version import LooseVersion

import easybuild.tools.toolkit as toolkit
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, run_cmd_qa
from easybuild.tools.modules import get_software_root, get_software_version


class EB_WIEN2k(Application):
    """Support for building/installing WIEN2k."""

    def __init__(self,*args,**kwargs):
        """Enable building in install dir."""
        Application.__init__(self, *args, **kwargs)

        self.build_in_installdir = True

    def unpack_src(self):
        """Unpack WIEN2k sources using gunzip and provided expand_lapw script."""
        Application.unpack_src(self)

        cmd = "gunzip *gz"
        run_cmd(cmd, log_all=True, simple=True)

        cmd = "./expand_lapw"
        qanda = {'continue (y/n)': 'y'}
        no_qa = [
                 'tar -xf.*',
                 '.*copied and linked.*'
                 ]

        run_cmd_qa(cmd, qanda, no_qa=no_qa, log_all=True, simple=True)
    
    def configure(self):
        """Configure WIEN2k build by patching siteconfig_lapw script and running it."""

        self.cfgscript = "siteconfig_lapw"

        # patch config file first
        fftwver = ''
        fftwfullversion = get_software_version('FFTW')
        if fftwfullversion:
            if LooseVersion(fftwfullversion) >= LooseVersion('3'):
                fftwver = fftwfullversion.split('.')[0]
                self.log.debug('fftwver: %s' % fftwver)
            else:
                self.log.debug('empty fftwver')
        else:
            self.log.error("FFTW module not loaded?")

        # toolkit-dependent values
        comp_answer = None
        if self.toolkit().comp_family() == toolkit.INTEL:
            static_flag = "-static-intel"
            if LooseVersion(get_software_version("icc")) >= LooseVersion("2011"):
                comp_answer = 'I'  # Linux (Intel ifort 12.0 compiler + mkl )
            else:
                comp_answer = "K1"  # Linux (Intel ifort 11.1 compiler + mkl )

        elif self.toolkit().comp_family() == toolkit.GCC:
            static_flag = "-static"
            comp_answer = 'V'  # Linux (gfortran compiler + gotolib)

        else:
            self.log.error("Failed to determine toolkit-dependent answers.")

        d = {
             'FC': '%s %s'%(os.getenv('F90'), os.getenv('FFLAGS')),
             'MPF': "%s %s"%(os.getenv('MPIF90'), os.getenv('FFLAGS')),
             'CC': os.getenv('CC'),
             'LDFLAGS': '$(FOPT) %s %s' % (os.getenv('LDFLAGS'), static_flag),
             'R_LIBS': '$(LIBSCALAPACK) %s -lpthread' % self.toolkit().get_openmp_flag(),
             'RP_LIBS' :'-L%(fftwroot)s/lib/ -lfftw%(fftwver)s_mpi ' \
                        '-lfftw%(fftwver)s $(LIBSCALAPACK)' % {
                                                               'fftwroot': get_software_root('FFTW'),
                                                               'fftwver': fftwver
                                                               },
             'MPIRUN': ''
            }

        for line in fileinput.input(self.cfgscript, inplace=1, backup='.orig'):
            # set config parameters
            for (k,v) in d.items():
                regexp = re.compile('^([a-z0-9]+):%s:.*' % k)
                res = regexp.search(line)
                if res:
                    # we need to exclude the lines with 'current', otherwise we break the script
                    if not res.group(1) == "current":
                        line = regexp.sub('\\1:%s:%s' % (k, v), line)
            # avoid exit code > 0 at end of configuration
            line = re.sub('(\s+)exit 1', '\\1exit 0', line)
            sys.stdout.write(line)

        # set correct compilers
        os.putenv('bin', os.getcwd())

        dc = {
              'COMPILERC': os.getenv('CC'),
              'COMPILER': os.getenv('F90'),
              'COMPILERP': os.getenv('MPIF90'),
             }

        for (k,v) in dc.items():
            f = open(k,"w")
            f.write(v)
            f.close()

        # configure with patched configure script
        self.log.debug('%s part I (configure)' % self.cfgscript)

        cmd = "./%s" % self.cfgscript
        qanda = {
                 'Press RETURN to continue': '',
                 'compiler) Selection:': comp_answer,
                 'R R_LIB (LAPACK+BLAS): -llapack_lapw -lgoto -llapack_lapw ' \
                    'S Save and Quit To change an item select option. Selection:': 'R',
                 'Your compiler:': '',
                 'Hit Enter to continue': '',
                 'Shared Memory Architecture? (y/n):': 'n',
                 'Remote shell (default is ssh) =': '',
                 'and you need to know details about your installed  mpi ..) (y/n)': 'y',
                 'Recommended setting for parallel f90 compiler: mpiifort ' \
                        'Current selection: Your compiler:': os.getenv('MPIF90'),
                 'Q to quit Selection:': 'Q',
                 'A Compile all programs (suggested) Q Quit Selection:': 'Q',
                 ' Please enter the full path of the perl program: ': '',
                 'continue or stop (c/s)': 'c',
                 'Real libraries=': "-L%s %s" % (os.getenv('LAPACK_LIB_DIR'), os.getenv('LIBLAPACK')),
                 '(like taskset -c). Enter N / your_specific_command:': 'N',
                 'If you are using mpi2 set MPI_REMOTE to 0  Set MPI_REMOTE to 0 / 1:': '0',
                 'Do you have MPI and Scalapack installed and intend to run ' \
                    'finegrained parallel? (This is usefull only for BIG cases ' \
                    '(50 atoms and more / unit cell) and you need to know details ' \
                    'about your installed  mpi and fftw ) (y/n)': 'y',
                }

        no_qa = [
                 'You have the following mkl libraries in %s :' % os.getenv('MKLROOT'),
                 "%s[ \t]*.*"%os.getenv('MPIF90'),
                 "%s[ \t]*.*"%os.getenv('F90'),
                 "%s[ \t]*.*"%os.getenv('CC'),
                 ".*SRC_.*"
                 ]

        std_qa = {
                  'S Save and Quit To change an item select option. Selection:': 'S',
                 }

        run_cmd_qa(cmd, qanda, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

    def make(self):
        """Build WIEN2k by running siteconfig_lapw script again."""

        self.log.debug('%s part II (make)' % self.cfgscript)

        cmd = "./%s" % self.cfgscript

        qanda = {
                 'L Perl path (if not in /usr/bin/perl) Q Quit Selection:': 'R',
                 'A Compile all programs S Select program Q Quit Selection:': 'A',
                 'Press RETURN to continue': '\nQ', # also answer on first qanda pattern with 'Q' to quit
                 ' Please enter the full path of the perl program: ':''}
        no_qa = [
                 "%s[ \t]*.*" % os.getenv('MPIF90'),
                 "%s[ \t]*.*" % os.getenv('F90'),
                 "%s[ \t]*.*" % os.getenv('CC'),
                 ".*SRC_.*",
                 ".*: warning .*"
                 ]
    
        self.log.debug("no_qa for %s: %s" % (cmd, no_qa))
        run_cmd_qa(cmd, qanda, no_qa=no_qa, log_all=True, simple=True)

    def make_install(self):
        """Fix broken symlinks after build/installation."""
        # fix broken symlink
        os.remove(os.path.join(self.installdir, "SRC_w2web", "htdocs", "usersguide"))
        os.symlink(os.path.join(self.installdir, "SRC_usersguide_html"),
                   os.path.join(self.installdir, "SRC_w2web","htdocs", "usersguide"))

    def sanitycheck(self):
        """Custom sanity check for WIEN2k."""

        if not self.getcfg('sanityCheckPaths'):
            lapwfiles = []
            for suffix in ["0","0_mpi","1","1_mpi","1c","1c_mpi","2","2_mpi","2c","2c_mpi",
                           "3","3c","5","5c","7","7c","dm","dmc","so"]:
                p = os.path.join(self.installdir, "lapw%s" % suffix)
                lapwfiles.append(p)

            self.setcfg('sanityCheckPaths',{'files': lapwfiles,
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

    def make_module_extra(self):
        """Set WIENROOT environment variable, and correctly prepend PATH."""

        txt = Application.make_module_extra(self)

        txt += self.moduleGenerator.setEnvironment("WIENROOT", "$root")
        txt += self.moduleGenerator.prependPaths("PATH", "$root")

        return txt
