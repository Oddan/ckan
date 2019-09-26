Regarding Solr
==============

Before running `docker-compose up`, some preparations have to be made for Solr.
The plugin requires a modified Solr schema.  To accomodate for this, as well as
letting it run under a more recent version of Solr (8.2), the following steps
should be taken:

- Replace the Dockerfile under `ckan/contrib/docker/solr` with the one found in
`ckan/ckanext-cdsmetadata/ckanext/cdsmetadata/solr`.  
- Check out the following
[Git-repo](https://github.com/docker-solr/docker-solr.git), and modify the
Dockerfile in the subdirectory `8.2` by commenting out the line towards the end
of the script saying `VOLUME /var/solr`.
- Create a Solr base image using the modified Dockerfile, and give the image the
name `solr:82`.

After carrying out these steps, you should be able to run `docker-compose up` in
the `ckan/contrib/docker` folder.
