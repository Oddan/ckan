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
sed 's/^ckan.site_url =.*$/ckan.site_url = http:\/\/localhost:5000/'  > /etc/ckan/production.ini.2

# setup sysadmin
cd $CKAN_VENV/src/ckan
ckan-paster user add admin email=admin@localhost name=admin password=$CKAN_ADMIN_PASSWORD -c /etc/ckan/production.ini
ckan-paster sysadmin add admin -c /etc/ckan/production.ini
cd -

# setting up database
ckan-paster --plugin=ckan db init -c "${CKAN_CONFIG}/production.ini"

# restarting server
# ckan-paster serve --reload /etc/ckan/production.ini
ckan-paster serve /etc/ckan/production.ini
