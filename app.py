import datetime
from sqlite3 import Cursor
from venv import logger
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CursorResult
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
from datetime import datetime
from flask_sqlalchemy import session
from flask import session, redirect, url_for
from sqlalchemy.sql import func
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
    __tablename__ = 'student_marks'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False, unique=True)  # Roll number
    avg_unit_test_marks = db.Column(db.Float, default=0.0)  # Average of UT1 (and UT2 if added later)
    external_exam = db.Column(db.Float, default=0.0)  # Max 80
    orals = db.Column(db.Float, default=0.0)  # Max 25
    term_work = db.Column(db.Float, default=0.0)  # Max 25
    cgpa = db.Column(db.Float, default=0.0)  # Calculated CGPA

class UnitTestMarks(db.Model):
    __tablename__ = 'unit_test_marks'
    id = db.Column(db.Integer, primary_key=True)
    student_marks_id = db.Column(db.Integer, db.ForeignKey('student_marks.id'), nullable=False, index=True)
    unit_test_number = db.Column(db.Integer, nullable=False)  # 1 for UT1
    question_number = db.Column(db.String(10), nullable=False)  # e.g., "1a", "2b", "3a"
    marks = db.Column(db.Integer, default=0)  # Marks for each question
    __table_args__ = (db.UniqueConstraint('student_marks_id', 'unit_test_number', 'question_number', name='unique_question_per_test'),)

class CO_Mapping(db.Model):
    __tablename__ = 'co_mapping'
    id = db.Column(db.Integer, primary_key=True)
    student_marks_id = db.Column(db.Integer, db.ForeignKey('student_marks.id'), nullable=False, index=True)
    unit_test_number = db.Column(db.Integer, nullable=False)  # 1 for UT1
    question_number = db.Column(db.String(10), nullable=False)  # e.g., "1a", "2b", "3a"
    co_value = db.Column(db.String(10))  # CO value (e.g., "CO1", "CO2")
    __table_args__ = (db.UniqueConstraint('student_marks_id', 'unit_test_number', 'question_number', name='unique_co_mapping'),)

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
    mapping_data = data.get("mapping_data", [])  # ✅ Extract CO-PO Mapping Values

    if not subject or not co_data or not po_data:
        return jsonify({"message": "Subject, COs, and POs are required!"}), 400

    try:
        # Delete existing CO-PO records for this subject
        SubjectCOPO.query.filter_by(user_id=current_user.id, subject_name=subject).delete()
        db.session.commit()  # ✅ Ensure old records are removed before inserting new ones

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

        db.session.flush()  # ✅ Get IDs of newly inserted SubjectCOPO entries

        # ✅ Debugging: Check if CO-PO records are saved
        print(f"✅ New CO-PO Entries: {[{'id': entry.id, 'co_code': entry.co_code, 'po_code': entry.po_code} for entry in new_entries]}")

        # ✅ Save CO-PO Mapping Table values
        for mapping in mapping_data:
            related_entry = next(
                (entry for entry in new_entries if entry.co_code == mapping["co_code"] and entry.po_code == mapping["po_code"]), 
                None
            )
            if related_entry:
                new_mapping = Mapping(
                    user_id=current_user.id,
                    subject_copo_id=related_entry.id,  # ✅ Corrected to use `subject_copo_id`
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
        return jsonify({"message": "CO-PO Mapping saved successfully!"})

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")  # Debugging
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route('/view_sub_co_po', methods=['GET'])
def view_sub_co_po():
    subject = request.args.get('subject')
    if not subject:
        return jsonify({"message": "Subject name required"}), 400

    # Fetch all SubjectCOPO entries for the subject
    subject_copos = SubjectCOPO.query.filter_by(subject_name=subject).all()
    if not subject_copos:
        return jsonify({"message": "No data found for this subject"}), 404

    # Construct response
    result = []
    for sc in subject_copos:
        mappings = Mapping.query.filter_by(subject_copo_id=sc.id).all()
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


@app.route('/cgpa_calculation')
def cgpa_calculation():
    return render_template('cgpa_calculation.html')

@app.route('/save_data', methods=['POST'])
def save_course_data():
    data = request.get_json()
    if not data or 'student_id' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    student = StudentMarks.query.filter_by(student_id=data['student_id']).first()
    if not student:
        student = StudentMarks(student_id=data['student_id'])
        db.session.add(student)

    student.avg_unit_test_marks = data['avg_unit_test_marks']
    student.external_exam = data['external_exam']
    student.orals = data['orals']
    student.term_work = data['term_work']
    student.cgpa = data['cgpa']

    # Clear and update Unit Test Marks for UT1
    UnitTestMarks.query.filter_by(student_marks_id=student.id, unit_test_number=1).delete()
    for ut in data['unit_test_marks']:
        if ut['unit_test_number'] == 1:  # Only UT1 based on HTML
            ut_record = UnitTestMarks(
                student_marks_id=student.id,
                unit_test_number=ut['unit_test_number'],
                question_number=ut['question_number'],
                marks=ut['marks']
            )
            db.session.add(ut_record)

    # Clear and update CO Mapping for UT1
    CO_Mapping.query.filter_by(student_marks_id=student.id, unit_test_number=1).delete()
    for co in data['co_mapping']:
        if co['unit_test_number'] == 1:  # Only UT1 based on HTML
            co_record = CO_Mapping(
                student_marks_id=student.id,
                unit_test_number=co['unit_test_number'],
                question_number=co['question_number'],
                co_value=co['co_value']
            )
            db.session.add(co_record)

    db.session.commit()
    return jsonify({'message': 'Data saved successfully'})

@app.route('/load_data', methods=['GET'])
def load_data():
    roll_no = request.args.get('roll_no')
    
    if not roll_no:
        return jsonify({"error": "Missing roll_no parameter"}), 400

    student = StudentMarks.query.filter_by(student_id=roll_no).first()
    
    if not student:
        return jsonify({"message": "No data found"}), 404

    unit_test_marks = UnitTestMarks.query.filter_by(student_marks_id=student.id, unit_test_number=1).all()
    co_mapping = CO_Mapping.query.filter_by(student_marks_id=student.id, unit_test_number=1).all()

    return jsonify({
        "avg_unit_test_marks": student.avg_unit_test_marks,
        "external_exam": student.external_exam,
        "orals": student.orals,
        "term_work": student.term_work,
        "cgpa": student.cgpa,
        "unit_test_marks": [
            {"unit_test_number": ut.unit_test_number, "question_number": ut.question_number, "marks": ut.marks}
            for ut in unit_test_marks
        ],
        "co_mapping": [
            {"unit_test_number": co.unit_test_number, "question_number": co.question_number, "co_value": co.co_value}
            for co in co_mapping
        ]
    })
    roll_no = request.args.get('roll_no')
    if not roll_no:
        return jsonify({"error": "No roll number provided"}), 400
    
    unit_test_marks = UnitTestMarks.query.filter_by(roll_no=roll_no).all()
    co_mapping = CO_Mapping.query.filter_by(roll_no=roll_no).all()
    student_data = StudentMarks.query.filter_by(roll_no=roll_no).first()
    
    if not student_data:
        return jsonify({"message": "No data found"})
    
    return jsonify({
        "external_exam": student_data.external_exam,
        "orals": student_data.orals,
        "term_work": student_data.term_work,
        "avg_unit_test_marks": student_data.avg_unit_test_marks,
        "cgpa": student_data.cgpa,
        "unit_test_marks": [{
            "unit_test_number": utm.unit_test_number,
            "question_number": utm.question_number,
            "marks": utm.marks
        } for utm in unit_test_marks],
        "co_mapping": [{
            "unit_test_number": co.unit_test_number,
            "question_number": co.question_number,
            "co_value": co.co_value
        } for co in co_mapping]
    })

@app.route('/course_exit_analysis')
def course_exit_analysis():
    return render_template('course_exit_analysis.html')

# Save Data (Insert into DB)
@app.route('/save', methods=['POST'])
def save_data():
    data = request.json
    new_entry = CourseExitForm(**data)
    
    try:
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"message": "Data saved successfully!"}), 201
    except:
        db.session.rollback()
        return jsonify({"error": "Roll No already exists or invalid data!"}), 400

# Retrieve Data (View)
@app.route('/view', methods=['GET'])
def view_data():
    records = CourseExitForm.query.all()
    return jsonify([{
        "roll_no": r.roll_no, "q1": r.q1, "q2": r.q2, "q3": r.q3,
        "q4": r.q4, "q5": r.q5, "q6": r.q6
    } for r in records])

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    try:
        data = request.json
        for record in data:
            new_entry = CourseExitForm(**record)
            db.session.add(new_entry)
        db.session.commit()
        return jsonify({"message": "CSV data uploaded successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Delete Data
@app.route('/delete/<string:roll_no>', methods=['DELETE'])
def delete_data(roll_no):
    record = CourseExitForm.query.filter_by(roll_no=roll_no).first()
    if record:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"message": "Record deleted successfully!"})
    return jsonify({"error": "Roll No not found!"}), 404


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


@app.route('/students_analysis')
def students_analysis():
    return render_template('students_analysis.html')

if __name__ == "__main__":
    app.run(debug=True)