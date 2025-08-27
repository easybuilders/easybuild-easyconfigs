# Amber and AmberTools Patches

Patches with names such as:

+ `Amber-24_update.1.patch`
+ `AmberTools-24_update.4.patch`

are from <https://ambermd.org/AmberPatches.php> and <https://ambermd.org/ATPatches.php> respectively.

Patches are named `[package]-[version]_update.[update_number].patch`, where:

+ `[package]` is _Amber_ or _AmberTools_ and the name is for whether they patch Amber or AmberTools
+ `[version]` is the Version number for Amber or AmberTools
+ `[update_number]` is the update number of the patch

So, `AmberTools-24_update.4.patch` was obtained by:

1. Download <https://ambermd.org/bugfixes/AmberTools/24.0/update.4>
1. Renaming `update.4` to be `AmberTools-24_update.4.patch`

These patches are included in the EasyConfig and applied in the order:

1. AmberTools patches in numerical order
1. Amber patches in numerical order

## Amber and AmberTools Mirrors:

From [_Amber 2025 Reference Manual_](https://ambermd.org/doc12/Amber25.pdf) page 28 (accessed 20250827):

> *Mirrors* If you would like to download Amber patches from another website or even a folder on a local filesystem, you can use the `--amber-updates` and `--ambertools-updates` command-line flags to specify a particular web address (must start with http://) or a local folder (use an absolute path). You can use the `--reset-remotes` command-line flag to erase these settings and return to the default Amber locations on https://ambermd.org.
>
> If you set up online mirrors and never plan on connecting directly to http://ambermd.org, you can change the web address that `update_amber` attempts to connect to when it verifies an internet connection using the `--internet-check` command-line option.

