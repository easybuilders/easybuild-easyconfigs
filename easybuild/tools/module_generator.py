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
    def __init__(self, application, fake = False):
        self.app = application
        self.fake = fake
        self.filename = None

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
        allPath = os.path.join(base, 'all', self.app.name())
        self.filename = os.path.join(allPath, self.app.installversion)

        # Make symlink in moduleclass category
        classPath = os.path.join(base, self.app.getCfg('moduleclass'), self.app.name())
        classPathFile = os.path.join(classPath, self.app.installversion)

        # Create directories and links
        for directory in [allPath, classPath]:
            if not os.path.isdir(directory):
                try:
                    os.makedirs(directory)
                except OSError, err:
                    log.exception("Couldn't make directory %s: %s" % (directory,err))

        # Make a symlink from classpathFile to self.filename
        try:
            # remove symlink if its there (even if it's broken)
            if os.path.lexists(classPathFile):
                os.remove(classPathFile)
            # remove module file if it's there (it'll be recreated), see Application.makeModule
            if os.path.exists(self.filename):
                os.remove(self.filename)
            os.symlink(self.filename, classPathFile)
        except OSError,err:
            log.exception("Failed to create symlink from %s to %s: %s" % (classPathFile, self.filename, err))

    def getDescription(self, conflict=True):
        """
        Generate a description.
        """
        description = "%s - Homepage: %s" % (self.app.getCfg('description'), self.app.getCfg('homepage'))

        txt = "#%Module\n"
        txt += """
proc ModulesHelp { } {
    puts stderr {   %(description)s
}
}

module-whatis {%(description)s}

set root    %(installdir)s

""" % {'description': description, 'installdir': self.app.installdir}

        if self.app.getCfg('moduleloadnoconflict'):
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
