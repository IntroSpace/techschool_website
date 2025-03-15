from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import random
import string
import os
from config import ADMIN_PASSWORD, WEB_SECRET_KEY

file_path = os.path.abspath(os.getcwd()) + "/data/database.db"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = WEB_SECRET_KEY

db = SQLAlchemy(app)


# --- Models ---
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50), nullable=True)
    balance_hours = db.Column(db.Float, default=0.0)
    password = db.Column(db.String(10), default=''.join(random.choices(string.ascii_letters + string.digits, k=8)))
    conference_link = db.Column(db.String(255), nullable=True)
    course_link = db.Column(db.String(255), nullable=True)
    telegram_login = db.Column(db.String(50), nullable=True)
    lessons = db.relationship('Lesson', backref='student', lazy=True)


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    completed = db.Column(db.Boolean, default=False)
    duration_hours = db.Column(db.Float, default=1.0)
    comment = db.Column(db.Text, nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)


class MiniCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(50), nullable=True)
    price = db.Column(db.Float, nullable=True)


class MiniLesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(255), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('mini_course.id'), nullable=False)


# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/products')
def products():
    return render_template('products.html')


@app.route('/offer')
def offer():
    return render_template('offer.html')


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


@app.route('/student/<int:id>')
def student_page(id):
    student = Student.query.get_or_404(id)
    return render_template('student.html', student=student)


@app.route('/parent/<int:id>')
def parent_page(id):
    student = Student.query.get_or_404(id)
    return render_template('parent.html', student=student)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get("admin_authenticated"):  # Проверка аутентификации
        return redirect(url_for('admin_login'))

    query = request.args.get('query', '').strip()
    max_balance = request.args.get('max_balance', type=float, default=None)

    students = Student.query

    if query:
        students = students.filter(
            (Student.last_name.ilike(f"%{query}%")) |
            (Student.first_name.ilike(f"%{query}%")) |
            (Student.middle_name.ilike(f"%{query}%"))
        )

    if max_balance is not None:
        students = students.filter(Student.balance_hours <= max_balance)

    students = students.all()
    return render_template('admin.html', students=students, query=query, max_balance=max_balance)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin_authenticated"] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin_login.html', error="Неверный пароль!")

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop("admin_authenticated", None)
    return redirect(url_for('admin_login'))


@app.route('/admin/add_student', methods=['GET', 'POST'])
def add_student():
    if not session.get("admin_authenticated"):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        student_id = request.form.get("id", type=int)
        last_name = request.form["last_name"]
        first_name = request.form["first_name"]
        middle_name = request.form.get("middle_name", "")
        balance_hours = float(request.form["balance_hours"])
        conference_link = request.form.get("conference_link", "")
        course_link = request.form.get("course_link", "")
        telegram_login = request.form.get('telegram_login', '')

        if Student.query.get(student_id):  # Проверяем, что ID не занят
            return render_template('add_student.html', error="ID уже существует!", student_id=student_id)

        new_student = Student(
            id=student_id,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            balance_hours=balance_hours,
            conference_link=conference_link,
            course_link=course_link,
            telegram_login=telegram_login
        )
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('admin'))

    return render_template('add_student.html')


@app.route('/admin/student/<int:id>/edit', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)
    if request.method == 'POST':
        student.last_name = request.form['last_name']
        student.first_name = request.form['first_name']
        student.middle_name = request.form['middle_name']
        student.balance_hours = float(request.form['balance_hours'])
        student.conference_link = request.form.get('conference_link', '')
        student.course_link = request.form.get('course_link', '')
        student.telegram_login = request.form.get('telegram_login', '')
        db.session.commit()
        # return redirect(url_for('admin'))
        return redirect(url_for('edit_student', id=id))
    return render_template('edit_student.html', student=student)


@app.route('/admin/student/<int:id>/add_lesson', methods=['POST'])
def add_lesson(id):
    student = Student.query.get_or_404(id)
    duration = float(request.form['duration'])
    completed = 'completed' in request.form
    comment = request.form['comment']

    new_lesson = Lesson(duration_hours=duration, student_id=id, comment=comment, completed=completed)
    student.balance_hours -= duration
    db.session.add(new_lesson)
    db.session.commit()
    return redirect(url_for('edit_student', id=id))


@app.route('/admin/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if request.method == 'POST':
        lesson.completed = 'completed' in request.form
        lesson.duration_hours = float(request.form['duration'])
        lesson.comment = request.form['comment']
        db.session.commit()
        return redirect(url_for('edit_student', id=lesson.student_id))
    return render_template('edit_lesson.html', lesson=lesson)


@app.route('/admin/lesson/<int:lesson_id>/delete', methods=['POST'])
def delete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    student = Student.query.get(lesson.student_id)
    student.balance_hours += lesson.duration_hours  # Возвращаем часы в баланс
    db.session.delete(lesson)
    db.session.commit()
    return redirect(url_for('edit_student', id=lesson.student_id))


@app.route('/admin/add-mini-course', methods=['GET', 'POST'])
def add_mini_course():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image_url = request.form['image_url']
        password = request.form['password']
        price = request.form['price']
        new_course = MiniCourse(title=title, description=description, image_url=image_url, password=password, price=price)
        db.session.add(new_course)
        db.session.commit()
        return redirect(url_for('admin_mini_courses'))
    return render_template('add_mini_course.html')


@app.route('/admin/add-mini-lesson/<int:course_id>', methods=['GET', 'POST'])
def add_mini_lesson(course_id):
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        video_url = request.form['video_url']
        new_lesson = MiniLesson(title=title, description=description, video_url=video_url, course_id=course_id)
        db.session.add(new_lesson)
        db.session.commit()
        return redirect(url_for('admin_mini_lessons', id=course_id))
    return render_template('add_mini_lesson.html', course_id=course_id)


@app.route('/admin/edit-mini-course/<int:id>', methods=['GET', 'POST'])
def edit_mini_course(id):
    course = MiniCourse.query.get_or_404(id)
    if request.method == 'POST':
        course.title = request.form['title']
        course.description = request.form['description']
        course.image_url = request.form['image_url']
        course.password = request.form['password']
        db.session.commit()
        return redirect(url_for('admin_mini_courses'))
    return render_template('edit_mini_course.html', course=course)

@app.route('/admin/delete-mini-course/<int:id>', methods=['POST'])
def delete_mini_course(id):
    course = MiniCourse.query.get_or_404(id)
    MiniLesson.query.filter_by(course_id=id).delete()
    db.session.delete(course)
    db.session.commit()
    return redirect(url_for('admin_mini_courses'))

@app.route('/admin/edit-mini-lesson/<int:id>', methods=['GET', 'POST'])
def edit_mini_lesson(id):
    lesson = MiniLesson.query.get_or_404(id)
    if request.method == 'POST':
        lesson.title = request.form['title']
        lesson.description = request.form['description']
        lesson.video_url = request.form['video_url']
        db.session.commit()
        return redirect(url_for('admin_mini_lessons', id=lesson.course_id))
    return render_template('edit_mini_lesson.html', lesson=lesson)

@app.route('/admin/delete-mini-lesson/<int:id>', methods=['POST'])
def delete_mini_lesson(id):
    lesson = MiniLesson.query.get_or_404(id)
    course_id = lesson.course_id
    db.session.delete(lesson)
    db.session.commit()
    return redirect(url_for('admin_mini_lessons', id=course_id))


@app.route('/admin/mini-courses')
def admin_mini_courses():
    courses = MiniCourse.query.all()
    return render_template('admin_mini_courses.html', courses=courses)


@app.route('/admin/mini-course/<int:id>/lessons')
def admin_mini_lessons(id):
    course = MiniCourse.query.get_or_404(id)
    lessons = MiniLesson.query.filter_by(course_id=id).all()
    return render_template('admin_mini_lessons.html', course=course, lessons=lessons)


@app.route('/mini-courses')
def mini_courses():
    courses = MiniCourse.query.all()
    return render_template('mini_courses.html', courses=courses)


@app.route('/mini-course/<int:id>', methods=['GET', 'POST'])
def mini_course(id):
    course = MiniCourse.query.get_or_404(id)
    if request.method == 'POST':
        entered_password = request.form['password']
        if entered_password == course.password:
            session[f'course_{id}'] = True
        else:
            return render_template('mini_course.html', course=course, error='Неверный пароль!')
    access_granted = session.get(f'course_{id}', False)
    lessons = MiniLesson.query.filter_by(course_id=id).all() if access_granted else []
    return render_template('mini_course.html', course=course, lessons=lessons, access_granted=access_granted)


@app.route('/mini-lesson/<int:id>')
def mini_lesson(id):
    lesson = MiniLesson.query.get_or_404(id)
    course = MiniCourse.query.get_or_404(lesson.course_id)
    lessons = MiniLesson.query.filter_by(course_id=course.id).all()

    current_index = lessons.index(lesson)
    prev_lesson = lessons[current_index - 1].id if current_index > 0 else None
    next_lesson = lessons[current_index + 1].id if current_index < len(lessons) - 1 else None

    return render_template('mini_lesson.html', lesson=lesson, course=course, prev_lesson=prev_lesson,
                           next_lesson=next_lesson)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # app.run(debug=True)
    app.run(port=8080)
