#!/bin/bash
mkdir -p /config/airflow/dags/
cp airflow.cfg /config/airflow/airflow.cfg
cp webserver_config.py /config/airflow/webserver_config.py
cp -R dags/* /config/airflow/dags
# Secret keys: use values from the environment if provided, otherwise generate random ones per start
export AIRFLOW__WEBSERVER__SECRET_KEY="${AIRFLOW__WEBSERVER__SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}"
export AIRFLOW__CORE__INTERNAL_API_SECRET_KEY="${AIRFLOW__CORE__INTERNAL_API_SECRET_KEY:-$AIRFLOW__WEBSERVER__SECRET_KEY}"
airflow db migrate
airflow standalone