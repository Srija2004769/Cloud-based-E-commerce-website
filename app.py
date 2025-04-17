from flask import Flask,render_template,url_for,request,flash,session,redirect
from flask_mysqldb import MySQL
import MySQLdb  # For handling DB exceptions
from werkzeug.security import generate_password_hash, check_password_hash

app=Flask(__name__)
app.secret_key='my_secret_key' # for session management 
#MySQL configuration
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']='Rootpassword@123'
app.config['MYSQL_DB']='bytebuy'
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
        return redirect(url_for('account'))
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
        if user and check_password_hash(user[3],password):
            session['username']=user[1]
            flash('Login Succeful',"Success")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials","danger ")
    return redirect(url_for('account'))

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
    for id,quantity in cart.items():
        cursor = mysql.connection.cursor()
        cursor.execute("Select id,product_name,price,image_url from products where id=%s",(id,))
        product = cursor.fetchone()
        cursor.close()
        if product:
            subtotal=float(product[2])*quantity
            total+=subtotal
            cart_items.append({
                'id':product[0],
                'product_name':product[1],
                'price':product[2],
                'image_url':product[3],
                'quantity':quantity,
                'subtotal':subtotal
            })
            tax=total*0.18
            grand_total=total+tax 
                                       
    return render_template('cart.html', cart_items=cart_items, total=total, tax=tax, grand_total=grand_total)

@app.route('/products')
def products():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.close()
    return render_template('products.html',products=products)

@app.route('/product/<int:id>')
def product_detail(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (id,))
    product = cur.fetchone()
    cur.close()
    if product:
        return render_template('productdetails.html', product=product)
    else:
        flash("Product not found", "danger")
        return redirect(url_for('products'))
    
@app.route('/add_to_cart/<int:id>', methods=['GET'])
def add_to_cart(id):
    quantity=int(request.args.get('quantity',1))
    if 'cart' not in session:
        session['cart']={}
    cart=session['cart']
    if str(id) in cart:
        cart[str(id)]+=quantity
    else:
        cart[str(id)]=quantity
    session['cart']=cart
    flash("Product added to cart", "success")
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

@app.route('/process_checkout',methods=['POST'])
def process_checkout():
    full_name = request.form['full_name']
    email = request.form['email']
    address = request.form['address']
    city = request.form['city']
    zip_code = request.form['zip_code']
    payment_method = request.form['payment_method']
    cart = session.get('cart', {})
    if not cart:
        flash("Cart is empty","danger")
        return redirect(url_for("products"))
    username = session.get('username') 
    #save the order details in the database
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO orders (username,full_name, email, address, city, zip_code, payment_method) VALUES (%s, %s, %s, %s, %s, %s, %s)", (username, full_name, email, address, city, zip_code, payment_method))
    cursor.connection.commit()
    #get the order id of the last inserted order
    order_id = cursor.lastrowid
    #save the order items in the database
    for product_id, quantity in cart.items():
        cursor.execute("Select price from products where id=%s",(product_id,))
        product=cursor.fetchone()
        if product:
            price=product[0]
            cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)", (order_id, product_id, quantity, price))
    cursor.connection.commit()
    
    cursor.close()
    #clear the cart after checkout
    session.pop('cart', None)
    flash("Order placed successfully", "success")   
    return redirect(url_for('order_summary', order_id=order_id))


@app.route('/order_history')
def order_history():
    username = session.get('username')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM orders WHERE username = %s", (username,))
    orders = cursor.fetchall()
    order_data = []
    for order in orders:
        # Fetch order items for each order
        cursor.execute("select order_items.quantity, order_items.price, products.product_name, products.image_url from order_items join products on order_items.product_id=products.id where order_items.order_id=%s",(order[0],))
        items=cursor.fetchall()
        order_data.append({
        'order':order,
        'items':items
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
    cursor.execute("""SELECT oi.quantity, oi.price, p.product_name, p.image_url
                      FROM order_items oi
                      JOIN products p ON oi.product_id = p.id
                      WHERE oi.order_id = %s""", (order_id,))
    items = cursor.fetchall()
    
    cursor.close()
    return render_template('order_summary.html', order=order, items=items)

@app.route("/wishlist")
def wishlist():
    username = session.get('username')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT p.id, p.product_name, p.price, p.image_url FROM wishlist w JOIN products p ON w.product_id = p.id WHERE w.username = %s", (username,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('wishlist.html', products=products)


if __name__=="__main__":
    app.run(debug=True)