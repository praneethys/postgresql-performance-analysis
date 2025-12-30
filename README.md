# PostgreSQL Performance Analysis: Diagnosing and Solving Slow Queries in High-Growth Tables

## Problem Statement

**"You have a large table growing by millions of rows daily. Queries are slowing down despite having indexes. How do you diagnose and solve this?"**

This repository contains a comprehensive analysis of PostgreSQL performance degradation in high-growth environments, complete with practical simulations, diagnostic approaches, and proven solutions.

## Overview

This project provides:
- A realistic simulation of a rapidly growing PostgreSQL table
- Performance benchmarking and monitoring tools
- Diagnostic queries and scripts
- Multiple optimization strategies with measurable results
- Complete documentation of findings in a white paper

## Repository Structure

```
postgresql-performance-analysis/
├── docker/                     # Docker setup for PostgreSQL
├── sql/                        # Database schemas and queries
│   ├── schema.sql             # Table definitions
│   ├── indexes.sql            # Index strategies
│   └── diagnostic-queries.sql # Performance analysis queries
├── scripts/                    # Automation scripts
│   ├── generate-data.py       # Data generation
│   ├── run-benchmarks.py      # Performance testing
│   └── analyze-results.py     # Results analysis
├── results/                    # Benchmark results and metrics
├── whitepaper/                 # White paper content
├── docs/                       # Additional documentation
└── blog/                       # LinkedIn post and Medium article

```

## Quick Start

```bash
# 1. Start environment
docker compose up -d
./scripts/setup-database.sh

# 2. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Generate test data
python scripts/generate-data.py --rows 10000000

# 4. Run benchmarks
python scripts/run-benchmarks.py

# 5. Analyze results
python scripts/analyze-results.py --format all
```

📚 **[Complete Setup Guide](SETUP.md)** | 📊 **[White Paper](whitepaper/postgresql-performance-whitepaper.md)**

## Key Findings

Based on empirical testing with **7.52 million rows** (2.6 GB):

- **17% of index storage wasted** - Two indexes (90 MB) had zero usage
- **Query performance varied 500x** - From 2ms (lookups) to 1067ms (aggregations)
- **Cache hit ratios 96-100%** - Proper buffer configuration critical
- **Index overhead: 20.5%** - 539 MB indexes for 2.1 GB data

💡 **Critical Insight**: Always monitor `pg_stat_user_indexes` - unused indexes waste storage and slow all writes.

**Full analysis**: [Performance Analysis White Paper](whitepaper/postgresql-performance-whitepaper.md)

## Performance Optimization Strategies Covered

1. **Index Optimization**
   - BRIN indexes for time-series data
   - Partial indexes
   - Index maintenance and bloat

2. **Table Partitioning**
   - Range partitioning by date
   - Partition pruning
   - Partition management automation

3. **Vacuum and Autovacuum Tuning**
   - Bloat detection and removal
   - Autovacuum configuration

4. **Query Optimization**
   - EXPLAIN ANALYZE interpretation
   - Query plan optimization
   - Statistics updates

5. **Hardware and Configuration**
   - Memory settings
   - Checkpoint tuning
   - Connection pooling

## Useful Commands

### Database Access
```bash
# Connect to database
docker exec -it postgres-perf-analysis psql -U postgres -d perf_analysis

# Check table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size('events')) FROM pg_tables WHERE tablename = 'events';

# View index usage
SELECT * FROM index_usage WHERE tablename = 'events';
```

### Data Management
```bash
# Clear all data
docker exec postgres-perf-analysis psql -U postgres -d perf_analysis -c "TRUNCATE events CASCADE"

# Reset everything
docker compose down -v && docker compose up -d && ./scripts/setup-database.sh
```

### Access Tools
- **PostgreSQL**: `localhost:5432` (user: postgres, password: postgres)
- **pgAdmin**: `http://localhost:5050` (admin@example.com / admin)

## Documentation

- 📖 **[Setup Guide](SETUP.md)** - Complete installation and configuration
- 📊 **[White Paper](whitepaper/postgresql-performance-whitepaper.md)** - Performance analysis findings
- 🗂️ **[Results](results/)** - Benchmark data (JSON/CSV)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License

## Author

**Praneeth Yerrapragada**

## References

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/16/)
- [PostgreSQL Performance Tuning Best Practices](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [High Performance PostgreSQL for Rails](https://pragprog.com/titles/aapsql/high-performance-postgresql-for-rails/)
