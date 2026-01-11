# airflow/Dockerfile
FROM apache/airflow:2.8.1

# The path is now simpler because the build context will be the 'airflow' directory
COPY requirements.txt .

# Install the postgres and celery providers
RUN pip install --no-cache-dir -r requirements.txt