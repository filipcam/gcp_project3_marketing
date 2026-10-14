# Data Publication Order and Domain Dependencies

## 1. Purpose

This document describes the proposed publication order between domains in the publishing data mesh project.

It is a working agreement for how domain data products should be refreshed and consumed by other domains.

This document focuses on publication order and cross-domain dependencies. Detailed column-level contracts should be maintained in `docs/data_products_contracts.md`.

---

## 2. Core principle

Each domain should publish stable data products for other domains.

Other domains should consume only published products, not raw or internal tables.

Recommended logical pattern:

```text
domain_raw -> internal/curated layer -> published products
```

The naming of layers may differ between domains. For example:
- Sales currently uses `sales` as the internal curated layer and `sales_products` as the published layer.
- Marketing uses `marketing_silver` as the internal layer and `marketing_published` as the published layer.
- Logistics currently uses `logistics` for its curated models; the final published layer still needs to be confirmed.

The important distinction is not the exact layer name, but whether a table is:
- internal to the owning domain,
- or published for cross-domain consumption.

---

## 3. Current domain projects and layers

## 3.1 Catalog

Project:

```text
publishing-mesh-project
```

Current published product:

```text
publishing-mesh-project.catalog.books
```

Status:

```text
Implemented
```

Purpose:

Catalog provides stable book master data for all other domains.

Main consumers:
- Logistics
- Marketing
- Sales

---

## 3.2 Sales

Project:

```text
publishing-mesh-sales
```

Current internal curated layer:

```text
publishing-mesh-sales.sales
```

Current published layer:

```text
publishing-mesh-sales.sales_products
```

Current published products:

```text
publishing-mesh-sales.sales_products.sales_daily_summary
publishing-mesh-sales.sales_products.top_products
publishing-mesh-sales.sales_products.book_daily_sales
```

Status:

```text
Implemented
```

The most important Sales product for Logistics and Marketing is:

```text
publishing-mesh-sales.sales_products.book_daily_sales
```

Grain:

```text
1 row = 1 sales_date + 1 book_id
```

Purpose:

This table shows which books were sold on each day and in what quantity.

---

## 3.3 Logistics

Project:

```text
publishing-mesh-logistics
```

Current known models:

```text
inventory_snapshot
shipments_curated
logistics_daily_summary
low_stock_alert
```

Current likely internal/curated layer:

```text
publishing-mesh-logistics.logistics
```

Known refresh frequency:

```text
Twice per day
```

Current publication status:

```text
To be confirmed
```

Recommended published layer:

```text
publishing-mesh-logistics.logistics_products
```

Recommended published product:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

Recommended grain:

```text
1 row = 1 snapshot_date + 1 book_id
```

Purpose:

This product should publish stock availability by book for Sales and Marketing.

---

## 3.4 Marketing

Project:

```text
data-mesh-marketing
```

Current raw layer:

```text
data-mesh-marketing.marketing_raw
```

Current internal layer:

```text
data-mesh-marketing.marketing_silver
```

The Marketing dbt project uses:
- `staging` models as views in `marketing_silver`,
- `intermediate` models as views in `marketing_silver`.

Current published layer:

```text
data-mesh-marketing.marketing_published
```

The Marketing dbt project uses:
- `marts` models as tables in `marketing_published`.

Known raw sources:

```text
marketing_raw.marketing_campaigns
marketing_raw.marketing_campaign_products
marketing_raw.marketing_campaign_daily_metrics
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
marketing_published.mrt_campaign_performance
marketing_published.mrt_campaign_daily_performance
```

Status:

```text
Implemented in a separate Marketing repository; final cross-domain publication contract to be confirmed
```

Important note:

Marketing has raw and staging data for campaign-to-book mapping through `marketing_campaign_products` / `stg_marketing_campaign_products`, but there is no confirmed published mart for campaign products yet.

Recommended additional published product:

```text
data-mesh-marketing.marketing_published.campaign_products
```

or another agreed published table exposing campaign-to-book mapping.

Purpose:

Sales needs campaign-to-book mapping if it is expected to calculate sales attribution or campaign effectiveness together with Marketing.

---

## 4. Proposed publication order

## 4.1 Step 1 — Catalog publishes book master data

Catalog should publish first because all other domains depend on stable book identifiers and metadata.

Published product:

```text
publishing-mesh-project.catalog.books
```

Grain:

```text
1 row = 1 book_id
```

Main consumers:
- Logistics
- Marketing
- Sales

Purpose:
- provide stable `book_id`,
- provide book metadata such as title, author, category, format and price.

---

## 4.2 Step 2 — Logistics publishes inventory and shipment data

Logistics should consume Catalog and publish stock availability.

Current known curated models:

```text
publishing-mesh-logistics.logistics.inventory_snapshot
publishing-mesh-logistics.logistics.shipments_curated
publishing-mesh-logistics.logistics.logistics_daily_summary
publishing-mesh-logistics.logistics.low_stock_alert
```

Recommended published product:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

Recommended grain:

```text
1 row = 1 snapshot_date + 1 book_id
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

Refresh frequency:

```text
Twice per day
```

Main consumers:
- Sales
- Marketing
- Catalog, if an availability-enriched catalog product is created

Purpose:
- show which books are available,
- support sales generation,
- support marketing campaign planning,
- identify low-stock items.

Open point:

```text
Confirm whether inventory_snapshot is a published product or only an internal curated model.
```

Recommendation:

```text
Create a separate inventory_by_book product for cross-domain use.
```

Reason:

`inventory_snapshot` is warehouse-level. Other domains usually need a simpler product aggregated by `book_id`.

---

## 4.3 Step 3 — Marketing publishes campaign plans and campaign metrics

Marketing should consume Catalog and Logistics availability before campaign execution.

Known raw inputs:

```text
marketing_campaigns
marketing_campaign_products
marketing_campaign_daily_metrics
```

Known internal Marketing models:

```text
marketing_silver.stg_marketing_campaigns
marketing_silver.stg_marketing_campaign_products
marketing_silver.stg_marketing_campaign_daily_metrics
marketing_silver.int_campaign_performance
```

Known published Marketing marts:

```text
marketing_published.mrt_campaign_performance
marketing_published.mrt_campaign_daily_performance
```

Recommended published products for cross-domain use:

```text
marketing_published.mrt_campaign_performance
marketing_published.mrt_campaign_daily_performance
marketing_published.campaign_products
```

The first two marts already exist as published candidates. The `campaign_products` product still needs confirmation or implementation as a published table.

Recommended grains:

```text
mrt_campaign_performance:
1 row = 1 campaign_id

mrt_campaign_daily_performance:
1 row = 1 campaign_id + 1 event_date

campaign_products:
1 row = 1 campaign_id + 1 book_id
```

Main consumers:
- Sales
- Marketing effectiveness reporting
- Management reporting

Purpose:
- define which campaigns are running,
- identify which books are promoted,
- publish daily campaign metrics,
- support later comparison with Sales results.

Open point:

```text
Confirm whether campaign-to-book mapping will be published as a dedicated product.
```

---

## 4.4 Step 4 — Sales publishes sales results

Sales should consume Catalog and, in the next version, Logistics availability.

Current published products:

```text
publishing-mesh-sales.sales_products.book_daily_sales
publishing-mesh-sales.sales_products.sales_daily_summary
publishing-mesh-sales.sales_products.top_products
```

Most important product for other domains:

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

Main consumers:
- Logistics
- Marketing
- Reporting

Purpose:
- show which books were sold on each day,
- provide quantities sold by book,
- support stock update logic,
- support campaign effectiveness analysis.

---

## 4.5 Step 5 — Marketing publishes campaign effectiveness

Campaign effectiveness should be calculated after Sales products are published.

Current Marketing published marts already provide campaign performance based on marketing metrics:

```text
marketing_published.mrt_campaign_performance
marketing_published.mrt_campaign_daily_performance
```

A cross-domain effectiveness product should additionally combine Marketing with Sales.

Possible product owned by Marketing:

```text
marketing_published.campaign_sales_effectiveness
```

Alternative product owner:

```text
sales_products.campaign_sales_attribution
```

To be decided by the team.

Recommended inputs:

```text
marketing_published.mrt_campaign_daily_performance
marketing_published.campaign_products
publishing-mesh-sales.sales_products.book_daily_sales
publishing-mesh-project.catalog.books
```

Recommended grain:

```text
1 row = 1 campaign_id + 1 book_id + 1 date
```

Purpose:
- compare promoted books with actual sales,
- measure campaign impact,
- support marketing performance reporting.

Open point:

```text
Decide whether cross-domain campaign effectiveness is owned by Marketing or Sales.
```

---

## 4.6 Step 6 — Logistics updates or analyzes inventory after Sales

After Sales publication, Logistics may update or analyze inventory movement.

Input from Sales:

```text
publishing-mesh-sales.sales_products.book_daily_sales
```

Possible Logistics products:

```text
logistics_products.inventory_by_book
logistics_products.inventory_movements
logistics_products.low_stock_alert
```

Purpose:
- reduce or analyze available stock after sales,
- identify books requiring replenishment,
- update low-stock alerts.

Open point:

```text
Confirm whether Logistics physically updates the inventory snapshot after Sales or only publishes independent inventory snapshots twice per day.
```

---

## 5. Proposed dependency map

```text
Catalog
  -> Logistics
  -> Marketing
  -> Sales

Logistics
  -> Marketing
  -> Sales

Marketing
  -> Sales attribution / campaign effectiveness

Sales
  -> Marketing effectiveness
  -> Logistics inventory update / replenishment analysis
```

More detailed:

```text
catalog.books
  -> logistics inventory generation
  -> marketing campaign planning
  -> sales generation and sales products

logistics inventory_by_book
  -> marketing campaign planning
  -> sales generation

marketing campaign_products
  -> campaign effectiveness / attribution

sales book_daily_sales
  -> marketing campaign effectiveness
  -> logistics inventory updates or replenishment analysis
```

---

## 6. Airflow implication

For demonstration, a single end-to-end DAG is acceptable.

Current demo DAG:

```text
data_mesh_demo_pipeline
```

Current order:

```text
Catalog -> Sales
```

Recommended future demo order:

```text
Catalog
  -> Logistics inventory refresh
  -> Marketing campaign planning / campaign metrics
  -> Sales
  -> Marketing effectiveness
  -> Logistics inventory update / low stock refresh
```

However, each domain may also have its own independent DAG:

```text
catalog_daily_pipeline
logistics_daily_pipeline
marketing_daily_pipeline
sales_daily_pipeline
```

The end-to-end DAG should be treated as a demo or coordination DAG, not necessarily as the only production-style orchestration model.

---

## 7. Open questions for Logistics

1. Is `inventory_snapshot` intended to be a published data product, or is it an internal curated model?
2. Should we create a separate product called `logistics_products.inventory_by_book`?
3. Should `inventory_by_book` be aggregated across warehouses?
4. Should the grain be `snapshot_date + book_id`?
5. Is Logistics publishing inventory twice per day as separate snapshots?
6. Should Sales generate orders only for books with `total_stock_available > 0`?
7. Should Logistics update stock after Sales, or is the project using independent simulated snapshots?

---

## 8. Open questions for Marketing

1. Confirm the GCP project and final dataset names for Marketing.
2. Confirm that `marketing_published` is the official published layer.
3. Confirm whether `mrt_campaign_performance` and `mrt_campaign_daily_performance` are intended for cross-domain consumption.
4. Confirm whether campaign-to-book mapping will be published as a product.
5. Confirm the final name of the campaign-to-book product.
6. Decide whether cross-domain campaign effectiveness is owned by Marketing or Sales.
7. Confirm what table Sales should use if it needs campaign context.

---

## 9. Current stable products available to other domains

### Catalog

```text
publishing-mesh-project.catalog.books
```

### Sales

```text
publishing-mesh-sales.sales_products.book_daily_sales
publishing-mesh-sales.sales_products.sales_daily_summary
publishing-mesh-sales.sales_products.top_products
```

### Logistics

To be confirmed.

Candidate products:

```text
publishing-mesh-logistics.logistics.inventory_snapshot
publishing-mesh-logistics.logistics.low_stock_alert
publishing-mesh-logistics.logistics.logistics_daily_summary
```

Recommended future published product:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

### Marketing

Known published candidate products:

```text
data-mesh-marketing.marketing_published.mrt_campaign_performance
data-mesh-marketing.marketing_published.mrt_campaign_daily_performance
```

Recommended additional product:

```text
data-mesh-marketing.marketing_published.campaign_products
```

---

## 10. Summary

The agreed publication order should be based on domain dependencies:

1. Catalog publishes book master data.
2. Logistics publishes availability and stock data twice per day.
3. Marketing publishes campaign plans and campaign metrics using Catalog and Logistics availability.
4. Sales publishes actual sales results.
5. Marketing or Sales publishes campaign effectiveness using Sales results.
6. Logistics updates or analyzes inventory after Sales.

The key principle is that domains should depend on published data products, not on raw or internal tables.

This document is a working version and should be updated after the Logistics and Marketing contracts are finalized.
