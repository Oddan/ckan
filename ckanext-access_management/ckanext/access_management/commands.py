import sys
from ckan.lib.cli import CkanCommand
from .plugin import ensure_special_access_table_present

class SetupTable(CkanCommand):
    ''' 
    Ensure that the database tables needed by the 'access_management' plugin 
    exist.

    Usage:
    paster ensure_tables_exists
       - Creates the table(s) required

    '''
    
    summary = "ensure 'access_management' plugin tables present"
    usage = __doc__
    min_args = 1
    max_args = 1

    def __init(self, name):
        super(SetupTable, self).__init(name)

    def command(self):
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.usage
            sys.exit(1)

        cmd = self.args[0]
        self._load_config()

        if cmd == "ensure_tables_exists":
            ensure_special_access_table_present()
        else:
            self.log.error('Command %s not recognized' % (cmd,))
