from flask import Blueprint
#from flask.globals import _request_ctx_stack, request, session, g
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import pdb


def custom_action():
    return "Hello World!"

class TestMiddleware:
    def __init__(self, app):
        #pdb.set_trace()
        self.app = app

        try:
            @app.before_request
            def tull():
                # only let logged-in users access site
                if toolkit.request.remote_user is None:
                    return toolkit.render("frontpagewrapper.html", {})
                    #return "Hello World~!"

        except Exception as e:
            pass 
        
    def __call__(self, environ, start_response):
        #pdb.set_trace()

        #return self.app.finalize_request("Hello world")
        #return "Hello world"
        #krull = self.app(environ,start_response)
        return self.app(environ,start_response)


class FrontpagewrapperPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IMiddleware)
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')

    def make_middleware(self, app, config):
        #pdb.set_trace()
        app = TestMiddleware(app)
        return app
        
    
    # plugins.implements(plugins.IBlueprint)

    # def get_blueprint(self):
    #     blueprint = Blueprint('foo', self.__module__)
    #     rules = [
    #         ('/', 'custom_action', custom_action),
    #     ]
    #     for rule in rules:
    #         blueprint.add_url_rule(*rule)

    #     return blueprint
    
