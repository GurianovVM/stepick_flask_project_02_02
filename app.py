from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import func
from flask_migrate import Migrate
import json
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, RadioField
from wtforms.validators import InputRequired, Length

with open('./static/goals.json', 'r') as f:
    goals = json.load(f)
'''
with open('./static/teachers.json', 'r') as f:
    teachers = json.load(f)
'''
week = {'mon': 'Понедельник', 'tue': 'Вторник', 'wed': 'Среда', 'thu': 'Четверг', 'fri': 'Пятница', 'sat': 'Суббота',
        'sun': 'Воскресенье'}
times = {'time_1': '1-2', 'time_2': '3-5', 'time_3': '5-7', 'time_4': '7-10'}

app = Flask(__name__)
app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Модель учителя в бд
class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    about = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    picture = db.Column(db.String(550), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    goal = db.Column(db.String(350), nullable=False)
    free = db.Column(db.String(1000), nullable=False)
    reverse = db.relationship('Reserve')


# Модель запроса на выбор времени
class Reserve(db.Model):
    __tablename__ = 'reserves'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    day = db.Column(db.String(3), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    teacher = db.relationship('Teacher')


# Модель запроса на подбор преподавателя
class Select(db.Model):
    __tablename__ = 'selections'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.Integer, nullable=False)
    goal = db.Column(db.String(30), nullable=False)
    time_learning = db.Column(db.String(20), nullable=False)


# Модель формы резерва времени
class ReserveForm(FlaskForm):
    name = StringField('Вас зовут', [InputRequired(), Length(min=3, max=100, message="от 3 до 100 символов")])
    phone = StringField('Ваш телефон', [InputRequired(), Length(min=4, max=15, message="от 4 до 15 цифр")])
    submit = SubmitField('Записаться на пробный урок')


# Модель на запрос преподователя
class SelectForm(FlaskForm):
    name = StringField('Вас зовут', [InputRequired(), Length(min=3, max=100, message="от 3 до 100 символов")])
    phone = StringField('Ваш телефон', [InputRequired(), Length(min=4, max=15, message="от 4 до 15 цифр")])
    goal = RadioField('Какая цель занятий?', default="work")
    limit_time = RadioField('Сколько времени есть?', default="time_3")
    submit = SubmitField('Найдите мне преподователя')


# заполнение таблицы учителей
def db_teachers():
    for t in teachers:
        create_teacher = Teacher(name=t['name'], about=t['about'], rating=t['rating'], picture=t['picture'],
                                 price=t['price'], goal=", ".join(t['goals']), free=str(json.dumps(t['free'])))
        db.session.add(create_teacher)
    db.session.commit()


# db_teachers()


@app.route('/')
def render_main():
    teacher = db.session.query(Teacher).order_by(func.random()).limit(6)
    temp_goal = {}
    for i in goals:
        temp_goal[i] = goals[i]
    temp_goal['travel'] = '⛱' + goals['travel']
    temp_goal['study'] = '🏫 ' + goals['study']
    temp_goal['work'] = '🏢 ' + goals['work']
    temp_goal['relocate'] = '🚜 ' + goals['relocate']
    return render_template('index.html', goals=temp_goal, teacher=teacher)


@app.route('/goals/<goal>/')
def render_goal(goal):
    goal_teacher = db.session.query(Teacher).filter(Teacher.goal.like('%' + goal + '%')).order_by(Teacher.rating).all()
    for i in goals:
        if i == goal:
            goal = goals[i]
    return render_template('goal.html', goal=goal, teachers=goal_teacher)


@app.route('/profiles/<id_teacher>/')
def render_profiles(id_teacher):
    temp = db.session.query(Teacher).get_or_404(id_teacher)
    teacher = {"id": temp.id, "name": temp.name, "about": temp.about, "rating": temp.rating, "picture": temp.picture,
               "price": temp.price, "free": json.loads(temp.free)}
    return render_template('profile.html', teacher=teacher, week=week, goals=goals)


@app.route('/request/', methods=['GET', 'POST'])
def render_request():
    form = SelectForm()
    choice_goal = []
    for i in goals:
        choice_goal.append(tuple([i, goals[i]]))
    form.goal.choices = choice_goal
    choice_time = []
    for i in times:
        choice_time.append(tuple([i, times[i]]))
    form.limit_time.choices = choice_time

    if form.validate_on_submit():
        select_order = Select(name=form.name.data, phone=form.phone.data, goal=form.goal.data,
                              time_learning=form.limit_time.data)
        db.session.add(select_order)
        db.session.commit()
        return render_template('request_done.html', name=form.name.data, phone=form.phone.data,
                               time=times[form.limit_time.data], goal=goals[form.goal.data])
    else:
        return render_template('request.html', form=form)


@app.route('/booking/<id_teacher>/<day>/<time>/', methods=['GET', 'POST'])
def render_booking(id_teacher, day, time):
    teacher_query = db.session.query(Teacher).get_or_404(id_teacher)
    teacher = {"id": teacher_query.id, "name": teacher_query.name, "picture": teacher_query.picture}
    form = ReserveForm()
    client_day = ''
    for week_day in week:
        if day == week_day:
            client_day = week[week_day]

    if form.validate_on_submit():
        reserve_order = Reserve(name=form.name.data, phone=form.phone.data, day=day, time=time, teacher_id=id_teacher)
        db.session.add(reserve_order)
        db.session.commit()
        return render_template('booking_done.html', name=reserve_order.name, client_day=client_day,
                               hour=reserve_order.time, phone=reserve_order.phone)
    else:
        return render_template('booking.html', teacher=teacher, day=day, client_day=client_day, time=time, form=form,
                               id=id_teacher)


@app.route('/all/')
def render_all_profiles():
    return render_template('all_profile.html', teachers=db.session.query(Teacher).all())


if __name__ == '__main__':
    app.run()
