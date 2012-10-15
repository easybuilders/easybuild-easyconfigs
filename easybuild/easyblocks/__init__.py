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
import os
from pkgutil import extend_path

# Extend path so python finds our easyblocks in the subdirectories where they are located
subdirs = [chr(l) for l in range(ord('a'),ord('z')+1)] + ['0']
__path__.extend([os.path.join(__path__[0], subdir) for subdir in subdirs])
# And let python know this is not the only place to look for them,
# so we can have 2 easybuild/easyblock paths in your pythonpath, one for public, one for private easyblocks.
__path__ = extend_path(__path__, __name__)

del subdir, subdirs, l
