Summary
=======

This directory contains (hopefully) sufficient gear in order to let you
bootstrap towards the Lmod implementation of environment modules.

Howto
=====

Assuming you have successfully used the bootstrap procedure of EasyBuild,
you should be able to initiate a recursive build of the following bits::

  EASYBUILD_OPTARCH= time eb Lmod-5.9-GCC-4.8.4.eb -r

which is going to build the following modules/easyconfigs::

  g/GCC/GCC-4.8.4.eb			## if this breaks use: --try-amend=parallel=1
  n/ncurses/ncurses-5.9-GCC-4.8.4.eb    ## On MacOSX, this should pick a special patch
  l/Lua/Lua-5.1.4-8-GCC-4.8.4.eb        ## Lmod is written in Lua, which needs ncurses
  l/Lmod/Lmod-5.9-GCC-4.8.4.eb          ## Lmod should be built with -r, to build the above

This operation is expected to be the needed substrate to launch you towards Lmod;
Lmod facility gets activated with the `sourceme` script available next to this file::

  source sourceme ## N.B. direct assignments on environment variables are intentional here

Then try::

  ml av         ## ie. the Lmod equivalent to `module avail` ; it should just work

If so, now you implemented the better instance of environment modules implementations:
  https://hpcbios.readthedocs.org/en/latest/HPCBIOS_06-17.html

Lmod's caching can help to work with *buildsets*; ref. https://fosdem.org/2014/schedule/event/hpc_devroom_hpcbios/
You should now be able to try alternative Lmod/Lua versions, toggle the cache, and so forth.

enjoy,
Fotis

2014-10-26

