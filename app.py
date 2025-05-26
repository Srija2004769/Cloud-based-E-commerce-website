from flask import Flask,render_template,url_for,request,flash,session,redirect
from flask_mysqldb import MySQL
import MySQLdb  # For handling DB exceptions
import MySQLdb.cursors  # For using DictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, redirect, render_template, url_for
 # Import the mysql object from your app

app=Flask(__name__)
app.secret_key='my_secret_key' # for session management 
#MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Rootpassword@123'
app.config['MYSQL_DB'] = 'bytebuy'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # Optional: for dict results
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/account',methods=['GET','POST'])
def account():
    return render_template('account.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash("Please login first", "warning")
    if not hasattr(mysql, 'connection') or mysql.connection is None:
        flash("Database connection failed. Please check your configuration.", "danger")
        return redirect(url_for('index'))
    cursor = mysql.connection.cursor()
    cursor = mysql.connection.cursor()
    username = session['username']
    #update profile
    if request.method == 'POST':
        username= request.form['username']
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        cursor.execute("UPDATE users SET full_name=%s, email=%s, phone=%s WHERE username=%s",
                       (full_name, email, phone, username))
        mysql.connection.commit()
        flash("Profile updated successfully!", "success")
    # Fetch user data from the database
    cursor.execute("SELECT username, full_name, email, phone FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    #fetch order items
    cursor.execute("select order_id, full_name, email, address, city, zip_code, payment_method from orders where username=%s",(username,))
    orders=cursor.fetchall()
    #fetch wish list items 
    cursor.execute("select p.id,p.product_name,p.price,p.image_url from wishlist w join products p on w.product_id=p.id where w.username=%s",(username,))
    wishlist=cursor.fetchall()
    cursor.close()
    return render_template('profile.html', user=user)


@app.route('/register',methods=['GET','POST'])
def register():
    # Fetch user data from the database
    username = request.form['username']
    email =request.form['email']
    password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("Insert into users (username,email,password) values (%s,%s,%s)",(username,email,password))
        mysql.connection.commit()
        cursor.close()
        flash('Account created successfully!')
    except MySQLdb.IntegrityError as e:
            if "Duplicate entry" in str(e):
                flash("This email is already registered.")
            else:
                flash("Something went wrong. Please try again.")
            return redirect(url_for('account'))
    return render_template('account.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username= request.form.get('username')
        email = request.form.get('email')
        password=request.form.get('password')
        cursor =mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND email = %s", (username, email))
        # Fetch the user data from the database
        user=cursor.fetchone()
        cursor.close()
        if user and check_password_hash(user['password'],password):
            session['username']=user['username']
            session['role']=user['role']  # Assuming 'role' is a column in your users table
            if user['role']=="admin":
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Login successful!","success")
                return redirect(url_for('index'))
        else:
            flash("Invalid credentials","danger ")
    return redirect(url_for('account'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("Access denied")
        return redirect(url_for('index'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) as total_orders FROM orders")
    order_count = cursor.fetchone()['total_orders']

    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT SUM(price * quantity) as revenue FROM order_items")
    revenue = cursor.fetchone()['revenue'] or 0

    cursor.close()
    return render_template('admin_dashboard.html', order_count=order_count, user_count=user_count, revenue=revenue)


@app.route('/logout')
def logout():
    session.pop("username",None)
    flash("Logged out", "info")
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    cart=session.get('cart',{})
    cart_items=[]
    total =0
    tax=0
    grand_total=0
    for id,quantity in cart.items():
        cursor = mysql.connection.cursor()
        cursor.execute("Select id,product_name,price,image_url from products where id=%s",(id,))
        product = cursor.fetchone()
        cursor.close()
        if product:
            subtotal=float(product['price'])*quantity
            total+=subtotal
            cart_items.append({
                'id':product['id'],
                'product_name':product['product_name'],
                'price':product['price'],
                'image_url':product['image_url'],
                'quantity':quantity,
                'subtotal':subtotal
            })
            tax=total*0.18
            grand_total=total+tax 
                                       
    return render_template('cart.html', cart_items=cart_items, total=total, tax=tax, grand_total=grand_total)

@app.route('/products')
def products():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    return render_template('products.html',products=products)

@app.route('/product/<int:id>')
def product_detail(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE id = %s", (id,))
    product = cursor.fetchone()
    cursor.close()
    if product:
        product = {
            'id': product['id'],
            'product_name': product['product_name'],
            'price': product['price'],
            'image_url': product['image_url'],
            'description': product['description']
        }
        return render_template('productdetails.html', product=product)
    else:
        flash("Product not found", "danger")
        return redirect(url_for('products'))
    
@app.route('/add_to_cart/<int:id>', methods=['GET'])
def add_to_cart(id):
    quantity=int(request.args.get('quantity',1))
    flash("Product added to cart", "success")
    if 'cart' not in session:
        session['cart']={}
    cart=session['cart']
    if str(id) in cart:
        cart[str(id)]+=quantity
    else:
        cart[str(id)]=quantity
    
    session['cart']=cart
    
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:id>', methods=['GET'])
def remove_from_cart(id):
    cart=session.get('cart',{})
    if str(id) in cart:
        del cart[str(id)]
        session['cart']=cart
        flash("Product removed from cart", "success")
    else:
        flash("Product not found in cart", "danger")
    return redirect(url_for('cart')) 

@app.route('/update_cart/<int:id>')
def update_cart(id):
    quantity=int(request.args.get('quantity',1))
    cart=session.get('cart',{})
    if quantity<1:
        quantity=1
    cart[str(id)]=quantity
    session['cart']=cart
    return {'success':True, 'message':'Cart updated successfully'}  

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    cart=session.get('cart',{})
    if not cart:
        flash("Your cart is empty", "warning")
        return redirect(url_for('products'))
    return render_template('checkout.html')

# @app.route('/process_checkout',methods=['POST'])
# def process_checkout():
#     full_name = request.form['full_name']
#     email = request.form['email']
#     address = request.form['address']
#     city = request.form['city']
#     zip_code = request.form['zip_code']
#     payment_method = request.form['payment_method']
#     cart = session.get('cart', {})
#     if not cart:
#         flash("Cart is empty","danger")
#         return redirect(url_for("products"))
#     username = session.get('username') 
#     #save the order details in the database
#     cursor = mysql.connection.cursor()
#     cursor.execute("INSERT INTO orders (username,full_name, email, address, city, zip_code, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)", (username, full_name, email, address, city, zip_code, payment_method))
#     cursor.connection.commit()
#     #get the order id of the last inserted order
#     order_id = cursor.lastrowid
#     #save the order items in the database
#     for product_id, quantity in cart.items():
#         cursor.execute("Select price from products where id=%s",(product_id,))
#         product=cursor.fetchone()
#         if product:
#             price=product['price']
#             cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)", (order_id, product_id, quantity, price))
#     cursor.connection.commit()
#     cursor.close()
#     flash("Order placed successfully", "success")   
#     #clear the cart after checkout
#     session.pop('cart', None)
    
#     return redirect(url_for('order_summary', order_id=order_id))

@app.route('/order_history')
def order_history():
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('account'))
    # Fetch order history for the logged-in user
    username = session.get('username')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM orders WHERE username = %s", (username,))
    orders = cursor.fetchall()
    order_data = []
    for order in orders:
        # Fetch order items for each order
        order_id = orders['order_id']
        cursor.execute("select order_items.quantity, order_items.price, products.product_name, products.image_url from order_items join products on order_items.product_id=products.id where order_items.order_id=%s",(orders['order_id'],))
        items=cursor.fetchall()
        order_data.append({
            'orders': {
                'order_id': orders['order_id'],
                'full_name': order['full_name'],
                'email': order['email'],
                'address': order['address'],
                'city': order['city'],
                'zip_code': order['zip_code'],
                'payment_method': order['payment_method'],
                'username': order['username'],
                'status': order['status']
            },
            'items': items
        })
    cursor.close()
    return render_template('order_history.html', orders=order_data)

@app.route('/order_summary/<int:order_id>')
def order_summary(order_id):
    cursor = mysql.connection.cursor()
    # Fetch order details
    cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()
    # Fetch items in that order
    cursor.execute("""SELECT  order_items.quantity,  order_items.price, products.product_name, products.image_url
                      FROM order_items 
                      JOIN products  ON  order_items.product_id = products.id
                      WHERE  order_items.order_id = %s""", (order_id,))
    items = cursor.fetchall()
    order_items = []
    for item in items:
        order_items.append({
            'quantity': item['quantity'],
            'price': item['price'],
            'product_name': item['product_name'],
            'image_url': item['image_url']
        })
    if not order:
        flash("Order not found", "danger")
        return redirect(url_for('order_history'))
    if not order_items:
        flash("No items found in this order", "warning")
        return redirect(url_for('order_history'))
    
    cursor.close()
    return render_template('order_summary.html', order=order, order_items=order_items , products=products)

@app.route("/wishlist")
def wishlist():
    username = session.get('username')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT p.id, p.product_name, p.price, p.image_url FROM wishlist w JOIN products p ON w.product_id = p.id WHERE w.username = %s", (username,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('wishlist.html', products=products)
    

@app.route('/process_checkout', methods=['POST'])
def process_checkout():
    full_name = request.form['full_name']
    email = request.form['email']
    address = request.form['address']
    city = request.form['city']
    zip_code = request.form['zip_code']
    payment_method = request.form['payment_method']
    status = "Pending"

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO orders (full_name, email, address, city, zip_code, payment_method, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (full_name, email, address, city, zip_code, payment_method, status))

    mysql.connection.commit()
    order_id = cur.lastrowid
    cur.close()

    if payment_method == 'cod':
        return render_template('order_success.html', order_id=order_id)
    elif payment_method == 'card':
        return redirect(url_for('mock_card_payment', order_id=order_id))
    elif payment_method == 'paypal':
        return redirect(url_for('mock_paypal_payment', order_id=order_id))
    elif payment_method == 'bank_transfer':
        return redirect(url_for('mock_bank_transfer', order_id=order_id))
    else:
        return "Invalid payment method", 400
    
@app.route('/mock_paypal_payment/<int:order_id>')
def mock_paypal_payment(order_id):
    return render_template('mock_paypal.html', order_id=order_id)

@app.route('/confirm_paypal_payment/<int:order_id>', methods=['POST'])
def confirm_paypal_payment(order_id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE order_id=%s", ("Paid - PayPal", order_id))
    mysql.connection.commit()
    cursor.close()
    flash("Payment successful via PayPal!", "success")
    return redirect(url_for('order_summary', order_id=order_id))

@app.route('/admin/manage_orders')
def manage_orders():
    # Fetch all orders from the database
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY order_id DESC")
    orders = cursor.fetchall()
    cursor.close()
    return render_template('index.html', orders=orders)

@app.route('/admin/manage_products')
def manage_products():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    return render_template('index.html', products=products)

@app.route('/admin/manage_users')
def manage_users():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    return render_template('index.html')





if __name__=="__main__":
    app.run(debug=True)