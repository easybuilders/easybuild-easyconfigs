##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
EasyBuild support for building and installing binutils, implemented as an easyblock

@author: Kenneth Hoste (HPC-UGent)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.modules import get_software_libdir, get_software_root
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_binutils(ConfigureMake):
    """Support for building/installing binutils."""

    def configure_step(self):
        """Custom configuration procedure for binutils: statically link to zlib, configure options."""

        libdirs = ['/lib', '/lib64', '/usr/lib', '/usr/lib64', '/usr/lib/x86_64-linux-gnu/']
        libs = ' '.join('-Wl,-rpath=%s' % libdir for libdir in libdirs if os.path.exists(libdir))

        # statically link to zlib if it is a (build) dependency
        zlibroot = get_software_root('zlib')
        if zlibroot:
            #libs += ' ' + os.path.join(zlibroot, 'lib', 'zlib.a')
            libs += ' ' + os.path.join(zlibroot, get_software_libdir('zlib'), 'libz.a')

        self.cfg.update('preconfigopts', "env LIBS='%s'" % libs)
        self.cfg.update('prebuildopts', "env LIBS='%s'" % libs)

        # use correct sysroot (no cross-compiling, use system libraries)
        self.cfg.update('configopts', '--with-sysroot=/')

        # build both static and shared libraries
        self.cfg.update('configopts', "--enable-shared --enable-static")

        # enable gold linker with plugin support, use ld as default linker
        self.cfg.update('configopts', "--enable-gold --enable-plugins --enable-ld=default")

        # complete configuration with configure_method of parent
        super(EB_binutils, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for binutils."""
        binaries = ['addr2line', 'ar', 'as', 'c++filt', 'elfedit', 'gprof', 'ld', 'ld.bfd', 'ld.gold', 'nm',
                    'objcopy', 'objdump', 'ranlib', 'readelf', 'size', 'strings', 'strip']
        headers = ['ansidecl.h', 'bfd.h', 'bfdlink.h', 'dis-asm.h', 'symcat.h']
        libs = ['bfd', 'opcodes']
        custom_paths = {
            'files': [os.path.join('bin', b) for b in binaries] +
                     [os.path.join('lib', 'lib%s.%s' % (l, ext)) for l in libs for ext in ['a', get_shared_lib_ext()]] +
                     [os.path.join('include', h) for h in headers],
            'dirs': [],
        }
        super(EB_binutils, self).sanity_check_step(custom_paths=custom_paths)
