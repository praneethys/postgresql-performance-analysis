#!/bin/bash
# Database Setup Script for PostgreSQL Performance Analysis

set -e

# Configuration
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-perf_analysis}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}

export PGPASSWORD=$DB_PASSWORD

echo "🔧 Setting up PostgreSQL database for performance analysis"
echo ""

# Check if Docker container is running
echo "Checking PostgreSQL container..."
if ! docker compose ps | grep -q "postgres-perf-analysis.*Up.*healthy"; then
    echo "✗ PostgreSQL container is not running or not healthy"
    echo "  Starting containers..."
    docker compose up -d
    echo "  Waiting for PostgreSQL to be ready..."
    sleep 10
fi

# Check PostgreSQL connection using docker exec
echo "Checking PostgreSQL connection..."
if ! docker exec postgres-perf-analysis pg_isready -U $DB_USER > /dev/null 2>&1; then
    echo "✗ PostgreSQL is not accessible"
    echo "  Please check container logs: docker compose logs postgres"
    exit 1
fi
echo "✓ PostgreSQL is running"

# Note: Database and schema are already created during container initialization
# This script can be used to re-create the schema if needed

echo ""
echo "Enabling extensions..."
docker exec -i postgres-perf-analysis psql -U $DB_USER -d $DB_NAME <<EOF
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
EOF
echo "✓ Extensions enabled"

# Verify schema exists
echo ""
echo "Verifying schema..."
table_count=$(docker exec postgres-perf-analysis psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")

if [ "$table_count" -lt 2 ]; then
    echo "  Schema not found, creating..."
    if [ -f "sql/01-schema.sql" ]; then
        docker exec -i postgres-perf-analysis psql -U $DB_USER -d $DB_NAME < sql/01-schema.sql
        echo "  ✓ Schema created"
    else
        echo "  ✗ Schema file not found: sql/01-schema.sql"
        exit 1
    fi
else
    echo "  ✓ Schema already exists ($table_count tables found)"
fi

# Create results directory
echo ""
echo "Creating results directory..."
mkdir -p results
echo "✓ Results directory ready"

echo ""
echo "✅ Database setup complete!"
echo ""
echo "Next steps:"
echo "  1. Generate data: python scripts/generate-data.py --rows 1000000"
echo "  2. Run benchmarks: python scripts/run-benchmarks.py"
echo ""
