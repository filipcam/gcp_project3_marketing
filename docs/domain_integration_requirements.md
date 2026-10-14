# Domain Integration Requirements

## 1. Purpose

This document defines the minimum information that each domain must publish or confirm so that the publishing data mesh project can be integrated across Catalog, Sales, Logistics and Marketing.

It is intended as an operational checklist for the team.

This document complements:

```text
docs/data_products_contracts.md
docs/data_publication_order.md
```

`data_products_contracts.md` describes product-level contracts.

`data_publication_order.md` describes the order in which domains publish data.

This document answers a more practical question:

```text
What exactly do we still need from each domain to connect the project end to end?
```

---

## 2. General integration rule

Domains should not consume raw or internal tables from other domains.

Each domain should expose data for other domains through a published product layer.

Examples:

```text
Sales:
publishing-mesh-sales.sales_products.*

Marketing:
data-mesh-marketing.marketing_published.*

Logistics:
publishing-mesh-logistics.logistics_products.*
```

If a domain uses a different naming convention, the team should explicitly mark which tables are published and stable for cross-domain use.

---

## 3. Current stable shared products

## 3.1 Catalog

Current stable product:

```text
publishing-mesh-project.catalog.books
```

Grain:

```text
1 row = 1 book_id
```

Main consumers:

- Sales
- Logistics
- Marketing

Status:

```text
Implemented
```

Expected use:

- stable book identifiers,
- book metadata,
- validation of `book_id` in domain generators and models.

---

## 3.2 Sales

Current stable products:

```text
publishing-mesh-sales.sales_products.sales_daily_summary
publishing-mesh-sales.sales_products.top_products
publishing-mesh-sales.sales_products.book_daily_sales
```

The most important Sales product for cross-domain integration is:

```text
publishing-mesh-sales.sales_products.book_daily_sales
```

Grain:

```text
1 row = 1 sales_date + 1 book_id
```

Main consumers:

- Logistics
- Marketing
- Reporting

Status:

```text
Implemented
```

Expected use:

- Logistics can use it to analyze sold quantities by book and date.
- Marketing can use it to compare campaign activity with actual book sales.
- Reporting can use it for product-level daily sales analysis.

---

## 4. Requirements from Logistics

## 4.1 Required published product

Sales and Marketing need a Logistics product that exposes inventory availability by book.

Recommended product name:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

Status:

```text
Required / to be confirmed
```

Recommended grain:

```text
1 row = 1 snapshot_date + 1 book_id
```

Recommended refresh frequency:

```text
Twice per day
```

Recommended columns:

```text
snapshot_date
book_id
total_stock_on_hand
total_stock_reserved
total_stock_available
warehouses_count
```

Optional columns:

```text
load_date
last_updated_at
stock_status
```

Recommended quality rules:

```text
book_id is not null
snapshot_date is not null
total_stock_on_hand >= 0
total_stock_reserved >= 0
total_stock_available >= 0
total_stock_reserved <= total_stock_on_hand
one row per snapshot_date + book_id
```

Expected consumers:

- Sales
- Marketing
- Catalog, only if an availability-enriched catalog product is created

---

## 4.2 Known Logistics models

Current known Logistics models in the shared repository:

```text
inventory_snapshot
shipments_curated
logistics_daily_summary
low_stock_alert
```

Current likely internal layer:

```text
publishing-mesh-logistics.logistics
```

Potential candidate tables:

```text
publishing-mesh-logistics.logistics.inventory_snapshot
publishing-mesh-logistics.logistics.low_stock_alert
publishing-mesh-logistics.logistics.logistics_daily_summary
```

However, the publication status of these tables still needs confirmation.

---

## 4.3 Recommended Logistics contract decision

The team should confirm whether:

```text
inventory_snapshot
```

is a published product or only an internal curated model.

Recommendation:

```text
Use inventory_snapshot as an internal warehouse-level model.
Publish a separate inventory_by_book product for other domains.
```

Reason:

`inventory_snapshot` appears to be warehouse-level. Sales and Marketing usually need a simpler book-level view aggregated across warehouses.

---

## 4.4 Logistics questions to confirm

1. Is `inventory_snapshot` internal or published?
2. Will Logistics publish `logistics_products.inventory_by_book`?
3. Is the expected grain `snapshot_date + book_id`?
4. Should `inventory_by_book` aggregate across all warehouses?
5. Does Logistics publish two separate inventory snapshots per day?
6. What is the exact timestamp/date column for the snapshot?
7. Should Sales generate orders only for books where `total_stock_available > 0`?
8. Does Logistics update stock after Sales, or does it publish independent inventory snapshots?
9. Which service accounts or users should receive read access to Logistics published products?

---

## 5. Requirements from Marketing

## 5.1 Known Marketing project structure

Current known Marketing project:

```text
data-mesh-marketing
```

Known dbt layers:

```text
staging      -> marketing_silver, materialized as views
intermediate -> marketing_silver, materialized as views
marts        -> marketing_published, materialized as tables
```

Known raw source dataset:

```text
data-mesh-marketing.marketing_raw
```

Known internal layer:

```text
data-mesh-marketing.marketing_silver
```

Known published layer:

```text
data-mesh-marketing.marketing_published
```

Known raw sources:

```text
marketing_campaigns
marketing_campaign_products
marketing_campaign_daily_metrics
```

Known staging models:

```text
stg_marketing_campaigns
stg_marketing_campaign_products
stg_marketing_campaign_daily_metrics
```

Known intermediate model:

```text
int_campaign_performance
```

Known published mart candidates:

```text
mrt_campaign_performance
mrt_campaign_daily_performance
```

---

## 5.2 Current Marketing published candidates

### `marketing_published.mrt_campaign_performance`

Recommended interpretation:

```text
1 row = 1 campaign_id
```

Purpose:

- campaign-level performance summary,
- total impressions,
- clicks,
- cost,
- sessions,
- add-to-cart,
- conversions,
- CTR,
- CPC,
- CVR,
- performance segment.

Potential consumers:

- Reporting
- Sales, if campaign-level context is needed
- Management reporting

---

### `marketing_published.mrt_campaign_daily_performance`

Recommended interpretation:

```text
1 row = 1 campaign_id + 1 event_date
```

Purpose:

- daily campaign performance,
- daily impressions,
- clicks,
- cost,
- sessions,
- add-to-cart,
- conversions,
- CTR,
- CPC,
- CVR.

Potential consumers:

- Sales
- Reporting
- Marketing analysis
- Campaign effectiveness analysis

---

## 5.3 Missing or unconfirmed Marketing product

Sales needs a campaign-to-book mapping if campaign effectiveness is expected to be calculated against book sales.

Recommended product:

```text
data-mesh-marketing.marketing_published.campaign_products
```

Alternative name, if preferred by Marketing:

```text
data-mesh-marketing.marketing_published.mrt_campaign_products
```

Recommended grain:

```text
1 row = 1 campaign_id + 1 book_id
```

Recommended columns:

```text
campaign_id
book_id
campaign_name
start_date
end_date
status
channel
objective
target_segment
promotion_type
discount_percentage
```

Minimum required columns:

```text
campaign_id
book_id
start_date
end_date
status
```

Expected consumers:

- Sales
- Campaign effectiveness reporting
- Management reporting

Reason:

Without a published campaign-to-book product, Sales can see campaign performance by campaign, but cannot reliably connect campaigns to specific books sold in `sales_products.book_daily_sales`.

---

## 5.4 Marketing questions to confirm

1. Is `marketing_published` the official published product layer?
2. Are `mrt_campaign_performance` and `mrt_campaign_daily_performance` intended for cross-domain consumption?
3. Will Marketing publish campaign-to-book mapping?
4. What will the final table name be for campaign-to-book mapping?
5. What is the expected grain of that product?
6. Should campaign effectiveness be owned by Marketing or Sales?
7. Which project should run cross-domain effectiveness queries?
8. Which users or service accounts should receive access to Marketing published products?

---

## 6. Requirements from Sales for other domains

Sales currently publishes:

```text
publishing-mesh-sales.sales_products.sales_daily_summary
publishing-mesh-sales.sales_products.top_products
publishing-mesh-sales.sales_products.book_daily_sales
```

The key integration product is:

```text
publishing-mesh-sales.sales_products.book_daily_sales
```

Grain:

```text
1 row = 1 sales_date + 1 book_id
```

Main columns:

```text
sales_date
book_id
title
author_name
category
format
orders_count
items_sold
gross_sales_amount
```

Expected consumers:

- Logistics
- Marketing
- Reporting

Recommended access:

```text
roles/bigquery.dataViewer on publishing-mesh-sales.sales_products
roles/bigquery.jobUser on the project used to execute queries
```

Sales should not expose these internal datasets for normal cross-domain consumption:

```text
publishing-mesh-sales.sales_raw
publishing-mesh-sales.sales
```

---

## 7. Airflow integration requirements

Current working demo DAG:

```text
data_mesh_demo_pipeline
```

Current order:

```text
Catalog -> Sales
```

Future possible order after Logistics and Marketing contracts are confirmed:

```text
Catalog
  -> Logistics inventory refresh
  -> Marketing campaign planning / campaign metrics
  -> Sales
  -> Marketing campaign effectiveness
  -> Logistics inventory update / low stock refresh
```

Recommended approach:

- Keep the current `Catalog -> Sales` DAG as a working demo.
- Do not add hard dependencies on Logistics or Marketing until their published products are confirmed.
- Add Logistics and Marketing to the demo DAG only after their products, access and refresh behavior are stable.
- Consider separate domain DAGs for each domain, plus one end-to-end demo DAG.

---

## 8. Access requirements

For every published product, the producing domain should define:

```text
who can read the product
which project runs query jobs
which service account runs automated pipelines
```

Recommended minimum pattern for consumers:

```text
BigQuery Data Viewer on the published dataset
BigQuery Job User on the execution project
```

Published datasets should be shared.

Raw and internal datasets should not be broadly shared.

---

## 9. Current blockers

## 9.1 Logistics

Blocked until the team confirms:

```text
final published inventory product
final dataset name
grain
columns
refresh behavior
access for Sales and Marketing
```

## 9.2 Marketing

Blocked until the team confirms:

```text
whether marts are official published products
whether campaign-to-book mapping will be published
final project/dataset/table names
access for Sales
ownership of campaign effectiveness
```

## 9.3 Sales

Sales can continue independently with current products.

Sales should not yet change its generator to depend on Logistics inventory until `inventory_by_book` or equivalent is confirmed.

---

## 10. Recommended next actions

1. Logistics confirms or creates a published inventory-by-book product.
2. Marketing confirms published marts and campaign-to-book product.
3. The team updates `docs/data_products_contracts.md`.
4. The team updates `docs/data_publication_order.md`.
5. Sales updates its generator to consume Logistics availability, if required.
6. Airflow demo DAG is extended only after Logistics and Marketing products are stable.
7. Final cleanup is done after the integration model is confirmed.

---

## 11. Summary

The current project already has stable Catalog and Sales published products.

The next integration step is not to change Sales or Airflow immediately, but to confirm what Logistics and Marketing publish as stable cross-domain products.

The minimum products needed for integration are:

```text
Catalog:
publishing-mesh-project.catalog.books

Sales:
publishing-mesh-sales.sales_products.book_daily_sales

Logistics:
publishing-mesh-logistics.logistics_products.inventory_by_book

Marketing:
data-mesh-marketing.marketing_published.mrt_campaign_daily_performance
data-mesh-marketing.marketing_published.mrt_campaign_performance
data-mesh-marketing.marketing_published.campaign_products
```

After these are confirmed, the team can safely extend Sales generation logic and Airflow orchestration.
