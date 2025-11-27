from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_sqlalchemy import SQLAlchemy
import os

auth_blueprint = Blueprint('auth', __name__, template_folder='templates')
db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

def init_db(app):
    # configure a local sqlite DB file for admin/password management
    db_path = os.environ.get('LOCAL_DB_PATH', 'sqlite:///app_local.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password='12345')
            db.session.add(admin)
            db.session.commit()

@auth_blueprint.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Admin.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user'] = user.username
            flash('Login berhasil','success')
            return redirect(url_for('index'))
        flash('Username atau password salah','danger')
    return render_template('login.html')

@auth_blueprint.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logout berhasil','success')
    return redirect(url_for('auth.login'))

@auth_blueprint.route('/reset', methods=['GET','POST'])
def reset():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        old = request.form.get('old_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        user = Admin.query.filter_by(username=session.get('user')).first()
        if not user or user.password != old:
            flash('Password lama tidak cocok','danger'); return redirect(url_for('auth.reset'))
        if new != confirm:
            flash('Konfirmasi tidak cocok','danger'); return redirect(url_for('auth.reset'))
        user.password = new
        db.session.commit()
        flash('Password berhasil diganti','success')
        return redirect(url_for('index'))
    return render_template('reset_password.html')
