# Setup Guide

## Quick Start

### 1. Start the Environment

```bash
# Start Docker containers
docker compose up -d

# Run setup script to enable extensions and verify schema
./scripts/setup-database.sh
```

### 2. Setup Python Environment

```bash
# Create virtual environment (first time only)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Generate Test Data

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Generate 1 million rows (adjust as needed)
python scripts/generate-data.py --rows 1000000

# For larger datasets (10M+ rows for realistic testing)
python scripts/generate-data.py --rows 10000000
```

### 4. Run Benchmarks

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run performance benchmarks
python scripts/run-benchmarks.py

# Analyze results
python scripts/analyze-results.py
```

## Environment Details

### Docker Services

- **PostgreSQL 16**: `localhost:5432`
  - Database: `perf_analysis`
  - User: `postgres`
  - Password: `postgres`

- **pgAdmin 4**: `http://localhost:5050`
  - Email: `admin@example.com`
  - Password: `admin`

### Database Schema

**Tables:**
- `events` - Non-partitioned table for baseline comparison
- `events_partitioned` - Range-partitioned table (by month)
- `events_partitioned_YYYY_MM` - Individual monthly partitions
- `performance_metrics` - Stores benchmark results

**Views:**
- `table_bloat` - Monitor table sizes and bloat
- `index_usage` - Track index usage statistics

**Extensions Enabled:**
- `pg_stat_statements` - Query performance tracking
- `pg_trgm` - Text similarity and trigram indexes
- `btree_gin` - GIN index support for common data types

## Manual Database Operations

### Connect to Database

```bash
# Using docker exec
docker exec -it postgres-perf-analysis psql -U postgres -d perf_analysis

# From host (requires PostgreSQL client)
psql -h localhost -p 5432 -U postgres -d perf_analysis
```

### Run Diagnostic Queries

```bash
docker exec -i postgres-perf-analysis psql -U postgres -d perf_analysis < queries/diagnostic-queries.sql
```

### Check Container Status

```bash
# View running containers
docker compose ps

# View logs
docker compose logs postgres
docker compose logs pgadmin

# Follow logs
docker compose logs -f postgres
```

### Restart Environment

```bash
# Restart containers (keeps data)
docker compose restart

# Stop containers
docker compose down

# Stop and remove volumes (DELETES ALL DATA)
docker compose down -v
```

## Troubleshooting

### PostgreSQL Not Starting

```bash
# Check logs
docker compose logs postgres

# Restart container
docker compose restart postgres
```

### Connection Issues

```bash
# Verify container is healthy
docker compose ps

# Test connection from container
docker exec postgres-perf-analysis pg_isready -U postgres

# Test connection from host
psql -h localhost -p 5432 -U postgres -d perf_analysis -c "SELECT version();"
```

### Reset Everything

```bash
# Stop containers and remove volumes
docker compose down -v

# Start fresh
docker compose up -d
./scripts/setup-database.sh
```

## Python Dependencies

Since macOS uses an externally managed Python environment, you'll need to use a virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt

# When you're done, deactivate the virtual environment
deactivate
```

**Important**: Always activate the virtual environment before running Python scripts:
```bash
source venv/bin/activate
python scripts/generate-data.py --rows 10000
```

## File Structure

```
postgresql-performance-analysis/
├── docker-compose.yml          # Docker services configuration
├── postgresql.conf             # PostgreSQL configuration
├── sql/
│   └── 01-schema.sql          # Database schema (auto-loaded on init)
├── queries/
│   ├── diagnostic-queries.sql # Performance diagnostic queries
│   └── benchmark-queries.sql  # Benchmark test queries
├── scripts/
│   ├── setup-database.sh      # Setup and verification script
│   ├── generate-data.py       # Test data generator
│   ├── run-benchmarks.py      # Benchmark execution
│   └── analyze-results.py     # Results analysis
├── results/                   # Benchmark results (JSON/CSV)
├── whitepaper/               # White paper documentation
├── docs/                     # Additional documentation
└── blog/                     # Blog posts and articles
```

## Next Steps

1. Generate test data with `python scripts/generate-data.py`
2. Run benchmarks with `python scripts/run-benchmarks.py`
3. Analyze results with `python scripts/analyze-results.py`
4. Document findings in the whitepaper
5. Iterate on optimizations and re-benchmark

## Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/16/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [pgAdmin Documentation](https://www.pgadmin.org/docs/)
