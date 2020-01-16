from ckan.controllers import package
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from flask import send_file, Blueprint, render_template
#from flask import request
import ckan.lib.helpers as h
from ckan.lib.base import abort, render
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.common import g, _, request, config
from country_list import iso3166_1
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
import fileinput
from exceptions import IOError
# abort(403, _('Not authorized to see this page.'))


PLUGIN_DIR = path.dirname(__file__)
LANDING_PAGE_DIR = 'landing_pages'
COUNTRY_OPTION_LIST = [{'name': c[1], 'value': c[0]} for c in iso3166_1]
DEFAULT_MAX_ZIPFILE_SIZE = 1e9; # A different value can be set using config
                                # parameter 'ckan.cdsmetadata.max_zipfile_size'

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


def _update_static_links(target_dir, replacement):

    # Replace references to 'static/' in the landing page HTML file with the
    # actual path used.  This solution is quick-and-dirty, a more rigorous
    # treatment might be considered.
    fname = path.join(target_dir, 'index.html')
    if not os.path.exists(fname):
        raise IOError('index.html not found')
    
    f = fileinput.FileInput(fname, inplace=True)
    for line in f:
        print(line.replace('./static/', '/' + replacement + '/'))
    f.close()


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
        _update_static_links(tmp_target_dir,
                             path.join(LANDING_PAGE_DIR, pkg_name, 'static'))
    except:
        # unable to extract archive.  Clean up and return error
        if path.exists(tmp_target_dir):
            shutil.rmtree(tmp_target_dir)
        return ["Error: failed to extract zip-file.  Corrupt?"]

    # extraction went OK.  Move result to target directory
    if path.exists(target_dir):
        shutil.rmtree(target_dir)
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


def _download_multiple_resources():

    context = {'model': model, 'user': g.user, 'auth_user_obj': g.userobj}
        
    res_ids = request.form.getlist('res_id')
    country = request.form.get('country', u'unspecified').encode('utf-8')
    affiliation = \
        request.form.get('affiliation', u'unspecified').strip().upper().encode('utf-8')

    headers = {'country': country, 'affiliation': affiliation}
    if 'Cookie' in request.headers.keys():
        headers['Cookie'] = request.headers['Cookie']

    if len(res_ids) == 0:
        # this should never happen (form should always contain at least one resource id
        abort(404, 'Resources not found.')

    package_id = _package_id_of_resource(context, res_ids[0])

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
        
    if len(res_ids) == 1:
        # no need to zip several files together
        url = _get_url(res_ids[0])
        return h.redirect_to(url)
        # f = _get_file(url)
        # if f.status_code == 403:
        #     return render_template(u"package/download_denied.html")
        # elif f.status_code == 404:
        #     return render_template(u"package/download_failed.html")
        
        # return send_file(io.BytesIO(f.content),
        #                  mimetype='application/octet-stream',
        #                  as_attachment=True,
        #                  attachment_filename=_get_filename(res_ids[0]))

    # if we got here, more than one resource were requested.  We zip them
    # together to a single download file.
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, mode='w',
                         compression=zipfile.ZIP_STORED) as zf:

        for res_id in res_ids:
            # @@ change when Flask becomes responsible for resources
            url = _get_url(res_id)
            f = _get_file(url)
            if f.status_code == 403:
                return render_template(u"package/download_denied.html")
            elif f.status_code == 404:
                return render_template(u"package/download_denied.html")
            filename = _get_filename(res_id)
            zf.writestr(filename, f.content)
            
    memory_file.seek(0)
    
    return send_file(memory_file,
                     mimetype='application/zip',
                     as_attachment=True,
                     attachment_filename='download.zip')


def _res_combined_size(res_ids):
    sz = 0L
    for res_id in res_ids:
        sz = sz + model.Resource.get(res_id).size
    return sz


def _resource_names(res_ids):
    return [model.Resource.get(res_id).name for res_id in res_ids]


def _max_zipfile_size():
    return float(config.get('ckan.cdsmetadata.max_zipfile_size',
                            DEFAULT_MAX_ZIPFILE_SIZE))


def _package_read_patch(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if request.method == 'POST':

            # The user has posted request to download dataset components.
            g.selected_resource_ids = request.params.values()
            g.selected_resource_names = _resource_names(g.selected_resource_ids)
            g.max_zipfile_size = \
                formatters.localised_filesize(int(_max_zipfile_size()))
            
            if len(g.selected_resource_ids) == 0:
                g.handle_request_error = 'no_requested_data'
            elif len(g.selected_resource_ids) > 1 and \
                 _res_combined_size(g.selected_resource_ids) > _max_zipfile_size():
                g.handle_request_error = 'exceeds_max_zipfile_size'
            else:
                # request was well formed, display download form
                g.country_list = COUNTRY_OPTION_LIST
                g.show_download_dialog = True
            
        # call the original controller function
        return function(*args, id=kwargs.get('id', None))

    return wrapper

def _resource_read_patch(function):

    @wraps(function)
    def wrapper(*args, **kwargs):
        
        if request.method == 'POST':
            res_id = kwargs['resource_id']
            # tell jinja to show the download dialog
            g.country_list = COUNTRY_OPTION_LIST
            g.show_download_dialog = True
            g.selected_resource_ids = [res_id]
            g.selected_resource_names = _resource_names([res_id])

        return function(*args,
                        id=kwargs.get('id', None),
                        resource_id=kwargs.get('resource_id', None))

    return wrapper
    
class CdsLandingPagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IMiddleware)

    # IMiddleware
    def make_middleware(self, app, config):
        # fetch the package.read function, which we need to generate pages with
        # custom error warnings
        if not tk.check_ckan_version('2.8.2', '2.8.2'):
            raise tk.CkanVersionException

        if app.app_name == 'pylons_app':
            ctrl = app.find_controller('package')
            ctrl.read = _package_read_patch(ctrl.read)
            ctrl.resource_read = _resource_read_patch(ctrl.resource_read)
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
        blueprint.add_url_rule(u'/landing_page_upload/<pkg_name>',
                               u'landing_page_upload',
                               _landing_page_upload,
                               methods=['GET', 'POST'])

        return blueprint
