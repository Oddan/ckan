#!/bin/bash

if [[ $# -eq 0 ]]; then
   echo "No arguments given.  Please specify 'devel', 'release' or 'release novolumes'"
   exit 1
fi
   
cp "Dockerfile."$1 Dockerfile
cp "contrib/docker/scripts/docker-compose.yml."$1 "contrib/docker/docker-compose.yml"
cp "contrib/docker/scripts/ckan-entrypoint.sh."$1 "contrib/docker/ckan-entrypoint.sh"

if [ $1 == "devel" ]; then
    cp "contrib/docker/scripts/setup_developer_mode.sh" "contrib/docker/setup_developer_mode.sh"
elif [ -e ./contrib/docker/setup_developer_mode.sh ]; then
   rm "contrib/docker/setup_developer_mode.sh"
fi

if [[ $# -eq 2 ]] && [[ $2 == "novolumes" ]]; then
   cp "contrib/docker/scripts/docker-compose.yml.release_novolumes" "contrib/docker/docker-compose.yml"
fi

echo "Switched to: " $1
