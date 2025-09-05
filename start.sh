#!/bin/bash

# Bulk DOCX to PDF Converter - Launch Script

echo "Starting Bulk DOCX to PDF Converter Service"
echo "=============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not available. Please install Docker with Compose plugin."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ".env file created. You can edit it to customize settings."
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if API is responding
max_attempts=30
attempt=0

echo "🔍 Checking if API is ready..."
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo " API is ready!"
        break
    else
        echo "   Waiting... (attempt $((attempt + 1))/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo " API failed to start. Check logs with: docker compose logs"
    exit 1
fi

echo ""
echo "🎉 Bulk DOCX to PDF Converter is now running!"
echo ""
echo "📋 Service Information:"
echo "   • API Endpoint:     http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Flower Monitoring: http://localhost:5555"
echo ""
echo "🔧 Management Commands:"
echo "   • View logs:        docker compose logs -f"
echo "   • Stop service:     docker compose down"
echo "   • Restart service:  docker compose restart"
echo "   • Scale workers:    docker compose up --scale worker=4"
echo ""
echo "🧪 Testing:"
echo "   • Run test script:  python3 test_service.py"
echo ""
echo "📚 For more information, see README.md"
