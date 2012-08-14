##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
# Copyright 2012 Toon Willems
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

import copy
import difflib
import os

from easybuild.tools.build_log import getLog, EasyBuildError
from easybuild.tools.toolkit import Toolkit
from easybuild.tools.systemtools import get_shared_lib_ext
from easybuild.tools.filetools import run_cmd


class EasyBlock:
    """
    Class which handles loading, reading, validation of easyconfigs
    """
    # mandatory entries
    mandatory = ['name', 'version', 'homepage', 'description', 'toolkit']
    validmoduleclasses = ['base', 'compiler', 'lib']
    validstops = ['cfg', 'source', 'patch', 'prepare', 'configure', 'make', 'install', 'test', 'postproc', 'cleanup', 'packages']

    default_config = {
          'name': [None, "Name of software"],
          'version': [None, "Version of software"],
          'easybuildVersion': [None, "EasyBuild-version this spec-file was written for"],
          'group': [None, "Name of the user group for which the software should be available"],
          'versionsuffix': ['', 'Additional suffix for software version (placed after toolkit name)'],
          'versionprefix': ['', 'Additional prefix for software version (placed before version and toolkit name)'],
          'runtest': [None, 'Indicates if a test should be run after make; should specify argument after make (for e.g., "test" for make test) (Default: None)'],
          'preconfigopts': ['', 'Extra options pre-passed to configure.'],
          'configopts': ['', 'Extra options passed to configure (Default already has --prefix)'],
          'premakeopts': ['', 'Extra options pre-passed to make.'],
          'makeopts': ['', 'Extra options passed to make (Default already has -j X)'],
          'installopts': ['', 'Extra options for installation (Default: nothing)'],
          'moduleclass': ['base', 'Module class to be used for this software (Default: base) (Valid: %s)' % validmoduleclasses],
          'moduleforceunload': [False, 'Force unload of all modules when loading the package (Default: False)'],
          'moduleloadnoconflict': [False, "Don't check for conflicts, unload other versions instead (Default: False)"],
          'startfrom': [None, 'Path to start the make in. If the path is absolute, use that path. If not, this is added to the guessed path.'],
          'onlytkmod': [False, 'Boolean/string to indicate if the toolkit should only load the enviornment with module (True) or also set all other variables (False) like compiler CC etc (If string: comma separated list of variables that will be ignored). (Default: False)'],
          'stop': [None, 'Keyword to halt the buildprocess at certain points. Valid are %s' % validstops],
          'homepage': [None, 'The homepage of the software'],
          'description': [None, 'A short description of the software'],
          'parallel': [None, 'Degree of parallelism for e.g. make (default: based on the number of cores and restrictions in ulimit)'],
          'maxparallel': [None, 'Max degree of parallelism (default: None)'],
          'keeppreviousinstall': [False, 'Boolean to keep the previous installation with identical name. Default False, expert s only!'],
          'cleanupoldbuild': [True, 'Boolean to remove (True) or backup (False) the previous build directory with identical name or not. Default True'],
          'cleanupoldinstall': [True, 'Boolean to remove (True) or backup (False) the previous install directory with identical name or not. Default True'],
          'dontcreateinstalldir': [False, 'Boolean to create (False) or not create (True) the install directory (Default False)'],
          'toolkit': [None, 'Name and version of toolkit'],
          'toolkitopts': ['', 'Extra options for compilers'],
          'keepsymlinks': [False, 'Boolean to determine whether symlinks are to be kept during copying or if the content of the files pointed to should be copied'],
          'licenseServer': [None, 'License server for software'],
          'licenseServerPort': [None, 'Port for license server'],
          'key': [None, 'Key for installing software'],
          'pkglist': [[], 'List with packages added to the baseinstallation (Default: [])'],
          'pkgmodulenames': [{}, 'Dictionary with real modules names for packages, if they are different from the package name (Default: {})'],
          'pkgloadmodule': [True, 'Load the to-be installed software using temporary module (Default: True)'],
          'pkgtemplate': ["%s-%s.tar.gz", "Template for package source file names (Default: %s-%s.tar.gz)"],
          'pkgfindsource': [True, "Find sources for packages (Default: True)"],
          'pkginstalldeps': [True, "Install dependencies for specified packages if necessary (Default: True)"],
          'pkgdefaultclass': [None, "List of module for and name of the default package class (Default: None)"],
          'skip': [False, "Skip existing software (Default: False)"],
          'pkgfilter': [None, "Package filter details. List with template for cmd and input to cmd (templates for name, version and src). (Default: None)"],
          'pkgpatches': [[], 'List with patches for packages (default: [])'],
          'pkgcfgs': [{}, 'Dictionary with config parameters for packages (default: {})'],
          'dependencies': [[], "List of dependencies (default: [])"],
          'builddependencies': [[], "List of build dependencies (default: [])"],
          'unpackOptions': [None, "Extra options for unpacking source (default: None)"],
          'modextravars': [{}, "Extra environment variables to be added to module file (default: {})"],
          'osdependencies': [[], "Packages that should be present on the system"],
          'sources': [[], "List of source files"],
          'sourceURLs': [[], "List of URLs for source files"],
          'patches': [[], "List of patches to apply"],
          'tests': [[], "List of test-scripts to run after install. A test script should return a non-zero exit status to fail"],
          'sanityCheckPaths': [{}, "List of files and directories to check (format: {'files':<list>, 'dirs':<list>}, default: {})"],
          'sanityCheckCommand': [None, "format: (name, options) e.g. ('gzip','-h') . If set to True it will use (name, '-h')"],
          'buildstats': [None, "A list of dicts with buildstats: build_time, platform, core_count, cpu_model, install_size, timestamp"],
        }

    def __init__(self, path, extra_options={}, validate=True):
        """
        initialize an easyconfig.
        path should be a path to a file that can be parsed
        extra_options is a dict of extra variables that can be set in this specific instance
        validate specifies whether validations should happen
        """
        # perform a deepcopy of the default_config found in the easybuild.tools.easyblock module
        self.config = copy.deepcopy(self.default_config)
        self.config.update(extra_options)
        self.log = getLog("EasyBlock")

        # store toolkit
        self._toolkit = None

        if not os.path.isfile(path):
            self.log.error("EasyBlock __init__ expected a valid path")

        self.validations = {'moduleclass': self.validmoduleclasses, 'stop': self.validstops }

        self.parse(path)

        # perform validations
        if validate:
            self.validate()

    def parse(self, path):
        """
        Parse the file and set options
        mandatory requirements are checked here
        """
        global_vars = {"shared_lib_ext": get_shared_lib_ext()}
        local_vars = {}

        try:
            execfile(path, global_vars, local_vars)
        except IOError, err:
            self.log.exception("Unexpected IOError during execfile()")
        except SyntaxError, err:
            self.log.exception("SyntaxError in easyblock %s" % path)

        # validate mandatory keys
        for key in self.mandatory:
            if key not in local_vars:
                self.log.error("mandatory variable %s not provided" % key)

        # provide suggestions for typos
        for key in local_vars:
            if key not in self.config:
                guesses = difflib.get_close_matches(key, self.config.keys(), 1, 0.85)
                if len(guesses) == 1:
                    self.log.error("You set invalid variable %s, possible suggestions: %s" % (key, guesses[0]))

        for key in local_vars:
            # do not store variables we don't need
            if key in self.config:
                self[key] = local_vars[key]
                self.log.info("setting config option %s: value %s" % (key, self[key]))

    def validate(self):
        """
        Validate this EasyBlock
        - check certain variables
        TODO: move more into here
        """
        self.log.info("Validating easy block")
        for attr in self.validations:
            self._validate(attr, self.validations[attr])

        self.log.info("Checking OS dependencies")
        self.validate_os_deps()

        return True

    def validate_os_deps(self):
        """
        validate presence of OS dependencies
        osdependencies should be a single list
        """
        not_found = []
        for dep in self['osdependencies']:
            if not self._os_dependency_check(dep):
                not_found.append(dep)

        if not_found:
            self.log.error("One or more OS dependencies were not found: %s" % not_found)
        else:
            self.log.info("OS dependencies ok: %s" % self['osdependencies'])

        return True

    def dependencies(self):
        """
        returns an array of parsed dependencies
        dependency = {'name': '', 'version': '', 'dummy': (False|True), 'suffix': ''}
        """

        deps = []

        for dep in self['dependencies']:
            deps.append(self._parse_dependency(dep))


        return deps + self.builddependencies()

    def builddependencies(self):
        """
        return the parsed build dependencies
        """
        deps = []

        for dep in self['builddependencies']:
            deps.append(self._parse_dependency(dep))

        return deps

    def toolkit_name(self):
        """
        Returns toolkit name.
        """
        return self['toolkit']['name']

    def toolkit_version(self):
        """
        Returns toolkit name.
        """
        return self['toolkit']['version']

    def toolkit(self):
        """
        returns the Toolkit used
        """
        if self._toolkit:
            return self._toolkit

        tk = Toolkit(self.toolkit_name(), self.toolkit_version())
        if self['toolkitopts']:
            tk.set_options(self['toolkitopts'])

        self._toolkit = tk
        return self._toolkit

    def installversion(self):
        """
        return the installation version name
        """
        prefix, suffix = self['versionprefix'], self['versionsuffix']

        if self.toolkit_name() == 'dummy':
            name = "%s%s%s" % (prefix, self['version'], suffix)
        else:
            extra = "%s-%s" % (self.toolkit_name(), self.toolkit_version())
            name = "%s%s-%s%s" % (prefix, self['version'], extra, suffix)

        return name

    def name(self):
        """
        return name of the package
        """
        return self['name']

    # private method
    def _validate(self, attr, values):
        """
        validation helper method. attr is the attribute it will check, values are the possible values.
        if the value of the attribute is not in the is array, it will report an error
        """
        if self[attr] and self[attr] not in values:
            self.log.error("%s provided %s is not valid: %s" % (attr, self[attr], values))

    # private method
    def _os_dependency_check(self, dep):
        """
        Check if package is available from OS.
        """
        # - uses rpm -q and dpkg -s --> can be run as non-root!!
        # - fallback on which
        # - should be extended to files later?
        if run_cmd('which rpm', simple=True, log_ok=False):
            cmd = "rpm -q %s" % dep
        elif run_cmd('which dpkg', simple=True, log_ok=False):
            cmd = "dpkg -s %s" % dep
        else:
            # fallback for when os-dependency is a binary
            cmd = "which %s" % dep

        try:
            return run_cmd(cmd, simple=True, log_all=False, log_ok=False)
        except:
            return False

    # private method
    def _parse_dependency(self, dep):
        """
        parses the dependency into a usable dict with a common format
        dep can be a dict, a tuple or a list.
        if it is a tuple or a list the attributes are expected to be in the following order:
        ['name', 'version', 'suffix', 'dummy']
        of these attributes, 'name' and 'version' are mandatory

        output dict contains these attributes:
        ['name', 'version', 'suffix', 'dummy', 'tk']
        """
        # convert tuple to string otherwise python might complain about the formatting
        self.log.debug("Parsing %s as a dependency" % str(dep))

        attr = ['name', 'version', 'suffix', 'dummy']
        dependency = {'name': '', 'version': '', 'suffix': '', 'dummy': False}
        if isinstance(dep, dict):
            dependency.update(dep)
        # Try and convert to list
        elif isinstance(dep, list) or isinstance(dep, tuple):
            dep = list(dep)
            dependency.update(dict(zip(attr, dep)))
        else:
            self.log.error('Dependency %s from unsupported type: %s.' % (dep, type(dep)))

        # Validations
        if not dependency['name']:
            self.log.error("Dependency without name given")

        if not dependency['version']:
            self.log.error('Dependency without version.')

        if not 'tk' in dependency:
            dependency['tk'] = self.toolkit().get_dependency_version(dependency)

        return dependency

    def __getitem__(self, key):
        """
        will return the value without the help text
        """
        return self.config[key][0]

    def __setitem__(self, key, value):
        """
        sets the value of key in config.
        help text is untouched
        """
        self.config[key][0] = value

