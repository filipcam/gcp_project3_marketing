# Data Product Contracts

## 1. Purpose

This document defines the main data products and cross-domain dependencies in the Publishing Mesh Project.

Its goal is to make clear:

- which domain owns each data product,
- where each data product is published,
- what grain and key columns it uses,
- which other domains may consume it,
- which datasets are internal and which are safe for cross-domain use,
- which products are implemented, recommended, planned, or confirmed for cross-domain use.

The central rule is:

> Domains should not consume other domains' raw or internal curated tables. They should consume only published data products.

---

## 2. Executive summary — main data product contracts

| Domain | Data product | Location | Status | Grain | Main consumers | Refresh |
|---|---|---|---|---|---|---|
| Catalog | `books` | `publishing-mesh-project.catalog.books` | Implemented | 1 row = 1 `book_id` | Sales, Logistics, Marketing | Daily / on demand |
| Sales | `book_daily_sales` | `publishing-mesh-sales.sales_products.book_daily_sales` | Implemented | 1 row = 1 `sales_date` + 1 `book_id` | Logistics, Marketing, reporting | Daily |
| Sales | `sales_daily_summary` | `publishing-mesh-sales.sales_products.sales_daily_summary` | Implemented | 1 row = 1 `sales_date` | Reporting, Marketing | Daily |
| Sales | `top_products` | `publishing-mesh-sales.sales_products.top_products` | Implemented | 1 row = 1 `book_id` | Marketing, reporting | Daily |
| Logistics | `inventory_by_book` | `publishing-mesh-logistics.logistics_products.inventory_by_book` | Implemented | 1 row = 1 `snapshot_date` + 1 `book_id` | Sales, Marketing | Daily |
| Marketing | `pub_campaign_performance` | `data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_performance` | Implemented | 1 row = 1 campaign | Marketing, reporting | Daily / on demand |
| Marketing | `pub_campaign_daily_performance` | `data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_daily_performance` | Implemented | 1 row = 1 campaign + 1 date | Marketing, Sales | Daily |
| Marketing | `pub_campaign_sales_attribution` | `data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_sales_attribution` | Implemented | 1 row = 1 campaign + 1 book / attribution unit | Marketing, Sales | Daily / on demand |

The detailed sections below describe each product contract in more detail, including ownership, purpose, access model, quality expectations and open questions.

The current stable cross-domain paths are:

```text
Catalog -> Sales
Catalog -> Logistics
Logistics -> Sales
```

Sales uses the Logistics published product `inventory_by_book` to generate sales only for books available in inventory. For sales date `D`, Sales uses the Logistics snapshot from `D - 1`.

---

## 3. Current implemented data products

## 3.1 Catalog: shared books

### Owner

Catalog domain

### Product name

`books`

### Location

```text
publishing-mesh-project.catalog.books
```

### Status

```text
Implemented
```

### Grain

```text
1 row = 1 book_id
```

### Key columns

- `book_id`

### Main columns

- `book_id`
- `isbn`
- `title`
- `author_name`
- `publisher_name`
- `category`
- `format`
- `publication_date`
- `list_price`
- `load_date`

### Purpose

This is the shared source of truth for book metadata.

It should be used by domains that need book-level reference information, such as:

- Sales,
- Logistics,
- Marketing.

### Consumers

Current consumers:

- Sales
- Logistics

Planned / expected consumers:

- Marketing

### Access model

Consumers should receive read access to:

```text
publishing-mesh-project.catalog.books
```

They should not read directly from:

```text
publishing-mesh-project.catalog_raw.books
```

unless they are explicitly debugging raw Catalog ingestion.

### Quality expectations

- `book_id` is not null.
- `book_id` is unique.
- `isbn` is not null.
- `title` is not null.
- `author_name` is not null.
- `category` is not null.
- `format` is not null.
- `list_price` is not null.
- `load_date` is not null.

### Notes

Catalog should remain a reference/master-data product. Inventory availability should not be embedded directly into `catalog.books`; Logistics owns stock and availability.

If Catalog needs price history, it should be implemented as a separate product, for example:

```text
publishing-mesh-project.catalog.book_price_history
```

This avoids changing the current contract of `catalog.books`, where one `book_id` corresponds to one current book record.

---

## 3.2 Sales: daily sales summary

### Owner

Sales domain

### Product name

`sales_daily_summary`

### Location

```text
publishing-mesh-sales.sales_products.sales_daily_summary
```

### Status

```text
Implemented
```

### Grain

```text
1 row = 1 sales_date
```

### Key columns

- `sales_date`

### Main columns

- `sales_date`
- `orders_count`
- `items_sold`
- `gross_sales_amount`

### Purpose

This product provides high-level daily Sales metrics for reporting and cross-domain analysis.

### Consumers

Potential consumers:

- Marketing
- Management reporting
- Future dashboard layer

### Access model

Consumers should receive:

- `roles/bigquery.dataViewer` on `publishing-mesh-sales.sales_products`,
- `roles/bigquery.jobUser` on the project where they execute queries, if required.

Consumers should not receive broad access to:

- `publishing-mesh-sales.sales_raw`,
- `publishing-mesh-sales.sales`.

### Quality expectations

- `sales_date` is not null.
- One row per `sales_date`.
- `orders_count >= 0`.
- `items_sold >= 0`.
- `gross_sales_amount >= 0`.

---

## 3.3 Sales: top products

### Owner

Sales domain

### Product name

`top_products`

### Location

```text
publishing-mesh-sales.sales_products.top_products
```

### Status

```text
Implemented
```

### Grain

```text
1 row = 1 book_id
```

### Key columns

- `book_id`

### Main columns

- `book_id`
- `title`
- `author_name`
- `category`
- `format`
- `total_orders`
- `total_items_sold`
- `gross_sales_amount`

### Purpose

This product provides product-level Sales metrics enriched with shared Catalog metadata.

It demonstrates cross-project data product consumption:

```text
publishing-mesh-sales.sales.order_items_curated
publishing-mesh-sales.sales.orders_curated
publishing-mesh-project.catalog.books
  -> publishing-mesh-sales.sales_products.top_products
```

### Consumers

Potential consumers:

- Marketing
- Catalog analysis
- Management reporting
- Future dashboard layer

### Access model

Consumers should read this product from:

```text
publishing-mesh-sales.sales_products.top_products
```

They should not read from internal Sales tables unless explicitly collaborating on the Sales implementation.

### Quality expectations

- `book_id` is not null.
- `book_id` is unique.
- `total_orders >= 0`.
- `total_items_sold >= 0`.
- `gross_sales_amount >= 0`.

---

## 3.4 Sales: book daily sales

### Owner

Sales domain

### Product name

`book_daily_sales`

### Location

```text
publishing-mesh-sales.sales_products.book_daily_sales
```

### Status

```text
Implemented
```

### Grain

```text
1 row = 1 sales_date + 1 book_id
```

### Key columns

- `sales_date`
- `book_id`

### Main columns

- `sales_date`
- `book_id`
- `title`
- `author_name`
- `category`
- `format`
- `orders_count`
- `items_sold`
- `gross_sales_amount`

### Purpose

This product provides daily book-level Sales metrics.

It answers which books were sold on a given day, in what quantity, and for what gross sales amount.

This is the main Sales product intended for Logistics and Marketing use cases.

### Upstream dependencies

- `publishing-mesh-sales.sales.orders_curated`
- `publishing-mesh-sales.sales.order_items_curated`
- `publishing-mesh-project.catalog.books`

### Consumers

Potential consumers:

- Logistics
- Marketing
- Management reporting
- Future dashboard layer

### Access model

Consumers should read this product from:

```text
publishing-mesh-sales.sales_products.book_daily_sales
```

They should not read from internal Sales tables such as:

- `publishing-mesh-sales.sales.orders_curated`
- `publishing-mesh-sales.sales.order_items_curated`

### Quality expectations

- `sales_date` is not null.
- `book_id` is not null.
- `items_sold` is not null and `items_sold >= 0`.
- `gross_sales_amount` is not null and `gross_sales_amount >= 0`.
- One row per `sales_date + book_id`.

### Inventory-aware generation note

The Sales data generator uses the Logistics published product:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

For sales date `D`, it uses the Logistics inventory snapshot from `D - 1`.

This rule applies to generated input data. The `book_daily_sales` product itself remains a Sales product and should not expose Logistics columns directly unless a separate cross-domain product is created.

---

## 3.5 Logistics: inventory by book

### Owner

Logistics domain

### Product name

`inventory_by_book`

### Location

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

### Status

```text
Implemented
```

### Grain

```text
1 row = 1 snapshot_date + 1 book_id
```

### Key columns

- `snapshot_date`
- `book_id`

### Main columns

- `snapshot_date`
- `book_id`
- `total_stock_on_hand`
- `total_stock_reserved`
- `total_stock_available`
- `warehouses_count`

### Purpose

This product publishes book inventory availability information owned by Logistics.

It answers questions such as:

- how many units of each book are in stock,
- how many units are reserved,
- how many units are available for sale,
- whether a book can be used by Sales generation or Marketing campaigns.

### Consumers

Current / expected consumers:

- Sales
- Marketing
- Management reporting
- Future dashboard layer

### Refresh frequency

```text
Daily
```

### Access model

Consumers should receive read access to:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

Consumers should not read directly from:

- `publishing-mesh-logistics.logistics_raw`,
- `publishing-mesh-logistics.logistics_curated`,
- other internal Logistics datasets.

### Quality expectations

- `snapshot_date` is not null.
- `book_id` is not null.
- `total_stock_on_hand >= 0`.
- `total_stock_reserved >= 0`.
- `total_stock_available >= 0`.
- `total_stock_reserved <= total_stock_on_hand`.
- One row per `snapshot_date + book_id`.

### Known validation

The product has been observed with the following expected schema:

```text
snapshot_date DATE
book_id INTEGER
total_stock_on_hand INTEGER
total_stock_reserved INTEGER
total_stock_available INTEGER
warehouses_count INTEGER
```

It has also been validated to contain one row per `snapshot_date + book_id` for checked snapshots.

### Design note

Inventory should not be embedded directly into the core Catalog product `catalog.books`.

The core Catalog product should remain book master data.

If an availability-enriched view is needed, it should be created as a separate product, for example:

```text
logistics_products.book_availability_enriched
```

This keeps ownership clear:

- Catalog owns book metadata.
- Logistics owns stock and availability.

---

## 4. Recommended / planned data products

## 4.1 Catalog: book price history

### Owner

Catalog domain

### Product name

`book_price_history`

### Suggested location

```text
publishing-mesh-project.catalog.book_price_history
```

### Status

```text
Planned / recommended
```

### Grain

```text
1 row = 1 book_id + 1 valid_from
```

Alternative interpretation:

```text
1 row = one catalog list price version for one book
```

### Key columns

- `book_id`
- `valid_from`

### Suggested columns

- `book_id`
- `list_price`
- `currency`
- `valid_from`
- `valid_to`
- `is_current`
- `created_at` or `loaded_at`

### Purpose

This product should track changes in catalog list price over time without changing the current contract of `catalog.books`.

### Design note

The existing product:

```text
publishing-mesh-project.catalog.books
```

should remain a current-state reference product with one row per `book_id`.

Historical price tracking should be published separately in `book_price_history`. This avoids accidental duplication in joins where consumers expect one row per book.

### Expected consumers

- Sales, if historical catalog list price is needed for analysis,
- Catalog analysis,
- Management reporting.

### Open questions

1. Should price history be generated from a separate source file?
2. Should currency always be `PLN` in the current demo scope?
3. Should Sales use catalog list price history, or only actual transaction price from Sales?
4. Should `valid_to` be nullable for the current record?

---

## 4.2 Logistics: low stock alert

### Owner

Logistics domain

### Product name

`low_stock_alert`

### Suggested location

```text
publishing-mesh-logistics.logistics_products.low_stock_alert
```

### Status

```text
Implemented as a Logistics model / publication status confirmed
```

### Recommended grain

```text
1 row = 1 snapshot_date + 1 book_id with low available stock
```

### Key columns

- `snapshot_date`
- `book_id`

### Known / expected columns

- `book_id`
- `total_stock_on_hand`
- `total_stock_reserved`
- `total_stock_available`
- `warehouses_count`
- `snapshot_date`

### Purpose

This product identifies books with low available stock across warehouses.

It can support:

- replenishment planning,
- campaign planning constraints,
- avoiding promotion of books with insufficient stock.

### Expected consumers

- Logistics
- Marketing
- Sales, if Sales generation should avoid low-stock books
- Management reporting

### Note

This should not replace `inventory_by_book`, because it only contains low-stock cases and does not represent the full inventory state.

---

## 4.3 Logistics: logistics daily summary

### Owner

Logistics domain

### Product name

`logistics_daily_summary`

### Suggested location

```text
publishing-mesh-logistics.logistics_products.logistics_daily_summary
```

### Status

```text
Implemented as a Logistics model / publication status confirmed
```

### Recommended grain

```text
1 row = 1 summary_date
```

### Key columns

- `summary_date`

### Known / expected columns

- `summary_date`
- `shipments_count`
- `delivered_count`
- `in_transit_count`
- `prepared_count`
- `returned_count`
- `total_stock_available`

### Purpose

This product provides daily Logistics operational metrics.

It can support reporting and high-level monitoring of shipments and inventory availability.

### Expected consumers

- Logistics
- Management reporting
- Future dashboard layer

---

## 4.4 Marketing: campaign performance

### Owner

Marketing domain

### Product name

`pub_campaign_performance`

### Location

```text
data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_performance
```

### Status

```text
Implemented / final publication dataset confirmed
```

### Grain

```text
1 row = 1 campaign_id
```

### Key columns

- `campaign_id`

### Main columns

Confirmed by Marketing owner.

Expected examples:

- `campaign_id`
- `campaign_name`
- `channel`
- `objective`
- `target_segment`
- `start_date`
- `end_date`
- `budget_amount`
- `status`
- campaign performance metrics

### Purpose

This product provides campaign-level performance metrics for Marketing reporting and cross-domain analysis.

### Expected consumers

- Marketing
- Management reporting
- Future attribution products

### Access model

Confirmed by Marketing owner.

Consumers should receive read access to the published Marketing dataset, not to raw or silver/internal Marketing tables.

### Open questions

1. Is `marketing_dbt_dev_marketing_published` the final dataset name or a development dataset?
2. What is the final schema?
3. Which teams should receive access?

---

## 4.5 Marketing: campaign daily performance

### Owner

Marketing domain

### Product name

`pub_campaign_daily_performance`

### Location

```text
data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_daily_performance
```

### Status

```text
Implemented / final publication dataset confirmed
```

### Grain

```text
1 row = 1 campaign_id + 1 event_date
```

### Key columns

- `campaign_id`
- `event_date`

### Main columns

Confirmed by Marketing owner.

Expected examples:

- `campaign_id`
- `campaign_name`
- `event_date`
- `channel`
- `objective`
- `impressions`
- `clicks`
- `cost_amount`
- `sessions`
- `add_to_cart`
- `conversions`
- calculated performance metrics

### Purpose

This product provides daily campaign performance metrics.

It supports:

- campaign trend analysis,
- comparison of marketing activity with daily Sales results,
- future campaign effectiveness analysis.

### Expected consumers

- Marketing
- Sales
- Management reporting
- Future attribution products

### Access model

Confirmed by Marketing owner.

Consumers should receive read access to the published Marketing dataset, not to raw or silver/internal Marketing tables.

---

## 4.6 Marketing: campaign sales attribution

### Owner

Marketing domain, or jointly Marketing and Sales if agreed by the team.

### Product name

`pub_campaign_sales_attribution`

### Location

```text
data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_sales_attribution
```

### Status

```text
Implemented / grain and final publication status confirmed
```

### Recommended grain

Confirmed.

Expected option:

```text
1 row = 1 campaign_id + 1 book_id + 1 date
```

### Key columns

Expected:

- `campaign_id`
- `book_id`
- date column confirmed

### Purpose

This product should compare campaign activity with actual book sales.

It can answer questions such as:

- which promoted books sold during a campaign,
- whether campaign activity correlates with book sales,
- which campaigns generated conversions or sales uplift,
- which campaigns had high spend but low sales impact.

### Expected consumers

- Marketing
- Sales
- Management reporting

### Open questions

1. What is the exact grain?
2. Does the product contain `book_id`?
3. Which date column should be used for joining with Sales?
4. Is the current dataset name final?
5. Is this product intended for cross-domain use?

---

## 4.7 Marketing: campaign-to-book mapping

### Owner

Marketing domain

### Product name

`campaign_products`

### Suggested location

```text
data-mesh-marketing.marketing_published.campaign_products
```

Alternative name:

```text
data-mesh-marketing.marketing_published.mrt_campaign_products
```

### Status

```text
Recommended / confirmed
```

### Reason for status

The Marketing attribution product is treated as the confirmed source for campaign-to-sales analysis. A separate campaign-to-book mapping product may still be added later if the team decides it is useful.

### Recommended grain

```text
1 row = 1 campaign_id + 1 book_id
```

### Key columns

- `campaign_id`
- `book_id`

### Suggested columns

Minimum required:

- `campaign_id`
- `book_id`
- `start_date`
- `end_date`
- `status`

Recommended additional columns:

- `campaign_name`
- `channel`
- `objective`
- `target_segment`
- `promotion_type`
- `discount_percentage`
- `_dbt_loaded_at`

### Purpose

This product should describe which books are promoted by which marketing campaigns.

It should use `book_id` from the shared Catalog product.

This product is required if Sales or Marketing wants to calculate campaign effectiveness against book-level Sales data.

### Expected consumers

- Sales
- Marketing analysis
- Future attribution products
- Management reporting

---

## 5. Cross-domain dependency map

## 5.1 Current implemented dependencies

```text
Catalog -> Sales
Catalog -> Logistics
Logistics -> Sales
```

Implemented dependency examples:

```text
publishing-mesh-project.catalog.books
  -> publishing-mesh-sales.sales_products.top_products
  -> publishing-mesh-sales.sales_products.book_daily_sales
```

```text
publishing-mesh-project.catalog.books
  -> publishing-mesh-logistics.logistics_products.inventory_by_book
```

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
  -> sales/generate_sales_daily.py
  -> publishing-mesh-sales.sales_products.book_daily_sales
```

Sales consumes Catalog to enrich product-level Sales metrics with book metadata.

Sales also uses Logistics inventory availability during data generation. For sales date `D`, Sales uses Logistics snapshot `D - 1`.

---

## 5.2 Recommended near-term dependencies

```text
Catalog -> Marketing
```

Marketing should use `catalog.books` when defining promoted books in campaigns.

```text
Sales -> Logistics
```

Logistics may use `sales_products.book_daily_sales` to update or analyze stock movements.

```text
Sales -> Marketing
```

Marketing may use `sales_products.book_daily_sales` to evaluate campaign effectiveness.

```text
Logistics -> Marketing
```

Marketing may use inventory availability to avoid campaigns for unavailable books.

```text
Marketing -> Sales
```

Sales may use Marketing campaign products and campaign performance products to build attribution, but only after the Marketing product grain and contract are confirmed.

---

## 6. Internal vs published datasets

Each domain should clearly distinguish raw/internal datasets from published products.

### Raw layer

Examples:

```text
sales_raw
logistics_raw
marketing_raw
catalog_raw
```

Purpose:

- raw ingestion,
- append-oriented source tables,
- technical loading/debugging.

Consumers:

- domain owner,
- pipeline service accounts,
- selected developers only.

### Internal curated layer

Examples:

```text
publishing-mesh-sales.sales
publishing-mesh-logistics.logistics_curated
data-mesh-marketing.marketing_silver
```

Purpose:

- cleaned internal tables,
- intermediate models,
- domain-owned transformations.

Consumers:

- domain owner,
- pipeline service accounts,
- selected collaborators only.

### Published products layer

Examples:

```text
publishing-mesh-sales.sales_products
publishing-mesh-logistics.logistics_products
data-mesh-marketing.marketing_published
```

Purpose:

- stable published data products,
- cross-domain consumption,
- reporting,
- demos and presentation.

Consumers:

- other domains,
- reporting users,
- downstream applications.

---

## 7. Naming conventions

Recommended dataset naming pattern:

```text
<domain>_raw
<domain>
<domain>_products
```

Examples:

```text
sales_raw
sales
sales_products
```

```text
logistics_raw
logistics_curated
logistics_products
```

Marketing currently uses a different but still clear naming pattern:

```text
marketing_raw
marketing_silver
marketing_published
```

This is acceptable as long as the published layer is clearly identified.

Catalog is a special shared domain:

```text
catalog_raw
catalog
```

The curated `catalog.books` table is already a shared product.

If Catalog later publishes additional derived products, a separate dataset such as `catalog_products` may be considered, but it is not required for the current scope.

---

## 8. Access model

### Human consumers

Human consumers of a published product should receive:

- `roles/bigquery.dataViewer` on the published dataset,
- `roles/bigquery.jobUser` on the project where they execute queries, if required.

They should not receive broad project-level `roles/viewer` only to consume one dataset.

### Service account consumers

If a virtual code environment, Airflow task or other automated tool uses a service account, that service account must receive the same product-level access as a human consumer.

Example member format:

```text
serviceAccount:<service-account-email>
```

### Domain owners

Domain owners may receive broader access to their own domain project, for example:

- editor access during development,
- data editor access on raw/internal datasets,
- permission to manage their own domain resources.

### Pipeline / Airflow service accounts

Automated pipelines should use service accounts rather than personal Gmail accounts.

A future Airflow or Cloud Composer service account will need permissions to:

- run BigQuery jobs,
- read required upstream products,
- write to raw/internal/published datasets owned by the pipeline's domain,
- access relevant Cloud Storage buckets.

These permissions should be managed with Terraform where possible.

---

## 9. Recommended contract checklist

Before a domain publishes a data product, it should document:

- product owner,
- table location,
- grain,
- primary key or logical key columns,
- main columns,
- refresh frequency,
- upstream dependencies,
- intended consumers,
- access model,
- whether the product is implemented, planned or confirmed,
- quality rules,
- breaking change policy.

This keeps cross-domain dependencies explicit and reduces accidental coupling to raw or internal tables.

---

## 10. Current stable products for other teams

Other teams can currently use the following implemented products.

### Catalog

```text
publishing-mesh-project.catalog.books
```

### Sales

```text
publishing-mesh-sales.sales_products.sales_daily_summary
publishing-mesh-sales.sales_products.top_products
publishing-mesh-sales.sales_products.book_daily_sales
```

### Logistics

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

### Marketing

Confirmed published products identified by the Marketing domain:

```text
data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_performance
data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_daily_performance
data-mesh-marketing.marketing_dbt_dev_marketing_published.pub_campaign_sales_attribution
```

Cross-domain access, dataset naming and publication status are treated as confirmed for the current project scope.

---

## 11. Summary

The current data mesh design is based on explicit data products rather than unrestricted access to raw or internal tables.

The implemented pattern is:

```text
Catalog publishes books.
Logistics publishes inventory_by_book.
Sales consumes Catalog and Logistics.
Sales publishes sales_daily_summary, top_products and book_daily_sales.
Other users consume Sales through sales_products.
```

Future Marketing work should follow the same principle:

```text
domain_raw -> internal/curated layer -> published products
```

Known Marketing implementation appears to follow a similar pattern, but final published dataset names and product grains still require confirmation.

The next integration steps are:

1. use confirmed Marketing products in cross-domain demo queries,
2. optionally add `catalog.book_price_history`,
3. document and test the end-to-end demo flow,
4. keep cross-domain consumers on published products only.
