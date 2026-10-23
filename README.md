# SkillSwap: Campus Peer Learning Platform

SkillSwap is a website where college students teach skills they know and learn skills from other students.

Example: Student A teaches Python. Student B wants to learn Python. B finds A, sends a learning request, A accepts, they schedule a session, and after the session both can leave feedback and a rating.

**Technology:** HTML5, CSS3, Bootstrap 5, JavaScript, Python (Flask), MySQL, mysql-connector-python.

---

## Features

- Register and log in with a roll number (passwords are hashed)
- Dashboard with your numbers and quick links
- My Skills: add, edit and delete skills you teach or want to learn (Beginner, Intermediate, Advanced)
- Explore: find teachers, search, and filter by skill, department and level
- Learning requests: send, accept, reject, cancel, and track the status (Pending, Accepted, Rejected, Cancelled, Completed)
- Sessions: schedule after a request is accepted, mark completed or cancel
- Feedback: rate a completed session from 1 to 5 and leave a comment
- Profile: skills, average rating, recent feedback, and edit profile

---

## Setup on Windows (step by step)

### Step 1: Install Python (if you do not have it)
1. Go to https://www.python.org/downloads/ and download Python 3.10 or newer.
2. Run the installer. **Tick the box "Add python.exe to PATH"**, then click Install.
3. Check it: open Command Prompt and type `python --version`.

### Step 2: Install MySQL (if you do not have it)
1. Go to https://dev.mysql.com/downloads/installer/ and download MySQL Installer.
2. Choose "Developer Default" or "Server only". Keep the default port 3306.
3. When it asks for a **root password**, choose one and **write it down**. You need it in Step 7.
4. Finish the installer. MySQL now runs as a Windows service.

### Step 3: Unzip the project
Right-click `SkillSwap_Project.zip`, choose **Extract All**, and pick a folder such as `Documents`. You get a folder named `SkillSwap`.

### Step 4: Open it in VS Code
1. Open VS Code. Click **File > Open Folder** and choose the `SkillSwap` folder.
2. Open the terminal: **Terminal > New Terminal**.

### Step 5: Create and activate a virtual environment
In the VS Code terminal, run:

```
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` at the start of the line.
If PowerShell says "running scripts is disabled", run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
(Or use the Command Prompt terminal and run `venv\Scripts\activate.bat`.)

### Step 6: Install the packages
```
pip install -r requirements.txt
```

### Step 7: Create your .env file
1. Copy the example file:
   ```
   copy .env.example .env
   ```
2. Open the new `.env` file in VS Code and set:
   - `DB_PASSWORD` = your MySQL root password from Step 2
   - `SECRET_KEY` = any long random text
   - Keep `DB_NAME=skillswap`

### Step 8: Create the database and tables
```
python init_db.py
```
You should see: `Done. The 'skillswap' database and all tables are ready.`

Other ways to run `database.sql` (use only one):
- **MySQL Workbench:** File > Open SQL Script > pick `database.sql` > click the lightning button.
- **Terminal:** `mysql -u root -p < database.sql`

### Step 9 (optional): Add demo students
```
python seed_demo.py
```
This adds 5 demo students (roll numbers `DEMO001` to `DEMO005`, password `demo123`) so the Explore page has teachers.

### Step 10: Start the website
```
python app.py
```
Open your browser at **http://127.0.0.1:5000**

Press `Ctrl + C` in the terminal to stop the server.

---

## How to demo it (2 minutes)

1. Register yourself, or log in as `DEMO001` with `demo123`.
2. My Skills: add a skill you teach.
3. Open a second browser window (or a private window) and log in as another student.
4. Explore: find the first student and click **Request to learn**.
5. Switch back to the first student: Requests > Received > **Accept**.
6. Sessions: **Schedule session**, then **Mark completed**, then **Give feedback**.
7. Open the Profile page to see the rating.

---

## Troubleshooting

| Problem | What to do |
|---|---|
| `python` is not recognized | Reinstall Python and tick "Add python.exe to PATH". Then open a new terminal. |
| `ModuleNotFoundError: No module named 'flask'` | The virtual environment is not active. Run `venv\Scripts\activate`, then `pip install -r requirements.txt`. |
| `Access denied for user 'root'` | `DB_PASSWORD` in `.env` is wrong. Fix it and restart. |
| `Can't connect to MySQL server on 'localhost'` | MySQL is not running. Press Windows key, type "Services", find **MySQL80**, and click Start. |
| `Unknown database 'skillswap'` | Run `python init_db.py` first. |
| Page shows "Database problem" | Same checks as the three rows above. Then run `python init_db.py` again. |
| Page looks plain, without colors | Bootstrap and fonts load from the internet. Connect to the internet and refresh. |
| "Your page expired. Please try again." | Refresh the page and submit again. This happens after the server restarts. |
| Port 5000 is already in use | Close the other program, or change `port=5000` at the bottom of `app.py`. |
| `.env` changes are not used | Stop the server (`Ctrl + C`) and start it again. |

---

## Project structure

```
SkillSwap/
  app.py              All Flask routes (pages and actions)
  config.py           Settings read from .env, plus department and level lists
  database.py         Small helpers to run SQL safely with MySQL
  database.sql        All tables and sample skills
  init_db.py          Runs database.sql for you
  seed_demo.py        Optional demo students
  requirements.txt    Python packages
  .env.example        Copy to .env and fill in
  templates/          HTML pages (Jinja2 + Bootstrap 5)
  static/css/style.css, static/js/script.js, static/images/logo.svg
```

## Database tables

| Table | Purpose |
|---|---|
| students | Student accounts (unique roll number, hashed password) |
| skills | List of skills (unique names) |
| student_skills | Which student teaches or wants to learn which skill, and the level (unique per student, skill and type) |
| learning_requests | Requests from a learner to a teacher for one skill, with a status |
| sessions | Sessions created from accepted requests |
| feedback | One rating and comment per reviewer per session |

Relations: a student has many student_skills and many requests. A request can have sessions. A session can have two feedback rows (one per participant). Foreign keys and unique constraints are in `database.sql`.

## Security notes

- Passwords are hashed with Werkzeug. Plain passwords are never stored.
- All SQL uses parameters (`%s`), which prevents SQL injection.
- Pages that change data use POST and a hidden CSRF token.
- The backend checks that you own a skill, or are part of a request, session or feedback, before changing it.
- Secrets live in `.env`, which is listed in `.gitignore`.

## Deploying later

You need a host that runs Python and has a MySQL database (for example PythonAnywhere, or any VPS). Remember to:
1. Set `SECRET_KEY`, `DB_HOST`, `DB_USER`, `DB_PASSWORD` and `DB_NAME` as environment variables or in a `.env` file on the server.
2. Create the tables there with `python init_db.py`.
3. Set `FLASK_DEBUG=0` and run the app with a production server (such as gunicorn on Linux), not `python app.py`.
