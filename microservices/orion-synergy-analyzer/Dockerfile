# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV APP_HOME /app
WORKDIR $APP_HOME

# Copy the application files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the web server on container startup
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
