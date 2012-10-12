##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
"""
Generic EasyBuild support for building and installing software.
The EasyBlock class should serve as a base class for all easyblocks.
"""

import copy
import glob
import grp  #@UnresolvedImport
import re
import os
import shutil
import stat
import time
import urllib
from distutils.version import LooseVersion

import easybuild
import easybuild.tools.environment as env
from easybuild.framework.easyconfig import EasyConfig, get_paths_for
from easybuild.tools.build_log import EasyBuildError, init_logger, print_msg, remove_log_handler
from easybuild.tools.config import build_path, install_path, log_path, read_only_installdir, source_path
from easybuild.tools.filetools import adjust_permissions, apply_patch, convert_name, download_file
from easybuild.tools.filetools import encode_class_name, extract_file, run_cmd
from easybuild.tools.module_generator import GENERAL_CLASS, ModuleGenerator
from easybuild.tools.modules import Modules, get_software_root
from easybuild.tools.systemtools import get_core_count


class EasyBlock(object):
    """Generic support for building and installing software, base class for actual easyblocks."""

    # static class method for extra easyconfig parameter definitions
    # this makes it easy to access the information without needing an instance
    # subclasses of EasyBlock should call this method with a dictionary
    @staticmethod
    def extra_options(extra=None):
        """
        Extra options method which will be passed to the EasyConfig constructor.
        """
        if extra == None:
            return []
        else:
            return extra

    #
    # INIT
    #
    def __init__(self, path, debug=False):
        """
        Initialize the EasyBlock instance.
        """

        # list of patch/source files
        self.patches = []
        self.src = []

        # build/install directories
        self.builddir = None
        self.installdir = None

        # extensions
        self.exts = None
        self.ext_instances = []
        self.skip = None
        self.module_extra_extensions = ''  # extra stuff for module file required by extentions

        # easyconfig for this application
        self.cfg = EasyConfig(path, self.extra_options())

        # module generator
        self.moduleGenerator = None

        self.sanityCheckOK = False

        # indicates whether build should be performed in installation dir
        self.build_in_installdir = False

        # logging
        self.log = None
        self.logfile = None
        self.loghandler = None
        self.logdebug = debug
        self.postmsg = ''  # allow a post message to be set, which can be shown as last output
        self.init_log()

        # original environ will be set later
        self.orig_environ = {}

        # list of loaded modules
        self.loaded_modules = []

    # INIT/CLOSE LOG
    def init_log(self):
        """
        Initialize the logger.
        """
        if not self.log:
            self.logfile, self.log, self.loghandler = init_logger(self.name, self.version,
                                                                 self.logdebug, typ=self.__class__.__name__)
            self.log.info("Init completed for application name %s version %s" % (self.name, self.version))

    def close_log(self):
        """
        Shutdown the logger.
        """
        self.log.info("Closing log for application name %s version %s" % (self.name, self.version))
        remove_log_handler(self.loghandler)
        self.loghandler.close()


    #
    # FETCH UTILITY FUNCTIONS
    #

    def fetch_sources(self, list_of_sources):
        """
        Add a list of source files (can be tarballs, isos, urls).
        All source files will be checked if a file exists (or can be located)
        """

        for source in list_of_sources:
            ## check if the sources can be located
            path = self.obtain_file(source)
            if path:
                self.log.debug('File %s found for source %s' % (path, source))
                self.src.append({'name':source, 'path':path})
            else:
                self.log.error('No file found for source %s' % source)

        self.log.info("Added sources: %s" % self.src)

    def fetch_patches(self, list_of_patches):
        """
        Add a list of patches.
        All patches will be checked if a file exists (or can be located)
        """

        for patchFile in list_of_patches:

            ## check if the patches can be located
            copy = False
            suff = None
            level = None
            if type(patchFile) in [list, tuple]:
                if not len(patchFile) == 2:
                    self.log.error("Unknown patch specification '%s', only two-element lists/tuples are supported!" % patchFile)
                pf = patchFile[0]

                if type(patchFile[1]) == int:
                    level = patchFile[1]
                elif type(patchFile[1]) == str:
                    # non-patch files are assumed to be files to copy
                    if not patchFile[0].endswith('.patch'):
                        copy = True
                    suff = patchFile[1]
                else:
                    self.log.error("Wrong patch specification '%s', only int and string are supported as second element!" % patchFile)
            else:
                pf = patchFile

            path = self.obtain_file(pf)
            if path:
                self.log.debug('File %s found for patch %s' % (path, patchFile))
                tmppatch = {'name':pf, 'path':path}
                if suff:
                    if copy:
                        tmppatch['copy'] = suff
                    else:
                        tmppatch['sourcepath'] = suff
                if level:
                    tmppatch['level'] = level
                self.patches.append(tmppatch)
            else:
                self.log.error('No file found for patch %s' % patchFile)

        self.log.info("Added patches: %s" % self.patches)

    def fetch_extension_patches(self, ext_name):
        """
        Find patches for extensions.
        """
        for (name, patches) in self.cfg['exts_patches']:
            if name == ext_name:
                exts_patches = []
                for p in patches:
                    pf = self.obtain_file(p, ext=True)
                    if pf:
                        exts_patches.append(pf)
                    else:
                        self.log.error("Unable to locate file for patch %s." % p)
                return exts_patches
        return []

    def fetch_extension_sources(self):
        """
        Find source file for extensions.
        """
        exts_sources = []
        for ext in self.cfg['exts_list']:
            if type(ext) in [list, tuple] and ext:
                ext_name = ext[0]
                forceunknownsource = False
                if len(ext) == 1:
                    exts_sources.append({'name':ext_name})
                else:
                    if len(ext) == 2:
                        fn = self.cfg['exts_template'] % (ext_name, ext[1])
                    elif len(ext) == 3:
                        if type(ext[2]) == bool:
                            forceunknownsource = ext[2]
                        else:
                            fn = ext[2]
                    else:
                        self.log.error('Extension specified in unknown format (list/tuple too long)')

                    if forceunknownsource:
                        exts_sources.append({
                                             'name':ext_name,
                                             'version':ext[1]
                                            })
                    else:
                        filename = self.obtain_file(fn, True)
                        if filename:
                            ext_src = {
                                       'name': ext_name,
                                       'version': ext[1],
                                       'src': filename
                                      }

                            ext_patches = self.fetch_extension_patches(ext_name)
                            if ext_patches:
                                self.log.debug('Found patches for extension %s: %s' % (ext_name, ext_patches))
                                ext_src.update({'patches':ext_patches})
                            else:
                                self.log.debug('No patches found for extension %s.' % ext_name)

                            exts_sources.append(ext_src)

                        else:
                            self.log.warning("Source for extension %s not found.")

            elif type(ext) == str:
                exts_sources.append({'name':ext})
            else:
                self.log.error("Extension specified in unknown format (not a string/list/tuple)")

        return exts_sources

    def obtain_file(self, filename, ext=False):
        """
        Locate the file with the given name
        - searches in different subdirectories of source path
        - supports fetching file from the web if path is specified as an url (i.e. starts with "http://:")
        """
        srcpath = source_path()

        # make sure we always deal with a list, to avoid code duplication
        if type(srcpath) == str:
            srcpaths = [srcpath]
        elif type(srcpath) == list:
            srcpaths = srcpath
        else:
            self.log.error("Source path '%s' has incorrect type: %s" % (srcpath, type(srcpath)))

        # should we download or just try and find it?
        if filename.startswith("http://") or filename.startswith("ftp://"):

            # URL detected, so let's try and download it

            url = filename
            filename = url.split('/')[-1]

            # figure out where to download the file to
            for srcpath in srcpaths:
                filepath = os.path.join(srcpath, self.name[0].lower(), self.name)
                if ext:
                    filepath = os.path.join(filepath, "extensions")
                if os.path.isdir(filepath):
                    self.log.info("Going to try and download file to %s" % filepath)
                    break

            # if no path was found, let's just create it in the last source path
            if not os.path.isdir(filepath):
                try:
                    self.log.info("No path found to download file to, so creating it: %s" % filepath)
                    os.makedirs(filepath)
                except OSError, err:
                    self.log.error("Failed to create %s: %s" % (filepath, err))

            try:
                fullpath = os.path.join(filepath, filename)

                # only download when it's not there yet
                if os.path.exists(fullpath):
                    self.log.info("Found file %s at %s, no need to download it." % (filename, filepath))
                    return fullpath

                else:
                    if download_file(filename, url, fullpath):
                        return fullpath

            except IOError, err:
                self.log.exception("Downloading file %s from url %s to %s failed: %s" % (filename, url, fullpath, err))

        else:
            # try and find file in various locations
            foundfile = None
            failedpaths = []
            for srcpath in srcpaths:
                # create list of candidate filepaths
                namepath = os.path.join(srcpath, self.name)
                fst_letter_path_low = os.path.join(srcpath, self.name.lower()[0])

                # most likely paths
                candidate_filepaths = [os.path.join(fst_letter_path_low, self.name), # easyblocks-style subdir
                                       namepath, # subdir with software name
                                       srcpath, # directly in sources directory
                                       ]

                # also consider easyconfigs paths as a fall back (e.g. for patch files, test cases, ...)
                for path in get_paths_for(self.log, "easyconfigs"):
                    candidate_filepaths.append(os.path.join(
                                                            path,
                                                            "easybuild",
                                                            "easyconfigs",
                                                            self.name.lower()[0],
                                                            self.name
                                                            ))

                # see if file can be found at that location
                for cfp in candidate_filepaths:

                    fullpath = os.path.join(cfp, filename)

                    # also check in 'extensions' subdir for extensions
                    if ext:
                        fullpaths = [
                                     os.path.join(cfp, "extensions", filename),
                                     os.path.join(cfp, "packages", filename),  # legacy
                                     fullpath 
                                    ]
                    else:
                        fullpaths = [fullpath]

                    for fp in fullpaths:
                        if os.path.isfile(fp):
                            self.log.info("Found file %s at %s" % (filename, fp))
                            foundfile = fp
                            break # no need to try further
                        else:
                            failedpaths.append(fp)

                if foundfile:
                    break # no need to try other source paths

            if foundfile:
                return foundfile
            else:
                # try and download source files from specified source URLs
                sourceURLs = self.cfg['sourceURLs']
                targetdir = candidate_filepaths[0]
                if not os.path.isdir(targetdir):
                    try:
                        os.makedirs(targetdir)
                    except OSError, err:
                        self.log.error("Failed to create directory %s to download source file %s into" % (targetdir, filename))

                for url in sourceURLs:

                    if ext:
                        targetpath = os.path.join(targetdir, "extensions", filename)
                    else:
                        targetpath = os.path.join(targetdir, filename)

                    if type(url) == str:
                        fullurl = "%s/%s" % (url, filename)
                    elif type(url) == tuple:
                        ## URLs that require a suffix, e.g., SourceForge download links
                        ## e.g. http://sourceforge.net/projects/math-atlas/files/Stable/3.8.4/atlas3.8.4.tar.bz2/download
                        fullurl = "%s/%s/%s" % (url[0], filename, url[1])
                    else:
                        self.log.warning("Source URL %s is of unknown type, so ignoring it." % url)
                        continue

                    self.log.debug("Trying to download file %s from %s to %s ..." % (filename, fullurl, targetpath))
                    downloaded = False
                    try:
                        if download_file(filename, fullurl, targetpath):
                            downloaded = True

                    except IOError, err:
                        self.log.debug("Failed to download %s from %s: %s" % (filename, url, err))
                        failedpaths.append(fullurl)
                        continue

                    if downloaded:
                        # if fetching from source URL worked, we're done
                        self.log.info("Successfully downloaded source file %s from %s" % (filename, fullurl))
                        return targetpath
                    else:
                        failedpaths.append(fullurl)

                self.log.error("Couldn't find file %s anywhere, and downloading it didn't work either...\nPaths attempted (in order): %s " % (filename, ', '.join(failedpaths)))


    #
    # GETTER/SETTER UTILITY FUNCTIONS
    #

    @property
    def name(self):
        """
        Shortcut the get the module name.
        """
        return self.cfg['name']

    @property
    def version(self):
        """
        Shortcut the get the module version.
        """
        return self.cfg['version']

    @property
    def toolchain(self):
        """
        Toolchain used to build this easyblock
        """
        return self.cfg.toolchain

    #
    # DIRECTORY UTILITY FUNCTIONS
    #

    def make_builddir(self):
        """
        Create the build directory.
        """
        if not self.build_in_installdir:
            # make a unique build dir
            ## if a tookitversion starts with a -, remove the - so prevent a -- in the path name
            tcversion = self.toolchain.version
            if tcversion.startswith('-'):
                tcversion = tcversion[1:]

            extra = "%s%s-%s%s" % (self.cfg['versionprefix'], self.toolchain.name, tcversion, self.cfg['versionsuffix'])
            localdir = os.path.join(build_path(), self.name, self.version, extra)

            ald = os.path.abspath(localdir)
            tmpald = ald
            counter = 1
            while os.path.isdir(tmpald):
                counter += 1
                tmpald = "%s.%d" % (ald, counter)

            self.builddir = ald

            self.log.debug("Creating the build directory %s (cleanup: %s)" % (self.builddir, self.cfg['cleanupoldbuild']))

        else:
            self.log.info("Changing build dir to %s" % self.installdir)
            self.builddir = self.installdir

            self.log.info("Overriding 'cleanupoldinstall' (to False), 'cleanupoldbuild' (to True) " \
                          "and 'keeppreviousinstall' because we're building in the installation directory.")
            # force cleanup before installation
            self.cfg['cleanupoldbuild'] = True
            self.cfg['keeppreviousinstall'] = False
            # avoid cleanup after installation
            self.cfg['cleanupoldinstall'] = False

        # always make build dir
        self.make_dir(self.builddir, self.cfg['cleanupoldbuild'])

    def gen_installdir(self):
        """
        Generate the name of the installation directory.
        """
        basepath = install_path()

        if basepath:
            installdir = os.path.join(basepath, self.name, self.get_installversion())
            self.installdir = os.path.abspath(installdir)
        else:
            self.log.error("Can't set installation directory")

    def make_installdir(self):
        """
        Create the installation directory.
        """
        self.log.debug("Creating the installation directory %s (cleanup: %s)" % (self.installdir, self.cfg['cleanupoldinstall']))
        if self.build_in_installdir:
            self.cfg['keeppreviousinstall'] = True
        self.make_dir(self.installdir, self.cfg['cleanupoldinstall'], self.cfg['dontcreateinstalldir'])

    def make_dir(self, dirName, clean, dontcreateinstalldir=False):
        """
        Create the directory.
        """
        if os.path.exists(dirName):
            self.log.info("Found old directory %s" % dirName)
            if self.cfg['keeppreviousinstall']:
                self.log.info("Keeping old directory %s (hopefully you know what you are doing)" % dirName)
                return
            elif clean:
                try:
                    shutil.rmtree(dirName)
                    self.log.info("Removed old directory %s" % dirName)
                except OSError, err:
                    self.log.exception("Removal of old directory %s failed: %s" % (dirName, err))
            else:
                try:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    backupdir = "%s.%s" % (dirName, timestamp)
                    shutil.move(dirName, backupdir)
                    self.log.info("Moved old directory %s to %s" % (dirName, backupdir))
                except OSError, err:
                    self.log.exception("Moving old directory to backup %s %s failed: %s" % (dirName, backupdir, err))

        if dontcreateinstalldir:
            olddir = dirName
            dirName = os.path.dirname(dirName)
            self.log.info("Cleaning only, no actual creation of %s, only verification/creation of dirname %s" % (olddir, dirName))
            if os.path.exists(dirName):
                return
            ## if not, create dir as usual

        try:
            os.makedirs(dirName)
        except OSError, err:
            self.log.exception("Can't create directory %s: %s" % (dirName, err))

    # 
    # MODULE UTILITY FUNCTIONS
    #

    def make_devel_module(self, create_in_builddir=False):
        """
        Create a develop module file which sets environment based on the build
        Usage: module load name, which loads the module you want to use. $EBDEVELNAME should then be the full path
        to the devel module file. So now you can module load $EBDEVELNAME.

        WARNING: you cannot unload using $EBDEVELNAME (for now: use module unload `basename $EBDEVELNAME`)
        """
        # first try loading the fake module (might have happened during sanity check, doesn't matter anyway
        # make fake module
        mod_path = [self.make_module_step(True)]

        # load the module
        mod_path.extend(Modules().modulePath)
        m = Modules(mod_path)
        self.log.debug("created module instance")
        m.add_module([[self.name, self.get_installversion()]])
        try:
            m.load()
        except EasyBuildError, err:
            self.log.debug("Loading module failed: %s" % err)
            self.log.debug("loaded modules: %s" % Modules().loaded_modules())

        mod_gen = ModuleGenerator(self)
        header = "#%Module\n"

        env_txt = ""
        for (key, val) in env.changes.items():
            # check if non-empty string
            # TODO: add unset for empty vars?
            if val.strip():
                env_txt += mod_gen.set_environment(key, val)

        load_txt = ""
        # capture all the EBDEVEL vars
        # these should be all the dependencies and we should load them
        for key in os.environ:
            # legacy support
            if key.startswith("EBDEVEL") or key.startswith("SOFTDEVEL"):
                if not key.endswith(convert_name(self.name, upper=True)):
                    path = os.environ[key]
                    if os.path.isfile(path):
                        name, version = path.rsplit('/', 1)
                        load_txt += mod_gen.load_module(name, version)

        if create_in_builddir:
            output_dir = self.builddir
        else:
            output_dir = os.path.join(self.installdir, log_path())
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

        filename = os.path.join(output_dir, "%s-%s-easybuild-devel" % (self.name, self.get_installversion()))
        self.log.debug("Writing devel module to %s" % filename)

        devel_module = open(filename, "w")
        devel_module.write(header)
        devel_module.write(load_txt)
        devel_module.write(env_txt)
        devel_module.close()

    def make_module_dep(self):
        """
        Make the dependencies for the module file.
        """
        load = unload = ''

        # Load toolchain
        if self.toolchain.name != 'dummy':
            load += self.moduleGenerator.load_module(self.toolchain.name, self.toolchain.version)
            unload += self.moduleGenerator.unload_module(self.toolchain.name, self.toolchain.version)

        # Load dependencies
        builddeps = self.cfg.builddependencies()
        for dep in self.toolchain.dependencies:
            if not dep in builddeps:
                self.log.debug("Adding %s/%s as a module dependency" % (dep['name'], dep['tc']))
                load += self.moduleGenerator.load_module(dep['name'], dep['tc'])
                unload += self.moduleGenerator.unload_module(dep['name'], dep['tc'])
            else:
                self.log.debug("Skipping builddependency %s/%s" % (dep['name'], dep['tc']))

        # Force unloading any other modules
        if self.cfg['moduleforceunload']:
            return unload + load
        else:
            return load

    def make_module_description(self):
        """
        Create the module description.
        """
        return self.moduleGenerator.get_description()

    def make_module_extra(self):
        """
        Sets optional variables (EBROOT, MPI tuning variables).
        """
        txt = "\n"

        # EBROOT + EBVERSION + EBDEVEL
        environment_name = convert_name(self.name, upper=True)
        txt += self.moduleGenerator.set_environment("EBROOT" + environment_name, "$root")
        txt += self.moduleGenerator.set_environment("EBVERSION" + environment_name, self.version)
        devel_path = os.path.join("$root", log_path(), "%s-%s-easybuild-devel" % (self.name,
            self.get_installversion()))
        txt += self.moduleGenerator.set_environment("EBDEVEL" + environment_name, devel_path)

        txt += "\n"
        for (key, value) in self.cfg['modextravars'].items():
            txt += self.moduleGenerator.set_environment(key, value)

        self.log.debug("make_module_extra added this: %s" % txt)

        return txt

    def make_module_extra_extensions(self):
        """
        Sets optional variables for extensions.
        """
        return self.module_extra_extensions

    def make_module_req(self):
        """
        Generate the environment-variables to run the module.
        """
        requirements = self.make_module_req_guess()

        txt = "\n"
        for key in sorted(requirements):
            for path in requirements[key]:
                globbedPaths = glob.glob(os.path.join(self.installdir, path))
                txt += self.moduleGenerator.prepend_paths(key, globbedPaths)
        return txt

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.
        """
        return {
            'PATH': ['bin'],
            'LD_LIBRARY_PATH': ['lib', 'lib64'],
            'CPATH':['include'],
            'MANPATH': ['man', 'share/man'],
            'PKG_CONFIG_PATH' : ['lib/pkgconfig', 'share/pkgconfig'],
        }

    def load_fake_module(self):
        """
        Create and load fake module.
        """

        # make fake module
        mod_path = [self.make_module_step(True)]

        # load the module
        mod_path.extend(Modules().modulePath)
        m = Modules(mod_path)
        self.log.debug("created module instance")
        m.add_module([[self.name, self.get_installversion()]])
        m.load()

    #
    # EXTENSIONS UTILITY FUNCTIONS
    #

    def prepare_for_extensions(self):
        """
        Also do this before (eg to set the template)
        """
        pass

    def skip_extensions(self):
        """
        Called when self.skip is True
        - use this to detect existing extensions and to remove them from self.exts
        - based on initial R version
        """
        cmdtmpl = self.cfg['exts_filter'][0]
        cmdinputtmpl = self.cfg['exts_filter'][1]

        res = []
        for ext in self.exts:
            name = ext['name']
            if name in self.cfg['exts_modulenames']:
                modname = self.cfg['exts_modulenames'][name]
            else:
                modname = name
            tmpldict = {'name':modname,
                       'version':ext.get('version'),
                       'src':ext.get('source')
                       }
            cmd = cmdtmpl % tmpldict
            if cmdinputtmpl:
                stdin = cmdinputtmpl % tmpldict
                (cmdStdouterr, ec) = run_cmd(cmd, log_all=False, log_ok=False, simple=False, inp=stdin, regexp=False)
            else:
                (cmdStdouterr, ec) = run_cmd(cmd, log_all=False, log_ok=False, simple=False, regexp=False)
            if ec:
                self.log.info("Not skipping %s" % name)
                self.log.debug("exit code: %s, stdout/err: %s" % (ec, cmdStdouterr))
                res.append(ext)
            else:
                self.log.info("Skipping %s" % name)
        self.exts = res

    #
    # MISCELLANEOUS UTILITY FUNCTIONS
    #

    def det_installsize(self):
        installsize = 0
        try:
            # change to home dir, to avoid that cwd no longer exists
            os.chdir(os.getenv('HOME'))

            # walk install dir to determine total size
            for (dirpath, _, filenames) in os.walk(self.installdir):
                for filename in filenames:
                    fullpath = os.path.join(dirpath, filename)
                    if os.path.exists(fullpath):
                        installsize += os.path.getsize(fullpath)
        except OSError, err:
            self.log.warn("Could not determine install size: %s" % err)

        return installsize

    def get_installversion(self):
        return self.cfg.get_installversion()

    def guess_start_dir(self):
        """
        Return the directory where to start the whole configure/make/make install cycle from
        - typically self.src[0]['finalpath']
        - start_dir option
        -- if abspath: use that
        -- else, treat it as subdir for regular procedure
        """
        tmpdir = ''
        if self.cfg['start_dir']:
            tmpdir = self.cfg['start_dir']

        if not os.path.isabs(tmpdir):
            if len(self.src) > 0 and not self.skip:
                self.cfg['start_dir'] = os.path.join(self.src[0]['finalpath'], tmpdir)
            else:
                self.cfg['start_dir'] = os.path.join(self.builddir, tmpdir)

        try:
            os.chdir(self.cfg['start_dir'])
            self.log.debug("Changed to real build directory %s" % (self.cfg['start_dir']))
        except OSError, err:
            self.log.exception("Can't change to real build directory %s: %s" % (self.cfg['start_dir'], err))

    def print_environ(self):
        """
        Prints the environment changes and loaded modules to the debug log
        - pretty prints the environment for easy copy-pasting
        """
        mods = [(mod['name'], mod['version']) for mod in Modules().loaded_modules()]
        mods_text = "\n".join(["module load %s/%s" % m for m in mods if m not in self.loaded_modules])
        self.loaded_modules = mods

        env = copy.deepcopy(os.environ)

        changed = [(k, env[k]) for k in env if k not in self.orig_environ]
        for k in env:
            if k in self.orig_environ and env[k] != self.orig_environ[k]:
                changed.append((k, env[k]))

        unset = [key for key in self.orig_environ if key not in env]

        text = "\n".join(['export %s="%s"' % change for change in changed])
        unset_text = "\n".join(['unset %s' % key for key in unset])

        if mods:
            self.log.debug("Loaded modules:\n%s" % mods_text)
        if changed:
            self.log.debug("Added to environment:\n%s" % text)
        if unset:
            self.log.debug("Removed from environment:\n%s" % unset_text)

        self.orig_environ = env

    def set_parallelism(self, nr=None):
        """
        Determines how many processes should be used (default: nr of procs - 1).
        """
        if not nr and self.cfg['parallel']:
            nr = self.cfg['parallel']

        if nr:
            try:
                nr = int(nr)
            except ValueError, err:
                self.log.error("Parallelism %s not integer: %s" % (nr, err))
        else:
            nr = get_core_count()
            ## check ulimit -u
            out, ec = run_cmd('ulimit -u')
            try:
                if out.startswith("unlimited"):
                    out = 2 ** 32 - 1
                maxuserproc = int(out)
                ## assume 6 processes per build thread + 15 overhead
                maxnr = int((maxuserproc - 15) / 6)
                if maxnr < nr:
                    nr = maxnr
                    self.log.info("Limit parallel builds to %s because max user processes is %s" % (nr, out))
            except ValueError, err:
                self.log.exception("Failed to determine max user processes (%s,%s): %s" % (ec, out, err))

        maxpar = self.cfg['maxparallel']
        if maxpar and maxpar < nr:
            self.log.info("Limiting parallellism from %s to %s" % (nr, maxpar))
            nr = min(nr, maxpar)

        self.cfg['parallel'] = nr
        self.log.info("Setting parallelism: %s" % nr)

    def verify_homepage(self):
        """
        Download homepage, verify if the name of the software is mentioned
        """
        homepage = self.cfg["homepage"]

        try:
            page = urllib.urlopen(homepage)
        except IOError:
            self.log.error("Homepage (%s) is unavailable." % homepage)
            return False

        regex = re.compile(self.name, re.I)

        # if url contains software name and is available we are satisfied
        if regex.search(homepage):
            return True

        # Perform a lowercase compare against the entire contents of the html page
        # (does not care about html)
        for line in page:
            if regex.search(line):
                return True
        return False


    #
    # STEP FUNCTIONS
    #

    def check_readiness_step(self):
        """
        Verify if all is ok to start build.
        """

        # Check whether modules are loaded
        loadedmods = Modules().loaded_modules()
        if len(loadedmods) > 0:
            self.log.warning("Loaded modules detected: %s" % loadedmods)

        # Do all dependencies have a toolchain version
        self.toolchain.add_dependencies(self.cfg.dependencies())
        if not len(self.cfg.dependencies()) == len(self.toolchain.dependencies):
            self.log.debug("dep %s (%s)" % (len(self.cfg.dependencies()), self.cfg.dependencies()))
            self.log.debug("tc.dep %s (%s)" % (len(self.toolchain.dependencies), self.toolchain.dependencies))
            self.log.error('Not all dependencies have a matching toolchain version')

        # Check if the application is not loaded at the moment
        (root, env_var) = get_software_root(self.name, with_env_var=True)
        if root:
            self.log.error("Module is already loaded (%s is set), installation cannot continue." % env_var)

        # Check if main install needs to be skipped
        # - if a current module can be found, skip is ok
        # -- this is potentially very dangerous
        if self.cfg['skip']:
            if Modules().exists(self.name, self.get_installversion()):
                self.skip = True
                self.log.info("Current version (name: %s, version: %s) found." % (self.name, self.get_installversion))
                self.log.info("Going to skip actually main build and potential existing extensions. Expert only.")
            else:
                self.log.info("No current version (name: %s, version: %s) found. Not skipping anything." % (self.name,
                    self.get_installversion()))

    def fetch_step(self):
        """
        prepare for building
        """

        ## check EasyBuild version
        easybuildVersion = self.cfg['easybuildVersion']
        if not easybuildVersion:
            self.log.warn("Easyconfig does not specify an EasyBuild-version (key 'easybuildVersion')! Assuming the latest version")
        else:
            if LooseVersion(easybuildVersion) < easybuild.VERSION:
                self.log.warn("EasyBuild-version %s is older than the currently running one. Proceed with caution!" % easybuildVersion)
            elif LooseVersion(easybuildVersion) > easybuild.VERSION:
                self.log.error("EasyBuild-version %s is newer than the currently running one. Aborting!" % easybuildVersion)

        # fetch sources
        if self.cfg['sources']:
            self.fetch_sources(self.cfg['sources'])
        else:
            self.log.info('no sources provided')

        # fetch patches
        if self.cfg['patches']:
            self.fetch_patches(self.cfg['patches'])
        else:
            self.log.info('no patches provided')

        # set level of parallelism for build
        self.set_parallelism()

        # create parent dirs in install and modules path already
        # this is required when building in parallel
        pardirs = [os.path.join(install_path(), self.name),
                   os.path.join(install_path('mod'), GENERAL_CLASS, self.name),
                   os.path.join(install_path('mod'), self.cfg['moduleclass'], self.name)]
        self.log.info("Checking dirs that need to be created: %s" % pardirs)
        try:
            for pardir in pardirs:
                if not os.path.exists(pardir):
                    os.makedirs(pardir)
                    self.log.debug("Created directory %s" % pardir)
                else:
                    self.log.debug("Not creating %s, it already exists." % pardir)
        except OSError, err:
            self.log.error("Failed to create parent dirs in install and modules path: %s" % err)

    def checksum_step(self):
        """Verify checksum of sources, if available."""
        pass

    def extract_step(self):
        """
        Unpack the source files.
        """
        for tmp in self.src:
            self.log.info("Unpacking source %s" % tmp['name'])
            srcdir = extract_file(tmp['path'], self.builddir, extra_options=self.cfg['unpackOptions'])
            if srcdir:
                self.src[self.src.index(tmp)]['finalpath'] = srcdir
            else:
                self.log.error("Unpacking source %s failed" % tmp['name'])

    def patch_step(self, beginpath=None):
        """
        Apply the patches
        """
        for tmp in self.patches:
            self.log.info("Applying patch %s" % tmp['name'])

            copy = False
            ## default: patch first source
            srcind = 0
            if 'source' in tmp:
                srcind = tmp['source']
            srcpathsuffix = ''
            if 'sourcepath' in tmp:
                srcpathsuffix = tmp['sourcepath']
            elif 'copy' in tmp:
                srcpathsuffix = tmp['copy']
                copy = True

            if not beginpath:
                beginpath = self.src[srcind]['finalpath']

            src = os.path.abspath("%s/%s" % (beginpath, srcpathsuffix))

            level = None
            if 'level' in tmp:
                level = tmp['level']

            if not apply_patch(tmp['path'], src, copy=copy, level=level):
                self.log.error("Applying patch %s failed" % tmp['name'])

    def prepare_step(self):
        """
        Pre-configure step. Set's up the builddir just before starting configure
        """
        self.toolchain.prepare(self.cfg['onlytcmod'])
        self.guess_start_dir()

    def configure_step(self):
        """Configure build  (abstract method)."""
        raise NotImplementedError

    def build_step(self):
        """Build software  (abstract method)."""
        raise NotImplementedError

    def test_step(self):
        """Run unit tests provided by software (if any)."""
        if self.cfg['runtest']:
          
            self.log.debug("Trying to execute %s as a command for running unit tests...") 
            (out, _) = run_cmd(self.cfg['runtest'], log_all=True, simple=False)

            return out

    def stage_install_step(self):
        """
        Install in a stage directory before actual installation.
        """
        pass

    def install_step(self):
        """Install built software (abstract method)."""
        raise NotImplementedError

    def extensions_step(self):
        """
        After make install, run this.
        - only if variable len(exts_list) > 0
        - optionally: load module that was just created using temp module file
        - find source for extensions, in 'extensions' (and 'packages' for legacy reasons)
        - run extra_extensions
        """

        if len(self.cfg['exts_list']) == 0:
            self.log.debug("No extensions in exts_list")
            return

        if not self.skip:
            modpath = self.make_module_step(fake=True)
        # adjust MODULEPATH and load module
        if self.cfg['exts_loadmodule']:
            if self.skip:
                m = Modules()
            else:
                self.log.debug("Adding %s to MODULEPATH" % modpath)
                m = Modules([modpath] + os.environ['MODULEPATH'].split(':'))

            if m.exists(self.name, self.get_installversion()):
                m.add_module([[self.name, self.get_installversion()]])
                m.load()
            else:
                self.log.error("module %s version %s doesn't exist" % (self.name, self.get_installversion()))

        self.prepare_for_extensions()

        self.exts = self.fetch_extension_sources()

        if self.skip:
            self.skip_extensions()

        # actually install extensions
        exts_installdeps = self.cfg['exts_installdeps']
        self.log.debug("Installing extensions")
        exts_defaultclass = self.cfg['exts_defaultclass']
        if not exts_defaultclass:
            self.log.error("ERROR: No default extension class set for %s" % self.name)

        allclassmodule = exts_defaultclass[0]
        defaultClass = exts_defaultclass[1]
        for ext in self.exts:
            name = encode_class_name(ext['name']) # Use the same encoding as get_class
            self.log.debug("Starting extension %s" % name)

            try:
                exec("from %s import %s" % (allclassmodule, name))
                p = eval("%s(self,ext,exts_installdeps)" % name)
                self.log.debug("Installing extension %s through class %s" % (ext['name'], name))
            except (ImportError, NameError), err:
                self.log.debug("Couldn't load class %s for extension %s with extension deps %s:\n%s" % (name, ext['name'], exts_installdeps, err))
                if defaultClass:
                    self.log.info("No class found for %s, using default %s instead." % (ext['name'], defaultClass))
                    try:
                        exec("from %s import %s" % (allclassmodule, defaultClass))
                        exec("p=%s(self,ext,exts_installdeps)" % defaultClass)
                        self.log.debug("Installing extension %s through default class %s" % (ext['name'], defaultClass))
                    except (ImportError, NameError), errbis:
                        self.log.error("Failed to use both class %s and default %s for extension %s, giving up:\n%s\n%s" % (name, defaultClass, ext['name'], err, errbis))
                else:
                    self.log.error("Failed to use both class %s and no default class for extension %s, giving up:\n%s" % (name, ext['name'], err))

            ## real work
            p.prerun()
            txt = p.run()
            if txt:
                self.module_extra_extensions += txt
            p.postrun()
            # Append so we can make us of it later (in sanity_check)
            self.ext_instances.append(p)


    def package_step(self):
        """Package software (e.g. into an RPM)."""
        pass

    def post_install_step(self):
        """
        Do some postprocessing
        - set file permissions ....
        Installing user must be member of the group that it is changed to
        """
        if self.cfg['group']:

            gid = grp.getgrnam(self.cfg['group'])[2]
            # rwx for owner, r-x for group, --- for other
            try:
                adjust_permissions(self.installdir, 0750, recursive=True, group_id=gid, relative=False, 
                                   ignore_errors=True)
            except EasyBuildError, err:
                self.log.error("Unable to change group permissions of file(s). " \
                               "Are you a member of this group?\n%s" % err)
            self.log.info("Successfully made software only available for group %s" % self.cfg['group'])

        else:
            # remove write permissions for group and other
            perms = stat.S_IWGRP | stat.S_IWOTH
            adjust_permissions(self.installdir, perms, add=False, recursive=True, relative=True, ignore_errors=True)
            self.log.info("Successfully removed write permissions recursively for group/other on install dir.")

        if read_only_installdir():
            # remove write permissions for everyone
            perms = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
            adjust_permissions(self.installdir, perms, add=False, recursive=True, relative=True, ignore_errors=True)
            self.log.info("Successfully removed write permissions recursively for *EVERYONE* on install dir.")

    def sanity_check_step(self, custom_paths=None, custom_commands=None):
        """
        Do a sanity check on the installation
        - if *any* of the files/subdirectories in the installation directory listed
          in sanityCheckPaths are non-existent (or empty), the sanity check fails
        """
        # prepare sanity check paths
        paths = self.cfg['sanityCheckPaths']
        if not paths:
            if custom_paths:
                paths = custom_paths
                self.log.info("Using customized sanity check paths: %s" % paths)
            else:
                paths = {
                         'files':[],
                         'dirs':["bin", "lib"]
                        }
                self.log.info("Using default sanity check paths: %s" % paths)
        else:
            self.log.info("Using specified sanity check paths: %s" % paths)

        # check sanity check paths
        ks = paths.keys()
        ks.sort()
        valnottypes = [type(x) != list for x in paths.values()]
        lenvals = [len(x) for x in paths.values()]
        if not ks == ["dirs", "files"] or sum(valnottypes) > 0 or sum(lenvals) == 0:
            self.log.error("Incorrect format for sanityCheckPaths (should only have 'files' and 'dirs' keys, " \
                           "values should be lists (at least one non-empty)).")

        self.sanityCheckOK = True

        # check if files exist
        for f in paths['files']:
            p = os.path.join(self.installdir, f)
            if not os.path.exists(p):
                self.log.debug("Sanity check: did not find file %s in %s" % (f, self.installdir))
                self.sanityCheckOK = False
                break
            else:
                self.log.debug("Sanity check: found file %s in %s" % (f, self.installdir))

        if self.sanityCheckOK:
            # check if directories exist, and whether they are non-empty
            for d in paths['dirs']:
                p = os.path.join(self.installdir, d)
                if not os.path.isdir(p) or not os.listdir(p):
                    self.log.debug("Sanity check: did not find non-empty directory %s in %s" % (d, self.installdir))
                    self.sanityCheckOK = False
                    break
                else:
                    self.log.debug("Sanity check: found non-empty directory %s in %s" % (d, self.installdir))

        try:
            self.load_fake_module()
        except EasyBuildError, err:
            self.log.debug("Loading fake module failed: %s" % err)
            self.sanityCheckOK = False

        # chdir to installdir (better environment for running tests)
        os.chdir(self.installdir)

        # run sanity check commands
        commands = self.cfg['sanityCheckCommands']
        self.log.info("Using specified sanity check paths: %s" % commands)
        if not commands:
            if custom_commands:
                commands = custom_commands
                self.log.info("Using customised sanity check commands: %s" % commands)
            else:
                commands = []
        for command in commands:
            # set command to default. This allows for config files with
            # non-tuple commands
            if not isinstance(command, tuple):
                self.log.debug("Setting sanity check command to default")
                command = (None, None)

            # Build substition dictionary
            check_cmd = { 'name': self.name.lower(), 'options': '-h' }

            if command[0] != None:
                check_cmd['name'] = command[0]

            if command[1] != None:
                check_cmd['options'] = command[1]

            cmd = "%(name)s %(options)s" % check_cmd

            out, ec = run_cmd(cmd, simple=False)
            if ec != 0:
                self.sanityCheckOK = False
                self.log.warning("sanityCheckCommand %s exited with code %s (output: %s)" % (cmd, ec, out))
            else:
                self.log.info("sanityCheckCommand %s ran successfully! (output: %s)" % (cmd, out))

        failed_exts = [ext.name for ext in self.ext_instances if not ext.sanity_check_step()]

        if failed_exts:
            self.log.info("Sanity check for extensions %s failed!" % failed_exts)
            self.sanityCheckOK = False

        # pass or fail
        if not self.sanityCheckOK:
            self.log.error("Sanity check failed!")
        else:
            self.log.debug("Sanity check passed!")

    def cleanup_step(self):
        """
        Cleanup leftover mess: remove/clean build directory

        except when we're building in the installation directory,
        otherwise we remove the installation
        """
        if not self.build_in_installdir:
            try:
                shutil.rmtree(self.builddir)
                base = os.path.dirname(self.builddir)

                # keep removing empty directories until we either find a non-empty one
                # or we end up in the root builddir
                while len(os.listdir(base)) == 0 and not os.path.samefile(base, build_path()):
                    os.rmdir(base)
                    base = os.path.dirname(base)

                self.log.info("Cleaning up builddir %s" % (self.builddir))
            except OSError, err:
                self.log.exception("Cleaning up builddir %s failed: %s" % (self.builddir, err))

    def make_module_step(self, fake=False):
        """
        Generate a module file.
        """
        self.moduleGenerator = ModuleGenerator(self, fake)
        modpath = self.moduleGenerator.create_files()

        txt = ''
        txt += self.make_module_description()
        txt += self.make_module_dep()
        txt += self.make_module_req()
        txt += self.make_module_extra()
        if self.cfg['exts_list']:
            txt += self.make_module_extra_extensions()
        txt += '\n# built with EasyBuild version %s\n' % easybuild.VERBOSE_VERSION

        try:
            f = open(self.moduleGenerator.filename, 'w')
            f.write(txt)
            f.close()
        except IOError, err:
            self.log.error("Writing to the file %s failed: %s" % (self.moduleGenerator.filename, err))

        self.log.info("Added modulefile: %s" % (self.moduleGenerator.filename))

        if not fake:
            self.make_devel_module()

        return modpath

    def test_cases_step(self):
        """
        Run provided test cases.
        """
        for test in self.cfg['tests']:
            # Current working dir no longer exists
            os.chdir(self.installdir)
            if os.path.isabs(test):
                path = test
            else:
                path = os.path.join(source_path(), self.name, test)

            try:
                self.log.debug("Running test %s" % path)
                run_cmd(path, log_all=True, simple=True)
            except EasyBuildError, err:
                self.log.exception("Running test %s failed: %s" % (path, err))

    def run_step(self, step, methods, skippable=False):
        """
        Run step, returns false when execution should be stopped
        """
        if skippable and self.skip:
            self.log.info("Skipping %s step" % step)
        else:
            self.log.info("Starting %s step" % step)
            for m in methods:
                m(self)

        if self.cfg['stop'] == step:
            self.log.info("Stopping after %s step." % step)
            raise StopException(step)

    def get_steps(self, run_test_cases=True):
        """Return a list of all steps to be performed."""

        steps = [
                  # stop name: (description, list of functions, skippable)
                  ('fetch', 'fetching files', [lambda x: x.fetch_step()], False),
                  ('ready', "getting ready, creating build dir, resetting environment",
                   [lambda x: x.check_readiness_step(), lambda x: x.gen_installdir(),
                    lambda x: x.make_builddir(), lambda x: env.reset_changes()],
                   False),
                  ('source', 'unpacking', [lambda x: x.checksum_step(),
                                           lambda x: x.extract_step()], True),
                  ('patch', 'patching', [lambda x: x.patch_step()], True),
                  ('prepare', 'preparing', [lambda x: x.prepare_step()], False),
                  ('configure', 'configuring', [lambda x: x.configure_step()], True),
                  ('build', 'building', [lambda x: x.build_step()], True),
                  ('test', 'testing', [lambda x: x.test_step()], True),
                  ('install', 'installing', [
                                             lambda x: x.stage_install_step(),
                                             lambda x: x.make_installdir(),
                                             lambda x: x.install_step(),
                                             ],
                   True),
                  ('extensions', 'taking care of extensions', [lambda x: x.extensions_step()], False),
                  ('package', 'packaging', [lambda x: x.package_step()], True),
                  ('postproc', 'postprocessing', [lambda x: x.post_install_step()], True),
                  ('sanitycheck', 'sanity checking', [lambda x: x.sanity_check_step()], False),
                  ('cleanup', 'cleaning up', [lambda x: x.cleanup_step()], False),
                  ('module', 'creating module', [lambda x: x.make_module_step()], False),
                  ]

        if run_test_cases and self.cfg['tests']:
            steps.append(('testcases', 'running test cases', [lambda x: x.test_cases_step()], False))
        else:
            self.log.debug('Skipping test cases')

        return steps

    def run_all_steps(self, run_test_cases, regtest_online):
        """
        Build and install this software.
        """
        if self.cfg['stop'] and self.cfg['stop'] == 'cfg':
            return True

        steps = self.get_steps(run_test_cases)

        try:
            for (stop_name, descr, step_methods, skippable) in steps:
                print_msg("%s..." % descr, self.log)
                self.run_step(stop_name, step_methods, skippable=skippable)

        except StopException:
            pass

        # return True for successfull build (or stopped build)
        return True


def get_class_for(modulepath, class_name):
    """
    Get class for a given class name and easyblock module path.
    """
    # >>> import pkgutil
    # >>> loader = pkgutil.find_loader('easybuild.apps.Base')
    # >>> d = loader.load_module('Base')
    # >>> c = getattr(d,'Likwid')
    # >>> c()
    m = __import__(modulepath, globals(), locals(), [''])
    try:
        c = getattr(m, class_name)
    except AttributeError:
        raise ImportError
    return c

def get_module_path(easyblock, generic=False):
    """
    Determine the module path for a given easyblock name,
    based on the encoded class name.
    """
    if not easyblock:
        return None

    # FIXME: we actually need a decoding function here,
    # i.e. from encoded class name to module name
    class_prefix = encode_class_name("")
    if easyblock.startswith(class_prefix):
        easyblock = easyblock[len(class_prefix):]

    # construct character translation table for module name
    # only 0-9, a-z, A-Z are retained, everything else is mapped to _
    charmap = 48*'_' + ''.join([chr(x) for x in range(48,58)]) # 0-9
    charmap += 7*'_' + ''.join([chr(x) for x in range(65,91)]) # A-Z
    charmap += 6*'_' + ''.join([chr(x) for x in range(97,123)]) + 133*'_' # a-z

    module_name = easyblock.translate(charmap)

    if generic:
        modpath = '.'.join(["easybuild", "easyblocks", "generic"])
    else:
        modpath = '.'.join(["easybuild", "easyblocks"])
    
    return '.'.join([modpath, module_name.lower()])

def get_class(easyblock, log, name=None):
    """
    Get class for a particular easyblock (or ConfigureMake by default)
    """

    app_mod_class = ("easybuild.easyblocks.generic.configuremake", "ConfigureMake")

    try:
        # if no easyblock specified, try to find if one exists
        if not easyblock:
            if not name:
                name = "UNKNOWN"
            # modulepath will be the namespace + encoded modulename (from the classname)
            modulepath = get_module_path(name)
            # The following is a generic way to calculate unique class names for any funny software title
            class_name = encode_class_name(name)

            # try and find easyblock
            try:
                log.debug("getting class for %s.%s" % (modulepath, class_name))
                cls = get_class_for(modulepath, class_name)
                log.info("Successfully obtained %s class instance from %s" % (class_name, modulepath))
                return cls
            except ImportError, err:
                # No easyblock could be found, so fall back to default class.

                log.warning("Failed to import easyblock for %s, falling back to default %s class: erro: %s" % \
                            (class_name, app_mod_class, err))
                (modulepath, class_name) = app_mod_class

        # something was specified, lets parse it
        else:
            class_name = easyblock.split('.')[-1]
            # figure out if full path was specified or not
            if len(easyblock.split('.')) > 1:
                log.info("Assuming that full easyblock module path was specified.")
                modulepath = easyblock
            else:
                modulepath = get_module_path(easyblock, generic=True)
                log.info("Derived full easyblock module path for %s: %s" % (class_name, modulepath))

        cls = get_class_for(modulepath, class_name)
        log.info("Successfully obtained %s class instance from %s" % (class_name, modulepath))
        return cls

    except Exception, err:
        log.error("Failed to obtain class for %s easyblock (not available?): %s" % (easyblock, err))
        raise EasyBuildError(str(err))

class StopException(Exception):
    """
    StopException class definition.
    """
    pass
