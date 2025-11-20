FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY WEBAPI/requirements.txt WEBAPI/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r WEBAPI/requirements.txt && \
    pip install --no-cache-dir python-multipart

# Copy the rest of the application
COPY . .

# Install the application package
RUN pip install .

# Ensure the serve script is executable
RUN chmod +x WEBAPI/serve.sh

# Expose the port the app runs on
EXPOSE 9000

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=9000
ENV PYTHONPATH=/app

# Command to run the application
CMD ["./WEBAPI/serve.sh"]
