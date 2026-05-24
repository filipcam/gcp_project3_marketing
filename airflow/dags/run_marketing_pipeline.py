from datetime import datetime, timedelta

from airflow import DAG
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
    start_date=datetime(2026, 5, 17),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["marketing", "generator", "dbt", "gcp"],
) as dag:

    # ── 1. GENERATE DATA ──────────────────────────────────────────────────────
    run_generator = BashOperator(
        task_id="run_generator_marketing",
        bash_command="""
        python3 /config/workspace/gcp_project3_marketing/data_generator/generator_marketing.py \
          --load-date {{ ds }} \
          --num-campaigns 4 \
          --books-min 20 \
          --books-max 80 \
          --project-id data-mesh-marketing \
          --bucket data-mesh-marketing-project3-bucket \
          --catalog-table publishing-mesh-project.catalog.books \
          --campaigns-table data-mesh-marketing.marketing_raw.ext_marketing_campaigns
        """,
    )

    # ── 2. VALIDATE RAW EXTERNAL TABLES ──────────────────────────────────────
    check_campaigns = BashOperator(
        task_id="check_ext_marketing_campaigns",
        bash_command="""
        COUNT=$(bq query --nouse_legacy_sql --project_id=data-mesh-marketing --format=csv \
          "SELECT COUNT(*) FROM \`data-mesh-marketing.marketing_raw.ext_marketing_campaigns\` \
           WHERE load_date = '{{ ds }}'" | tail -1)
        echo "Row count: $COUNT"
        [ "$COUNT" -gt 0 ] || { echo "ERROR: No data for {{ ds }}"; exit 1; }
        """,
    )

    check_products = BashOperator(
        task_id="check_ext_marketing_campaign_products",
        bash_command="""
        COUNT=$(bq query --nouse_legacy_sql --project_id=data-mesh-marketing --format=csv \
          "SELECT COUNT(*) FROM \`data-mesh-marketing.marketing_raw.ext_marketing_campaign_products\` \
           WHERE load_date = '{{ ds }}'" | tail -1)
        echo "Row count: $COUNT"
        [ "$COUNT" -gt 0 ] || { echo "ERROR: No data for {{ ds }}"; exit 1; }
        """,
    )

    check_daily_metrics = BashOperator(
        task_id="check_ext_marketing_campaign_daily_metrics",
        bash_command="""
        COUNT=$(bq query --nouse_legacy_sql --project_id=data-mesh-marketing --format=csv \
          "SELECT COUNT(*) FROM \`data-mesh-marketing.marketing_raw.ext_marketing_campaign_daily_metrics\` \
           WHERE load_date = '{{ ds }}'" | tail -1)
        echo "Row count: $COUNT"
        [ "$COUNT" -gt 0 ] || { echo "ERROR: No data for {{ ds }}"; exit 1; }
        """,
    )

    # ── 3. DBT RUN — curated layer ────────────────────────────────────────────
    # stg_marketing_campaigns, stg_marketing_campaign_products,
    # stg_marketing_campaign_daily_metrics, stg_book_daily_sales,
    # int_campaign_performance
    dbt_run_curated = BashOperator(
        task_id="dbt_run_curated",
        bash_command="""
        cd /config/workspace/gcp_project3_marketing/dbt/marketing_dbt && \
        dbt run \
          --profiles-dir /config/workspace/gcp_project3_marketing/dbt/marketing_dbt \
          --select curated \
          --vars '{"load_date": "{{ ds }}"}'
        """,
    )

    # ── 4. DBT RUN — published layer ──────────────────────────────────────────
    # pub_campaign_performance, pub_campaign_daily_performance,
    # pub_campaign_sales_attribution
    dbt_run_published = BashOperator(
        task_id="dbt_run_published",
        bash_command="""
        cd /config/workspace/gcp_project3_marketing/dbt/marketing_dbt && \
        dbt run \
          --profiles-dir /config/workspace/gcp_project3_marketing/dbt/marketing_dbt \
          --select published \
          --vars '{"load_date": "{{ ds }}"}'
        """,
    )

    # ── 5. DBT TEST — quality gate ────────────────────────────────────────────
    dbt_test = BashOperator(
        task_id="dbt_test_marketing",
        bash_command="""
        cd /config/workspace/gcp_project3_marketing/dbt/marketing_dbt && \
        dbt test \
          --profiles-dir /config/workspace/gcp_project3_marketing/dbt/marketing_dbt \
          --select curated published \
          --vars '{"load_date": "{{ ds }}"}'
        """,
    )

    # ── DEPENDENCIES ──────────────────────────────────────────────────────────
    run_generator >> [check_campaigns, check_products, check_daily_metrics]
    [check_campaigns, check_products, check_daily_metrics] >> dbt_run_curated
    dbt_run_curated >> dbt_run_published
    dbt_run_published >> dbt_test