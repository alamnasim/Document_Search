#!/bin/bash
# Quick start script for ingestion pipeline

echo "=================================="
echo "🚀 Document Ingestion Pipeline"
echo "=================================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check if setup test should be run
if [ "$1" == "--skip-test" ]; then
    echo "  Skipping setup validation..."
    echo ""
else
    echo "📋 Running setup validation first..."
    echo ""
    python3 setup_test.py
    
    if [ $? -ne 0 ]; then
        echo ""
        echo " Setup validation failed. Please fix the issues above."
        echo ""
        echo "To skip validation and run anyway, use:"
        echo "  ./start.sh --skip-test"
        echo ""
        exit 1
    fi
    
    echo ""
    read -p " Validation passed. Start ingestion? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo " Cancelled by user"
        exit 0
    fi
fi

echo ""
echo "🚀 Starting ingestion service..."
echo ""

# Run ingestion
python3 run_ingestion.py
