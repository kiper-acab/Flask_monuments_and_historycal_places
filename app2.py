# импорты
from flask import Flask, render_template, redirect, request, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests  


# инициализация
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = '123'
db = SQLAlchemy(app)
manager = LoginManager(app)


# ORM модели
class Towns(db.Model):
    __tablename__ = 'towns'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(200))
    background = db.Column(db.String(200))
    description = db.Column(db.Text)

    def __repr__(self) -> str:
        return f"Город [{self.id}] {self.name}"


class Monuments(db.Model):
    __tablename__ = 'monuments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    town = db.Column(db.Integer, db.ForeignKey('towns.id'), nullable=False)
    rating = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))
    map = db.Column(db.Text)

    def __repr__(self) -> str:
        return f"Памятник [{self.id}] {self.name}"
    

class Historical_places(db.Model):
    __tablename__ = 'historical_places'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    town = db.Column(db.Integer, db.ForeignKey('towns.id'), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))

    def __repr__(self) -> str:
        return f"Исторические места: {self.name}"
    

class People(db.Model, UserMixin):
    __tablename__ = 'people'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self) -> str:
        return f"Пользователь [{self.id}] {self.name}"


class Comments(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False)
    town = db.Column(db.Integer, db.ForeignKey('towns.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"Комментарий [{self.id}] {self.username}, {self.town}, text:{self.body}, date: {self.date_posted}"

# обновление базы
app.app_context().push()
db.create_all()

# декораторы
@manager.user_loader
def load_user(user_id):
    return People.query.get(user_id)


@app.route('/')
def preloader():
    return render_template('preloader.html')


@app.route('/home')
def index():
    return render_template('index.html', current_user=current_user)


@app.route('/towns/')
def towns():
    return render_template('towns.html', towns=Towns.query.all())


@app.route('/town/<int:id>/', methods=['POST', 'GET'])
def town(id):
    town = Towns.query.get_or_404(id)
    try:
        res = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={town.name.strip()}&units=metric&type=like&appid=9f4c1fe0ad890b08c2e63e3975469f42").json()     
        temperature = round(res['main']['temp'], 1)
    except:
        temperature = "Ошибка"
    if request.method == 'POST':
        if 'text' in request.form:
            body = request.form['text']
            if len(body) != 0:
                try:
                    new_comment = Comments(username=current_user.name if current_user.is_authenticated else 'Anonymous', town=id, body=body)
                    db.session.add(new_comment)
                    db.session.commit()
                except Exception as e:
                    return f'Что-то пошло не так: {str(e)}'
            else:
                flash('Комментарий не может быть пустым', 'warning')
    else:
        if current_user.is_authenticated:
            comments = Comments.query.filter_by(town=id).order_by(Comments.date_posted.desc()).all()
            historical_places = Historical_places.query.filter_by(town=id).all()
            monuments = Monuments.query.filter_by(town=id).all()
            return render_template('town_description.html', town=town, comments=comments, historical_places=historical_places, monuments=monuments, temperature=temperature)
        
        else: 
            flash('/registration')
            session.modified = True
            return redirect('/login')

    return redirect(url_for('town', id=id))


@app.route('/monuments/')
def monuments():
    monuments_db = Monuments.query.order_by(Monuments.rating.desc()).all()
    return render_template('monuments.html', monuments=monuments_db)


@app.route('/historical_places/')
def historical_places():
    historical_places = Historical_places.query.all()
    return render_template('historical_places.html' , historical_places=historical_places)


@app.route('/monuments/<int:id>')
def monuments_description(id):
    monument = Monuments.query.get(id)
    return render_template('monuments_description.html', monument=monument)


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        if 'register' in request.form:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']

            existing_user = People.query.filter_by(name=name).first()
            existing_email = People.query.filter_by(email=email).first()

            if existing_user:
                flash('Пользователь с таким именем уже существует!', 'warning')

            if existing_email:
                flash('Пользователь с таким email уже существует!', 'warning')

            if not existing_user and not existing_email:
                try:
                    hash_pwd = generate_password_hash(password)
                    new_user = People(name=name, email=email, password=hash_pwd)
                    db.session.add(new_user)
                    db.session.commit()
                    return redirect('/login')
                except Exception as e:
                    flash(f'Возникла ошибка при регистрации: {str(e)}', 'danger')

    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('emailtologin')
        password = request.form.get('passwordtologin')

        if email and password:
            user = People.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect('/home')
            else:
                flash('Неверная почта или пароль', 'warning')
        return render_template('authorization.html')
    else:
        return render_template('authorization.html')    


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect('/home')

@app.route('/delete_account')
@login_required
def delete_account():
    people = People.query.filter_by(id=current_user.id).first()
    try:
        db.session.delete(people)
        db.session.commit()
        return redirect('/home')
    except:
        return 'При удалении статьи возникла ошибка'
    

#  запуск
if __name__ == '__main__':
    app.run(debug=False)