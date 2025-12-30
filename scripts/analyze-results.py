#!/usr/bin/env python3
"""
Analyze Performance Benchmark Results
This script analyzes benchmark results from the performance_metrics table
and generates visualizations and reports.
"""

import psycopg2
import json
import csv
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
import argparse
import os


class PerformanceAnalyzer:
    def __init__(self, host='localhost', port=5432, database='perf_analysis',
                 user='postgres', password='postgres'):
        self.conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }

    def connect(self):
        """Establish database connection"""
        return psycopg2.connect(**self.conn_params)

    def fetch_metrics(self, test_name=None, limit=None) -> List[Dict[str, Any]]:
        """Fetch performance metrics from the database"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        id,
                        test_name,
                        table_name,
                        row_count,
                        query,
                        execution_time_ms,
                        plan_time_ms,
                        buffers_hit,
                        buffers_read,
                        test_timestamp,
                        notes
                    FROM performance_metrics
                """

                conditions = []
                params = []

                if test_name:
                    conditions.append("test_name = %s")
                    params.append(test_name)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY test_timestamp DESC"

                if limit:
                    query += f" LIMIT {limit}"

                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                return [dict(zip(columns, row)) for row in rows]

    def analyze_by_table(self) -> Dict[str, Any]:
        """Analyze performance by table type"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        table_name,
                        COUNT(*) as test_count,
                        AVG(execution_time_ms) as avg_execution_time,
                        MIN(execution_time_ms) as min_execution_time,
                        MAX(execution_time_ms) as max_execution_time,
                        AVG(buffers_hit) as avg_buffers_hit,
                        AVG(buffers_read) as avg_buffers_read
                    FROM performance_metrics
                    GROUP BY table_name
                    ORDER BY avg_execution_time DESC
                """

                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                return {
                    'summary': [dict(zip(columns, row)) for row in rows],
                    'timestamp': datetime.now().isoformat()
                }

    def analyze_by_test(self) -> Dict[str, Any]:
        """Analyze performance by test type"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        test_name,
                        COUNT(*) as execution_count,
                        AVG(execution_time_ms) as avg_execution_time,
                        MIN(execution_time_ms) as min_execution_time,
                        MAX(execution_time_ms) as max_execution_time,
                        STDDEV(execution_time_ms) as stddev_execution_time
                    FROM performance_metrics
                    GROUP BY test_name
                    ORDER BY avg_execution_time DESC
                """

                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                return {
                    'summary': [dict(zip(columns, row)) for row in rows],
                    'timestamp': datetime.now().isoformat()
                }

    def compare_partitioned_vs_non_partitioned(self) -> Dict[str, Any]:
        """Compare performance between partitioned and non-partitioned tables"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                query = """
                    WITH comparison AS (
                        SELECT
                            test_name,
                            table_name,
                            AVG(execution_time_ms) as avg_time
                        FROM performance_metrics
                        WHERE table_name IN ('events', 'events_partitioned')
                        GROUP BY test_name, table_name
                    )
                    SELECT
                        c1.test_name,
                        c1.avg_time as events_avg_time,
                        c2.avg_time as events_partitioned_avg_time,
                        ROUND(((c1.avg_time - c2.avg_time) / c1.avg_time * 100)::numeric, 2) as improvement_percent
                    FROM comparison c1
                    LEFT JOIN comparison c2
                        ON c1.test_name = c2.test_name
                        AND c1.table_name = 'events'
                        AND c2.table_name = 'events_partitioned'
                    WHERE c1.table_name = 'events'
                    ORDER BY improvement_percent DESC
                """

                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                results = [dict(zip(columns, row)) for row in rows]

                return {
                    'comparison': results,
                    'timestamp': datetime.now().isoformat()
                }

    def export_to_csv(self, data: List[Dict[str, Any]], filename: str):
        """Export data to CSV file"""
        if not data:
            print("No data to export")
            return

        filepath = os.path.join('results', filename)

        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        print(f"Exported to {filepath}")

    def export_to_json(self, data: Any, filename: str):
        """Export data to JSON file"""
        filepath = os.path.join('results', filename)

        # Custom JSON serializer for datetime and Decimal objects
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(filepath, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=2, default=json_serial)

        print(f"Exported to {filepath}")

    def generate_report(self, output_format='text'):
        """Generate comprehensive performance report"""
        print("\n" + "="*80)
        print("POSTGRESQL PERFORMANCE ANALYSIS REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")

        # Table-level analysis
        print("\n1. PERFORMANCE BY TABLE TYPE")
        print("-" * 80)
        table_analysis = self.analyze_by_table()
        for item in table_analysis['summary']:
            print(f"\nTable: {item['table_name']}")
            print(f"  Tests Run: {item['test_count']}")
            print(f"  Avg Execution Time: {float(item['avg_execution_time']):.2f} ms")
            print(f"  Min Execution Time: {float(item['min_execution_time']):.2f} ms")
            print(f"  Max Execution Time: {float(item['max_execution_time']):.2f} ms")
            print(f"  Avg Buffer Hits: {float(item['avg_buffers_hit']):.0f}")
            print(f"  Avg Buffer Reads: {float(item['avg_buffers_read']):.0f}")

        # Test-level analysis
        print("\n\n2. PERFORMANCE BY TEST TYPE")
        print("-" * 80)
        test_analysis = self.analyze_by_test()
        for item in test_analysis['summary']:
            print(f"\nTest: {item['test_name']}")
            print(f"  Executions: {item['execution_count']}")
            print(f"  Avg Time: {float(item['avg_execution_time']):.2f} ms")
            print(f"  Min Time: {float(item['min_execution_time']):.2f} ms")
            print(f"  Max Time: {float(item['max_execution_time']):.2f} ms")
            if item['stddev_execution_time']:
                print(f"  Std Dev: {float(item['stddev_execution_time']):.2f} ms")

        # Comparison analysis
        print("\n\n3. PARTITIONED VS NON-PARTITIONED COMPARISON")
        print("-" * 80)
        comparison = self.compare_partitioned_vs_non_partitioned()
        for item in comparison['comparison']:
            if item['events_partitioned_avg_time']:
                print(f"\nTest: {item['test_name']}")
                print(f"  Non-Partitioned: {float(item['events_avg_time']):.2f} ms")
                print(f"  Partitioned: {float(item['events_partitioned_avg_time']):.2f} ms")
                print(f"  Improvement: {float(item['improvement_percent']):.2f}%")

        print("\n" + "="*80 + "\n")

        # Export data
        if output_format in ['json', 'all']:
            self.export_to_json(table_analysis, 'table_analysis.json')
            self.export_to_json(test_analysis, 'test_analysis.json')
            self.export_to_json(comparison, 'comparison_analysis.json')

        if output_format in ['csv', 'all']:
            self.export_to_csv(table_analysis['summary'], 'table_analysis.csv')
            self.export_to_csv(test_analysis['summary'], 'test_analysis.csv')
            if comparison['comparison']:
                self.export_to_csv(comparison['comparison'], 'comparison_analysis.csv')


def main():
    parser = argparse.ArgumentParser(
        description='Analyze PostgreSQL performance benchmark results'
    )
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', type=int, default=5432, help='Database port')
    parser.add_argument('--database', default='perf_analysis', help='Database name')
    parser.add_argument('--user', default='postgres', help='Database user')
    parser.add_argument('--password', default='postgres', help='Database password')
    parser.add_argument('--format', choices=['text', 'json', 'csv', 'all'],
                       default='all', help='Output format')
    parser.add_argument('--test-name', help='Filter by specific test name')
    parser.add_argument('--export-raw', action='store_true',
                       help='Export raw metrics data')

    args = parser.parse_args()

    analyzer = PerformanceAnalyzer(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password
    )

    try:
        # Generate main report
        analyzer.generate_report(output_format=args.format)

        # Export raw data if requested
        if args.export_raw:
            print("\nExporting raw metrics data...")
            metrics = analyzer.fetch_metrics(test_name=args.test_name)
            analyzer.export_to_json(metrics, 'raw_metrics.json')
            analyzer.export_to_csv(metrics, 'raw_metrics.csv')
            print(f"Exported {len(metrics)} metrics records")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
