##
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
module for doing parallel builds. This uses a PBS-like cluster. You should be able to submit jobs (which can have
dependencies)

Support for PBS is provided via the PbsJob class. If you want you could create other job classes and use them here.
"""
import math
import os
import re

from easybuild.framework.application import get_class
from easybuild.tools.pbs_job import PbsJob
from easybuild.tools.config import getRepository


def build_packages_in_parallel(build_command, packages, output_dir, log):
    """
    packages is a list of packages which can be build! (e.g. they have no unresolved dependencies)
    this function will build them in parallel by submitting jobs

    returns the jobs
    """
    log.info("going to build these packages in parallel: %s", packages)
    job_module_dict = {}
    # dependencies have already been resolved this means one can linearly walk over the list and use previous job id's
    jobs = []
    for pkg in packages:
        # This is very important, otherwise we might have race conditions
        # e.g. GCC-4.5.3 finds cloog.tar.gz but it was incorrectly downloaded by GCC-4.6.3
        # running this step here, prevents this
        prepare_package(pkg, log)

        # the new job will only depend on already submitted jobs
        log.info("creating job for pkg: %s" % str(pkg))
        new_job = create_job(build_command, pkg, output_dir)
        # Sometimes unresolvedDependencies will contain things, not needed to be build.
        job_deps = [job_module_dict[dep] for dep in pkg['unresolvedDependencies'] if dep in job_module_dict]
        new_job.add_dependencies(job_deps)
        new_job.submit()
        log.info("job for module %s has been submitted (job id: %s)" % (new_job.module, new_job.jobid))
        # update dictionary
        job_module_dict[new_job.module] = new_job.jobid
        jobs.append(new_job)

    return jobs


def create_job(build_command, package, output_dir=""):
    """
    Creates a job, to build a *single* package
    build_command is a format string in which a full path to an eb file will be substituted
    package should be in the format as processEasyConfig returns them
    output_dir is an optional path. EASYBUILDTESTOUTPUT will be set inside the job with this variable
    returns the job
    """
    # create command based on build_command template
    command = build_command % package['spec']

    # capture PYTHONPATH, MODULEPATH and all variables starting with EASYBUILD
    easybuild_vars = {}
    for name in os.environ:
        if name.startswith("EASYBUILD"):
            easybuild_vars[name] = os.environ[name]

    others = ["PYTHONPATH", "MODULEPATH"]

    for env_var in others:
        if env_var in os.environ:
            easybuild_vars[env_var] = os.environ[env_var]

    # create unique name based on module name
    name = "%s-%s" % package['module']

    easybuild_vars['EASYBUILDTESTOUTPUT'] = os.path.join(os.path.abspath(output_dir), name)

    # just use latest build stats
    buildstats = getRepository().get_buildstats(*package['module'])
    resources = {}
    if buildstats:
        previous_time = buildstats[-1]['build_time']
        resources['hours'] = int(math.ceil(previous_time * 2 / 60))

    job = PbsJob(command, name, easybuild_vars, resources=resources)
    job.module = package['module']

    return job


def get_instance(package, log):
    """
    Get an instance for this package
    package is in the format provided by processEasyConfig
    log is a logger object

    returns an instance of Application (or subclass thereof)
    """
    spec = package['spec']
    name = package['module'][0]

    # handle easyconfigs with custom easyblocks
    easyblock = None
    reg = re.compile(r"^\s*easyblock\s*=(.*)$")
    for line in open(spec).readlines():
        match = reg.search(line)
        if match:
            easyblock = eval(match.group(1))
            break

    app_class = get_class(easyblock, log, name=name)
    return app_class(spec, debug=True)


def prepare_package(pkg, log):
    """ prepare for building """
    try:
        instance = get_instance(pkg, log)
        instance.prepare_build()
    except:
        pass
