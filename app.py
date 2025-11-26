from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
from datetime import datetime
import os, uuid

app = Flask(__name__)
app.secret_key = "lostfound-secret"

# File upload setup
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database setup
engine = create_engine("sqlite:///lostfound.db", echo=False, future=True)

# Create table if not exists
with engine.begin() as conn:
    conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL,
            location TEXT,
            photo TEXT,
            contact TEXT,
            created_at TEXT
        )
    """)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    q = (request.args.get("q") or "").strip().lower()
    filter_status = request.args.get("status") or ""
    sql = "SELECT * FROM items WHERE 1=1"
    params = {}

    if q:
        sql += " AND (lower(title) LIKE :q OR lower(description) LIKE :q OR lower(location) LIKE :q)"
        params["q"] = f"%{q}%"

    if filter_status in ["Lost", "Found"]:
        sql += " AND status = :status"
        params["status"] = filter_status

    sql += " ORDER BY datetime(created_at) DESC"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return render_template("index.html", items=rows, q=q, status_filter=filter_status)

# Add item
@app.route("/add", methods=["GET", "POST"])
def add_item():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "")
        location = request.form.get("location", "").strip()
        contact = request.form.get("contact", "").strip()
        photo = request.files.get("photo")

        if not title or status not in ["Lost", "Found"]:
            flash("Title and Status are required.", "danger")
            return redirect(url_for("add_item"))

        filename = ""
        if photo and photo.filename:
            filename = secure_filename(f"{uuid.uuid4().hex}_{photo.filename}")
            photo.save(os.path.join(UPLOAD_FOLDER, filename))

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO items (id, title, description, status, location, contact, photo, created_at)
                VALUES (:id, :t, :d, :s, :l, :c, :p, :cr)
            """), {
                "id": str(uuid.uuid4()), "t": title, "d": description,
                "s": status, "l": location, "c": contact,
                "p": filename, "cr": now()
            })

        flash("Item added successfully!", "success")
        return redirect(url_for("index"))

    return render_template("form.html")

# Delete item
@app.post("/delete/<id>")
def delete_item(id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM items WHERE id=:id"), {"id": id})
    flash("Item deleted successfully.", "info")
    return redirect(url_for("index"))

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
