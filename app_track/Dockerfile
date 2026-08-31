FROM python:3.11-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Collect static files only — NO DATABASE MIGRATIONS HERE
RUN python manage.py collectstatic --no-input

# Expose port
EXPOSE 8000

# Make startup script executable
RUN chmod +x start.sh

# Start: run migrations then launch the app
CMD ["bash", "start.sh"]

