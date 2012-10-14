EasyBuild: building software with ease
=======================================

[EasyBuild] [1] is a software build and installation framework written in Python
that allows you to install software in a structured, repeatable and robust way.

It is motivated by the need for a tool that allows to:

 * independently install multiple versions of software side-by-side
 * support multiple compilers and libraries for building software
   and its dependencies
 * keep the software build configuration simple
 * divert from the standard configure / make / make install with custom
   procedures (which is often necessary for scientific software)
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

For more information on EasyBuild, see the [EasyBuild wiki] [2] on GitHub.


REQUIREMENTS
-------------

EasyBuild requires Python 2.4 (or a more recent 2.x version) to be available,
as well as the [environment modules] [3] tool.

The [GitPython] [4] Python module is recommended, especially when EasyBuild is
being used from a git repository.

See the EasyBuild wiki for more information on [EasyBuild dependencies] [5].


QUICK DEMO FOR THE IMPATIENT
-----------------------------

To see EasyBuild in action, build HPL with the robot feature of EasyBuild, by
running the following (bash/sh syntax):

    export EBHOME="<path to where you unpacked EasyBuild>"
    export CFGS="$EBHOME/easybuild/easyconfigs"
    ${EBHOME}/eb --robot ${CFGS} ${CFGS}/h/HPL/HPL-2.0-goalf-1.1.0.eb

This will build and install HPL, after building and installing a GCC-based
compiler toolchain and all of its dependencies using the default EasyBuild
configuration, which will install to $HOME/.local/easybuild/software.

The entire process should take about an hour on a recent system.

Module files will be provided in $HOME/.local/easybuild/modules/all, so to load
the provided modules, update your MODULEPATH environment variable.

Note: this demo requires a C and C++ compiler to be available on your system,
e.g., gcc and g++.


QUICK START
------------

To get started, you first need to [configure EasyBuild] [6] for use.

Once this is done, using EasyBuild is as simple as creating a .eb specification
file, and providing it to the framework:

	easybuild/eb example.eb

For command line options, see

	easybuild/eb -h (or --help)

See the EasyBuild wiki for documentation on writing your own [easyconfig files] [7] (.eb).

To add support for particular software that requires a custom
installation procedure, you will need to implement an easyblock that can be
plugged into the EasyBuild framework (see [Development guide] [8]).

On the EasyBuild wiki, a step-by-step guide to [getting started] [9] with EasyBuild is provided.

CONTACT INFO
------------

You can get in contact with the EasyBuild community in different ways:

### Mailing list

An EasyBuild mailinglist easybuild@lists.ugent.be is available to subscribe to.

This list is used by both users and developers of EasyBuild, so if you have any questions or suggestions, you can post them there.

Only members can post to this mailinglist. To request membership, see https://lists.ugent.be/sympa/info/easybuild.

### IRC

An IRC channel #easybuild has been set up on the FreeNode network.

Just connect your IRC client to the irc.freenode.net server, and join the #easybuild channel.

There is an IRC bot present (easybuilder). Just type !help to get pointers to the available commands.

### Twitter

The EasyBuild team also has a Twitter feed: [@easy_build] [10].

DISCLAIMER
-----------

EasyBuild has mainly been tested on RPM-based 64-bit Linux systems, i.e.,
Scientific Linux 5.x/6.x.  Support for other Linux distributions and operating
systems is pending.


LICENSE
--------

EasyBuild is developed by the [High-Performance Computing team at Ghent University] [11]
and is made available under the GNU General Public License (GPL) version 2.


[1]: https://github.com/hpcugent/easybuild "EasyBuild"
[2]: https://github.com/hpcugent/easybuild/wiki/Home "EasyBuild wiki"
[3]: http://modules.sourceforge.net/ "environment modules"
[4]: http://gitorious.org/git-python "GitPython"
[5]: https://github.com/hpcugent/easybuild/wiki/Dependencies "EasyBuild dependencies"
[6]: https://github.com/hpcugent/easybuild/wiki/Configuration "configure EasyBuild"
[7]: https://github.com/hpcugent/easybuild/wiki/Specification-files "easyconfig files"
[8]: https://github.com/hpcugent/easybuild/wiki/Development-guide "Development guide"
[9]: https://github.com/hpcugent/easybuild/wiki/Step-by-step-guide "getting started"
[10]: http://twitter.com/easy_build "@easy_build"
[11]: https://ugent.be/hpcugent "High-Performance Computing team at Ghent University"
