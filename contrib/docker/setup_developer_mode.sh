#!/bin/sh

# remove existing CKAN source directory
rm -rf $CKAN_VENV/src/ckan

# link developer directory as new CKAN source directory
ln -s /ckan_devel $CKAN_VENV/src/ckan

# re-run ckan-pip and related stuff
ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt
ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirements.txt
ckan-pip install -e $CKAN_VENV/src/ckan/
rm $CKAN_CONFIG/who.ini
ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini

# modifying configuration file
sed 's/^debug =.*$/debug = true/' /etc/ckan/production.ini | \
sed 's/^ckan.site_url =.*$/ckan.site_url = http:\/\/localhost:5000/'  > /etc/ckan/production.ini.2

# restarting server
# ckan-paster serve --reload /etc/ckan/production.ini
ckan-paster serve /etc/ckan/production.ini
