#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting SmartBet Backend Build..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

# NOTE: Database migrations should NOT run during build phase on Railway
# because the build environment cannot access the private database network.
# Migrations will be run as part of the start command in Procfile.

echo "✅ Build completed successfully!"
