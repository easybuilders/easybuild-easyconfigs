EasyBuild: building software with ease
=======================================

EasyBuild [1] is a software build and installation framework written in Python
that allows you to install software in a structured, repeatable and robust way.

It is motivated by the need for a tool that allows to:

 * independently install multiple versions of a software package side-by-side
 * support multiple compilers and libraries for building a software package
   and its dependencies
 * keep the package configuration simple
 * divert from the standard configure / make / make install with custom
   procedures (which is often necessary for scientific packages)
 * use environment modules for dependency resolution and making the software
   available to users in a transparent way
 * keep record of the installation logs
 * keep track of installation configuration in version control

Some key properties of EasyBuild:

 * installation configuration is done using a (very concise) .eb specification file
 * custom behaviour is described in easyblocks; these are Python classes that can be
   plugged into the EasyBuild framework
 * the generation of the module files to easily make the software available to users
 * the dependencies for installation are resolved using environment modules and can
   be automatically installed using the robot feature
 * after the installation, the specification files can be sent to a repository for
   archiving

For more information on EasyBuild, see the documentation wiki on github [3].


REQUIREMENTS
-------------

EasyBuild requires Python 2.4 (or a more recent 2.x version) to be available,
as well as the environment-modules software package [4].

The GitPython Python module [5] is recommended, especially when EasyBuild is
being used from a git repository.

See [6] for more information on EasyBuild dependencies.


QUICK DEMO FOR THE IMPATIENT
-----------------------------

To see EasyBuild in action, build HPL with the robot feature of EasyBuild, by
running the following (bash/sh syntax):

    export EBHOME="<path to where you unpacked EasyBuild>"
    export CFGS="$EBHOME/easybuild/easyconfigs"
    ${EBHOME}/eb --robot ${CFGS} ${CFGS}/h/HPL/HPL-2.0-goalf-1.1.0.eb

This will build and install HPL, after building and installing a GCC-based
compiler toolkit and all of its dependencies using the default EasyBuild
configuration, which will install to $HOME/.local/easybuild/software.

The entire process should take about an hour on a recent system.

Module files will be provided in $HOME/.local/easybuild/modules/all, so to load
the provided modules, update your MODULEPATH environment variable.

Note: this demo requires a C and C++ compiler to be available on your system,
e.g., gcc and g++.


QUICK START
------------

To get started, you first need to configure EasyBuild for use [7].

Once this is done, using EasyBuild is as simple as creating a .eb specification
file, and providing it to the framework:

	easybuild/eb example.eb

For command line options, see

	easybuild/eb -h (or --help)

Documentation on writing your own .eb specification files is available on the
EasyBuild github wiki [8].

To add support for a particular software package that requires a custom
installation procedure, you will need to implement an easyblock that can be
plugged into the EasyBuild framework [9].

A step-by-step guide to getting started with EasyBuild is provided on
the github wiki [10].


DISCLAIMER
-----------

EasyBuild has mainly been tested on RPM-based 64-bit Linux systems, i.e.,
Scientific Linux 5.x/6.x.  Support for other Linux distributions and operating
systems is pending.


LICENSE
--------

EasyBuild is developed by the High-Performance Computing team at Ghent University [2]
and is made available under the GNU General Public License (GPL) version 2.


[1] https://github.com/hpcugent/easybuild
[2] http://www.ugent.be/hpc/en
[3] https://github.com/hpcugent/easybuild/wiki/Home
[4] http://modules.sourceforge.net/
[5] http://gitorious.org/git-python
[6] https://github.com/hpcugent/easybuild/wiki/Dependencies
[7] https://github.com/hpcugent/easybuild/wiki/Configuration
[8] https://github.com/hpcugent/easybuild/wiki/Specification-files
[9] https://github.com/hpcugent/easybuild/wiki/Development-guide
[10] https://github.com/hpcugent/easybuild/wiki/Step-by-step-guide
