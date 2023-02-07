import logging
import os
import shutil
import csv

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
    def __init__(self):
        super().__init__()
        self.statefile_columns = None
        self.stored_columns = None

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

        statefile = self.get_state_file()
        self.statefile_columns = statefile.get("columns", [])

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
            self.handle_columns(table_def.full_path, self.statefile_columns)
        else:
            shutil.rmtree(table_def.full_path)
        shutil.rmtree(temp_folder)

        self.write_state_file({"columns": self.stored_columns})

    def handle_columns(self, input_file, old_columns):
        """
        Removes empty columns resulting from json flattening.
        Also uses statefile to append columns that are stored in statefile so that Keboola mapping
        does not fail
        :param input_file: definition object of handled file
        :param old_columns: List of columns stored in previous run (loaded from statefile)
        :return: None
        """
        logging.info("Removing empty rows")
        with open(input_file, 'r') as file_in:
            reader = csv.DictReader(file_in)
            header = reader.fieldnames

            empty_columns = header.copy()
            for row in reader:
                for col in header:
                    if col in empty_columns and row[col] != "":
                        empty_columns.remove(col)

            logging.info(f"The following empty columns will be removed: {empty_columns}")
            non_empty_columns = [item for item in header if item not in empty_columns]

        with open(input_file, 'r') as file_in:
            reader = csv.DictReader(file_in)

            temp_file = input_file + '.temp'
            with open(temp_file, 'w', newline='') as file_out:
                fieldnames = list(set(non_empty_columns+old_columns))
                writer = csv.DictWriter(file_out, fieldnames=fieldnames)
                writer.writeheader()
                for row in reader:
                    new_row = {k: v for k, v in row.items() if k in non_empty_columns}
                    for col in self.statefile_columns:
                        if col not in list(new_row.keys()):
                            new_row[col] = ""
                    writer.writerow(new_row)

        os.replace(temp_file, input_file)
        self.stored_columns = non_empty_columns


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
