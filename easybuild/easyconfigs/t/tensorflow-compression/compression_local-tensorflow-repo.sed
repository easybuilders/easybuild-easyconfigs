# Convert http repo for tensorflow to local repo
# Copied from jax/jaxlib_local-tensorflow-repo.sed
/^http_archive(/{
    :a;N;/\n)/!ba;
    /org_tensorflow/{
        s/^/# /;
        s/\n/\n# /g;
        s|$|\
local_repository(\
    name = "org_tensorflow",\
    path = "EB_TF_REPOPATH",\
)|;
    }
}
