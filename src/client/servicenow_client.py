from keboola.http_client import HttpClient
from requests.exceptions import HTTPError
import logging
from keboola.csvwriter import ElasticDictWriter


class ServiceNowClientError(Exception):
    pass


class ServiceNowClient:
    def __init__(self, user, password, server):
        self.server = server
        self.limit = 500

        default_header = {
            'Accept': 'application/json'
        }

        default_params = {
            'sysparm_limit': self.limit
        }

        self.client = HttpClient(server, default_http_header=default_header, auth=(user, password),
                                 default_params=default_params)

    def fetch_table(self, table, sysparm_query, sysparm_fields, table_def):
        params = {}
        if sysparm_query:
            params["sysparm_query"] = sysparm_query
        if sysparm_fields:
            params["sysparm_fields"] = sysparm_fields

        sysparm_offset = 0

        first_request = True
        has_more = True
        with ElasticDictWriter(table_def.full_path, []) as wr:
            while has_more:
                params["sysparm_offset"] = sysparm_offset
                r = self.client.get_raw(table, params=params)

                try:
                    r.raise_for_status()
                except HTTPError as e:
                    raise ServiceNowClientError(f"Unable to fetch data for table {table}") from e

                if first_request:
                    total_count = r.headers.get("X-Total-Count")
                    logging.info(f"Component will fetch {total_count} rows for table {table}.")
                    first_request = False

                result = r.json().get("result")
                wr.writerows(result)

                if len(result) < self.limit:
                    has_more = False

                logging.info(f"Processed records: {sysparm_offset+len(result)}")
                sysparm_offset += self.limit

            wr.writeheader()
            logging.info(f"Done fetching of table {table}")


