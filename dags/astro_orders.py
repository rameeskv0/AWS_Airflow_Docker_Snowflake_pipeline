from datetime import datetime
from airflow import DAG
from airflow.operators.email_operator import EmailOperator
from airflow.utils.email import send_email_smtp
from pandas import DataFrame
from astro import sql as aql
from astro.files import File
from astro.sql.table import Table
from airflow.hooks.base_hook import BaseHook

S3_FILE_PATH = "s3://airflow-snowflake-data"
S3_CONN_ID = "aws_default"
SNOWFLAKE_CONN_ID = "snowflake_default"
SNOWFLAKE_ORDERS = "orders_table"
SNOWFLAKE_FILTERED_ORDERS = "filtered_table"
SNOWFLAKE_JOINED = "joined_table"
SNOWFLAKE_CUSTOMERS = "customers_table"
SNOWFLAKE_REPORTING = "reporting_table"

@aql.transform
def filter_orders(input_table: Table):
    return "SELECT * FROM {{input_table}} WHERE amount > 150"

@aql.transform
def join_orders_customers(filtered_orders_table: Table, customers_table: Table):
    return """SELECT c.customer_id, customer_name, order_id, purchase_date, amount, type
    FROM {{filtered_orders_table}} f JOIN {{customers_table}} c
    ON f.customer_id = c.customer_id"""

@aql.dataframe
def transform_dataframe(df: DataFrame):
    purchase_dates = df.loc[:, "purchase_date"]
    print("purchase dates:", purchase_dates)
    return purchase_dates

def notify_email(context, success=True):
    dag_run = context['dag_run']
    task_instances = dag_run.get_task_instances()
    failed_tasks = [ti.task_id for ti in task_instances if ti.state == 'failed']
    subject = "DAG {dag_id} Success".format(dag_id=dag_run.dag_id) if success else "DAG {dag_id} Failed".format(dag_id=dag_run.dag_id)
    html_content = "DAG {dag_id} succeeded.".format(dag_id=dag_run.dag_id) if success else "DAG {dag_id} failed.<br>Failed Tasks: {tasks}".format(dag_id=dag_run.dag_id, tasks=", ".join(failed_tasks))
    send_email_smtp('0ramees0@gmail.com', subject, html_content)

with DAG(dag_id='astro_ytcode', start_date=datetime(2024, 5, 22), schedule_interval='@daily', catchup=False, default_args={
    'on_failure_callback': lambda context: notify_email(context, success=False)
}) as dag:
    orders_data = aql.load_file(
        input_file=File(path=S3_FILE_PATH + "/orders_data_headers.csv", conn_id=S3_CONN_ID),
        output_table=Table(conn_id=SNOWFLAKE_CONN_ID)
    )

    customers_table = Table(
        name=SNOWFLAKE_CUSTOMERS,
        conn_id=SNOWFLAKE_CONN_ID,
    )

    joined_data = join_orders_customers(filter_orders(orders_data), customers_table)

    reporting_table = aql.merge(
        target_table=Table(
            name=SNOWFLAKE_REPORTING,
            conn_id=SNOWFLAKE_CONN_ID),
        source_table=joined_data,
        target_conflict_columns=["order_id"],
        columns=["customer_id", "customer_name"],
        if_conflicts="update"
    )

    purchase_dates = transform_dataframe(reporting_table)

    send_success_email = EmailOperator(
        task_id='send_success_email',
        to='0ramees0@gmail.com',
        subject='DAG astro_ytcode Success',
        html_content='DAG astro_ytcode completed successfully.'
    )

    cleanup_task = aql.cleanup(
        task_id='cleanup'
    )

    purchase_dates >> send_success_email >> cleanup_task
