"""SkillSwap - Campus Peer Learning Platform (Flask + MySQL).

Sections in this file:
  1. Setup and helpers        4. Skills
  2. Register / login         5. Learning requests
  3. Dashboard                6. Sessions, feedback, profile, errors
"""
import os
import re
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import errors as db_errors
from werkzeug.security import check_password_hash, generate_password_hash

import database as db
from config import Config, DEPARTMENTS, LEVELS

app = Flask(__name__)
app.config.from_object(Config)

ROLL_RE = re.compile(r"^[A-Z0-9][A-Z0-9/_-]{2,29}$")
HASH_METHOD = "pbkdf2:sha256"


# ----------------------------------------------------------------------------
# 1. Setup and helpers
# ----------------------------------------------------------------------------
def current_id():
    return session.get("student_id")


def login_required(view):
    """Send people who are not logged in to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_id() is None:
            flash("Please log in to continue.", "warning")
            if request.method == "GET":
                return redirect(url_for("login", next=request.path))
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def safe_next(url):
    """Only allow redirects to pages inside this website."""
    if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return None


def get_csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = get_csrf_token


@app.before_request
def csrf_protect():
    """Every POST form must carry the secret token from our own pages."""
    if request.method == "POST":
        token = session.get("_csrf")
        if not token or token != request.form.get("csrf_token"):
            flash("Your page expired. Please try again.", "warning")
            return redirect(url_for("dashboard" if current_id() else "login"))


@app.template_filter("dt")
def format_datetime(value, fmt="%d %b %Y, %I:%M %p"):
    if not value:
        return ""
    if isinstance(value, str):
        value = datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")
    return value.strftime(fmt)


def validate_student_form(form):
    """Check name, roll number, department and year. Returns a list of error texts."""
    errors = []
    form["roll_number"] = form["roll_number"].upper()
    if not 2 <= len(form["full_name"]) <= 100:
        errors.append("Full name must be 2 to 100 characters.")
    if not ROLL_RE.match(form["roll_number"]):
        errors.append("Roll number must be 3 to 30 characters: letters, numbers, / _ or -.")
    if form["department"] not in DEPARTMENTS:
        errors.append("Please choose your department.")
    if form["year_of_study"] not in ("1", "2", "3", "4", "5"):
        errors.append("Please choose your year of study (1 to 5).")
    return errors


# Reusable SQL pieces ---------------------------------------------------------
MY_SKILLS_SQL = """
    SELECT ss.student_skill_id, ss.student_id, ss.skill_id, k.skill_name,
           ss.skill_type, ss.skill_level, ss.description
    FROM student_skills ss
    JOIN skills k ON k.skill_id = ss.skill_id
    WHERE ss.student_id = %s
    ORDER BY k.skill_name
"""

REQUEST_SELECT = """
    SELECT r.request_id, r.learner_id, r.teacher_id, r.skill_id, r.message, r.status, r.created_at,
           k.skill_name,
           l.full_name AS learner_name, l.department AS learner_department,
           t.full_name AS teacher_name, t.department AS teacher_department
    FROM learning_requests r
    JOIN skills k ON k.skill_id = r.skill_id
    JOIN students l ON l.student_id = r.learner_id
    JOIN students t ON t.student_id = r.teacher_id
"""

SESSION_SELECT = """
    SELECT se.session_id, se.request_id, se.title, se.session_datetime, se.location, se.status,
           r.learner_id, r.teacher_id, k.skill_name,
           l.full_name AS learner_name, t.full_name AS teacher_name,
           (SELECT COUNT(*) FROM feedback f
             WHERE f.session_id = se.session_id AND f.reviewer_id = %s) AS my_feedback
    FROM sessions se
    JOIN learning_requests r ON r.request_id = se.request_id
    JOIN skills k ON k.skill_id = r.skill_id
    JOIN students l ON l.student_id = r.learner_id
    JOIN students t ON t.student_id = r.teacher_id
"""


def get_user_sessions(student_id):
    return db.fetch_all(
        SESSION_SELECT + " WHERE r.learner_id = %s OR r.teacher_id = %s ORDER BY se.session_datetime",
        (student_id, student_id, student_id))


# ----------------------------------------------------------------------------
# 2. Register / login / logout
# ----------------------------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("dashboard" if current_id() else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_id():
        return redirect(url_for("dashboard"))
    form = {}
    if request.method == "POST":
        form = {key: request.form.get(key, "").strip()
                for key in ("full_name", "roll_number", "department", "year_of_study")}
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        errors = validate_student_form(form)
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        elif password != confirm:
            errors.append("The two passwords do not match.")
        if not errors and db.fetch_one(
                "SELECT student_id FROM students WHERE roll_number = %s", (form["roll_number"],)):
            errors.append("This roll number is already registered. Try logging in.")
        if not errors:
            try:
                db.insert(
                    "INSERT INTO students (full_name, roll_number, department, year_of_study, password_hash) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (form["full_name"], form["roll_number"], form["department"],
                     int(form["year_of_study"]), generate_password_hash(password, method=HASH_METHOD)))
                flash("Account created. You can log in now.", "success")
                return redirect(url_for("login"))
            except db_errors.IntegrityError:
                errors.append("This roll number is already registered. Try logging in.")
        for error in errors:
            flash(error, "danger")
    return render_template("register.html", form=form, departments=DEPARTMENTS)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_id():
        return redirect(url_for("dashboard"))
    next_url = request.values.get("next", "")
    if request.method == "POST":
        roll = request.form.get("roll_number", "").strip().upper()
        password = request.form.get("password", "")
        if not roll or not password:
            flash("Enter your roll number and password.", "danger")
        else:
            student = db.fetch_one(
                "SELECT student_id, full_name, password_hash FROM students WHERE roll_number = %s", (roll,))
            if student and check_password_hash(student["password_hash"], password):
                session.clear()
                session["student_id"] = student["student_id"]
                session["name"] = student["full_name"]
                flash("Welcome back, " + student["full_name"] + "!", "success")
                return redirect(safe_next(next_url) or url_for("dashboard"))
            flash("Roll number or password is wrong.", "danger")
    return render_template("login.html", next_url=next_url)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ----------------------------------------------------------------------------
# 3. Dashboard
# ----------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    me = current_id()
    stats = db.fetch_one("""
        SELECT
          (SELECT COUNT(*) FROM student_skills WHERE student_id = %s AND skill_type = 'teach') AS teach_count,
          (SELECT COUNT(*) FROM student_skills WHERE student_id = %s AND skill_type = 'learn') AS learn_count,
          (SELECT COUNT(*) FROM learning_requests WHERE teacher_id = %s AND status = 'Pending') AS pending_count,
          (SELECT COUNT(*) FROM learning_requests
            WHERE (learner_id = %s OR teacher_id = %s) AND status = 'Accepted') AS accepted_count,
          (SELECT ROUND(AVG(rating), 1) FROM feedback WHERE reviewee_id = %s) AS avg_rating,
          (SELECT COUNT(*) FROM feedback WHERE reviewee_id = %s) AS rating_count
    """, (me, me, me, me, me, me, me))
    pending = db.fetch_all(
        REQUEST_SELECT + " WHERE r.teacher_id = %s AND r.status = 'Pending' ORDER BY r.request_id DESC LIMIT 4",
        (me,))
    upcoming = [s for s in get_user_sessions(me) if s["status"] == "Scheduled"][:4]
    return render_template("dashboard.html", stats=stats, pending=pending, upcoming=upcoming)


# ----------------------------------------------------------------------------
# 4. Skills
# ----------------------------------------------------------------------------
@app.route("/skills")
@login_required
def my_skills():
    rows = db.fetch_all(MY_SKILLS_SQL, (current_id(),))
    all_skills = db.fetch_all("SELECT skill_id, skill_name FROM skills ORDER BY skill_name")
    return render_template(
        "my_skills.html",
        teach_skills=[r for r in rows if r["skill_type"] == "teach"],
        learn_skills=[r for r in rows if r["skill_type"] == "learn"],
        all_skills=all_skills, levels=LEVELS)


@app.route("/skills/add", methods=["POST"])
@login_required
def add_skill():
    me = current_id()
    skill_type = request.form.get("skill_type", "")
    level = request.form.get("skill_level", "")
    description = request.form.get("description", "").strip()
    new_name = " ".join(request.form.get("new_skill", "").split())
    skill_id = request.form.get("skill_id", type=int)

    if skill_type not in ("teach", "learn") or level not in LEVELS:
        flash("Choose if you teach or want to learn this skill, and a level.", "danger")
        return redirect(url_for("my_skills"))
    if len(description) > 255:
        flash("The note can be 255 characters at most.", "danger")
        return redirect(url_for("my_skills"))

    if new_name:
        if not 2 <= len(new_name) <= 60:
            flash("A new skill name must be 2 to 60 characters.", "danger")
            return redirect(url_for("my_skills"))
        found = db.fetch_one("SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(%s)", (new_name,))
        skill_id = found["skill_id"] if found else db.insert(
            "INSERT INTO skills (skill_name) VALUES (%s)", (new_name,))
    elif not skill_id or not db.fetch_one("SELECT skill_id FROM skills WHERE skill_id = %s", (skill_id,)):
        flash("Choose a skill from the list or type a new one.", "danger")
        return redirect(url_for("my_skills"))

    if db.fetch_one(
            "SELECT student_skill_id FROM student_skills "
            "WHERE student_id = %s AND skill_id = %s AND skill_type = %s", (me, skill_id, skill_type)):
        flash("You already added this skill in that list.", "warning")
        return redirect(url_for("my_skills"))
    try:
        db.insert(
            "INSERT INTO student_skills (student_id, skill_id, skill_type, skill_level, description) "
            "VALUES (%s, %s, %s, %s, %s)", (me, skill_id, skill_type, level, description or None))
        flash("Skill added.", "success")
    except db_errors.IntegrityError:
        flash("You already added this skill in that list.", "warning")
    return redirect(url_for("my_skills"))


def get_my_skill_or_error(student_skill_id):
    row = db.fetch_one("SELECT student_skill_id, student_id FROM student_skills WHERE student_skill_id = %s",
                       (student_skill_id,))
    if row is None:
        abort(404)
    if row["student_id"] != current_id():
        abort(403)
    return row


@app.route("/skills/<int:student_skill_id>/edit", methods=["POST"])
@login_required
def edit_skill(student_skill_id):
    get_my_skill_or_error(student_skill_id)
    level = request.form.get("skill_level", "")
    description = request.form.get("description", "").strip()
    if level not in LEVELS or len(description) > 255:
        flash("Choose a valid level. The note can be 255 characters at most.", "danger")
        return redirect(url_for("my_skills"))
    db.execute("UPDATE student_skills SET skill_level = %s, description = %s WHERE student_skill_id = %s",
               (level, description or None, student_skill_id))
    flash("Skill updated.", "success")
    return redirect(url_for("my_skills"))


@app.route("/skills/<int:student_skill_id>/delete", methods=["POST"])
@login_required
def delete_skill(student_skill_id):
    get_my_skill_or_error(student_skill_id)
    db.execute("DELETE FROM student_skills WHERE student_skill_id = %s", (student_skill_id,))
    flash("Skill deleted.", "info")
    return redirect(url_for("my_skills"))


# ----------------------------------------------------------------------------
# 5. Explore and learning requests
# ----------------------------------------------------------------------------
@app.route("/explore")
@login_required
def explore():
    me = current_id()
    filters = {
        "q": request.args.get("q", "").strip(),
        "skill_id": request.args.get("skill_id", type=int),
        "department": request.args.get("department", "").strip(),
        "level": request.args.get("level", "").strip(),
    }
    sql = """
        SELECT s.student_id, s.full_name, s.department, s.year_of_study,
               k.skill_id, k.skill_name, ss.skill_level, ss.description,
               (SELECT ROUND(AVG(f.rating), 1) FROM feedback f WHERE f.reviewee_id = s.student_id) AS avg_rating,
               (SELECT COUNT(*) FROM feedback f WHERE f.reviewee_id = s.student_id) AS rating_count,
               (SELECT COUNT(*) FROM learning_requests r
                 WHERE r.learner_id = %s AND r.teacher_id = s.student_id
                   AND r.skill_id = k.skill_id AND r.status = 'Pending') AS already_requested
        FROM student_skills ss
        JOIN students s ON s.student_id = ss.student_id
        JOIN skills k ON k.skill_id = ss.skill_id
        WHERE ss.skill_type = 'teach' AND s.student_id <> %s
    """
    params = [me, me]
    if filters["q"]:
        sql += " AND (k.skill_name LIKE %s OR s.full_name LIKE %s)"
        params += ["%" + filters["q"] + "%"] * 2
    if filters["skill_id"]:
        sql += " AND k.skill_id = %s"
        params.append(filters["skill_id"])
    if filters["department"] in DEPARTMENTS:
        sql += " AND s.department = %s"
        params.append(filters["department"])
    if filters["level"] in LEVELS:
        sql += " AND ss.skill_level = %s"
        params.append(filters["level"])
    sql += " ORDER BY k.skill_name, s.full_name"
    results = db.fetch_all(sql, tuple(params))
    skills = db.fetch_all("SELECT skill_id, skill_name FROM skills ORDER BY skill_name")
    return render_template("explore.html", results=results, skills=skills, filters=filters,
                           departments=DEPARTMENTS, levels=LEVELS)


@app.route("/request/new/<int:teacher_id>", methods=["GET", "POST"])
@login_required
def send_request(teacher_id):
    me = current_id()
    if teacher_id == me:
        flash("You cannot send a learning request to yourself.", "warning")
        return redirect(url_for("explore"))
    teacher = db.fetch_one(
        "SELECT student_id, full_name, department, year_of_study FROM students WHERE student_id = %s",
        (teacher_id,))
    if teacher is None:
        abort(404)
    skills = db.fetch_all(
        "SELECT k.skill_id, k.skill_name, ss.skill_level FROM student_skills ss "
        "JOIN skills k ON k.skill_id = ss.skill_id "
        "WHERE ss.student_id = %s AND ss.skill_type = 'teach' ORDER BY k.skill_name", (teacher_id,))
    if not skills:
        flash(teacher["full_name"] + " is not teaching any skill right now.", "info")
        return redirect(url_for("explore"))

    selected = request.args.get("skill_id", type=int)
    message = ""
    if request.method == "POST":
        selected = request.form.get("skill_id", type=int)
        message = request.form.get("message", "").strip()
        if selected not in [s["skill_id"] for s in skills]:
            flash("Choose one of the skills this student teaches.", "danger")
        elif len(message) > 500:
            flash("The message can be 500 characters at most.", "danger")
        elif db.fetch_one(
                "SELECT request_id FROM learning_requests WHERE learner_id = %s AND teacher_id = %s "
                "AND skill_id = %s AND status = 'Pending'", (me, teacher_id, selected)):
            flash("You already have a pending request for this skill with this student.", "warning")
        else:
            db.insert("INSERT INTO learning_requests (learner_id, teacher_id, skill_id, message) "
                      "VALUES (%s, %s, %s, %s)", (me, teacher_id, selected, message or None))
            flash("Request sent to " + teacher["full_name"] + ".", "success")
            return redirect(url_for("sent_requests"))
    return render_template("send_request.html", teacher=teacher, skills=skills,
                           selected_skill=selected, message=message)


@app.route("/requests/sent")
@login_required
def sent_requests():
    rows = db.fetch_all(REQUEST_SELECT + " WHERE r.learner_id = %s ORDER BY r.request_id DESC", (current_id(),))
    return render_template("sent_requests.html", requests=rows)


@app.route("/requests/received")
@login_required
def received_requests():
    rows = db.fetch_all(REQUEST_SELECT + " WHERE r.teacher_id = %s ORDER BY r.request_id DESC", (current_id(),))
    return render_template("received_requests.html", requests=rows)


def change_request_status(request_id, new_status, owner_column):
    """Change a PENDING request. owner_column says who may do it:
    'teacher_id' (accept/reject) or 'learner_id' (cancel)."""
    req = db.fetch_one("SELECT request_id, learner_id, teacher_id, status FROM learning_requests "
                       "WHERE request_id = %s", (request_id,))
    if req is None:
        abort(404)
    if req[owner_column] != current_id():
        abort(403)
    if req["status"] != "Pending":
        flash("Only pending requests can be changed. This one is " + req["status"] + ".", "warning")
        return False
    db.execute("UPDATE learning_requests SET status = %s WHERE request_id = %s AND status = 'Pending'",
               (new_status, request_id))
    return True


@app.route("/requests/<int:request_id>/accept", methods=["POST"])
@login_required
def accept_request(request_id):
    if change_request_status(request_id, "Accepted", "teacher_id"):
        flash("Request accepted. You can now schedule a session.", "success")
    return redirect(url_for("received_requests"))


@app.route("/requests/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_request(request_id):
    if change_request_status(request_id, "Rejected", "teacher_id"):
        flash("Request rejected.", "info")
    return redirect(url_for("received_requests"))


@app.route("/requests/<int:request_id>/cancel", methods=["POST"])
@login_required
def cancel_request(request_id):
    if change_request_status(request_id, "Cancelled", "learner_id"):
        flash("Request cancelled.", "info")
    return redirect(url_for("sent_requests"))


# ----------------------------------------------------------------------------
# 6. Sessions, feedback, profile
# ----------------------------------------------------------------------------
def load_session(session_id):
    """Load a session and make sure the logged-in student is part of it."""
    me = current_id()
    row = db.fetch_one(SESSION_SELECT + " WHERE se.session_id = %s", (me, session_id))
    if row is None:
        abort(404)
    if me not in (row["learner_id"], row["teacher_id"]):
        abort(403)
    return row


@app.route("/sessions")
@login_required
def sessions_list():
    me = current_id()
    all_sessions = get_user_sessions(me)
    upcoming = [s for s in all_sessions if s["status"] == "Scheduled"]
    past = [s for s in all_sessions if s["status"] != "Scheduled"][::-1]
    ready = db.fetch_all(
        REQUEST_SELECT + " WHERE (r.learner_id = %s OR r.teacher_id = %s) AND r.status = 'Accepted' "
        "ORDER BY r.request_id DESC", (me, me))
    return render_template("sessions.html", upcoming=upcoming, past=past, ready=ready)


@app.route("/sessions/new/<int:request_id>", methods=["GET", "POST"])
@login_required
def schedule_session(request_id):
    me = current_id()
    req = db.fetch_one(REQUEST_SELECT + " WHERE r.request_id = %s", (request_id,))
    if req is None:
        abort(404)
    if me not in (req["learner_id"], req["teacher_id"]):
        abort(403)
    if req["status"] != "Accepted":
        flash("You can only schedule a session for an accepted request.", "warning")
        return redirect(url_for("sessions_list"))

    form = {"title": req["skill_name"] + " session", "when": "", "location": ""}
    if request.method == "POST":
        form = {"title": request.form.get("title", "").strip(),
                "when": request.form.get("when", "").strip(),
                "location": request.form.get("location", "").strip()}
        errors = []
        if not 3 <= len(form["title"]) <= 100:
            errors.append("Session title must be 3 to 100 characters.")
        if len(form["location"]) > 255:
            errors.append("Location or link can be 255 characters at most.")
        when = None
        try:
            when = datetime.strptime(form["when"], "%Y-%m-%dT%H:%M")
            if when < datetime.now():
                errors.append("Pick a date and time in the future.")
        except ValueError:
            errors.append("Pick a valid date and time.")
        if not errors:
            db.insert("INSERT INTO sessions (request_id, title, session_datetime, location) "
                      "VALUES (%s, %s, %s, %s)", (request_id, form["title"], when, form["location"] or None))
            flash("Session scheduled.", "success")
            return redirect(url_for("sessions_list"))
        for error in errors:
            flash(error, "danger")
    return render_template("schedule_session.html", req=req, form=form)


@app.route("/sessions/<int:session_id>/complete", methods=["POST"])
@login_required
def complete_session(session_id):
    sess = load_session(session_id)
    if sess["status"] != "Scheduled":
        flash("Only scheduled sessions can be marked as completed.", "warning")
        return redirect(url_for("sessions_list"))
    db.execute("UPDATE sessions SET status = 'Completed' WHERE session_id = %s", (session_id,))
    left = db.fetch_one("SELECT COUNT(*) AS n FROM sessions WHERE request_id = %s AND status = 'Scheduled'",
                        (sess["request_id"],))
    if left["n"] == 0:
        db.execute("UPDATE learning_requests SET status = 'Completed' WHERE request_id = %s", (sess["request_id"],))
    flash("Session marked as completed. You can now leave feedback.", "success")
    return redirect(url_for("sessions_list"))


@app.route("/sessions/<int:session_id>/cancel", methods=["POST"])
@login_required
def cancel_session(session_id):
    sess = load_session(session_id)
    if sess["status"] != "Scheduled":
        flash("Only scheduled sessions can be cancelled.", "warning")
    else:
        db.execute("UPDATE sessions SET status = 'Cancelled' WHERE session_id = %s", (session_id,))
        flash("Session cancelled.", "info")
    return redirect(url_for("sessions_list"))


@app.route("/feedback/<int:session_id>", methods=["GET", "POST"])
@login_required
def feedback_page(session_id):
    me = current_id()
    sess = load_session(session_id)
    if sess["status"] != "Completed":
        flash("Feedback is possible only after a session is completed.", "warning")
        return redirect(url_for("sessions_list"))
    other_id = sess["teacher_id"] if sess["learner_id"] == me else sess["learner_id"]
    other_name = sess["teacher_name"] if sess["learner_id"] == me else sess["learner_name"]
    mine = db.fetch_one("SELECT rating, comments FROM feedback WHERE session_id = %s AND reviewer_id = %s",
                        (session_id, me))

    if request.method == "POST":
        rating = request.form.get("rating", type=int)
        comments = request.form.get("comments", "").strip()
        if mine:
            flash("You already gave feedback for this session.", "warning")
        elif rating is None or not 1 <= rating <= 5:
            flash("Choose a rating from 1 to 5.", "danger")
        elif len(comments) > 500:
            flash("Comments can be 500 characters at most.", "danger")
        else:
            try:
                db.insert("INSERT INTO feedback (session_id, reviewer_id, reviewee_id, rating, comments) "
                          "VALUES (%s, %s, %s, %s, %s)", (session_id, me, other_id, rating, comments or None))
                flash("Thank you! Your feedback was saved.", "success")
                return redirect(url_for("sessions_list"))
            except db_errors.IntegrityError:
                flash("You already gave feedback for this session.", "warning")
        return redirect(url_for("feedback_page", session_id=session_id))
    return render_template("feedback.html", sess=sess, other_name=other_name, mine=mine)


@app.route("/profile")
@app.route("/profile/<int:student_id>")
@login_required
def profile(student_id=None):
    me = current_id()
    student_id = student_id or me
    student = db.fetch_one(
        "SELECT student_id, full_name, roll_number, department, year_of_study, bio "
        "FROM students WHERE student_id = %s", (student_id,))
    if student is None:
        abort(404)
    skills = db.fetch_all(MY_SKILLS_SQL, (student_id,))
    rating = db.fetch_one("SELECT ROUND(AVG(rating), 1) AS avg_rating, COUNT(*) AS rating_count "
                          "FROM feedback WHERE reviewee_id = %s", (student_id,))
    reviews = db.fetch_all(
        "SELECT f.rating, f.comments, f.created_at, s.full_name AS reviewer_name, k.skill_name "
        "FROM feedback f "
        "JOIN students s ON s.student_id = f.reviewer_id "
        "JOIN sessions se ON se.session_id = f.session_id "
        "JOIN learning_requests r ON r.request_id = se.request_id "
        "JOIN skills k ON k.skill_id = r.skill_id "
        "WHERE f.reviewee_id = %s ORDER BY f.feedback_id DESC LIMIT 5", (student_id,))
    return render_template(
        "profile.html", student=student, is_self=(student_id == me),
        teach=[s for s in skills if s["skill_type"] == "teach"],
        learn=[s for s in skills if s["skill_type"] == "learn"],
        avg_rating=rating["avg_rating"], rating_count=rating["rating_count"], reviews=reviews)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    me = current_id()
    if request.method == "POST":
        form = {key: request.form.get(key, "").strip()
                for key in ("full_name", "roll_number", "department", "year_of_study", "bio")}
        errors = validate_student_form(form)
        if len(form["bio"]) > 255:
            errors.append("The bio can be 255 characters at most.")
        if not errors and db.fetch_one(
                "SELECT student_id FROM students WHERE roll_number = %s AND student_id <> %s",
                (form["roll_number"], me)):
            errors.append("Another student already uses this roll number.")
        if not errors:
            try:
                db.execute(
                    "UPDATE students SET full_name = %s, roll_number = %s, department = %s, "
                    "year_of_study = %s, bio = %s WHERE student_id = %s",
                    (form["full_name"], form["roll_number"], form["department"],
                     int(form["year_of_study"]), form["bio"] or None, me))
                session["name"] = form["full_name"]
                flash("Profile updated.", "success")
                return redirect(url_for("profile"))
            except db_errors.IntegrityError:
                errors.append("Another student already uses this roll number.")
        for error in errors:
            flash(error, "danger")
    else:
        form = db.fetch_one("SELECT full_name, roll_number, department, year_of_study, bio "
                            "FROM students WHERE student_id = %s", (me,))
        form["year_of_study"] = str(form["year_of_study"])
        form["bio"] = form["bio"] or ""
    return render_template("edit_profile.html", form=form, departments=DEPARTMENTS)


# ----------------------------------------------------------------------------
# Error pages
# ----------------------------------------------------------------------------
def show_error(code, title, message):
    return render_template("error.html", code=code, title=title, message=message), code


@app.errorhandler(403)
def forbidden(_error):
    return show_error(403, "This is not yours", "You do not have permission to open or change this.")


@app.errorhandler(404)
def not_found(_error):
    return show_error(404, "Page not found", "We could not find what you were looking for.")


@app.errorhandler(db_errors.Error)
def database_problem(error):
    app.logger.error("Database error: %s", error)
    return show_error(500, "Database problem",
                      "The app could not talk to MySQL. Check that MySQL is running and that the "
                      "values in your .env file are correct. Then run: python init_db.py")


@app.errorhandler(500)
def server_error(_error):
    return show_error(500, "Something went wrong", "Please go back and try again.")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG", "1") == "1")
