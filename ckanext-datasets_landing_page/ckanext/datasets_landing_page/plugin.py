import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import send_file, Blueprint, request
import zipfile
import io
import requests

import pdb

# This function sets the authorisation to download a dataset
def user_download_dataset(context, data_dict=None):
    return {'success': False, 'msg': 'You are not authorized to download the dataset.'}

def download_multiple_resources():
    if request.method == "POST":

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, mode='w', compression=zipfile.ZIP_STORED) as zf:
            for res in request.form.values():
                #pdb.set_trace()
                f = requests.get(res)
                zf.writestr('download.txt', f.content)
        memory_file.seek(0) # return to beginning of file <----------- is this needed??
        
    return send_file(memory_file, mimetype='application/zip', as_attachment = True, attachment_filename= 'download.zip')



class Datasets_Landing_PagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        #toolkit.add_public_directory(config_, '../../../ckan/public/test_dataset_public_files')
        toolkit.add_resource('fanstatic', 'datasets_landing_page')


    # IAuthFunctions

    def get_auth_functions(self):
        return {'user_download_dataset': user_download_dataset}



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