import sqlite3
from datetime import datetime, date, timedelta
import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import os
import socket
import random
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import qrcode
import io

DB_PATH = "inventoryproject.db"

PRIMARY = "#4361ee"
SECONDARY = "#3a0ca3"
ACCENT = "#7209b7"
SUCCESS = "#4cc9f0"
WARNING = "#f72585"
BG_LIGHT = "#f8f9fa"
CARD_BG = "#ffffff"

def get_local_ip() -> str:
    """Get the current system's IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.1.1"


def generate_barcode_image(data: str) -> Image.Image:
    """
    Generate a high‑resolution Code 128 barcode encoding any ASCII string.
    Returns a PIL.Image (RGB) with no human‑readable text.
    """
    try:
        cls = barcode.get_barcode_class("code128")
        bc = cls(data, writer=ImageWriter())

        # Optimized settings for scannability
        options = {
            "module_width": 0.35,  # Slightly thicker bars
            "module_height": 25.0,  # Taller bars
            "quiet_zone": 10.0,  # Larger quiet zone (critical for scanning)
            "dpi": 300,  # Higher resolution
            "font_size": 0,
            "text_distance": 0,
            "write_text": False,
            "background": "white",  # Ensure white background
            "foreground": "black",  # Ensure black bars
        }

        buf = BytesIO()
        bc.write(buf, options)
        buf.seek(0)
        return Image.open(buf).convert("RGB")
    except Exception as e:
        print(f"Barcode generation error: {e}")
        return Image.new('RGB', (300, 100), color='white')  # Larger placeholder

    # In show_product_details function:
    # Barcode section - generate from barcode2
    barcode_frame = ctk.CTkFrame(code_frame, fg_color="transparent", width=300, height=100)  # Increase frame size
    barcode_frame.grid(row=0, column=2, padx=15, pady=15)

    try:
        # Generate barcode image from full URL
        barcode_img = generate_barcode_image(full_url)  # Use the full URL

        # Maintain original size - DO NOT RESIZE
        barcode_photo = ImageTk.PhotoImage(barcode_img)
        barcode_label = tk.Label(barcode_frame, image=barcode_photo, bg="#f8f9fa")
        barcode_label.image = barcode_photo
        barcode_label.pack()

    except Exception as e:
        print(f"Error creating barcode: {e}")
        ctk.CTkLabel(
            barcode_frame,
            text="Barcode Error",
            font=("Arial", 12),
            text_color="#ff0000"
        ).pack()


def update_missing_barcodes():
    """Update all products with missing barcodes in the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Find all products with missing barcodes
        cur.execute("SELECT productID FROM product WHERE barcode2 IS NULL OR barcode2 = ''")
        products = cur.fetchall()

        # Update each product individually
        for product in products:
            product_id = product[0]
            new_barcode = ''.join(random.choices('0123456789', k=12))
            cur.execute("UPDATE product SET barcode2=? WHERE productID=?", (new_barcode, product_id))
            conn.commit()
            print(f"Generated new barcode: {new_barcode} for product ID: {product_id}")

        return len(products)
    except sqlite3.Error as e:
        print(f"Database error updating barcodes: {e}")
        return 0
    finally:
        conn.close()
update_missing_barcodes()

def show_product_details(product_id):
    """Show detailed product information in a popup window"""
    # First ensure all missing barcodes are updated
    updated_count = update_missing_barcodes()
    if updated_count > 0:
        print(f"Updated {updated_count} missing barcodes")

    # Fetch product details
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM product WHERE productID=?", (product_id,))
    product = cur.fetchone()
    conn.close()

    if not product:
        print(f"No product found with ID: {product_id}")
        return

    # Unpack product data (barcode2 is guaranteed to exist after update)
    (pid, name, category, qr_path, price, stock, imagepath,status,date,barcode_code) = product

    # Get current IP address
    ip_address = get_local_ip()

    # Create full URL from the numeric code
    full_url = f"http://{ip_address}:5000/scan?code={barcode_code}"

    # Create popup window
    detail_win = ctk.CTkToplevel()
    detail_win.title(f"Product Details - {name}")
    detail_win.geometry("800x750")  # Increased width for better layout
    detail_win.resizable(False, False)
    detail_win.attributes("-topmost", True)

    # Main frame
    main_frame = ctk.CTkFrame(detail_win, fg_color="#ffffff")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Header section
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=15)

    ctk.CTkLabel(
        header_frame,
        text=name,
        font=("Segoe UI", 24, "bold"),
        text_color="#2d3e50",
        anchor="w"
    ).pack(fill="x")

    ctk.CTkLabel(
        header_frame,
        text=f"ID: {pid} | Category: {category}",
        font=("Segoe UI", 16),
        text_color="#666666",
        anchor="w"
    ).pack(fill="x", pady=(5, 0))

    # Image and code section
    code_frame = ctk.CTkFrame(main_frame, fg_color="#f8f9fa", corner_radius=10)
    code_frame.pack(fill="x", padx=20, pady=10)

    # Configure grid columns
    code_frame.grid_columnconfigure(0, weight=1)
    code_frame.grid_columnconfigure(1, weight=1)
    code_frame.grid_columnconfigure(2, weight=1)

    # Product image - fixed size
    img_frame = ctk.CTkFrame(code_frame, fg_color="transparent", width=160, height=160)
    img_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    img_frame.grid_propagate(False)  # Prevent frame from resizing to contents

    try:
        if imagepath and os.path.exists(imagepath):
            img = Image.open(imagepath)
            img = img.resize((150, 150), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(img_frame, image=photo, bg="#f8f9fa")
            img_label.image = photo
            img_label.place(relx=0.5, rely=0.5, anchor="center")  # Center the image
        else:
            raise Exception("Image not found")
    except:
        ctk.CTkLabel(
            img_frame,
            text="🖼️ No Image",
            font=("Arial", 14),
            text_color="#cccccc",
        ).place(relx=0.5, rely=0.5, anchor="center")

    # QR code - fixed size

    qr_frame = ctk.CTkFrame(code_frame, fg_color="transparent", width=160, height=160)
    qr_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    qr_frame.grid_propagate(False)

    def load_qr_image(qr_path):
        # 1) From file path
        if isinstance(qr_path, str) and os.path.exists(qr_path) and qr_path != "-":
            try:
                return Image.open(qr_path).resize((150, 150), Image.LANCZOS)
            except:
                pass

        # 2) From BLOB bytes
        if qr_path:
            try:
                if isinstance(qr_path, memoryview):
                    raw = qr_path.tobytes()
                elif isinstance(qr_path, bytearray):
                    raw = bytes(qr_path)
                elif isinstance(qr_path, bytes):
                    raw = qr_path
                else:
                    raise TypeError(f"Unexpected QR blob type: {type(qr_path)}")

                img = Image.open(io.BytesIO(raw))
                return img.resize((150, 150), Image.LANCZOS)
            except:
                pass

        # 3) Fallback: generate a simple QR
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data("No QR available")
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white") \
            .convert("RGB") \
            .resize((150, 150), Image.LANCZOS)

    # Load PIL image
    pil_img = load_qr_image(qr_path)

    # Wrap in CTkImage via your ctk alias
    ctk_img = ctk.CTkImage(light_image=pil_img, size=(150, 150))
    qr_label = ctk.CTkLabel(qr_frame, image=ctk_img, text="")
    qr_label.place(relx=0.5, rely=0.5, anchor="center")

    # Barcode section - fixed height, flexible width
    barcode_frame = ctk.CTkFrame(code_frame, fg_color="transparent", height=120)
    barcode_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
    barcode_frame.grid_propagate(False)  # Prevent frame from resizing to contents

    # Create barcode image from full URL
    try:
        # Generate barcode image from full URL
        barcode_img = generate_barcode_image(full_url)

        # Resize barcode to appropriate dimensions (width proportional to height)
        original_width, original_height = barcode_img.size
        new_height = 80
        new_width = int((original_width / original_height) * new_height)
        barcode_img = barcode_img.resize((new_width, new_height), Image.LANCZOS)

        # Convert to PhotoImage
        barcode_photo = ImageTk.PhotoImage(barcode_img)

        # Create container for centering
        container_frame = ctk.CTkFrame(barcode_frame, fg_color="transparent")
        container_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Display barcode
        # Display barcode at original size
        barcode_label = tk.Label(
            container_frame,
            image=barcode_photo,
            bg="#f8f9fa",
            cursor="hand2"  # Show hand cursor to indicate clickable
        )
        barcode_label.image = barcode_photo
        barcode_label.pack()

        # Function to show enlarged barcode
        def show_enlarged_barcode(event):
            """Show enlarged barcode in a popup window"""
            # Create popup window
            barcode_popup = ctk.CTkToplevel()
            barcode_popup.title("Barcode")
            barcode_popup.geometry("1195x200")
            barcode_popup.resizable(False, False)
            barcode_popup.attributes("-topmost", True)
            barcode_popup.lift()  # Bring to front
            detail_win.attributes("-topmost", False)  # Lower product details

            # Generate new barcode at larger size
            try:
                # Generate a new barcode with the same data but optimized for large size
                options = {
                    "module_width": 1.0,  # Wider bars for better scanning
                    "module_height": 40.0,  # Taller bars
                    "quiet_zone": 15.0,  # Larger quiet zone
                    "dpi": 300,
                    "font_size": 0,
                    "text_distance": 0,
                    "write_text": False,
                    "background": "white",
                    "foreground": "black",
                }

                # Generate barcode using the same method
                cls = barcode.get_barcode_class("code128")
                bc = cls(full_url, writer=ImageWriter())
                buf = BytesIO()
                bc.write(buf, options)
                buf.seek(0)
                large_barcode_img = Image.open(buf).convert("RGB")

                # Resize to exact dimensions
                large_barcode_img = large_barcode_img.resize((1195, 200), Image.LANCZOS)
                large_barcode_photo = ImageTk.PhotoImage(large_barcode_img)

                # Display in popup
                barcode_label_popup = tk.Label(
                    barcode_popup,
                    image=large_barcode_photo,
                    bg="white"
                )
                barcode_label_popup.image = large_barcode_photo
                barcode_label_popup.pack(fill="both", expand=True)

            except Exception as e:
                print(f"Error creating enlarged barcode: {e}")
                ctk.CTkLabel(
                    barcode_popup,
                    text="Barcode Generation Error",
                    text_color="red"
                ).pack()

            # Center the popup
            barcode_popup.update_idletasks()
            width = barcode_popup.winfo_width()
            height = barcode_popup.winfo_height()
            x = (barcode_popup.winfo_screenwidth() // 2) - (width // 2)
            y = (barcode_popup.winfo_screenheight() // 2) - (height // 2)
            barcode_popup.geometry(f'+{x}+{y}')

        # Bind click event to barcode label
        barcode_label.bind("<Button-1>", show_enlarged_barcode)

    except Exception as e:
        print(f"Error creating barcode: {e}")
        ctk.CTkLabel(
            barcode_frame,
            text="Barcode Error",
            font=("Arial", 12),
            text_color="#ff0000"
        ).place(relx=0.5, rely=0.5, anchor="center")
        # Display the numeric code below the barcode
        ctk.CTkLabel(
            container_frame,
            text=barcode_code,
            font=("Courier New", 14),
            text_color="#000000",
        ).pack(pady=(5, 0), anchor="center")

    except Exception as e:
        print(f"Error creating barcode: {e}")
        ctk.CTkLabel(
            barcode_frame,
            text="Barcode Error",
            font=("Arial", 12),
            text_color="#ff0000"
        ).place(relx=0.5, rely=0.5, anchor="center")

    # Details section
    details_frame = ctk.CTkFrame(main_frame, fg_color="#f8f9fa", corner_radius=10)
    details_frame.pack(fill="x", padx=20, pady=(0, 15))

    # Create a grid for details - show numeric code, not URL
    details = [
        ("Product ID", pid),
        ("Product Name", name),
        ("Category", category),
        ("Price", f"RM{price:.2f}"),
        ("Stock Quantity", stock),
        ("Barcode", barcode_code),
        ("QR Code Path", qr_path if qr_path else "Not available"),
        ("Image Path", imagepath if imagepath else "Not available")
    ]

    for i, (label, value) in enumerate(details):
        # Label
        ctk.CTkLabel(
            details_frame,
            text=label + ":",
            font=("Segoe UI", 14, "bold"),
            text_color="#444",
            anchor="w",
            width=150
        ).grid(row=i, column=0, padx=(20, 5), pady=5, sticky="w")

        # Value
        ctk.CTkLabel(
            details_frame,
            text=str(value),
            font=("Segoe UI", 14),
            text_color="#333",
            anchor="w"
        ).grid(row=i, column=1, padx=5, pady=5, sticky="w")

    # Close button
    btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkButton(
        btn_frame,
        text="Close",
        font=("Segoe UI", 14, "bold"),
        fg_color="#2d3e50",
        hover_color="#3c4f63",
        command=detail_win.destroy
    ).pack(side="right")

    # Center the window
    detail_win.update_idletasks()
    width = detail_win.winfo_width()
    height = detail_win.winfo_height()
    x = (detail_win.winfo_screenwidth() // 2) - (width // 2)
    y = (detail_win.winfo_screenheight() // 2) - (height // 2)
    detail_win.geometry(f'+{x}+{y}')




def print_receipt(image_path):
    """
    Sends the receipt image to the default printer (Windows only).
    On Windows, os.startfile with the "print" verb will invoke the associated
    program's print command. Adjust for other OSes as needed.
    """
    try:
        # This only works on Windows
        os.startfile(image_path, "print")

    except Exception as e:
        print("Failed to print receipt:", e)

def view_receipt(image_path):
    """
    Opens a fixed-size, centered popup to display the receipt image,
    with Print and Close buttons.
    """
    if not image_path:
        print("No image path provided.")
        return

    def on_print():
        print_receipt(image_path)
        win.destroy()

    # Set desired window size
    receipt_width  = 350
    receipt_height = 600

    # Create Toplevel window
    win = tk.Toplevel()
    win.overrideredirect(True)  # remove borders
    win.attributes("-topmost", True)

    # Center the window
    win.update_idletasks()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = (screen_w // 2) - (receipt_width // 2)
    y = (screen_h // 2) - (receipt_height // 2)
    win.geometry(f"{receipt_width}x{receipt_height}+{x}+{y}")

    try:
        # Load and resize image
        img = Image.open(image_path)
        img = img.resize((receipt_width, receipt_height), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
    except Exception as e:
        print("Failed to load image:", e)
        win.destroy()
        return

    # Display image
    lbl = tk.Label(win, image=photo, bg="white")
    lbl.image = photo  # keep reference!
    lbl.pack(fill="both", expand=True)

    # Close button
    btn_close = ctk.CTkButton(
        win,
        text="Close",
        fg_color="#2d3e50",
        hover_color="#3c4f63",
        command=win.destroy
    )
    btn_close.place(relx=0.25, rely=0.96, anchor="center")

    # Print button
    btn_print = ctk.CTkButton(
        win,
        text="Print",
        fg_color="#2d3e50",
        hover_color="#3c4f63",
        command=lambda: on_print()
    )
    btn_print.place(relx=0.75, rely=0.96, anchor="center")




def update_stock_alerts():
    """
    1) For any product whose stockQuantity <= 5, ensure there's an active low_stock alert.
    2) For any product whose stockQuantity > 5, if there's an active low_stock alert, mark it resolved.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1) Find all products with stockQuantity <= 5
    cur.execute("SELECT ProductID FROM product WHERE stockQuantity <= 5")
    low_pids = [row[0] for row in cur.fetchall()]

    for pid in low_pids:
        # Check if there's already an active low_stock alert for this ProductID
        cur.execute("""
            SELECT COUNT(*)
              FROM stockAlert
             WHERE ProductID   = ?
               AND AlertType   = 'low_stock'
               AND AlertStatus = 'active'
        """, (pid,))
        count_active = cur.fetchone()[0]

        if count_active == 0:
            # Insert a new active low_stock alert
            cur.execute("""
                INSERT INTO stockAlert
                    (ProductID, AlertType, AlertStatus, TimeStamp)
                VALUES (?, 'low_stock', 'active', ?)
            """, (pid, now_str))

    # 2) Find all products with stockQuantity > 5
    cur.execute("SELECT ProductID FROM product WHERE stockQuantity > 5")
    high_pids = [row[0] for row in cur.fetchall()]

    for pid in high_pids:
        # If there is any active low_stock alert for this pid, mark it resolved
        cur.execute("""
            SELECT COUNT(*)
              FROM stockAlert
             WHERE ProductID   = ?
               AND AlertType   = 'low_stock'
               AND AlertStatus = 'active'
        """, (pid,))
        count_active = cur.fetchone()[0]

        if count_active > 0:
            cur.execute("""
                UPDATE stockAlert
                   SET AlertStatus = 'resolved',
                       TimeStamp   = ?
                 WHERE ProductID  = ?
                   AND AlertType   = 'low_stock'
                   AND AlertStatus = 'active'
            """, (now_str, pid))

    conn.commit()
    conn.close()

def fetch_alerts(threshold=5):
    """
    1) Sync product → stockAlert (new low-stock alerts; resolve recovered items).
    2) Return: (AlertID, ProductID, productName, stockQuantity, AlertStatus, TimeStamp)
    """
    # ensure stockAlert is current
    update_stock_alerts()

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
      SELECT sa.AlertID,
             sa.ProductID,
             p.productName,
             p.stockQuantity,
             sa.AlertStatus,
             sa.TimeStamp,
             p.imagePath
        FROM stockAlert AS sa
        JOIN product     AS p
          ON p.ProductID = sa.ProductID
       WHERE sa.AlertType = 'low_stock'
         AND p.stockQuantity <= ?
       ORDER BY sa.TimeStamp DESC
    """, (threshold,))
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_all_products():
    """
    Returns every product:
      [(ProductID, productName, category, price, stockQuantity), …]
    """
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
      SELECT ProductID, productName, category, price, stockQuantity, imagepath
        FROM product
       ORDER BY productName
    """)
    rows = cur.fetchall()
    conn.close()
    return rows



def fetch_transactions(txn_id=None, date_from=None, date_to=None, limit=None):
    """
    Returns rows:
      (TransactionID, Username, DateTIme, TotalAmount, Receipt)
    Applies the same filters as before on TransactionID and date range.
    """
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Base SELECT with join to user
    base = """
      SELECT 
        t.TransactionID,
        u.Username,
        t.DateTIme,
        t.TotalAmount,
        t.Receipt
      FROM "transaction" AS t
      JOIN "user"        AS u
        ON t.CashierID = u.UserID
    """

    clauses = []
    params  = []
    if txn_id:
        clauses.append("t.TransactionID = ?")
        params.append(txn_id)
    if date_from and date_to:
        clauses.append("DATE(t.DateTIme) BETWEEN ? AND ?")
        params.extend([date_from.isoformat(), date_to.isoformat()])
    elif date_from:
        clauses.append("DATE(t.DateTIme) >= ?")
        params.append(date_from.isoformat())
    elif date_to:
        clauses.append("DATE(t.DateTIme) <= ?")
        params.append(date_to.isoformat())

    if clauses:
        base += " WHERE " + " AND ".join(clauses)

    base += " ORDER BY t.DateTIme DESC"

    if not clauses and limit:
        base += " LIMIT ?"
        params.append(limit)

    cur.execute(base, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return rows



def fetch_sales_summary():
    """
    Count & sum today's transactions (DateTIme between YYYY-MM-DD 00:00:00 and next day 00:00:00).
    Returns: (txn_count, total_sales)
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)

    start_of_day = f"{today.isoformat()} 00:00:00"
    start_of_next = f"{tomorrow.isoformat()} 00:00:00"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """
        SELECT 
            COUNT(*) AS txn_count,
            COALESCE(SUM(TotalAmount), 0) AS total_sales
        FROM "transaction"
        WHERE DateTIme >= ?
          AND DateTIme < ?
    """
    cur.execute(query, (start_of_day, start_of_next))
    result = cur.fetchone()
    conn.close()

    if result:
        return (result[0], result[1])
    else:
        return (0, 0.0)


def create_dashboard_widgets(parent):
    """
    Build the Sales Summary banner on top, then two side-by-side tables:
      • Left:  Low Stock Alerts  (with “Sort by Status” filter, expanded Timestamp column)
      • Right: Transaction History (with Transaction ID + Date Range search + Emoji Reset)
    Uses larger fonts (20 pt summary, 16 pt filters, 14 pt rows).
    """

    # ── Sales Summary Frame (top) ──
    txn_count, total_sales = fetch_sales_summary()

    summary_frame = ctk.CTkFrame(parent, fg_color=PRIMARY, corner_radius=12)
    summary_frame.pack(fill="x", padx=15, pady=15, ipady=0)
    summary_frame.grid_columnconfigure(0, weight=1)
    summary_frame.grid_columnconfigure(1, weight=1)

    lbl_txn = ctk.CTkLabel(
        summary_frame,
        text=f"📊Today Transaction: {txn_count}",
        font=("Segoe UI", 22, "bold"),
        text_color="white"
    )
    lbl_txn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    lbl_sales = ctk.CTkLabel(
        summary_frame,
        text=f"💰Daily Sales: RM {total_sales:.2f}",
        font=("Segoe UI", 22, "bold"),
        text_color="white"
    )
    lbl_sales.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="e")  # align to right half

    # ── Container for two tables ──
    content_frame = ctk.CTkFrame(parent, fg_color="#E8EDF2", corner_radius=0)
    content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    content_frame.grid_columnconfigure(0, weight=5)
    content_frame.grid_columnconfigure(1, weight=1)

    content_frame.grid_rowconfigure(0, weight=1)

    # ══ LEFT SIDE: Inventory / Alerts ══
    left_frame = ctk.CTkFrame(content_frame, fg_color="#ffffff", corner_radius=12)
    left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    left_frame.grid_columnconfigure(0, weight=1)
    left_frame.grid_rowconfigure(1, weight=1)

    # ── Header with title and view toggle ──
    header_frame = ctk.CTkFrame(left_frame, fg_color="transparent", height=40)
    header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
    header_frame.grid_columnconfigure(1, weight=1)

    # Title label - will be updated dynamically
    title_label = ctk.CTkLabel(
        header_frame,
        text="Low Stock Alerts",
        font=("Segoe UI", 16, "bold"),
        text_color="#2d3e50",
        anchor="w"
    )
    title_label.grid(row=0, column=0, sticky="w")

    # View toggle
    view_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    view_frame.grid(row=0, column=1, sticky="e")

    ctk.CTkLabel(
        view_frame,
        text="View:",
        font=("Segoe UI", 13),
        text_color="#555"
    ).pack(side="left", padx=(0, 8), pady=0)

    view_var = tk.StringVar(value="Low Stock Only")
    view_menu = ctk.CTkOptionMenu(
        view_frame,
        values=["Low Stock Only", "All Products"],
        variable=view_var,
        font=("Segoe UI", 12),
        width=130,
        height=26,
        fg_color="#ffffff",
        button_color="#e0e0e0",
        button_hover_color="#d0d0d0",
        dropdown_fg_color="#ffffff",
        dropdown_hover_color="#f0f0f0",
        text_color="#333",
        dropdown_text_color="#333",
        command=lambda _: reload_left_table()
    )
    view_menu.pack(side="right")

    # ── Scrollable Area ──
    left_scroll = ctk.CTkScrollableFrame(
        left_frame,
        fg_color="transparent",
        corner_radius=0
    )
    left_scroll.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
    left_scroll.grid_columnconfigure(0, weight=1)

    def reload_left_table():
        # Clear existing widgets
        for widget in left_scroll.winfo_children():
            widget.destroy()

        mode = view_var.get()
        # Update title based on view
        if mode == "Low Stock Only":
            data = fetch_alerts()
            title_label.configure(text="Low Stock Alerts")
        else:
            data = fetch_all_products()
            title_label.configure(text="All Products")

        if not data:
            # Empty state message
            empty_frame = ctk.CTkFrame(left_scroll, fg_color="transparent", height=150)
            empty_frame.pack(fill="both", expand=True, pady=20)

            ctk.CTkLabel(
                empty_frame,
                text="🎉 All products are well-stocked!" if mode == "Low Stock Only" else "No products found",
                font=("Segoe UI", 16),
                text_color="#777"
            ).pack(pady=10)

            return

        # Create compact cards with images
        for item in data:
            # Unpack data based on mode
            if mode == "Low Stock Only":
                _, pid, name, qty, status, ts, img_path = item
                is_low = True
                # Format timestamp to "Jun 30, 3:45 PM"
                timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %I:%M %p")
                details = f"Alert: {timestamp}"
            else:
                pid, name, category, price, qty, img_path = item
                is_low = qty <= 5
                details = f"{category} • RM{price:.2f}"

            # Define status color
            status_color = "#e63946" if is_low else "#2a9d8f"

            # Card frame
            card = ctk.CTkFrame(
                left_scroll,
                fg_color="#ffffff",
                border_color="#eaeaea",
                border_width=1,
                corner_radius=8,
                height=100  # Increased height for progress bar
            )
            card.pack(fill="x", pady=(0, 6), padx=0)
            card.pack_propagate(False)

            # Status indicator (colored left border)
            status_indicator = ctk.CTkFrame(
                card,
                fg_color=status_color,
                width=4,
                corner_radius=2,
                height=96  # Slightly less than card height
            )
            status_indicator.place(x=3, y=2)


            # Product image container
            img_container = ctk.CTkFrame(card, width=50, height=50, fg_color="transparent")
            img_container.place(x=15, y=25)

            try:
                if img_path and os.path.exists(img_path):
                    img = Image.open(img_path)
                    img = img.resize((45, 45), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    img_label = tk.Label(img_container, image=photo, bg="#ffffff")
                    img_label.image = photo
                    img_label.place(relx=0.5, rely=0.5, anchor="center")
                else:
                    raise Exception("Image not found")
            except:
                # Placeholder if image missing
                placeholder = ctk.CTkLabel(
                    img_container,
                    text="🖼️",
                    font=("Arial", 16),
                    text_color="#cccccc",
                    width=45,
                    height=45
                )
                placeholder.place(relx=0.5, rely=0.5, anchor="center")

            # Text content frame
            text_frame = ctk.CTkFrame(
                card,
                fg_color="transparent",
                width=200,
                height=50
            )
            text_frame.place(x=75, y=25)

            # Product name
            name_label = ctk.CTkLabel(
                text_frame,
                text=name,
                font=("Segoe UI", 15),
                text_color="#2d3e50",
                anchor="w",
                wraplength=180
            )
            name_label.pack(fill="x", anchor="w", pady=(0, 2))

            # Details
            details_label = ctk.CTkLabel(
                text_frame,
                text=details,
                font=("Segoe UI", 13),
                text_color="#777",
                anchor="w"
            )
            details_label.pack(fill="x", anchor="w")

            # Stock info frame
            stock_frame = ctk.CTkFrame(
                card,
                fg_color="transparent",
                width=100,
                height=45
            )
            stock_frame.place(relx=0.75, rely=0.5, anchor="center", y=10)

            # Progress bar showing stock level (ABOVE the stock number)
            progress = ctk.CTkProgressBar(
                stock_frame,
                width=90,
                height=10,
                fg_color="#e0e0e0",
                progress_color=status_color,
                corner_radius=4
            )
            progress.set(min(qty / 100, 1.0))  # Scale for visual
            progress.pack(pady=(0, 5))

            # Stock number and low stock indicator frame
            stock_num_frame = ctk.CTkFrame(
                stock_frame,
                fg_color="transparent"
            )
            stock_num_frame.pack()

            # Stock amount
            stock_label = ctk.CTkLabel(
                stock_num_frame,
                text=f"{qty}",
                font=("Segoe UI", 16, "bold"),
                text_color="#e63946" if is_low else "#2a9d8f",
            )
            stock_label.pack(side="left", padx=(0, 5))

            # LOW STOCK indicator - to the right of the stock number
            if is_low:
                low_label = ctk.CTkLabel(
                    stock_num_frame,
                    text="LOW STOCK",
                    font=("Segoe UI", 11, "bold"),
                    text_color="#ffffff",
                    fg_color="#e63946",
                    corner_radius=4,
                    padx=4,
                    pady=1
                )
                low_label.pack(side="left")

            # "in stock" text below the progress bar
            stock_text = ctk.CTkLabel(
                stock_frame,
                text="in stock",
                font=("Segoe UI", 11),
                text_color="#777"
            )
            stock_text.pack()

            # Information button
            info_btn = ctk.CTkButton(
                card,
                text="ⓘ",
                width=28,
                height=28,
                font=("Arial", 14, "bold"),
                fg_color="#e0e0e0",
                hover_color="#d0d0d0",
                text_color="#2d3e50",
                command=lambda pid=pid: show_product_details(pid)
            )
            info_btn.place(relx=0.93, rely=0.5, anchor="center")

    # initial load
    reload_left_table()

    # ══ RIGHT SIDE: Transaction History ══
    right_frame = ctk.CTkFrame(
        content_frame,
        fg_color="#fff",
        corner_radius=8,
        border_width=0,
        border_color="#ccc"
    )
    right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    right_frame.grid_columnconfigure(0, weight=1)
    right_frame.grid_rowconfigure(3, weight=1)

    lbl_txn_header = ctk.CTkLabel(
        right_frame,
        text="Transaction History",
        font=("Segoe UI", 20, "bold"),
        text_color="#333"
    )
    lbl_txn_header.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

    # ── Search Row: Transaction ID + Date Range + "Search" + "🔄" Reset ──
    search_frame = ctk.CTkFrame(right_frame, fg_color="#E8EDF2", corner_radius=8)
    search_frame.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
    search_frame.grid_columnconfigure(1, weight=1)
    search_frame.grid_columnconfigure(3, weight=1)
    search_frame.grid_columnconfigure(5, weight=1)

    lbl_txn_id = ctk.CTkLabel(
        search_frame,
        text="Transaction ID:",
        font=("Segoe UI", 16),   # 16 pt for bigger text
        text_color="#333"
    )
    lbl_txn_id.grid(row=0, column=0, padx=(8, 2), pady=5, sticky="w")
    txn_id_var = tk.StringVar()
    entry_txn_id = ctk.CTkEntry(
        search_frame,
        textvariable=txn_id_var,
        font=("Segoe UI", 14),
        placeholder_text="e.g. 12345"
    )
    entry_txn_id.grid(row=0, column=1, padx=(2, 10), pady=5, sticky="w")

    lbl_from = ctk.CTkLabel(
        search_frame,
        text="From:",
        font=("Segoe UI", 16),   # 16 pt
        text_color="#333"
    )
    lbl_from.grid(row=0, column=2, padx=(8, 2), pady=5, sticky="w")
    date_from_var = tk.StringVar()
    date_from_picker = DateEntry(
        search_frame,
        textvariable=date_from_var,
        date_pattern="yyyy-mm-dd",
        font=("Segoe UI", 14),
        background="white",
        foreground="black",
        borderwidth=1
    )
    date_from_picker.grid(row=0, column=3, padx=(2, 10), pady=5, sticky="w")

    lbl_to = ctk.CTkLabel(
        search_frame,
        text="To:",
        font=("Segoe UI", 16),   # 16 pt
        text_color="#333"
    )
    lbl_to.grid(row=0, column=4, padx=(8, 2), pady=5, sticky="w")
    date_to_var = tk.StringVar()
    date_to_picker = DateEntry(
        search_frame,
        textvariable=date_to_var,
        date_pattern="yyyy-mm-dd",
        font=("Segoe UI", 14),
        background="white",
        foreground="black",
        borderwidth=1
    )
    date_to_picker.grid(row=0, column=5, padx=(2, 10), pady=5, sticky="w")
    date_from_picker = DateEntry(
        search_frame,
        textvariable=date_from_var,
        date_pattern="yyyy-mm-dd",
        font=("Segoe UI", 14),
        background="white",
        foreground="black",
        borderwidth=1
    )
    date_from_picker.grid(row=0, column=3, padx=(2, 10), pady=5, sticky="w")
    date_from_var.set("")   # make it empty by default

    # Create “To” DateEntry, then clear it immediately
    date_to_picker = DateEntry(
        search_frame,
        textvariable=date_to_var,
        date_pattern="yyyy-mm-dd",
        font=("Segoe UI", 14),
        background="white",
        foreground="black",
        borderwidth=1
    )
    date_to_picker.grid(row=0, column=5, padx=(2, 10), pady=5, sticky="w")
    date_to_var.set("")

    def on_search_button():
        """
        Called when user clicks "Search"—reads txn_id_var, date_from_var, date_to_var,
        converts them, then calls reload_txn_table(...) accordingly.
        """
        tid = txn_id_var.get().strip()
        from_str = date_from_var.get().strip()
        to_str   = date_to_var.get().strip()

        dt_from = None
        dt_to   = None

        if from_str:
            try:
                dt_from = datetime.strptime(from_str, "%Y-%m-%d").date()
            except ValueError:
                dt_from = None

        if to_str:
            try:
                dt_to = datetime.strptime(to_str, "%Y-%m-%d").date()
            except ValueError:
                dt_to = None

        reload_txn_table(txn_id=tid or None, date_from=dt_from, date_to=dt_to)

    btn_search = ctk.CTkButton(
        search_frame,
        text="Search",
        font=("Segoe UI", 14, "bold"),
        fg_color="#2d3e50",    # Button color
        hover_color="#3c4f63",
        command=on_search_button
    )
    btn_search.grid(row=0, column=6, padx=(5, 2), pady=5, sticky="w")

    def on_reset_button():
        """
        Called when user clicks "🔄"—clears all filter fields and reloads unfiltered table.
        """
        txn_id_var.set("")
        date_from_var.set("")
        date_to_var.set("")
        reload_txn_table()

    btn_reset = ctk.CTkButton(
        search_frame,
        text="🔄",
        font=("Segoe UI", 14),
        fg_color="#2d3e50",
        hover_color="#3c4f63",
        command=on_reset_button
    )
    btn_reset.grid(row=0, column=7, padx=(2, 10), pady=5, sticky="w")

    # ── Scrollable Table for Transactions ──
    txn_scroll = ctk.CTkScrollableFrame(
        right_frame,
        fg_color="#ffffff",
        corner_radius=8,
        border_width=0,
        border_color="#ddd"
    )
    txn_scroll._scrollbar.grid_remove()
    txn_scroll.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")
    for col in range(4):
        txn_scroll.grid_columnconfigure(col, weight=1)



    # ── Create the header background frame ──
    txn_header_bg = ctk.CTkFrame(txn_scroll, fg_color="#e0e0e0", corner_radius=0, height=40)
    # Prevent the grid layout from resizing txn_header_bg
    txn_header_bg.grid_propagate(False)

    txn_header_bg.grid(row=0, column=0, columnspan=5, sticky="ew")
    for col in range(5):
        txn_header_bg.grid_columnconfigure(col, weight=1)

    # Place each label with a fixed height of 40px
    txn_headers = ["Transaction ID", "Cashier Name", "Date and Time", "Total (RM)", "Receipt"]
    n_cols = len(txn_headers)

    for i, h in enumerate(txn_headers):
        ctk.CTkLabel(
            txn_header_bg,
            text=h,
            font=("Segoe UI", 16, "bold"),
            text_color="#555",
            height=40  # set the height here, not in place()
        ).place(
            relx=i / n_cols,
            y=0,
            relwidth=1 / n_cols,
            anchor="nw"
        )

    # Store references so reload function can clear + repopulate
    right_frame.txn_scroll    = txn_scroll
    right_frame.txn_id_var    = txn_id_var
    right_frame.date_from_var = date_from_var
    right_frame.date_to_var   = date_to_var

    def _create_txn_header(parent):
        """Recreate the transaction table header"""
        # Header separator
        header_separator = ctk.CTkFrame(
            parent,
            height=2,
            fg_color=PRIMARY,
            corner_radius=2
        )
        header_separator.pack(fill="x", pady=(0, 5))

        # Header background
        txn_header_bg = ctk.CTkFrame(parent, fg_color="#e0e0e0", corner_radius=0, height=40)
        txn_header_bg.pack(fill="x")

        # Header labels
        txn_headers = ["Transaction ID", "Cashier Name", "Date and Time", "Total (RM)", "Receipt"]
        n_cols = len(txn_headers)

        for i, h in enumerate(txn_headers):
            ctk.CTkLabel(
                txn_header_bg,
                text=h,
                font=("Segoe UI", 16, "bold"),
                text_color="#555",
                height=40
            ).place(
                relx=i / n_cols,
                y=0,
                relwidth=1 / n_cols,
                anchor="nw"
            )

        # Store references for future access
        parent.header_separator = header_separator
        parent.txn_header_bg = txn_header_bg

    def reload_txn_table(txn_id=None, date_from=None, date_to=None):
        """
        Clears existing rows and repopulates with improved vertical alignment
        """
        # Clear existing rows
        for widget in txn_scroll.winfo_children():
            widget.destroy()

        # Fetch transactions
        recent_txns = fetch_transactions(
            txn_id=txn_id,
            date_from=date_from,
            date_to=date_to,
            limit=None
        )

        if not recent_txns:
            # Empty state
            empty_frame = ctk.CTkFrame(txn_scroll, fg_color="transparent", height=150)
            empty_frame.pack(fill="both", expand=True, pady=20)

            ctk.CTkLabel(
                empty_frame,
                text="📭 No transactions found",
                font=("Segoe UI", 18),
                text_color="#777"
            ).pack(pady=10)
            return

        # Create compact cards with improved alignment
        for tid, username, dt, total, receipt in recent_txns:
            # Create card container
            card = ctk.CTkFrame(
                txn_scroll,
                fg_color="#ffffff",
                border_color="#e0e6ed",
                border_width=1,
                corner_radius=14,
                height=75  # Slightly taller for better spacing
            )
            card.pack(fill="x", pady=(0, 8), padx=0)
            card.pack_propagate(False)

            # Main content grid with improved vertical alignment
            content_frame = ctk.CTkFrame(card, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=15, pady=12)  # Increased vertical padding

            # Configure grid columns
            content_frame.grid_columnconfigure(0, weight=0, minsize=100)  # ID column
            content_frame.grid_columnconfigure(1, weight=3)  # Info column
            content_frame.grid_columnconfigure(2, weight=1)  # Amount/receipt column

            # Create a single row with all elements vertically centered
            id_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            id_frame.grid(row=0, column=0, sticky="nsw")

            info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            info_frame.grid(row=0, column=1, sticky="nsw", padx=10)

            right_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            right_frame.grid(row=0, column=2, sticky="nse")

            # Transaction ID with emoji - vertically centered
            ctk.CTkLabel(
                id_frame,
                text=f"🆔 #{tid}",
                font=("Segoe UI", 17, "bold"),
                text_color="#4361ee",
                height=40,  # Fixed height for consistent alignment
                anchor="w"
            ).pack(fill="x", pady=5)  # Vertical padding for centering

            # Combined cashier and date in one line - vertically centered
            try:
                formatted_dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %I:%M%p")
            except:
                formatted_dt = dt

            # Create combined info string with emojis
            info_text = f"👤 {username} • 📅 {formatted_dt}"

            ctk.CTkLabel(
                info_frame,
                text=info_text,
                font=("Segoe UI", 15),
                text_color="#555",
                height=40,  # Fixed height for consistent alignment
                anchor="w"
            ).pack(fill="x", pady=5)  # Vertical padding for centering

            # Right section container - vertically centered
            amount_receipt_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
            amount_receipt_frame.pack(anchor="e", fill="y", expand=True)

            # Amount and receipt in a horizontal layout
            amount_frame = ctk.CTkFrame(amount_receipt_frame, fg_color="transparent")
            amount_frame.pack(side="left", padx=(0, 15), fill="y", expand=True)

            # Amount without emoji - vertically centered
            ctk.CTkLabel(
                amount_frame,
                text=f"RM{total:.2f}",
                font=("Segoe UI", 17, "bold"),
                text_color="#2a9d8f",
                height=40,  # Fixed height for consistent alignment
                anchor="e"
            ).pack(fill="both", expand=True, pady=5)

            # Receipt button - vertically centered
            receipt_frame = ctk.CTkFrame(amount_receipt_frame, fg_color="transparent")
            receipt_frame.pack(side="left", fill="y", expand=True)

            if receipt:
                receipt_button = ctk.CTkButton(
                    receipt_frame,
                    text="📄 Receipt",
                    width=100,
                    height=32,
                    corner_radius=8,
                    fg_color="#4361ee",
                    hover_color="#3a0ca3",
                    font=("Segoe UI", 13),
                    anchor="center",  # Center text in button
                    command=lambda p=receipt: view_receipt(p)
                )
                receipt_button.pack(pady=5)  # Vertical padding for centering
            else:
                receipt_indicator = ctk.CTkLabel(
                    receipt_frame,
                    text="📭 No Receipt",
                    font=("Segoe UI", 13),
                    text_color="#aaa",
                    height=40,  # Fixed height for consistent alignment
                    anchor="center"
                )
                receipt_indicator.pack(fill="both", expand=True, pady=5)


    # ... elsewhere in your setup, after widgets are created:
    reload_txn_table()

            # Column 4 (Receipt) is intentionally left blank



# Example of how you might launch this in a CTk window:
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1200x700")
    root.title("Inventory Dashboard")

    create_dashboard_widgets(root)

    root.mainloop()
