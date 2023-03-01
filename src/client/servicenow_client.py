import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from functools import partial
import math
import os
import backoff as backoff
import json
import uuid
from collections.abc import MutableMapping

import requests.exceptions
from keboola.http_client import HttpClient
from requests.exceptions import HTTPError, JSONDecodeError
from keboola.csvwriter import ElasticDictWriter


def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


class ServiceNowClientError(Exception):
    pass


class ServiceNowCredentialsError(Exception):
    pass


class ServiceNowClient:
    def __init__(self, user, password, server, threads):
        self.server = server
        self.limit = 300
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

    @backoff.on_exception(backoff.expo, ServiceNowClientError, max_tries=10)
    def fetch_page(self, table, params, temp_folder, offset):

        params["sysparm_offset"] = offset
        r = self.table_client.get_raw(table, params=params)

        try:
            r.raise_for_status()
        except HTTPError as e:
            raise ServiceNowClientError(f"Unable to fetch data for table {table} with error {e}") from e

        total_count = r.headers.get("X-Total-Count")

        try:
            result = r.json().get("result")
        except JSONDecodeError as e:
            raise ServiceNowClientError(f"Unable to parse response data with error: {e}") from e

        if isinstance(result, str):
            raise ServiceNowClientError(f"Result is str: {result}")

        for row in result:
            with open(os.path.join(temp_folder, f"{uuid.uuid1()}.json"), "w") as outfile:
                json.dump(flatten(row), outfile)

        return f"Table progress: {table} - {offset + len(result)}/{total_count}"

    @backoff.on_exception(backoff.expo, ServiceNowClientError, max_tries=5)
    def get_table_stats(self, table, sysparm_query, sysparm_fields):
        params = {}
        if sysparm_query:
            params["sysparm_query"] = sysparm_query
        if sysparm_fields:
            params["sysparm_fields"] = sysparm_fields
        params["sysparm_count"] = True

        try:
            r = self.stats_client.get_raw(table, params=params)
            r.raise_for_status()
        except HTTPError as e:
            raise ServiceNowClientError(f"Unable to fetch rows count for table {table} with error {e}") from e

        try:
            result = r.json().get("result")
        except JSONDecodeError as e:
            raise ServiceNowClientError(f"unable to parse response data with error: {e}") from e

        return result["stats"]["count"]

    def fetch_table(self, table, sysparm_query, sysparm_fields, table_def, temp_folder) -> bool:
        """
        Returns True if fetching was successful, otherwise returns False. This is to avoid mapping errors in Keboola
        storage.
        """
        try:
            row_count = self.get_table_stats(table, sysparm_query, sysparm_fields)
        except requests.exceptions.MissingSchema as e:
            raise ServiceNowClientError(e)
        except ServiceNowClientError as e:
            raise ServiceNowCredentialsError("Cannot get table stats. Please check your credentials.") from e

        if int(row_count) == 0:
            logging.warning(f"API returned no results for table {table}, with query {sysparm_query}.")
            return False

        iterations = math.ceil(int(row_count) / self.limit)

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

        func = partial(self.fetch_page, table, params, temp_folder)

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {
                executor.submit(func, offset): offset for offset in offset_list
            }

            for future in as_completed(futures):
                logging.info(future.result())
        logging.info(f"Done fetching of table {table}")

        with ElasticDictWriter(table_def.full_path, []) as wr:
            for file in os.scandir(temp_folder):
                try:
                    with open(file.path) as json_file:
                        data = json.load(json_file)
                        wr.writerow(data)
                except UnicodeDecodeError:
                    raise Exception(f"Bad File: {file.path}")
                except JSONDecodeError:
                    raise Exception(f"Bad File: {file.path}")
            wr.writeheader()
        return True
