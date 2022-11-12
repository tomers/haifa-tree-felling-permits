#!/usr/bin/env bash

set -e
DOCKER_TAG=haifa-tree-felling-permits

# Make sure to create .env file with a Google API key with the following APIs enabled:
# - Geocoding API
# - Time Zone API
# For further info: https://towardsdatascience.com/geocode-with-python-161ec1e62b89
# GCP_API_KEY=xxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxx_xxxxxx
if [ -f .env ]; then
    source .env
else
    >&2 echo "Error: missing .env file"
    exit 1
fi

if [ -z "$NO_BUILD" ]; then
    docker build \
        -t $DOCKER_TAG \
        .
fi

docker run \
    --rm \
    -it \
    -e GCP_API_KEY=$GCP_API_KEY \
    -v $(pwd)/src:/usr/src/app \
    -v $(pwd)/build:/usr/src/app/build \
    $DOCKER_TAG \
    ./main.py $@
