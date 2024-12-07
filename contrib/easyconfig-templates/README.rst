Easyconfig templates for EasyBuild
==================================

.. image:: https://easybuilders.github.io/easybuild/images/easybuild_logo_small.png
   :align: center

EasyBuild website: https://easybuilders.github.io/easybuild/
EasyBuild docs: https://easybuild.readthedocs.io

This directory contains a collection of easyconfig templates for commonly used
package archetypes. These templates are designed to be used as starting points
for the development of any new easyconfigs. Some are minimal and others are
more complete and complex. All of them will help you save time by providing the
structure of the easyconfig and several basic requirements already filled in. 

The templates are organized in folders per toolchain generation. All of them
are already adapted to the requirements of their generation, including any
versions of dependencies and build dependencies for instance.

Templates can use Python *f-strings* for formatting (*i.e.*
``f"Text and {some_var}"``) and also the string templates provided by EasyBuild
itself (*i.e.* ``Text and %(some_var)s``). These are **not placeholders** and
can be left in place. Keep in mind that *f-strings* are resolved before the
string templates from EB.

See https://docs.easybuild.io/writing-easyconfig-files/ for
documentation on writing easyconfig files for EasyBuild.
