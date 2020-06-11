#!/bin/bash

set -e

if [[ ! -d /var/solr/data/$SOLR_CORE ]]; then

   mkdir -p /var/solr/data/$SOLR_CORE
   mv $CKAN_TMPDIR/data /var/solr/data/$SOLR_CORE
   mv $CKAN_TMPDIR/conf /var/solr/data/$SOLR_CORE

   echo name=$SOLR_CORE > /var/solr/data/$SOLR_CORE/core.properties
   
fi
   
