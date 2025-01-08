import os
import sqlite3
import random
from datetime import datetime, timedelta
import time

# Connect to SQLite database (creates if not exists)
print("Creating database...")
conn = sqlite3.connect('tracking.db')
cursor = conn.cursor()

# Create the events table
cursor.execute('DROP TABLE IF EXISTS events')
cursor.execute('''
CREATE TABLE IF NOT EXISTS events (
    event_id BLOB PRIMARY KEY,
    event_ts INTEGER,
    track_conf REAL,
    event_name TEXT,
    track_class INTEGER,
    cam_id BLOB,
    track_id BLOB
)
''')

# Configuration
num_tracks = 500_000
num_events = 2_000_000
base_time = datetime(2024, 1, 1).timestamp()
batch_size = 100_000

uuid_count = num_tracks + num_events + 1

import multiprocessing
import uuid

def get_uuid(_):
    return uuid.UUID(bytes=os.urandom(16), version=4).bytes

uuids=[]
def main():
    global uuids
    pool = multiprocessing.Pool( 20 )
    uuids = pool.map( get_uuid, range( uuid_count ) )

if __name__ == '__main__': main()

cam_id = uuids[len(uuids)-1]

# Generate track_ids
track_ids = [uuids[num_events + track_number] for track_number in range(num_tracks)]

# Base scenarios template
base_scenarios = [
    # Scenario 1: Normal flow - entrance -> exit zone -> leave zone
    {
        'events': [
            ('enter_zone_entrance', 0),
            ('enter_zone_exit', 300),
            ('leave_zone_exit', 360)
        ]
    },
    # Scenario 2: Entrance -> exit zone only
    {
        'events': [
            ('enter_zone_entrance', 0),
            ('enter_zone_exit', 300)
        ]
    },
    # Scenario 3: Entrance -> direct leave_zone_exit
    {
        'events': [
            ('enter_zone_entrance', 0),
            ('leave_zone_exit', 300)
        ]
    },
    # Scenario 4: Multiple entrances and exits
    {
        'events': [
            ('enter_zone_entrance', 0),
            ('enter_zone_exit', 300),
            ('leave_zone_exit', 360),
            ('enter_zone_entrance', 600)
        ]
    },
    # Scenario 5: Only entrance
    {
        'events': [
            ('enter_zone_entrance', 0)
        ]
    },
    # Scenario 6: Only exit
    {
        'events': [
            ('enter_zone_exit', 0)
        ]
    },
    # Scenario 7: Exit before entrance
    {
        'events': [
            ('enter_zone_exit', 0),
            ('enter_zone_entrance', 300)
        ]
    },
    # Scenario 8: Multiple exits
    {
        'events': [
            ('enter_zone_entrance', 0),
            ('enter_zone_exit', 300),
            ('leave_zone_exit', 360),
            ('enter_zone_exit', 420)
        ]
    },
    # Scenario 9: Different locations
    {
        'events': [
            ('enter_zone_entrance', 0),
            ('enter_zone_exit', 300),
            ('leave_zone_exit', 360)
        ]
    },
    # Scenario 10: Quick sequence
    {
        'events': [
            ('enter_zone_entrance', 0),
            ('enter_zone_exit', 60),
            ('leave_zone_exit', 90)
        ]
    }
]

# Function to generate random confidence score
def random_conf():
    return round(random.uniform(0.65, 0.98), 2)

# Base timestamp for events
base_ts = int(datetime(2024, 1, 1).timestamp())


print("Preparing to insert data...")
start_time = time.time()

# Use transaction for faster inserts
cursor.execute('BEGIN TRANSACTION')

tracks_created = 0
events_created = 0


try:
    for i in range(num_events):
        if i % 10000 == 0:  # Progress update every 10000 iterations
            print(f"Processing iteration {i}/{num_events}...")
        
        # Random time offset for this batch of scenarios (within a 90 day period)
        batch_time_offset = random.randint(0, 7776000)  # 90 days in seconds
        
        # Create each scenario with random timing
        for scenario_num, base_scenario in enumerate(base_scenarios, 1):
            if tracks_created >= num_tracks:
                break
            print(tracks_created, len(track_ids))
            track_id = track_ids[tracks_created]
            tracks_created += 1
            
            # Randomize the relative timing between events while maintaining order
            last_time = 0
            events = []
            for event_name, base_offset in base_scenario['events']:
                # Add some random variation to the timing between events
                time_offset = last_time + random.randint(30, 300)  # 30 to 300 seconds after last event
                last_time = time_offset
                events.append((event_name, time_offset))
            
            # Insert all events for this track
            for event_name, time_offset in events:
                
                if events_created >= num_events:
                    break
                event_id = uuids[events_created]
                events_created = events_created+1
                final_ts = base_ts + batch_time_offset + time_offset
                
                print(events_created)
                
                cursor.execute('''
                INSERT INTO events (event_id, event_ts, track_conf, event_name, track_class,  cam_id, track_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (event_id, final_ts, random_conf(), event_name, 1,  cam_id, track_id))
            
            if events_created >= num_events:
                break
        if tracks_created >= num_tracks:
            break
        if events_created >= num_events:
            break
                

    # Commit the transaction
    cursor.execute('COMMIT')
    
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Get final count
    cursor.execute('SELECT COUNT(*) FROM events')
    total_events = cursor.fetchone()[0]
    
    print(f"\nDatabase created successfully!")
    print(f"Total events inserted: {total_events:,}")
    print(f"Total tracks created: {tracks_created:,}")
    print(f"Total time taken: {total_time:.2f} seconds")
    print(f"Average insertion rate: {total_events/total_time:.2f} events/second")

except Exception as e:
    cursor.execute('ROLLBACK')
    print(f"An error occurred: {e}")
    raise

finally:
    # Close connection
    conn.close()