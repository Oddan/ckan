#!/bin/sh

# link developer directory as new CKAN source directory
ln -s /ckan_devel $CKAN_VENV/src/ckan

# setting up
ckan-pip install -U pip
ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt
ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirements.txt
ckan-pip install -e $CKAN_VENV/src/ckan/
ckan-pip install flask_debugtoolbar --upgrade
ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini
chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

# create configuration file
CONFIG=$CKAN_CONFIG/development.ini
ckan-paster make-config --no-interactive ckan "$CONFIG"

# installing ckanext_spatial stuff
ckan-pip install -e "git+https://github.com/ckan/ckanext-spatial.git#egg=ckanext-spatial"
ckan-pip install -r $CKAN_VENV/src/ckanext-spatial/pip-requirements.txt
echo "In your configuration file, remember to add 'spatial_metadata' and 'spatial_query' to your plugin list, and introduce 'ckanext.spatial.search_backend = solr-spatial-field'"

# modifying configuration file
sed 's/^debug =.*$/debug = true/' $CKAN_CONFIG/development.ini | \
    sed 's/^ckan.site_url =.*$/ckan.site_url = http:\/\/localhost:5000/' | \
    sed 's/^ckan.plugins =.*$/ckan.plugins = stats text_view image_view recline_view cdsaccess cdslandingpage cdstheme cdsmetadata cdsmetadata_resources spatial_metadata spatial_query cdsstats/' | \
    sed '/ckan.plugins/ a ckan.cdsmetadata.max_zipfile_size = 5000000000' | \
    sed '/ckan.plugins/ a ckanext.spatial.search_backend = solr-spatial-field' > \
	$CKAN_CONFIG/tmp.ini
mv $CKAN_CONFIG/development.ini $CKAN_CONFIG/development_orig.ini
mv $CKAN_CONFIG/tmp.ini $CKAN_CONFIG/development.ini

# setting up database
ckan-paster --plugin=ckan db init -c "${CKAN_CONFIG}/development_orig.ini"

# setup sysadmin

sleep 8 # wait for database to complete

# registering plugins
cd $CKAN_VENV
. bin/activate
cd $CKAN_VENV/src/ckanext-spatial/
python setup.py develop
cd $CKAN_VENV/src/ckan/ckanext-cdsmetadata/
python setup.py develop
deactivate

cd $CKAN_VENV/src/ckan
ckan-paster --plugin=ckan user add admin email=admin@localhost name=admin password=passpass -c /etc/ckan/development.ini
ckan-paster --plugin=ckan sysadmin add admin -c /etc/ckan/development.ini
cd -



# restarting server
ckan-paster serve /etc/ckan/development.ini
