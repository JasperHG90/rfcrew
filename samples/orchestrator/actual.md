# [Infrastructure] Choose an orchestrator

|                 |                                                                                                                                                              |
| :-------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Author**      | @Ginn, Jasper                                                                                                                                                |
| **Reviewers**   |                                                                                                                                                              |
| **Ticket**      |                                                                                                                                                              |
| **Date**        | 27/02/2025                                                                                                                                                   |
| **Final decision** | Composer is the obvious choice. This needs to be hashed out a little more in terms of pricing and (domain) architecture. This RFC will be revisited when approved by the architecture board. |
| **Version**     | v0.0.1                                                                                                                                                       |

## Overview 🔗

The Sligro EDP does not have an orchestrator. This is causing issues with overview, failure detection, change tracking, and adaptability. Moreover, we need to anticipate future workflows in which orchestration will be indispensable, such as managing multiple ODS deployments.

The requirements for a new orchestrator include easy accessibility, quick familiarization, testing without deployment, comprehensive pipeline overview, clear failure display, source control updates, and integration with other tools.

Two options are considered: Airflow (Composer or Astronomer), Dagster. Pros and cons are listed for each option, along with associated costs.

## Table of contents 🔗

*   Overview
*   Table of contents
*   Changelog
*   Goals and Requirements
*   Audience
*   Context and Scope
*   Options
*   Costs
*   Current Use
*   Future Use
*   Recommendation
*   Impact
*   Discussion
*   Follow-ups
*   Related

## Changelog 🔗

| Version | Changes       |
| :------ | :------------ |
| v0.1    | First version |

## Goals and Requirements 🔗

From users:

*   Tool should be easily accessible
*   Easy to quickly get familiar with using and configuring the tool
*   Pipelines should be easy to test without requiring a deployment
*   Tool should provide a comprehensive overview of the various pipelines run for ingestion and transformation of data
*   Failures should clearly displayed and allow for some basic diagnostics of the underlying issue
*   Updates to the tool should be possible via source control such that there is versioning and a change review process

## Audience 🔗

This change primarily affects Data Engineers as they need to refactor/migrate existing workflows

## Context and Scope 🔗

The current orchestration setup for the Sligro EDP is split across different tools. Most data products are triggered from CRON schedules defined on GCP. Others, like ODS, are triggered based on incoming webhooks. This is problematic in terms of:

*   Having a good overview
*   Detecting / identifying failures
*   Keeping track of changes to the orchestration
*   Ensuring changes are reviewed
*   Lack of boilerplate code for situations that demand additional technical requirements (e.g. Fivetran webhook or Ingestor rate limiter).
*   Disjointed schedules for ingestion and transformation pipelines.

The orchestrator needs to:

*   Trigger Fivetran ingestion pipelines
*   Trigger transformation pipelines with dbt cloud
*   Trigger GCP resources (e.g. functions, cloud run jobs)
*   Support integration with other tooling
*   Support sensors to detect if all preconditions have been met before kicking off the next part of a pipeline
*   Be able to queue or defer workloads that cannot run simultaneously (e.g. ODS)

## Options 🔗

|         | Option 1                                                                                                                                                                                               | Option 2                                                                                                                                                                                                                             |
| :------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tool**  | Airflow                                                                                                                                                                                                | Dagster                                                                                                                                                                                                                              |
| **Link**  | [airflow.apache.org](https://airflow.apache.org)                                                                                                                                                           | [dagster.io](https://dagster.io)                                                                                                                                                                                                       |
| **Pros**  | • Mature tool<br>• Big community<br>• DAG defined in code<br>• Open source<br>• Lots of connectors including Fivetran, dbt Cloud, and BigQuery<br>• Many hosting options<br>• Supports SSO with Entra ID | • Improved over Airflow<br>• Nice DBT integration<br>• Easier to develop with than Airflow due to developer-first experience.<br>• Separates business logic from infra<br>• Lightweight to run (no scheduler required)<br>• Good testing support<br>• DAG defined in code<br>• SSO available via Entra ID |
| **Cons**  | • Not everyone knows Python<br>• Local testing hard<br>• Pipeline bound to execution environment<br>• Running upgrades (depending on version)<br>• Requires procurement<br>• Exposing logs is fiddly<br>• DBT DAG mapping not natively supported | • Small community (321 contributors vs 2,594)<br>• Not everyone knows Python<br>• It's a big unknown for upgrades, scalability,<br>• Requires procurement                                                                      |
| **Other** | Task-centric                                                                                                                                                                                           | • Data-centric<br>• Hybrid deployment mode available (metadata on dagster cloud, data on GCP)                                                                                                                                         |
| **Costs** | See Option 1 A&B below                                                                                                                                                                               | [link]() (Note: Link URL missing in OCR)                                                                                                                                                                                             |

**Option 1 - A & B**

|          | Option 1A                                                                                                                                                                                                                                                              | Option 1B                                                                                                                                       |
| :------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Context**| Astronomer                                                                                                                                                                                                                                                             | GCP Cloud Composer                                                                                                                              |
| **Link**   | [astronomer.io](https://astronomer.io)                                                                                                                                                                                                                                   | [docs](https://cloud.google.com/composer/docs)                                                                                                   |
| **Pros**   | • Astronomer employees Airflow contributors<br>• Good support for getting started<br>• Astro CLI vastly improves the developer experience<br>• Latest Airflow version<br>• Airflow hosting managed by Astronomer. Hybrid execution model available with control over self-hosted execution environment. See [docs](https://docs.astronomer.io/).<br>• Fine-grained control over DAG runtime docker image.<br>• Amazing documentation.<br>• Support for many different kinds of executors.<br>• GitHub integration for CI/CD | • Integrated with GCP services, including logging, secret manager, cloud run and cloud functions<br>• Easy to get started: just deploy an instance<br>• IAM integration for access control |
| **Cons**   | • Can update in-place<br>• No direct log integration with GCP logging                                                                                                                                                                                                  | • No local development environment. Can probably use the Astro CLI workflow to develop locally.<br>• Hard to control the DAG runtime docker container. DAGs are synced via cloud storage.<br>• Supports only blocked executors. |
| **Other**  | • Dags deployed via astro tool<br>• No data in Astronomer, but metadata yes<br>• Hosting in GCP/AWS                                                                                                                                                                    | • Dags added via storage account                                                                                                                |
| **Costs**  | [link]() (Note: Link URL missing in OCR)                                                                                                                                                                                                                               | [link]() (Note: Link URL missing in OCR)                                                                                                        |

## Costs 🔗

### Current Use 🔗

Based loosely on current use, we'd need something like this for Production

*   A workflow to orchestrate ingestion, modelling and serving workflows, run on a daily basis
*   An ingestion workflow to trigger 10 Fivetran resources dbt jobs, cloud run jobs, and cloud functions

For Development:

*   The ability to verify workflows against our infrastructure

Per option:

**Option 1A - Airflow Astronomer**

Info: 🔗 [Astronomer (Astro) Pricing - Transparent & Flexible at Scale](https://www.astronomer.io/pricing/)

*   choice between "Pay As You Go" or "Custom"
*   "Pay As You Go" -> $0.35+/hr per deployment
*   Cost is (Deployment Cost) + (Worker Cost)
*   Deployment could be 24/7 Production and Development - create/delete as needed

Astronomer provides some pricing scenarios:

Standard - 100 DAGS - $934.40 per month
*   Production Deployment (Medium Scheduler, Two A10 Workers)
*   Dev Deployment (Small Scheduler, One A5 Worker)

Light - 10-50 DAGs - $350.40 per month
*   Small Scheduler & One A5 worker

**Option 1B - Cloud Composer**

With two composer instances running (one small, one medium), we would pay +-$1.100-$2.000 per month according to the [pricing calculator](https://cloud.google.com/products/calculator/#id=16f5e5e8-a2d4-4d8a-8e3b-7b2e7a3c9d7f) (Note: Link is generic, specific calculation might be needed).

**Option 2 - Dagster**

*   Team - $100 per month, 3 users (unlimited viewers), $0.005 per serverless compute minute. 30K materializations.
*   Enterprise - "Contact sales", $0.005 per serverless

This would cost +-$1200 / month

## Future Use 🔗

Considerations:

*   More data sources added
*   Additional transformations added

So maybe:

*   Longer run time
*   More compute

## Recommendation 🔗

The Astronomer runtime gives us more control over the development environment and the runtime environment, which is really nice and far superior over what Composer offers. It's also less expensive, although running the hybrid execution model would add costs for hosting our own Kubernetes clusters.

The trade-off between these two comes down to ease-of-setup v. customizability. The fact that Composer offers no control over the runtime environment is ultimately something that could become a blocker for data engineering work, as well as the limited executor support.

## Impact 🔗

This is an entirely different way-of-working than what we've done until now.

We probably need a migration strategy for current data products (if necessary), so that all workloads that need to be scheduled are orchestrated from the solution that we pick.

## Discussion 🔗

Lack of control over runtime execution environment makes Composer less attractive than Astronomer. The latter also adds a lot of additional tools to streamline DAG development and supports more complex DAGs. However, it's easy to start with composer and possibly migrate to Astronomer later if desired.

## Follow-ups 🔗

Place follow-up work here

## Related 🔗

Place related RFCs, ADRs or other documents here
