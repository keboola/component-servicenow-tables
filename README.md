
=============

**Table of contents:**

[TOC]

Functionality notes
===================

This component extracts data from ServiceNow using [Table API endpoint](https://developer.servicenow.com/dev.do#!/reference/api/tokyo/rest/c_TableAPI#table-GET). 

Configuration
=============

## ServiceNow table extractor configuration
 - Username (user) - [REQ] a username used to log in to ServiceNow
 - Password (#password) - [REQ] a password associated with username
 - Server (server) - [OPT] server url that should look like "https://kebooladev.service-now.com"
 - Threads (threads) - [OPT] integer that specifies number of threads used to call ServiceNow API for a single row. Keep in mind that setting this to a high number and combining with parallel row execution can lead to overload of the source system. This can further lead to API returning 5** status codes that will force the extractor to use backoff strategy leading to increased component run times. Default number of threads is 8
 - Output bucket (output_bucket) - [OPT] Name of the output bucket. If the bucket with specified name does not exit, it will be created automatically.

## ServiceNow table extractor row configuration
 - Table (table) - [REQ] Name of the table to be extracted
 - SysParm Query (sysparm_query) - [OPT] Query which will be sent along with get table request.
For more information about querying please refer to [Table API documentation](https://developer.servicenow.com/dev.do#!/reference/api/tokyo/rest/c_TableAPI#table-GET).
 - SysParm Fields (sysparm_fields) - [OPT] Using this parameter you can limit fetched fields. Please use comma separation.
 - Increment (increment) - [OPT] Use this parameter to define if you want to do incremental load.

Sample Configuration
=============
```json
{
    "parameters": {
        "user": "servicenow_user",
        "#password": "SECRET_VALUE",
        "server": "https://kebooladev.service-now.com",
        "table": "asmt_metric_result",
        "sysparm_query": "sys_created_on>javascript:gs.dateGenerate('2020-12-31','23:59:59')",
        "sysparm_fields": "sys_id,sc_item_option,request_item",
        "output_bucket": "test_bucket",
        "threads": 8
    },
    "action": "run"
}
```

Output
======

Tables with columns specified in `sysparm_fields` and rows filtered by `sysparm_query`.
Tables are loaded with column `sys_id` used as primary key.

Development
-----------

If required, change local data folder (the `CUSTOM_FOLDER` placeholder) path to your custom path in
the `docker-compose.yml` file:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone this repository, init the workspace and run the component with following command:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
docker-compose build
docker-compose run --rm dev
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the test suite and lint check using this command:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
docker-compose run --rm test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration
===========

For information about deployment and integration with KBC, please refer to the
[deployment section of developers documentation](https://developers.keboola.com/extend/component/deployment/)