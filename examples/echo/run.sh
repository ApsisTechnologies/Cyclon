#!/bin/sh

CWD=`pwd`
SRC_DIR=${CWD}/../../src
SLS_FILE_PATH=${CWD}/serverless.yml

PYTHONPATH=${SRC_DIR} python3 ${SRC_DIR}/api_gateway.py \
  --sls ${SLS_FILE_PATH} \
  --functions ${CWD}
