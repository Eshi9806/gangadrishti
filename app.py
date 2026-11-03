"""importing all required libraries"""
import os
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from helpers import login_required
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# 1. Initialize the Flask application once at the top
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-fallback-key-12345")

# Configure upload folder for Ganga photos
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
  return (
      "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
  )


def get_db_connection():
  conn = sqlite3.connect("ganga.db")
  # Row factory allows accessing columns by name
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  with get_db_connection() as conn:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY"
        " AUTOINCREMENT, username TEXT NOT NULL UNIQUE, hash TEXT NOT NULL);"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY"
        " AUTOINCREMENT, user_id INTEGER, image_filename TEXT, location TEXT,"
        " soil_condition TEXT, FOREIGN KEY(user_id) REFERENCES users(id));"
    )
    conn.commit()


# Initialize database tables on startup
init_db()

# Tourism mapping dictionary for locations along the Ganga
TOURISM_SPOTS = {
    "Buxar": [
        {
            "name": "Buxar Fort",
            "desc": "Historic fort situated on the banks of the Ganga.",
            "link": "https://www.google.com/search?q=Buxar+Fort+Bihar",
        },
        {
            "name": "Ram Rekha Ghat",
            "desc": "Sacred bathing ghat associated with ancient history.",
            "link": "https://www.google.com/search?q=Ram+Rekha+Ghat+Buxar",
        },
    ],
    "Bhojpur": [
        {
            "name": "Arrah Mahendru Ghat",
            "desc": "Important riverside location along the Ganga stretch.",
            "link": "https://www.google.com/search?q=Bhojpur+Ganga+river+spot",
        },
        {
            "name": "Aranya Devi Temple",
            "desc": "Prominent ancient temple located in Arrah, Bhojpur.",
            "link": "https://www.google.com/search?q=Aranya+Devi+Temple+Arrah",
        },
    ],
    "Saran": [
        {
            "name": "Chhapra Mauni Baba Ashram",
            "desc": "Spiritual retreat and gathering spot near the river bank.",
            "link": "https://www.google.com/search?q=Chhapra+Ganga+river+spots",
        },
        {
            "name": "Sonpur Confluence (Hariharkshetra)",
            "desc": "Famous confluence point where the Gandak meets the Ganga.",
            "link": "https://www.google.com/search?q=Sonpur+Hariharkshetra+Bihar",
        },
    ],
    "Patna": [
        {
            "name": "Golghar",
            "desc": "Historic granary with panoramic city and river views.",
            "link": "https://www.google.com/search?q=Golghar+Patna",
        },
        {
            "name": "Patna Sahib",
            "desc": "Sacred Sikh shrine located near the riverbank.",
            "link": "https://www.google.com/search?q=Takht+Sri+Harmandir+Ji+Patna+Sahib",
        },
        {
            "name": "Marine Drive Patna (Jethuli Ghat)",
            "desc": "Scenic riverside promenade along the Ganga.",
            "link": "https://www.google.com/search?q=Marine+Drive+Patna+Ganga",
        },
    ],
    "Vaishali": [
        {
            "name": "Hajipur Konhara Ghat",
            "desc": "Historic bathing ghat where the Gandak river meets the Ganga.",
            "link": "https://www.google.com/search?q=Konhara+Ghat+Hajipur",
        },
        {
            "name": "Phausar Ghat",
            "desc": "Peaceful riverside spot in Vaishali district.",
            "link": "https://www.google.com/search?q=Vaishali+Ganga+river+ghat",
        },
    ],
    "Samastipur": [
        {
            "name": "Mohanpur Ganga Ghats",
            "desc": "Active riverbank areas supporting local culture and trade.",
            "link": "https://www.google.com/search?q=Samastipur+Ganga+river+ghat",
        },
    ],
    "Begusarai": [
        {
            "name": "Simaria Ghat",
            "desc": (
                "Sacred pilgrimage and bathing ghat, birthplace of poet"
                " Ramdhari Singh Dinkar."
            ),
            "link": "https://www.google.com/search?q=Simaria+Ghat+Begusarai",
        },
        {
            "name": "Kanwar Lake Bird Sanctuary",
            "desc": "Asia's largest freshwater oxbow lake close to the Ganga basin.",
            "link": "https://www.google.com/search?q=Kanwar+Lake+Bird+Sanctuary",
        },
    ],
    "Lakhisarai": [
        {
            "name": "Surajgarha Ganga Bank",
            "desc": "Historic river banks where the Kiul river joins the Ganga.",
            "link": "https://www.google.com/search?q=Surajgarha+Lakhisarai+Ganga",
        },
    ],
    "Munger": [
        {
            "name": "Munger Fort",
            "desc": "Ancient fort complex dramatically overlooking the Ganga river.",
            "link": "https://www.google.com/search?q=Munger+Fort",
        },
        {
            "name": "Kastharani Ghat",
            "desc": "Renowned therapeutic bathing ghat believed to wash away fatigue.",
            "link": "https://www.google.com/search?q=Kastharani+Ghat+Munger",
        },
    ],
    "Khagaria": [
        {
            "name": "Gogri Jamalpur Riverfront",
            "desc": (
                "Important confluence zone where the Burhi Gandak meets the"
                " Ganga."
            ),
            "link": "https://www.google.com/search?q=Khagaria+Ganga+riverfront",
        },
    ],
    "Bhagalpur": [
        {
            "name": "Vikramshila Dolphin Sanctuary",
            "desc": (
                "India's only sanctuary protecting endangered Gangetic river"
                " dolphins."
            ),
            "link": (
                "https://www.google.com/search?q=Vikramshila+Gangetic+Dolphin+Sanctuary"
            ),
        },
        {
            "name": "Ajhgaynath Temple",
            "desc": "Ancient Shiva temple situated right on the riverbank in Sultanganj.",
            "link": "https://www.google.com/search?q=Sultanganj+Ajhgaynath+Temple",
        },
    ],
    "Katihar": [
        {
            "name": "Manihari Ghat",
            "desc": (
                "Scenic final stretch where the Ganga flows out of Bihar toward"
                " Jharkhand."
            ),
            "link": "https://www.google.com/search?q=Manihari+Ghat+Katihar",
        },
    ],
}


@app.route("/")
@login_required
def index():
  user_id = session.get("user_id")
  with get_db_connection() as conn:
    submissions = conn.execute(
        "SELECT * FROM submissions WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
  return render_template("index.html", submissions=submissions)


@app.route("/login", methods=["GET", "POST"])
def login():
  """Log user in"""
  session.clear()

  if request.method == "POST":
    if not request.form.get("username"):
      return "must provide username", 403
    elif not request.form.get("password"):
      return "must provide password", 403

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM users WHERE username = ?", (request.form.get("username"),)
    ).fetchall()
    conn.close()

    if len(rows) != 1 or not check_password_hash(
        rows[0]["hash"], request.form.get("password")
    ):
      return "invalid username and/or password", 403

    session["user_id"] = rows[0]["id"]
    return redirect("/")
  else:
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
  """Log user out"""
  session.clear()
  return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
  if request.method == "GET":
    return render_template("register.html")
  else:
    username = request.form.get("username")
    if not username:
      return "Provide Username", 400

    password = request.form.get("password")
    if not password:
      return "Provide a password", 400

    confirm_password = request.form.get("confirmation")
    if not confirm_password:
      return "Confirm Password", 400

    if password != confirm_password:
      return "Password not matched", 400

    conn = get_db_connection()
    if (
        len(
            conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchall()
        )
        > 0
    ):
      conn.close()
      return "Username already taken", 400

    password_hash = generate_password_hash(password)
    conn.execute(
        "INSERT INTO users (username, hash) VALUES (?, ?)",
        (username, password_hash),
    )
    conn.commit()
    conn.close()

    return redirect("/login")


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
  if request.method == "GET":
    return render_template("upload.html", locations=list(TOURISM_SPOTS.keys()))
  else:
    location = request.form.get("location")
    if not location:
      return "Provide Location", 400

    file = request.files.get("photo")
    if not file or not allowed_file(file.filename):
      return "Valid image file is required", 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    user_id = session.get("user_id")

    conn = get_db_connection()
    try:
      conn.execute(
          """
                INSERT INTO submissions (user_id, image_filename, location)
                VALUES (?, ?, ?)
                """,
          (user_id, filename, location),
      )
      conn.commit()
      flash("Photo and observation submitted successfully!", "success")
    finally:
      conn.close()

    recommendations = TOURISM_SPOTS.get(location, [])
    return render_template(
        "success.html",
        filename=filename,
        location=location,
        recommendations=recommendations,
    )



if __name__ == '__main__':
    # Add host='0.0.0.0' inside the run() function
    app.run(debug=True, host='0.0.0.0', port=5000)
