from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
from collections import defaultdict
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuration
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Vivekreddy1234*'
app.config['MYSQL_DATABASE_DB'] = 'acad_hall_slot_management'

# Connect to MySQL
db = mysql.connector.connect(
    host=app.config['MYSQL_DATABASE_HOST'],
    user=app.config['MYSQL_DATABASE_USER'],
    password=app.config['MYSQL_DATABASE_PASSWORD'],
    database=app.config['MYSQL_DATABASE_DB']
)

cursor = db.cursor(dictionary=True)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form['user_type']
        user_id = request.form['user_id']
        password = request.form['password']
        
        if user_type == 'student':
            query = "SELECT * FROM STUDENT WHERE Student_Id = %s AND Password = %s"
        elif user_type == 'faculty':
            query = "SELECT * FROM INSTRUCTOR WHERE Instructor_Id = %s AND Password = %s"
        else:
            flash('Invalid user type')
            return redirect(url_for('login'))
        
        cursor.execute(query, (user_id, password))
        user = cursor.fetchone()
        
        if user:
            session['user_id'] = user_id
            session['user_type'] = user_type
            if user_type == 'student':
                return redirect(url_for('student_dashboard'))
            elif user_type == 'faculty':
                return redirect(url_for('faculty_dashboard'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_type', None)
    return redirect(url_for('login'))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        password = request.form['password']
        
        if admin_id == 'admin' and password == 'admin':
            session['admin_id'] = admin_id
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard
        else:
            flash('Invalid admin credentials')
    
    return render_template('admin_login.html')


# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    return render_template('admin_dashboard.html')

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    student_id = session['user_id']
    
    # Fetch the student's timetable
    query = """
    SELECT SLOT.Slot_Id, SLOT.Time_Start, SLOT.Time_End, HALLS.Hall_Id, COURSE.Course_Id, COURSE.Name AS Course_Name, INSTRUCTOR.Name AS Instructor_Name
    FROM ENROLLED
    JOIN SLOT ON ENROLLED.Slot_Id = SLOT.Slot_Id
    JOIN HALLS ON SLOT.Hall_Id = HALLS.Hall_Id
    JOIN COURSE ON ENROLLED.Course_Id = COURSE.Course_Id
    JOIN INSTRUCTOR ON COURSE.Instructor_Id = INSTRUCTOR.Instructor_Id
    WHERE ENROLLED.Student_Id = %s
    """
    cursor.execute(query, (student_id,))
    timetable = cursor.fetchall()
    
    # Group the timetable by days
    grouped_timetable = defaultdict(list)
    for entry in timetable:
        grouped_timetable[entry['Day']].append(entry)
    
    # Fetch the lecture requests by professors
    query = "SELECT * FROM INSTRUCTOR_REQUEST WHERE Batch = (SELECT Batch FROM STUDENT WHERE Student_Id = %s)"
    cursor.execute(query, (student_id,))
    requests = cursor.fetchall()
    
    return render_template('student_dashboard.html', timetable=grouped_timetable, requests=requests)

@app.route('/faculty_dashboard', methods=['GET', 'POST'])
def faculty_dashboard():
    if 'user_id' not in session or session['user_type'] != 'faculty':
        return redirect(url_for('login'))
    
    instructor_id = session['user_id']
    
    if request.method == 'POST':
        request_id = request.form['request_id']
        course_id = request.form['course_id']
        batch = request.form['batch']
        slot_id = request.form['slot_id']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        
        # Check slot availability
        availability_query = "SELECT * FROM SLOT WHERE Slot_Id = %s AND Hall_Id NOT IN (SELECT Hall_Id FROM INSTRUCTOR_REQUEST WHERE Slot_Id = %s AND Time_Start < %s AND Time_End > %s)"
        cursor.execute(availability_query, (slot_id, slot_id, time_end, time_start))
        available_slots = cursor.fetchall()
        
        if available_slots:
            # Slot is available
            status = 'Available'
        else:
            # Slot is not available
            status = 'Not Available'
        
        # Insert the request with status
        query = "INSERT INTO INSTRUCTOR_REQUEST (Request_Id, Instructor_Id, Course_Id, Batch, Slot_Id, Time_Start, Time_End, Status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        values = (request_id, instructor_id, course_id, batch, slot_id, time_start, time_end, status)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('faculty_dashboard'))
    
    # Fetch the faculty's schedule including status
    query = """
    SELECT SLOT.Slot_Id, SLOT.Day, SLOT.Time_Start, SLOT.Time_End, HALLS.Hall_Id, COURSE.Course_Id, COURSE.Name AS Course_Name, INSTRUCTOR_REQUEST.Status
    FROM COURSE
    JOIN SLOT ON COURSE.Slot_Id = SLOT.Slot_Id
    JOIN HALLS ON SLOT.Hall_Id = HALLS.Hall_Id
    LEFT JOIN INSTRUCTOR_REQUEST ON COURSE.Course_Id = INSTRUCTOR_REQUEST.Course_Id AND INSTRUCTOR_REQUEST.Instructor_Id = %s
    WHERE COURSE.Instructor_Id = %s
    """
    cursor.execute(query, (instructor_id, instructor_id))
    schedule = cursor.fetchall()
    
    # Fetch the faculty's requests
    query = "SELECT * FROM INSTRUCTOR_REQUEST WHERE Instructor_Id = %s"
    cursor.execute(query, (instructor_id,))
    requests = cursor.fetchall()
    
    return render_template('faculty_dashboard.html', schedule=schedule, requests=requests)

@app.route('/students', methods=['GET', 'POST'])
def students():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        dept = request.form['dept']
        sem = request.form['sem']
        email = request.form['email']
        phone = request.form['phone']
        batch = request.form['batch']
        credits = request.form['credits']
        password = request.form['password']
        
        query = "INSERT INTO STUDENT (Student_Id, Name, Dept, Sem, E_Mail, Phone_Number, Batch, Total_Credits, Password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (student_id, name, dept, sem, email, phone, batch, credits, password)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('students'))
    
    cursor.execute("SELECT * FROM STUDENT")
    students = cursor.fetchall()
    return render_template('students.html', students=students)

@app.route('/students/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    query = "DELETE FROM STUDENT WHERE Student_Id = %s"
    cursor.execute(query, (student_id,))
    db.commit()
    return redirect(url_for('students'))

@app.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['dept']
        sem = request.form['sem']
        email = request.form['email']
        phone = request.form['phone']
        batch = request.form['batch']
        credits = request.form['credits']
        password = request.form['password']
        
        query = "UPDATE STUDENT SET Name = %s, Dept = %s, Sem = %s, E_Mail = %s, Phone_Number = %s, Batch = %s, Total_Credits = %s, Password = %s WHERE Student_Id = %s"
        values = (name, dept, sem, email, phone, batch, credits, password, student_id)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('students'))
    
    cursor.execute("SELECT * FROM STUDENT WHERE Student_Id = %s", (student_id,))
    student = cursor.fetchone()
    return render_template('edit_student.html', student=student)

@app.route('/instructors', methods=['GET', 'POST'])
def instructors():
    if request.method == 'POST':
        instructor_id = request.form['instructor_id']
        name = request.form['name']
        dept = request.form['dept']
        email = request.form['email']
        cabin_no = request.form['cabin_no']
        course_id = request.form['course_id']
        batch = request.form['batch']
        password = request.form['password']
        
        query = "INSERT INTO INSTRUCTOR (Instructor_Id, Name, Dept, E_mail, Cabin_no, Course_Id, Batch, Password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        values = (instructor_id, name, dept, email, cabin_no, course_id, batch, password)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('instructors'))
    
    cursor.execute("SELECT * FROM INSTRUCTOR")
    instructors = cursor.fetchall()
    return render_template('instructors.html', instructors=instructors)

@app.route('/instructors/delete/<int:instructor_id>', methods=['POST'])
def delete_instructor(instructor_id):
    query = "DELETE FROM INSTRUCTOR WHERE Instructor_Id = %s"
    cursor.execute(query, (instructor_id,))
    db.commit()
    return redirect(url_for('instructors'))

@app.route('/instructors/edit/<int:instructor_id>', methods=['GET', 'POST'])
def edit_instructor(instructor_id):
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['dept']
        email = request.form['email']
        cabin_no = request.form['cabin_no']
        course_id = request.form['course_id']
        batch = request.form['batch']
        password = request.form['password']
        
        query = "UPDATE INSTRUCTOR SET Name = %s, Dept = %s, E_mail = %s, Cabin_no = %s, Course_Id = %s, Batch = %s, Password = %s WHERE Instructor_Id = %s"
        values = (name, dept, email, cabin_no, course_id, batch, password, instructor_id)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('instructors'))
    
    cursor.execute("SELECT * FROM INSTRUCTOR WHERE Instructor_Id = %s", (instructor_id,))
    instructor = cursor.fetchone()
    return render_template('edit_instructor.html', instructor=instructor)

@app.route('/courses', methods=['GET', 'POST'])
def courses():
    if request.method == 'POST':
        course_id = request.form['course_id']
        name = request.form['name']
        credits = request.form['credits']
        sem = request.form['sem']
        dept = request.form['dept']
        num_of_std = request.form['num_of_std']
        instructor_id = request.form['instructor_id']
        hall_id = request.form['hall_id']
        slot_id = request.form['slot_id']
        
        query = "INSERT INTO COURSE (Course_Id, Name, Credits, Sem, Dept, Num_of_std, Instructor_Id, Hall_Id, Slot_Id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (course_id, name, credits, sem, dept, num_of_std, instructor_id, hall_id, slot_id)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('courses'))
    
    cursor.execute("SELECT * FROM COURSE")
    courses = cursor.fetchall()
    return render_template('courses.html', courses=courses)

@app.route('/courses/delete/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    query = "DELETE FROM COURSE WHERE Course_Id = %s"
    cursor.execute(query, (course_id,))
    db.commit()
    return redirect(url_for('courses'))

@app.route('/courses/edit/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if request.method == 'POST':
        name = request.form['name']
        credits = request.form['credits']
        sem = request.form['sem']
        dept = request.form['dept']
        num_of_std = request.form['num_of_std']
        instructor_id = request.form['instructor_id']
        hall_id = request.form['hall_id']
        slot_id = request.form['slot_id']
        
        query = "UPDATE COURSE SET Name = %s, Credits = %s, Sem = %s, Dept = %s, Num_of_std = %s, Instructor_Id = %s, Hall_Id = %s, Slot_Id = %s WHERE Course_Id = %s"
        values = (name, credits, sem, dept, num_of_std, instructor_id, hall_id, slot_id, course_id)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('courses'))
    
    cursor.execute("SELECT * FROM COURSE WHERE Course_Id = %s", (course_id,))
    course = cursor.fetchone()
    return render_template('edit_course.html', course=course)

@app.route('/slots', methods=['GET', 'POST'])
def slots():
    if request.method == 'POST':
        slot_id = request.form['slot_id']
        day = request.form['day']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        hall_id = request.form['hall_id']
        batch = request.form['batch']
        
        query = "INSERT INTO SLOT (Slot_Id, Day, Time_Start, Time_End, Hall_Id, Batch) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (slot_id, day, time_start, time_end, hall_id, batch)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('slots'))
    
    cursor.execute("SELECT * FROM SLOT")
    slots = cursor.fetchall()
    return render_template('slots.html', slots=slots)

@app.route('/slots/delete/<int:slot_id>', methods=['POST'])
def delete_slot(slot_id):
    query = "DELETE FROM SLOT WHERE Slot_Id = %s"
    cursor.execute(query, (slot_id,))
    db.commit()
    return redirect(url_for('slots'))

@app.route('/slots/edit/<int:slot_id>', methods=['GET', 'POST'])
def edit_slot(slot_id):
    if request.method == 'POST':
        day = request.form['day']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        hall_id = request.form['hall_id']
        batch = request.form['batch']
        
        query = "UPDATE SLOT SET Day = %s, Time_Start = %s, Time_End = %s, Hall_Id = %s, Batch = %s WHERE Slot_Id = %s"
        values = (day, time_start, time_end, hall_id, batch, slot_id)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('slots'))
    
    cursor.execute("SELECT * FROM SLOT WHERE Slot_Id = %s", (slot_id,))
    slot = cursor.fetchone()
    return render_template('edit_slot.html', slot=slot)

@app.route('/halls', methods=['GET', 'POST'])
def halls():
    if request.method == 'POST':
        hall_id = request.form['hall_id']
        capacity = request.form['capacity']
        projector = request.form['projector']
        mic = request.form['mic']
        floor = request.form['floor']
        
        query = "INSERT INTO HALLS (Hall_Id, Capacity, Projector, Mic, Floor) VALUES (%s, %s, %s, %s, %s)"
        values = (hall_id, capacity, projector, mic, floor)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('halls'))
    
    cursor.execute("SELECT * FROM HALLS")
    halls = cursor.fetchall()
    return render_template('halls.html', halls=halls)

@app.route('/halls/delete/<int:hall_id>', methods=['POST'])
def delete_hall(hall_id):
    query = "DELETE FROM HALLS WHERE Hall_Id = %s"
    cursor.execute(query, (hall_id,))
    db.commit()
    return redirect(url_for('halls'))

@app.route('/halls/edit/<int:hall_id>', methods=['GET', 'POST'])
def edit_hall(hall_id):
    if request.method == 'POST':
        capacity = request.form['capacity']
        projector = request.form['projector']
        mic = request.form['mic']
        floor = request.form['floor']
        
        query = "UPDATE HALLS SET Capacity = %s, Projector = %s, Mic = %s, Floor = %s WHERE Hall_Id = %s"
        values = (capacity, projector, mic, floor, hall_id)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('halls'))
    
    cursor.execute("SELECT * FROM HALLS WHERE Hall_Id = %s", (hall_id,))
    hall = cursor.fetchone()
    return render_template('edit_hall.html', hall=hall)

@app.route('/requests', methods=['GET', 'POST'])
def requests():
    if request.method == 'POST':
        request_id = request.form['request_id']
        instructor_id = request.form['instructor_id']
        course_id = request.form['course_id']
        batch = request.form['batch']
        slot_id = request.form['slot_id']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        status = request.form['status']
        
        query = "INSERT INTO INSTRUCTOR_REQUEST (Request_Id, Instructor_Id, Course_Id, Batch, Slot_Id, Time_Start, Time_End, Status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        values = (request_id, instructor_id, course_id, batch, slot_id, time_start, time_end, status)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('requests'))
    
    cursor.execute("SELECT * FROM INSTRUCTOR_REQUEST")
    requests = cursor.fetchall()
    return render_template('requests.html', requests=requests)

@app.route('/requests/delete/<int:request_id>', methods=['POST'])
def delete_request(request_id):
    query = "DELETE FROM INSTRUCTOR_REQUEST WHERE Request_Id = %s"
    cursor.execute(query, (request_id,))
    db.commit()
    return redirect(url_for('requests'))

@app.route('/requests/edit/<int:request_id>', methods=['GET', 'POST'])
def edit_request(request_id):
    if request.method == 'POST':
        instructor_id = request.form['instructor_id']
        course_id = request.form['course_id']
        batch = request.form['batch']
        slot_id = request.form['slot_id']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        status = request.form['status']
        
        query = "UPDATE INSTRUCTOR_REQUEST SET Instructor_Id = %s, Course_Id = %s, Batch = %s, Slot_Id = %s, Time_Start = %s, Time_End = %s, Status = %s WHERE Request_Id = %s"
        values = (instructor_id, course_id, batch, slot_id, time_start, time_end, status, request_id)
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for('requests'))
    
    cursor.execute("SELECT * FROM INSTRUCTOR_REQUEST WHERE Request_Id = %s", (request_id,))
    request = cursor.fetchone()
    return render_template('edit_request.html', request=request)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)