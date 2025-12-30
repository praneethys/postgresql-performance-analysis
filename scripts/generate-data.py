#!/usr/bin/env python3
"""
Data Generation Script for PostgreSQL Performance Analysis
Generates realistic event data for testing performance at scale
"""

import argparse
import random
import sys
from datetime import datetime, timedelta
from typing import List, Dict
import psycopg2
from psycopg2.extras import execute_batch
from faker import Faker

fake = Faker()

# Configuration
EVENT_TYPES = ['page_view', 'add_to_cart', 'purchase', 'wishlist_add', 'search', 'click']
COUNTRIES = ['US', 'UK', 'CA', 'DE', 'FR', 'JP', 'AU', 'IN', 'BR', 'MX']
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
    'Mozilla/5.0 (Linux; Android 11; SM-G991B)',
]

class DataGenerator:
    def __init__(self, conn_params: Dict[str, str], batch_size: int = 10000):
        self.conn_params = conn_params
        self.batch_size = batch_size
        self.conn = None
        self.user_id_range = (1, 1000000)
        self.product_id_range = (1, 100000)

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = False
            print("✓ Connected to PostgreSQL")
        except Exception as e:
            print(f"✗ Error connecting to PostgreSQL: {e}")
            sys.exit(1)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Connection closed")

    def generate_event(self, event_time: datetime) -> tuple:
        """Generate a single event record"""
        event_type = random.choice(EVENT_TYPES)
        user_id = random.randint(*self.user_id_range)
        product_id = random.randint(*self.product_id_range) if event_type in ['page_view', 'add_to_cart', 'purchase', 'wishlist_add'] else None
        session_id = fake.uuid4()
        ip_address = fake.ipv4()
        user_agent = random.choice(USER_AGENTS)
        country_code = random.choice(COUNTRIES)
        city = fake.city()
        revenue = round(random.uniform(10, 500), 2) if event_type == 'purchase' else None

        # Generate realistic metadata
        metadata = {
            'platform': random.choice(['web', 'mobile', 'tablet']),
            'referrer': random.choice(['google', 'facebook', 'direct', 'email', 'instagram']),
            'device_type': random.choice(['desktop', 'mobile', 'tablet']),
        }

        if event_type == 'search':
            metadata['search_term'] = fake.word()

        return (
            event_time,
            user_id,
            event_type,
            product_id,
            session_id,
            ip_address,
            user_agent,
            country_code,
            city,
            revenue,
            psycopg2.extras.Json(metadata),
            event_time
        )

    def generate_batch(self, start_date: datetime, end_date: datetime, count: int) -> List[tuple]:
        """Generate a batch of events"""
        batch = []
        time_delta = end_date - start_date

        for _ in range(count):
            # Generate random timestamp within the range
            random_seconds = random.randint(0, int(time_delta.total_seconds()))
            event_time = start_date + timedelta(seconds=random_seconds)
            batch.append(self.generate_event(event_time))

        return batch

    def insert_batch(self, table_name: str, batch: List[tuple]):
        """Insert a batch of records"""
        insert_query = f"""
            INSERT INTO {table_name} (
                event_time, user_id, event_type, product_id, session_id,
                ip_address, user_agent, country_code, city, revenue,
                metadata, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        cursor = self.conn.cursor()
        try:
            execute_batch(cursor, insert_query, batch, page_size=self.batch_size)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            self.conn.rollback()
            cursor.close()
            raise e

    def generate_data(self, total_rows: int, table_name: str = 'events',
                     days_back: int = 365, daily_growth: bool = True):
        """
        Generate data with realistic time distribution

        Args:
            total_rows: Total number of rows to generate
            table_name: Target table name
            days_back: Number of days to spread data over
            daily_growth: If True, simulate daily growth (more recent = more data)
        """
        print(f"\n📊 Generating {total_rows:,} rows for table '{table_name}'")
        print(f"   Time range: {days_back} days")
        print(f"   Batch size: {self.batch_size:,}")
        print(f"   Growth pattern: {'Increasing' if daily_growth else 'Uniform'}")
        print()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        rows_generated = 0

        if daily_growth:
            # Simulate exponential growth - more recent days have more data
            # Distribute rows with increasing density toward present
            for day in range(days_back):
                day_start = start_date + timedelta(days=day)
                day_end = day_start + timedelta(days=1)

                # More rows for recent days
                weight = (day + 1) / days_back
                day_rows = int((total_rows / days_back) * weight * 1.5)

                if rows_generated + day_rows > total_rows:
                    day_rows = total_rows - rows_generated

                if day_rows <= 0:
                    continue

                # Generate in batches
                batches = (day_rows + self.batch_size - 1) // self.batch_size

                for batch_num in range(batches):
                    batch_count = min(self.batch_size, day_rows - (batch_num * self.batch_size))
                    batch = self.generate_batch(day_start, day_end, batch_count)
                    self.insert_batch(table_name, batch)
                    rows_generated += batch_count

                    if rows_generated % 100000 == 0:
                        print(f"   Progress: {rows_generated:,} / {total_rows:,} rows ({100*rows_generated/total_rows:.1f}%)")

                if rows_generated >= total_rows:
                    break
        else:
            # Uniform distribution
            batches = (total_rows + self.batch_size - 1) // self.batch_size

            for batch_num in range(batches):
                batch_count = min(self.batch_size, total_rows - rows_generated)
                batch = self.generate_batch(start_date, end_date, batch_count)
                self.insert_batch(table_name, batch)
                rows_generated += batch_count

                if rows_generated % 100000 == 0:
                    print(f"   Progress: {rows_generated:,} / {total_rows:,} rows ({100*rows_generated/total_rows:.1f}%)")

        print(f"\n✓ Generated {rows_generated:,} rows successfully")

        # Analyze table for better query planning
        cursor = self.conn.cursor()
        cursor.execute(f"ANALYZE {table_name}")
        self.conn.commit()
        cursor.close()
        print(f"✓ Table '{table_name}' analyzed")

def main():
    parser = argparse.ArgumentParser(description='Generate test data for PostgreSQL performance analysis')
    parser.add_argument('--rows', type=int, default=10000000, help='Total rows to generate (default: 10M)')
    parser.add_argument('--table', type=str, default='events', help='Target table (default: events)')
    parser.add_argument('--batch-size', type=int, default=10000, help='Batch size for inserts (default: 10000)')
    parser.add_argument('--days', type=int, default=365, help='Days to spread data over (default: 365)')
    parser.add_argument('--uniform', action='store_true', help='Use uniform distribution (default: growth pattern)')
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

    generator = DataGenerator(conn_params, batch_size=args.batch_size)

    try:
        generator.connect()
        generator.generate_data(
            total_rows=args.rows,
            table_name=args.table,
            days_back=args.days,
            daily_growth=not args.uniform
        )
    except KeyboardInterrupt:
        print("\n\n⚠ Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    finally:
        generator.close()

if __name__ == '__main__':
    main()
