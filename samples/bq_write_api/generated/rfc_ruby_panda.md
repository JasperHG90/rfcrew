# RFC: Python Batch Ingestion to BigQuery via Storage Write API and Protobuf

## 📜 Table of contents
---
<!-- Use markdown-toc or similar to generate this -->
* [🤓 TL;DR;](#-tldr)
* [🔭 Context and Scope](#-context-and-scope)
* [🎯 Goals (and Non-Goals)](#-goals-and-non-goals)
* [🦉 The Actual Design](#-the-actual-design)
* [🌈 Alternatives considered](#-alternatives-considered)
* [💥 Impact](#-impact)
* [💬 Discussion](#-discussion)
* [🤝 Final decision](#-final-decision)
* [☝️ Follow-ups](#️-follow-ups)
* [🔗 Related](#-related)
* [📝 Reviewer Feedback Summary](#-reviewer-feedback-summary)

## 🤓 TL;DR;
---
This RFC proposes using the BigQuery Storage Write API via a pure Python application running on Cloud Run to ingest data batches from an internal API every 10 minutes. The solution will leverage Protobuf for schema definition and serialization, utilizing the `_default` stream for at-least-once delivery semantics and simplified implementation, adhering to the constraint of not using Pub/Sub. This approach balances efficiency and meets specific technical requirements but introduces operational considerations around schema management and error handling.
<!-- Peer Reviewer Comment: TL;DR is clear and accurately summarizes the core proposal and constraints. -->
<!-- Ops & Risk Comment: This TL;DR provides a good high-level overview. The use of Cloud Run, BQ Write API, Protobuf, and the default stream are key components to assess for operational impact, security, and cost. -->

## 🔭 Context and Scope
---
**Background:** We currently have a Python application responsible for retrieving data from an internal API and ingesting it into our BigQuery data warehouse. This application executes on a 10-minute schedule. A previous RFC established the decision to utilize the BigQuery Write API for this ingestion process, replacing potentially older or less efficient methods. However, specific implementation guidance, particularly for using the Write API with Python and Protobuf messages, is limited, necessitating this investigation.

**Problem Definition:** The core problem is to determine and document the optimal method for writing data batches from our scheduled Python application (running on Google Cloud Run) to BigQuery using the Write API. Key constraints include the mandatory use of Python, the prohibition of using Pub/Sub, a preference for serverless GCP infrastructure (Cloud Run), and the requirement to use Protobuf for schema definition. The application runs every 10 minutes, fetching data and sending it as a batch.
<!-- Ops & Risk Comment: The 10-minute schedule implies a batch processing pattern, not true streaming. This affects monitoring needs (batch success/failure vs. continuous stream health). -->

**Scope:**
*   **In Scope:** Defining the architecture and implementation pattern for a Python application on Cloud Run to batch-write data to BigQuery using the Storage Write API, Protobuf serialization, and the `_default` stream. Providing guidance on setup, error handling (including dead-lettering), schema management within this specific context, monitoring requirements, security considerations, and illustrative code samples.
*   **Out of Scope:** The specifics of the internal API data retrieval logic (including its reliability and error handling), the detailed design of the Protobuf schema itself (beyond the mechanism), alternative ingestion methods not using the Write API (like load jobs or legacy streaming), solutions involving Pub/Sub, or infrastructure choices outside of GCP serverless options (specifically Cloud Run). Row-level atomicity guarantees and exactly-once semantics are explicitly out of scope.
<!-- Peer Reviewer Comment: Context and scope are well-defined. Explicitly stating row-level atomicity is out of scope is important given the at-least-once semantics and batching. -->
<!-- Ops & Risk Comment: The exclusion of the internal API retrieval logic means its reliability, latency, and error handling characteristics are external dependencies that could impact this solution. This should be noted in operational readiness. -->
<!-- Ops & Risk Comment: Explicitly stating row-level atomicity is out of scope is important for setting expectations, especially regarding potential duplicates with at-least-once delivery. -->

## 🎯 Goals (and Non-Goals)
---
**Goals:**
*   Utilize a pure Python implementation for data ingestion.
*   Employ the BigQuery Storage Write API for sending data to BigQuery.
*   Implement batch data sending from the Python application.
*   Use Protobuf for defining the data schema and serializing payloads.
*   Achieve at-least-once delivery semantics for ingested data.
*   Keep the solution architecture as simple as possible within the constraints, specifically by using the `_default` stream.
*   Deploy the solution on GCP serverless infrastructure (Cloud Run).
*   Implement robust error handling, including dead-lettering for persistent failures.
*   Ensure the solution is monitorable and secure according to team standards.

**Non-Goals:**
*   Using Pub/Sub for data ingestion.
*   Using the legacy BigQuery streaming API (`tabledata.insertAll`).
*   Achieving exactly-once semantics or row-level atomicity across multiple append calls (downstream systems must handle potential duplicates).
*   Implementing dynamic schema detection and adaptation purely within the Write API client (schema evolution requires application updates and redeployment).
*   Providing a fully managed stream processing solution (the application runs in batches).
<!-- Peer Reviewer Comment: Goals and Non-Goals are clear and align with the problem statement and constraints. Explicitly stating at-least-once and not exactly-once is crucial and sets expectations correctly. -->
<!-- Ops & Risk Comment: The at-least-once guarantee with the default stream means downstream processes must be idempotent or handle potential duplicates. This is a key operational consideration. -->
<!-- Ops & Risk Comment: The non-goal of dynamic schema adaptation highlights the operational overhead of schema changes, which is addressed later but is a significant point for readiness. -->

## 🦉 The Actual Design
---
The proposed design involves a Python application deployed on Google Cloud Run. This application will run every 10 minutes, triggered via Cloud Scheduler invoking an authenticated HTTP endpoint on the Cloud Run service. It fetches data from the internal API, uses the `google-cloud-bigquery-storage` Python client library to serialize data to Protobuf format, and writes data batches to a designated BigQuery table via the Storage Write API's `_default` stream.

<!-- Ops & Risk Comment: Operations: Cloud Scheduler triggering Cloud Run via HTTP requires ensuring the Cloud Run service is not publicly accessible (use Internal ingress) and Cloud Scheduler is configured with appropriate authentication (e.g., OIDC tokens via its service account). -->
<!-- Ops & Risk Comment: Security: Ensure the Cloud Run service is configured for private ingress ('Internal' or 'Internal and Cloud Load Balancing') and requires authentication for invocation. -->
<!-- Peer Reviewer Comment: Using Cloud Run triggered by Cloud Scheduler is a standard and feasible pattern for scheduled tasks. -->

**Key Components & Flow:**

1.  **Protobuf Schema Definition (`.proto` file):**
    *   A `.proto` file (e.g., `your_data.proto`) defines the structure of the data messages, mirroring the target BigQuery table schema. This file is the source of truth for the data structure being ingested.
    *   This file is compiled using the `protoc` compiler (`protoc --python_out=. your_data.proto`) to generate corresponding Python classes (e.g., `your_data_pb2.py`).
    *   **CI/CD Integration:** This compilation step **must** be integrated into the CI/CD pipeline to ensure consistency and automate the generation of Python classes based on the committed `.proto` file definition. The `protoc` compiler version should be pinned.
    <!-- Peer Reviewer Comment: Standard Protobuf workflow. Agree that integrating `protoc` compilation into the CI/CD pipeline is essential for maintainability and consistency. -->
    <!-- Ops & Risk Comment: Readiness: The dependency on the `protoc` compiler and the generated Python code needs to be managed in the CI/CD pipeline. Ensure the compiler version is consistent. -->

2.  **Python Application (Cloud Run):**
    *   **Configuration:** Reads configuration (Project ID, Dataset ID, Table ID, Source API endpoint/credentials) from environment variables. Sensitive credentials for the source API **must** be retrieved from Secret Manager at runtime, not stored directly in environment variables.
    <!-- Ops & Risk Comment: Security: Environment variables are used for config. Ensure sensitive config (like API keys for the source API, if not using Secret Manager) are NOT stored here. -->
    *   **Data Retrieval:** Fetches data from the internal API. Reliability and performance of this API are external dependencies. The application should implement appropriate timeouts and potentially retry logic for transient API issues.
    <!-- Ops & Risk Comment: Operations: Dependency: The reliability and performance of the internal API are critical external dependencies. How are API failures handled (e.g., retries, circuit breakers)? What is the expected API response time and how does it fit within Cloud Run request timeouts? -->
    <!-- Ops & Risk Comment: Security: How are credentials for the internal API stored and accessed by the Cloud Run service? Recommend using Secret Manager. -->
    *   **Data Transformation & Serialization:**
        *   Maps the retrieved API data (e.g., dictionaries) into instances of the generated Protobuf Python classes. Logic must handle `None` or missing optional fields appropriately, aligning with Protobuf's behavior.
        *   Uses `google.protobuf.json_format.ParseDict` with `ignore_unknown_fields=True` to provide some tolerance for new fields appearing in the source API data before the `.proto` definition is updated.
        *   Serializes each valid Protobuf message object into bytes using `.SerializeToString()`. Individual rows failing serialization should be logged (masking sensitive data) and potentially sent to a specific dead-letter location for analysis, without failing the entire batch.
    <!-- Peer Reviewer Comment: Using `ParseDict` with `ignore_unknown_fields=True` is a good practice for handling minor schema variations or additions in the source data before the `.proto` is updated. -->
    <!-- Peer Reviewer Comment: Good practice to log and skip individual rows that fail serialization, preventing a single bad record from failing the entire batch. Returning None is a clear way to signal this. -->
    <!-- Ops & Risk Comment: Operations: Error Handling: Logging the failed dictionary is useful for debugging but be cautious about logging sensitive data. Ensure sensitive fields are masked or excluded from logs. -->
    *   **Batching:** Collects multiple serialized Protobuf messages into a list. The optimal batch size needs tuning based on message size, Cloud Run memory limits, and Write API performance/quotas.
    <!-- Ops & Risk Comment: Operations: Batch size is a key tuning parameter affecting performance, memory usage, and cost. Needs monitoring and potential optimization. -->
    *   **Write API Interaction:**
        *   Instantiates `bigquery_storage_v1.BigQueryWriteClient` (a new client per invocation is suitable for Cloud Run).
        *   Defines the target table path and specifies the `_default` stream (e.g., `projects/{p}/datasets/{d}/tables/{t}/_default`).
        *   Creates a `types.AppendRowsRequest` template, including a `ProtoSchema` derived from the compiled Protobuf message descriptor (`YourDataMessage.DESCRIPTOR`).
        *   Initializes an `AppendRowsStream` using `writer.AppendRowsStream(write_client, request_template)`.
        *   Creates a `types.ProtoRows` object containing the batch of serialized Protobuf message bytes.
        *   Sends the batch using `append_rows_stream.send(request).result()`. The `_default` stream handles underlying stream management and provides at-least-once guarantees. Explicit offset management is not required.
        <!-- Peer Reviewer Comment: Using the `_default` stream simplifies stream management as intended. It supports concurrent writers from multiple Cloud Run instances (if scaled), providing at-least-once semantics. This means duplicate rows are possible, especially if retries occur. Ensure downstream processes can handle potential duplicates or implement deduplication if needed. -->
        <!-- Peer Reviewer Comment: Correct, explicit offset management is not needed for the `_default` stream. -->
    *   **Error Handling (Batch Level):**
        *   Implements `try...except` blocks around the `send().result()` call.
        *   Leverages client library retries for transient network/API issues.
        *   For persistent errors (e.g., schema mismatch, permission issues, quota exceeded after retries) or exceptions raised by `result()`:
            *   Logs the error details thoroughly.
            *   Sends the **entire failed batch** (serialized rows) to a designated dead-letter mechanism (e.g., a specific GCS bucket) along with error metadata.
            *   Raises an exception or returns an appropriate HTTP error code (e.g., 500) to signal failure to Cloud Scheduler.
    <!-- Peer Reviewer Comment: Basic error handling is mentioned, but this is a critical area for at-least-once guarantees. Need more detail on *how* persistent errors are identified and handled. What specific exceptions are caught? How are partial batch failures handled? A robust dead-lettering strategy is essential. -->
    <!-- Peer Reviewer Comment: This is the crucial point for batch-level error handling. If `send().result()` raises an exception, the *entire batch* failed (or its status is unknown). The current code just logs and re-raises. A robust implementation needs to capture the failed batch data and send it to the dead-letter queue here to ensure at-least-once delivery for the batch. -->
    <!-- Ops & Risk Comment: Operations: Robust error handling and a dead-letter queue are critical for reliability and data integrity. The RFC mentions this but needs specific details on implementation (format, location, alerting). -->
    <!-- Ops & Risk Comment: Monitoring: Need metrics on successful writes, failed writes, number of rows sent to dead-letter queue. -->
    *   **Stream Closure:** Uses a `finally` block to ensure the `AppendRowsStream` and `BigQueryWriteClient` are closed properly after each batch attempt, preventing resource leaks.
    <!-- Peer Reviewer Comment: Proper resource cleanup (closing client and stream) is important, especially in a serverless environment like Cloud Run. The sample code includes this in a `finally` block, which is good. -->
    <!-- Ops & Risk Comment: Operations: Resource Management: Ensure client and stream are properly closed to avoid resource leaks, especially important in a serverless environment with potentially many short-lived instances. -->
    *   **Logging:** Implements structured logging (e.g., JSON format) for key events: process start/end, batch send attempts, successful writes (with row counts), individual row serialization failures, batch write failures, dead-lettering events. Logs should be sent to Cloud Logging. Sensitive data in logs must be masked.
    <!-- Ops & Risk Comment: Operations: Ensure logs are structured (e.g., JSON) for easier parsing and analysis in Cloud Logging. Define logging levels. -->

3.  **Infrastructure:**
    *   **Cloud Run:** Hosts the containerized Python application. Configuration includes:
        *   Dedicated Service Account with minimal IAM permissions.
        *   Appropriate CPU/Memory allocation (to be tuned).
        *   Scaling settings (min/max instances, concurrency - to be tuned).
        *   Ingress control set to 'Internal'.
        *   Environment variables for non-sensitive config.
        *   Secret Manager integration for sensitive config (e.g., source API keys).
        *   Appropriate GCP labels for cost tracking.
    <!-- Peer Reviewer Comment: Cloud Run is a suitable choice. Consider potential cold starts if the service isn't frequently invoked, although a 10-minute schedule should mitigate this somewhat. Ensure adequate CPU allocation and memory limits are configured. -->
    <!-- Ops & Risk Comment: Operations: Cloud Run scaling configuration (min/max instances, concurrency) needs to be defined based on expected load and cost considerations. -->
    <!-- Ops & Risk Comment: Cost: Cloud Run costs are based on request time, CPU/memory allocation, and number of instances. Configuration choices here directly impact cost. -->
    *   **Cloud Scheduler:** Triggers the Cloud Run service's HTTP endpoint every 10 minutes using an authenticated request (OIDC). Job monitoring must be enabled.
    <!-- Ops & Risk Comment: Operations: Cloud Scheduler job monitoring is needed to ensure the trigger is firing reliably. -->
    *   **BigQuery:** The destination data warehouse table. The table schema must be kept synchronized with the `.proto` definition.
    <!-- Ops & Risk Comment: Operations: Dependency: The BigQuery table must exist and have a schema compatible with the Protobuf definition. Schema drift is a risk. -->
    *   **IAM:**
        *   Cloud Run Service Account: Requires `bigquery.tables.updateData` on the target table and `secretmanager.secretAccessor` for accessing secrets. Use a dedicated service account, not the default compute SA.
        *   Cloud Scheduler Service Account: Requires `run.invoker` role on the Cloud Run service.
    <!-- Peer Reviewer Comment: `bigquery.tables.updateData` is the correct minimal permission for writing data. -->
    <!-- Ops & Risk Comment: Security: Principle of Least Privilege: Confirm that `bigquery.tables.updateData` is the minimum required permission. Using a dedicated service account for this Cloud Run service is a good practice. -->
    *   **Secret Manager:** Stores credentials for the internal source API.
    *   **Cloud Storage (GCS):** Recommended destination for the dead-letter queue (failed batches and potentially individual failed rows). Requires appropriate bucket configuration and IAM permissions for the Cloud Run service account (`storage.objects.create`).
    *   **Cloud Monitoring:** Used for metrics, dashboards, and alerting (see Impact and Follow-ups).
    *   **Infrastructure as Code (IaC):** All infrastructure components (Cloud Run service, IAM, Scheduler, GCS bucket, etc.) should be managed via Terraform or similar IaC tools.
    <!-- Ops & Risk Comment: Readiness: Create Terraform or other IaC scripts for provisioning the Cloud Run service, IAM service account, Cloud Scheduler job, and configuring necessary permissions. -->

**Schema Evolution:**
Schema evolution is a **manual, coordinated process** involving potential downtime or data ingestion pauses if not handled carefully:
1.  **Plan:** Define the schema change (e.g., adding an optional field). Ensure backward compatibility if possible (e.g., only add optional fields).
2.  **Update BigQuery:** Apply the schema change to the target BigQuery table first.
3.  **Update `.proto`:** Modify the `.proto` file to match the new BigQuery schema.
4.  **Recompile & Test:** Recompile the `.proto` file using `protoc` (via CI/CD pipeline) and test the application code locally with the new generated classes.
5.  **Update Application Code:** Modify the Python application code if necessary (e.g., to populate the new field).
6.  **Deploy:** Redeploy the Cloud Run service with the updated application code and newly generated Protobuf classes.
Using `ignore_unknown_fields=True` during `ParseDict` helps the application tolerate *new* fields in the source API data *before* the `.proto` and application are updated, but the data for those fields won't be ingested until steps 3-6 are completed. Removing fields or changing types requires careful planning to avoid breaking the ingestion pipeline.
<!-- Peer Reviewer Comment: This manual process is a significant point of friction and potential for errors. It requires strict coordination between BQ schema changes, `.proto` updates, and code deployments. Consider documenting this process thoroughly in a runbook or exploring ways to automate parts of it in the future. How are backward/forward compatibility rules enforced (e.g., only adding optional fields)? -->
<!-- Ops & Risk Comment: Readiness: This manual process is a significant operational overhead and potential source of errors. A clear, documented process and potentially automation (e.g., schema registry integration, automated `.proto` generation) are needed for readiness. -->
<!-- Ops & Risk Comment: Compliance: If schema changes involve sensitive data, ensure the process aligns with data governance and compliance requirements (e.g., documenting changes, access controls). -->

**Diagram:**

```mermaid
graph TD
    subgraph "Build/Deploy Time"
        ProtoFile["your_data.proto"] -- "1. Define Schema" --> Protoc["protoc Compiler (in CI/CD)"];
        Protoc -- "2. Generates" --> PyClasses["your_data_pb2.py"];
        PyClasses -- "3. Included in" --> Container["Container Image"];
    end

    subgraph "Runtime (Every 10 Mins)"
        CS[Cloud Scheduler] -- "4. Triggers (OIDC Auth)" --> CR["Python App (Cloud Run)"];
        CR -- "5. Reads Secrets" --> SM[Secret Manager];
        CR -- "6. Fetches data (using Secrets)" --> IntAPI["Internal API"];
        IntAPI -- "Provides data" --> CR;
        subgraph "App Processing"
            direction LR
            CR -- "7. Maps data using PyClasses" --> PData["Protobuf Objects"];
            PData -- "8. Serializes (.SerializeToString)" --> SerData["Serialized Protobuf Batch"];
        end
        CR -- "9. Sends Batch via BQ Write Client Lib" --> BQAPI["BigQuery Write API (_default stream)"];
        BQAPI -- "10. Writes data" --> BQTable["BigQuery Table"];
        CR -- "On Persistent Batch Error" -.-> DLQ["Dead Letter Queue (GCS Bucket)"];
        CR -- "On Individual Row Error" -.-> DLQ;
        CR -- "Logs Events" --> Log[Cloud Logging];
    end

    Container -- "Deployed To" --> CR;
    SM -- "Stores Credentials for" --> IntAPI;

    style DLQ fill:#f9f,stroke:#333,stroke-width:2px
```
<!-- Editor Note: Diagram updated to reflect build-time steps and runtime flow, including Secret Manager and Dead Letter Queue, based on reviewer feedback. -->
<!-- Peer Reviewer Comment: Diagram Accuracy: The diagram accurately reflects the main components and data flow described in the text. It clearly shows the scheduled trigger, the Cloud Run app, the internal API interaction, the processing steps (mapping, serialization, batching implied), the Write API interaction via the default stream, and the destination table. It also includes the error handling path. Syntax appears valid. -->
<!-- Peer Reviewer Comment: Diagram Suggestion: Consider adding the Protobuf definition file (.proto) and the `protoc` compilation step as external elements influencing the "App Processing" subgraph, perhaps as a build-time dependency, to make the schema management aspect more visible in the diagram. -->

**Illustrative Code Sample (Conceptual - Requires Refinement):**

```python
# sample_data.proto
syntax = "proto2";
package your_package; // Added package declaration

message YourDataMessage {
  required string id = 1;
  optional string name = 2;
  optional int64 timestamp = 3;
  // Add other fields corresponding to your BigQuery table schema
}
```

```bash
# Compile the .proto file (part of build/deploy process in CI/CD)
protoc --python_out=. your_data.proto
```

```python
# main.py (Illustrative Python code for Cloud Run - Needs error handling, logging, secret mgmt etc.)
import json
import time
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types
from google.cloud.bigquery_storage_v1 import writer
from google.protobuf import descriptor_pb2
from google.protobuf.json_format import ParseDict, ParseError
from google.api_core.exceptions import GoogleAPICallError
import logging
import os
import sys # For exit codes

# Import the generated Protobuf classes (adjust import path as needed)
import your_data_pb2

# Configure structured logging (Example - adapt as needed)
# In Cloud Run, logs printed to stdout/stderr are automatically collected
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "message": "%(message)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logger = logging.getLogger(__name__)

# Get config from environment variables (non-sensitive)
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
DATASET_ID = os.environ.get("BQ_DATASET_ID")
TABLE_ID = os.environ.get("BQ_TABLE_ID")
# DEAD_LETTER_BUCKET = os.environ.get("DEAD_LETTER_BUCKET") # Example for DLQ config

# TODO: Implement function to get source API credentials from Secret Manager

if not all([PROJECT_ID, DATASET_ID, TABLE_ID]):
    logger.error('{"message": "Missing required environment variables: GCP_PROJECT_ID, BQ_DATASET_ID, BQ_TABLE_ID"}')
    sys.exit(1) # Exit with error code

# TODO: Implement function to write failed data (row or batch) to GCS Dead Letter Queue

def create_protobuf_row(data_dict):
    """Creates a serialized Protobuf message from a dictionary. Returns None on failure."""
    row = your_data_pb2.YourDataMessage()
    try:
        ParseDict(data_dict, row, ignore_unknown_fields=True)
        return row.SerializeToString()
    except (ParseError, TypeError, ValueError) as e:
        # Log error, masking sensitive data if necessary
        log_payload = {"message": "Failed to parse dictionary to protobuf", "error": str(e), "data_keys": list(data_dict.keys())} # Avoid logging full data
        logger.error(json.dumps(log_payload))
        # TODO: Optionally send problematic data_dict to a specific dead-letter location for rows
        return None
    <!-- Peer Reviewer Comment: Good practice to log and skip individual rows that fail serialization, preventing a single bad record from failing the entire batch. Returning None is a clear way to signal this. -->

def write_to_bigquery(data_list):
    """Writes a list of dictionaries to BigQuery using the Storage Write API default stream."""
    write_client = None
    append_rows_stream = None
    serialized_rows_batch = []
    valid_rows_count = 0
    invalid_rows_count = 0

    # Serialize rows first, handling individual errors
    for data_dict in data_list:
        serialized_row = create_protobuf_row(data_dict)
        if serialized_row is not None:
            serialized_rows_batch.append(serialized_row)
            valid_rows_count += 1
        else:
            invalid_rows_count += 1

    if invalid_rows_count > 0:
        logger.warning(f'{{"message": "{invalid_rows_count} rows failed serialization and were skipped."}}')
        # Ops & Risk Comment: Monitoring: Alerting: Set up alerts for a high rate of invalid rows.

    if not serialized_rows_batch:
        logger.info('{"message": "No valid rows to write after serialization."}')
        return # Nothing to send

    try:
        write_client = bigquery_storage_v1.BigQueryWriteClient()
        parent = write_client.table_path(PROJECT_ID, DATASET_ID, TABLE_ID)
        stream_name = f'{parent}/_default'

        request_template = types.AppendRowsRequest()
        request_template.write_stream = stream_name

        proto_schema = types.ProtoSchema()
        proto_descriptor = descriptor_pb2.DescriptorProto()
        your_data_pb2.YourDataMessage.DESCRIPTOR.CopyToProto(proto_descriptor)
        proto_schema.proto_descriptor = proto_descriptor
        proto_data = types.AppendRowsRequest.ProtoData()
        proto_data.writer_schema = proto_schema
        request_template.proto_rows = proto_data

        append_rows_stream = writer.AppendRowsStream(write_client, request_template)

        proto_rows = types.ProtoRows()
        proto_rows.serialized_rows.extend(serialized_rows_batch)

        request = types.AppendRowsRequest()
        request.proto_rows = proto_data # Schema included here
        request.proto_rows.rows = proto_rows # Actual data rows

        log_payload = {"message": "Sending batch to BigQuery", "row_count": valid_rows_count, "stream": stream_name}
        logger.info(json.dumps(log_payload))
        # Ops & Risk Comment: Monitoring: Log successful batch sends with row count.

        # Send the request and block until completion/failure
        response_future = append_rows_stream.send(request)
        # result() will raise GoogleAPICallError on API error after client library retries
        response = response_future.result()

        # Check response status if needed, though errors usually raise exceptions
        if response and not response.error.message: # Basic check
             log_payload = {"message": "Successfully wrote batch to BigQuery", "row_count": valid_rows_count, "response_details": str(response)} # Be careful logging full response
             logger.info(json.dumps(log_payload))
             # Ops & Risk Comment: Monitoring: Log successful write API responses.
        else:
             # This case might be rare if exceptions are raised properly
             log_payload = {"message": "BigQuery write response indicated an issue", "row_count": valid_rows_count, "response_error": str(response.error)}
             logger.error(json.dumps(log_payload))
             # Treat as failure for dead-lettering
             raise GoogleAPICallError(f"Write response error: {response.error.message}")


    except GoogleAPICallError as e:
        log_payload = {"message": "Error writing batch to BigQuery", "error": str(e), "row_count": valid_rows_count}
        logger.error(json.dumps(log_payload))
        # Ops & Risk Comment: Operations: Error Handling: Define specific error handling for different BigQuery Write API errors (e.g., schema mismatch, quota errors). Application-level retries with exponential backoff are recommended for transient errors.
        # Ops & Risk Comment: Monitoring: Alerting: Set up alerts for BigQuery Write API errors.
        # Send the *entire failed batch* (serialized_rows_batch) to the dead-letter queue
        # TODO: Implement dead_letter_batch(serialized_rows_batch, error=e)
        raise # Re-raise to signal failure to the caller (Cloud Run / Scheduler)

    except Exception as e: # Catch other potential exceptions
        log_payload = {"message": "Unexpected error during BigQuery write operation", "error": str(e), "row_count": valid_rows_count}
        logger.error(json.dumps(log_payload))
        # Also dead-letter the batch in case of unexpected errors during the write phase
        # TODO: Implement dead_letter_batch(serialized_rows_batch, error=e)
        raise

    finally:
        # Ensure resources are cleaned up
        if append_rows_stream:
            append_rows_stream.close()
        if write_client:
            write_client.close()

# Example function called by Cloud Run HTTP handler / Cloud Scheduler trigger
# Needs to be adapted for a web framework like Flask/FastAPI if using HTTP trigger
def process_api_data_and_write():
    """Fetches data from API and writes to BigQuery."""
    logger.info('{"message": "Starting data ingestion process..."}')
    # TODO: 1. Get API credentials from Secret Manager
    # TODO: 2. Fetch data from the internal API (implement retries/timeouts)
    # api_data = fetch_data_from_internal_api()
    # Simulate fetching data:
    sample_api_data = [
        {"id": "201", "name": "Charlie", "timestamp": int(time.time())},
        {"id": "202", "name": "David", "timestamp": int(time.time())},
        {"id": "203", "timestamp": int(time.time())}, # Missing 'name' (handled by optional field)
        {"invalid_field": "some_value"} # This dict won't parse correctly
    ]
    api_data = sample_api_data # Use sample data for illustration

    if not api_data:
        logger.info('{"message": "No data received from API."}')
        # Ops & Risk Comment: Operations: Dependency: Handle cases where the source API returns no data or an empty response. Log this appropriately.
        return # Successful exit, nothing to process

    # 3. Write the data to BigQuery
    try:
        write_to_bigquery(api_data)
        logger.info('{"message": "Data ingestion process completed successfully."}')
        # Ops & Risk Comment: Monitoring: Log successful completion of the entire process run.
        # If HTTP triggered, return 200 OK here
    except Exception as e:
        # Error already logged in write_to_bigquery or create_protobuf_row
        logger.error(f'{{"message": "Data ingestion process failed.", "error": "{str(e)}"}}')
        # Ops & Risk Comment: Operations: Error Handling: If triggered by Cloud Scheduler via HTTP, returning a non-200 status code will signal failure to Cloud Scheduler, which can be configured for retries.
        # Ops & Risk Comment: Monitoring: Alerting: Set up alerts for overall process failures.
        # If HTTP triggered, return 500 Internal Server Error here
        sys.exit(1) # Exit with error code for non-HTTP triggers

# Entry point (adapt for Cloud Run service framework like Flask/FastAPI)
if __name__ == "__main__":
    # This block is for local testing/illustration; Cloud Run invokes via HTTP typically
    process_api_data_and_write()

```
<!-- Peer Reviewer Comment: Overall, the sample code provides a good illustration of the core logic. Key areas for refinement in the actual implementation are the detailed error handling (especially for batch failures and dead-lettering) and integrating the Protobuf compilation into the build process. -->
<!-- Editor Note: Code sample updated with basic structured logging, error handling placeholders, package declaration for proto, and notes on required refinements (Secret Manager, DLQ implementation, web framework integration). This remains illustrative. -->

## 🌈 Alternatives considered
---
The research focused on finding a solution that met all the strict requirements (Python, Write API, Protobuf, No Pub/Sub, Serverless GCP, Batch, At-least-once). Given these constraints, the primary viable approach identified was using the Python client library for the BigQuery Storage Write API with Protobuf and the default stream. Other conceptual alternatives were implicitly or explicitly ruled out:

*   **BigQuery Write API with JSON (via Python):** While the Write API supports JSON, the requirement was specifically to use Protobuf. JSON might be simpler for schema evolution but less efficient for serialization/transfer.
*   **Pub/Sub -> BigQuery Subscription:** Explicitly disallowed by requirements. This would offer a more managed, streaming approach but violates constraints.
*   **Legacy BigQuery Streaming API (`tabledata.insertAll`):** Mentioned in preliminary research as something to avoid in favor of the newer Write API due to lower throughput limits, higher cost, and lack of Protobuf support.
*   **BigQuery Load Jobs:** Not suitable for the 10-minute batch frequency and closer-to-real-time nature implied by using the Write API. Load jobs are better suited for larger, less frequent batches.

Therefore, the comparison focuses on the details of the single viable option identified.
<!-- Peer Reviewer Comment: The constraints are indeed strict and effectively narrow down the options. The rationale for excluding the listed alternatives is sound based on these constraints and general best practices (avoiding legacy API, load jobs for frequent small batches). -->

|          | Option 1 (Pure Python with BQ Storage Write API Default Stream and Protobuf) |
| -------- | -------------------------------------------------------------------------- |
| Overview | Python app on Cloud Run uses `google-cloud-bigquery-storage` library to serialize data to Protobuf and append batches to the BQ table's `_default` stream every 10 minutes. |
| Links    | - [Write API Intro](https://cloud.google.com/bigquery/docs/write-api) <br/> - [Python Client Docs](https://cloud.google.com/python/docs/reference/bigquerystorage/latest) <br/> - [Protobuf Dev](https://protobuf.dev/) <br/> - [Xebia Guide](https://xebia.com/blog/bigquery-storage-write-api-a-hands-on-guide-with-python-and-protobuf/) |
| Pros     | - Meets all requirements (Python, Write API, Protobuf, Batch, `_default` stream, At-least-once, No Pub/Sub, GCP Serverless). <br/> - Uses preferred `_default` stream for simplicity (no manual stream management). <br/> - Cost-effective & efficient ingestion (gRPC, binary format). <br/> - Leverages scalable, serverless Cloud Run. |
| Cons     | - **Schema Evolution Complexity:** Requires manual, coordinated updates to `.proto` file, BQ table, `protoc` compilation (in CI/CD), and application code redeployment. High potential for errors if process isn't robust. <br/> - **Operational Overhead:** Requires detailed monitoring, alerting, dead-letter queue management, and runbooks. <br/> - **At-least-once Semantics:** Potential for duplicate rows requires downstream deduplication or idempotent processing. <br/> - **Lower-level Client:** Python client requires explicit serialization and more detailed error handling compared to some higher-level abstractions (like Pub/Sub subscriptions). |
| Other    | - Runs on Cloud Run. <br/> - Uses BigQuery Storage Write API. <br/> - Requires specific IAM permissions (`bigquery.tables.updateData`, `secretmanager.secretAccessor`, `run.invoker`, `storage.objects.create`). <br/> - Dependencies: Internal API, Cloud Scheduler, Secret Manager, GCS (for DLQ). |

**Comparison Summary & Rationale:**
Option 1 is the only approach that satisfies all the mandatory requirements and constraints outlined in the initial problem definition. Specifically, it uses Python, the BigQuery Write API, Protobuf, avoids Pub/Sub, runs serverlessly on GCP (Cloud Run), supports batching, and provides the required at-least-once semantics via the `_default` stream. The preference for simplicity is addressed by using the `_default` stream, which abstracts away manual stream management compared to explicitly managed streams. While the manual handling of Protobuf schemas and the need for robust operational practices (error handling, monitoring, schema evolution process) add significant complexity compared to hypothetical alternatives, this complexity is inherent in meeting the specific, strict requirements set forth. Therefore, Option 1 is recommended as the direct and compliant solution, acknowledging the associated operational responsibilities.
<!-- Peer Reviewer Comment: The comparison table and summary accurately reflect the trade-offs given the strict constraints. The rationale for choosing Option 1 is technically sound and directly tied to meeting the mandatory requirements. -->

## 💥 Impact
---
*   **Systems:**
    *   Introduces a new Cloud Run service, Cloud Scheduler job, dedicated IAM service accounts, potentially a GCS bucket for dead-lettering, and Secret Manager secrets.
    *   Relies heavily on the BigQuery Storage Write API endpoint availability and quotas.
    *   Depends critically on the availability, performance, and contract stability of the internal source API.
    *   Requires integration with existing monitoring/alerting systems (Cloud Monitoring).
    *   Requires CI/CD pipeline modifications to include `protoc` compilation.
    <!-- Ops & Risk Comment: Operations: Document the dependencies clearly (Source API, Cloud Scheduler, BigQuery table). Define expected uptime and failure modes for each. -->
*   **Teams/Workflow:**
    *   **Development:** Requires developers to learn and manage Protobuf schema definitions (`.proto` files), the `protoc` compilation process, and the nuances of the `google-cloud-bigquery-storage` client library. Requires careful handling of schema evolution.
    <!-- Readiness: Plan for training or knowledge transfer sessions on Protobuf for the team. -->
    *   **Operations/SRE:** Requires defining and implementing monitoring dashboards, alerts for key metrics (ingestion rate, errors, latency, DLQ size), and runbooks for troubleshooting common issues (e.g., schema mismatch errors, persistent API failures, DLQ processing). Requires managing the schema evolution process.
    <!-- Operations: Define specific monitoring dashboards and alerts in Cloud Monitoring. Key metrics include Cloud Run request count, latency, error rate, instance count, CPU/Memory utilization, and BigQuery Write API metrics (rows inserted, errors, latency). -->
    <!-- Operations: On-Call & Support: Develop runbooks for common issues (e.g., ingestion failures, high error rates, dead-letter queue filling up). -->
    *   **Schema Management:** Schema evolution becomes a formal, multi-step process requiring strict coordination between BigQuery schema changes, `.proto` file updates, CI/CD pipeline execution, and application deployment. This process must be documented and rigorously followed.
    <!-- Readiness: This process needs to be clearly defined, documented, and potentially automated to minimize operational risk during schema changes. Consider versioning strategy for `.proto` files and corresponding application code. -->
*   **Cost:**
    *   **Cloud Run:** Costs based on vCPU/memory allocation, request execution time, and number of requests (invoked every 10 mins). Tiered pricing applies. Configure appropriate resources to balance performance and cost.
    *   **BigQuery Storage Write API:** Costs based on data volume ingested ($0.025 per GiB as of Q3 2023, 1KB minimum per row). Using the `_default` stream avoids explicit stream commit costs.
    *   **Cloud Scheduler:** Minimal cost per job.
    *   **Cloud Storage:** Costs for storing dead-lettered data (standard storage rates apply).
    *   **Secret Manager:** Costs based on secret versions and access operations.
    *   **Cloud Logging/Monitoring:** Costs depend on volume of logs/metrics ingested and retention periods (generous free tier usually sufficient unless logging is excessive).
    *   **Recommendation:** Implement GCP labels on all resources (Cloud Run, BQ Table, GCS Bucket) for accurate cost allocation and tracking. Estimate costs based on expected data volume and Cloud Run configuration.
    <!-- Cost: Cloud Run pricing is based on CPU/Memory allocation and request time ($0.000024/GiB-sec, $0.000024/vCPU-sec in Tier 1, plus request cost). BigQuery Write API pricing is $0.025 per GiB ingested (with a 1KB minimum per row). The cost estimate should break down these components based on projected data volume and Cloud Run resource usage. -->
    <!-- Cost: Add GCP labels (e.g., `service: [service-name]`, `data-domain: [domain]`) to the Cloud Run service and potentially the BigQuery table for cost allocation and tracking. -->
    <!-- Peer Reviewer Comment: Cost assessment seems reasonable. Monitoring costs during initial rollout is advisable. -->
*   **Performance:**
    *   Write API offers high throughput via gRPC and efficient binary Protobuf format.
    *   Performance depends on batch size, message complexity, network latency, Cloud Run instance configuration (CPU/memory), and source API responsiveness.
    *   The 10-minute batch interval is well within capabilities, but tuning (batch size, Cloud Run resources) is needed to optimize latency and resource usage.
    *   Potential for Cloud Run cold starts exists, though the 10-min schedule should keep instances warm most of the time. Consider configuring minimum instances if consistent low latency is critical.
    <!-- Peer Reviewer Comment: Performance characteristics are correctly identified. Batch size tuning will be key for optimizing performance and cost. -->
    <!-- Operations: Performance testing (e.g., load testing) should be conducted to validate performance assumptions and determine optimal batch size and Cloud Run resource allocation. -->
*   **Security:**
    *   **IAM:** Requires careful management of dedicated service accounts (Cloud Run, Cloud Scheduler) with least-privilege permissions (see Design section). Avoid default service accounts.
    <!-- Security: Ensure a dedicated, minimal-privilege service account is created for this Cloud Run service. Avoid using the default compute service account. The `bigquery.tables.updateData` permission is appropriate for writing. -->
    *   **Secrets:** Source API credentials **must** be stored in Secret Manager, accessed by the Cloud Run SA at runtime.
    <!-- Security: How are credentials for the *source* internal API handled? Recommend using Secret Manager and granting the Cloud Run service account permission to access the specific secret. -->
    *   **Network:** Cloud Run ingress must be restricted ('Internal'). Cloud Scheduler must use authenticated invocation (OIDC). Network policies might be needed depending on VPC-SC setup.
    <!-- Security: Ensure Cloud Run ingress is set to 'Internal' or 'Internal and Cloud Load Balancing' if applicable, and invocation requires authentication (e.g., IAM roles). Cloud Scheduler should use OIDC authentication to trigger the service. -->
    *   **Auditing:** Ensure Cloud Audit Logs are enabled for Cloud Run, BigQuery, IAM, Secret Manager, and Cloud Storage to track access and modifications.
    <!-- Security: Audit Logging: Ensure Cloud Audit Logs are enabled for Cloud Run and BigQuery to track API calls and access. -->
    *   **Data:** Ensure compliance with data handling policies, especially if sensitive data is involved (logging, dead-lettering).
    <!-- Peer Reviewer Comment: Standard security considerations apply. Ensure the service account has only the necessary permissions. -->
*   **Reliability:**
    *   At-least-once semantics provided by the `_default` stream meet the goal but necessitate downstream idempotency or deduplication.
    *   Overall reliability depends heavily on:
        *   Robust application-level error handling (retries for transient errors).
        *   Effective dead-lettering mechanism for persistent errors (capturing failed data).
        *   Reliability of the source internal API.
        *   Proper monitoring and alerting to detect and respond to failures quickly.
        *   Well-defined schema evolution process to prevent deployment-related breakages.
    <!-- Peer Reviewer Comment: Re-iterates the importance of robust application-level error handling for reliability, which is critical given the at-least-once guarantee. -->
    <!-- Operations: Define the retry strategy (client library defaults + application-level) and the dead-lettering mechanism (destination, format, retention). -->

## 💬 Discussion
---
*   **Schema Evolution Rigor:** The manual process is the biggest risk. How can we make it safer?
    *   Mandate strict backward-compatibility rules (e.g., only add optional fields, never remove/rename required fields)?
    *   Implement pre-deployment checks (e.g., comparing `.proto` against BQ schema)?
    *   Explore schema registry tools (e.g., Confluent Schema Registry, Apicurio) even if just for tracking/validation, though full integration might be complex?
    *   What is the rollback strategy if a schema change deployment fails?
    <!-- Peer Reviewer Comment: Excellent points for discussion. This is the main technical risk/complexity area. A clear, documented process is needed. -->
    <!-- Readiness: This is a critical readiness gap. A formal, documented process is needed. Consider tools or automation to help manage `.proto` files and schema synchronization. -->
*   **Dead-Letter Queue (DLQ) Implementation:**
    *   Destination: GCS bucket is standard. Define the exact path and object naming convention.
    *   Format: Store the serialized Protobuf batch (or individual row) along with metadata (timestamp, error message, service name, original source info if possible). JSON wrapper?
    *   Processing: How will data in the DLQ be processed/replayed? Manual intervention? Automated retry mechanism? Define the process and retention policy for DLQ data.
    *   Alerting: Alert when DLQ size exceeds a threshold or receives data frequently.
    <!-- Peer Reviewer Comment: Crucial details for implementation. Defining the dead-lettering strategy and alerting is paramount for operational reliability. -->
    <!-- Operations: These details are essential for operationalizing the solution. Define error types for dead-lettering, specify the dead-letter destination and data format (e.g., original payload + error metadata), and create specific alerts in Cloud Monitoring. -->
*   **Error Handling Specificity:** Which specific `GoogleAPICallError` subtypes (or status codes within them) indicate non-retryable issues (e.g., `INVALID_ARGUMENT` for schema mismatch) vs. potentially retryable ones (e.g., `UNAVAILABLE`, `INTERNAL`)? The application logic needs to differentiate these for appropriate action (retry vs. dead-letter).
*   **Batch Size & Resource Tuning:** What's the starting point for batch size (e.g., 1000 rows, 1MB)? How will tuning be performed (load testing, monitoring production)? What are the initial Cloud Run CPU/memory settings?
    <!-- Peer Reviewer Comment: Important optimization point. Start with a reasonable size and monitor/tune. -->
    <!-- Operations: Plan for performance testing to determine the optimal batch size. Monitor Cloud Run memory/CPU usage and BigQuery Write API performance metrics during testing. -->
*   **Monitoring & Alerting Details:** Define specific SLOs/SLIs (e.g., ingestion latency, error rate). List the exact metrics to monitor in Cloud Monitoring (Cloud Run invocation count/latency/errors, BQ Write API AppendRows latency/errors/throttling, DLQ object count) and the corresponding alert thresholds and notification channels.
    <!-- Peer Reviewer Comment: Essential for operating the solution. Define key metrics and integrate with existing monitoring systems. -->
    <!-- Operations: Create a monitoring dashboard in Cloud Monitoring. Define specific alerting policies with clear thresholds and notification channels for key metrics (e.g., Cloud Run error rate > X%, BigQuery Write API append errors > Y/min, dead-letter count > Z). -->
*   **Handling `None`/Missing Optional Fields:** Confirm the exact behavior of `ParseDict` and Protobuf serialization for missing optional fields vs. fields present with `None` values in the source data. Ensure this aligns with BigQuery's expectations for `NULL` values. Document the chosen mapping logic.
    <!-- Peer Reviewer Comment: Good point regarding data mapping specifics and aligning with Protobuf behavior. -->
    <!-- Operations: Document the specific mapping logic and how `None` or missing values are translated to Protobuf defaults or explicitly handled. This is important for data quality. -->
*   **CI/CD Pipeline Details:** Specify the exact stage and commands for `protoc` compilation within the pipeline. How are the generated Python files packaged into the container?
    <!-- Peer Reviewer Comment: Practical implementation detail that needs to be planned. -->
    <!-- Readiness: Define the CI/CD pipeline steps, including where and how `protoc` is run and how the generated files are included in the container image. -->
*   **Dependency Management (Source API):** What are the known failure modes and rate limits of the internal API? How will changes to the source API contract be communicated and managed?
*   **Duplicate Handling:** Reiterate that downstream consumers of the BigQuery table must be prepared to handle potential duplicate rows due to the at-least-once guarantee. Is a downstream deduplication step needed?

## 🤝 Final decision
---
The final decision is to adopt **Option 1: Pure Python with BigQuery Storage Write API Default Stream and Protobuf**, implemented on Cloud Run and triggered by Cloud Scheduler.

This approach directly fulfills all stated technical requirements and constraints. While it introduces significant operational responsibilities, particularly around the manual schema evolution process and the need for robust error handling, monitoring, and alerting, it is the most direct and compliant solution identified. The team accepts the operational overhead associated with managing Protobuf schemas and the at-least-once delivery model in exchange for meeting the specific technical constraints (Python, Protobuf, No Pub/Sub, Write API). Implementation must prioritize the operational aspects detailed in the Follow-ups section.
<!-- Peer Reviewer Comment: The decision is well-justified based on the analysis and constraints. -->

## ☝️ Follow-ups
---
*   **Schema Evolution Process:** **(Critical)** Define, document, and train the team on the detailed, step-by-step process for schema evolution, including version control for `.proto` files, backward compatibility guidelines, CI/CD integration, BQ schema update procedures, deployment coordination, testing, and rollback strategy.
    <!-- Readiness: This is a critical follow-up. The process needs to be robust and clearly communicated to the team. -->
*   **Error Handling & DLQ Implementation:** Implement robust error handling in the Cloud Run application, differentiating retryable vs. non-retryable errors. Implement the dead-letter mechanism (GCS bucket destination, data format including error metadata, IAM permissions). Document the DLQ processing/replay strategy and retention policy.
    <!-- Operations: Essential for reliability. Specify the dead-letter destination, format, and retention policy. -->
*   **Monitoring & Alerting Setup:** Create Cloud Monitoring dashboards and configure specific alerts for: Cloud Run execution errors, high request latency, BigQuery Write API errors (AppendRows), high serialization error rate, DLQ write failures, DLQ size/growth rate, and Cloud Scheduler job failures. Define thresholds and notification channels.
    <!-- Operations: Define specific metrics, dashboards, and alerting policies in Cloud Monitoring. -->
*   **CI/CD Pipeline Integration:** Integrate the `protoc` compilation step into the project's CI/CD pipeline, ensuring generated Python files are correctly packaged. Pin the `protoc` version.
    <!-- Readiness: This is a key CI/CD task. -->
*   **IaC Implementation:** Develop Terraform (or chosen IaC tool) scripts to provision and manage all required GCP resources (Cloud Run service, IAM roles/service accounts, Cloud Scheduler job, Secret Manager secrets, GCS DLQ bucket).
    <!-- Ops & Risk Comment: Readiness: Create Terraform or other IaC scripts for provisioning the Cloud Run service, IAM service account, Cloud Scheduler job, and configuring necessary permissions. -->
*   **Security Implementation:**
    *   Create dedicated service accounts with least-privilege IAM roles.
    *   Implement Secret Manager for source API credentials.
    *   Configure Cloud Run for internal ingress and authenticated invocation.
    *   Configure Cloud Scheduler for OIDC authenticated invocation.
    <!-- Ops & Risk Comment: Security: Implement secret management for source API credentials using Google Secret Manager. -->
*   **Performance Tuning:** Determine an initial batch size and Cloud Run resource allocation. Plan and execute performance/load testing to validate assumptions and tune these parameters based on observed metrics (latency, throughput, resource utilization, cost).
    <!-- Operations: Include performance testing in the implementation plan. -->
*   **Runbook Development:** Create operational runbooks/troubleshooting guides covering common failure scenarios (e.g., schema mismatch, API unavailability, permission errors, DLQ analysis).
    <!-- Ops & Risk Comment: Readiness: Develop runbooks and troubleshooting guides for common operational issues. -->
*   **Code Development:** Develop the Cloud Run service based on the design and illustrative code, incorporating robust logging, error handling, DLQ logic, and Secret Manager integration. Finalize the mapping logic for API data to Protobuf, documenting handling of optional/missing fields.
    <!-- Readiness: Core development task. -->
    <!-- Operations: Document this logic for maintainability and data quality assurance. -->
*   **Cost Tracking:** Implement GCP resource labels for cost allocation. Refine cost estimates based on testing and projected volume.
    <!-- Ops & Risk Comment: Cost: Implement cost tracking using GCP labels. Refine cost estimate based on initial testing and projected data volume. -->
*   **Compliance Review:** If handling sensitive data, conduct a compliance review of the design, particularly data handling in logs and the DLQ, to ensure alignment with requirements.
    <!-- Ops & Risk Comment: Compliance: If handling sensitive data, document how the solution meets relevant compliance requirements (e.g., data handling, retention). -->

## 🔗 Related
---
*   [Introduction to the BigQuery Storage Write API - Google Cloud](https://cloud.google.com/bigquery/docs/write-api)
*   [Stream data using the Storage Write API | BigQuery - Google Cloud](https://cloud.google.com/bigquery/docs/write-api-streaming) (_Note: While we use the API, our pattern is batch append via default stream, not continuous streaming_)
*   [BigQuery Storage Write API best practices - Google Cloud](https://cloud.google.com/bigquery/docs/write-api-best-practices)
*   [BigQuery Storage Write API: A Hands-On Guide with Python and Protobuf - Xebia](https://xebia.com/blog/bigquery-storage-write-api-a-hands-on-guide-with-python-and-protobuf/)
*   [Protocol Buffers - Google's data interchange format](https://protobuf.dev/)
*   [google-cloud-bigquery-storage Python Client Library Documentation](https://cloud.google.com/python/docs/reference/bigquerystorage/latest)
*   [Cloud Run Documentation](https://cloud.google.com/run/docs)
*   [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
*   [Google Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
*   [Language Guide (proto2)](https://protobuf.dev/programming-guides/proto2/)
*   [Previous RFC deciding on Write API usage] - *Placeholder for link to previous internal RFC*
<!-- Peer Reviewer Comment: Relevant links are provided. -->

## 📝 Reviewer Feedback Summary
---
This section summarizes key points raised during the technical and operational/risk reviews, which have been integrated into the document above.

*   **Schema Evolution:** Both reviews highlighted the manual Protobuf schema evolution process as a major complexity and risk factor. A robust, documented process, CI/CD integration for `protoc`, and careful coordination are critical (See Follow-ups).
*   **Error Handling & Dead-Lettering:** Strong emphasis from both reviews on the need for detailed, robust error handling, particularly distinguishing retryable vs. non-retryable errors and implementing a well-defined dead-letter queue (DLQ) for persistent batch failures and potentially individual row serialization failures (See Follow-ups, Design).
*   **Operational Readiness:** Ops/Risk review stressed the need for comprehensive monitoring, alerting, structured logging, IaC for infrastructure, runbooks, and clear documentation for operational hand-off (See Impact, Discussion, Follow-ups).
*   **Security:** Ops/Risk review emphasized security best practices: least-privilege IAM using dedicated service accounts, secure secret management (Secret Manager), restricted network ingress for Cloud Run, and authenticated invocation (See Design, Impact, Follow-ups).
*   **At-least-once Semantics:** Both reviews noted the implication of potential duplicates due to the `_default` stream's at-least-once guarantee, requiring downstream consideration (See Goals, Impact, Discussion).
*   **Dependencies:** The reliance on the external source API's reliability and contract stability was noted as an external risk factor (See Context, Impact).
*   **Code & Diagram:** Technical review provided feedback on the code sample structure (error handling, resource closure) and suggested improvements for diagram clarity, which have been incorporated.
*   **Cost & Performance:** Tuning batch size and Cloud Run resources is important for optimizing cost and performance. Cost tracking via labels is recommended (See Impact, Discussion, Follow-ups).
