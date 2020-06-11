FROM solr:8.2
MAINTAINER Open Knowledge

# Enviroment
ENV SOLR_CORE ckan

ENV CKAN_TMPDIR /tmp/ckan_tmp
RUN mkdir -p $CKAN_TMPDIR/data && \
    mkdir -p $CKAN_TMPDIR/conf && \
    echo name=$SOLR_CORE > $CKAN_TMPDIR/core.properties

# Adding Files
ADD ./ckanext-cdsmetadata/ckanext/cdsmetadata/solr/solrconfig.xml \
./ckanext-cdsmetadata/ckanext/cdsmetadata/solr/schema.xml \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/currency.xml \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/synonyms.txt \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/stopwords.txt \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/basic_configs/conf/protwords.txt \
https://raw.githubusercontent.com/apache/lucene-solr/releases/lucene-solr/6.6.2/solr/server/solr/configsets/data_driven_schema_configs/conf/elevate.xml \
$CKAN_TMPDIR/conf/

ADD ./contrib/docker/solr/initscript.sh /docker-entrypoint-initdb.d/

# Giving ownership to Solr
USER root
RUN chown -R $SOLR_USER:$SOLR_USER $CKAN_TMPDIR

# User
USER $SOLR_USER:$SOLR_USER
     
