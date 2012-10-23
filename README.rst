EasyBuild: building software with ease
--------------------------------------

The easybuild-easyblocks package provides a collection of easyblocks for
EasyBuild (http://hpcugent.github.com/easybuild), a software build and
installation framework written in Python that allows you to install
software in a structured, repeatable and robust way.

Easyblocks are Python modules that implement the install procedure for a
(group of) software package(s). Together with the EasyBuild framework,
they allow to easily build and install supported software packages.

The code of the easybuild-easyblocks package is hosted on GitHub, along
with an issue tracker for bug reports and feature requests, see
http://github.com/hpcugent/easybuild-easyblocks.

The EasyBuild documentation is available on the GitHub wiki of the
easybuild meta-package, see
http://github.com/hpcugent/easybuild/wiki/Home.

Related packages: \* easybuild-framework
(http://pypi.python.org/pypi/easybuild-framework): the EasyBuild
framework, which includes the easybuild.framework and easybuild.tools
Python packages that provide general support for building and installing
software \* easybuild-easyconfigs
(http://pypi.python.org/pypi/easybuild-easyconfigs): a collection of
example easyconfig files that specify which software to build, and using
which build options; these easyconfigs will be well tested with the
latest compatible versions of the easybuild-framework and
easybuild-easyblocks packages
