from flask import Flask, render_template, request, redirect, session, flash
import sqlite3, os, smtplib
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "jobportal"




UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    db = get_db()

    # Users
    try:
        db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except:
        pass

    try:
        db.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except:
        pass

    # Jobs
    db.execute("""
    CREATE TABLE IF NOT EXISTS jobs(
        id INTEGER PRIMARY KEY,
        title TEXT,
        company TEXT
    )
    """)

    # Applications
    try:
        db.execute("ALTER TABLE applications ADD COLUMN status TEXT DEFAULT 'Pending'")
    except:
        pass

    db.execute("""
    CREATE TABLE IF NOT EXISTS applications(
        id INTEGER PRIMARY KEY,
        username TEXT,
        job_title TEXT,
        resume TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    db.execute("""
    INSERT OR IGNORE INTO users(username,password,is_admin,email)
    VALUES(?,?,?,?)
    """, ("admin", generate_password_hash("admin123"), 1, "yourgmail@gmail.com"))

    db.commit()
    db.close()

init_db()

# ---------------- EMAIL ----------------
def send_email(user, job):
    sender = "ajittorane2000@gmail.com"
    password = "mdwfyjufsoiagtmj"

    admin_email = "ajittorane2000@gmail.com"

    message = f"""Subject: New Job Application

User: {user}
Job: {job}

A new candidate has applied.
Login to admin panel to review.
"""

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, admin_email, message)
        server.quit()
    except:
        print("Email failed")

# ---------------- HELPERS ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            flash("Please login first!", "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    def wrapper(*args, **kwargs):
        if session.get('is_admin') != 1:
            flash("Admins only!", "danger")
            return redirect("/dashboard")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form['username']
        p = request.form['password']

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        db.close()

        if user and check_password_hash(user[2], p):
            session['user'] = user[1]
            session['is_admin'] = user[3] or 0
            flash("Login successful!", "success")
            return redirect("/admin" if session['is_admin'] == 1 else "/dashboard")
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form['username']
        p = generate_password_hash(request.form['password'])

        db = get_db()
        try:
            db.execute("INSERT INTO users(username,password) VALUES(?,?)", (u, p))
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect("/login")
        except:
            flash("Username already exists!", "danger")
        db.close()
    return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    if session.get('is_admin') == 1:
        # Admin sees admin panel instead
        return redirect("/admin")
    else:
        # Normal user sees only their applications
        apps = db.execute("SELECT * FROM applications WHERE username=?", (session['user'],)).fetchall()
    db.close()
    return render_template("user_dashboard.html", apps=apps)

@app.route("/jobs")
@login_required
def jobs():
    search = request.args.get("search")
    db = get_db()
    if search:
        jobs = db.execute("SELECT * FROM jobs WHERE title LIKE ?", ('%'+search+'%',)).fetchall()
    else:
        jobs = db.execute("SELECT * FROM jobs").fetchall()
    db.close()
    return render_template("index.html", jobs=jobs)


@app.route("/profile")
@login_required
def profile():
    db = get_db()
    apps = db.execute("""
        SELECT job_title, resume, status
        FROM applications
        WHERE username=?
    """, (session['user'],)).fetchall()
    db.close()

    return render_template("profile.html", apps=apps)

@app.route("/update_status/<int:app_id>/<status>")
@login_required
@admin_required
def update_status(app_id, status):
    db = get_db()
    db.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    db.commit()
    db.close()
    flash("Status updated", "success")
    return redirect("/admin")


@app.route("/my_applications")
@login_required
def my_applications():
    db = get_db()
    apps = db.execute("""
        SELECT * FROM applications
        WHERE username = ?
    """, (session['user'],)).fetchall()
    db.close()
    return render_template("applications.html", apps=apps)


# ---------------- POST JOB (ADMIN ONLY) ----------------
@app.route("/post_job", methods=["GET","POST"])
@login_required
@admin_required
def post_job():
    if request.method == "POST":
        t = request.form['title']
        c = request.form['company']
        db = get_db()
        db.execute("INSERT INTO jobs(title,company) VALUES(?,?)", (t, c))
        db.commit()
        db.close()
        flash("Job posted successfully!", "success")
        return redirect("/admin")
    return render_template("post_job.html")

@app.route("/apply/<int:job_id>", methods=["GET","POST"])
@login_required
def apply(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    db.close()

    if not job:
        flash("Job not found!", "danger")
        return redirect("/jobs")

    if request.method == "POST":
        file = request.files['resume']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            db = get_db()
            db.execute("INSERT INTO applications(username,job_title,resume) VALUES(?,?,?)",
                       (session['user'], job[1], filename))
            db.commit()
            db.close()

            send_email(session['user'], job[1])
            flash("Applied successfully!", "success")
            return redirect("/jobs")
        else:
            flash("Invalid file type! Only PDF/DOC/DOCX allowed.", "danger")

    return render_template("apply.html", job=job[1])

# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
@login_required
@admin_required
def admin():
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    jobs = db.execute("SELECT * FROM jobs").fetchall()
    apps = db.execute("SELECT * FROM applications").fetchall()  # all applications
    db.close()
    return render_template("admin.html", users=users, jobs=jobs, apps=apps)


# ---------------- DELETE JOB / APPLICATION (ADMIN ONLY) ----------------
@app.route("/delete_job/<int:id>")
@login_required
def delete_job(id):
    if session.get("is_admin") != 1:
        flash("Unauthorized access", "danger")
        return redirect("/dashboard")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Delete all applications for this job first
    c.execute("DELETE FROM applications WHERE job_id=?", (id,))

    # Delete the job
    c.execute("DELETE FROM jobs WHERE id=?", (id,))

    conn.commit()
    conn.close()

    flash("Job deleted successfully", "success")
    return redirect("/admin")


@app.route("/delete_application/<int:id>")
@login_required
def delete_application(id):
    if session.get("is_admin") != 1:
        flash("Unauthorized access", "danger")
        return redirect("/dashboard")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM applications WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Application deleted successfully", "success")
    return redirect("/admin")


@app.route("/edit_job/<int:id>", methods=["GET","POST"])
@login_required
@admin_required
def edit_job(id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (id,)).fetchone()

    if not job:
        flash("Job not found", "danger")
        return redirect("/admin")

    if request.method == "POST":
        title = request.form['title']
        company = request.form['company']

        db.execute("UPDATE jobs SET title=?, company=? WHERE id=?", 
                   (title, company, id))
        db.commit()
        db.close()
        flash("Job updated successfully!", "success")
        return redirect("/admin")

    db.close()
    return render_template("edit_job.html", job=job)





# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
