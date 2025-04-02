drop database if exists fitness;
create database if not exists fitness;

use fitness;

create table if not exists exercises (
	id int auto_increment primary key,
	muscle_group varchar(100),
	name varchar(100),
	unique (name)
);

create table if not exists users (
	id int auto_increment primary key,
	name varchar(100),
	keep_score int,
	unique (name)
);

create table if not exists mesos (
	id int auto_increment primary key,
	completed int,
	completed_day int,
	day_id int,
	exercise_id int,
	meso_id int,
	name varchar(100),
	order_id int,
	reps int,
	set_id int,
	user_id int,
	week_id int,
	weight numeric(15, 1),
	date_created datetime,
	date_completed datetime,
	unique (meso_id, name, user_id, exercise_id, day_id, week_id, set_id)
);

insert into users (name) values ('brandon');
insert into users (name) values ('ivy');

insert into exercises (name, muscle_group) values ('incline bench press', 'chest');
insert into exercises (name, muscle_group) values ('pec dec', 'chest');
insert into exercises (name, muscle_group) values ('machine chest press', 'chest');
insert into exercises (name, muscle_group) values ('incline dumbbell press', 'chest');
insert into exercises (name, muscle_group) values ('low incline dumbbell press', 'chest');
insert into exercises (name, muscle_group) values ('smith machine row', 'back');
insert into exercises (name, muscle_group) values ('deadlift', 'back');
insert into exercises (name, muscle_group) values ('machine t-bar row', 'back');
insert into exercises (name, muscle_group) values ('assisted pull-up', 'back');
insert into exercises (name, muscle_group) values ('chest supported row', 'back');
insert into exercises (name, muscle_group) values ('freemotion curl', 'biceps');
insert into exercises (name, muscle_group) values ('leg press', 'quads');
insert into exercises (name, muscle_group) values ('calf press machine', 'calves');
insert into exercises (name, muscle_group) values ('leg press calves', 'calves');
insert into exercises (name, muscle_group) values ('machine lateral raise','shoulders');
insert into exercises (name, muscle_group) values ('cable tricep pushdown','triceps');
insert into exercises (name, muscle_group) values ('machine preacher curl','biceps');
insert into exercises (name, muscle_group) values ('straight arm pulldown','back');
insert into exercises (name, muscle_group) values ('barbell skullcrusher','triceps');
insert into exercises (name, muscle_group) values ('machine crunch','abs');
insert into exercises (name, muscle_group) values ('leg extension','quads');
insert into exercises (name, muscle_group) values ('cross body cable lateral raise','shoulders');
insert into exercises (name, muscle_group) values ('single arm tricep pushdown','triceps');
insert into exercises (name, muscle_group) values ('incline dumbbell curl','biceps');
insert into exercises (name, muscle_group) values ('lying leg raise','abs');
insert into exercises (name, muscle_group) values ('ez bar preacher curl','biceps');
insert into exercises (name, muscle_group) values ('cable overhead extension','triceps');
insert into exercises (name, muscle_group) values ('dumbbell lateral raise','shoulders');
insert into exercises (name, muscle_group) values ('back raise','hamstrings');
insert into exercises (name, muscle_group) values ('barbell squat','quads');
insert into exercises (name, muscle_group) values ('walking lunges','quads');
insert into exercises (name, muscle_group) values ('sissy squat','quads');

