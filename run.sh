#!/usr/bin/env bash

docker build -t haifa-tree-felling-permits .
docker run \
    --rm \
    -it \
    -v $(pwd)/src:/usr/src/app \
    -v $(pwd)/build:/usr/src/app/build \
    haifa-tree-felling-permits \
    ./main.py $@
