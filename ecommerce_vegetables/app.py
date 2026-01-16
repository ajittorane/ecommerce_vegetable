from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, UserMixin, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os

# ------------------- APP CONFIG -------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------- MODELS -------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(150), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    customer_name = db.Column(db.String(150))
    address = db.Column(db.Text)
    mobile = db.Column(db.String(15))
    payment_method = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ------------------- HELPERS -------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required!", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

def user_only():
    return current_user.is_admin

# ------------------- PUBLIC -------------------
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product.html', product=product)

# ------------------- USER AUTH -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash("Username already exists", "danger")
            return redirect(url_for('register'))

        user = User(
            username=request.form['username'],
            password=generate_password_hash(request.form['password']),
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully!", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'], is_admin=False).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ------------------- CART -------------------
@app.route('/add_to_cart/<int:id>', methods=['POST'])
@login_required
def add_to_cart(id):
    if user_only():
        return redirect(url_for('index'))

    qty = int(request.form.get('quantity', 1))

    order = Order.query.filter_by(
        user_id=current_user.id,
        product_id=id
    ).first()

    if order:
        order.quantity += qty
    else:
        db.session.add(Order(
            user_id=current_user.id,
            product_id=id,
            quantity=qty
        ))

    db.session.commit()
    flash("Product added to cart", "success")
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    if user_only():
        return redirect(url_for('index'))

    orders = Order.query.filter_by(user_id=current_user.id).all()
    products = {p.id: p for p in Product.query.all()}
    return render_template('cart.html', orders=orders, products=products)

@app.route('/update_cart/<int:id>', methods=['POST'])
@login_required
def update_cart(id):
    order = Order.query.get_or_404(id)

    if order.user_id != current_user.id:
        return redirect(url_for('cart'))

    action = request.form.get('action')
    if action == 'increase':
        order.quantity += 1
    elif action == 'decrease' and order.quantity > 1:
        order.quantity -= 1

    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:id>', methods=['POST'])
@login_required
def remove_from_cart(id):
    order = Order.query.get_or_404(id)

    if order.user_id != current_user.id:
        return redirect(url_for('cart'))

    db.session.delete(order)
    db.session.commit()
    flash("Item removed", "success")
    return redirect(url_for('cart'))

# ------------------- CHECKOUT -------------------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if user_only():
        return redirect(url_for('index'))

    orders = Order.query.filter_by(user_id=current_user.id).all()
    if not orders:
        flash("Your cart is empty", "warning")
        return redirect(url_for('cart'))

    if request.method == 'POST':
        for o in orders:
            o.customer_name = request.form['name']
            o.address = request.form['address']
            o.mobile = request.form['mobile']
            o.payment_method = request.form['payment']

        db.session.commit()
        flash("Order placed successfully!", "success")
        return redirect(url_for('order_success'))

    products = {p.id: p for p in Product.query.all()}
    return render_template('checkout.html', orders=orders, products=products)

@app.route('/order-success')
@login_required
def order_success():
    return render_template('order_success.html')

# ------------------- ADMIN AUTH -------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin = User.query.filter_by(username=request.form['username'], is_admin=True).first()
        if admin and check_password_hash(admin.password, request.form['password']):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash("Invalid admin login", "danger")
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# ------------------- ADMIN DASHBOARD -------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    products = Product.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', products=products, users=users)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.all()
    products = {p.id: p for p in Product.query.all()}
    return render_template('admin_orders.html', orders=orders, products=products)

# ------------------- ADMIN CRUD -------------------
@app.route('/admin/add', methods=['GET', 'POST'])
@admin_required
def admin_add():
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            db.session.add(Product(
                name=request.form['name'],
                price=float(request.form['price']),
                image=filename
            ))
            db.session.commit()
            flash("Product added successfully!", "success")
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_add.html')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit(id):
    product = Product.query.get_or_404(id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])

        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image = filename

        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_edit.html', product=product)

@app.route('/admin/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# ------------------- INIT -------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            db.session.add(User(
                username='admin',
                password=generate_password_hash('admin123'),
                is_admin=True
            ))
            db.session.commit()

    app.run(debug=True)
