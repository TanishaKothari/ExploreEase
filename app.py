from flask import Flask, flash, render_template, redirect, session, request
from werkzeug.security import check_password_hash, generate_password_hash
from utilities import login_required
from flask_session import Session
import os
from crewai import Agent, Task, Crew, Process
import mysql.connector

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# MySQL connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT"))
    )
    
con = get_db_connection()
cursor = con.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTO_INCREMENT NOT NULL, username VARCHAR(255) NOT NULL, 
    hash VARCHAR(255) NOT NULL)''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_input (
        id INTEGER PRIMARY KEY AUTO_INCREMENT NOT NULL, user_id INTEGER NOT NULL,
        destination VARCHAR(255) NOT NULL, budget INTEGER, duration INTEGER, pace VARCHAR(7),
        months VARCHAR(50), interests TEXT, dietary_restrictions TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id))''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_plans (id INTEGER PRIMARY KEY AUTO_INCREMENT NOT NULL,
        user_id INTEGER NOT NULL, plan_details TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id))''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTO_INCREMENT NOT NULL,
        user_id INTEGER NOT NULL, feedback TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id))''')

con.commit()
cursor.close()
con.close()

generated_itinerary = ''


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    return render_template('index.html')


# Validate login
@app.route("/login", methods=["GET", "POST"])
def login():
    con = get_db_connection()
    cursor = con.cursor()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Query database for username
        cursor.execute("SELECT * FROM users WHERE username = %s", (request.form.get("username"),))
        rows = cursor.fetchall()

        cursor.close()
        con.close()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            flash("Invalid username and/or password")
            return redirect("/login")
        
        # Remember which user has logged in
        session["user_id"] = rows[0][0]
        session["username"] = rows[0][1]

        # Redirect user to home page
        return redirect("/")
    
    return render_template("login.html")


# Log user out and delete stored user input
@app.route("/logout")
def logout():
    """Log user out"""
    # Delete stored user input
    con = get_db_connection()
    cursor = con.cursor()
    cursor.execute("DELETE FROM user_input WHERE user_id = %s", (session["user_id"],))
    con.commit()
    cursor.close()
    con.close()

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


# Create new user account and store in users table
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    con = get_db_connection()
    cursor = con.cursor()

    if request.method == "POST":
        # Get user inputs from the form
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validate inputs
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone() is not None:
            flash("Username already exists.")
            return redirect("/register")
        if password != confirmation:
            flash("Passwords do not match.")
            return redirect("/register")

        hashed_password = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, hash) VALUES(%s, %s)", (username, hashed_password))
        con.commit()
        return redirect("/login")

    cursor.close()
    con.close()
    return render_template("register.html")


# Update user input and generate itinerary as per new input
@app.route("/suggestions", methods=['GET', 'POST'])
@login_required
def get_suggestions():
    if request.method == 'POST':
        con = get_db_connection()
        cursor = con.cursor()
        # Get user input from the form
        input_dict = {
            'duration': request.form['duration'] + ' days',
            'destination': request.form['destination'],
            'months': request.form['months'],
            'budget': request.form['budget'],
            'pace': request.form['pace'],
            'interests': request.form.getlist('interests'),
            'dietary_restrictions': request.form.getlist('dietary_restrictions'),
        }
        cursor.execute("SELECT * FROM user_input WHERE user_id = %s", (session["user_id"],))
        user_input = cursor.fetchone()

        if user_input is not None:
            cursor.execute('''
                UPDATE user_input SET duration =%s, destination =%s, months =%s, budget =%s, pace =%s, interests =%s, dietary_restrictions =%s WHERE user_id =%s''',  
                (input_dict['duration'], input_dict['destination'], input_dict['months'], input_dict['budget'], input_dict['pace'],
                ','.join(input_dict['interests']), ','.join(input_dict['dietary_restrictions']), session["user_id"]))
            con.commit()
        else:
            cursor.execute('''
                INSERT INTO user_input (user_id, duration, destination, months, budget, pace, interests, dietary_restrictions)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''', 
                (session["user_id"], input_dict['duration'], input_dict['destination'], input_dict['months'], input_dict['budget'], input_dict['pace'],
                ','.join(input_dict['interests']), ','.join(input_dict['dietary_restrictions'])))
            con.commit()
        
        itinerary = generate_itinerary()

        cursor.close()
        con.close()

        return render_template('suggestions.html', generated_plan=itinerary)
    return redirect("/")


# Generate new itinerary using same input
@app.route("/regenerate", methods=['POST'])
@login_required
def regenerate():
    itinerary = generate_itinerary()
    return render_template('suggestions.html', generated_plan=itinerary)


# Save itinerary for user in saved_plans table
@app.route("/save_plan", methods=['POST'])
@login_required
def save_plan():
    # Retrieve the plan details from the form
    generated_itinerary = request.form.get('plan_details')

    # Store the plan in the database
    con = get_db_connection()
    cursor = con.cursor()
    cursor.execute('''
        INSERT INTO saved_plans (user_id, plan_details)
        VALUES (%s, %s)
    ''', (session["user_id"], generated_itinerary))
    con.commit()
    cursor.close()
    con.close()

    flash("Plan saved successfully!")
    return redirect("/")


# Show all saved itineraries for the user
@app.route("/saved_plans")
@login_required
def saved_plans():
    con = get_db_connection()
    cursor = con.cursor()
    cursor.execute("SELECT id, plan_details FROM saved_plans WHERE user_id = %s", (session["user_id"],))
    saved_plans = cursor.fetchall()
    cursor.close()
    con.close()

    return render_template('saves.html', saved_plans=saved_plans)


# Delete plan from saved_plans table
@app.route("/delete_saved_plans", methods=['POST'])
@login_required
def delete_saved_plans():
    plan_id = request.form.get('plan_id')
    con = get_db_connection()
    cursor = con.cursor()
    cursor.execute("DELETE FROM saved_plans WHERE id = %s AND user_id = %s", (plan_id, session["user_id"]))
    con.commit()
    cursor.close()
    con.close()
    flash("Plan deleted successfully!")
    return redirect("/")


# Allow user to give feedback on the itinerary and display all stored feedbacks below form
@app.route("/feedback", methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        con = get_db_connection()
        cursor = con.cursor()
        # Get user input from the form
        feedback = request.form.get("feedback")
        cursor.execute('''
            INSERT INTO feedback (user_id, feedback)
            VALUES (%s, %s)
        ''', (session["user_id"], feedback))
        con.commit()
        cursor.close()
        con.close()
        flash("Feedback submitted successfully!")
        return redirect("/")
    return render_template('feedback.html')


@app.route("/edit_profile", methods=['GET', 'POST'])
@login_required
def edit_profile():
    return render_template('edit_profile.html')


# Allow user to change password if all inputs are correct
@app.route("/change_password", methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        con = get_db_connection()
        cursor = con.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (session["username"],))
        rows = cursor.fetchall()

        # Ensure current password entered is correct
        if not check_password_hash(rows[0][2], request.form.get("current_password")):
            flash("Invalid password")
            return redirect("/edit_profile")
        
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_password")

        # Ensure new password and confirm new password match
        if new_password != confirm_new_password:
            flash("Passwords do not match")
            return redirect("/edit_profile")
        cursor.execute('''
            UPDATE users SET hash = %s WHERE id = %s
            ''', (generate_password_hash(new_password), session["user_id"]))
        con.commit()
        cursor.close()
        con.close()
        flash("Password changed successfully!")
        session.clear()
        return redirect("/login")
    return render_template('edit_profile.html')


# Allow user to change username if new one is available
@app.route("/change_username", methods=['GET', 'POST'])
@login_required
def change_username():
    if request.method == 'POST':
        con = get_db_connection()
        cursor = con.cursor()

        # Change username if new one is available
        new_username = request.form.get("new_username")
        cursor.execute("SELECT * FROM users WHERE username = %s", (new_username,))
        if cursor.fetchone() is not None:
            flash("Username already exists.")
            return redirect("/edit_profile")
        else:
            cursor.execute('''
                UPDATE users SET username = %s WHERE id = %s''', (new_username, session["user_id"]))
            con.commit()
            cursor.close()
            con.close()
            session["username"] = new_username
            flash("Username changed successfully!")
            return redirect("/")
    return render_template('edit_profile.html')


# Allow user to delete account and delete all data associated with it from users, user_input and saved_plans tables
@app.route("/delete_account", methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        con = get_db_connection()
        cursor = con.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s", (session["username"],))
        rows = cursor.fetchall()

        # Ensure current password entered is correct
        if not check_password_hash(rows[0][2], request.form.get("current_password")):
            flash("Invalid password")
            return redirect("/edit_profile")
        
        cursor.execute('''
            DELETE FROM user_input WHERE user_id = %s''', (session["user_id"],))
        cursor.execute('''
            DELETE FROM saved_plans WHERE user_id = %s''', (session["user_id"],))
        cursor.execute('''
            DELETE FROM feedback WHERE user_id = %s''', (session["user_id"],))
        cursor.execute('''
            DELETE FROM users WHERE id = %s''', (session["user_id"],))
        con.commit()
        cursor.close()
        con.close()

        # Forget user_id
        session.clear()

        flash("Account deleted successfully!")
        return redirect("/register")
    return render_template('edit_profile.html')


# Generate itinerary based on the user input found in the table user_input using openAI through groq API.
def generate_itinerary():
    con = get_db_connection()
    cursor = con.cursor()

    # Retrieve user input from the database
    cursor.execute("SELECT * FROM user_input WHERE user_id = %s", (session["user_id"],))
    user_input = cursor.fetchone()

    os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
    os.environ["OPENAI_MODEL_NAME"] = "llama3-70b-8192"
    os.environ["OPENAI_API_KEY"] = os.getenv('API_KEY')

    criteria = f"duration: {user_input[4]}, destination: {user_input[2]}, first month: {user_input[6]}, budget: {user_input[3]} USD, pace: {user_input[5]}, interests: {user_input[7]}, dietary restrictions: {user_input[8]}"

    generator = Agent(
        role = "travel itinerary generator",
        goal = "Create a personalized travel itinerary.",
        backstory = "You are an AI assistant. You have to create a personalized travel itinerary.",
        verbose = True,
        allow_delegation = False
    )

    generate_itinerary = Task(
        description = f"Generate a travel itinerary based on the following criteria: {criteria}. Also consider the places' weather for the duration of the trip. If no specific criteria is provided, generate based on the weather situations of different places.",
        agent = generator,
        expected_output = "a personalized travel itinerary"
    )

    crew = Crew(
        agents = [generator],
        tasks = [generate_itinerary],
        verbose = True,
        process = Process.sequential
    )

    itinerary = crew.kickoff()
    itinerary = itinerary.raw

    cursor.close()
    con.close()

    generated_itinerary = itinerary.replace('*', '')
    return generated_itinerary


if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(port=port)