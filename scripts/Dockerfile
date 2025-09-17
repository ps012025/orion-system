# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script into the container at /app
COPY run_alpha_loop.py .

# Set the GOOGLE_CLOUD_PROJECT environment variable (can be overridden at runtime)
# This is a placeholder and should be set by the Vertex AI Custom Job environment
ENV GOOGLE_CLOUD_PROJECT="project-orion-admins"

# Define the command to run the script
CMD ["python", "run_alpha_loop.py"]
