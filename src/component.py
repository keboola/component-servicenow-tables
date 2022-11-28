'''
Template Component main class.

'''
import logging
import os

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

from client.servicenow_client import ServiceNowClient, ServiceNowClientError # noqa

# configuration variables
KEY_USER = 'user'
KEY_PASSWORD = '#password'
KEY_SERVER = 'server'
KEY_TABLE = 'table'
KEY_SYSPARM_QUERY = 'sysparm_query'
KEY_SYSPARM_FIELDS = 'sysparm_fields'
KEY_THREADS = 'threads'

# list of mandatory parameters => if some is missing,
# component will fail with readable message on initialization.
REQUIRED_PARAMETERS = [KEY_USER, KEY_SERVER, KEY_TABLE]
REQUIRED_IMAGE_PARS = []


class Component(ComponentBase):
    """
        Extends base class for general Python components. Initializes the CommonInterface
        and performs configuration validation.

        For easier debugging the data folder is picked up by default from `../data` path,
        relative to working directory.

        If `debug` parameter is present in the `config.json`, the default logger is set to verbose DEBUG mode.
    """

    def __init__(self):
        super().__init__()

    def run(self):
        '''
        Main execution code
        '''

        # ####### EXAMPLE TO REMOVE
        # check for missing configuration parameters
        self.validate_configuration_parameters(REQUIRED_PARAMETERS)
        params = self.configuration.parameters

        user = params.get(KEY_USER)
        password = params.get(KEY_PASSWORD)
        table = params.get(KEY_TABLE)
        server = params.get(KEY_SERVER)
        sysparm_query = params.get(KEY_SYSPARM_QUERY)
        sysparm_fields = params.get(KEY_SYSPARM_FIELDS)
        threads = params.get(KEY_THREADS)
        if not threads:
            threads = 8
        logging.info(f"Component will use {str(threads)} threads.")

        client = ServiceNowClient(user=user, password=password, server=server, threads=threads)

        table_def = self.create_out_table_definition(f'{table}.csv', incremental=True, primary_key=['sys_id'])
        if not os.path.exists(table_def.full_path):
            os.makedirs(table_def.full_path)

        client.fetch_table(table=table, sysparm_query=sysparm_query, sysparm_fields=sysparm_fields, table_def=table_def)
        if not client.fieldnames_ok():
            raise UserException("There was a problem with fieldnames. Component is unable to save data.")
        self.write_manifest(table_def)


"""
        Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        # this triggers the run method by default and is controlled by the configuration.action parameter
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
