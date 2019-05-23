import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import send_file, Blueprint, request, render_template
import zipfile
import io
import requests
from ckan.common import c
from os.path import basename
import pdb

'''
This plugin does the following:
    - Implements the Datasets Landing Page. This is the page the user will see when clicking ona a dataset
    - The Dataset Langin Page loads the description of the dataset from a custom-made html. The file
      is either provided by the customer or made by the consortium, and is located in a folder in CKAN's public directory. The path to the description file
      must be supplied when the dataset is created in one of the "extra fields" using custom_html_desc
      as key for the field.
    - Implements a checkbox form for the user to select and download resources.
      The download function zips the resources on-the-fly, in memory, and provides the file for download.
      The file is deleted and the memory freed after the download finishes.
      The user must accept the dataset's licence to be able to download the files.
'''


def download_multiple_resources():
    access = True
    if request.method == "POST":
        
        if not c.userobj:
            return render_template(u"package/download_denied.html")

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, mode='w', compression=zipfile.ZIP_STORED) as zf:
            for res_name in request.form:
                #pdb.set_trace()
                f = requests.get(request.form[res_name], allow_redirects=True, headers={'Authorization': c.userobj.apikey}) # OBS: The function c is from Pylons. How to substitute with h?
                if f.status_code == 404:
                    return render_template(u"package/download_denied.html")
                zf.writestr(basename(request.form[res_name]), f.content)

        memory_file.seek(0)
        
    return send_file(memory_file, mimetype='application/zip', as_attachment = True, attachment_filename= 'download.zip')





class Datasets_Landing_PagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)


    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'datasets_landing_page')


    # IBlueprint

    def get_blueprint(self):
        u'''Return a Flask Blueprint object to be registered by the app.'''

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # Add plugin url rules to Blueprint object
        rules = [
            (u'/multiple_download', u'multiple_download', download_multiple_resources),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule, methods=['POST'])

        return blueprint
