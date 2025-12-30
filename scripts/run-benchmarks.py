#!/usr/bin/env python3
"""
Benchmark Runner for PostgreSQL Performance Analysis
Executes test queries and collects performance metrics
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Tuple
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
import csv
from datetime import datetime

class BenchmarkRunner:
    def __init__(self, conn_params: Dict[str, str]):
        self.conn_params = conn_params
        self.conn = None
        self.results = []

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True
            print("✓ Connected to PostgreSQL")
        except Exception as e:
            print(f"✗ Error connecting to PostgreSQL: {e}")
            sys.exit(1)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Connection closed")

    def run_query_with_explain(self, query: str, query_name: str) -> Dict:
        """
        Run a query with EXPLAIN ANALYZE and collect metrics

        Returns dict with execution metrics
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        # Wrap query with EXPLAIN ANALYZE
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"

        try:
            start_time = time.time()
            cursor.execute(explain_query)
            end_time = time.time()

            result = cursor.fetchone()
            plan = result['QUERY PLAN'][0]

            execution_time = plan.get('Execution Time', 0)
            planning_time = plan.get('Planning Time', 0)

            # Extract buffer statistics
            shared_hit = 0
            shared_read = 0

            def extract_buffers(node):
                nonlocal shared_hit, shared_read
                if 'Shared Hit Blocks' in node:
                    shared_hit += node['Shared Hit Blocks']
                if 'Shared Read Blocks' in node:
                    shared_read += node['Shared Read Blocks']
                if 'Plans' in node:
                    for child in node['Plans']:
                        extract_buffers(child)

            extract_buffers(plan['Plan'])

            metrics = {
                'query_name': query_name,
                'execution_time_ms': round(execution_time, 2),
                'planning_time_ms': round(planning_time, 2),
                'total_time_ms': round(execution_time + planning_time, 2),
                'wall_clock_time_ms': round((end_time - start_time) * 1000, 2),
                'shared_buffers_hit': shared_hit,
                'shared_buffers_read': shared_read,
                'buffer_hit_ratio': round(100 * shared_hit / max(shared_hit + shared_read, 1), 2),
                'plan': plan,
                'timestamp': datetime.now().isoformat()
            }

            cursor.close()
            return metrics

        except Exception as e:
            cursor.close()
            print(f"✗ Error running query '{query_name}': {e}")
            return None

    def run_simple_query(self, query: str, query_name: str) -> Dict:
        """
        Run a query without EXPLAIN (for timing only)
        """
        cursor = self.conn.cursor()

        try:
            start_time = time.time()
            cursor.execute(query)
            result = cursor.fetchall()
            end_time = time.time()

            metrics = {
                'query_name': query_name,
                'execution_time_ms': round((end_time - start_time) * 1000, 2),
                'row_count': len(result),
                'timestamp': datetime.now().isoformat()
            }

            cursor.close()
            return metrics

        except Exception as e:
            cursor.close()
            print(f"✗ Error running query '{query_name}': {e}")
            return None

    def get_table_stats(self, table_name: str) -> Dict:
        """Get current statistics for a table"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        query = f"""
            SELECT
                schemaname,
                tablename,
                pg_total_relation_size(schemaname||'.'||tablename) as total_bytes,
                pg_relation_size(schemaname||'.'||tablename) as table_bytes,
                pg_stat_get_live_tuples(c.oid) as live_tuples,
                pg_stat_get_dead_tuples(c.oid) as dead_tuples
            FROM pg_tables t
            JOIN pg_class c ON c.relname = t.tablename
            WHERE tablename = '{table_name}'
              AND schemaname = 'public'
        """

        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()

        if result:
            return dict(result)
        return {}

    def run_benchmark_suite(self, queries: List[Tuple[str, str]], iterations: int = 3) -> List[Dict]:
        """
        Run a suite of benchmark queries multiple times

        Args:
            queries: List of (query_name, query_sql) tuples
            iterations: Number of times to run each query
        """
        print(f"\n🔬 Running benchmark suite ({len(queries)} queries, {iterations} iterations each)")
        print(f"   Total tests: {len(queries) * iterations}\n")

        results = []

        for idx, (query_name, query_sql) in enumerate(queries, 1):
            print(f"[{idx}/{len(queries)}] {query_name}")

            for iteration in range(iterations):
                metrics = self.run_query_with_explain(query_sql, query_name)

                if metrics:
                    metrics['iteration'] = iteration + 1
                    metrics['query'] = query_sql  # Add the actual query text
                    results.append(metrics)
                    print(f"    Iteration {iteration + 1}: {metrics['total_time_ms']}ms "
                          f"(exec: {metrics['execution_time_ms']}ms, plan: {metrics['planning_time_ms']}ms)")
                else:
                    print(f"    Iteration {iteration + 1}: FAILED")

            print()

        return results

    def save_results(self, results: List[Dict], output_file: str):
        """Save benchmark results to JSON file"""
        try:
            # Custom JSON serializer for datetime and Decimal objects
            def json_serial(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                if isinstance(obj, Decimal):
                    return float(obj)
                return str(obj)

            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=json_serial)
            print(f"✓ Results saved to {output_file}")
        except Exception as e:
            print(f"✗ Error saving results: {e}")

    def save_results_csv(self, results: List[Dict], output_file: str):
        """Save benchmark results to CSV file (without full plan)"""
        try:
            # Remove plan from results for CSV
            csv_results = []
            for r in results:
                csv_row = {k: v for k, v in r.items() if k != 'plan'}
                csv_results.append(csv_row)

            if csv_results:
                with open(output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=csv_results[0].keys())
                    writer.writeheader()
                    writer.writerows(csv_results)
                print(f"✓ CSV results saved to {output_file}")
        except Exception as e:
            print(f"✗ Error saving CSV results: {e}")

    def save_results_to_db(self, results: List[Dict], table_name: str = 'events'):
        """Save benchmark results to performance_metrics table"""
        try:
            with self.conn.cursor() as cur:
                for r in results:
                    # Get row count for the table
                    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cur.fetchone()[0]

                    cur.execute("""
                        INSERT INTO performance_metrics (
                            test_name, table_name, row_count, query,
                            execution_time_ms, plan_time_ms,
                            buffers_hit, buffers_read, notes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        r['query_name'],
                        table_name,
                        row_count,
                        r['query'],
                        r['execution_time_ms'],
                        r.get('planning_time_ms', 0),
                        r.get('buffers_hit', 0),
                        r.get('buffers_read', 0),
                        f"Iteration {r.get('iteration', 1)}"
                    ))
                self.conn.commit()
                print(f"✓ Saved {len(results)} benchmark results to database")
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error saving results to database: {e}")

    def print_summary(self, results: List[Dict]):
        """Print summary statistics"""
        if not results:
            return

        print("\n📊 Benchmark Summary")
        print("=" * 80)

        # Group by query name
        queries = {}
        for r in results:
            name = r['query_name']
            if name not in queries:
                queries[name] = []
            queries[name].append(r)

        for query_name, metrics in queries.items():
            exec_times = [m['execution_time_ms'] for m in metrics]
            avg_exec = sum(exec_times) / len(exec_times)
            min_exec = min(exec_times)
            max_exec = max(exec_times)

            buffer_ratios = [m.get('buffer_hit_ratio', 0) for m in metrics]
            avg_buffer_ratio = sum(buffer_ratios) / len(buffer_ratios)

            print(f"\n{query_name}")
            print(f"  Iterations: {len(metrics)}")
            print(f"  Execution time: avg={avg_exec:.2f}ms, min={min_exec:.2f}ms, max={max_exec:.2f}ms")
            print(f"  Buffer hit ratio: {avg_buffer_ratio:.2f}%")

        print("\n" + "=" * 80)

def load_queries_from_file(file_path: str) -> List[Tuple[str, str]]:
    """Load queries from SQL file"""
    queries = []

    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # Simple parser: split by comments and EXPLAIN
        # This is a basic implementation - improve as needed
        current_query = []
        query_name = None

        for line in content.split('\n'):
            line = line.strip()

            if line.startswith('-- Query'):
                # Save previous query
                if query_name and current_query:
                    queries.append((query_name, '\n'.join(current_query)))
                    current_query = []

                # Extract query name
                query_name = line.replace('--', '').strip()

            elif line and not line.startswith('--'):
                # Skip EXPLAIN if present
                if not line.startswith('EXPLAIN'):
                    current_query.append(line)

        # Save last query
        if query_name and current_query:
            queries.append((query_name, '\n'.join(current_query)))

    except Exception as e:
        print(f"Error loading queries from file: {e}")

    return queries

def main():
    parser = argparse.ArgumentParser(description='Run PostgreSQL performance benchmarks')
    parser.add_argument('--iterations', type=int, default=3, help='Iterations per query (default: 3)')
    parser.add_argument('--output', type=str, default='results/benchmark-results.json', help='Output JSON file')
    parser.add_argument('--csv', type=str, help='Optional CSV output file')
    parser.add_argument('--host', type=str, default='localhost', help='PostgreSQL host')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--database', type=str, default='perf_analysis', help='Database name')
    parser.add_argument('--user', type=str, default='postgres', help='PostgreSQL user')
    parser.add_argument('--password', type=str, default='postgres', help='PostgreSQL password')

    args = parser.parse_args()

    conn_params = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }

    # Define benchmark queries
    queries = [
        ("Recent user events", """
            SELECT * FROM events
            WHERE user_id = 12345 AND event_time >= NOW() - INTERVAL '7 days'
            ORDER BY event_time DESC LIMIT 100
        """),
        ("Hourly aggregation", """
            SELECT event_type, DATE_TRUNC('hour', event_time) AS hour,
                   COUNT(*) AS event_count
            FROM events
            WHERE event_time >= NOW() - INTERVAL '24 hours'
            GROUP BY event_type, hour
            ORDER BY hour DESC
        """),
        ("Revenue by product", """
            SELECT product_id, COUNT(*) AS purchase_count, SUM(revenue) AS total_revenue
            FROM events
            WHERE event_type = 'purchase' AND event_time >= NOW() - INTERVAL '30 days'
              AND product_id IS NOT NULL
            GROUP BY product_id
            ORDER BY total_revenue DESC LIMIT 50
        """),
        ("Count recent events", """
            SELECT COUNT(*) FROM events
            WHERE event_time >= NOW() - INTERVAL '7 days'
        """),
    ]

    runner = BenchmarkRunner(conn_params)

    try:
        runner.connect()
        results = runner.run_benchmark_suite(queries, iterations=args.iterations)
        runner.print_summary(results)
        runner.save_results(results, args.output)
        runner.save_results_to_db(results, table_name='events')

        if args.csv:
            runner.save_results_csv(results, args.csv)

    except KeyboardInterrupt:
        print("\n\n⚠ Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        runner.close()

if __name__ == '__main__':
    main()
