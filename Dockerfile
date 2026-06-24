# Use the official lightweight Python image.
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file from the sub-folder to the root
COPY BeHazeld_OS_Backend/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Set the PYTHONPATH so Python can find the 'app' module inside the sub-folder
ENV PYTHONPATH=/app/BeHazeld_OS_Backend

# Expose the port the app runs on
EXPOSE 8000

# Start the application using uvicorn.
# Railway injects PORT dynamically; fall back to 8000 for local Docker runs.
CMD ["sh", "-c", "uvicorn BeHazeld_OS_Backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
