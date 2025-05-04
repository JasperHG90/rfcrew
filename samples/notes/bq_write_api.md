# [Ingestor] Using the BigQuery Write API with Protobuf Messages

## 👇 Context & scope

In [Ingestor] Use of BigQuery storage write API streaming inserts we decided to use the BigQuery Write API to ingest data from Datahubs into the Data Warehouse.

This requires some investigation, as there is limited documentation available on how to use the BQ Write API with Python.

## Background

We have a Python application that needs to retrieve new data from a DataHubs API and store it in BigQuery every ten minutes. We're trying to figure out what the best way of doing this is.

## Problem definition

We need to choose the best way of writing data to BigQuery given that we're using a python application on google cloud run.

## Requirements

- We need to use Python to send batches of data to BigQuery
- We need to use the BigQuery Write API
- We want to use ProtoBuf for desining the schema
- The solution needs to be atomic at the row level

## 👍 Follow-ups

*   Implement a Python function to automatically generate a Proto schema from a BigQuery table
