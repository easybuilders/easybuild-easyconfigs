
Summary:

This directory contains (hopefully) sufficient gear in order to let you
bootstrap towards the Lmod implementation of environment modules.

Howto:

Assuming you have successfully used the bootstrap procedure of EasyBuild,
you should be able to initiate a recursive build of the following bits:

  `time eb Lmod-5.6-GCC-4.8.2.eb -r`

l/Lmod/Lmod-5.6-GCC-4.8.2.eb ### so, you just aim for this one, with "-r"
l/Lua/Lua-5.1.4-8-GCC-4.8.2.eb
n/ncurses/ncurses-5.9-GCC-4.8.2.eb
g/GCC/GCC-4.8.2.eb

This set is expected to be the needed substrate to launch you towards Lmod,
which gets activated with the `sourceme` script sitting in the same directory:

`source sourceme` # N.B. it does direct assignments on environment variables; that's intentional

Then try:

`ml av` # ie. the Lmod equivalent to `module avail` ; it should work

If so, now you implemented the better instance of: https://hpcbios.readthedocs.org/en/latest/HPCBIOS_06-17.html
Lmod's caching can help to work with *buildsets*; ref. https://fosdem.org/2014/schedule/event/hpc_devroom_hpcbios/
You should now be able to try alternative Lmod/Lua versions, toggle cache, and so forth.

enjoy,
Fotis

2014-05-23
