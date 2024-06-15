from flask import Flask, render_template, jsonify, request, redirect, session as flask_session
from model import Session, User, Log
import bcrypt, json
from datetime import datetime, timedelta
from attendance import ssid_utils, hmac_utils
import os, base64
from sqlalchemy.exc import SQLAlchemyError
from config import config
from sqlalchemy.exc import SQLAlchemyError
import pytz
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = "b'6y[^\xb2*|\xf2\xccd\x9d\x04'"

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/home")
def home():
    if 'username' in flask_session:
        session = Session()
        dates = {}
        unique_dates = session.query(func.date(Log.timestamp)).distinct().all()

        for date in unique_dates:
            records = []
            date = date[0]
            total_users = session.query(User).count()
            for i in range(1, total_users+1):
                user = session.query(User).filter_by(id=i).first()
                if user:
                    record_user = session.query(Log).filter_by(member_id=user.id).all()
                    time_list = []
                    for record in record_user:
                        if record.timestamp.date() == date:
                            time_list.append(record.timestamp)
                    
                    min_time = min(time_list) if time_list != [] else 0
                    max_time = max(time_list) if time_list != [] else 0
                    records.append({
                        'name': user.name,
                        'rollNo': user.rollNo,
                        'login_time': min_time.strftime('%I:%M:%S %p') if min_time != 0 else 'Absent',
                        'logout_time': max_time.strftime('%I:%M:%S %p') if max_time != 0 else 'Absent',
                    })
            dates[date.strftime('%d/%m/%Y')] = records

        session.close()
        return render_template('home.html', username=flask_session['username'], dates=dates)
    
    return redirect('/login')

@app.route("/current_day")
def current_day_json():
    session = Session()
    result = []
    try:
        total_users = session.query(User).count()
        for i in range(1, total_users+1):
            user = session.query(User).filter_by(id=i).first()
            if user:
                record_user = session.query(Log).filter_by(member_id=user.id).all()
                current_date = datetime.now().date()
                time_list = []
                for record in record_user:
                    if record.timestamp.date() == current_date:
                        time_list.append(record.timestamp)
                
                min_time = min(time_list) if time_list != [] else 0
                max_time = max(time_list) if time_list != [] else 0
                result.append({
                    'name': user.name,
                    'rollNo': user.rollNo,
                    'date': current_date.strftime('%d/%m/%Y'),
                    'login_time': min_time.strftime('%I:%M %p') if min_time != 0 else 'Absent',
                    'logout_time': max_time.strftime('%I:%M %p') if max_time != 0 else 'Absent',
                })
        return jsonify(result)
    
    except Exception as e:
        print("Error fetching current day data:", e)
        return jsonify({'error': 'An error occurred while fetching data'}), 500
    
    finally:
        session.close()

@app.route("/dashboard")
def dashboard():
    session = Session()
    try:
        current_user = session.query(User).filter_by(user_name=flask_session['username']).first()
    except Exception as e:
        return redirect('/login')
    if 'username' in flask_session:
        return render_template('dashboard.html', username=flask_session['username'], user=current_user)
    return redirect('/login')

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        session = Session()
        data = request.form
        user = session.query(User).filter_by(user_name=data.get('username')).first()
        if user and bcrypt.checkpw(data.get('password').encode('utf-8'), user.password.encode('utf-8')):
            flask_session['username'] = user.user_name
            return redirect('/home')
        else:
            return render_template('login.html', error='Invalid credentials')
    else:
        return render_template('login.html')

@app.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        session = Session()
        data = request.form
        username = data.get('username')
        password = data.get('password')
        name = data.get('name')
        rollNo = data.get('rollNo')

        if not username or not password or not name or not rollNo:
            return render_template('register.html', error='All fields are required')

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        shared_secret = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
        new_user = User(
            user_name=username,
            password=hashed_password,
            name=name,
            rollNo=rollNo,
            shared_secret=shared_secret
        )
        session.add(new_user)
        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            return render_template('register.html', error='Username already exists')
        return redirect('/login')
    else:
        return render_template('register.html')

@app.route("/logout")
def logout():
    flask_session.clear()
    return redirect('/login')

@app.route("/editProfile", methods=['POST', 'GET'])
def edit_profile():
    if 'username' not in flask_session:
        return redirect('/login')

    session = Session()
    current_user = session.query(User).filter_by(user_name=flask_session['username']).first()

    if request.method == 'POST':
        data = request.form
        new_name = data.get('name')
        new_roll_no = data.get('rollNum')

        if new_name:
            current_user.name = new_name

        if new_roll_no:
            current_user.rollNo = new_roll_no

        print(current_user.shared_secret)

        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            return render_template('dashboard.html', user=current_user, error=str(e))

        return redirect('/home')

    return render_template('dashboard.html', user=current_user)

@app.route("/verify", methods=["POST"])
def verify_credentials():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    shared_secret = data.get('shared_secret')

    session = Session()
    try:
        user = session.query(User).filter_by(user_name=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')) and user.shared_secret == shared_secret:
            return jsonify({"status": "success", "message" : "Creds Verified"}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except Exception as e:
        print("Error occurred:", e)
        session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        session.close()

@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    ssid_list = data.get('list')
    message = data.get('message')
    received_hmac = data.get('hmac')
    to_tz = pytz.timezone(str(config['TIMEZONE']))  
    now = datetime.now(to_tz)  
    authenticated = False
    ssid_verified = False

    session = Session()
    try:
        user = session.query(User).filter_by(user_name=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            authenticated = True
        
        if not authenticated:
            return jsonify({"status": "error", "message": "Authentication failed"}), 401

        ssid_verified = ssid_utils.verify_ssid(ssid_list)
        if not ssid_verified:
            return jsonify({"status": "error", "message": "SSID verification failed"}), 401

        if not hmac_utils.verify_hmac(user.shared_secret, message, received_hmac):
            return jsonify({"status": "error", "message": "HMAC verification failed"}), 401

        log = session.query(Log).filter(Log.member_id == user.id).first()

        log = Log(member_id=user.id, timestamp=now)
        session.add(log)

        session.commit()

        session.commit()
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        print("Error occurred:", e)
        session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        session.close()

if __name__ == "__main__":
    app.run(debug=True)
