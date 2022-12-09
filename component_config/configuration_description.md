#### Input

##### Config Description

A Configuration of 4 mandatory parameters is required for base configuration. A sample configuration of the component can be found in [component's repository](https://bitbucket.org/kds_consulting_team/kds-team.ex-servicenow-tables/src/master/component_config/sample-config/config.json).

- Username (`user`) - a username used to log in to ServiceNow;
- Password (`#password`) - a password associated with username;
- Server (`server`) - server url that should look like "https://kebooladev.service-now.com";
- Output bucket (`output_bucket`) - Name of the output bucket. If the bucket with specified name does not exit, it will be created automatically.

Optional parameters:

- threads (`server`) - integer that specifies number of threads used to call ServiceNow API for a single row.
Keep in mind that setting this to a high number and combining with parallel row execution can lead to overload of the source system.
This can further lead to API returning 5** status codes that will force the extractor to use backoff strategy leading to increased 
component run times. Default number of threads is 8;

##### Row Configuration Description

Additionally, 1 mandatory parameter is required for row configuration.

- Table (`table`) - Name of the table in ServiceNow database;

Optional parameters:

- SysParm Query (`sysparm_query`) - Use this parameter to limit the number of results;
- SysParm Fields (`sysparm_fields`) - Use this parameter to limit the number of columns.
You must use a comma separated list of values;
- Increment (`increment`) - This parameter specifies whether to store data to Keboola storage Incrementally
or whether to use full load (Table will be truncated first before importing new data);

#### Output

Tables with columns specified in `sysparm_fields` and rows filtered by `sysparm_query`.
Tables are loaded with column `sys_id` used as primary key.