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
import re
import tempfile

from easybuild.tools.build_log import getLog
from easybuild.tools.toolkit import Toolkit
from easybuild.tools.systemtools import get_shared_lib_ext
from easybuild.tools.filetools import run_cmd
from easybuild.tools.ordereddict import OrderedDict

# we use a tuple here so we can sort them based on the numbers
MANDATORY = (0, 'mandatory')
CUSTOM = (1, 'easyblock-specific')
TOOLKIT = (2, 'toolkit')
BUILD = (3, 'build')
FILEMANAGEMENT = (4, 'file-management')
DEPENDENCIES = (5, 'dependencies')
LICENSE = (6, 'license')
PACKAGE = (7, 'package')
MODULES = (8, 'modules')
OTHER = (9, 'other')


class EasyConfig:
    """
    Class which handles loading, reading, validation of easyconfigs
    """
    # validations
    validmoduleclasses = ['base', 'compiler', 'lib']
    validstops = ['cfg', 'source', 'patch', 'prepare', 'configure', 'make',
                  'install', 'test', 'postproc', 'cleanup', 'packages']

    # List of tuples. Each tuple has the following format (key, [default, help text, category])
    default_config = [
          ('name', [None, "Name of software", MANDATORY]),
          ('version', [None, "Version of software", MANDATORY]),
          ('toolkit', [None, 'Name and version of toolkit', MANDATORY]),
          ('description', [None, 'A short description of the software', MANDATORY]),
          ('homepage', [None, 'The homepage of the software', MANDATORY]),

          ('toolkitopts', ['', 'Extra options for compilers', TOOLKIT]),
          ('onlytkmod', [False,"Boolean/string to indicate if the toolkit should only load " \
                               "the enviornment with module (True) or also set all other " \
                               "variables (False) like compiler CC etc (If string: comma separated" \
                               "list of variables that will be ignored). (Default: False)", TOOLKIT]),

          ('easybuildVersion', [None, "EasyBuild-version this spec-file was written for", BUILD]),
          ('versionsuffix', ['', 'Additional suffix for software version (placed after toolkit name)',
                             BUILD]),
          ('versionprefix', ['', "Additional prefix for software version (placed before version " \
                                 "and toolkit name)", BUILD]),
          ('runtest', [None, 'Indicates if a test should be run after make; should specify argument ' \
                             'after make (for e.g.,"test" for make test) (Default: None)', BUILD]),
          ('preconfigopts', ['', 'Extra options pre-passed to configure.', BUILD]),
          ('configopts', ['', 'Extra options passed to configure (Default already has --prefix)', BUILD]),
          ('premakeopts', ['', 'Extra options pre-passed to make.', BUILD]),
          ('makeopts', ['', 'Extra options passed to make (Default already has -j X)', BUILD]),
          ('installopts', ['', 'Extra options for installation (Default: nothing)', BUILD]),
          ('unpackOptions', [None, "Extra options for unpacking source (default: None)", BUILD]),
          ('stop', [None, 'Keyword to halt the buildprocess at certain points. Valid are %s' % validstops,
                    BUILD]),
          ('skip', [False, "Skip existing software (Default: False)", BUILD]),
          ('parallel', [None, 'Degree of parallelism for e.g. make (default: based on the number of ' \
                              'cores and restrictions in ulimit)', BUILD]),
          ('maxparallel', [None, 'Max degree of parallelism (default: None)', BUILD]),
          ('sources', [[], "List of source files", BUILD]),
          ('sourceURLs', [[], "List of URLs for source files", BUILD]),
          ('patches', [[], "List of patches to apply", BUILD]),
          ('tests', [[], "List of test-scripts to run after install. A test script should return a " \
                         "non-zero exit status to fail", BUILD]),
          ('sanityCheckPaths', [{}, "List of files and directories to check (format: {'files':<list>, " \
                                    "'dirs':<list>}, default: {})", BUILD]),
          ('sanityCheckCommand', [None, "format: (name, options) e.g. ('gzip','-h') . If set to True " \
                                        "it will use (name, '-h')", BUILD]),

          ('startfrom', [None, 'Path to start the make in. If the path is absolute, use that path. ' \
                               'If not, this is added to the guessed path.', FILEMANAGEMENT]),
          ('keeppreviousinstall', [False, 'Boolean to keep the previous installation with identical ' \
                                          'name. Default False, experts only!', FILEMANAGEMENT]),
          ('cleanupoldbuild', [True, 'Boolean to remove (True) or backup (False) the previous build ' \
                                     'directory with identical name or not. Default True', FILEMANAGEMENT]),
          ('cleanupoldinstall', [True, 'Boolean to remove (True) or backup (False) the previous install ' \
                                       'directory with identical name or not. Default True',
                                       FILEMANAGEMENT]),
          ('dontcreateinstalldir', [False, 'Boolean to create (False) or not create (True) the install ' \
                                           'directory (Default False)', FILEMANAGEMENT]),
          ('keepsymlinks', [False, 'Boolean to determine whether symlinks are to be kept during copying ' \
                                   'or if the content of the files pointed to should be copied',
                                   FILEMANAGEMENT]),

          ('dependencies', [[], "List of dependencies (default: [])", DEPENDENCIES]),
          ('builddependencies', [[], "List of build dependencies (default: [])", DEPENDENCIES]),
          ('osdependencies', [[], "Packages that should be present on the system", DEPENDENCIES]),

          ('licenseServer', [None, 'License server for software', LICENSE]),
          ('licenseServerPort', [None, 'Port for license server', LICENSE]),
          ('key', [None, 'Key for installing software', LICENSE]),
          ('group', [None, "Name of the user group for which the software should be available",  LICENSE]),

          ('pkglist', [[], 'List with packages added to the baseinstallation (Default: [])', PACKAGE]),
          ('pkgmodulenames', [{}, 'Dictionary with real modules names for packages, if they are different from the package name (Default: {})', PACKAGE]),
          ('pkgloadmodule', [True, 'Load the to-be installed software using temporary module (Default: True)', PACKAGE]),
          ('pkgtemplate', ["%s-%s.tar.gz", "Template for package source file names (Default: %s-%s.tar.gz)", PACKAGE]),
          ('pkgfindsource', [True, "Find sources for packages (Default: True)", PACKAGE]),
          ('pkginstalldeps', [True, "Install dependencies for specified packages if necessary (Default: True)", PACKAGE]),
          ('pkgdefaultclass', [None, "List of module for and name of the default package class (Default: None)", PACKAGE]),
          ('pkgfilter', [None, "Package filter details. List with template for cmd and input to cmd (templates for name, version and src). (Default: None)", PACKAGE]),
          ('pkgpatches', [[], 'List with patches for packages (default: [])', PACKAGE]),
          ('pkgcfgs', [{}, 'Dictionary with config parameters for packages (default: {})', PACKAGE]),

          ('modextravars', [{}, "Extra environment variables to be added to module file (default: {})", MODULES]),
          ('moduleclass', ['base', 'Module class to be used for this software (Default: base) (Valid: %s)' % validmoduleclasses, MODULES]),
          ('moduleforceunload', [False, 'Force unload of all modules when loading the package (Default: False)', MODULES]),
          ('moduleloadnoconflict', [False, "Don't check for conflicts, unload other versions instead (Default: False)", MODULES]),

          ('buildstats', [None, "A list of dicts with buildstats: build_time, platform, core_count, cpu_model, install_size, timestamp", OTHER]),
        ]

    def __init__(self, path, extra_options=[], validate=True):
        """
        initialize an easyconfig.
        path should be a path to a file that can be parsed
        extra_options is a dict of extra variables that can be set in this specific instance
        validate specifies whether validations should happen
        """
        # perform a deepcopy of the default_config found in the easybuild.tools.easyblock module
        self.config = dict(copy.deepcopy(self.default_config))
        self.config.update(extra_options)
        self.path = path
        self.mandatory = ['name', 'version', 'homepage', 'description', 'toolkit']

        # extend mandatory keys
        for (key, value) in extra_options:
            if value[2] == MANDATORY:
                self.mandatory.append(key)

        self.log = getLog("EasyConfig")

        # store toolkit
        self._toolkit = None

        if not os.path.isfile(path):
            self.log.error("EasyConfig __init__ expected a valid path")

        self.validations = {
                            'moduleclass': self.validmoduleclasses,
                            'stop': self.validstops
                           }

        self.parse(path, validate)

        # perform validations
        if validate:
            self.validate()

    def parse(self, path, validate=True):
        """
        Parse the file and set options
        mandatory requirements are checked here
        """
        global_vars = {"shared_lib_ext": get_shared_lib_ext()}
        local_vars = {}

        try:
            execfile(path, global_vars, local_vars)
        except IOError, err:
            self.log.exception("Unexpected IOError during execfile(): %s" % err)
        except SyntaxError, err:
            self.log.exception("SyntaxError in easyblock %s: %s" % (path, err))

        # validate mandatory keys
        if validate:
            missing_keys = [key for key in self.mandatory if key not in local_vars]
            if missing_keys:
                self.log.error("mandatory variables %s not provided" % missing_keys)

            # provide suggestions for typos
            possible_typos = [(key, difflib.get_close_matches(key, self.config.keys(), 1, 0.85))
                              for key in local_vars if key not in self.config]

            typos = [(key, guesses[0]) for (key, guesses) in possible_typos if len(guesses) == 1]
            if typos:
                self.log.error("You may have some typos in your easyconfig file: %s" %
                                ', '.join(["%s -> %s" % typo for typo in typos]))

        for key in local_vars:
            # validations are skipped, just set in the config
            if not validate:
                if key in self.config:
                    self[key] = local_vars[key]
                else:
                    self.config[key] = [local_vars[key], ""]

            # do not store variables we don't need
            elif key in self.config:
                self[key] = local_vars[key]
                self.log.info("setting config option %s: value %s" % (key, self[key]))

    def validate(self):
        """
        Validate this EasyConfig
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
        return det_installversion(self['version'], self.toolkit_name(), self.toolkit_version(),
                                  self['versionprefix'], self['versionsuffix'])

    def name(self):
        """
        return name of the package
        """
        return self['name']

    def dump(self, fp):
        """
        Dump this easyconfig to file, with the given filename.
        """
        eb_file = file(fp, "w")

        def to_str(x):
            if type(x) == str:
                if '\n' in x or ('"' in x and "'" in x):
                    return '"""%s"""' % x
                elif "'" in x:
                    return '"%s"' % x
                else:
                    return "'%s'" % x
            else:
                return "%s" % x

        # ordered groups of keys to obtain a nice looking easyconfig file
        grouped_keys = [
                        ["name", "version", "versionprefix", "versionsuffix"],
                        ["homepage", "description"],
                        ["toolkit", "toolkitopts"],
                        ["sourceURLs", "sources"],
                        ["patches"],
                        ["dependencies"],
                        ["parallel", "maxparallel"],
                        ["osdependencies"]
                        ]

        # print easyconfig parameters ordered and in groups specified above
        ebtxt = []
        printed_keys = []
        for group in grouped_keys:
            for key1 in group:
                val = self.config[key1][0]
                for (key2, [def_val, _, _]) in self.default_config:
                    # only print parameters that are different from the default value
                    if key1 == key2 and val != def_val:
                        ebtxt.append("%s = %s" % (key1, to_str(val)))
                        printed_keys.append(key1)
            ebtxt.append("")

        # print other easyconfig parameters at the end
        for (key, [val, _, _]) in self.default_config:
            if not key in printed_keys and val != self.config[key][0]:
                ebtxt.append("%s = %s" % (key, to_str(self.config[key][0])))

        eb_file.write('\n'.join(ebtxt))
        eb_file.close()

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


def det_installversion(version, toolkit_name, toolkit_version, prefix, suffix):
    """
    Determine exact install version, based on supplied parameters.
    e.g. 1.2.3-goalf-1.1.0-no-OFED or 1.2.3 (for dummy toolkits)
    """

    installversion = None

    # determine main install version based on toolkit
    if toolkit_name == 'dummy':
        installversion = version
    else:
        installversion = "%s-%s-%s" % (version, toolkit_name, toolkit_version)

    # prepend/append prefix/suffix
    if prefix:
        installversion = "%s%s" % (prefix, installversion)
    if suffix:
        installversion += suffix

    return installversion

def sorted_categories():
    """
    returns the categories in the correct order
    """
    categories = [MANDATORY, CUSTOM , TOOLKIT, BUILD, FILEMANAGEMENT,
                  DEPENDENCIES, LICENSE , PACKAGE, MODULES, OTHER]
    categories.sort(key = lambda c: c[0])
    return categories

def convert_to_help(option_list):
    """
    Converts the given list to a mapping of category -> [(name, help)] (OrderedDict)
    """
    mapping = OrderedDict()

    for category in sorted_categories():
        mapping[category[1]] = [(arr[0], arr[1][1]) for arr in option_list if arr[1][2] == category]

    return mapping

def ec_filename_for(path):
    """
    Return a suiting file name for the easyconfig file at <path>,
    as determined by its contents.
    """
    ec = EasyConfig(path, validate=False)

    fn = "%s-%s.eb" % (ec['name'], det_installversion(ec['version'], ec['toolkit']['name'],
                                                      ec['toolkit']['version'], ec['versionprefix'],
                                                      ec['versionsuffix']))

    return fn

def tweak(src_fn, target_fn, tweaks, log):
    """
    Tweak an easyconfig file with the given list of tweaks, using replacement via regular expressions.
    Note: this will only work 'well-written' easyconfig files, i.e. ones that e.g. set the version
    once and then use the 'version' variable to construct the list of sources, and possibly other
    parameters that depend on the version (e.g. list of patch files, dependencies, version suffix, ...)

    The tweaks should be specified in a dictionary, with parameters and keys that map to the values
    to be set.

    Reads easyconfig file at path <src_fn>, and writes the tweaked easyconfig file to <target_fn>.

    If no target filename is provided, a target filepath is generated based on the contents of
    the tweaked easyconfig file.
    """

    # read easyconfig file
    ectxt = None
    print src_fn
    try:
        f = open(src_fn, "r")
        ectxt = f.read()
        f.close()
    except IOError, err:
        log.error("Failed to read easyconfig file %s: %s" % (src_fn, err))

    log.debug("Contents of original easyconfig file, prior to tweaking:\n%s" % ectxt)

    # determine new toolkit if it's being changed
    keys = tweaks.keys()
    if 'toolkit_name' in keys or 'toolkit_version' in keys:

        tk_regexp = re.compile("^\s*toolkit\s*=\s*(.*)$", re.M)

        res = tk_regexp.search(ectxt)
        if not res:
            log.error("No toolkit found in easyconfig file %s?" % src_fn)

        toolkit = eval(res.group(1))

        for key in ['toolkit_name', 'toolkit_version']:
            if key in keys:
                toolkit.update({key: tweaks[key]})
                tweaks.pop(key)

        tweaks.update({'toolkit': {'name': toolkit['name'], 'version': toolkit['version']}})

        log.debug("New toolkit constructed: %s" % tweaks['toolkit'])

    additions = []

    # we need to treat patches seperately, i.e. we append to the list
    if tweaks.has_key('patches'):
        patches_regexp = re.compile("^\s*patches\s*=\s*(.*)$", re.M)

        res = patches_regexp.search(ectxt)
        if res:
            patches = "%s + %s" % (res.group(1), tweaks['patches'])
            ectxt = patches_regexp.sub("patches = %s # tweaked by EasyBuild" % patches, ectxt)
            log.info("Tweaked patch list to '%s'" % patches)
        else:
            additions.append("patches = %s" % tweaks['patches'])

        tweaks.pop('patches')

    def quoted(x):
        """Obtain a new value to be used in string replacement context.

        For non-string values, it just returns the exact same value.

        For string values, it tries to escape the string in quotes, e.g.,
        foo becomes 'foo', foo'bar becomes "foo'bar",
        foo'bar"baz becomes \"\"\"foo'bar"baz\"\"\", etc.
        """
        if type(x) == str:
            if "'" in x and '"' in x:
                return '"""%s"""' % x
            elif "'" in x:
                return '"%s"' % x
            else:
                return "'%s'" % x
        else:
            return x

    # add parameters or replace existing ones
    for (key,val) in tweaks.items():

        val = quoted(val)

        regexp = re.compile("^\s*%s\s*=\s*(.*)$" % key, re.M)
        log.debug("Regexp pattern for replacing '%s': %s" % (key, regexp.pattern))

        res = regexp.search(ectxt)
        if res:
            # onyl tweak if the value is different
            if not eval(res.group(1)) == val:
                ectxt = regexp.sub("%s = %s # tweaked by EasyBuild" % (key,val), ectxt)
        else:
            additions.append("%s = %s" % (key, val))

        log.info("Tweaked '%s' to '%s'" % (key, val))

    if additions:
        log.info("Adding additional parameters to tweaked easyconfig file: %s")
        ectxt += "\n\n# added by EasyBuild as dictated by command line options\n"
        ectxt += '\n'.join(additions) + '\n'

    log.debug("Contents of tweaked easyconfig file:\n%s" % ectxt)

    # come up with suiting file name for tweaked easyconfig file if none was specified
    if not target_fn:

        fn = None

        try:
            # obtain temporary filename
            fd, tmpfn = tempfile.mkstemp()
            os.close(fd)

            # write easyconfig to temporary file
            f = open(tmpfn, "w")
            f.write(ectxt)
            f.close()

            # determine suiting filename
            fn = ec_filename_for(tmpfn)

            # get rid of temporary file
            os.remove(tmpfn)

        except (IOError, OSError), err:
            log.error("Failed to determine suiting filename for tweaked easyconfig file: %s" % err)

        target_fn = os.path.join(tempfile.gettempdir(), fn)
        log.debug("Generated file name for tweaked easyconfig file: %s" % target_fn)

    # write out tweaked easyconfig file
    try:
        f = open(target_fn, "w")
        f.write(ectxt)
        f.close()
        log.info("Tweaked easyconfig file written to %s" % target_fn)
    except IOError, err:
        log.error("Failed to write tweaked easyconfig file to %s: %s" % (target_fn, err))

    return target_fn