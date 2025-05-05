# Using the BigQuery Write API with Protobuf Messages

## Context & scope

In a previous RFC we decided to use the BigQuery Write API to ingest data from our internal API into our BigQuery data warehouse.

This requires some investigation, as there is limited documentation available on how to use the BQ Write API with Python.

## Background

We have a Python application that retrieves data from an API and stores it in BigQuery. It runs every ten minutes. We need to find out what the best way to do this is given our constraints and requirements

## Problem definition

We need to choose the best way of writing data to BigQuery given that we're using a python application on google cloud run. Our Python application runs every 10 minutes, retrieves data from an API, and sends it to BigQuery.

We cannot use Pub/Sub since we are not allowed to use it. As such, we need a pure Python implementation.

All services must be deployed on Google Cloud Platform (GCP). We strongly prefer to use serverless infrastructure.

## Preliminary research

- We can use Pub/Sub with BigQuery as a subscriber to a topic to stream data directly to BQ using Pub/Sub. This is not allowed but it would be good to do some investigation here to contrast it against using the BQ write API from python. The approach is superior I think because it removes the need to use Protobuf schemas, queueing etc.
- There is a legacy Python approach that apprently we should not use. The BQ write API is the way to go.
- We strongly prefer using the `_default` stream to reduce complexity.

## Requirements

- We need to use Python to send batches of data to BigQuery.
- We need to use the BigQuery Write API.
- We prefer to keep our solution as simple as possible.
- We want to use ProtoBuf for designing the schema
- The solution does not need to be atomic at the row level
- We require at-least-once semantics

## Open questions

- What's the best way to handle schema evolution?

## Other requirements

Please add code samples that we can use.
