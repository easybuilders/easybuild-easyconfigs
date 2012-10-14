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
Generating module files.
"""
import os
import shutil
import tempfile

from easybuild.tools.build_log import get_log
from easybuild.tools.config import install_path


log = get_log('moduleGenerator')

# general module class
GENERAL_CLASS = 'all'


class ModuleGenerator(object):
    """
    Class for generating module files.
    """
    def __init__(self, application, fake=False):
        self.app = application
        self.fake = fake
        self.filename = None
        self.tmpdir = None

    def create_files(self):
        """
        Creates the absolute filename for the module.
        """
        module_path = install_path('mod')

        # Fake mode: set installpath to temporary dir
        if self.fake:
            self.tmpdir = tempfile.mkdtemp()
            log.debug("Fake mode: using %s (instead of %s)" % (self.tmpdir, module_path))
            module_path = self.tmpdir

        # Real file goes in 'all' category
        self.filename = os.path.join(module_path, GENERAL_CLASS, self.app.name, self.app.get_installversion())

        # Make symlink in moduleclass category
        classPath = os.path.join(module_path, self.app.cfg['moduleclass'], self.app.name)
        classPathFile = os.path.join(classPath, self.app.get_installversion())

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
            # remove module file if it's there (it'll be recreated), see Application.make_module
            if os.path.exists(self.filename):
                os.remove(self.filename)
            os.symlink(self.filename, classPathFile)
        except OSError, err:
            log.exception("Failed to create symlink from %s to %s: %s" % (classPathFile, self.filename, err))

        return os.path.join(module_path, GENERAL_CLASS)

    def get_description(self, conflict=True):
        """
        Generate a description.
        """
        description = "%s - Homepage: %s" % (self.app.cfg['description'], self.app.cfg['homepage'])

        txt = "#%Module\n"
        txt += """
proc ModulesHelp { } {
    puts stderr {   %(description)s
}
}

module-whatis {%(description)s}

set root    %(installdir)s

""" % {'description': description, 'installdir': self.app.installdir}

        if self.app.cfg['moduleloadnoconflict']:
            txt += """
if { ![is-loaded %(name)s/%(version)s] } {
    if { [is-loaded %(name)s] } {
        module unload %(name)s
    }
}

""" % {'name': self.app.name, 'version': self.app.version}

        elif conflict:
            txt += "conflict    %s\n" % self.app.name

        return txt

    def load_module(self, name, version):
        """
        Generate load statements for module with name and version.
        """
        return """
if { ![is-loaded %(name)s/%(version)s] } {
    module load %(name)s/%(version)s
}
""" % {'name': name, 'version': version}

    def unload_module(self, name, version):
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

    def prepend_paths(self, key, paths):
        """
        Generate prepend-path statements for the given list of paths.
        """
        fullInstallPath = os.path.abspath(self.app.installdir) + '/'
        template = "prepend-path\t%s\t\t$root/%s\n" # $root = installdir

        statements = [template % (key, p.replace(fullInstallPath, '')) for p in paths]
        return ''.join(statements)

    def set_environment(self, key, value):
        """
        Generate setenv statement for the given key/value pair.
        """
        return "setenv\t%s\t\t%s\n" % (key, value)

    def __del__(self):
        """
        Desconstructor: clean up temporary directory used for fake modules, if any.
        """
        if self.fake:
            log.info("Cleaning up fake modules dir %s" % self.tmpdir)
            try:
                shutil.rmtree(self.tmpdir)
            except OSError, err:
                log.exception("Cleaning up fake module dir failed: %s" % err)
