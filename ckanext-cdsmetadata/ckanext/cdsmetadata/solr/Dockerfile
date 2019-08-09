from solr:8.2
# FROM solr:8.1.1
# MAINTAINER Open Knowledge

# Enviroment
ENV SOLR_CORE ckan

#USER root

# Create Directories
# RUN mkdir -p /var/solr/data/$SOLR_CORE/conf
# RUN mkdir -p /var/solr/data/$SOLR_CORE/data

RUN mkdir -p /var/solr/data/ckan/data
RUN mkdir -p /var/solr/data/ckan/conf

# Adding Files
ADD ./ckanext-cdsmetadata/ckanext/cdsmetadata/solr/solrconfig.xml \
./ckanext-cdsmetadata/ckanext/cdsmetadata/solr/schema.xml \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/currency.xml \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/synonyms.txt \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/stopwords.txt \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/protwords.txt \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/data_driven_schema_configs/conf/elevate.xml \
/var/solr/data/$SOLR_CORE/conf/

# Create Core.properties
RUN echo name=$SOLR_CORE > /var/solr/data/$SOLR_CORE/core.properties
RUN echo name=ckan > /var/solr/data/ckan/core.properties

# Giving ownership to Solr

USER root
#RUN chown -R $SOLR_USER:$SOLR_USER /var/solr/
RUN chown -R $SOLR_USER:$SOLR_USER /var/solr/data/$SOLR_CORE

# User
USER $SOLR_USER:$SOLR_USER
     
