import os
from pathlib import Path
import random
from datetime import datetime
import sqlite3
import uuid

import pyarrow as pa

# Configuration
num_tracks = 5000
num_events = 1_000_000
base_time = datetime(2024, 1, 1).timestamp()
batch_size = 100_000

uuid_count = num_tracks + num_events + 1

import multiprocessing
import uuid

def get_uuid(_):
    return str(uuid.UUID(bytes=os.urandom(16), version=4))

uuids=[]
def main():
    global uuids
    pool = multiprocessing.Pool( 20 )
    uuids = pool.map( get_uuid, range( uuid_count ) )

if __name__ == '__main__': main()

def get_precalculated_uuid():
    return uuid.uuid4().bytes

cam_id = uuids[len(uuids)-1]

# Generate track_ids
track_ids = [uuids[num_events + track_number] for track_number in range(num_tracks)]

event_number=0
# Event patterns
def generate_sequence(track_id, start_time):
    global event_number
    sequence = []
    duration = random.uniform(5, 300)
    current_time = start_time
    
    # Entrance
    end_time = current_time + random.uniform(2, 10)
    sequence.append((
        uuids[event_number],
        int(current_time * 1000000),
        int(end_time * 1000000),
        int(random.uniform(0.7, 0.98) * 100),
        'person_zone_entrance',
        track_id
    ))
    event_number += 1
    current_time = end_time + random.uniform(0, 5)
    
    # Random number of center events
    num_center = random.randint(0, 5)
    for _ in range(num_center):
        if current_time - start_time > duration:
            break
        end_time = current_time + random.uniform(2, 30)
        sequence.append((
            uuids[event_number],
            int(current_time * 1000000),
            int(end_time * 1000000),
            int(random.uniform(0.7, 0.98) * 100),
            'person_zone_center',
            track_id
        ))
        event_number += 1
        current_time = end_time + random.uniform(0, 5)
    
    # Exit (80% chance)
    if random.random() < 0.8 and (current_time - start_time) < duration:
        end_time = current_time + random.uniform(2, 10)
        sequence.append((
            uuids[event_number],
            int(current_time * 1000000),
            int(end_time * 1000000),
            int(random.uniform(0.7, 0.98) * 100),
            'person_zone_exit',
            track_id
        ))
        event_number += 1
    
    return sequence

# Generate events
events = []
current_base_time = base_time

while event_number < num_events:
    track_id = random.choice(track_ids)
    sequence = generate_sequence(track_id, current_base_time)
    events.extend(sequence)
    current_base_time += random.uniform(0, 300)

# Truncate to exactly num_events and prepare batches
events = events[:num_events]
batches = [events[i:i + batch_size] for i in range(0, len(events), batch_size)]

database_folder_path = os.path.normpath(Path(__file__).parent / "../../../db/")

connection = sqlite3.connect(f"{str(database_folder_path)}/cam1.db")
cursor = connection.cursor()
cursor.execute(f""" CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    cam_id TEXT NOT NULL,
    event_end NUMERIC NOT NULL,
    event_name TEXT NOT NULL,
    event_start NUMERIC NOT NULL,
    track_class INTEGER NOT NULL,
    track_conf NUMERIC NOT NULL,
    track_id TEXT NOT NULL
);""")
cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_track_name_start ON events(track_id, event_name, event_start);')
connection.commit()

# Generate SQL with batched inserts
print("BEGIN TRANSACTION;")
i = 0
for batch in batches:
    i+=1
    print('pushing', i * batch_size, '/', num_events, i * batch_size / num_events * 100, '%')
    values = []
    for event in batch:
        values.append([
            event[0], event[1], event[2], event[3], event[4], 0, cam_id, event[5] # type: ignore
        ])
    cursor.executemany("INSERT INTO events (event_id, event_start, event_end, track_conf, event_name, track_class, cam_id, track_id) values (?, ?, ?, ?, ?, ?, ?, ?)", values)
connection.commit()

