import datetime
from sqlite3 import Cursor
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CursorResult
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
from datetime import datetime

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
   
# Define Student Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), nullable=False,unique = True)
    full_name = db.Column(db.String(255), nullable=False)

class ExamResult(db.Model):  
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  
    roll_no = db.Column(db.String(20), nullable=False)  
    exam_name = db.Column(db.String(100), nullable=False)  
    exam_type = db.Column(db.String(20))  # Make sure this exists!
    total_marks = db.Column(db.Integer, nullable=False)  
    marks_obtained = db.Column(db.Integer, nullable=False)  
    cgpa = db.Column(db.Numeric(4,2), default=None)   

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # ✅ FIXED

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
    return render_template("sub_co_po.html")  # Create this template

    
@app.route("/save_sub_co_po", methods=["POST"])
@login_required
def save_sub_co_po():
    data = request.json
    print("✅ Received Data:", data)  # Debugging line
    
    subject = data.get("subject")
    co_data = data.get("co_data", [])
    po_data = data.get("po_data", [])

    if not subject or not co_data or not po_data:
        return jsonify({"message": "Subject, COs, and POs are required!"}), 400

    try:
        # Delete existing records for this subject
        SubjectCOPO.query.filter_by(user_id=current_user.id, subject_name=subject).delete()
        
        # Save new CO-PO mappings
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
        
        db.session.commit()
        return jsonify({"message": "CO-PO Mapping saved successfully!"})
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")  # Debugging
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route('/view_sub_co_po', methods=['GET'])
@login_required
def view_sub_co_po():
    subject = request.args.get('subject')

    if not subject:
        return jsonify({"message": "Subject is required!"}), 400

    try:
        records = SubjectCOPO.query.filter_by(user_id=current_user.id, subject_name=subject).all()
        
        if not records:
            return jsonify([])

        unique_pos = {}
        response = []

        for rec in records:
            # Avoid duplicate POs
            if rec.po_code not in unique_pos:
                unique_pos[rec.po_code] = {
                    "po_code": rec.po_code,
                    "po_text": rec.po_text
                }

            response.append({
                "co_code": rec.co_code,
                "co_text": rec.co_text,
                "cognition": rec.cognition,
                "po_code": rec.po_code,
                "po_text": rec.po_text
            })

        return jsonify(response)

    except Exception as e:
        print(f"❌ ERROR in /view_sub_co_po: {e}")  # Debugging
        return jsonify({"error": str(e)}), 500

@app.route("/delete_subject", methods=["DELETE"])
@login_required
def delete_subject():
    data = request.json
    subject = data.get("subject")

    if not subject:
        return jsonify({"error": "Subject is required!"}), 400

    SubjectCOPO.query.filter_by(user_id=current_user.id, subject_name=subject).delete()
    db.session.commit()

    return jsonify({"message": "Subject deleted successfully!"})
    

@app.route("/delete_sub_co_po", methods=["DELETE"])
@login_required
def delete_sub_co_po():
    data = request.json
    subject = data.get("subject")

    if not subject:
        return jsonify({"message": "Subject is required!"}), 400

    SubjectCOPO.query.filter_by(user_id=current_user.id, subject_name=subject).delete()
    db.session.commit()
    return jsonify({"message": "CO-PO Mapping deleted successfully!"})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))  # 🔥 Redirect to home page


@app.route("/next_page")
def next_page():
    return render_template("next_page.html")

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

@app.route('/get_students', methods=['GET'])
def get_students():
    students = Student.query.all()
    return jsonify({"students": [{"roll_no": s.roll_no, "full_name": s.full_name} for s in students]})

@app.route('/update_student', methods=['POST'])
def update_student():
    data = request.json
    roll_no = data.get("roll_no")
    full_name = data.get("full_name")
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
    data = request.json
    roll_no = data.get("roll_no")

    if not roll_no:
        return jsonify({"message": "Roll number missing!"}), 400

    print(f"Attempting to delete student with Roll No: {roll_no}")  # Debugging

    student = Student.query.get(roll_no)

    if student:
        db.session.delete(student)
        db.session.commit()
        return jsonify({"message": "Student deleted successfully!"})
    
    print("Student not found!")  # Debugging
    return jsonify({"message": "Student not found!"}), 404

@app.route('/get_student')
def get_student():
    roll_no = request.args.get("roll_no")
    student = next((s for s in student if s["roll_no"] == roll_no), None)
    return jsonify(student) if student else ("Student not found", 404)

@app.route('/cgpa_calculation')
def cgpa_calculation():
    return render_template('cgpa_calculation.html')

@app.route('/store_exam', methods=['POST'])
def store_exam():
    data = request.get_json()
    roll_no = data.get('roll_no')
    exam_type = data.get('exam_type')
    subject_code = data.get('subject_code')
    marks_obtained = data.get('marks_obtained')
    total_marks = data.get('total_marks')
    
    student = Student.query.filter_by(roll_no=roll_no).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    new_exam_result = ExamResult(
        roll_no=roll_no,
        exam_type=exam_type,
        subject_code=subject_code,
        marks_obtained=marks_obtained,
        total_marks=total_marks
    )
    db.session.add(new_exam_result)
    db.session.commit()
    
    return jsonify({'message': 'Exam result stored successfully'})

    
@app.route('/get_exams/<roll_no>', methods=['GET'])
def get_exams(roll_no):
    exams = ExamResult.query.filter_by(roll_no=roll_no).all()
    if not exams:
        return jsonify({'message': 'No exam records found'}), 404
    
    results = []
    for exam in exams:
        results.append({
            'exam_type': exam.exam_type,
            'subject_code': exam.subject_code,
            'marks_obtained': exam.marks_obtained,
            'total_marks': exam.total_marks,
            'date': exam.date.strftime('%Y-%m-%d')
        })
    
    return jsonify({'exam_results': results})


if __name__ == "__main__":
    app.run(debug=True)
