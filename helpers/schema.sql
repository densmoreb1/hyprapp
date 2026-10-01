CREATE TABLE IF NOT EXISTS exercises (
    id integer PRIMARY KEY,
    muscle_group text,
    name text COLLATE nocase,
    UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS users (
    id integer PRIMARY KEY,
    name text COLLATE nocase,
    keep_score int DEFAULT 0,
    past_mesos int DEFAULT 3,
    months int DEFAULT 8,
    UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS mesos (
    id integer PRIMARY KEY,
    completed int,
    completed_day int,
    day_id int,
    exercise_id int,
    meso_id int,
    name text,
    order_id int,
    reps int,
    set_id int,
    user_id int,
    week_id int,
    -- 'real' not 'numeric': numeric affinity would store 180.0 as 180.
    weight real,
    date_created text,
    date_completed text,
    UNIQUE (meso_id, name, user_id, exercise_id, day_id, week_id, set_id)
);

CREATE TABLE IF NOT EXISTS meso_drafts (
    user_id integer PRIMARY KEY,
    draft text,
    updated_at text,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
