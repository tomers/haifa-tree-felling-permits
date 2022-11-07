#!/usr/bin/env bash

DOCKER_TAG=haifa-tree-felling-permits

docker build \
    -t $DOCKER_TAG \
    .
docker run \
    --rm \
    -it \
    -v $(pwd)/src:/usr/src/app \
    -v $(pwd)/build:/usr/src/app/build \
    $DOCKER_TAG \
    ./main.py $@
