from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import os
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = os.environ.get(
    "PHARMAUZ_SECRET_KEY",
    "pharmauz_secret_key_2026"
)

DATABASE = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Dorilar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active_ingredient TEXT,
            manufacturer TEXT,
            dosage TEXT,
            form TEXT,
            prescription_required INTEGER DEFAULT 0
        )
    """)

    # Dorixonalar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pharmacies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        city TEXT,
        address TEXT,
        phone TEXT,
        distance REAL,
        latitude REAL,
        longitude REAL,
        username TEXT,
        password TEXT,
        status TEXT DEFAULT 'pending'
    )
""")
    try:
        cursor.execute("""
            ALTER TABLE pharmacies
            ADD COLUMN status TEXT DEFAULT 'pending'
        """)
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("""
        ALTER TABLE pharmacies
        ADD COLUMN latitude REAL
    """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
        ALTER TABLE pharmacies
        ADD COLUMN longitude REAL
    """)
    except sqlite3.OperationalError:
        pass

    # Dorixona ombori
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pharmacy_id INTEGER,
            medicine_id INTEGER,
            price REAL,
            quantity INTEGER,
            updated_at TEXT,
            FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id),
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        )
    """)

    # Demo dorilar
    cursor.execute("SELECT COUNT(*) FROM medicines")
    if cursor.fetchone()[0] == 0:

        cursor.execute("""
            INSERT INTO medicines
            (name, active_ingredient, manufacturer, dosage, form, prescription_required)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Paratsetamol 500 mg",
            "Paracetamol",
            "Demo Pharma",
            "500 mg",
            "Tabletka",
            0
        ))

        cursor.execute("""
            INSERT INTO medicines
            (name, active_ingredient, manufacturer, dosage, form, prescription_required)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Amoksitsillin 500 mg",
            "Amoxicillin",
            "Demo Pharma",
            "500 mg",
            "Kapsula",
            1
        ))

    # Demo dorixonalar
    cursor.execute("SELECT COUNT(*) FROM pharmacies")
    if cursor.fetchone()[0] == 0:

        cursor.execute("""
    INSERT INTO pharmacies
    (name, city, address, phone, distance, username, password)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    "Salomat Pharm",
    "Nukus shahri",
    "Markaziy ko‘cha",
    "+998 90 000 00 01",
    0.7,
    "salomat",
    "12345"
))

        cursor.execute("""
    INSERT INTO pharmacies
    (name, city, address, phone, distance, username, password)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    "Dori-Darmon",
    "Nukus shahri",
    "Berdaq ko‘chasi",
    "+998 90 000 00 02",
    1.2,
    "doridarmon",
    "12345"
))

    # Demo ombor ma'lumotlari
    cursor.execute("SELECT COUNT(*) FROM inventory")

    if cursor.fetchone()[0] == 0:

        cursor.execute("""
            INSERT INTO inventory
            (pharmacy_id, medicine_id, price, quantity, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            1,
            1,
            8000,
            24,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        cursor.execute("""
            INSERT INTO inventory
            (pharmacy_id, medicine_id, price, quantity, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            2,
            1,
            7800,
            11,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        cursor.execute("""
            INSERT INTO inventory
            (pharmacy_id, medicine_id, price, quantity, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            1,
            2,
            25000,
            8,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM pharmacies
            WHERE username = ?
        """, (username,))

        pharmacy = cursor.fetchone()

        conn.close()

        password_ok = False

        if pharmacy:
            stored_password = pharmacy["password"]

            if stored_password.startswith(("scrypt:", "pbkdf2:")):
                password_ok = check_password_hash(stored_password, password)

            else:
                password_ok = (stored_password == password)

                if password_ok:
                    new_hash = generate_password_hash(password)

                    conn = get_db()

                    conn.execute("""
                        UPDATE pharmacies
                        SET password = ?
                        WHERE id = ?
                    """, (
                        new_hash,
                        pharmacy["id"]
                    ))

                    conn.commit()
                    conn.close()

            if password_ok:
                if pharmacy["status"] == "pending":
                    return render_template(
                        "login.html",
                    error="Akkauntingiz hali admin tomonidan tasdiqlanmagan."
                    )

                if pharmacy["status"] == "blocked":
                    return render_template(
                        "login.html",
                    error="Akkauntingiz bloklangan. Admin bilan bog‘laning."
    )
                session["pharmacy_id"] = pharmacy["id"]
                session["pharmacy_name"] = pharmacy["name"]

                return redirect("/dashboard")

        else:

            return render_template(
                "login.html",
                error="Login yoki parol noto‘g‘ri!"
            )

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "pharmacy_id" not in session:
        return redirect("/login")

    pharmacy_id = session["pharmacy_id"]

    conn = get_db()

    pharmacy = conn.execute("""
        SELECT *
        FROM pharmacies
        WHERE id = ?
    """, (pharmacy_id,)).fetchone()

    products = conn.execute("""
        SELECT
            inventory.id AS inventory_id,
            medicines.name,
            medicines.dosage,
            medicines.form,
            inventory.price,
            inventory.quantity,
            inventory.updated_at
        FROM inventory
        JOIN medicines
            ON medicines.id = inventory.medicine_id
        WHERE inventory.pharmacy_id = ?
    """, (pharmacy_id,)).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        pharmacy=pharmacy,
        products=products
    )
@app.route("/inventory/update/<int:inventory_id>", methods=["POST"])
def update_inventory(inventory_id):

    if "pharmacy_id" not in session:
        return redirect("/login")

    price = request.form.get("price")
    quantity = request.form.get("quantity")
    
    price = float(price)
    quantity = int(quantity)

    pharmacy_id = session["pharmacy_id"]

    conn = get_db()

    conn.execute("""
    UPDATE inventory
    SET price = ?,
        quantity = ?,
        updated_at = ?
    WHERE id = ? AND pharmacy_id = ?
""", (
    price,
    quantity,
    datetime.now().strftime("%Y-%m-%d %H:%M"),
    inventory_id,
    pharmacy_id
))
    conn.commit()
    conn.close()

    return redirect("/dashboard")
@app.route("/inventory/delete/<int:inventory_id>", methods=["POST"])
def delete_inventory(inventory_id):

    if "pharmacy_id" not in session:
        return redirect("/login")

    pharmacy_id = session["pharmacy_id"]

    conn = get_db()
    conn.execute("""
    DELETE FROM inventory
    WHERE id = ? AND pharmacy_id = ?
""", (
    inventory_id,
    pharmacy_id
))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/inventory/add", methods=["GET", "POST"])
def add_inventory():

    if "pharmacy_id" not in session:
        return redirect("/login")

    conn = get_db()
    pharmacy_id = session["pharmacy_id"]

    if request.method == "POST":

        medicine_id = request.form.get("medicine_id")
        price = request.form.get("price")
        quantity = request.form.get("quantity")

        medicine_id = int(medicine_id)
        price = float(price)
        quantity = int(quantity)

        existing = conn.execute("""
            SELECT id
            FROM inventory
            WHERE pharmacy_id = ?
              AND medicine_id = ?
        """, (
            pharmacy_id,
            medicine_id
        )).fetchone()

        if existing:

            conn.execute("""
                UPDATE inventory
                SET price = ?,
                    quantity = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                price,
                quantity,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                existing["id"]
            ))

        else:

            conn.execute("""
                INSERT INTO inventory
                (
                    pharmacy_id,
                    medicine_id,
                    price,
                    quantity,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                pharmacy_id,
                medicine_id,
                price,
                quantity,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

        conn.commit()
        conn.close()

        return redirect("/dashboard")


    medicines = conn.execute("""
        SELECT id, name
        FROM medicines
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "add_inventory.html",
        medicines=medicines
    )
@app.route("/profile")
def profile():

    if "pharmacy_id" not in session:
        return redirect("/login")

    pharmacy_id = session["pharmacy_id"]

    conn = get_db()

    pharmacy = conn.execute("""
        SELECT *
        FROM pharmacies
        WHERE id = ?
    """, (pharmacy_id,)).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        pharmacy=pharmacy
    )
@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():

    if "pharmacy_id" not in session:
        return redirect("/login")
    if request.method == "POST":

        name = request.form.get("name")
        city = request.form.get("city")
        address = request.form.get("address")
        phone = request.form.get("phone")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        pharmacy_id = session["pharmacy_id"]

        conn = get_db()

        conn.execute("""
            UPDATE pharmacies
            SET name = ?,
                city = ?,
                address = ?,
                phone = ?,
                latitude = ?,
                longitude = ?
            WHERE id = ?
        """, (
            name,
            city,
            address,
            phone,
            latitude,
            longitude,
            pharmacy_id
        ))

        conn.commit()
        conn.close()

        session["pharmacy_name"] = name

        return redirect("/profile")
    pharmacy_id = session["pharmacy_id"]

    conn = get_db()

    pharmacy = conn.execute("""
        SELECT *
        FROM pharmacies
        WHERE id = ?
    """, (pharmacy_id,)).fetchone()

    conn.close()

    return render_template(
        "edit_profile.html",
        pharmacy=pharmacy
    )

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db()

    pharmacies = conn.execute("""
        SELECT
            id,
            name,
            city,
            address,
            phone,
            username,
            status
        FROM pharmacies
        ORDER BY id DESC
    """).fetchall()

    medicines = conn.execute("""
        SELECT
            id,
            name,
            active_ingredient,
            manufacturer,
            dosage,
            form
        FROM medicines
        ORDER BY id DESC
    """).fetchall()

    inventory_count = conn.execute("""
        SELECT COUNT(*)
        FROM inventory
    """).fetchone()[0]

    pharmacy_count = conn.execute("""
        SELECT COUNT(*)
        FROM pharmacies
    """).fetchone()[0]

    medicine_count = conn.execute("""
        SELECT COUNT(*)
        FROM medicines
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        pharmacies=pharmacies,
        medicines=medicines,
        inventory_count=inventory_count,
        pharmacy_count=pharmacy_count,
        medicine_count=medicine_count
    )

@app.route("/admin/medicine/add", methods=["GET", "POST"])
def admin_add_medicine():

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    if request.method == "POST":

        name = request.form.get("name")
        active_ingredient = request.form.get("active_ingredient")
        manufacturer = request.form.get("manufacturer")
        dosage = request.form.get("dosage")
        form = request.form.get("form")
        prescription_required = request.form.get("prescription_required")

        if prescription_required == "1":
            prescription_required = 1
        else:
            prescription_required = 0

        conn = get_db()

        existing = conn.execute("""
            SELECT id
            FROM medicines
            WHERE name = ?
              AND dosage = ?
              AND form = ?
        """, (
            name,
            dosage,
            form
        )).fetchone()

        if existing:

            conn.close()

            return render_template(
                "admin_add_medicine.html",
                error="Bu dori katalogda allaqachon mavjud!"
            )

        conn.execute("""
            INSERT INTO medicines
            (
                name,
                active_ingredient,
                manufacturer,
                dosage,
                form,
                prescription_required
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            active_ingredient,
            manufacturer,
            dosage,
            form,
            prescription_required
        ))

        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("admin_add_medicine.html")

@app.route("/admin/medicine/edit/<int:medicine_id>", methods=["GET", "POST"])
def admin_edit_medicine(medicine_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db()

    medicine = conn.execute("""
        SELECT *
        FROM medicines
        WHERE id = ?
    """, (medicine_id,)).fetchone()

    if not medicine:
        conn.close()
        return redirect("/admin")

    if request.method == "POST":

        name = request.form.get("name")
        active_ingredient = request.form.get("active_ingredient")
        manufacturer = request.form.get("manufacturer")
        dosage = request.form.get("dosage")
        form = request.form.get("form")
        prescription_required = request.form.get("prescription_required")

        prescription_required = 1 if prescription_required == "1" else 0

        conn.execute("""
            UPDATE medicines
            SET name = ?,
                active_ingredient = ?,
                manufacturer = ?,
                dosage = ?,
                form = ?,
                prescription_required = ?
            WHERE id = ?
        """, (
            name,
            active_ingredient,
            manufacturer,
            dosage,
            form,
            prescription_required,
            medicine_id
        ))

        conn.commit()
        conn.close()

        return redirect("/admin")

    conn.close()

    return render_template(
        "admin_edit_medicine.html",
        medicine=medicine
    )

@app.route("/admin/medicine/delete/<int:medicine_id>", methods=["POST"])
def admin_delete_medicine(medicine_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db()

    # Avval shu doriga bog‘langan ombor yozuvlarini o‘chiramiz
    conn.execute("""
        DELETE FROM inventory
        WHERE medicine_id = ?
    """, (medicine_id,))

    # Keyin dorining o‘zini o‘chiramiz
    conn.execute("""
        DELETE FROM medicines
        WHERE id = ?
    """, (medicine_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/api/medicines")
def api_medicines():

    q = request.args.get("q", "").strip()

    conn = get_db()

    medicines = conn.execute("""
        SELECT id, name, dosage
        FROM medicines
        WHERE name LIKE ?
        ORDER BY name
        LIMIT 10
    """, (q + "%",)).fetchall()

    conn.close()

    result = []

    for medicine in medicines:
        result.append({
            "id": medicine["id"],
            "name": medicine["name"],
            "dosage": medicine["dosage"]
        })

    return jsonify(result)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    admin_username = os.environ.get("PHARMAUZ_ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("PHARMAUZ_ADMIN_PASSWORD", "admin123")

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == admin_username and password == admin_password:
            session["admin_logged_in"] = True
            return redirect("/admin")

        else:
            return render_template(
                "admin_login.html",
                error="Admin login yoki parol noto‘g‘ri!"
            )

    return render_template("admin_login.html")

@app.route("/admin/pharmacy/approve/<int:pharmacy_id>", methods=["POST"])
def approve_pharmacy(pharmacy_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db()

    conn.execute("""
        UPDATE pharmacies
        SET status = 'approved'
        WHERE id = ?
    """, (pharmacy_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/admin/pharmacy/block/<int:pharmacy_id>", methods=["POST"])
def block_pharmacy(pharmacy_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db()

    conn.execute("""
        UPDATE pharmacies
        SET status = 'blocked'
        WHERE id = ?
    """, (pharmacy_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/admin/pharmacy/unblock/<int:pharmacy_id>", methods=["POST"])
def unblock_pharmacy(pharmacy_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db()

    conn.execute("""
        UPDATE pharmacies
        SET status = 'approved'
        WHERE id = ?
    """, (pharmacy_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect("/admin/login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        city = request.form.get("city")
        address = request.form.get("address")
        phone = request.form.get("phone")
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)
        conn = get_db()

        existing_user = conn.execute("""
            SELECT id
            FROM pharmacies
            WHERE username = ?
        """, (username,)).fetchone()
        if existing_user:
            conn.close()
            return render_template(
                "register.html",
                error="Bu login allaqachon band!"
            )

        conn.execute("""
            INSERT INTO pharmacies
            (name, city, address, phone, distance, latitude, longitude, username, password, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
                name,
                city,
                address,
                phone,
                0,
                None,
                None,
                username,
                hashed_password,
                "pending"
        ))

        conn.commit()
        conn.close()

        return redirect("/login")
    return render_template("register.html")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    conn = get_db()

    medicines = conn.execute("""
        SELECT *
        FROM medicines
        WHERE name LIKE ?
           OR active_ingredient LIKE ?
    """, (
        f"%{query}%",
        f"%{query}%"
    )).fetchall()

    conn.close()

    return render_template(
        "search.html",
        medicines=medicines,
        query=query
    )


@app.route("/medicine/<int:medicine_id>")
def medicine(medicine_id):

    conn = get_db()

    medicine = conn.execute("""
        SELECT *
        FROM medicines
        WHERE id = ?
    """, (medicine_id,)).fetchone()

    pharmacies = conn.execute("""
        SELECT
            pharmacies.id,
            pharmacies.name,
            pharmacies.address,
            pharmacies.phone,
            pharmacies.distance,
            inventory.price,
            inventory.quantity,
            inventory.updated_at
        FROM inventory
        JOIN pharmacies
            ON pharmacies.id = inventory.pharmacy_id
        WHERE inventory.medicine_id = ?
        ORDER BY pharmacies.distance
    """, (medicine_id,)).fetchall()

    conn.close()

    return render_template(
        "medicine.html",
        medicine=medicine,
        pharmacies=pharmacies
    )


@app.route("/pharmacy/<int:pharmacy_id>")
def pharmacy(pharmacy_id):

    conn = get_db()

    pharmacy = conn.execute("""
        SELECT *
        FROM pharmacies
        WHERE id = ?
    """, (pharmacy_id,)).fetchone()

    products = conn.execute("""
        SELECT
            medicines.name,
            medicines.dosage,
            medicines.form,
            inventory.price,
            inventory.quantity,
            inventory.updated_at
        FROM inventory
        JOIN medicines
            ON medicines.id = inventory.medicine_id
        WHERE inventory.pharmacy_id = ?
    """, (pharmacy_id,)).fetchall()

    conn.close()

    return render_template(
        "pharmacy.html",
        pharmacy=pharmacy,
        products=products
    )


init_db()

if __name__ == "__main__":

    print("PharmaUZ ishga tushmoqda...")
    print("Brauzerda http://127.0.0.1:5000 manzilini oching.")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )