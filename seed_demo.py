"""OPTIONAL: adds 5 demo students so the Explore page is not empty.

Run:  python seed_demo.py
Demo roll numbers: DEMO001 to DEMO005. Password for all of them: demo123
It is safe to run again. Existing demo students are skipped.
"""
from werkzeug.security import generate_password_hash

import database as db

DEMO_STUDENTS = [
    ("Anita Rao", "DEMO001", "Computer Science", 3,
     [("Python", "Advanced", "Can teach basics to projects"), ("SQL", "Intermediate", "Queries and joins")],
     [("Graphic Design", "Beginner", "Posters and logos")]),
    ("Ravi Teja", "DEMO002", "Information Technology", 2,
     [("Web Development", "Intermediate", "HTML, CSS and JavaScript"), ("Excel", "Advanced", "Formulas and charts")],
     [("Machine Learning", "Beginner", "Want to start from zero")]),
    ("Meera Nair", "DEMO003", "AI and Machine Learning", 4,
     [("Machine Learning", "Advanced", "Models with scikit-learn"), ("Data Structures", "Intermediate", "Arrays to trees")],
     [("Communication Skills", "Intermediate", "Interview practice")]),
    ("Karthik Reddy", "DEMO004", "Electronics and Communication", 3,
     [("C Programming", "Advanced", "Pointers made simple"), ("Java", "Beginner", "Core Java basics")],
     [("Python", "Beginner", "For my final year project")]),
    ("Sana Khan", "DEMO005", "Business Administration", 2,
     [("Communication Skills", "Advanced", "Public speaking"), ("Graphic Design", "Intermediate", "Canva and Figma")],
     [("Excel", "Beginner", "Budgeting sheets")]),
]


def skill_id_for(name):
    row = db.fetch_one("SELECT skill_id FROM skills WHERE skill_name=%s", (name,))
    return row["skill_id"] if row else db.insert("INSERT INTO skills (skill_name) VALUES (%s)", (name,))


def main():
    password_hash = generate_password_hash("demo123", method="pbkdf2:sha256")
    for name, roll, dept, year, teach, learn in DEMO_STUDENTS:
        if db.fetch_one("SELECT student_id FROM students WHERE roll_number=%s", (roll,)):
            print("Skipped (already exists):", roll)
            continue
        student_id = db.insert(
            "INSERT INTO students (full_name, roll_number, department, year_of_study, password_hash) "
            "VALUES (%s, %s, %s, %s, %s)", (name, roll, dept, year, password_hash))
        for skill_type, items in (("teach", teach), ("learn", learn)):
            for skill_name, level, text in items:
                db.insert(
                    "INSERT INTO student_skills (student_id, skill_id, skill_type, skill_level, description) "
                    "VALUES (%s, %s, %s, %s, %s)", (student_id, skill_id_for(skill_name), skill_type, level, text))
        print("Added:", roll, name)
    print("Done. Log in with a demo roll number and the password demo123.")


if __name__ == "__main__":
    main()
