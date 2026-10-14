# Operational Runbook — Publishing Mesh Project

## 1. Purpose

This document describes the basic operational procedures for handling failures in the Publishing Mesh Project.

It covers issues related to:

* data generators,
* CSV files and Google Cloud Storage uploads,
* BigQuery raw tables,
* dbt models and dbt tests,
* Airflow DAG execution,
* cross-domain dependencies,
* demo data reset and recovery.

The runbook does not assume that every recovery action is fully automated. Its purpose is to define what should be checked, when a pipeline should be stopped, when data should be cleaned up, and how a correct state can be rebuilt safely.

---

## 2. Scope

This runbook applies to the following domains:

* Catalog,
* Sales,
* Logistics,
* Marketing,
* cross-domain demo flows.

It covers the following layers:

* source CSV files,
* Google Cloud Storage staging paths,
* BigQuery raw tables,
* dbt curated models,
* published data products,
* Airflow DAGs.

---

## 3. Main operational principles

1. **Do not publish incorrect data.**
   If a generator, load step, dbt run, or dbt test indicates a problem, the resulting data product should not be treated as successfully published.

2. **Consume published data products, not raw or internal tables.**
   Cross-domain dependencies should use published products only.

3. **Create a backup before manual cleanup.**
   This is especially important for BigQuery raw tables and published products.

4. **Raw data can be rebuilt from source files only if the correct batch is known.**
   GCS is used as a staging/archive layer, but incorrect batches should not be blindly reloaded.

5. **dbt tests are part of the publication criteria.**
   A product should not be considered ready if the relevant dbt tests fail.

6. **Domain pipelines may run independently.**
   A single global DAG is not required, as long as the published products are created in the agreed business order.

7. **Cross-domain demo steps should be skipped if an upstream product is missing or invalid.**
   It is better to show a stable partial flow than to rely on raw/internal fallback tables.

---

## 4. Failure scenarios and recommended actions

| Problem                             | Example                                                                 | Recommended action                                                           |
| ----------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Invalid input data                  | CSV has wrong schema, missing keys, negative values                     | Stop the pipeline, fix the input data, rerun the affected step               |
| Generator produces invalid data     | Catalog reseeds books from `book_id = 1`; Sales sells unavailable books | Do not load the generated file to raw; fix the generator; test locally       |
| GCS upload fails                    | CSV is not copied to the expected bucket path                           | Check bucket name, permissions, file path, and retry the upload              |
| BigQuery load fails                 | `bq load` fails because of schema or permission issues                  | Check the CSV file, table schema, project, dataset, and IAM permissions      |
| dbt run fails                       | SQL model does not compile; source table is missing                     | Fix the model or source configuration; do not publish downstream products    |
| dbt tests fail                      | Nulls, duplicates, broken grain, invalid values                         | Investigate raw data and model logic; stop dependent pipelines               |
| DAG did not run                     | No daily batch for a required date                                      | Trigger the DAG manually for the missing date                                |
| DAG ran for the wrong date          | Data was loaded with an incorrect `load_date`                           | Back up affected tables, delete the incorrect date range, rebuild dbt models |
| Incorrect batch already reached raw | Bad Catalog seed loaded into `catalog_raw.books`                        | Back up raw, delete the bad batch, rebuild curated/published models          |
| Upstream product missing            | `inventory_by_book` is missing for the required date                    | Do not run dependent Sales/Marketing steps; fix or rerun the upstream domain |
| Access denied                       | Another domain cannot read a product                                    | Verify whether access should be granted to the published dataset only        |

---

## 5. General incident procedure

1. **Identify where the failure happened**

   * generator,
   * GCS upload,
   * BigQuery load,
   * dbt run,
   * dbt test,
   * Airflow DAG,
   * missing upstream product.

2. **Inspect logs**

   * Airflow task logs,
   * shell script output,
   * `dbt run` / `dbt test` output,
   * BigQuery error messages.

3. **Stop dependent domains if the upstream product is invalid**
   Example: if `catalog.books` is invalid, Sales should not generate new sales data based on it.

4. **Back up data before manual cleanup**

   Example:

   ```bash
   bq cp \
     publishing-mesh-project:catalog_raw.books \
     publishing-mesh-project:catalog_raw.books_backup_before_cleanup_YYYYMMDD
   ```

5. **Delete only the affected data range**
   Prefer cleanup by `load_date`, `sales_date`, `snapshot_date`, or another clear batch/date column.

6. **Rebuild dbt models**
   After cleanup, run the relevant `dbt run` and `dbt test` commands.

7. **Validate the published product**
   Check row counts, dates, grain uniqueness, and basic business values.

---

## 6. Catalog domain procedures

### 6.1 Problem: Catalog generator reseeds the catalog

Symptoms:

* `catalog/books.csv` contains around 100 records again,
* `catalog_raw.books` contains new rows for `book_id` 1–100 with different titles or ISBNs,
* `catalog.books` shows different books for previously existing `book_id` values.

Likely cause:

* the generator failed to read existing data from BigQuery and incorrectly treated the catalog as empty.

Expected safeguard:

* the generator should fail if reading `catalog.books` from BigQuery fails;
* it should not silently reseed the catalog after a BigQuery read error.

Recovery procedure:

1. Back up `catalog_raw.books`.

2. Delete the incorrect batch from `catalog_raw.books`, usually by `load_date` or another clear identifier.

3. Rebuild Catalog models:

   ```bash
   cd dbt/publishing_mesh_dbt
   dbt run --target shared --select models/catalog
   dbt test --target shared --select models/catalog
   ```

4. Validate `catalog.books`:

   ```bash
   bq query --use_legacy_sql=false '
   SELECT
     COUNT(*) AS rows_count,
     COUNT(DISTINCT book_id) AS distinct_books,
     MIN(book_id) AS min_book_id,
     MAX(book_id) AS max_book_id
   FROM `publishing-mesh-project.catalog.books`
   '
   ```

---

## 7. Sales domain procedures

### 7.1 Problem: Sales generates orders for unavailable books

Business rule:

* Sales for date `D` should use the Logistics inventory snapshot from date `D - 1`.

Expected product used by Sales:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

Expected safeguards:

* Sales should generate order items only for books with `total_stock_available > 0` in the previous-day snapshot.
* Sales should not sell more units of a given book than the available stock from that snapshot.
* Sales should fail if the required Logistics snapshot is missing.

Validation query:

```bash
bq query --use_legacy_sql=false '
SELECT
  snapshot_date,
  COUNT(*) AS rows_count,
  COUNT(DISTINCT book_id) AS distinct_books
FROM `publishing-mesh-logistics.logistics_products.inventory_by_book`
GROUP BY snapshot_date
ORDER BY snapshot_date
'
```

If the snapshot for `D - 1` does not exist, Sales for date `D` should not be generated.

---

## 8. Logistics domain procedures

### 8.1 Expected published product: `inventory_by_book`

Expected location:

```text
publishing-mesh-logistics.logistics_products.inventory_by_book
```

Expected grain:

```text
1 row = 1 snapshot_date + 1 book_id
```

Expected columns:

* `snapshot_date`,
* `book_id`,
* `total_stock_on_hand`,
* `total_stock_reserved`,
* `total_stock_available`,
* `warehouses_count`.

Schema check:

```bash
bq show --schema --format=prettyjson \
  publishing-mesh-logistics:logistics_products.inventory_by_book
```

Grain validation:

```bash
bq query --use_legacy_sql=false '
SELECT
  snapshot_date,
  book_id,
  COUNT(*) AS rows_count
FROM `publishing-mesh-logistics.logistics_products.inventory_by_book`
GROUP BY snapshot_date, book_id
HAVING COUNT(*) > 1
LIMIT 20
'
```

If this query returns any rows, the product grain is violated.

---

## 9. Marketing domain procedures

### 9.1 Problem: Marketing product names or structures change

Marketing may publish products such as:

* campaign performance,
* campaign daily performance,
* campaign sales attribution,
* campaign-to-book mapping.

Procedure before using a Marketing product:

1. Confirm the published dataset name.
2. Confirm the final table name.
3. Confirm the grain.
4. Confirm integration keys, for example:

   * `campaign_id`,
   * `book_id`,
   * campaign date,
   * sales date.
5. Confirm whether the product is stable enough for cross-domain use.

Until the contract is confirmed, Sales should not depend on Marketing products.

---

## 10. Demo data reset procedure

Before replaying the demo flow from a specific date, the team may need to clean up existing demo data from that date onward.

Example:

```bash
export RESET_DATE=2026-05-18
```

### 10.1 Catalog raw cleanup

```bash
bq query --use_legacy_sql=false "
DELETE FROM \`publishing-mesh-project.catalog_raw.books\`
WHERE load_date >= DATE '${RESET_DATE}'
"
```

### 10.2 Sales raw cleanup

```bash
bq query --use_legacy_sql=false "
DELETE FROM \`publishing-mesh-sales.sales_raw.orders\`
WHERE load_date >= DATE '${RESET_DATE}'
"
```

```bash
bq query --use_legacy_sql=false "
DELETE FROM \`publishing-mesh-sales.sales_raw.order_items\`
WHERE load_date >= DATE '${RESET_DATE}'
"
```

### 10.3 Rebuild dbt models after cleanup

```bash
cd dbt/publishing_mesh_dbt

dbt run --target shared --select models/catalog
dbt test --target shared --select models/catalog

dbt run --target sales --select models/sales
dbt test --target sales --select models/sales
```

---

## 11. Minimal validation before demo

### 11.1 Catalog

```bash
bq query --use_legacy_sql=false '
SELECT
  COUNT(*) AS rows_count,
  COUNT(DISTINCT book_id) AS distinct_books,
  MIN(book_id) AS min_book_id,
  MAX(book_id) AS max_book_id
FROM `publishing-mesh-project.catalog.books`
'
```

### 11.2 Sales

```bash
bq query --use_legacy_sql=false '
SELECT
  sales_date,
  COUNT(*) AS rows_count
FROM `publishing-mesh-sales.sales_products.book_daily_sales`
GROUP BY sales_date
ORDER BY sales_date
'
```

### 11.3 Logistics

```bash
bq query --use_legacy_sql=false '
SELECT
  snapshot_date,
  COUNT(*) AS rows_count,
  COUNT(DISTINCT book_id) AS distinct_books
FROM `publishing-mesh-logistics.logistics_products.inventory_by_book`
GROUP BY snapshot_date
ORDER BY snapshot_date
'
```

### 11.4 Check that Sales demo dates are clean before replay

```bash
bq query --use_legacy_sql=false '
SELECT
  sales_date,
  COUNT(*) AS rows_count
FROM `publishing-mesh-sales.sales_products.book_daily_sales`
WHERE sales_date >= DATE "2026-05-18"
GROUP BY sales_date
ORDER BY sales_date
'
```

Expected result before replaying the demo: no rows.

---

## 12. What to do if an upstream product is not ready

If an upstream product is missing, invalid, or not accessible:

1. Do not run dependent demo steps.
2. Show the stable part of the flow.
3. Explain the missing product as a target integration point.
4. Do not replace a published product with another domain's raw or internal table unless explicitly agreed by the team.

Examples:

* If Logistics does not publish `inventory_by_book`, Sales should not generate inventory-aware sales data.
* If Marketing does not publish a stable attribution product, the demo can show Catalog + Logistics + Sales and describe Marketing as a planned integration step.

---

## 13. Data retention and cleanup policy

This section describes the recommended retention and cleanup approach for the Publishing Mesh Project.

The project currently focuses on demo and coursework implementation, so not every retention rule is automated yet. In a production setup, the retention policy should be implemented through a combination of:

- Google Cloud Storage lifecycle rules,
- BigQuery partition expiration,
- scheduled cleanup DAGs,
- documented manual cleanup procedures,
- Terraform-managed infrastructure rules where possible.

The main principle is:

> Temporary and technical data can be cleaned earlier, while published data products and business history should be retained longer.

### 13.1 Retention by layer and domain

| Domain | Layer / object type | Examples | Recommended retention | Cleanup approach | Notes |
|---|---|---|---|---|---|
| Catalog | Local generated files | `catalog/books.csv` | Working copy only | Do not rely on it as long-term storage | This file is overwritten by the generator and should not be treated as historical storage. |
| Catalog | GCS staging files | `gs://publishing-mesh-catalog-euc2/catalog/books/...` | 30–90 days | GCS lifecycle rule | Useful for debugging recent loads, but not required permanently. |
| Catalog | Raw BigQuery tables | `catalog_raw.books` | 1–2 years, or longer for audit/demo needs | Date-based cleanup where possible | Raw snapshots are useful for rebuilding `catalog.books` and deriving `book_price_history`. |
| Catalog | Published product | `catalog.books` | Long-term | Rebuilt by dbt; do not delete manually during normal operations | Shared book reference product used by other domains. |
| Catalog | Historical product | `catalog.book_price_history` | Long-term | Rebuilt by dbt from raw snapshots | Supports historical price analysis. |
| Sales | Local generated files | `sales/orders/load_date=...`, `sales/order_items/load_date=...` | Working copy only | Can be deleted locally after successful load | These files can be regenerated for demo dates if needed. |
| Sales | GCS staging files | `gs://publishing-mesh-sales-euc2/orders/...`, `gs://publishing-mesh-sales-euc2/order_items/...` | 30–90 days | GCS lifecycle rule | Keep recent files for debugging failed loads; expire older files. |
| Sales | Raw BigQuery tables | `sales_raw.orders`, `sales_raw.order_items` | 1–2 years minimum | Date-based cleanup by `load_date` | Supports rebuilding curated and published Sales products. |
| Sales | Internal curated tables | `sales.orders_curated`, `sales.order_items_curated` | Rebuildable | Rebuilt by dbt | Should be recreated from raw rather than manually edited. |
| Sales | Published products | `sales_products.book_daily_sales`, `sales_products.sales_daily_summary`, `sales_products.top_products` | 5–10 years, depending on analytical requirements | Prefer retention in published analytical layer | Sales history is business-critical and should be retained longer than staging/raw files. |
| Logistics | Local generated files | `logistics/inventory/load_date=...`, `logistics/shipments/load_date=...` | Working copy only | Can be deleted locally after successful load | Local files are technical artifacts. |
| Logistics | GCS staging files | Logistics inventory and shipment load batches | 30–90 days | GCS lifecycle rule | Keep recent batches for debugging; expire older technical files. |
| Logistics | Raw BigQuery tables | `logistics_raw.inventory`, `logistics_raw.shipments` | 6–24 months | Date-based cleanup by `load_date` or source date | Raw logistics snapshots may grow quickly. |
| Logistics | Internal curated tables | `logistics_curated.*` | Rebuildable | Rebuilt by dbt | Internal tables should not be consumed directly by other domains. |
| Logistics | Published inventory product | `logistics_products.inventory_by_book` | 1–3 years at detailed snapshot level | Keep detailed snapshots for a limited period; optionally aggregate older data | Daily inventory snapshots can grow over time. |
| Logistics | Published operational summaries | logistics daily summary products, if published | 3–5 years | Retain longer than detailed snapshots | Aggregated logistics metrics are cheaper to keep and useful for reporting. |
| Marketing | Local/generated files | campaign input extracts, local generated CSVs | Working copy only | Can be deleted after successful load | Local files should not be treated as the system of record. |
| Marketing | GCS staging files | campaign raw/staging uploads | 30–90 days | GCS lifecycle rule | Retain recent campaign loads for debugging. |
| Marketing | Raw BigQuery tables | `marketing_raw.*` | 1–2 years | Date-based cleanup if partitioned | Raw campaign events may be large and should have defined retention. |
| Marketing | Internal curated/silver tables | `marketing_silver.*` or equivalent | Rebuildable | Rebuilt by dbt | Internal Marketing tables should not be consumed cross-domain. |
| Marketing | Published products | `marketing_published.*` / confirmed campaign products | 3–5 years | Retain as analytical products | Campaign performance and attribution products support historical analysis. |
| Cross-domain demo | Demo-generated data | demo runs from specific dates such as `2026-05-18+` | Keep only if useful for presentation/audit | Manual reset by date range before replaying demo | Demo data can be cleaned more aggressively than business history. |
| Cross-domain analysis | Derived cross-domain outputs | future Sales + Logistics + Marketing analysis tables | 1–3 years, depending on purpose | Rebuild from source products if possible | Prefer rebuilding these from stable domain products rather than treating them as primary records. |

### 13.2 What should be cleaned first

The recommended cleanup order is:

1. **Local generated files**
   - safe to remove after successful load,
   - easy to regenerate,
   - not part of the official data product layer.

2. **Old GCS staging files**
   - useful for recent debugging,
   - should usually have lifecycle expiration,
   - should not be the only source of important business history.

3. **Incorrect raw batches**
   - remove only after backup,
   - remove only the affected date or batch,
   - rebuild dbt models after cleanup.

4. **Old raw partitions**
   - clean only according to agreed retention rules,
   - raw data is useful for rebuilding products and auditing ingestion.

5. **Published products**
   - do not delete casually,
   - they represent the stable consumption layer,
   - if incorrect, fix upstream data and rebuild with dbt.

### 13.3 What should not be cleaned without team agreement

Do not delete the following without explicit team agreement:

- `catalog.books`,
- `catalog.book_price_history`,
- `sales_products.book_daily_sales`,
- `sales_products.sales_daily_summary`,
- `sales_products.top_products`,
- `logistics_products.inventory_by_book`,
- confirmed Marketing published products,
- raw data needed to rebuild published products,
- data required for the final presentation/demo.

### 13.4 Recommended implementation mechanisms

| Mechanism | Applies to | Purpose |
|---|---|---|
| GCS lifecycle rules | staging CSV files in buckets | Automatically delete old technical files after 30–90 days. |
| BigQuery partition expiration | partitioned raw tables and large snapshot tables | Automatically expire old raw/snapshot data. |
| Scheduled cleanup DAG | demo data and controlled cleanup windows | Execute repeatable cleanup logic with logs and date parameters. |
| Manual cleanup with backup | incident recovery | Used when a bad batch was loaded and must be removed safely. |
| Terraform | buckets, datasets, IAM, lifecycle rules | Manage retention-related infrastructure as code. |
| dbt rebuild | curated and published products | Recreate product tables after raw cleanup or logic fixes. |

### 13.5 Demo cleanup policy

For demo purposes, the team may clean data from a specific date onward before replaying the flow.

Example:

```bash
export RESET_DATE=2026-05-18
```

The current demo cleanup approach is:

- clean Catalog raw data from `RESET_DATE` onward only if Catalog demo data needs to be replayed,
- clean Sales raw data from `RESET_DATE` onward before replaying Sales demo,
- rebuild Catalog and Sales dbt models after cleanup,
- keep older test data unless it interferes with the demo,
- avoid deleting GCS staging files unless necessary.

GCS staging files from previous runs do not affect the demo as long as they are not reloaded into BigQuery.

### 13.6 Future improvement

A future production-ready implementation should include:

- lifecycle rules for all staging buckets,
- partitioning and expiration strategy for raw BigQuery tables,
- scheduled cleanup DAGs for demo and non-production data,
- documented retention requirements per domain,
- Terraform-managed retention configuration,
- monitoring or alerts when expected daily data is missing.

---

## 14. Data quality and tests

This section summarizes the main data quality checks used or expected in the project.

The project uses two types of validation:

- **dbt tests** defined in model YAML files,
- **manual or operational validation queries** used in the runbook and demo checks.

The general rule is:

> If dbt tests or key validation queries fail, the affected product should not be treated as successfully published.

### 14.1 Data quality checks by domain

| Domain | Product / layer | Check type | Columns / rule | Tool / approach |
|---|---|---|---|---|
| Catalog | `catalog.books` | Not null checks | `book_id`, `isbn`, `title`, `author_name`, `publisher_name`, `category`, `format`, `publication_date`, `list_price`, `load_date` | dbt tests |
| Catalog | `catalog.books` | Uniqueness | one current row per `book_id` | dbt test on `book_id` |
| Catalog | `catalog.book_price_history` | Not null checks | `book_id`, `list_price`, `currency`, `valid_from`, `is_current` | dbt tests |
| Catalog | `catalog.book_price_history` | Current price consistency | at most one `is_current = true` record per `book_id` | validation query / future custom dbt test |
| Sales | `sales.orders_curated` | Not null checks | key order fields such as `order_id`, `order_date`, `load_date` | dbt tests |
| Sales | `sales.order_items_curated` | Not null checks | `order_item_id`, `order_id`, `book_id`, `quantity`, `unit_price`, `line_amount`, `load_date` | dbt tests |
| Sales | `sales_products.book_daily_sales` | Not null checks | `sales_date`, `book_id`, `items_sold`, `gross_sales_amount` | dbt tests |
| Sales | `sales_products.book_daily_sales` | Grain check | one row per `sales_date + book_id` | dbt test / validation query |
| Sales | generator | Business rule | generated sales must not exceed available stock from Logistics snapshot `D-1` | generator logic + validation query |
| Logistics | `logistics_products.inventory_by_book` | Grain check | one row per `snapshot_date + book_id` | validation query |
| Logistics | `logistics_products.inventory_by_book` | Non-negative values | `total_stock_on_hand >= 0`, `total_stock_reserved >= 0`, `total_stock_available >= 0` | dbt test expected / validation query |
| Logistics | `logistics_products.inventory_by_book` | Business consistency | `total_stock_reserved <= total_stock_on_hand` | dbt test expected / validation query |
| Marketing | `pub_campaign_performance` | Key check | `campaign_id` should not be null | dbt test expected |
| Marketing | `pub_campaign_daily_performance` | Grain check | one row per `campaign_id + event_date` | dbt test expected / validation query |
| Marketing | `pub_campaign_sales_attribution` | Referential check | campaign attribution should reference valid campaigns and books | dbt test expected / validation query |
| Cross-domain | Catalog → Sales | Referential consistency | Sales `book_id` should exist in `catalog.books` | dbt relationship test expected |
| Cross-domain | Logistics → Sales | Availability rule | Sales for date `D` uses Logistics snapshot from `D-1` | validation query |
| Cross-domain | Marketing → Sales | Attribution consistency | campaign-related sales analysis should use confirmed Marketing published products | contract + validation query |

### 14.2 Example validation queries

Check that `book_price_history` has at most one current price per book:

```bash
bq query --use_legacy_sql=false '
SELECT
  book_id,
  COUNT(*) AS current_rows
FROM `publishing-mesh-project.catalog.book_price_history`
WHERE is_current = true
GROUP BY book_id
HAVING COUNT(*) > 1
'
```

Check that Sales did not sell more than available Logistics stock:

```bash
bq query --use_legacy_sql=false '
WITH sales AS (
  SELECT
    sales_date,
    book_id,
    SUM(items_sold) AS items_sold
  FROM `publishing-mesh-sales.sales_products.book_daily_sales`
  WHERE sales_date = DATE "2026-05-19"
  GROUP BY sales_date, book_id
),
inventory AS (
  SELECT
    snapshot_date,
    book_id,
    total_stock_available
  FROM `publishing-mesh-logistics.logistics_products.inventory_by_book`
  WHERE snapshot_date = DATE "2026-05-18"
)
SELECT
  s.sales_date,
  i.snapshot_date,
  s.book_id,
  s.items_sold,
  i.total_stock_available
FROM sales s
JOIN inventory i
  ON s.book_id = i.book_id
WHERE s.items_sold > i.total_stock_available
'
```

Expected result: no rows.

### 14.3 Future improvement

Future improvements may include:

- custom dbt tests for grain validation,
- dbt relationship tests between domain products,
- automated cross-domain validation DAGs,
- alerts when expected daily products are missing,
- data quality checks managed consistently across domains.

---

## 15. Summary

The operational rules for the project are:

* each domain owns its data,
* cross-domain consumers use published data products only,
* invalid data should not be published,
* backups should be created before manual cleanup,
* dbt models should be rebuilt and tested after cleanup,
* missing daily data should be fixed by rerunning the relevant DAG for the correct date,
* the cross-domain demo should use stable, published products only.
