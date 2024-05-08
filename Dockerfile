# Use a slim version of the Python image based on Ubuntu
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install the Python packages listed in requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the dagster_tutorial directory contents into the container at /app
COPY ./dagster_tutorial /app/dagster_tutorial
RUN rm -rf /app/dagster_tutorial/logs
# Create empty logs directory
RUN mkdir /app/dagster_tutorial/logs

# Copy the supervisord configuration file into the container
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set the new working directory to the dagster_tutorial
WORKDIR /app/dagster_tutorial

# Install project dependencies
RUN pip install -e .
ENV DAGSTER_HOME=/app/dagster_tutorial

# Expose the port the Dagster webserver runs on
EXPOSE 3001

# Expose the port the Streamlit app runs on
EXPOSE 8502

# Initialize the SQLite database for ingest (at build time rather than run time)
RUN python docker_setup/duckdb_setup.py

# Start supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# build: docker build -t dagster_tutorial .
# run: docker run -p 3001:3001 -p 8502:8502 dagster_tutorial
