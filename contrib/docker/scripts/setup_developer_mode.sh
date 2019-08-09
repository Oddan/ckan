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
CONFIG=$CKAN_CONFIG/production.ini
ckan-paster make-config --no-interactive ckan "$CONFIG"

# modifying configuration file
sed 's/^debug =.*$/debug = true/' /etc/ckan/production.ini | \
sed 's/^ckan.site_url =.*$/ckan.site_url = http:\/\/localhost:5000/'  > /etc/ckan/development.ini

# installing ckanext_spatial stuff
ckan-pip install -e "git+https://github.com/ckan/ckanext-spatial.git#egg=ckanext-spatial"
ckan-pip install -r $CKAN_VENV/src/ckanext-spatial/pip-requirements.txt
echo "In your configuration file, remember to add 'spatial_metadata' and 'spatial_query' to your plugin list, and introduce 'ckanext.spatial.search_backend = solr-spatial-field'"

# setting up database
ckan-paster --plugin=ckan db init -c "${CKAN_CONFIG}/development.ini"

# setup sysadmin
sleep 8 # wait for database to complete
cd $CKAN_VENV/src/ckan
ckan-paster --plugin=ckan user add admin email=admin@localhost name=admin password=passpass -c /etc/ckan/development.ini
ckan-paster --plugin=ckan sysadmin add admin -c /etc/ckan/development.ini
cd -

# restarting server
# ckan-paster serve --reload /etc/ckan/development.ini
ckan-paster serve /etc/ckan/development.ini
