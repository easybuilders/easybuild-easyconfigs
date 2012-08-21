#!/usr/bin/env python
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
Main entry point for EasyBuild: build software from .eb input file
"""

import copy
import glob
import platform
import os
import re
import shutil
import sys
import tempfile
import time
from distutils.version import LooseVersion
from optparse import OptionParser, OptionGroup

import easybuild  # required for VERBOSE_VERSION
import easybuild.framework.easyconfig as easyconfig
import easybuild.tools.config as config
import easybuild.tools.filetools as filetools
import easybuild.tools.parallelbuild as parbuild
from easybuild.framework.application import get_class
from easybuild.framework.easyconfig import EasyConfig
from easybuild.tools.build_log import EasyBuildError, initLogger, \
    removeLogHandler, print_msg
from easybuild.tools.class_dumper import dumpClasses
from easybuild.tools.modules import Modules, searchModule
from easybuild.tools.config import getRepository
from easybuild.tools import systemtools


# applications use their own logger, we need to tell them to debug or not
# so this global variable is used.
LOGDEBUG = False

def add_cmdline_options(parser):
    """
    Add build options to options parser
    """
    # runtime options
    basic_options = OptionGroup(parser, "Basic options", "Basic runtime options for EasyBuild.")

    basic_options.add_option("-b", "--only-blocks", metavar="BLOCKS", help="Only build blocks blk[,blk2]")
    basic_options.add_option("-d", "--debug" , action="store_true", help="log debug messages")
    basic_options.add_option("-f", "--force", action="store_true", dest="force",
                        help="force to rebuild software even if it's already installed (i.e. can be found as module)")
    basic_options.add_option("--job", action="store_true", help="will submit the build as a job")
    basic_options.add_option("-k", "--skip", action="store_true",
                        help="skip existing software (useful for installing additional packages)")
    basic_options.add_option("-l", action="store_true", dest="stdoutLog", help="log to stdout")
    basic_options.add_option("-r", "--robot", metavar="PATH",
                        help="path to search for easyconfigs for missing dependencies")
    basic_options.add_option("--regtest", action="store_true", help="enable regression test mode")
    basic_options.add_option("--regtest-online", action="store_true", help="enable online regression test mode")
    basic_options.add_option("-s", "--stop", type="choice", choices=EasyConfig.validstops,
                        help="stop the installation after certain step (valid: %s)" % ', '.join(EasyConfig.validstops))
    strictness_options = ['ignore', 'warn', 'error']
    basic_options.add_option("--strict", type="choice", choices=strictness_options, help="set strictness " + \
                               "level (possible levels: %s)" % ', '.join(strictness_options))

    parser.add_option_group(basic_options)

    # software build options
    software_build_options = OptionGroup(parser, "Software build options",
                                     "Specify software build options (overrides settings in easyconfig.")

    software_build_options.add_option("--software-name", metavar="NAME",
                                help="build software package with given name")
    software_build_options.add_option("--software-version", metavar="VERSION",
                                help="build software with this particular version")
    software_build_options.add_option("--software-versionprefix", metavar="PREFIX",
                                help="build software with this particular version prefix")
    software_build_options.add_option("--software-versionsuffix", metavar="SUFFIX",
                                help="build software with this particular version suffix")
    software_build_options.add_option("--toolkit", metavar="NAME,VERSION",
                                help="build with specified toolkit (name and version)")
    software_build_options.add_option("--toolkit-name", metavar="NAME",
                                help="build with specified toolkit name")
    software_build_options.add_option("--toolkit-version", metavar="VERSION",
                                help="build with specified toolkit version")
    software_build_options.add_option("--add-patches", metavar="PATCH_1[,PATCH_N]",
                                help="add additional patch files")

    parser.add_option_group(software_build_options)

    # override options
    override_options = OptionGroup(parser, "Override options", "Override default EasyBuild behavior.")
    
    override_options.add_option("-C", "--config",
                        help = "path to EasyBuild config file [default: $EASYBUILDCONFIG or easybuild/easybuild_config.py]")
    override_options.add_option("-e", "--easyblock", metavar="CLASS",
                        help="loads the class from module to process the spec file or dump " \
                               "the options for [default: Application class]")
    override_options.add_option("-p", "--pretend", action="store_true", help="does the build/installation in " \
                                "a test directory located in $HOME/easybuildinstall [default: $EASYBUILDINSTALLDIR " \
                                "or installiPath in EasyBuild config file]")
    override_options.add_option("-t", "--skip-tests", action="store_true", help="skip testing")

    parser.add_option_group(override_options)

    # informative options
    informative_options = OptionGroup(parser, "Informative options",
                                      "Obtain information about EasyBuild.")

    informative_options.add_option("-a", "--avail-easyconfig-params", action="store_true",
                                   help="show available easyconfig parameters")
    informative_options.add_option("--dump-classes", action="store_true",
                                   help="show list of available classes")
    informative_options.add_option("--search", help="search for module-files in the robot-directory")
    informative_options.add_option("-v", "--version", action="store_true", help="show version")

    parser.add_option_group(informative_options)


def main():
    """
    Main function:
    - parse command line options
    - initialize logger
    - read easyconfig
    - build software
    """
    # disallow running EasyBuild as root
    if os.getuid() == 0:
        sys.stderr.write("ERROR: You seem to be running EasyBuild with root priveleges.\n" \
                        "That's not wise, so let's end this here.\n" \
                        "Exiting.\n")
        sys.exit(1)

    # options parser
    parser = OptionParser()

    parser.usage = "%prog [options] easyconfig [..]"
    parser.description = "Builds software package based on easyconfig (or parse a directory). " \
                         "Provide one or more easyconfigs or directories, use -h or --help more information."

    add_cmdline_options(parser)

    (options, paths) = parser.parse_args()

    # mkstemp returns (fd,filename), fd is from os.open, not regular open!
    fd, logFile = tempfile.mkstemp(suffix='.log', prefix='easybuild-')
    os.close(fd)

    if options.stdoutLog:
        os.remove(logFile)
        logFile = None

    global LOGDEBUG
    LOGDEBUG = options.debug

    configOptions = {}
    if options.pretend:
        configOptions['installPath'] = os.path.join(os.environ['HOME'], 'easybuildinstall')

    if options.only_blocks:
        blocks = options.only_blocks.split(',')
    else:
        blocks = None

    # initialize logger
    logFile, log, hn = initLogger(filename=logFile, debug=options.debug, typ="build")

    # show version
    if options.version:
        print_msg("This is EasyBuild %s" % easybuild.VERBOSE_VERSION, log)

    # initialize configuration
    # - check environment variable EASYBUILDCONFIG
    # - then, check command line option
    # - last, use default config file easybuild_config.py in build.py directory
    config_file = options.config

    if not config_file and os.getenv(config.environmentVariables['configFile']):
        config_file = os.getenv(config.environmentVariables['configFile'])
    else:
        appPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        config_file = os.path.join(appPath, "easybuild_config.py")
    config.init(config_file, **configOptions)

    # dump possible options
    if options.avail_easyconfig_params:
        print_avail_params(options.easyblock, log)

    # dump available classes
    if options.dump_classes:
        dumpClasses('easybuild.easyblocks')

    # search for modules
    if options.search:
        if not options.robot:
            error("Please provide a search-path to --robot when using --search")
        searchModule(options.robot, options.search)

    if options.avail_easyconfig_params or options.dump_classes or options.search or options.version:
        if logFile:
            os.remove(logFile)
        sys.exit(0)

    # set strictness of filetools module
    if options.strict:
        filetools.strictness = options.strict

    # process software build options, i.e.
    # software name/version, toolkit name/version, extra patches, ...
    software_build_options = process_software_build_options(options)

    # collect tweaks for easyconfig files
    easyconfig_tweaks = setup_easyconfig_tweaks(software_build_options)

    # read easyconfig files
    packages = []
    if len(paths) == 0:
        if software_build_options.has_key('name'):
            # if no easyconfig files/paths were provided, but we did get a software name,
            # we can try and find a suitable easyconfig ourselves, or generate one if we can
            paths = [find_best_matching_easyconfig(log, software_build_options,
                                                   options.robot, None, easyconfig_tweaks)]

        else:
            error("Please provide one or multiple easyconfig files, or use software build " \
                  "options to make EasyBuild search for easyconfigs", optparser=parser)

    for path in paths:
        path = os.path.abspath(path)
        if not (os.path.exists(path)):
            error("Can't find path %s" % path)

        try:
            files = findEasyconfigs(path, log)
            for eb_file in files:
                packages.extend(processEasyconfig(eb_file, log, blocks, tweaks=easyconfig_tweaks))
        except IOError, err:
            log.error("Processing easyconfigs in path %s failed: %s" % (path, err))

    # before building starts, take snapshot of environment (watch out -t option!)
    origEnviron = copy.deepcopy(os.environ)
    os.chdir(os.environ['PWD'])

    # skip modules that are already installed unless forced
    if not options.force:
        m = Modules()
        packages, checkPackages = [], packages
        for package in checkPackages:
            module = package['module']
            mod = "%s (version %s)" % (module[0], module[1])
            modspath = os.path.join(config.installPath("mod"), 'all')
            if m.exists(module[0], module[1], modspath):
                msg = "%s is already installed (module found in %s), skipping " % (mod, modspath)
                print_msg(msg, log)
                log.info(msg)
            else:
                log.debug("%s is not installed yet, so retaining it" % mod)
                packages.append(package)

    # determine an order that will allow all specs in the set to build
    if len(packages) > 0:
        print_msg("resolving dependencies ...", log)
        orderedSpecs = resolveDependencies(packages, options.robot, log, tweaks=easyconfig_tweaks)
    else:
        print_msg("No packages left to be built.", log)
        orderedSpecs = []

    if options.job:
        curdir = os.getcwd()
        easybuild_basedir = os.path.dirname(os.path.dirname(sys.argv[0]))
        eb_path = os.path.join(easybuild_basedir, "eb")

        # Reverse option parser -> string

        # the options to ignore
        ignore = map(parser.get_option, ['--robot', '--help', '--job'])

        # loop over all the different options.
        result_opts = []
        relevant_opts = [o for o in parser.option_list if o not in ignore]
        for opt in relevant_opts:
            value = getattr(options, opt.dest)
            # explicit check for None (some option are store_false)
            if value != None:
                # get_opt_string is not documented (but is a public method)
                name = opt.get_opt_string()
                if opt.action == 'store':
                    result_opts.append("%s %s" % (name, value))
                else:
                    result_opts.append(name)

        opts = ' '.join(result_opts)

        command = "cd %s && %s %%s %s" % (curdir, eb_path, opts)
        jobs = parbuild.build_packages_in_parallel(command, orderedSpecs, "easybuild-build", log)
        for job in jobs:
            print "%s: %s" % (job.name, job.jobid)

        log.info("Submitted parallel build jobs, exiting now")
        sys.exit(0)

    # build software, will exit when errors occurs (except when regtesting)
    correct_built_cnt = 0
    all_built_cnt = 0
    for spec in orderedSpecs:
        (success, _) = build(spec, options, log, origEnviron, 
                             exitOnFailure=(not options.regtest), tweaks=easyconfig_tweaks)
        if success:
            correct_built_cnt += 1
        all_built_cnt += 1

    print_msg("Build succeeded for %s out of %s" % (correct_built_cnt, all_built_cnt), log)

    getRepository().cleanup()
    # cleanup tmp log file (all is well, all modules have their own log file)
    try:
        removeLogHandler(hn)
        hn.close()
        if logFile:
            os.remove(logFile)

        for package in packages:
            if 'originalSpec' in package:
                os.remove(package['spec'])

    except IOError, err:
        error("Something went wrong closing and removing the log %s : %s" % (logFile, err))

def error(message, exitCode=1, optparser=None):
    """
    Print error message and exit EasyBuild
    """
    print_msg("\nERROR: %s\n" % message)
    if optparser:
        optparser.print_help()
        print_msg("\nERROR: %s\n" % message)
    sys.exit(exitCode)

def findEasyconfigs(path, log):
    """
    Find .eb easyconfig files in path
    """
    if os.path.isfile(path):
        return [path]

    # walk through the start directory, retain all files that end in .eb
    files = []
    path = os.path.abspath(path)
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            if not f.endswith('.eb'):
                continue

            spec = os.path.join(dirpath, f)
            log.debug("Found easyconfig %s" % spec)
            files.append(spec)

    return files

def processEasyconfig(path, log, onlyBlocks=None, regtest_online=False, tweaks=None):
    """
    Process easyconfig, returning some information for each block
    """
    blocks = retrieveBlocksInSpec(path, log, onlyBlocks)

    packages = []
    for spec in blocks:
        # process for dependencies and real installversionname
        # - use mod? __init__ and importCfg are ignored.
        log.debug("Processing easyconfig %s" % spec)

        # create easyconfig
        try:
            ec = EasyConfig(spec)
            if tweaks:
                ec.tweak(tweaks)
        except EasyBuildError, err:
            msg = "Failed to process easyconfig %s:\n%s" % (spec, err.msg)
            log.exception(msg)

        name = ec['name']

        # this app will appear as following module in the list
        package = {
            'spec': spec,
            'module': (ec.name(), ec.installversion()),
            'dependencies': []
        }
        if len(blocks) > 1:
            package['originalSpec'] = path

        for d in ec.dependencies():
            dep = (d['name'], d['tk'])
            log.debug("Adding dependency %s for app %s." % (dep, name))
            package['dependencies'].append(dep)

        if ec.toolkit_name() != 'dummy':
            dep = (ec.toolkit_name(), ec.toolkit_version())
            log.debug("Adding toolkit %s as dependency for app %s." % (dep, name))
            package['dependencies'].append(dep)

        del ec

        # this is used by the parallel builder
        package['unresolvedDependencies'] = copy.copy(package['dependencies'])

        packages.append(package)

    return packages

def resolveDependencies(unprocessed, robot, log, tweaks=None):
    """
    Work through the list of packages to determine an optimal order
    """

    # get a list of all available modules (format: [(name, installversion), ...])
    availableModules = Modules().available()
    if len(availableModules) == 0:
        log.warning("No installed modules. Your MODULEPATH is probably incomplete.")

    orderedSpecs = []
    # All available modules can be used for resolving dependencies except
    # those that will be installed
    beingInstalled = [p['module'] for p in unprocessed]
    processed = [m for m in availableModules if not m in beingInstalled]

    # as long as there is progress in processing the modules, keep on trying
    loopcnt = 0
    maxloopcnt = 10000
    robotAddedDependency = True
    while robotAddedDependency:

        robotAddedDependency = False

        # make sure this stops, we really don't want to get stuck in an infinite loop
        loopcnt += 1
        if loopcnt > maxloopcnt:
            msg = "Maximum loop cnt %s reached, so quitting." % maxloopcnt
            log.error(msg)

        # first try resolving dependencies without using external dependencies
        lastProcessedCount = -1
        while len(processed) > lastProcessedCount:
            lastProcessedCount = len(processed)
            orderedSpecs.extend(findResolvedModules(unprocessed, processed, log))

        # robot: look for an existing dependency, add one
        if robot and len(unprocessed) > 0:

            beingInstalled = [p['module'] for p in unprocessed]

            for module in unprocessed:
                # do not choose a module that is being installed in the current run
                # if they depend, you probably want to rebuild them using the new dependency
                candidates = [d for d in module['dependencies'] if not d in beingInstalled]
                if len(candidates) > 0:
                    # find easyconfig, might not find any
                    path = robotFindEasyconfig(log, robot, candidates[0])

                else:
                    path = None
                    log.debug("No more candidate dependencies to resolve for module %s" % str(module['module']))

                if path:
                    log.info("Robot: resolving dependency %s with %s" % (candidates[0], path))

                    processedSpecs = processEasyconfig(path, log, tweaks=tweaks)

                    # ensure the pathname is equal to the module
                    mods = [spec['module'] for spec in processedSpecs]
                    if not candidates[0] in mods:
                        log.error("easyconfig file %s does not contain module %s" % (path, candidates[0]))

                    unprocessed.extend(processedSpecs)
                    robotAddedDependency = True
                    break

    # there are dependencies that cannot be resolved
    if len(unprocessed) > 0:
        log.debug("List of unresolved dependencies: %s" % unprocessed)
        missingDependencies = {}
        for module in unprocessed:
            for dep in module['dependencies']:
                missingDependencies[dep] = True

        msg = "Dependencies not met. Cannot resolve %s" % missingDependencies.keys()
        log.error(msg)

    log.info("Dependency resolution complete, building as follows:\n%s" % orderedSpecs)
    return orderedSpecs

def findResolvedModules(unprocessed, processed, log):
    """
    Find modules in unprocessed which can be fully resolved using packages in processed
    """
    orderedSpecs = []

    for module in unprocessed:
        module['dependencies'] = [d for d in module['dependencies'] if not d in processed]

        if len(module['dependencies']) == 0:
            log.debug("Adding easyconfig %s to final list" % module['spec'])
            orderedSpecs.append(module)
            processed.append(module['module'])

    unprocessed[:] = [m for m in unprocessed if len(m['dependencies']) > 0]

    return orderedSpecs

def create_paths(path, name, version):
    """
    returns all the paths where easyconfig could be located
    path is the basepath
    name should be a string
    version can be a '*' if you use glob patterns or otherwise an installversion
    """
    return [os.path.join(path, name, version + ".eb"),
            os.path.join(path, name, "%s-%s.eb" % (name, version)),
            os.path.join(path, name.lower()[0], name, "%s-%s.eb" % (name, version)),
            os.path.join(path, "%s-%s.eb" % (name, version)),
           ]

def process_software_build_options(options):
    """
    Create a dictionary with specified software build options.
    The options arguments should be a parsed option list (as delivered by OptionParser.parse_args)
    """

    buildopts = {}

    if options.software_name:
        buildopts.update({'name': options.software_name})

    if options.software_version:
        buildopts.update({'version': options.software_version})

    if options.software_versionprefix:
        buildopts.update({'versionprefix': options.software_versionprefix})

    if options.software_versionsuffix:
        buildopts.update({'versionsuffix': options.software_versionsuffix})

    if options.toolkit:
        tk = options.toolkit.split(',')
        if not len(tk) == 2:
            error("Please specify to toolkit to use as 'name,version' (e.g., 'goalf,1.1.0').")
        [toolkit_name, toolkit_version] = tk
        buildopts.update({'toolkit_name': toolkit_name})
        buildopts.update({'toolkit_version': toolkit_version})

    if options.toolkit_name:
        buildopts.update({'toolkit_name': options.toolkit_name})

    if options.toolkit_version:
        buildopts.update({'toolkit_version': options.toolkit_version})

    if options.add_patches:
        buildopts.update({'patches': options.add_patches.split(',')})

    return buildopts

def setup_easyconfig_tweaks(buildopts):
    """
    Create a list of tweaks for easyconfig files.

    Each tweak has the format (<function_name>, <value>), in which function_name is the name of
    EasyConfig class function that will be called with the given value
    """

    tweaks = []

    if buildopts.has_key('version'):
        tweaks.append(('set_version', buildopts['version']))

    if buildopts.has_key('versionprefix'):
        tweaks.append(('set_versionprefix', buildopts['versionprefix']))

    if buildopts.has_key('versionsuffix'):
        tweaks.append(('set_versionsuffix', buildopts['versionsuffix']))

    if buildopts.has_key('toolkit_name'):
        tweaks.append(('set_toolkit_name', buildopts['toolkit_name']))

    if buildopts.has_key('toolkit_version'):
        tweaks.append(('set_toolkit_version', buildopts['toolkit_version']))

    if buildopts.has_key('patches'):
        tweaks.append(('add_patches', buildopts['patches']))

    return tweaks

def find_best_matching_easyconfig(log, buildopts, robot, fp, easyconfig_tweaks):

    # collect paths to search in
    paths = []
    if robot:
        paths.append(robot)

    if not paths:
        log.error("No paths to look for easyconfig files, specify a path with --robot.")

    # create glob patterns based on supplied info

    reqs = {}
    for key in ['name', 'version', 'toolkit_name', 'toolkit_version', 'versionprefix', 'versionsuffix']:
        reqs.update({key: buildopts.get(key)})

    # figure out the install version
    installver = easyconfig.det_installversion(reqs['version'] or '*', reqs['toolkit_name'] or '*',
                                               reqs['toolkit_version'] or '*',
                                               reqs['versionprefix'] or '*',
                                               reqs['versionsuffix'] or '*')

    # find easyconfigs that match a pattern
    easyconfig_files = []
    for path in paths:
        patterns = create_paths(path, reqs['name'], installver)
        for pattern in patterns:
            easyconfig_files.extend(glob.glob(pattern))

    cnt = len(easyconfig_files)

    log.debug("List of obtained easyconfig files (%d): %s" % (cnt, easyconfig_files))

    # select best easyconfig, or try to generate one that fits the requirements

    if cnt > 0:
        # one or multiple matches, so select one
        if cnt == 1:
            log.info("Found a single exact match (%s), so using it." % easyconfig_files[0])
            return easyconfig_files[0]
    
        else:
            (ok, res) = select_best_easyconfig(easyconfig_files, reqs, log)
            if ok:
                return res
            else:
                log.error("Failed to further select from the list of %s files: %s" % (len(res), res))

    else:
        # no matches found, so we'll try and generate an easyconfig file
        (ok, res) = generate_easyconfig(fp, paths, reqs, easyconfig_tweaks, log)
        if ok:
            return res
        else:
            log.error("No easyconfig found for requested software, and also failed to generate one.")

def select_best_easyconfig(ec_files, reqs, log):
    """Select the best easyconfig given the specifications."""

    # if no software version was specified, only retain most recent software version
    if not reqs['version']:
        easyconfigs = [EasyConfig(f, validate=False) for f in ec_files]
        versions = sorted([LooseVersion(ec['version']) for ec in easyconfigs])

        if len(versions) > 1:
            log.debug("sorted software versions: %s" % versions)
            print "No software version specified, so only retaining last version %s" % versions[-1]

            def retain(eb_file):
                ec = EasyConfig(eb_file, validate=False)
                return LooseVersion(ec['version']) == versions[-1]
    
            ec_files = [f for f in ec_files if retain(f)]

    # if no toolkit was specified without version, only retain most recent toolkit versions
    if reqs['toolkit_name'] and not reqs['toolkit_version']:
        easyconfigs = [EasyConfig(f, validate=False) for f in ec_files]
        tkversions = sorted([LooseVersion(ec['toolkit']['version']) for ec in easyconfigs])

        if len(tkversions) > 1:
            log.debug("sorted toolkit versions: %s" % tkversions)
            print "No toolkit version specified, so only retaining last version" \
                  " %s-%s" % (reqs['toolkit_name'], tkversions[-1])
    
            def retain(eb_file):
                ec = EasyConfig(eb_file, validate=False)
                return LooseVersion(ec['toolkit']['version']) == tkversions[-1]

            ec_files = [f for f in ec_files if retain(f)]

    cnt = len(ec_files)
    log.debug("Retained %s easyconfig files: %s" % (cnt, ec_files))

    if len(ec_files) == 1:
        res = ec_files[0]
        print "Selected easyconfig file %s to build requested software" % res
        log.info("Selected %s from list of %d files." % (res, cnt))
        return (True, res)
    else:
        return (False, ec_files)

def generate_easyconfig(fp, paths, reqs, easyconfig_tweaks, log):
    """
    Generate an easyconfig file with the given requirements, based on existing config files.

    If easyconfig files are available for the specified software package,
    then this function will first try to determine which toolkit to use.
     * if a toolkit is given, it will use that (possible using a template easyconfig file as base);
     * if not, and only a single toolkit is available, is will assume it can use that toolkit
     * else, it fails -- EasyBuild doesn't select between multiple available toolkits

    Next, it will trim down the selection of easyconfig files to a single one,
    based on the following requirements (in order of preference):
     * toolkit version: it will use an easyconfig file
     * software version:
     * versionprefix:
     * versionsuffix:
    """

    # find ALL available easyconfigs for specified software
    ec_files = []
    installver = easyconfig.det_installversion('*', 'dummy', '*', '*', '*')
    for path in paths:
        patterns = create_paths(path, reqs['name'], installver)
        for pattern in patterns:
            ec_files.extend(glob.glob(pattern))

    # we need at least one config file to start from
    if len(ec_files) == 0:
        log.error("No easyconfig files found for software %s, I'm all out of ideas." % reqs['name'])

    easyconfigs = [EasyConfig(f, validate=False) for f in ec_files]

    def unique(l):  # no such function available in Python?!?
        """Retain unique elements in a sorted list."""
        l2 = [l[0]]
        for x in l:
            if not x in l2:
                l2.append(x)
        return l2


    # TOOLKIT NAME

    tkname = None

    # determine list of unique toolkit names
    tknames = unique(sorted([ec['toolkit']['name'] for ec in easyconfigs]))
    log.debug("Found %d unique toolkit names: %s" % (len(tknames), tknames))

    # if multiple toolkits are available, and none is specified, we quit
    # we can't just pick one, how would we prefer one over the other?
    if len(tknames) > 1 and not reqs['toolkit_name']:
        log.error("No toolkit specified, and easyconfig files found for more than one toolkit.")

    # if a toolkit was selected, and we have no easyconfig files for it, try and use a template
    if reqs['toolkit_name'] and not reqs['toolkit_name'] in tknames:
        if "TEMPLATE" in tknames:
            log.info("No easyconfig file for specified toolkit, but template is available.")
        else:
            log.error("No easyconfig file for %s with toolkit %s, " \
                      "and no template available." % (reqs['name'], reqs['toolkit_name']))

    if not reqs['toolkit_name'] == "TEMPLATE":
        tkname = reqs['toolkit_name']

    # trim down list according to selected toolkit
    if tkname in tknames:
        # known toolkit, so only retain those
        easyconfigs = [ec for ec in easyconfigs if ec['toolkit']['name'] == tkname]
    else:
        if len(tknames) == 1 and not tknames[0] == "TEMPLATE":
            # only one (non-template) toolkit availble, so use that
            tkname = tknames[0]
            easyconfigs = [ec for ec in easyconfigs if ec['toolkit']['name'] == tkname]
        else:
            # fall-back: use template toolkit if a toolkit name was specified
            if tkname:
                easyconfigs = [ec for ec in easyconfigs if ec['toolkit']['name'] == "TEMPLATE"]
            else:
                log.error("No toolkit name specified, and more than one available: %s." % tknames)

    log.debug("Filtered easyconfigs: %s" % [(ec['name'], ec['version'],
                                             ec['toolkit']['name'], ec['toolkit']['version'])
                                            for ec in easyconfigs])


    def pick_version(req_ver, avail_vers):
        """Pick version based on an optionally desired version and available versions.

        If a desired version is specifed, the most recent version that is less recent
        than the desired version will be picked; else, the most recent version will be picked.

        This function returns both the version to be used, which is equal to the desired version 
        if it was specified, and the version picked that matches that closest. 
        """
        if req_ver:
            # if a desired toolkit version is specified,
            # retain the most recent version that's less recent than the desired toolkit version

            ver = req_ver

            selected_ver = [v for v in avail_vers if v < LooseVersion(ver)][-1]

        else:
            # if no desired toolkit version is specified, just use last version
            ver = avail_vers[-1]
            selected_ver = ver

        return (ver, selected_ver)


    # TOOLKIT VERSION

    tkvers = unique(sorted([ec['toolkit']['version'] for ec in easyconfigs]))
    log.debug("Found %d unique toolkit versions: %s" % (len(tkvers), tkvers))

    (tkver, selected_tkv) = pick_version(reqs['toolkit_version'], tkvers)

    log.debug("Filtering easyconfigs based on toolkit version '%s'..." % selected_tkv)
    easyconfigs = [ec for ec in easyconfigs if ec['toolkit']['version'] == selected_tkv]
    log.debug("Filtered easyconfigs: %s" % [(ec['name'], ec['version'],
                                             ec['toolkit']['name'], ec['toolkit']['version'])
                                            for ec in easyconfigs])

    # SOFTWARE VERSION

    vers = unique(sorted([ec['version'] for ec in easyconfigs]))
    log.debug("Found %d unique software versions: %s" % (len(vers), vers))

    (ver, selected_ver)= pick_version(reqs['version'], vers)

    log.debug("Filtering easyconfigs based on software version '%s'..." % selected_ver)
    easyconfigs = [ec for ec in easyconfigs if ec['version'] == selected_ver]
    log.debug("Filtered easyconfigs: %s" % [(ec['name'], ec['version'],
                                             ec['toolkit']['name'], ec['toolkit']['version'])
                                            for ec in easyconfigs])

    # SOFTWARE VERSION PREFIX and SUFFIX

    for fix in ['prefix', 'suffix']:

        verfixs = unique([ec['version%s' % fix] for ec in easyconfigs])

        verfix = None
        if reqs['version%s' % fix]:
            verfix = reqs['version%s' % fix]
        else:
            if len(verfixs) == 1:
                verfix = verfixs[0]
            else:
                log.error("No version %s specified, and multiple ones available: %s" % (fix, verfixs))

        log.debug("Filtering easyconfigs based on version %s '%s'..." % (fix, verfix))
        easyconfigs = [ec for ec in easyconfigs if ec['version%s' % fix] == verfix]
        log.debug("Filtered easyconfigs: %s" % [(ec['name'], ec['version'],
                                                 ec['toolkit']['name'], ec['toolkit']['version'])
                                                for ec in easyconfigs])

        if fix == "prefix":
            verpref = fix
        elif fix == "suffix":
            versuff = fix
        else:
            log.error("FAIL: neither prefix nor suffix?!?")

    cnt = len(easyconfigs)
    if not cnt == 1:
        log.error("Failed to select a single easyconfig from available ones, %s left." % cnt)

    else:
        # GENERATE

        # if no file path was specified, generate a file name
        if not fp:
            installver = easyconfig.det_installversion(ver, tkname, tkver, verpref, versuff)
            fp= "%s%s.eb" % (reqs['name'], installver)

        # generate easyconfig and dump it to file
        selected_easyconfig = easyconfigs[0]
        # FIXME: just tweaking is not sufficient, e.g. when version is changed also sources is,
        #        and possibly dependencies, patch files, ... as well
        # so, we need to perform regexp substitutions on the origin easyconfig file, and assume
        # they are well written, i.e. that versions aren't hard-coded in dependencies, sources, ...
        selected_easyconfig.tweak(easyconfig_tweaks)
        selected_easyconfig.dump(fp)

        log.info("Generated easyconfig file %s, and using it to build the requested software." % fp)

        return (True, fp)

def robotFindEasyconfig(log, path, module):
    """
    Find an easyconfig for module in path
    """
    name, version = module
    # candidate easyconfig paths
    easyconfigsPaths = create_paths(path, name, version)
    for easyconfigPath in easyconfigsPaths:
        log.debug("Checking easyconfig path %s" % easyconfigPath)
        if os.path.isfile(easyconfigPath):
            log.debug("Found easyconfig file for %s at %s" % (module, easyconfigPath))
            return os.path.abspath(easyconfigPath)

    return None

def retrieveBlocksInSpec(spec, log, onlyBlocks):
    """
    Easyconfigs can contain blocks (headed by a [Title]-line)
    which contain commands specific to that block. Commands in the beginning of the file
    above any block headers are common and shared between each block.
    """
    regBlock = re.compile(r"^\s*\[([\w.-]+)\]\s*$", re.M)
    regDepBlock = re.compile(r"^\s*block\s*=(\s*.*?)\s*$", re.M)

    cfgName = os.path.basename(spec)
    pieces = regBlock.split(open(spec).read())

    # the first block contains common statements
    common = pieces.pop(0)
    if pieces:
        # make a map of blocks
        blocks = []
        while pieces:
            blockName = pieces.pop(0)
            blockContents = pieces.pop(0)

            if blockName in [b['name'] for b in blocks]:
                msg = "Found block %s twice in %s." % (blockName, spec)
                log.error(msg)

            block = {'name': blockName, 'contents': blockContents}

            # dependency block
            depBlock = regDepBlock.search(blockContents)
            if depBlock:
                dependencies = eval(depBlock.group(1))
                if type(dependencies) == list:
                    block['dependencies'] = dependencies
                else:
                    block['dependencies'] = [dependencies]

            blocks.append(block)

        # make a new easyconfig for each block
        # they will be processed in the same order as they are all described in the original file
        specs = []
        for block in blocks:
            name = block['name']
            if onlyBlocks and not (name in onlyBlocks):
                print_msg("Skipping block %s-%s" % (cfgName, name))
                continue

            (fd, blockPath) = tempfile.mkstemp(prefix='easybuild-', suffix='%s-%s' % (cfgName, name))
            os.close(fd)
            try:
                f = open(blockPath, 'w')
                f.write(common)

                if 'dependencies' in block:
                    for dep in block['dependencies']:
                        if not dep in [b['name'] for b in blocks]:
                            msg = "Block %s depends on %s, but block was not found." % (name, dep)
                            log.error(msg)

                        dep = [b for b in blocks if b['name'] == dep][0]
                        f.write("\n# Dependency block %s" % (dep['name']))
                        f.write(dep['contents'])

                f.write("\n# Main block %s" % name)
                f.write(block['contents'])
                f.close()

            except Exception:
                msg = "Failed to write block %s to easyconfig %s" % (name, spec)
                log.exception(msg)

            specs.append(blockPath)

        log.debug("Found %s block(s) in %s" % (len(specs), spec))
        return specs
    else:
        # no blocks, one file
        return [spec]

def build(module, options, log, origEnviron, exitOnFailure=True, tweaks=None):
    """
    Build the software
    """
    spec = module['spec']

    print_msg("processing EasyBuild easyconfig %s" % spec, log)

    # restore original environment
    log.info("Resetting environment")
    filetools.errorsFoundInLog = 0
    if not filetools.modifyEnv(os.environ, origEnviron):
        error("Failed changing the environment back to original")

    cwd = os.getcwd()

    # load easyblock
    easyblock = options.easyblock
    if not easyblock:
        # try to look in .eb file
        reg = re.compile(r"^\s*easyblock\s*=(.*)$")
        for line in open(spec).readlines():
            match = reg.search(line)
            if match:
                easyblock = eval(match.group(1))
                break

    name = module['module'][0]
    try:
        app_class = get_class(easyblock, log, name=name)
        app = app_class(spec, debug=options.debug, easyconfig_tweaks=tweaks)
        log.info("Obtained application instance of for %s (easyblock: %s)" % (name, easyblock))
    except EasyBuildError, err:
        error("Failed to get application instance for %s (easyblock: %s): %s" % (name, easyblock, err.msg))

    # application settings
    if options.stop:
        log.debug("Stop set to %s" % options.stop)
        app.setcfg('stop', options.stop)

    if options.skip:
        log.debug("Skip set to %s" % options.skip)
        app.setcfg('skip', options.skip)

    # build easyconfig
    errormsg = '(no error)'
    # timing info
    starttime = time.time()
    try:
        result = app.autobuild(spec, runTests=not options.skip_tests, regtest_online=options.regtest_online)
    except EasyBuildError, err:
        lastn = 300
        errormsg = "autoBuild Failed (last %d chars): %s" % (lastn, err.msg[-lastn:])
        log.exception(errormsg)
        result = False

    ended = "ended"

    # successful build
    if result:

        # collect build stats
        log.info("Collecting build stats...")
        buildtime = round(time.time() - starttime, 2)
        installsize = 0
        try:
            # change to home dir, to avoid that cwd no longer exists
            os.chdir(os.getenv('HOME'))

            # walk install dir to determine total size
            for dirpath, _, filenames in os.walk(app.installdir):
                for filename in filenames:
                    fullpath = os.path.join(dirpath, filename)
                    if os.path.exists(fullpath):
                        installsize += os.path.getsize(fullpath)
        except OSError, err:
            log.error("Failed to determine install size: %s" % err)

        currentbuildstats = app.getcfg('buildstats')
        buildstats = {'build_time' : buildtime,
                 'platform' : platform.platform(),
                 'core_count' : systemtools.get_core_count(),
                 'cpu_model': systemtools.get_cpu_model(),
                 'install_size' : installsize,
                 'timestamp' : int(time.time()),
                 'host' : os.uname()[1],
                 }
        log.debug("Build stats: %s" % buildstats)

        if app.getcfg('stop'):
            ended = "STOPPED"
            newLogDir = os.path.join(app.builddir, config.logPath())
        else:
            newLogDir = os.path.join(app.installdir, config.logPath())

            try:
                # upload spec to central repository
                repo = getRepository()
                if 'originalSpec' in module:
                    repo.addEasyconfig(module['originalSpec'], app.name(), app.installversion() + ".block", buildstats, currentbuildstats)
                repo.addEasyconfig(spec, app.name(), app.installversion(), buildstats, currentbuildstats)
                repo.commit("Built %s/%s" % (app.name(), app.installversion()))
                del repo
            except EasyBuildError, err:
                log.warn("Unable to commit easyconfig to repository (%s)", err)

        exitCode = 0
        succ = "successfully"
        summary = "COMPLETED"

        # cleanup logs
        app.closelog()
        try:
            if not os.path.isdir(newLogDir):
                os.makedirs(newLogDir)
            applicationLog = os.path.join(newLogDir, os.path.basename(app.logfile))
            shutil.move(app.logfile, applicationLog)
        except IOError, err:
            error("Failed to move log file %s to new log file %s: %s" % (app.logfile, applicationLog, err))

        try:
            shutil.copy(spec, os.path.join(newLogDir, "%s-%s.eb" % (app.name(), app.installversion())))
        except IOError, err:
            error("Failed to move easyconfig %s to log dir %s: %s" % (spec, newLogDir, err))

    # build failed
    else:
        exitCode = 1
        summary = "FAILED"

        buildDir = ''
        if app.builddir:
            buildDir = " (build directory: %s)" % (app.builddir)
        succ = "unsuccessfully%s:\n%s" % (buildDir, errormsg)

        # cleanup logs
        app.closelog()
        applicationLog = app.logfile

    print_msg("%s: Installation %s %s" % (summary, ended, succ), log)

    # check for errors
    if exitCode > 0 or filetools.errorsFoundInLog > 0:
        print_msg("\nWARNING: Build exited with exit code %d. %d possible error(s) were detected in the " \
                  "build logs, please verify the build.\n" % (exitCode, filetools.errorsFoundInLog),
                  log)

    if app.postmsg:
        print_msg("\nWARNING: %s\n" % app.postmsg, log)

    print_msg("Results of the build can be found in the log file %s" % applicationLog, log)

    del app
    os.chdir(cwd)

    if exitCode > 0:
        # don't exit on failure in test suite
        if exitOnFailure:
            sys.exit(exitCode)
        else:
            return (False, applicationLog)
    else:
        return (True, applicationLog)

def print_avail_params(easyblock, log):
    app = get_class(easyblock, log)
    extra = app.extra_options()
    mapping = easyconfig.convert_to_help(EasyConfig.default_config + extra)

    for key, values in mapping.items():
        print "%s" % key.upper()
        print '-' * len(key)
        for name, value in values:
            tabs = "\t" * (3 - (len(name) + 1) / 8)
            print "%s:%s%s" % (name, tabs, value)

        print


if __name__ == "__main__":
    try:
        main()
    except EasyBuildError, e:
        sys.stderr.write('ERROR: %s\n' % e.msg)
        sys.exit(1)
