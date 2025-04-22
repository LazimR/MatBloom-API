
CREATE TABLE content (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE question (
	id SERIAL NOT NULL, 
	enunciation VARCHAR NOT NULL, 
	itens VARCHAR[] NOT NULL, 
	correct_item INTEGER, 
	level INTEGER NOT NULL, 
	contents VARCHAR[], 
	PRIMARY KEY (id)
)

;


CREATE TABLE student (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE test (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE question_content (
	question_id INTEGER NOT NULL, 
	content_id INTEGER NOT NULL, 
	PRIMARY KEY (question_id, content_id), 
	FOREIGN KEY(question_id) REFERENCES question (id), 
	FOREIGN KEY(content_id) REFERENCES content (id)
)

;


CREATE TABLE question_dependency (
	question_id INTEGER NOT NULL, 
	dependency_id INTEGER NOT NULL, 
	PRIMARY KEY (question_id, dependency_id), 
	FOREIGN KEY(question_id) REFERENCES question (id), 
	FOREIGN KEY(dependency_id) REFERENCES question (id)
)

;


CREATE TABLE test_question (
	test_id INTEGER NOT NULL, 
	question_id INTEGER NOT NULL, 
	PRIMARY KEY (test_id, question_id), 
	FOREIGN KEY(test_id) REFERENCES test (id), 
	FOREIGN KEY(question_id) REFERENCES question (id)
)

;


CREATE TABLE test_response (
	id SERIAL NOT NULL, 
	test_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	score FLOAT, 
	responses INTEGER[] NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(test_id) REFERENCES test (id), 
	FOREIGN KEY(student_id) REFERENCES student (id)
)

;

