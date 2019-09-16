from ckan.controllers import package
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from flask import send_file, Blueprint, render_template
#from flask import request
import ckan.lib.helpers as h
from ckan.lib.base import abort, render
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.common import g, _, request, config
import ckan.lib.formatters as formatters
# from ckan.controllers.package import PackageController
from functools import wraps
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
DEFAULT_MAX_ZIPFILE_SIZE = 1e9; # A different value can be set using config
                                # parameter 'ckan.cdsmetadata.max_zipfile_size'
_SIZE_ERROR_DIRECTIVE = 'size_error'
_DOWNLOAD_FORM_DIRECTIVE = 'download_form'

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
            if 'zipfile' not in request.files \
               or request.files['zipfile'] == '':
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
            target_dir = path.join(PLUGIN_DIR, 'public',
                                   LANDING_PAGE_DIR, pkg_name)
            if path.exists(target_dir):
                shutil.rmtree(target_dir)
            return tk.redirect_to(h.url_for(controller='package',
                                            action='read', id=pkg_id))

    extra_vars = {'pkg': pkg, 'pkg_name': pkg_name, 'errors': errors}
    return render('landing_page_upload.html', extra_vars)


def _screen_download_request():

    num_selected = len(request.form.values())

    if num_selected == 0:
        return ('', 204) # no content

    context = {'model': model, 'user': g.user, 'auth_user_obj': g.userobj}
    package_id = _package_id_of_resource(context, request.form.values()[0])
    max_zipfile_size = float(config.get('ckan.cdsmetadata.max_zipfile_size',
                                        DEFAULT_MAX_ZIPFILE_SIZE))

    def _combined_size(res_ids):
        sz = 0L
        for res_id in res_ids:
            sz = sz + model.Resource.get(res_id).size
        return sz

    if num_selected > 1 and \
         _combined_size(request.form.values()) > max_zipfile_size:
        # display overlay error message and let user try again
        return tk.redirect_to(h.url_for(controller='package',
                                        action='read', id=package_id,
                                        data='0',
                                        download_directive = _SIZE_ERROR_DIRECTIVE))

    # everything is all right.  Redirect user to form to fill-in before download.
    data = ''.join([rid + "_" for rid in request.form.values()]).strip('_')
    return tk.redirect_to(h.url_for(controller='package',
                                    action='read', id=package_id,
                                    data=data,
                                    download_directive=_DOWNLOAD_FORM_DIRECTIVE))
    

def _download_multiple_resources():

    context = {'model': model, 'user': g.user, 'auth_user_obj': g.userobj}
    max_zipfile_size = float(config.get('ckan.cdsmetadata.max_zipfile_size',
                                        DEFAULT_MAX_ZIPFILE_SIZE))
    if request.method == "POST":

        headers = {}
        if 'Cookie' in request.headers.keys():
            headers['Cookie'] = request.headers['Cookie']

        if len(request.form.values()) == 0:
            return None # nothing to do

        package_id = _package_id_of_resource(context, request.form.values()[0])

        def _get_url(res_id):
            return h.url_for(controller='package',
                             action='resource_download',
                             id=package_id,
                             resource_id=res_id,
                             qualified=True)

        def _get_file(url):
            return requests.get(url, allow_redirects=True, headers=headers)

        def _get_filename(res_id):
            return basename(model.Resource.get(res_id).url)

        def _combined_size(res_ids):
            sz = 0L
            for res_id in res_ids:
                sz = sz + model.Resource.get(res_id).size
            return sz

        if len(request.form.values()) == 1:
            res_id = request.form.values()[0]
            # no need to zip several files together
            url = _get_url(res_id)
            f = _get_file(url)
            if f.status_code == 404:
                return render_template(u"package/download_denied.html")
            
            return send_file(io.BytesIO(f.content),
                             mimetype='application/octet-stream',
                             as_attachment=True,
                             attachment_filename=_get_filename(res_id))
                
        # check if size limit is surpassed for creation of intermediary zip-files
        if _combined_size(request.form.values()) > max_zipfile_size:
            # show error message and do nothing else
            return tk.redirect_to(h.url_for(controller='package',
                                            action='read', id=package_id,
                                            data='0',
                                            download_directive = _SIZE_ERROR_DIRECTIVE))

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, mode='w',
                             compression=zipfile.ZIP_STORED) as zf:

            # combined size is acceptable.  Let us create the zipfile
            for res_id in request.form.values():
                # @@ change when Flask becomes responsible for resources
                url = _get_url(res_id)
                f = _get_file(url)
                if f.status_code == 404:
                    return render_template(u"package/download_denied.html")
                filename = _get_filename(res_id)
                zf.writestr(filename, f.content)
                
        memory_file.seek(0)

        return send_file(memory_file,
                         mimetype='application/zip',
                         as_attachment=True,
                         attachment_filename='download.zip')


def _package_read_patch(function):

    @wraps(function)
    def wrapper(*args, **kwargs):
        id = kwargs.get('id', None)
        g.zipfile_size_limit = formatters.localised_filesize(
            int(config.get('ckan.cdsmetadata.max_zipfile_size',
                           DEFAULT_MAX_ZIPFILE_SIZE)))

        directive = kwargs.get('download_directive', None)

        g.size_error_occured = False
        g.selected_resource_ids = None
        if directive == _SIZE_ERROR_DIRECTIVE:
            g.size_error_occured = True
        elif directive == _DOWNLOAD_FORM_DIRECTIVE:
            g.selected_resource_ids = kwargs.get('data', None)
            if g.selected_resource_ids is not None:
                g.selected_resource_ids = g.selected_resource_ids.split('_')

        return function(*args, id=id)

    return wrapper
        
    
class CdsLandingPagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IMiddleware)
    plugins.implements(plugins.IRoutes)

    # IRoutes
    def before_map(self, map):
        # add functionality to package.read function through local wrapper
        map.connect('/dataset/{id}/{data}/{download_directive}',
                    controller='package', action='read')
        return map

    def after_map(self, map):
        return map

    # IMiddleware
    def make_middleware(self, app, config):
        # fetch the package.read function, which we need to generate pages with
        # custom error warnings
        if not tk.check_ckan_version('2.8.2', '2.8.2'):
            raise tk.CkanVersionException

        if app.app_name == 'pylons_app':
            ctrl = app.find_controller('package')
            ctrl.read = _package_read_patch(ctrl.read)
        else:
            assert app.app_name == 'flask_app'
            
        return app

    def make_error_log_middleware(self, app, config):
        return app

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
        blueprint.add_url_rule(u'/screen_download_request',
                               u'screen_download_request',
                               _screen_download_request,
                               methods=['POST'])
        blueprint.add_url_rule(u'/landing_page_upload/<pkg_name>',
                               u'landing_page_upload',
                               _landing_page_upload,
                               methods=['GET', 'POST'])

        return blueprint
