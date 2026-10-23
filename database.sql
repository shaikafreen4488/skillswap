-- SkillSwap database setup. Run this file ONE time (see README.md).

CREATE DATABASE IF NOT EXISTS skillswap_web CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE skillswap_web;

CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    roll_number VARCHAR(30) NOT NULL,
    department VARCHAR(100) NOT NULL,
    year_of_study TINYINT NOT NULL,
    bio VARCHAR(255) NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_students_roll UNIQUE (roll_number),
    CONSTRAINT chk_students_year CHECK (year_of_study BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(80) NOT NULL,
    CONSTRAINT uq_skills_name UNIQUE (skill_name)
);

INSERT IGNORE INTO skills (skill_name) VALUES
    ('Python'), ('Java'), ('C Programming'), ('SQL'), ('Web Development'),
    ('Data Structures'), ('Machine Learning'), ('Communication Skills'),
    ('Graphic Design'), ('Excel');

CREATE TABLE IF NOT EXISTS student_skills (
    student_skill_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    skill_type ENUM('teach', 'learn') NOT NULL,
    skill_level ENUM('Beginner', 'Intermediate', 'Advanced') NOT NULL,
    description VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_student_skill UNIQUE (student_id, skill_id, skill_type),
    INDEX idx_student_skills_type (skill_type),
    CONSTRAINT fk_ss_student FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_ss_skill FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
);

CREATE TABLE IF NOT EXISTS learning_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    learner_id INT NOT NULL,
    teacher_id INT NOT NULL,
    skill_id INT NOT NULL,
    message VARCHAR(500) NULL,
    status ENUM('Pending', 'Accepted', 'Rejected', 'Cancelled', 'Completed') NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_requests_status (status),
    INDEX idx_requests_pair (learner_id, teacher_id, skill_id),
    CONSTRAINT fk_req_learner FOREIGN KEY (learner_id) REFERENCES students (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_req_teacher FOREIGN KEY (teacher_id) REFERENCES students (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_req_skill FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    session_datetime DATETIME NOT NULL,
    location VARCHAR(255) NULL,
    status ENUM('Scheduled', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Scheduled',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_when (session_datetime),
    CONSTRAINT fk_sessions_request FOREIGN KEY (request_id) REFERENCES learning_requests (request_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    reviewer_id INT NOT NULL,
    reviewee_id INT NOT NULL,
    rating TINYINT NOT NULL,
    comments VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_feedback_once UNIQUE (session_id, reviewer_id),
    CONSTRAINT chk_feedback_rating CHECK (rating BETWEEN 1 AND 5),
    INDEX idx_feedback_reviewee (reviewee_id),
    CONSTRAINT fk_fb_session FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
    CONSTRAINT fk_fb_reviewer FOREIGN KEY (reviewer_id) REFERENCES students (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_fb_reviewee FOREIGN KEY (reviewee_id) REFERENCES students (student_id) ON DELETE CASCADE
);
