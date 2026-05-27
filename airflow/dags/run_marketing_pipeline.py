from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="run_marketing_pipeline",
    description="Marketing domain pipeline: generate → validate raw → dbt run → dbt test",
    start_date=datetime(2026, 5, 19),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["marketing", "generator", "dbt", "gcp"],
    params={
        "load_date": Param(
            default="",
            type="string",
            description="Override load date (YYYY-MM-DD). Leave empty to use DAG logical date (ds).",
        )
    },
) as dag:

    # ── 1. GENERATE DATA ──────────────────────────────────────────────────────
    run_generator = BashOperator(
        task_id="run_generator_marketing",
        bash_command="""
        LOAD_DATE="{{ params.load_date or ds }}"
        echo "Using load_date: $LOAD_DATE"

        python3 /config/workspace/gcp_project3_marketing/data_generator/generator_marketing.py \
          --load-date "$LOAD_DATE" \
          --num-campaigns 4 \
          --books-min 20 \
          --books-max 80 \
          --project-id data-mesh-marketing \
          --bucket data-mesh-marketing-project3-bucket \
          --inventory-table publishing-mesh-logistics.logistics_products.inventory_by_book \
          --campaigns-table data-mesh-marketing.marketing_raw.ext_marketing_campaigns
        """,
    )

    # ── 2. VALIDATE RAW EXTERNAL TABLES ──────────────────────────────────────
    check_campaigns = BashOperator(
        task_id="check_ext_marketing_campaigns",
        bash_command="""
        LOAD_DATE="{{ params.load_date or ds }}"
        COUNT=$(bq query --nouse_legacy_sql --project_id=data-mesh-marketing --format=csv \
          "SELECT COUNT(*) FROM \`data-mesh-marketing.marketing_raw.ext_marketing_campaigns\` \
           WHERE load_date = '$LOAD_DATE'" | tail -1)
        echo "Campaigns rows for $LOAD_DATE: $COUNT"
        [ "$COUNT" -gt 0 ] || { echo "ERROR: No campaigns data for $LOAD_DATE"; exit 1; }
        """,
    )

    check_products = BashOperator(
        task_id="check_ext_marketing_campaign_products",
        bash_command="""
        COUNT=$(bq query --nouse_legacy_sql --project_id=data-mesh-marketing --format=csv \
          "SELECT COUNT(*) FROM \`data-mesh-marketing.marketing_raw.ext_marketing_campaign_products\`" \
          | tail -1)
        echo "Total product rows in table: $COUNT"
        [ "$COUNT" -gt 0 ] || { echo "ERROR: marketing_campaign_products table is empty"; exit 1; }
        """,
    )

    check_daily_metrics = BashOperator(
        task_id="check_ext_marketing_campaign_daily_metrics",
        bash_command="""
        LOAD_DATE="{{ params.load_date or ds }}"
        COUNT=$(bq query --nouse_legacy_sql --project_id=data-mesh-marketing --format=csv \
          "SELECT COUNT(*) FROM \`data-mesh-marketing.marketing_raw.ext_marketing_campaign_daily_metrics\` \
           WHERE load_date = '$LOAD_DATE'" | tail -1)
        echo "Daily metrics rows for $LOAD_DATE: $COUNT"
        [ "$COUNT" -gt 0 ] || { echo "ERROR: No daily_metrics data for $LOAD_DATE"; exit 1; }
        """,
    )

    # ── 3. DBT RUN — curated layer ────────────────────────────────────────────
    dbt_run_curated = BashOperator(
        task_id="dbt_run_curated",
        bash_command="""
        LOAD_DATE="{{ params.load_date or ds }}"
        echo "dbt run curated for load_date: $LOAD_DATE"

        cd /config/workspace/gcp_project3_marketing/dbt/marketing_dbt && \
        dbt run \
          --profiles-dir /config/workspace/gcp_project3_marketing/dbt/marketing_dbt \
          --select curated \
          --vars "{\"load_date\": \"$LOAD_DATE\"}"
        """,
    )

    # ── 4. DBT RUN — published layer ──────────────────────────────────────────
    dbt_run_published = BashOperator(
        task_id="dbt_run_published",
        bash_command="""
        LOAD_DATE="{{ params.load_date or ds }}"
        echo "dbt run published for load_date: $LOAD_DATE"

        cd /config/workspace/gcp_project3_marketing/dbt/marketing_dbt && \
        dbt run \
          --profiles-dir /config/workspace/gcp_project3_marketing/dbt/marketing_dbt \
          --select published \
          --vars "{\"load_date\": \"$LOAD_DATE\"}"
        """,
    )

    # ── 5. DBT TEST — quality gate ────────────────────────────────────────────
    dbt_test = BashOperator(
        task_id="dbt_test_marketing",
        bash_command="""
        LOAD_DATE="{{ params.load_date or ds }}"
        echo "dbt test for load_date: $LOAD_DATE"

        cd /config/workspace/gcp_project3_marketing/dbt/marketing_dbt && \
        dbt test \
          --profiles-dir /config/workspace/gcp_project3_marketing/dbt/marketing_dbt \
          --select curated published \
          --vars "{\"load_date\": \"$LOAD_DATE\"}"
        """,
    )

    # ── DEPENDENCIES ──────────────────────────────────────────────────────────
    run_generator >> [check_campaigns, check_products, check_daily_metrics]
    [check_campaigns, check_products, check_daily_metrics] >> dbt_run_curated
    dbt_run_curated >> dbt_run_published
    dbt_run_published >> dbt_test