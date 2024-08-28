from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import pooling
import logging
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = 'th4t_1s_v3ry_c0mpl3x_Push@1234_sain1'

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Configure MySQL connection pool
db_config = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "Push@1234",
    "database": "freecourseforallwithpks"
}

try:
    pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **db_config)
    logging.info("Database connection pool created successfully")
except mysql.connector.Error as err:
    logging.error(f"Error creating connection pool: {err}")

@app.route('/')
def home():
    logging.info("Accessed home route")
    if 'user_id' in session:
        logging.info(f"User {session['user_id']} is logged in, rendering index.html")
        return render_template('index.html')
    logging.info("User not logged in, redirecting to register")
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    logging.info("Accessed register route")
    if 'user_id' in session:
        logging.info(f"User {session['user_id']} is already logged in, redirecting to home")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        connection = pool.get_connection()
        cursor = connection.cursor(buffered=True)
        try:
            # Check for existing user
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                logging.warning(f"Registration attempt with existing username or email: {username}, {email}")
                flash("Username or email already exists. Please choose different credentials.", "error")
                return render_template('register.html')
            
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                           (username, email, password))
            connection.commit()
            logging.info(f"User {username} registered successfully")
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            logging.error(f"Error registering user: {err}")
            flash("An error occurred during registration. Please try again.", "error")
        finally:
            cursor.close()
            connection.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    logging.info("Accessed login route")
    if 'user_id' in session:
        logging.info(f"User {session['user_id']} is already logged in, redirecting to home")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s",
                           (username, password))
            user = cursor.fetchone()
            
            if user:
                session['user_id'] = user['id']
                logging.info(f"User {user['id']} logged in successfully")
                flash("Logged in successfully", "success")
                return redirect(url_for('home'))
            else:
                logging.warning(f"Failed login attempt for username: {username}")
                flash("Invalid credentials", "error")
        except mysql.connector.Error as err:
            logging.error(f"Error during login: {err}")
            flash("An error occurred during login. Please try again.", "error")
        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    logging.info(f"User {session.get('user_id')} logged out")
    session.pop('user_id', None)
    flash("You have been logged out", "info")
    return redirect(url_for('login'))


# Add this function to send emails
def send_reset_email(email, reset_token):
    sender_email = os.getenv('EMAIL_USER')       # Fetch from environment variables
    sender_password = os.getenv('EMAIL_PASS')   # Fetch from environment variables

    message = MIMEMultipart("alternative")
    message["Subject"] = "Password Reset Request"
    message["From"] = sender_email
    message["To"] = email

    text = f"""
    To reset your password, please click on the following link:
    http://localhost:5000/reset_password/{reset_token}
    
    If you did not request a password reset, please ignore this email.
    """

    part = MIMEText(text, "plain")
    message.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, message.as_string())

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                reset_token = secrets.token_urlsafe(32)
                cursor.execute("UPDATE users SET reset_token = %s WHERE email = %s", (reset_token, email))
                connection.commit()
                send_reset_email(email, reset_token)
                flash("Password reset link has been sent to your email.", "info")
                return redirect(url_for('login'))
            else:
                flash("No account found with that email address.", "error")
        except mysql.connector.Error as err:
            logging.error(f"Error in forgot password process: {err}")
            flash("An error occurred. Please try again.", "error")
        finally:
            cursor.close()
            connection.close()
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('reset_password.html', token=token)
        
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE reset_token = %s", (token,))
            user = cursor.fetchone()
            if user:
                cursor.execute("UPDATE users SET password = %s, reset_token = NULL WHERE id = %s", (new_password, user['id']))
                connection.commit()
                flash("Your password has been reset successfully. Please login with your new password.", "success")
                return redirect(url_for('login'))
            else:
                flash("Invalid or expired reset token.", "error")
        except mysql.connector.Error as err:
            logging.error(f"Error in resetting password: {err}")
            flash("An error occurred. Please try again.", "error")
        finally:
            cursor.close()
            connection.close()
    return render_template('reset_password.html', token=token)










if __name__ == '__main__':
    app.run(debug=True)