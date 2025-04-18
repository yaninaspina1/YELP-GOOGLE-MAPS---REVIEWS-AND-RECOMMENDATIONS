"""DAG maestro

¿Qué hace?
Preparar el script de carga a GCS como función reutilizable.
Crear el DAG de Airflow (pipeline_dag.py) que:
Ejecuta el ETL
Sube los archivos .parquet generados al bucket del Data Lake (datalake-restaurantes-2025)
(más adelante) ejecutará la carga al DW y modelos de ML"""


from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
from google.cloud import storage

# Configuración
LOCAL_PARQUET_FOLDER = "/opt/airflow/data_lake/"
GCP_BUCKET_NAME = "datalake-restaurantes-2025"
GCP_CREDENTIALS = "/opt/airflow/keys/keyfile.json"  # Ruta DENTRO del contenedor

default_args = {
    "owner": "harry",
    "start_date": datetime(2025, 4, 1),
    "retries": 1,
}

dag = DAG(
    "pipeline_etl_to_gcs",
    default_args=default_args,
    description="Pipeline ETL + carga al Data Lake en GCS",
    schedule_interval="@daily",
    catchup=False,
)

# Función para subir archivos .parquet a GCS
def upload_parquet_files_to_gcs():
    print(f"📁 Buscando archivos en: {LOCAL_PARQUET_FOLDER}")
    files = [f for f in os.listdir(LOCAL_PARQUET_FOLDER) if f.endswith(".parquet")]

    if not files:
        print("⚠️ No se encontraron archivos .parquet para subir.")
        return

    client = storage.Client.from_service_account_json(GCP_CREDENTIALS)
    bucket = client.bucket(GCP_BUCKET_NAME)

    for file_name in files:
        local_path = os.path.join(LOCAL_PARQUET_FOLDER, file_name)
        blob = bucket.blob(file_name)
        blob.upload_from_filename(local_path)
        print(f"✅ Archivo subido a GCS: {file_name}")

# Tarea 1: Subir archivos .parquet a GCS
upload_task = PythonOperator(
    task_id="upload_to_gcs",
    python_callable=upload_parquet_files_to_gcs,
    dag=dag,
)

upload_task


"""Integración del modelo al DAG"""

from airflow.operators.bash import BashOperator

# Tarea 1: Subir archivos al Data Lake (GCS)
upload_task = PythonOperator(
    task_id="upload_to_gcs",
    python_callable=upload_parquet_files_to_gcs,
    dag=dag,
)

# Tarea 2: Ejecutar entrenamiento del modelo ML
train_model_task = BashOperator(
    task_id="train_sentiment_model",
    bash_command="python /opt/airflow/ml/train_sentiment.py",
    dag=dag,
)

# Flujo: primero subir a GCS, luego entrenar modelo
upload_task >> train_model_task

"""Modificaciones para flujo de DAG's"""

# 📁 dags/pipeline_dag.py

from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime

default_args = {
    "owner": "harry",
    "start_date": datetime(2025, 4, 1),
    "retries": 1,
}

dag = DAG(
    "pipeline_dag",
    default_args=default_args,
    description="DAG maestro que orquesta los DAGs de ETL, DW y ML",
    schedule_interval=None,
    catchup=False,
)

# Tarea 1: Ejecutar el DAG de ETL (etl_dag)
trigger_etl = TriggerDagRunOperator(
    task_id="trigger_etl_dag",
    trigger_dag_id="etl_dag",  # Debe coincidir con el dag_id dentro del archivo etl_dag.py
    dag=dag,
)

# Tarea 2: Ejecutar el DAG de DW (dw_dag)
trigger_dw = TriggerDagRunOperator(
    task_id="trigger_dw_dag",
    trigger_dag_id="dw_dag",
    dag=dag,
)

# Tarea 3: Ejecutar el DAG de ML training (ml_training_dag)
trigger_ml_training = TriggerDagRunOperator(
    task_id="trigger_ml_training_dag",
    trigger_dag_id="ml_training_dag",
    dag=dag,
)

# Flujo completo
trigger_etl >> trigger_dw >> trigger_ml_training






