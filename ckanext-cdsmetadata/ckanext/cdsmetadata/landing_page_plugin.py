import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from flask import send_file, Blueprint, request, render_template
import ckan.lib.helpers as h
from ckan.common import g
import zipfile
import io
import requests
from os.path import basename
import ckan.model as model
from ckan.lib.base import abort
import pdb

# abort(403, _('Not authorized to see this page.'))


def _package_id_of_resource(context, resource_id):

    res = tk.get_action('resource_show')(context, {'id': resource_id})
    return res['package_id']


def _landing_page_upload(pkg_name):
    # @@ make sure to check for permission
    # @@ make sure to check for correct type file
    return "Hello world"
    # errors = {'zipfile': ["Bad file input."]}
    # # @@ make upload directory customizable
    # pdb.set_trace()
    # abort(405, 'upload not yet implemented')


def _download_multiple_resources():

    context = {'model': model, 'user': g.user, 'auth_user_obj': g.userobj}

    if request.method == "POST":

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, mode='w',
                             compression=zipfile.ZIP_STORED) as zf:
            for res_id in request.form.values():

                # @@ change when Flask becomes responsible for resources
                url = h.url_for(controller='package',
                                action='resource_download',
                                id=_package_id_of_resource(context, res_id),
                                resource_id=res_id,
                                qualified=True)

                f = requests.get(url,
                                 allow_redirects=True,
                                 headers={'Cookie': request.headers['cookie']})

                if f.status_code == 404:
                    return render_template(u"package/download_denied.html")
                filename = basename(model.Resource.get(res_id).url)
                zf.writestr(filename, f.content)

        memory_file.seek(0)

    return send_file(memory_file,
                     mimetype='application/zip',
                     as_attachment=True,
                     attachment_filename='download.zip')


class CdsLandingPagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer
    def update_config(self, config):
        tk.add_template_directory(config, 'templates/landing_page')
        tk.add_public_directory(config, 'public')
        tk.add_resource('fanstatic/landing_page', 'cdslandingpage')

    # IBlueprint
    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'

        blueprint.add_url_rule(u'/multiple_download',
                               u'multiple_download',
                               _download_multiple_resources,
                               methods=['POST'])
        blueprint.add_url_rule(u'/landing_page_upload/<pkg_name>',
                               u'landing_page_upload',
                               _landing_page_upload,
                               methods=['GET'])

        
        # rules = [
        #     (u'/multiple_download',
        #      u'multiple_download',
        #      _download_multiple_resources),
        #     (u'/landing_page_upload',
        #      u'landing_page_upload',
        #      _landing_page_upload)
        #     # (u'/landing_page_upload/<pkg_name>',
        #     #  u'landing_page_upload',
        #     #  _landing_page_upload)
        # ]
        # for rule in rules:
        #     blueprint.add_url_rule(*rule, methods=['POST'])

        return blueprint
