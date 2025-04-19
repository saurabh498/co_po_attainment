import csv
import io
import json
import datetime
from io import StringIO
import os
from sqlite3 import Cursor
import traceback
from venv import logger
from flask import Flask, Response, make_response, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CursorResult
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
from datetime import datetime
from flask_sqlalchemy import session
from flask import session, redirect, url_for
from sqlalchemy.sql import func
import pandas as pd  # Yeh line zaroori hai
from flask import request
import pdfkit

pymysql.install_as_MySQLdb()

# Initialize Flask App
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Skbhai$123@localhost/co_po_attainment'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------ DATABASE MODELS ------------------ #

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class AcademicInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SubjectCOPO(db.Model):
    __tablename__ = "subject_copo"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Tracks who added it
    subject_name = db.Column(db.String(200), nullable=False)
    co_code = db.Column(db.String(20), nullable=False)  # CO1, CO2, etc.
    co_text = db.Column(db.Text, nullable=False)
    cognition = db.Column(db.String(100), nullable=False)
    po_code = db.Column(db.String(20), nullable=False)  # PO1, PO2, etc.
    po_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="co_po_entries")
    
    # Relationship with Mapping table
    mappings = db.relationship("Mapping", backref="subject_copo", cascade="all, delete-orphan", lazy=True)

class Mapping(db.Model):
    __tablename__ = "mapping"

    id = db.Column(db.Integer, primary_key=True)
    subject_copo_id = db.Column(db.Integer, db.ForeignKey('subject_copo.id'), nullable=False)  # Link to SubjectCOPO
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Tracks who added it
    co_code = db.Column(db.String(20), nullable=False)  # CO1, CO2, etc.
    po_code = db.Column(db.String(20), nullable=False)  # PO1, PO2, etc.
    mapping_value = db.Column(db.Float, nullable=False)
    total_hours = db.Column(db.Float, nullable=False, default=0)
    avg_value = db.Column(db.Float, nullable=False, default=0)
    
    user = db.relationship("User", backref="mappings")
    
  
   
# Define Student Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), nullable=False, unique=True)
    full_name = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'roll_no': self.roll_no,
            'full_name': self.full_name
        }

class StudentMarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    q1a = db.Column(db.Float, nullable=False, default=0)
    q1b = db.Column(db.Float, nullable=False, default=0)
    q1c = db.Column(db.Float, nullable=False, default=0)
    q1d = db.Column(db.Float, nullable=False, default=0)
    q1e = db.Column(db.Float, nullable=False, default=0)
    q1f = db.Column(db.Float, nullable=False, default=0)
    q2a = db.Column(db.Float, nullable=False, default=0)
    q2b = db.Column(db.Float, nullable=False, default=0)
    q3a = db.Column(db.Float, nullable=False, default=0)
    q3b = db.Column(db.Float, nullable=False, default=0)
    total = db.Column(db.Float, nullable=False, default=0)

class SummaryData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q1a_avg = db.Column(db.Float, nullable=False, default=0)
    q1b_avg = db.Column(db.Float, nullable=False, default=0)
    q1c_avg = db.Column(db.Float, nullable=False, default=0)
    q1d_avg = db.Column(db.Float, nullable=False, default=0)
    q1e_avg = db.Column(db.Float, nullable=False, default=0)
    q1f_avg = db.Column(db.Float, nullable=False, default=0)
    q2a_avg = db.Column(db.Float, nullable=False, default=0)
    q2b_avg = db.Column(db.Float, nullable=False, default=0)
    q3a_avg = db.Column(db.Float, nullable=False, default=0)
    q3b_avg = db.Column(db.Float, nullable=False, default=0)
    total_avg = db.Column(db.Float, nullable=False, default=0)
    q1a_perc = db.Column(db.Float, nullable=False, default=0)
    q1b_perc = db.Column(db.Float, nullable=False, default=0)
    q1c_perc = db.Column(db.Float, nullable=False, default=0)
    q1d_perc = db.Column(db.Float, nullable=False, default=0)
    q1e_perc = db.Column(db.Float, nullable=False, default=0)
    q1f_perc = db.Column(db.Float, nullable=False, default=0)
    q2a_perc = db.Column(db.Float, nullable=False, default=0)
    q2b_perc = db.Column(db.Float, nullable=False, default=0)
    q3a_perc = db.Column(db.Float, nullable=False, default=0)
    q3b_perc = db.Column(db.Float, nullable=False, default=0)
    total_perc = db.Column(db.Float, nullable=False, default=0)

class COData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    co = db.Column(db.String(10), nullable=False)
    q1a = db.Column(db.Float, nullable=False, default=0)
    q1b = db.Column(db.Float, nullable=False, default=0)
    q1c = db.Column(db.Float, nullable=False, default=0)
    q1d = db.Column(db.Float, nullable=False, default=0)
    q1e = db.Column(db.Float, nullable=False, default=0)
    q1f = db.Column(db.Float, nullable=False, default=0)
    q2a = db.Column(db.Float, nullable=False, default=0)
    q2b = db.Column(db.Float, nullable=False, default=0)
    q3a = db.Column(db.Float, nullable=False, default=0)
    q3b = db.Column(db.Float, nullable=False, default=0)
    avg = db.Column(db.Float, nullable=False, default=0)
    perc = db.Column(db.Float, nullable=False, default=0)

class CourseExitForm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    q1 = db.Column(db.Integer, nullable=False)
    q2 = db.Column(db.Integer, nullable=False)
    q3 = db.Column(db.Integer, nullable=False)
    q4 = db.Column(db.Integer, nullable=False)
    q5 = db.Column(db.Integer, nullable=False)
    q6 = db.Column(db.Integer, nullable=False)

    def __init__(self, roll_no, q1, q2, q3, q4, q5, q6):
        self.roll_no = roll_no
        self.q1 = q1
        self.q2 = q2
        self.q3 = q3
        self.q4 = q4
        self.q5 = q5
        self.q6 = q6

class CourseAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    avg_co1 = db.Column(db.Float, nullable=False)
    avg_co2 = db.Column(db.Float, nullable=False)
    avg_co3 = db.Column(db.Float, nullable=False)
    avg_co4 = db.Column(db.Float, nullable=False)
    avg_co5 = db.Column(db.Float, nullable=False)
    avg_co6 = db.Column(db.Float, nullable=False)
    max_co1 = db.Column(db.Integer, nullable=False)  # New column for Max
    max_co2 = db.Column(db.Integer, nullable=False)  # New column for Max
    max_co3 = db.Column(db.Integer, nullable=False)  # New column for Max
    max_co4 = db.Column(db.Integer, nullable=False)  # New column for Max
    max_co5 = db.Column(db.Integer, nullable=False)  # New column for Max
    max_co6 = db.Column(db.Integer, nullable=False)  # New column for Max
    wt_avg_co1 = db.Column(db.Float, nullable=False)
    wt_avg_co2 = db.Column(db.Float, nullable=False)
    wt_avg_co3 = db.Column(db.Float, nullable=False)
    wt_avg_co4 = db.Column(db.Float, nullable=False)
    wt_avg_co5 = db.Column(db.Float, nullable=False)
    wt_avg_co6 = db.Column(db.Float, nullable=False)

    def __init__(self, avg_co1, avg_co2, avg_co3, avg_co4, avg_co5, avg_co6,
                 max_co1, max_co2, max_co3, max_co4, max_co5, max_co6,
                 wt_avg_co1, wt_avg_co2, wt_avg_co3, wt_avg_co4, wt_avg_co5, wt_avg_co6):
        self.avg_co1 = avg_co1
        self.avg_co2 = avg_co2
        self.avg_co3 = avg_co3
        self.avg_co4 = avg_co4
        self.avg_co5 = avg_co5
        self.avg_co6 = avg_co6
        self.max_co1 = max_co1
        self.max_co2 = max_co2
        self.max_co3 = max_co3
        self.max_co4 = max_co4
        self.max_co5 = max_co5
        self.max_co6 = max_co6
        self.wt_avg_co1 = wt_avg_co1
        self.wt_avg_co2 = wt_avg_co2
        self.wt_avg_co3 = wt_avg_co3
        self.wt_avg_co4 = wt_avg_co4
        self.wt_avg_co5 = wt_avg_co5
        self.wt_avg_co6 = wt_avg_co6   

class DirectAssessment(db.Model):
    __tablename__ = "direct_assessment"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    roll_no = db.Column(db.String(20), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    total_ext = db.Column(db.Integer, nullable=False)  # Max 80
    total_int = db.Column(db.Integer, nullable=False)  # Max 20
    total_marks = db.Column(db.Integer, nullable=False)  # Max 100
    grade = db.Column(db.String(5))

    def to_dict(self):
        return {
            "id": self.id,
            "roll_no": self.roll_no,
            "student_name": self.student_name,
            "total_ext": self.total_ext,
            "total_int": self.total_int,
            "total_marks": self.total_marks,
            "grade": self.grade
        }

class AssessmentSummary(db.Model):
    __tablename__ = "assessment_summary"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    average_marks = db.Column(db.Float, nullable=False)
    max_ext_marks = db.Column(db.Integer, nullable=False)
    max_int_marks = db.Column(db.Integer, nullable=False)
    overall_percentage = db.Column(db.Float, nullable=False)
    most_common_grade = db.Column(db.String(5), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())  # Auto-set current time

    def to_dict(self):
        return {
            "id": self.id,
            "average_marks": self.average_marks,
            "max_ext_marks": self.max_ext_marks,
            "max_int_marks": self.max_int_marks,
            "overall_percentage": self.overall_percentage,
            "most_common_grade": self.most_common_grade,
            "timestamp": self.timestamp.isoformat()
        }

class StudentPerformance(db.Model):
    __tablename__ = 'student_performance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    roll_no = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    test_marks = db.Column(db.Float, nullable=False)
    test_percentage = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # Bright, Weak, Average
    observation = db.Column(db.String(255), nullable=False)

# Define Models
class DirectAttainment(db.Model):
    __tablename__ = 'direct_attainment'
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(20), nullable=False)
    see_percentage = db.Column(db.Float, nullable=False)  # SEE (%)
    cie_ut_avg = db.Column(db.Float, nullable=False)     # CIE UT AVG
    see_atn = db.Column(db.Integer)                      # Atn (X)
    cie_atn = db.Column(db.Integer)                      # Atn (Y)

class IndirectAttainment(db.Model):
    __tablename__ = 'indirect_attainment'
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(20), nullable=False)
    ces_avg = db.Column(db.Float, nullable=False)        # CES AVG
    ces_atn = db.Column(db.Integer)

class FinalAttainment(db.Model):
    __tablename__ = 'final_attainment'
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(20), nullable=False, unique=True)
    final_attainment = db.Column(db.Float, nullable=False)    

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)  # ✅ FIXED


@app.route("/delete_test_student", methods=["POST"])
def delete_test_student():
    roll_no = "17"  # Roll number of the test student
    student = Student.query.filter_by(roll_no=roll_no).first()
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Test student deleted successfully'})


# Ensure tables exist
with app.app_context():
    db.create_all()


# ------------------ ROUTES ------------------ #

@app.route("/")
def home():
    return render_template("home.html")  # Home page with a stylish UI

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()  # Normalize username
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validate fields
        if not username or not password or not confirm_password:
            return render_template("register.html", error="All fields are required!")

        # Check password confirmation
        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match!")

        # Check if the user already exists (case-insensitive)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template("register.html", error="Username already taken!")

        # Create a new user
        new_user = User(username=username)
        new_user.set_password(password)  # Hash password
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))  # Redirect to login page

    return render_template("register.html") 

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)

            # If request comes from fetch(), return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True, "redirect": url_for("dashboard")})

            return redirect(url_for("dashboard"))

        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": "Invalid credentials"}), 401

        return render_template("login.html", error="Invalid credentials. Try again.")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    academic_records = AcademicInfo.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", records=academic_records)

@app.route("/save_academic_info", methods=["POST"])
@login_required
def save_academic_info():
    department = request.form.get("department")
    academic_year = request.form.get("academic_year")
    semester = request.form.get("semester")

    if not department or not academic_year or not semester:
        return jsonify({"message": "All fields are required!"}), 400

    new_entry = AcademicInfo(user_id=current_user.id, department=department, academic_year=academic_year, semester=semester)
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({"message": "Academic information saved successfully!"})

@app.route("/view_academic_info")
@login_required
def view_academic_info():
    records = AcademicInfo.query.filter_by(user_id=current_user.id).all()
    data = [{"department": rec.department, "academic_year": rec.academic_year, "semester": rec.semester} for rec in records]
    return jsonify(data)

@app.route("/delete_academic_info", methods=["DELETE"])
@login_required
def delete_academic_info():
    data = request.json
    department = data.get("department")
    academic_year = data.get("academic_year")
    semester = data.get("semester")

    record = AcademicInfo.query.filter_by(user_id=current_user.id, department=department, academic_year=academic_year, semester=semester).first()

    if record:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"message": "Record deleted successfully!"})
    else:
        return jsonify({"message": "Record not found!"}), 404
    
@app.route("/sub_co_po")
@login_required
def sub_co_po():
    return render_template("sub_co_po.html")

@app.route("/save_sub_co_po", methods=["POST"])
@login_required
def save_sub_co_po():
    data = request.json
    print("✅ Received Data:", data)  # Debugging
    
    subject = data.get("subject")
    co_data = data.get("co_data", [])
    po_data = data.get("po_data", [])
    mapping_data = data.get("mapping_data", [])

    if not subject or not co_data or not po_data:
        return jsonify({"message": "Subject, COs, and POs are required!"}), 400

    try:
        # Delete existing CO-PO records for this subject and user
        SubjectCOPO.query.filter_by(user_id=current_user.id, subject_name=subject).delete()
        db.session.commit()

        # Save CO-PO relationships
        new_entries = []
        for co in co_data:
            for po in po_data:
                new_entry = SubjectCOPO(
                    user_id=current_user.id,
                    subject_name=subject,
                    co_code=co["co_code"],
                    co_text=co["co_text"],
                    cognition=co["cognition"],
                    po_code=po["po_code"],
                    po_text=po["po_text"]
                )
                db.session.add(new_entry)
                new_entries.append(new_entry)

        db.session.flush()

        # Save CO-PO Mapping values
        for mapping in mapping_data:
            related_entry = next(
                (entry for entry in new_entries if entry.co_code == mapping["co_code"] and entry.po_code == mapping["po_code"]), 
                None
            )
            if related_entry:
                new_mapping = Mapping(
                    user_id=current_user.id,
                    subject_copo_id=related_entry.id,
                    co_code=mapping["co_code"],
                    po_code=mapping["po_code"],
                    mapping_value=mapping["mapping_value"],
                    total_hours=mapping["mapping_value"],
                    avg_value=mapping["mapping_value"]
                )
                db.session.add(new_mapping)
            else:
                print(f"⚠️ No matching SubjectCOPO entry found for CO: {mapping['co_code']} and PO: {mapping['po_code']}")

        db.session.commit()
        return jsonify({"message": "CO-PO Mapping saved successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/view_sub_co_po', methods=['GET'])
@login_required
def view_sub_co_po():
    subject = request.args.get('subject')
    if not subject:
        return jsonify({"message": "Subject name required"}), 400

    # Fetch SubjectCOPO entries for the subject and user
    subject_copos = SubjectCOPO.query.filter_by(subject_name=subject, user_id=current_user.id).all()
    if not subject_copos:
        return jsonify({"message": "No data found for this subject"}), 404

    # Construct response
    result = []
    for sc in subject_copos:
        mappings = Mapping.query.filter_by(subject_copo_id=sc.id, user_id=current_user.id).all()
        for mapping in mappings:
            result.append({
                "co_code": sc.co_code,
                "co_text": sc.co_text,
                "cognition": sc.cognition,
                "po_code": sc.po_code,
                "po_text": sc.po_text,
                "mapping_value": mapping.mapping_value,
                "total_hours": mapping.total_hours,
                "avg_value": mapping.avg_value
            })
        if not mappings:  # Include CO-PO pairs without mappings
            result.append({
                "co_code": sc.co_code,
                "co_text": sc.co_text,
                "cognition": sc.cognition,
                "po_code": sc.po_code,
                "po_text": sc.po_text,
                "mapping_value": 0,
                "total_hours": 0,
                "avg_value": 0
            })

    return jsonify(result), 200

@app.route("/delete_subject", methods=["DELETE"])
@login_required
def delete_subject():
    data = request.get_json()
    subject_name = data.get("subject")

    if not subject_name:
        return jsonify({"error": "Subject name is required"}), 400

    subject = SubjectCOPO.query.filter_by(subject_name=subject_name, user_id=current_user.id).first()
    
    if not subject:
        return jsonify({"error": "Subject not found"}), 404

    db.session.delete(subject)
    db.session.commit()

    return jsonify({"message": f"Subject '{subject_name}' deleted successfully"}), 200

@app.route("/logout")
def logout():
    session.clear()  # Clears all session data
    return redirect(url_for("home"))  # Redirect to home after logout


@app.route('/next_page')
def next_page():
    return render_template('next_page.html')


@app.route("/save_students", methods=["POST"])
def save_students():
    data = request.get_json()
    students = data.get("students", [])

    if not students:
        return jsonify({"message": "No students provided!"}), 400

    try:
        for student in students:
            new_student = Student(roll_no=student["roll_no"], full_name=student["full_name"])
            db.session.add(new_student)

        db.session.commit()
        return jsonify({"message": "Student details saved successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error saving students!", "error": str(e)}), 500

@app.route("/get_user/<int:user_id>")
def get_user(user_id):
    with session(db) as session:
        user = session.get(User, user_id)
    return jsonify(user.to_dict() if user else {"error": "User not found"})

@app.route("/get_students", methods=["GET"])
def get_students():
    try:
        students = Student.query.all()

        if not students:  # Check if students list is empty
            return jsonify({"students": [], "message": "No students found"}), 200

        return jsonify({"students": [student.to_dict() for student in students]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update_student', methods=['POST'])
def update_student():
    data = request.json
    roll_no = data.get("roll_no")
    full_name = data.get("full_name")

    if not roll_no or not full_name:
        return jsonify({"message": "Roll number and full name are required!"}), 400

    try:
        student = Student.query.get(roll_no)
        if student:
            student.full_name = full_name
            db.session.commit()
            return jsonify({"message": "Student updated successfully!"})
        return jsonify({"message": "Student not found!"}), 404
    except Exception as e:
        return jsonify({"message": "Error updating student", "error": str(e)}), 500


@app.route('/delete_student', methods=['POST'])
def delete_student():
    data = request.get_json()
    roll_no = data.get('roll_no')  # Correct JSON parsing

    if not roll_no:
        return jsonify({'error': 'Roll No not provided'}), 400

    student = Student.query.filter_by(roll_no=roll_no).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Student deleted successfully'})


@app.route('/unit_test_one')
def unit_test_one():
    return render_template('unit_test_one.html')

@app.route('/upload_unit1', methods=['POST'])
def upload_unit1():
    try:
        # Get the uploaded file from the form
        file = request.files['csv_file']
        
        if file and file.filename.endswith('.csv'):
            # Read the file as a CSV
            file_content = file.stream.read().decode('utf-8')  # Read file as binary, then decode as utf-8
            csv_reader = csv.reader(file_content.splitlines())

            # Skip the header row
            next(csv_reader)

            # Process CSV data
            data = []
            for row in csv_reader:
                data.append(row)

            # Return the data as JSON for use on the frontend
            return jsonify({'status': 'success', 'data': data})

        else:
            return jsonify({'error': 'Invalid file format. Please upload a CSV file.'})
    
    except Exception as e:
        return jsonify({'error': f'Error processing CSV file: {str(e)}'})

# Save data endpoint
@app.route('/save_unit1', methods=['POST'])
def save_unit1():
    try:
        data = request.get_json()
        if not data or 'students' not in data or 'summary' not in data or 'co' not in data:
            return jsonify({'error': 'Invalid data format'}), 400

        # Clear existing data (optional, depending on your requirements)
        db.session.query(StudentMarks).delete()
        db.session.query(SummaryData).delete()
        db.session.query(COData).delete()

        # Save student marks
        for student in data['students']:
            if len(student) < 12:
                continue  # Skip invalid rows
            total = sum(float(mark) for mark in student[2:12] if mark)  # Calculate total
            student_marks = StudentMarks(
                roll_no=student[0],
                name=student[1],
                q1a=float(student[2]) if student[2] else 0,
                q1b=float(student[3]) if student[3] else 0,
                q1c=float(student[4]) if student[4] else 0,
                q1d=float(student[5]) if student[5] else 0,
                q1e=float(student[6]) if student[6] else 0,
                q1f=float(student[7]) if student[7] else 0,
                q2a=float(student[8]) if student[8] else 0,
                q2b=float(student[9]) if student[9] else 0,
                q3a=float(student[10]) if student[10] else 0,
                q3b=float(student[11]) if student[11] else 0,
                total=total
            )
            db.session.add(student_marks)

        # Save summary data
        summary = data['summary']
        summary_data = SummaryData(
            q1a_avg=float(summary['q1a_avg']) if summary['q1a_avg'] else 0,
            q1b_avg=float(summary['q1b_avg']) if summary['q1b_avg'] else 0,
            q1c_avg=float(summary['q1c_avg']) if summary['q1c_avg'] else 0,
            q1d_avg=float(summary['q1d_avg']) if summary['q1d_avg'] else 0,
            q1e_avg=float(summary['q1e_avg']) if summary['q1e_avg'] else 0,
            q1f_avg=float(summary['q1f_avg']) if summary['q1f_avg'] else 0,
            q2a_avg=float(summary['q2a_avg']) if summary['q2a_avg'] else 0,
            q2b_avg=float(summary['q2b_avg']) if summary['q2b_avg'] else 0,
            q3a_avg=float(summary['q3a_avg']) if summary['q3a_avg'] else 0,
            q3b_avg=float(summary['q3b_avg']) if summary['q3b_avg'] else 0,
            total_avg=float(summary['total_avg']) if summary['total_avg'] else 0,
            q1a_perc=float(summary['q1a_perc']) if summary['q1a_perc'] else 0,
            q1b_perc=float(summary['q1b_perc']) if summary['q1b_perc'] else 0,
            q1c_perc=float(summary['q1c_perc']) if summary['q1c_perc'] else 0,
            q1d_perc=float(summary['q1d_perc']) if summary['q1d_perc'] else 0,
            q1e_perc=float(summary['q1e_perc']) if summary['q1e_perc'] else 0,
            q1f_perc=float(summary['q1f_perc']) if summary['q1f_perc'] else 0,
            q2a_perc=float(summary['q2a_perc']) if summary['q2a_perc'] else 0,
            q2b_perc=float(summary['q2b_perc']) if summary['q2b_perc'] else 0,
            q3a_perc=float(summary['q3a_perc']) if summary['q3a_perc'] else 0,
            q3b_perc=float(summary['q3b_perc']) if summary['q3b_perc'] else 0,
            total_perc=float(summary['total_perc']) if summary['total_perc'] else 0
        )
        db.session.add(summary_data)

        # Save CO data
        for co in data['co']:
            co_data = COData(
                co=co['co'],
                q1a=float(co['q1a']) if co['q1a'] else 0,
                q1b=float(co['q1b']) if co['q1b'] else 0,
                q1c=float(co['q1c']) if co['q1c'] else 0,
                q1d=float(co['q1d']) if co['q1d'] else 0,
                q1e=float(co['q1e']) if co['q1e'] else 0,
                q1f=float(co['q1f']) if co['q1f'] else 0,
                q2a=float(co['q2a']) if co['q2a'] else 0,
                q2b=float(co['q2b']) if co['q2b'] else 0,
                q3a=float(co['q3a']) if co['q3a'] else 0,
                q3b=float(co['q3b']) if co['q3b'] else 0,
                avg=float(co['avg']) if co['avg'] else 0,
                perc=float(co['perc']) if co['perc'] else 0
            )
            db.session.add(co_data)

        # Commit changes to the database
        db.session.commit()
        return jsonify({'message': 'Data saved successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error saving data: {str(e)}'}), 500

@app.route('/load_unit1', methods=['GET'])
def load_unit1():
    try:
        students = StudentMarks.query.all()
        summary = SummaryData.query.first() or SummaryData()
        co_data = COData.query.all()

        student_data = [
            [s.roll_no, s.name, s.q1a, s.q1b, s.q1c, s.q1d, s.q1e, s.q1f, s.q2a, s.q2b, s.q3a, s.q3b]
            for s in students
        ]
        summary_data = {
            'q1a_avg': summary.q1a_avg, 'q1b_avg': summary.q1b_avg, 'q1c_avg': summary.q1c_avg,
            'q1d_avg': summary.q1d_avg, 'q1e_avg': summary.q1e_avg, 'q1f_avg': summary.q1f_avg,
            'q2a_avg': summary.q2a_avg, 'q2b_avg': summary.q2b_avg, 'q3a_avg': summary.q3a_avg,
            'q3b_avg': summary.q3b_avg, 'total_avg': summary.total_avg,
            'q1a_perc': summary.q1a_perc, 'q1b_perc': summary.q1b_perc, 'q1c_perc': summary.q1c_perc,
            'q1d_perc': summary.q1d_perc, 'q1e_perc': summary.q1e_perc, 'q1f_perc': summary.q1f_perc,
            'q2a_perc': summary.q2a_perc, 'q2b_perc': summary.q2b_perc, 'q3a_perc': summary.q3a_perc,
            'q3b_perc': summary.q3b_perc, 'total_perc': summary.total_perc
        }
        co_data_list = [
            {
                'co': c.co, 'q1a': c.q1a, 'q1b': c.q1b, 'q1c': c.q1c, 'q1d': c.q1d,
                'q1e': c.q1e, 'q1f': c.q1f, 'q2a': c.q2a, 'q2b': c.q2b, 'q3a': c.q3a,
                'q3b': c.q3b, 'avg': c.avg, 'perc': c.perc
            } for c in co_data
        ]

        return jsonify({
            'students': student_data,
            'summary': summary_data,
            'co': co_data_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/students_analysis')
def students_analysis():
    return render_template('students_analysis.html')

@app.route('/save_data_analysis', methods=['POST'])
def save_data_analysis():
    data = request.json
    try:
        for student in data:
            percentage_value = student['percentage'].replace('%', '').strip()
            new_student = StudentPerformance(
                roll_no=student['roll_no'],
                name=student['name'],
                test_marks=float(student['marks']),
                test_percentage=float(percentage_value),
                category=student['category'],
                observation=student['observation']
            )
            db.session.add(new_student)
        db.session.commit()
        return jsonify({"message": "Data saved successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/view_saved_data', methods=['GET'])
def view_saved_data():
    try:
        students = StudentPerformance.query.all()  # Fetch all records
        student_list = [{
            "roll_no": student.roll_no,
            "name": student.name,
            "marks": student.test_marks,
            "percentage": student.test_percentage,
            "category": student.category,
            "observation": student.observation
        } for student in students]

        return jsonify(student_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/update_analysis/<roll_no>", methods=["PATCH"])
def update_analysis(roll_no):
    try:
        data = request.json
        new_roll_no = data.get("roll_no")  # Match frontend key
        name = data.get("name")
        marks = float(data.get("marks"))  # Ensure marks are numeric

        # Check if the new roll number already exists (excluding the current student)
        existing_student = StudentPerformance.query.filter_by(roll_no=new_roll_no).first()
        if existing_student and existing_student.roll_no != roll_no:
            return jsonify({"error": "Roll Number already exists!"}), 400

        # Fetch student from database
        student = StudentPerformance.query.filter_by(roll_no=roll_no).first()
        if not student:
            return jsonify({"error": "Student not found!"}), 404

        # Update values
        student.roll_no = new_roll_no
        student.name = name
        student.test_marks = marks

        # Recalculate Percentage, Category, and Observation
        max_marks = 20  # Class test total marks
        student.test_percentage = (marks / max_marks) * 100

        if student.test_percentage >= 75:
            student.category = "Bright"
            student.observation = "Excellent Performance"
        elif student.test_percentage < 40:
            student.category = "Fail"
            student.observation = "Needs Improvement"
        elif student.test_percentage >= 40 and student.test_percentage <= 50:
            student.category = "Weak"
            student.observation = "Needs To Study Hard "    
        else:
            student.category = "Average"
            student.observation = "Can Do Better"

        # Commit changes
        db.session.commit()
        return jsonify({
            "message": "Student data updated successfully!",
            "student": {
                "roll_no": student.roll_no,
                "name": student.name,
                "marks": student.test_marks,
                "percentage": student.test_percentage,
                "category": student.category,
                "observation": student.observation
            }
        }), 200

    except ValueError as e:
        return jsonify({"error": "Invalid marks value provided!"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update student: {str(e)}"}), 500

@app.route('/delete_analysis/<roll_no>', methods=['DELETE'])
def delete_analysis(roll_no):
    student = StudentPerformance.query.filter_by(roll_no=roll_no).first()
    
    if not student:
        return jsonify({"error": "Student not found"}), 404  # Return error if roll number not found

    db.session.delete(student)
    db.session.commit()
    
    return jsonify({"message": f"Record for Roll No. {roll_no} deleted successfully!"})

# Helper function for attainment levels
def get_attainment_level(percentage, context):
    percentage = float(percentage)
    if context == 'CES':
        if percentage >= 85:
            return 3
        elif percentage >= 80:
            return 2
        return 1
    else:  # SEE or CIE
        if percentage >= 75:
            return 3
        elif percentage >= 50:
            return 2
        return 1    
    
@app.route('/unit_test_two')
def unit_test_two():
    return render_template('unit_test_two.html')   

@app.route('/upload_unit2', methods=['POST'])
def upload_unit2():
    try:
        # Get the uploaded file from the form
        file = request.files['csv_file']
        
        if file and file.filename.endswith('.csv'):
            # Read the file as a CSV
            file_content = file.stream.read().decode('utf-8')  # Read file as binary, then decode as utf-8
            csv_reader = csv.reader(file_content.splitlines())

            # Skip the header row
            next(csv_reader)

            # Process CSV data
            data = []
            for row in csv_reader:
                data.append(row)

            # Return the data as JSON for use on the frontend
            return jsonify({'status': 'success', 'data': data})

        else:
            return jsonify({'error': 'Invalid file format. Please upload a CSV file.'})
    
    except Exception as e:
        return jsonify({'error': f'Error processing CSV file: {str(e)}'}) 
    
@app.route('/students_analysis2')
def students_analysis2():
    return render_template('students_analysis2.html')    

@app.route('/direct_assesment')
def direct_assesment():
    return render_template('direct_assesment.html')

@app.route('/save_marks', methods=['POST'])
def save_marks():
    try:
        data = request.get_json()  # Get JSON data from frontend
        if not data or not isinstance(data, list):
            return jsonify({"message": "Invalid data format. Expected a list of records."}), 400

        for entry in data:
            # Ensure required fields exist
            if not all(k in entry for k in ["roll_no", "student_name", "total_ext", "total_int", "total_marks", "grade"]):
                return jsonify({"message": "Missing required fields in request data"}), 400

            # Validate numerical values
            try:
                total_ext = int(entry['total_ext'])
                total_int = int(entry['total_int'])
                total_marks = int(entry['total_marks'])
            except ValueError:
                return jsonify({"message": "Invalid number format in total_ext, total_int, or total_marks"}), 400

            # Ensure total_ext and total_int are within valid ranges
            if not (0 <= total_ext <= 80) or not (0 <= total_int <= 20):
                return jsonify({"message": f"Invalid marks for Roll No {entry['roll_no']}. Check Ext (0-80) and Int (0-20)."}), 400

            # Check if record already exists
            existing = DirectAssessment.query.filter_by(roll_no=entry['roll_no']).first()
            if existing:
                # Update existing record
                existing.student_name = entry['student_name']
                existing.total_ext = total_ext
                existing.total_int = total_int
                existing.total_marks = total_marks
                existing.grade = entry['grade']
            else:
                # Create new record
                new_assessment = DirectAssessment(
                    roll_no=entry['roll_no'],
                    student_name=entry['student_name'],
                    total_ext=total_ext,
                    total_int=total_int,
                    total_marks=total_marks,
                    grade=entry['grade']
                )
                db.session.add(new_assessment)

        db.session.commit()
        return jsonify({"message": "Data saved successfully"}), 200

    except Exception as e:
        db.session.rollback()  # Rollback any failed transactions
        return jsonify({"message": f"Error saving data: {str(e)}"}), 500
    
@app.route('/save_summary', methods=['POST'])
def save_summary():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ["average_marks", "max_ext_marks", "max_int_marks", "overall_percentage", "most_common_grade"]):
            return jsonify({"message": "Invalid summary data format"}), 400

        try:
            average_marks = float(data['average_marks'])
            max_ext_marks = int(data['max_ext_marks'])
            max_int_marks = int(data['max_int_marks'])
            overall_percentage = float(data['overall_percentage'])
        except ValueError:
            return jsonify({"message": "Invalid number format in summary data"}), 400

        if not (0 <= max_ext_marks <= 80) or not (0 <= max_int_marks <= 20):
            return jsonify({"message": "Invalid max marks range. Ext (0-80), Int (0-20)."}), 400

        # Check if a summary already exists (optional: update or create new)
        existing_summary = AssessmentSummary.query.first()  # You can modify this logic (e.g., by timestamp)
        if existing_summary:
            existing_summary.average_marks = average_marks
            existing_summary.max_ext_marks = max_ext_marks
            existing_summary.max_int_marks = max_int_marks
            existing_summary.overall_percentage = overall_percentage
            existing_summary.most_common_grade = data['most_common_grade']
        else:
            new_summary = AssessmentSummary(
                average_marks=average_marks,
                max_ext_marks=max_ext_marks,
                max_int_marks=max_int_marks,
                overall_percentage=overall_percentage,
                most_common_grade=data['most_common_grade']
            )
            db.session.add(new_summary)

        db.session.commit()
        return jsonify({"message": "Summary saved successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error saving summary: {str(e)}"}), 500    

@app.route('/get_all_marks', methods=['GET'])
def get_all_marks():
    try:
        assessments = DirectAssessment.query.all()  # Fetch all records
        return jsonify([assessment.to_dict() for assessment in assessments]), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching data: {str(e)}"}), 500

@app.route('/delete_marks', methods=['POST'])
def delete_marks():
    try:
        data = request.get_json()
        roll_nos = data.get('roll_nos', [])

        if not roll_nos:
            return jsonify({"message": "No roll numbers provided"}), 400

        # Delete records matching the roll numbers
        deleted_count = DirectAssessment.query.filter(DirectAssessment.roll_no.in_(roll_nos)).delete(synchronize_session=False)
        db.session.commit()

        if deleted_count > 0:
            return jsonify({"message": "Data deleted successfully"}), 200
        else:
            return jsonify({"message": "No matching records found"}), 404

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error deleting data: {str(e)}"}), 500

# New route to serve summary data for Co_Attainment_Cal.html
@app.route('/get_direct_summary', methods=['GET'])
def get_direct_summary():
    try:
        latest_summary = AssessmentSummary.query.order_by(AssessmentSummary.timestamp.desc()).first()
        if not latest_summary:
            return jsonify({
                'error': 'No summary data available',
                'perc1': '0',
                'perc2': '0'
            }), 404

        # Match HTML's updateSummary() logic
        assessments = DirectAssessment.query.all()
        if not assessments:
            return jsonify({'perc1': '0', 'perc2': '0'}), 200

        ext_sum = sum(a.total_ext for a in assessments)
        int_sum = sum(a.total_int for a in assessments)
        valid_students = len(assessments)
        perc1 = (ext_sum / (80 * valid_students)) * 100
        perc2 = (int_sum / (20 * valid_students)) * 100

        return jsonify({
            'perc1': f'{perc1:.2f}',
            'perc2': f'{perc2:.2f}'
        }), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching summary data: {str(e)}"}), 500

@app.route('/Indirect_assesment')
def Indirect_assesment():
    return render_template('Indirect_assesment.html')  # Your new HTML file

# Upload CSV (validate and return data for display, no saving yet)
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({'error': 'Invalid or empty CSV data'}), 400
        
        # Validate each record
        for record in data:
            if not all(key in record for key in ['roll_no', 'q1', 'q2', 'q3', 'q4', 'q5', 'q6']):
                return jsonify({'error': 'Missing required fields in CSV data'}), 400
            if not all(isinstance(record[f'q{i}'], (int, str)) and 1 <= int(record[f'q{i}']) <= 5 for i in range(1, 7)):
                return jsonify({'error': 'Question values must be between 1 and 5'}), 400
        
        return jsonify({'message': 'CSV data validated successfully', 'data': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Save Data (manual entry or bulk CSV data)
@app.route('/save', methods=['POST'])
def save_data():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            # Check if roll_no already exists
            existing = CourseExitForm.query.filter_by(roll_no=entry['roll_no']).first()
            if existing:
                # Update existing record
                existing.q1 = entry['q1']
                existing.q2 = entry['q2']
                existing.q3 = entry['q3']
                existing.q4 = entry['q4']
                existing.q5 = entry['q5']
                existing.q6 = entry['q6']
            else:
                # Insert new record
                new_entry = CourseExitForm(**entry)
                db.session.add(new_entry)
        
        db.session.commit()
        return jsonify({'message': 'Course data saved successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

# Save Analysis Data
@app.route('/save_analysis', methods=['POST'])
def save_analysis():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No analysis data provided'}), 400

    try:
        new_analysis = CourseAnalysis(
            avg_co1=data['avg_co1'],
            avg_co2=data['avg_co2'],
            avg_co3=data['avg_co3'],
            avg_co4=data['avg_co4'],
            avg_co5=data['avg_co5'],
            avg_co6=data['avg_co6'],
            max_co1=data.get('max_co1', 5),  # Default to 5 if not provided
            max_co2=data.get('max_co2', 5),
            max_co3=data.get('max_co3', 5),
            max_co4=data.get('max_co4', 5),
            max_co5=data.get('max_co5', 5),
            max_co6=data.get('max_co6', 5),
            wt_avg_co1=data['wt_avg_co1'],
            wt_avg_co2=data['wt_avg_co2'],
            wt_avg_co3=data['wt_avg_co3'],
            wt_avg_co4=data['wt_avg_co4'],
            wt_avg_co5=data['wt_avg_co5'],
            wt_avg_co6=data['wt_avg_co6']
        )
        db.session.add(new_analysis)
        db.session.commit()
        return jsonify({'message': 'Analysis data saved successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to save analysis: {str(e)}'}), 500

# View Saved Course Data
@app.route('/view', methods=['GET'])
def view_data():
    records = CourseExitForm.query.all()
    return jsonify([{
        'roll_no': r.roll_no, 'q1': r.q1, 'q2': r.q2, 'q3': r.q3,
        'q4': r.q4, 'q5': r.q5, 'q6': r.q6
    } for r in records])

# View Saved Analysis Data (optional, if you want to display historical analysis)
@app.route('/view_analysis', methods=['GET'])
def view_analysis():
    records = CourseAnalysis.query.all()
    return jsonify([{
        'analysis_date': r.analysis_date.isoformat(),
        'avg_co1': r.avg_co1, 'avg_co2': r.avg_co2, 'avg_co3': r.avg_co3,
        'avg_co4': r.avg_co4, 'avg_co5': r.avg_co5, 'avg_co6': r.avg_co6,
        'max_co1': r.max_co1, 'max_co2': r.max_co2, 'max_co3': r.max_co3,
        'max_co4': r.max_co4, 'max_co5': r.max_co5, 'max_co6': r.max_co6,
        'wt_avg_co1': r.wt_avg_co1, 'wt_avg_co2': r.wt_avg_co2, 'wt_avg_co3': r.wt_avg_co3,
        'wt_avg_co4': r.wt_avg_co4, 'wt_avg_co5': r.wt_avg_co5, 'wt_avg_co6': r.wt_avg_co6
    } for r in records])

# Delete Data
@app.route('/delete/<string:roll_no>', methods=['DELETE'])
def delete_data(roll_no):
    record = CourseExitForm.query.filter_by(roll_no=roll_no).first()
    if record:
        db.session.delete(record)
        db.session.commit()
        return jsonify({'message': 'Record deleted successfully'})
    return jsonify({'error': 'Roll No not found'}), 404

# New route to serve summary data for Co_Attainment_Cal.html
@app.route('/get_indirect_summary', methods=['GET'])
def get_indirect_summary():
    try:
        # Fetch the latest CourseAnalysis
        latest_analysis = CourseAnalysis.query.order_by(CourseAnalysis.analysis_date.desc()).first()
        if not latest_analysis:
            return jsonify({
                'error': 'No analysis data available',
                'wtAvgCO1': 0.0,
                'wtAvgCO2': 0.0,
                'wtAvgCO3': 0.0,
                'wtAvgCO4': 0.0,
                'wtAvgCO5': 0.0,
                'wtAvgCO6': 0.0
            }), 404

        # Return Wt.Avg Max Percentages
        return jsonify({
            'wtAvgCO1': float(latest_analysis.wt_avg_co1),
            'wtAvgCO2': float(latest_analysis.wt_avg_co2),
            'wtAvgCO3': float(latest_analysis.wt_avg_co3),
            'wtAvgCO4': float(latest_analysis.wt_avg_co4),
            'wtAvgCO5': float(latest_analysis.wt_avg_co5),
            'wtAvgCO6': float(latest_analysis.wt_avg_co6)
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error fetching summary data: {str(e)}"}), 500



# Routes
@app.route('/Co_Attainment_Cal')
def co_attainment_cal():
    return render_template('co_attainment_cal.html')

@app.route('/get_summary', methods=['GET'])
def get_summary():
    try:
        direct_data = DirectAttainment.query.all()
        if not direct_data:
            courses = ['CSC305.1', 'CSC305.2', 'CSC305.3', 'CSC305.4', 'CSC305.5', 'CSC305.6']
            for course in courses:
                new_direct = DirectAttainment(
                    course=course,
                    see_percentage=0.0,
                    cie_ut_avg=0.0,
                    see_atn=1,
                    cie_atn=1
                )
                db.session.add(new_direct)
            db.session.commit()
            direct_data = DirectAttainment.query.all()

        response = {
            'perc1': sum(d.see_percentage for d in direct_data) / len(direct_data),
            'perc2': sum(d.cie_ut_avg for d in direct_data) / len(direct_data)
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_indirect', methods=['GET'])
def get_indirect():
    try:
        indirect_data = IndirectAttainment.query.all()
        if not indirect_data:
            courses = ['CSC305.1', 'CSC305.2', 'CSC305.3', 'CSC305.4', 'CSC305.5', 'CSC305.6']
            for i, course in enumerate(courses, 1):
                new_indirect = IndirectAttainment(
                    course=course,
                    ces_avg=0.0,
                    ces_atn=1
                )
                db.session.add(new_indirect)
            db.session.commit()
            indirect_data = IndirectAttainment.query.all()

        response = {
            'wtAvgCO1': indirect_data[0].ces_avg,
            'wtAvgCO2': indirect_data[1].ces_avg,
            'wtAvgCO3': indirect_data[2].ces_avg,
            'wtAvgCO4': indirect_data[3].ces_avg,
            'wtAvgCO5': indirect_data[4].ces_avg,
            'wtAvgCO6': indirect_data[5].ces_avg
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_attainment', methods=['POST'])
def save_attainment():
    try:
        data = request.json
        print(f"Received save data: {data}")  # Debug
        course = data.get('course')
        see_percentage = float(data.get('see_percentage', 0))
        cie_ut_avg = float(data.get('cie_ut_avg', 0))
        ces_avg = float(data.get('ces_avg', 0))

        direct = DirectAttainment.query.filter_by(course=course).first()
        if direct:
            direct.see_percentage = see_percentage
            direct.cie_ut_avg = cie_ut_avg
            direct.see_atn = get_attainment_level(see_percentage, 'SEE')
            direct.cie_atn = get_attainment_level(cie_ut_avg, 'CIE')
        else:
            direct = DirectAttainment(
                course=course,
                see_percentage=see_percentage,
                cie_ut_avg=cie_ut_avg,
                see_atn=get_attainment_level(see_percentage, 'SEE'),
                cie_atn=get_attainment_level(cie_ut_avg, 'CIE')
            )
            db.session.add(direct)

        indirect = IndirectAttainment.query.filter_by(course=course).first()
        if indirect:
            indirect.ces_avg = ces_avg
            indirect.ces_atn = get_attainment_level(ces_avg, 'CES')
        else:
            indirect = IndirectAttainment(
                course=course,
                ces_avg=ces_avg,
                ces_atn=get_attainment_level(ces_avg, 'CES')
            )
            db.session.add(indirect)

        db.session.commit()
        print(f"Saved {course}: see_atn={direct.see_atn}, cie_atn={direct.cie_atn}, ces_atn={indirect.ces_atn}")  # Debug
        return jsonify({'message': 'Data saved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Save error: {str(e)}")  # Debug
        return jsonify({'error': str(e)}), 500

@app.route('/get_final_attainment', methods=['GET'])
def get_final_attainment():
    try:
        direct_data = DirectAttainment.query.all()
        indirect_data = IndirectAttainment.query.all()
        print(f"Direct data: {[(d.course, d.see_percentage, d.cie_ut_avg, d.see_atn, d.cie_atn) for d in direct_data]}")  # Debug
        print(f"Indirect data: {[(i.course, i.ces_avg, i.ces_atn) for i in indirect_data]}")  # Debug

        courses = ['CSC305.1', 'CSC305.2', 'CSC305.3', 'CSC305.4', 'CSC305.5', 'CSC305.6']
        if not direct_data:
            for course in courses:
                new_direct = DirectAttainment(course=course, see_percentage=0.0, cie_ut_avg=0.0, see_atn=1, cie_atn=1)
                db.session.add(new_direct)
            print("Initialized direct_attainment")
        if not indirect_data:
            for course in courses:
                new_indirect = IndirectAttainment(course=course, ces_avg=0.0, ces_atn=1)
                db.session.add(new_indirect)
            print("Initialized indirect_attainment")
        
        if not direct_data or not indirect_data:
            db.session.commit()
            direct_data = DirectAttainment.query.all()
            indirect_data = IndirectAttainment.query.all()

        direct_dict = {d.course: d for d in direct_data}
        indirect_dict = {i.course: i for i in indirect_data}

        attainments = {}
        for course in courses:
            direct = direct_dict.get(course)
            indirect = indirect_dict.get(course)
            if direct and indirect:
                direct_component = 0.8 * direct.see_atn + 0.2 * direct.cie_atn
                final_attainment = 0.9 * direct_component + 0.1 * indirect.ces_atn
                attainments[course] = round(final_attainment, 2)

                # Save or update final attainment in the database
                final_record = FinalAttainment.query.filter_by(course=course).first()
                if final_record:
                    final_record.final_attainment = attainments[course]
                else:
                    final_record = FinalAttainment(course=course, final_attainment=attainments[course])
                    db.session.add(final_record)
                print(f"{course}: see_atn={direct.see_atn}, cie_atn={direct.cie_atn}, ces_atn={indirect.ces_atn}, final={attainments[course]}")  # Debug

        db.session.commit()
        print(f"Returning: {attainments}")  # Debug
        return jsonify({"attainments": attainments}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error in get_final_attainment: {str(e)}")  # Debug
        return jsonify({"error": str(e)}), 500

@app.route('/co_achievement', methods=['GET'])
def co_achievement():
    try:
        return render_template('co_achievement.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/Po_Attainment_Cal', methods=['GET'])
def Po_Attainment_Cal():
    try:
        return render_template('Po_Attainment_Cal.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 500    

@app.route('/po_achievement', methods=['GET'])
def po_achievement():
    try:
        return render_template('po_achievement.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 500    
    
if __name__ == "__main__":
    app.run(debug=True)