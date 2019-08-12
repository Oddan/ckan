import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from flask import send_file, Blueprint, request, render_template
import ckan.lib.helpers as h
from ckan.lib.base import abort, render
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.common import g, _, request
import zipfile
import io
import requests
import ckan.logic as logic
from os.path import basename
import ckan.model as model
import pdb

# abort(403, _('Not authorized to see this page.'))


def _only_sysadmin_auth(context, data_dict=None):
    # only sysadmins should have access (and sysamins bypass the login system)
    return {'success': False, 'msg': 'Only sysadmins are authorized.'}


def _package_id_of_resource(context, resource_id):

    res = tk.get_action('resource_show')(context, {'id': resource_id})
    return res['package_id']


def _landing_page_upload(pkg_name):

    # check for permission
    
    try:
        tk.check_access('only_sysadmin', {'auth_user_obj': g.userobj})
    except logic.NotAuthorized:
        abort(403, _('Only sysadmins are allowed to change landing pages.'))

    if request.method == 'POST':
        pdb.set_trace()
        pass
        
    try:
        pkg_id = convert_package_name_or_id_to_id(pkg_name, {'session': model.Session})
        pkg = model.Package.get(pkg_id)
    except:
        abort(404, 'Requested package not found.')
        
    extra_vars = {'pkg': pkg, 'pkg_name': pkg_name}
    return render('landing_page_upload.html', extra_vars)
        

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
    plugins.implements(plugins.IAuthFunctions)

    # IAuthFunctions
    def get_auth_functions(self):
        return {'only_sysadmin': _only_sysadmin_auth}
    
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
                               methods=['GET', 'POST'])

        return blueprint
