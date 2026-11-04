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
from werkzeug.middleware.proxy_fix import ProxyFix

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
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, 
                image_filename TEXT, 
                location TEXT,
                latitude REAL,
                longitude REAL,
                soil_condition TEXT, 
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
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
            "desc": "Sacred pilgrimage and bathing ghat, birthplace of poet Ramdhari Singh Dinkar.",
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
            "desc": "Important confluence zone where the Burhi Gandak meets the Ganga.",
            "link": "https://www.google.com/search?q=Khagaria+Ganga+riverfront",
        },
    ],
    "Bhagalpur": [
        {
            "name": "Vikramshila Dolphin Sanctuary",
            "desc": "India's only sanctuary protecting endangered Gangetic river dolphins.",
            "link": "https://www.google.com/search?q=Vikramshila+Gangetic+Dolphin+Sanctuary",
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
            "desc": "Scenic final stretch where the Ganga flows out of Bihar toward Jharkhand.",
            "link": "https://www.google.com/search?q=Manihari+Ghat+Katihar",
        },
    ],
}

# Approximate district centroids for automatic GPS-to-District mapping
DISTRICT_CENTROIDS = {
    "Buxar": (25.55, 83.98),
    "Bhojpur": (25.56, 84.66),
    "Saran": (25.77, 84.73),
    "Patna": (25.61, 85.14),
    "Vaishali": (25.68, 85.21),
    "Samastipur": (25.85, 85.78),
    "Begusarai": (25.42, 86.13),
    "Lakhisarai": (25.17, 86.08),
    "Munger": (25.37, 86.47),
    "Khagaria": (25.50, 86.48),
    "Bhagalpur": (25.25, 86.98),
    "Katihar": (25.54, 87.57)
}

def get_district_from_gps(lat, lon):
    """Maps GPS latitude and longitude to the nearest Ganga-flowing district in Bihar."""
    closest_district = "Patna"
    min_dist = float('inf')
    for district, (d_lat, d_lon) in DISTRICT_CENTROIDS.items():
        dist = (lat - d_lat)**2 + (lon - d_lon)**2
        if dist < min_dist:
            min_dist = dist
            closest_district = district
    return closest_district


# ==================== ROUTES ====================

@app.route("/")
@login_required
def index():
    with get_db_connection() as conn:
        submissions = conn.execute(
            "SELECT * FROM submissions WHERE user_id = ?", (session["user_id"],)
        ).fetchall()
    return render_template("index.html", submissions=submissions)


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            return render_template("login.html", error="Must provide username and password")

        with get_db_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

        if user is None or not check_password_hash(user["hash"], password):
            return render_template("login.html", error="Invalid username and/or password")

        session["user_id"] = user["id"]
        return redirect("/")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or password != confirmation:
            return render_template("register.html", error="Invalid input or passwords do not match")

        hash_password = generate_password_hash(password)
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, hash) VALUES (?, ?)",
                    (username, hash_password),
                )
                conn.commit()
                session["user_id"] = cursor.lastrowid
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username already exists")

        return redirect("/")

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        soil_condition = request.form.get("soil_condition")
        
        # Get GPS coordinates sent from the frontend JS
        try:
            latitude = float(request.form.get("latitude"))
            longitude = float(request.form.get("longitude"))
        except (TypeError, ValueError):
            latitude = 25.61  # Fallback Patna default
            longitude = 85.14

        # Automatically compute district from GPS
        detected_location = get_district_from_gps(latitude, longitude)

        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO submissions (user_id, image_filename, location, latitude, longitude, soil_condition)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session["user_id"], filename, detected_location, latitude, longitude, soil_condition),
            )
            conn.commit()

        # Fetch tourism spots for the calculated district (mapped to 'recommendations' for your success.html)
        recommendations = TOURISM_SPOTS.get(detected_location, [])
        
        return render_template(
            "success.html", 
            location=detected_location, 
            recommendations=recommendations, 
            soil=soil_condition,
            latitude=latitude,
            longitude=longitude,
            filename=filename
        )

    return render_template("upload.html")