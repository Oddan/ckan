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
import os.path as path
import os
import shutil
# abort(403, _('Not authorized to see this page.'))


PLUGIN_DIR = path.dirname(__file__)
LANDING_PAGE_DIR = 'landing_pages'


def _only_sysadmin_auth(context, data_dict=None):
    # only sysadmins should have access (and sysamins bypass the login system)
    return {'success': False, 'msg': 'Only sysadmins are authorized.'}


def _package_id_of_resource(context, resource_id):

    res = tk.get_action('resource_show')(context, {'id': resource_id})
    return res['package_id']


def _verify_landing_page_filelist(flist):
    index_found = False
    for fname in flist:
        if fname == 'index.html':
            # we identified the index file
            index_found = True
        elif len(fname) >= 7 and fname[0:7] == 'static/':
            # this refers to static content
            pass
        else:
            # there should be no other file in the archive, so this is an error
            return ["Error: zipped archive contains files other than 'index.html' and 'static/*'"]

    if not index_found:
        return ["Error: 'index.html' missing from zipped archive."]


def _unpack_landing_page_zipfile(afile, pkg_name):

    if afile.content_type != 'application/zip':
        return ['The file you tried to upload was not a zip-file.']

    input_zip = zipfile.ZipFile(afile)

    # check contents of uploaded zipfile
    errors = _verify_landing_page_filelist(input_zip.namelist())

    if errors:
        return errors

    # contents verified.  Extract and process files.
    root_dir = path.join(PLUGIN_DIR, 'public', LANDING_PAGE_DIR)
    if not path.exists(root_dir):
        os.makedirs(root_dir)  # ensure base directory exists
    
    target_dir = \
        path.join(PLUGIN_DIR, 'public', LANDING_PAGE_DIR, pkg_name)
    tmp_target_dir = \
        path.join(PLUGIN_DIR, 'public', LANDING_PAGE_DIR, '_' + pkg_name)

    try:
        if not path.exists(tmp_target_dir):
            os.makedirs(tmp_target_dir)
        input_zip.extractall(path=tmp_target_dir)
    except:
        # unable to extract archive.  Clean up and return error
        if path.exists(tmp_target_dir):
            shutil.rmtree(tmp_target_dir)
        return ["Error: failed to extract zip-file.  Corrupt?"]

    # extraction went OK.  Move result to target directory
    if path.exists(target_dir):
        shutil.rmtree(tmp_target_dir)
    os.rename(tmp_target_dir, target_dir)

    return []


def _landing_page_upload(pkg_name):

    # check for permission
    try:
        tk.check_access('only_sysadmin', {'auth_user_obj': g.userobj})
    except logic.NotAuthorized:
        abort(403, _('Only sysadmins are allowed to change landing pages.'))

    # check that requested package exists
    try:
        pkg_id = convert_package_name_or_id_to_id(pkg_name,
                                                  {'session': model.Session})
        pkg = model.Package.get(pkg_id)
    except:
        abort(404, 'Requested package not found.')

    errors = []
    if request.method == 'POST':

        if 'save' in request.form:
            if 'zipfile' not in request.files or request.files['zipfile'] == '':
                errors = ['No file chosen.']
            else:
                errors = _unpack_landing_page_zipfile(request.files['zipfile'],
                                                      pkg_name)
                if len(errors) == 0:
                    # everything went well.
                    return tk.redirect_to(h.url_for(controller='package',
                                                    action='read', id=pkg_id))
        else:
            # a 'delete' was requested 
            # removing directory containing landing page
            target_dir = path.join(PLUGIN_DIR, 'public', LANDING_PAGE_DIR, pkg_name)
            if path.exists(target_dir):
                shutil.rmtree(target_dir)
            return tk.redirect_to(h.url_for(controller='package',
                                            action='read', id=pkg_id))

    extra_vars = {'pkg': pkg, 'pkg_name': pkg_name, 'errors': errors}
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
    plugins.implements(plugins.ITemplateHelpers)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'landing_page_index':
            lambda pkg_name: LANDING_PAGE_DIR + '/' + pkg_name + '/index.html'
        }

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
