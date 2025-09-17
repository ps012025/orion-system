# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for Flask
ENV APP_HOME /app
ENV FLASK_APP main.py
WORKDIR $APP_HOME

# Install gunicorn for production server
RUN pip install gunicorn

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY main.py .

# Run the web server on container startup
# Use the PORT environment variable provided by Cloud Run
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
