from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    import hashlib
    import binascii
    import hmac
    import os

    def generate_password_hash(password):
        salt = os.urandom(16)
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return binascii.hexlify(salt).decode('utf-8') + ':' + binascii.hexlify(hash_bytes).decode('utf-8')

    def check_password_hash(stored_hash, password):
        try:
            salt_hex, hash_hex = stored_hash.split(':', 1)
        except ValueError:
            return False
        salt = binascii.unhexlify(salt_hex)
        expected_hash = binascii.unhexlify(hash_hex)
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(computed_hash, expected_hash)

from models import db, User, Post

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-to-a-random-string'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'danger'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('home.html', posts=posts)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title   = request.form['title'].strip()
        content = request.form['content'].strip()
        if not title or not content:
            flash('Title and content cannot be empty.', 'danger')
            return render_template('create_post.html')
        new_post = Post(title=title, content=content, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        flash('Post published successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html')

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You can only edit your own posts.', 'danger')
        return redirect(url_for('home'))
    if request.method == 'POST':
        post.title   = request.form['title'].strip()
        post.content = request.form['content'].strip()
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('post', post_id=post.id))
    return render_template('edit_post.html', post=post)

@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You can only delete your own posts.', 'danger')
        return redirect(url_for('home'))
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted.', 'success')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        email    = request.form['email'].strip().lower()
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email    = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        flash('Incorrect email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)