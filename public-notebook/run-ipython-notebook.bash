#!/bin/bash
export PYTHONPATH=/home/nugrid

IPN_URL="https://github.com/NuGrid/WENDI.git"
IP_PROFILE="/home/nugrid/.ipython/profile_nbserver"
IPN_LOCAL="/home/nugrid/nugridnotebooks"
IPN_DIR="${IPN_LOCAL}/notebooks"

OMEGA_SYGMA_URL="https://github.com/NuGrid/NuPyCEE.git"
OMEGA_SYGMA_DIR="/home/nugrid/omega_sygma"

[[ -d ${IPN_DIR} ]] || git clone --depth 1 ${IPN_URL} ${IPN_LOCAL}
[[ -d ${OMEGA_SYGMA_DIR} ]] || git clone --depth 1 ${OMEGA_SYGMA_URL} ${OMEGA_SYGMA_DIR}

# move startup files to IPython profile
mv ${IPN_LOCAL}/startup/* ${IP_PROFILE}/startup/

# add Luke's widget module to python path:
export PYTHONPATH=${IPN_LOCAL}/modules:${OMEGA_SYGMA_DIR}:$PYTHONPATH
export SYGMADIR=${OMEGA_SYGMA_DIR}

#trus the widget notebooks
ipython trust \
    --profile=nbserver \
    ${IPN_DIR}/NuGrid_Mesa_Explorer.ipynb \
    ${IPN_DIR}/SYGMA.ipynb \
    ${IPN_DIR}/OMEGA.ipynb \

ipython notebook \
    --profile=nbserver \
    --no-browser \
    --ip=0.0.0.0 \
    --port=8888 \
    --notebook-dir=${IPN_DIR}
