#! /bin/bash

export GIT_REPO=swjones/nugridnotebooks
export REPO_DIR=notebooks

# Check whether the GIT_REPO has already been cloned, if not
# then clone it. If GIT_REPO has not been defined, then just
# start an empty notebook-dir.
r=$(basename $GIT_REPO)
set -e
if [ -z "$GIT_REPO" ]; then
    echo "Git Repo not defined. Blank project will be used"
else
    if [ -d /tmp/notebook/$r/$REPO_DIR ]; then
        echo "Git Repo already cloned."
    else
        cd /tmp/notebook && git clone https://github.com/$GIT_REPO
        cd
    fi
fi

# Now we have to do the fuse install, which requires the --privileged=true
# flag for docker run, which can not be invoked during the build
if hash fusermount 2>/dev/null; then
    echo "fuse is already installed"
else
    apt-get install -y fuse
    chmod +x /dev/fuse
fi

# now we can mount the CADC and launch the notebook.
# upon stopping the container, it seems that the VOSpace is
# unmounted by default, so we don't need the fusermount -u
# command below.
if [ -d /CADC ]; then
    #fusermount -u /CADC/NuGrid
    :
else
    mkdir /CADC
    mkdir /CADC/vosCache /CADC/NuGrid
fi


mountvofs --readonly --log=/CADC/vos_log --cache_nodes --cache_dir=/CADC/vosCache --mountpoint=/CADC/NuGrid --vospace=vos:nugrid
ipython notebook --no-browser --ip=0.0.0.0 --port=8080 --notebook-dir=/tmp/notebook/${GIT_REPO/*\/}/${REPO_DIR}
