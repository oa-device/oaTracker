import chdb

print(chdb.query("""
CREATE DATABASE _temporary_and_external_tables;
CREATE DATABASE test;
USE test;
CREATE TABLE hackernews_history UUID '66491946-56e3-4790-a112-d2dc3963e68a'
    (
        `update_time` DateTime DEFAULT now(),
        `id` UInt32,
        `deleted` UInt8,
        `type` Enum8('story' = 1, 'comment' = 2, 'poll' = 3, 'pollopt' = 4, 'job' = 5),
        `by` LowCardinality(String),
        `time` DateTime,
        `text` String,
        `dead` UInt8,
        `parent` UInt32,
        `poll` UInt32,
        `kids` Array(UInt32),
        `url` String,
        `score` Int32,
        `title` String,
        `parts` Array(UInt32),
        `descendants` Int32
    )
    ENGINE = ReplacingMergeTree(update_time)
    ORDER BY id
    SETTINGS disk = disk(readonly = true, type = 's3_plain_rewritable', endpoint = 'https://clicklake-test-2.s3.eu-central-1.amazonaws.com/', use_environment_credentials = true);
    """))

#print("SELECT * FROM hackernews_history WHERE text LIKE '%Clickhouse is amazing%' ORDER BY update_time")