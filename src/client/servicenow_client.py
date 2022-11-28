from keboola.http_client import HttpClient
from requests.exceptions import HTTPError
import logging
from keboola.csvwriter import ElasticDictWriter
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from functools import partial
import math
import os


class ServiceNowClientError(Exception):
    pass


class ServiceNowClient:
    def __init__(self, user, password, server, threads):
        self.server = server
        self.limit = 500
        self.threads = threads

        default_header = {
            'Accept': 'application/json'
        }

        tc_default_params = {
            'sysparm_limit': self.limit
        }

        table_url = server + "/api/now/v2/table/"
        stats_url = server + "/api/now/stats/"

        self.table_client = HttpClient(table_url, default_http_header=default_header, auth=(user, password),
                                       default_params=tc_default_params)

        self.stats_client = HttpClient(stats_url, default_http_header=default_header, auth=(user, password))
        self.fieldnames_list = []

    def fetch_page(self, table, params, table_def, offset):
        filename = table+str(offset)
        path = os.path.join(table_def.full_path, filename)

        with ElasticDictWriter(path, []) as wr:
            params["sysparm_offset"] = offset
            r = self.table_client.get_raw(table, params=params)

            try:
                r.raise_for_status()
            except HTTPError as e:
                raise ServiceNowClientError(f"Unable to fetch data for table {table} with error {e}") from e

            total_count = r.headers.get("X-Total-Count")

            result = r.json().get("result")
            wr.writerows(result)
            self.fieldnames_list.append(wr.fieldnames)

        logging.info(f"Table progress: {table} - {offset + len(result)}/{total_count}")

    def get_table_stats(self, table, sysparm_query, sysparm_fields):
        params = {}
        if sysparm_query:
            params["sysparm_query"] = sysparm_query
        if sysparm_fields:
            params["sysparm_fields"] = sysparm_fields
        params["sysparm_count"] = True

        r = self.stats_client.get_raw(table, params=params)
        return r.json()["result"]["stats"]["count"]

    def fetch_table(self, table, sysparm_query, sysparm_fields, table_def):
        row_count = self.get_table_stats(table, sysparm_query, sysparm_fields)
        iterations = math.ceil(int(row_count)/self.limit)

        offset_list = []

        params = {}
        if sysparm_query:
            params["sysparm_query"] = sysparm_query
        if sysparm_fields:
            params["sysparm_fields"] = sysparm_fields
        sysparm_offset = 0

        for _ in range(iterations):
            offset_list.append(sysparm_offset)
            sysparm_offset += self.limit

        func = partial(self.fetch_page, table, params, table_def)

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {
                executor.submit(func, offset): offset for offset in offset_list
            }
            for future in as_completed(futures):
                if future.exception():
                    raise ServiceNowClientError(f"Fetching failed for chunk {futures[future]}"
                                                f", reason: {future.exception()}.")

        logging.info(f"Done fetching of table {table}")

    def fieldnames_ok(self) -> bool:
        iterator = iter(self.fieldnames_list)
        try:
            first = next(iterator)
        except StopIteration:
            return True
        return all(first == x for x in iterator)

    def get_fieldnames(self) -> list:
        return self.fieldnames_list[0]
