from airflow import DAG
from airflow.operators.email_operator import EmailOperator
from datetime import datetime


default_args = {
  'owner': 'airflow',
  'email': ['0ramees0@gmail.com'], 
  'email_on_failure': True,
}

with DAG(
  dag_id='send_email_example',
  default_args=default_args,
  start_date=datetime(2024, 5, 24),
  schedule_interval=None,
) as dag:

  send_email = EmailOperator(
      task_id='send_email',
      to='0ramees0@gmail.com',
      subject='Airflow Example Email',
      html_content='<h3>This is a test email from Airflow!</h3>',
  )
