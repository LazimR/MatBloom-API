CREATE TABLE classroom (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	school_year INTEGER NOT NULL, 
	grade_level VARCHAR NOT NULL, 
	shift VARCHAR NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE content (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE question (
	id SERIAL NOT NULL, 
	enunciation VARCHAR NOT NULL, 
	itens VARCHAR[] NOT NULL, 
	correct_item INTEGER, 
	level INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE "user" (
	id SERIAL NOT NULL, 
	username VARCHAR NOT NULL, 
	password VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
);

CREATE TABLE question_content (
	question_id INTEGER NOT NULL, 
	content_id INTEGER NOT NULL, 
	PRIMARY KEY (question_id, content_id), 
	FOREIGN KEY(question_id) REFERENCES question (id), 
	FOREIGN KEY(content_id) REFERENCES content (id)
);

CREATE TABLE question_dependency (
	question_id INTEGER NOT NULL, 
	dependency_id INTEGER NOT NULL, 
	PRIMARY KEY (question_id, dependency_id), 
	FOREIGN KEY(question_id) REFERENCES question (id), 
	FOREIGN KEY(dependency_id) REFERENCES question (id)
);

CREATE TABLE student (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	registration VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	active BOOLEAN NOT NULL, 
	classroom_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (registration), 
	FOREIGN KEY(classroom_id) REFERENCES classroom (id)
);

CREATE TABLE user_classroom (
	user_id INTEGER NOT NULL, 
	classroom_id INTEGER NOT NULL, 
	PRIMARY KEY (user_id, classroom_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(classroom_id) REFERENCES classroom (id)
);

CREATE TABLE test (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	theme VARCHAR NOT NULL, 
	application_date DATE, 
	created_by_user_id INTEGER, 
	applied_by_user_id INTEGER, 
	classroom_id INTEGER, 
	student_id INTEGER, 
	source_test_id INTEGER, 
	template_group_id INTEGER, 
	version_number INTEGER NOT NULL, 
	kind VARCHAR NOT NULL, 
	visibility VARCHAR NOT NULL, 
	target_type VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_user_id) REFERENCES "user" (id), 
	FOREIGN KEY(applied_by_user_id) REFERENCES "user" (id), 
	FOREIGN KEY(classroom_id) REFERENCES classroom (id), 
	FOREIGN KEY(student_id) REFERENCES student (id), 
	FOREIGN KEY(source_test_id) REFERENCES test (id), 
	FOREIGN KEY(template_group_id) REFERENCES test (id)
);

CREATE TABLE test_question (
	test_id INTEGER NOT NULL, 
	question_id INTEGER NOT NULL, 
	PRIMARY KEY (test_id, question_id), 
	FOREIGN KEY(test_id) REFERENCES test (id), 
	FOREIGN KEY(question_id) REFERENCES question (id)
);

CREATE TABLE test_response (
	id SERIAL NOT NULL, 
	test_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	score FLOAT, 
	responses INTEGER[] NOT NULL, 
	wrong_questions INTEGER[], 
	attempt_date DATE DEFAULT CURRENT_DATE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(test_id) REFERENCES test (id), 
	FOREIGN KEY(student_id) REFERENCES student (id)
);
