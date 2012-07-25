##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
Generating module files.
"""
import os

from easybuild.tools.build_log import getLog
from easybuild.tools.config import installPath

log = getLog('moduleGenerator')

class ModuleGenerator:
    """
    Class for generating module files.
    """
    def __init__(self, application, fake=False):
        self.app = application
        self.fake = fake
        self.filename = None
        self.module_path = None

    def createFiles(self):
        """
        Creates the absolute filename for the module.
        """
        base = installPath('mod')

        # Fake mode: set installpath to builddir
        if self.fake:
            log.debug("Fake mode: using %s (instead of %s)" % (self.app.builddir, base))
            base = self.app.builddir

        # Real file goes in 'all' category
        self.module_path = os.path.join(base, 'all')
        self.filename = os.path.join(self.module_path, self.app.name(), self.app.installversion)

        # Make symlink in moduleclass category
        classPath = os.path.join(base, self.app.getcfg('moduleclass'), self.app.name())
        classPathFile = os.path.join(classPath, self.app.installversion)

        # Create directories and links
        for directory in [os.path.dirname(x) for x in [self.filename, classPathFile]]:
            if not os.path.isdir(directory):
                try:
                    os.makedirs(directory)
                except OSError, err:
                    log.exception("Couldn't make directory %s: %s" % (directory, err))

        # Make a symlink from classpathFile to self.filename
        try:
            # remove symlink if its there (even if it's broken)
            if os.path.lexists(classPathFile):
                os.remove(classPathFile)
            # remove module file if it's there (it'll be recreated), see Application.makeModule
            if os.path.exists(self.filename):
                os.remove(self.filename)
            os.symlink(self.filename, classPathFile)
        except OSError, err:
            log.exception("Failed to create symlink from %s to %s: %s" % (classPathFile, self.filename, err))

    def getDescription(self, conflict=True):
        """
        Generate a description.
        """
        description = "%s - Homepage: %s" % (self.app.getcfg('description'), self.app.getcfg('homepage'))

        txt = "#%Module\n"
        txt += """
proc ModulesHelp { } {
    puts stderr {   %(description)s
}
}

module-whatis {%(description)s}

set root    %(installdir)s

""" % {'description': description, 'installdir': self.app.installdir}

        if self.app.getcfg('moduleloadnoconflict'):
            txt += """
if { ![is-loaded %(name)s/%(version)s] } {
    if { [is-loaded %(name)s] } {
        module unload %(name)s
    }
}

""" % {'name': self.app.name(), 'version': self.app.version()}

        elif conflict:
            txt += "conflict    %s\n" % self.app.name()

        return txt

    def loadModule(self, name, version):
        """
        Generate load statements for module with name and version.
        """
        return """
if { ![is-loaded %(name)s/%(version)s] } {
    module load %(name)s/%(version)s
}
""" % {'name': name, 'version': version}

    def unloadModule(self, name, version):
        """
        Generate unload statements for module with name and version.
        """
        return """
if { ![is-loaded %(name)s/%(version)s] } {
    if { [is-loaded %(name)s] } {
        module unload %(name)s
    }
}
""" % {'name': name, 'version': version}

    def prependPaths(self, key, paths):
        """
        Generate prepend-path statements for the given list of paths.
        """
        fullInstallPath = os.path.abspath(self.app.installdir) + '/'
        template = "prepend-path\t%s\t\t$root/%s\n" # $root = installdir

        statements = [template % (key, p.replace(fullInstallPath, '')) for p in paths]
        return ''.join(statements)

    def setEnvironment(self, key, value):
        """
        Generate setenv statement for the given key/value pair.
        """
        return "setenv\t%s\t\t%s\n" % (key, value)
