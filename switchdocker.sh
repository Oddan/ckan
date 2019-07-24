#!/bin/bash

cp "Dockerfile."$1 Dockerfile
cp "contrib/docker/scripts/docker-compose.yml."$1 "contrib/docker/docker-compose.yml"
cp "contrib/docker/scripts/ckan-entrypoint.sh."$1 "contrib/docker/ckan-entrypoint.sh"

if [ $1 == "devel" ]; then
    cp "contrib/docker/scripts/setup_developer_mode.sh" "contrib/docker/setup_developer_mode.sh"
elif [ -e ./contrib/docker/setup_developer_mode.sh ]; then
   rm "contrib/docker/setup_developer_mode.sh"
fi

echo "Switched to: " $1
