import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import random

from fpdf import FPDF
import base64

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect('fitness_app.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        name TEXT,
        email TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        workout_type TEXT,
        duration INTEGER,
        calories_burned INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        challenge_name TEXT,
        goal INTEGER,
        challenge_type TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS challenge_participants (
        user_id INTEGER,
        challenge_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(challenge_id) REFERENCES challenges(id)
    )
''')

# ---------- AUTHENTICATION FUNCTIONS ----------
def check_user(username):
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()

def add_user(username, password, name, email):
    cursor.execute('INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)',
                   (username, password, name, email))
    conn.commit()

def verify_user(username, password):
    user = check_user(username)
    if user and user[2] == password:
        return user
    return None

# ---------- WORKOUT FUNCTIONS ----------
def log_workout(user_id, workout_type, duration, calories_burned):
    cursor.execute('INSERT INTO workouts (user_id, workout_type, duration, calories_burned) VALUES (?, ?, ?, ?)',
                   (user_id, workout_type, duration, calories_burned))
    conn.commit()

# ---------- CHALLENGE FUNCTIONS ----------
def create_challenge(user_id, challenge_name, goal, challenge_type):
    cursor.execute('INSERT INTO challenges (user_id, challenge_name, goal, challenge_type) VALUES (?, ?, ?, ?)',
                   (user_id, challenge_name, goal, challenge_type))
    conn.commit()

def join_challenge(user_id, challenge_id):
    cursor.execute('INSERT INTO challenge_participants (user_id, challenge_id) VALUES (?, ?)',
                   (user_id, challenge_id))
    conn.commit()

def display_leaderboard():
    cursor.execute('''
        SELECT users.username, SUM(workouts.calories_burned) AS total_calories
        FROM workouts
        JOIN users ON workouts.user_id = users.id
        GROUP BY users.username
        ORDER BY total_calories DESC
    ''')
    leaderboard = cursor.fetchall()
    st.subheader("Leaderboard")
    for i, entry in enumerate(leaderboard, 1):
        st.write(f"{i}. {entry[0]} - {entry[1]} calories burned")

# ---------- DASHBOARD ----------
def user_dashboard(user_id):
    st.header("🏋️‍♀️ Your Fitness Dashboard")
    cursor.execute('SELECT workout_type, duration, calories_burned FROM workouts WHERE user_id = ?', (user_id,))
    data = cursor.fetchall()
    if not data:
        st.info("You haven't logged any workouts yet.")
        return
    df = pd.DataFrame(data, columns=["Workout", "Duration", "Calories"])
    st.metric("Total Workouts", len(df))
    st.metric("Total Duration (min)", int(df["Duration"].sum()))
    st.metric("Total Calories Burned", int(df["Calories"].sum()))

    st.subheader("Calories Burned by Workout Type")
    st.bar_chart(df.groupby("Workout")["Calories"].sum())

    st.subheader("Workout Duration Trend")
    st.line_chart(df["Duration"])

    st.subheader("Workout Type Distribution")
    fig, ax = plt.subplots()
    df["Workout"].value_counts().plot.pie(autopct="%1.1f%%", ax=ax)
    st.pyplot(fig)

    st.subheader("Workout History")
    st.dataframe(df)

def show_challenge_progress(user_id):
    st.subheader("Your Challenge Progress")
    challenges = [
        {"name": "10K Run", "goal": 10000, "achieved": 3000},
        {"name": "500 Pushups", "goal": 500, "achieved": 120},
    ]
    for challenge in challenges:
        st.write(f"**{challenge['name']}**")
        progress = challenge["achieved"] / challenge["goal"]
        st.progress(progress)
        st.caption(f"{challenge['achieved']} out of {challenge['goal']} completed")

# ---------- WORKOUT PAGE ----------
def workout_page(user_id):
    st.title("Log Your Workout")
    workout_type = st.selectbox("Workout Type", ["","Running", "Cycling", "Strength Training", "Yoga", "Other"])
    duration = st.number_input("Duration (minutes)", min_value=1)
    calories_burned = st.number_input("Calories Burned", min_value=0)
    if st.button("Log Workout"):
        log_workout(user_id, workout_type, duration, calories_burned)
        st.success(f"{workout_type} workout logged!")

# ---------- CHALLENGES PAGE ----------
def challenge_page(user_id):
    st.title("Fitness Challenges")
    challenge_name = st.text_input("Challenge Name")
    goal = st.number_input("Goal", min_value=1)
    challenge_type = st.selectbox("Challenge Type", ["","Time-based", "Reps-based", "Distance-based"])

    if st.button("Create Challenge"):
        create_challenge(user_id, challenge_name, goal, challenge_type)
        st.success(f"Challenge '{challenge_name}' created!")

    st.subheader("Join Existing Challenges")
    challenges = [(1, "Running Challenge", 100), (2, "Cycling Challenge", 50)]
    for cid, name, goal in challenges:
        st.write(f"{name} - Goal: {goal}")
        if st.button(f"Join {name}"):
            join_challenge(user_id, cid)
            st.success(f"You joined {name}!")

# ---------- VISUALIZATIONS PAGE ----------
def visualizations_page(user_id):
    st.title("📊 Workout Visualizations")

    cursor.execute('SELECT workout_type, duration, calories_burned FROM workouts WHERE user_id = ?', (user_id,))
    data = cursor.fetchall()

    if not data:
        st.info("No workout data available to visualize.")
        return

    df = pd.DataFrame(data, columns=["Workout Type", "Duration (min)", "Calories Burned"])

    st.subheader("Calories Burned by Workout Type")
    fig1 = px.bar(df.groupby("Workout Type").sum().reset_index(), x="Workout Type", y="Calories Burned",
                  color="Workout Type", title="Total Calories Burned by Workout Type")
    st.plotly_chart(fig1)

    st.subheader("Workout Duration by Type")
    fig2 = px.box(df, x="Workout Type", y="Duration (min)", color="Workout Type",
                  title="Distribution of Workout Durations")
    st.plotly_chart(fig2)

    st.subheader("Calories vs Duration")
    fig3 = px.scatter(df, x="Duration (min)", y="Calories Burned", color="Workout Type",
                      size="Calories Burned", title="Calories Burned vs Duration")
    st.plotly_chart(fig3)

    st.subheader("Workout Count per Type")
    fig4 = px.pie(df, names="Workout Type", title="Workout Count per Type")
    st.plotly_chart(fig4)

# ---------- RESET PASSWORD ----------
def reset_password(username, new_password):
    cursor.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
    conn.commit()





def generate_report(user_id):
    cursor.execute('SELECT username, name, email FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    cursor.execute('SELECT workout_type, duration, calories_burned FROM workouts WHERE user_id = ?', (user_id,))
    workouts = cursor.fetchall()

    df = pd.DataFrame(workouts, columns=["Workout", "Duration", "Calories"])
    total_duration = df["Duration"].sum()
    total_calories = df["Calories"].sum()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Fitness Report", ln=True, align="C")
    pdf.ln(10)

    pdf.cell(200, 10, txt=f"Name: {user[1]}", ln=True)
    pdf.cell(200, 10, txt=f"Username: {user[0]}", ln=True)
    pdf.cell(200, 10, txt=f"Email: {user[2]}", ln=True)
    pdf.ln(10)

    pdf.cell(200, 10, txt=f"Total Workouts: {len(df)}", ln=True)
    pdf.cell(200, 10, txt=f"Total Duration: {total_duration} min", ln=True)
    pdf.cell(200, 10, txt=f"Total Calories Burned: {total_calories}", ln=True)
    pdf.ln(10)

    pdf.cell(200, 10, txt="Workout Log:", ln=True)
    pdf.ln(5)
    for _, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Workout']} - {row['Duration']} min - {row['Calories']} cal", ln=True)

    
    filepath = f"fitness_report_user_{user_id}.pdf"

    pdf.output(filepath)

    with open(filepath, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    href = f'<a href="data:application/octet-stream;base64,{base64_pdf}" download="fitness_report.pdf">📄 Download Fitness Report</a>'
    st.markdown(href, unsafe_allow_html=True)

# Inject balloons and download option in dashboard
def user_dashboard(user_id):
    st.balloons()  # 🎈 Show when dashboard opens
    st.header("🏋️‍♀️ Your Fitness Dashboard")

    cursor.execute('SELECT workout_type, duration, calories_burned FROM workouts WHERE user_id = ?', (user_id,))
    data = cursor.fetchall()
    if not data:
        st.info("You haven't logged any workouts yet.")
        return
    df = pd.DataFrame(data, columns=["Workout", "Duration", "Calories"])
    st.metric("Total Workouts", len(df))
    st.metric("Total Duration (min)", int(df["Duration"].sum()))
    st.metric("Total Calories Burned", int(df["Calories"].sum()))

    st.subheader("Calories Burned by Workout Type")
    st.bar_chart(df.groupby("Workout")["Calories"].sum())

    st.subheader("Workout Duration Trend")
    st.line_chart(df["Duration"])

    st.subheader("Workout Type Distribution")
    fig, ax = plt.subplots()
    df["Workout"].value_counts().plot.pie(autopct="%1.1f%%", ax=ax)
    st.pyplot(fig)

    st.subheader("Workout History")
    st.dataframe(df)

    st.markdown("### 📥 Export Your Report")
    if st.button("Generate & Download Report"):
        generate_report(user_id)
        st.success("Report ready for download! ✅")
        st.balloons()


# ---------- MAIN ----------
def main():
    st.image("https://images.unsplash.com/photo-1599058917212-d6d6dfc82686", use_container_width=True)

    st.markdown("<h2 style='text-align:center;'>Get Fit, Stay Motivated 💪</h2>", unsafe_allow_html=True)
    st.title("Fitness Tracker")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None

    if not st.session_state.logged_in:
        menu = ["Home", "Login", "Signup", "Forgot Password"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Home":
            st.subheader("Welcome to the Fitness App!")
            st.write("Track your workouts, participate in challenges, and stay motivated.")

        elif choice == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                user = verify_user(username, password)
                if user:
                    st.success("Logged in successfully!")
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        elif choice == "Signup":
            st.subheader("Create Account")
            username = st.text_input("New Username")
            password = st.text_input("New Password", type='password')
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            if st.button("Sign Up"):
                if check_user(username):
                    st.error("Username already exists!")
                else:
                    add_user(username, password, name, email)
                    st.success("Account created! You can now login.")

        elif choice == "Forgot Password":
            st.subheader("🔑 Reset Password")
            username = st.text_input("Enter your username")
            new_password = st.text_input("Enter new password", type='password')
            confirm_password = st.text_input("Confirm new password", type='password')
            if st.button("Reset Password"):
                if not check_user(username):
                    st.error("🚫 Username not found!")
                elif new_password != confirm_password:
                    st.warning("⚠️ Passwords do not match.")
                else:
                    reset_password(username, new_password)
                    st.success("✅ Password reset successfully! You can now login.")

    else:
        # LOGGED IN SECTION
        st.sidebar.success(f"Welcome, {st.session_state.user[3]}! 👋")
        nav = st.sidebar.radio("Navigation", ["Dashboard", "Log Workout", "Challenges", "Leaderboard", "Visualizations"])
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

        user_id = st.session_state.user[0]

        if nav == "Dashboard":
            user_dashboard(user_id)
            show_challenge_progress(user_id)
        elif nav == "Log Workout":
            workout_page(user_id)
        elif nav == "Challenges":
            challenge_page(user_id)
        elif nav == "Leaderboard":
            display_leaderboard()
        elif nav == "Visualizations":
            visualizations_page(user_id)


if __name__ == "__main__":
    main()






