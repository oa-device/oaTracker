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
    event_id TEXT PRIMARY KEY,
    event_ts INTEGER,
    track_conf REAL,
    event_name TEXT,
    track_class INTEGER,
    location_id TEXT,
    cam_id TEXT,
    track_id TEXT
)
''')

# Base scenarios template
base_scenarios = [
    # Scenario 1: Normal flow - entrance -> exit zone -> leave zone
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_main_entrance', 'cam_entrance_01'),
            ('enter_zone_exit', 300, 'loc_main_exit', 'cam_exit_01'),
            ('leave_zone_exit', 360, 'loc_main_exit', 'cam_exit_01')
        ]
    },
    # Scenario 2: Entrance -> exit zone only
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_main_entrance', 'cam_entrance_01'),
            ('enter_zone_exit', 300, 'loc_main_exit', 'cam_exit_01')
        ]
    },
    # Scenario 3: Entrance -> direct leave_zone_exit
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_main_entrance', 'cam_entrance_01'),
            ('leave_zone_exit', 300, 'loc_main_exit', 'cam_exit_01')
        ]
    },
    # Scenario 4: Multiple entrances and exits
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_main_entrance', 'cam_entrance_01'),
            ('enter_zone_exit', 300, 'loc_main_exit', 'cam_exit_01'),
            ('leave_zone_exit', 360, 'loc_main_exit', 'cam_exit_01'),
            ('enter_zone_entrance', 600, 'loc_main_entrance', 'cam_entrance_01')
        ]
    },
    # Scenario 5: Only entrance
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_main_entrance', 'cam_entrance_01')
        ]
    },
    # Scenario 6: Only exit
    {
        'events': [
            ('enter_zone_exit', 0, 'loc_main_exit', 'cam_exit_01')
        ]
    },
    # Scenario 7: Exit before entrance
    {
        'events': [
            ('enter_zone_exit', 0, 'loc_main_exit', 'cam_exit_01'),
            ('enter_zone_entrance', 300, 'loc_main_entrance', 'cam_entrance_01')
        ]
    },
    # Scenario 8: Multiple exits
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_main_entrance', 'cam_entrance_01'),
            ('enter_zone_exit', 300, 'loc_main_exit', 'cam_exit_01'),
            ('leave_zone_exit', 360, 'loc_main_exit', 'cam_exit_01'),
            ('enter_zone_exit', 420, 'loc_main_exit', 'cam_exit_02')
        ]
    },
    # Scenario 9: Different locations
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_side_entrance', 'cam_entrance_02'),
            ('enter_zone_exit', 300, 'loc_emergency_exit', 'cam_exit_03'),
            ('leave_zone_exit', 360, 'loc_emergency_exit', 'cam_exit_03')
        ]
    },
    # Scenario 10: Quick sequence
    {
        'events': [
            ('enter_zone_entrance', 0, 'loc_main_entrance', 'cam_entrance_01'),
            ('enter_zone_exit', 60, 'loc_main_exit', 'cam_exit_01'),
            ('leave_zone_exit', 90, 'loc_main_exit', 'cam_exit_01')
        ]
    }
]

# Function to generate random confidence score
def random_conf():
    return round(random.uniform(0.65, 0.98), 2)

# Base timestamp for events
base_ts = int(datetime(2024, 1, 1).timestamp())

# Number of iterations
num_iterations = 2500000  # This will generate ~1M events (10 scenarios * ~10 events each * 100000)

print("Preparing to insert data...")
start_time = time.time()

# Use transaction for faster inserts
cursor.execute('BEGIN TRANSACTION')

event_id_counter = 1
tracks_created = 0

try:
    for i in range(num_iterations):
        if i % 10000 == 0:  # Progress update every 10000 iterations
            print(f"Processing iteration {i}/{num_iterations}...")
        
        # Random time offset for this batch of scenarios (within a 90 day period)
        batch_time_offset = random.randint(0, 7776000)  # 90 days in seconds
        
        # Create each scenario with random timing
        for scenario_num, base_scenario in enumerate(base_scenarios, 1):
            track_id = f'trk_person_{tracks_created:06d}'
            tracks_created += 1
            
            # Randomize the relative timing between events while maintaining order
            last_time = 0
            events = []
            for event_name, base_offset, location, camera in base_scenario['events']:
                # Add some random variation to the timing between events
                time_offset = last_time + random.randint(30, 300)  # 30 to 300 seconds after last event
                last_time = time_offset
                events.append((event_name, time_offset, location, camera))
            
            # Insert all events for this track
            for event_name, time_offset, location, camera in events:
                event_id = f'evt_{event_id_counter:08d}'
                final_ts = base_ts + batch_time_offset + time_offset
                
                cursor.execute('''
                INSERT INTO events (event_id, event_ts, track_conf, event_name, track_class, location_id, cam_id, track_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (event_id, final_ts, random_conf(), event_name, 1, location, camera, track_id))
                
                event_id_counter += 1

    # Commit the transaction
    cursor.execute('COMMIT')
    
    # Create indices for better query performance
    print("Creating indices...")
    cursor.execute('CREATE INDEX idx_track_id_ts ON events(track_id, event_ts)')
    cursor.execute('CREATE INDEX idx_event_name ON events(event_name)')
    
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