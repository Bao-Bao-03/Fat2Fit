from datetime import datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    session,
    send_from_directory,
)
from geopy.distance import distance
from werkzeug.security import generate_password_hash, check_password_hash
import folium
import pandas as pd
import sqlite3

app = Flask(__name__)
DATABASE = "users.db"
app.secret_key = "your_secret_key"

path = "coord.csv"

# get the start time from data
def getStartTime(path):
    df = pd.read_csv(path)
    return df.iloc[0, 0].split("T")[0] + "T" + df.iloc[0, 0].split("T")[1][:8]


# function use to handle database connections in Flask application
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


# close connection
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# create database if not exists
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                gender TEXT,
                age INTEGER,
                weight REAL,
                height REAL
            )
        """
        )
        db.commit()


# 404 page
@app.route("/404")
def wip():
    return render_template("404.html")


# home page
@app.route("/")
def home():
    return render_template("home.html")


# sign page
@app.route("/sign")
def sign():
    return render_template("signInUp.html")


# signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")

    if not email or not username or not password:
        flash("Please fill out all fields", "danger")
        return redirect(url_for("sign"))

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, username, password) VALUES (?, ?, ?)",
            (email, username, hashed_password),
        )
        db.commit()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(url_for("landing"))
    except sqlite3.IntegrityError as e:
        flash("Email already exists!", "danger")
        return redirect(url_for("sign"))
    except Exception as e:
        flash("An error occurred during registration.", "danger")
        return redirect(url_for("sign"))


# login
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Please fill out all fields", "danger")
        return redirect(url_for("sign"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash("Login successful!", "success")
        return redirect(url_for("profile"))
    else:
        flash("Invalid email or password.Try again.", "danger")
        return redirect(url_for("sign"))


# forgot password page
@app.route("/forgot_password")
def forgot_password():
    return render_template("forget_pass.html")


# reset password
@app.route("/reset_password", methods=["POST"])
def reset_password():
    email = request.form.get("email")
    new_password = request.form.get("password")

    if not email or not new_password:
        flash("Please fill out all fields", "danger")
        return redirect(url_for("forgot_password"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if user:
        hashed_password = generate_password_hash(new_password, method="pbkdf2:sha256")
        try:
            cursor.execute(
                "UPDATE users SET password = ? WHERE email = ?",
                (hashed_password, email),
            )
            db.commit()
            flash("Your password has been updated successfully.", "success")
            return redirect(url_for("sign"))
        except Exception as e:
            flash("An error occurred while updating your password.", "danger")
            return redirect(url_for("forgot_password"))
    else:
        flash("No account found with that email address.", "danger")
        return redirect(url_for("forgot_password"))


# landing page
@app.route("/landing")
def landing():
    return render_template("landing.html")


# add user's information
@app.route("/stat", methods=["POST"])
def stat():
    if "user_id" not in session:
        flash("Please log in to update your information.", "danger")
        return redirect(url_for("sign"))

    user_id = session["user_id"]
    gender = request.form.get("gender")
    age = request.form.get("age")
    weight = request.form.get("weight")
    height = request.form.get("height")

    if not gender or not age or not weight or not height:
        flash("Please fill out all fields", "danger")
        return redirect(url_for("landing"))

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE users SET gender = ?, age = ?, weight = ?, height = ?
            WHERE id = ?
        """,
            (gender, int(age), float(weight), float(height), user_id),
        )
        db.commit()

        return redirect(url_for("profile"))

    except Exception as e:
        flash("An error occurred while updating your information.", "danger")
        return redirect(url_for("landing"))


# profile page
@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("Please log in to access your profile.", "danger")
        return redirect(url_for("sign"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT username, email, gender, age, weight, height FROM users WHERE id = ?",
        (session["user_id"],),
    )
    user = cursor.fetchone()
    return render_template("profile1.html", user=user)


# edit user's information
@app.route("/stat2", methods=["POST"])
def stat2():
    if "user_id" not in session:
        flash("Please log in to update your information.", "danger")
        return redirect(url_for("sign"))

    user_id = session["user_id"]
    gender = request.form.get("gender")
    age = request.form.get("age")
    weight = request.form.get("weight")
    height = request.form.get("height")

    if not gender or not age or not weight or not height:
        flash("Please fill out all fields", "danger")
        return redirect(url_for("landing"))

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE users SET gender = ?, age = ?, weight = ?, height = ?
            WHERE id = ?
        """,
            (gender, int(age), float(weight), float(height), user_id),
        )
        db.commit()

        flash("Your information has been updated successfully.", "success")
        return redirect(url_for("profile"))

    except Exception as e:
        flash("An error occurred while updating your information.", "danger")
        return redirect(url_for("profile"))


# function calculate the time limit
def timelimit(path):
    df = pd.read_csv(path)
    datetime_start = df.iloc[0, 0].split("T")[0] + " " + df.iloc[0, 0].split("T")[1][:8]
    datetime_end = df.iloc[-1, 0].split("T")[0] + " " + df.iloc[-1, 0].split("T")[1][:8]

    datetime_format = "%Y-%m-%d %H:%M:%S"

    datetime_start = datetime.strptime(datetime_start, datetime_format)
    datetime_end = datetime.strptime(datetime_end, datetime_format)

    time_difference = datetime_end - datetime_start
    return time_difference


# tracking page
@app.route("/track")
def track():
    if "user_id" not in session:
        flash("Please log in to access your profile.", "danger")
        return redirect(url_for("sign"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT username, email, gender, age, weight, height FROM users WHERE id = ?",
        (session["user_id"],),
    )
    user = cursor.fetchone()
    
    time_limit = str(timelimit(path)) #! set time limit

    return render_template("tracking.html", user=user, time_limit=time_limit)


# add map to the tracking page
@app.route("/map")
def map():
    return send_from_directory("templates", "route_map.html")


# function to calculate the total distance ran/walked and show it on a map
def get_distance(h, m, s):
    df = pd.read_csv(path)
    start_time = str(getStartTime(path))
    start_datetime = datetime.fromisoformat(str(getStartTime(path)))

    df["lat"] = df["lat"].str.extract(r'lat":(\d+\.\d+)').astype(float)
    df["lon"] = df["lon"].str.extract(r"lon:(\d+\.\d+)").astype(float)
    df["time"] = pd.to_datetime(df["time"])

    hour = int(h)
    minute = int(m)
    second = int(s)

    user_time = start_datetime + timedelta(hours=hour, minutes=minute, seconds=second)

    end_time = user_time.strftime("%Y-%m-%dT%H:%M:%S")
    filtered_df = df[(df["time"] >= start_time) & (df["time"] <= end_time)]
    coordinates = list(zip(filtered_df["lat"], filtered_df["lon"]))

    total_dis = 0
    for i in range(len(coordinates) - 1):
        point_1 = coordinates[i]
        point_2 = coordinates[i + 1]
        total_dis += distance(point_1, point_2).km

    map_center = [df["lat"].mean(), df["lon"].mean()]
    mymap = folium.Map(location=map_center, zoom_start=15)
    folium.PolyLine(locations=coordinates, color="blue", weight=4).add_to(mymap)
    mymap.save("templates/route_map.html")
    return total_dis


# function calculate bmr
def calculate_bmr(weight, height_cm, age, gender):
    if gender == "Male":
        return 88.362 + (13.397 * weight) + (4.799 * height_cm) - (5.677 * age)
    elif gender == "Female":
        return 447.593 + (9.247 * weight) + (3.098 * height_cm) - (4.330 * age)
    else:
        raise ValueError("Invalid gender. Please choose 'male' or 'female'.")


# function calculate met base on speed
def determine_met(speed_kmh):
    speed_mph = speed_kmh * 0.621371
    if speed_mph < 2:
        return 2 # Light walking
    elif 3.5 <= speed_mph < 5:
        return 4.5  # Brisk walking
    elif 5 <= speed_mph < 7:
        return 8  # Light running
    else:
        return 11.5 # Running fast


# function calculate the calories burned
def calculate_calories(weight, time_minutes, distance_km, gender, age, height_cm):
    speed_km_h = distance_km / (time_minutes / 60)
    met = determine_met(speed_km_h)
    calories_burned = met * weight * (time_minutes / 60)
    bmr = calculate_bmr(weight, height_cm, age, gender)
    adjusted_calories_burned = calories_burned * (
        bmr / 2000
    )  # 2000 is the average daily calorie needs
    return adjusted_calories_burned


# function calculate pace from met
def getpace(met):
    if met < 5.6:
        return "Slow"
    elif met < 7.2:
        return "Moderate"
    elif met >= 7.2:
        return "Brisk"


# function calculate stridelength from met
def getstridelength(gender, pace, height):
    if gender == "Male":
        stride_factor = 0.413
    else:
        stride_factor = 0.415

    stride_length = height * stride_factor

    if pace == "Moderate":
        stride_length *= 1.5
    if pace == "Brisk":
        stride_length *= 1.95

    return stride_length


#! calculate
@app.route("/calculate", methods=["POST"])
def cal():
    # ? ----------------------------------------------------------- input from user "time": h(hours), m(minutes), s(seconds)
    if request.method == "POST":
        h = int(request.form["hour"])
        m = int(request.form["minute"])
        s = int(request.form["second"])

    # ? ------------------------------------------------------------ calculate time (min)
    time_mins = h * 60 + m + s / 60
    time_hours = h + m * 60 + s * 60 * 60

    # ? ------------------------------------------------------------ calculate the distance: dis(km)
    dis_km = round(get_distance(h, m, s), 2)

    # ? ------------------------------------------------------------ database: username, email, gender, age, weight, height
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT email, username, gender, age, weight, height FROM users WHERE id = ?",
        (session["user_id"],),
    )
    user = cursor.fetchone()
    email, username, gender, age, weight, height = user

    # ? ------------------------------------------------------------ calculate speed(km/h)
    speed_kmh = dis_km / time_hours

    # ? ------------------------------------------------------------ calculate met
    met = determine_met(speed_kmh)

    # ? ------------------------------------------------------------ calories burned (new)
    calories = calculate_calories(weight, time_mins, dis_km, gender, age, height)
    calories2 = (((0.035 * weight) + (((speed_kmh * 1000 / 3600) ** 2) / height))) * 0.029 * weight * time_mins 
    
    # ? ------------------------------------------------------------ from met -> pace -> stride_lenght
    pace = getpace(met)
    stride_length = getstridelength(gender, pace, height)

    # ? ------------------------------------------------------------ calculate steps
    steps = round(dis_km * 1000 / (stride_length / 100), 1)

    history = []
    result = {"Hour": h, "Minute": m, "Second": s}
    history.append(result)

    time_limit = str(timelimit(path))
    
    return render_template(
        "tracking.html",
        user=user,
        dis=dis_km,
        steps=int(round(steps,0)),
        pace=pace,
        calo_per_hour=round(calories2,3),
        history=history,
        time_limit=time_limit
    )


# logout
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
