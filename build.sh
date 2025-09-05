#!/bin/bash

echo "Installing system dependencies..."
apt-get update
apt-get install -y libreoffice fonts-liberation fonts-dejavu

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Creating storage directories..."
mkdir -p /tmp/storage/{uploads,outputs,temp}

echo "Running database migrations..."
python -c "
from app.config.database import engine, Base
from app.models.models import ConversionJob, ConversionFile
Base.metadata.create_all(bind=engine)
print('Database tables created')
"

echo "Build completed successfully!"
