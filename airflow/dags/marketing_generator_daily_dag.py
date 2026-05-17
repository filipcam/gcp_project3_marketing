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
    dag_id="marketing_generator_daily",
    description="Run marketing generator with Airflow logical date as load_date",
    start_date=datetime(2026, 5, 17),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["marketing", "generator", "gcp"],
) as dag:

    run_generator_marketing = BashOperator(
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
          --campaigns-table data-mesh-marketing.marketing_raw.marketing_campaigns
        """,
    )