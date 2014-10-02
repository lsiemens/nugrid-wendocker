#!/bin/bash

VOS_DIR=${1:-/vos_nugrid}

# clear up cache if it already exists
rm -rf ${VOS_DIR}/cache
mountvofs --readonly \
    --log=/var/log/vos.log \
    --allow_other \
    --cache_nodes \
    --cache_dir=${VOS_DIR}/cache \
    --mountpoint=${VOS_DIR}/data \
    --vospace=vos:nugrid
