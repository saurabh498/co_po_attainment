import datetime
from sqlite3 import Cursor
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
    id = db.Column(db.Integer, primary_key=True)
    avg_unit_test_marks = db.Column(db.Float, default=0.0)
    external_exam = db.Column(db.Integer, default=0)
    orals = db.Column(db.Integer, default=0)
    term_work = db.Column(db.Integer, default=0)
    cgpa = db.Column(db.Float, default=0.0)

    # Relationship with UnitTestMarks and CO_Mapping
    unit_test_marks = db.relationship('UnitTestMarks', backref='student_marks', cascade="all, delete", lazy=True)
    co_mapping = db.relationship('CO_Mapping', backref='student_marks', cascade="all, delete", lazy=True)

class UnitTestMarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_marks_id = db.Column(db.Integer, db.ForeignKey('student_marks.id'), nullable=False, index=True)
    unit_test_number = db.Column(db.Integer, nullable=False)  # 1 for UT1, 2 for UT2
    question_number = db.Column(db.String(10), nullable=False)  # e.g., "Q1_A", "Q2_B"
    marks = db.Column(db.Integer, default=0)

    # Unique constraint to avoid duplicate entries for the same student, test, and question
    __table_args__ = (db.UniqueConstraint('student_marks_id', 'unit_test_number', 'question_number', name='unique_question_per_test'),)

class CO_Mapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_marks_id = db.Column(db.Integer, db.ForeignKey('student_marks.id'), nullable=False, index=True)
    unit_test_number = db.Column(db.Integer, nullable=False)
    question_number = db.Column(db.String(10), nullable=False)  # e.g., "Q1_A", "Q2_B"
    co_value = db.Column(db.String(10))

    # Unique constraint to avoid duplicate CO mappings for the same question
    __table_args__ = (db.UniqueConstraint('student_marks_id', 'unit_test_number', 'question_number', name='unique_co_mapping'),)



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
@login_required
def view_sub_co_po():
    subject = request.args.get('subject')

    if not subject:
        return jsonify({"message": "Subject is required!"}), 400

    try:
        # Fetch data with NULL handling
        results = db.session.query(
            SubjectCOPO.co_code,
            SubjectCOPO.co_text,
            SubjectCOPO.cognition,
            SubjectCOPO.po_code,
            SubjectCOPO.po_text,
            Mapping.mapping_value,
            func.coalesce(Mapping.total_hours, 0.0).label("total_hours"),  # ✅ Handle NULL values
            func.coalesce(Mapping.avg_value, 0.0).label("avg_value")  # ✅ Handle NULL values
        ).join(
            Mapping, SubjectCOPO.id == Mapping.subject_copo_id
        ).filter(
            SubjectCOPO.user_id == current_user.id,
            SubjectCOPO.subject_name == subject
        ).all()

        if not results:
            return jsonify([])

        # Debugging - Print the results
        print("✅ DEBUGGING RESULTS:")
        for rec in results:
            print(rec)

        # Convert results to a list
        response = [
            {
                "co_code": rec.co_code or "N/A",
                "co_text": rec.co_text or "N/A",
                "cognition": rec.cognition or "N/A",
                "po_code": rec.po_code or "N/A",
                "po_text": rec.po_text or "N/A",
                "mapping_value": rec.mapping_value or 0.0,
                "total_hours": rec.total_hours or 0.0,
                "avg_value": rec.avg_value or 0.0
            }
            for rec in results
        ]

        return jsonify(response)

    except Exception as e:
        print(f"❌ ERROR in /view_sub_co_po: {e}")  # Debugging
        return jsonify({"error": str(e)}), 500


 

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

@app.route('/calculate_cgpa', methods=['POST'])
def calculateCgpa():
    try:
        # Get form data
        avg_marks = float(request.form.get('avgMarks', 0))
        external_marks = float(request.form.get('externalMarks', 0))
        oral_marks = float(request.form.get('oralMarks', 0))
        term_work_marks = float(request.form.get('termWorkMarks', 0))

        # Calculate total marks
        total_marks = avg_marks + external_marks + oral_marks + term_work_marks

        # Normalize CGPA on a 10-point scale
        cgpa = (total_marks / 150) * 10
        if cgpa > 10:
            cgpa = 10

        return jsonify({"cgpa": round(cgpa, 2)})

    except Exception as e:
        return jsonify({"error": str(e)})
    
@app.route('/save_data', methods=['POST'])
def save_data():
    try:
        data = request.get_json()
        print("Received data:", data)  # Debugging line to check incoming data

        student_id = data.get('student_id')
        if not student_id:
            return jsonify({"error": "Missing student_id"}), 400

        # Insert into student_marks
        new_student_marks = StudentMarks(
            avg_unit_test_marks=data.get('avgMarks', 0),
            external_exam=data.get('external', 0),
            orals=data.get('oral', 0),
            term_work=data.get('termWork', 0),
            cgpa=data.get('cgpa', 0.0)
        )
        db.session.add(new_student_marks)
        db.session.commit()  # Commit to get the ID

        # Insert CO Mapping if data exists
        co_mappings = data.get('co_mapping', [])  # Expecting list of mappings
        for co in co_mappings:
            new_co_mapping = CO_Mapping(
                student_marks_id=new_student_marks.id,
                unit_test_number=co.get('unit_test_number', 1),
                question_number=co.get('question_number', ""),
                co_value=co.get('co_value', "")
            )
            db.session.add(new_co_mapping)

        db.session.commit()
        return jsonify({"message": "Data saved successfully!"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500




@app.route('/next_student', methods=['POST'])
def next_student():
    return jsonify({"message": "Next student loaded!"})


if __name__ == "__main__":
    app.run(debug=True)
