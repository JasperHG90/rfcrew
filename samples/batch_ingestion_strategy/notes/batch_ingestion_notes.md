# Choosing a batch ingestion strategy

## Context & scope

We need to choose a batch ingestion strategy that addresses the majority of data sources that we will initially need at our client.

## Background

We want to focus on:

- ‘Straight forward’ data sources (e.g. relational databases) that easily fit in the paradigm of Azure Data Factory, and for which we can define broadly applicable and repeatable logic.

Not on complex patterns:

- Full ingestion loads rather than incremental loads. The latter will be the subject of a future RFC.

## Problem definition

Our client has a lot of Azure SQL databases. We need to:

1. Extract these using ADF, store at some location
2. Process with Databricks and Data build tool (dbt), store in data lake
3. Send out a hook to Power BI to refresh a report

We use Astronomer Airflow to orchestrate the entire flow.

## Preliminary research

- We can use ADLS as storage layer (e.g. landing zone and data lake)
- dbt has integration with databricks
- Airflow can integrate with dbt, databricks, and ADF

## Requirements

- We prefer to keep our solution as simple as possible.
- Data stored in the landing area must be in Parquet format
- All data stored in landing zone must use a logical path convention (e.g.  '/data_source/database/schema/logical_date_table/*.parquet')
- All data stored in data lake must be in delta format.

## Open questions

- Archiving data: what's the best strategy? Can we just place a lifecycle on our storage layer?

## Out of scope

- Schema evolution in source systems
