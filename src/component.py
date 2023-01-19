'''
Template Component main class.

'''
import logging
import os
import shutil

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

from client.servicenow_client import ServiceNowClient, ServiceNowClientError, ServiceNowCredentialsError  # noqa

# configuration variables
KEY_USER = 'user'
KEY_PASSWORD = '#password'
KEY_SERVER = 'server'
KEY_TABLE = 'table'
KEY_SYSPARM_QUERY = 'sysparm_query'
KEY_SYSPARM_FIELDS = 'sysparm_fields'
KEY_THREADS = 'threads'
KEY_INCREMENT = 'increment'
KEY_BUCKET = 'output_bucket'

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
        """
        Main execution code
        """

        self.validate_configuration_parameters(REQUIRED_PARAMETERS)
        params = self.configuration.parameters

        user = params.get(KEY_USER)
        password = params.get(KEY_PASSWORD)
        table = params.get(KEY_TABLE)
        server = params.get(KEY_SERVER)
        sysparm_query = params.get(KEY_SYSPARM_QUERY)
        sysparm_fields = params.get(KEY_SYSPARM_FIELDS)
        increment = params.get(KEY_INCREMENT)
        if not increment:
            increment = False

        threads = params.get(KEY_THREADS)
        if not threads:
            threads = 8

        output_bucket = params.get(KEY_BUCKET)
        if not output_bucket:
            output_bucket = "kds-team.ex-servicenow-tables"

        logging.info(f"Component will use {str(threads)} threads.")

        client = ServiceNowClient(user=user, password=password, server=server, threads=threads)

        table_def = self.create_out_table_definition(table, destination=f'in.c-{output_bucket}.{table}',
                                                     incremental=increment, primary_key=['sys_id'])

        temp_folder = os.path.join(self.data_folder_path, "temp")
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)

        try:
            fetching_done = client.fetch_table(table=table,
                                               sysparm_query=sysparm_query,
                                               sysparm_fields=sysparm_fields,
                                               table_def=table_def,
                                               temp_folder=temp_folder)
        except ServiceNowCredentialsError as e:
            raise UserException(e)

        if fetching_done:
            self.write_manifest(table_def)
        else:
            shutil.rmtree(table_def.full_path)
        shutil.rmtree(temp_folder)


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
