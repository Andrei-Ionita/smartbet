FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE 8000

# Create a script to run both web and worker processes
RUN echo '#!/bin/bash\n\
trap "exit" SIGINT SIGTERM\n\
nohup python manage.py qcluster > /app/logs/qcluster.log 2>&1 &\n\
python manage.py setup_scheduled_tasks\n\
gunicorn smartbet.wsgi:application --bind 0.0.0.0:8000' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs

# Run the startup script
CMD ["/app/entrypoint.sh"] 