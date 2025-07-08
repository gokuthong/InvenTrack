from PIL import Image
import customtkinter as ctk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import bcrypt
import re
import qrcode
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class PaymentPageDatabase:
    def __init__(self, db_file=Path(__file__).parent.parent / "inventoryproject.db"):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.create_card_payment_table()

    def create_card_payment_table(self):
        """Create CardPayment table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS CardPayment (
                PaymentID INTEGER PRIMARY KEY AUTOINCREMENT,
                TransactionID INTEGER,
                CardholderName BLOB NOT NULL,
                CardNumber BLOB NOT NULL,
                ExpiryDate BLOB NOT NULL,
                CVV BLOB NOT NULL,
                PaymentDateTime TEXT NOT NULL,
                FOREIGN KEY (TransactionID) REFERENCES `Transaction` (TransactionID)
            )
        """)
        self.conn.commit()

    def insert_card_payment(self, transaction_id, cardholder_name_hashed, card_number_hashed, expiry_hashed, cvv_hashed):
        """Insert hashed card payment details into CardPayment table."""
        payment_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.cursor.execute("""
                INSERT INTO CardPayment (TransactionID, CardholderName, CardNumber, ExpiryDate, CVV, PaymentDateTime)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (transaction_id, cardholder_name_hashed, card_number_hashed, expiry_hashed, cvv_hashed, payment_datetime))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error during card payment insertion: {e}")
            return False

    def insert_transaction(self, total_amount, cashier_id):
        """Insert a new transaction into the Transaction table."""
        transaction_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.cursor.execute("""
                INSERT INTO `Transaction` (DateTime, TotalAmount, CashierID)
                VALUES (?, ?, ?)
            """, (transaction_datetime, total_amount, cashier_id))
            self.conn.commit()
            return self.cursor.lastrowid  # Return the TransactionID
        except sqlite3.Error as e:
            print(f"Database error during transaction insertion: {e}")
            return None

    def deduct_stock(self, cart_items):
        """Deduct stock quantities for sold items in the product table and return low stock items."""
        low_stock_items = []
        try:
            for product_id, quantity in cart_items.items():
                self.cursor.execute("SELECT stockQuantity, productName FROM product WHERE productID = ?", (product_id,))
                result = self.cursor.fetchone()
                if result is None:
                    print(f"Product ID {product_id} not found in database.")
                    return False, low_stock_items
                current_stock, product_name = result
                if current_stock < quantity:
                    print(f"Insufficient stock for {product_name} (ID: {product_id}). Required: {quantity}, Available: {current_stock}")
                    return False, low_stock_items
                new_stock = current_stock - quantity
                self.cursor.execute("UPDATE product SET stockQuantity = ? WHERE productID = ?", (new_stock, product_id))
                if new_stock < 5:
                    low_stock_items.append({
                        'product_id': product_id,
                        'product_name': product_name,
                        'stock_quantity': new_stock
                    })
            self.conn.commit()
            return True, low_stock_items
        except sqlite3.Error as e:
            print(f"Database error during stock deduction: {e}")
            return False, low_stock_items

    def get_admin_emails(self):
        """Retrieve email addresses of all admin users from the Users table."""
        try:
            self.cursor.execute("SELECT Email FROM User WHERE Role = 'Admin'")
            admin_emails = [row[0] for row in self.cursor.fetchall() if row[0]]
            return admin_emails
        except sqlite3.Error as e:
            print(f"Database error while fetching admin emails: {e}")
            return []

    def get_product_details(self, product_id):
        """Fetch product name and price from the product table."""
        self.cursor.execute("SELECT productName, price FROM product WHERE productID = ?", (product_id,))
        return self.cursor.fetchone()

    def close(self):
        """Close the database connection."""
        self.conn.close()

class PaymentPage(ctk.CTk):
    def __init__(self, cashier_id=1):
        super().__init__()
        self.db = PaymentPageDatabase()
        self.cashier_id = cashier_id
        self.title("Payment Page")
        self.geometry("1920x1080")
        self.configure(fg_color="white")
        self.resizable(True, True)

        self.payment_completed = False
        self.view_receipt_button = None
        self.transaction_id = None  # Store TransactionID
        self.total_amount = 0.0
        self.cart_items = {}  # Store cart items for receipt display

        self.image_refs = []
        placeholder_img = Image.new('RGB', (260, 155), color='#cccccc')
        self.default_image = ctk.CTkImage(placeholder_img, size=(260, 155))
        self.image_refs.append(self.default_image)

        try:
            pil_bg = Image.open(Path(__file__).parent / "pictures/background.png")
            ctk_bg = ctk.CTkImage(pil_bg, size=(1920, 1080))
            self.image_refs.append(ctk_bg)
            bg_label = ctk.CTkLabel(self, image=ctk_bg, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Background load error: {e}")

        self.sidebar_expanded = False
        self.sidebar_width = 180
        self.current_page = "Payment Page"

        self.header_frame = ctk.CTkFrame(self, fg_color="#2d3e50", bg_color="#2d3e50", width=1920, height=55)
        self.header_frame.place(x=0, y=0)

        self.title_label = ctk.CTkLabel(self.header_frame, text=self.current_page, font=("Segoe UI", 25), text_color="#fff")
        self.title_label.place(x=120, y=10)

        # Load cart and create transaction on page load
        self.cart_items = self.load_cart_items()
        if self.cart_items:
            self.calculate_total_amount()
            self.create_initial_transaction()
        else:
            print("Cart is empty. No transaction created.")

        self._create_sidebar()
        self._create_toggle_button()
        self._create_top_buttons()

        self.payment_methods = ["Card", "Touch'N Go", "Cash"]
        self.selected_payment_method = "Card"

        self._create_main_panel()

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color="#2d3e50", corner_radius=0, width=self.sidebar_width, height=1080, border_width=0, border_color="#ddd")
        ctk.CTkLabel(self.sidebar, text="InvenTrack", font=("Segoe UI", 28, "bold"), text_color="#fff").place(x=20, y=20)
        self.sidebar_buttons = {}
        y = 80
        for name in ["Payment Page"]:
            is_current = (name == self.current_page)
            btn = ctk.CTkButton(self.sidebar, text=name, width=160, height=50, corner_radius=10,
                                fg_color="#34495E" if is_current else "transparent",
                                hover_color="#3E5870" if is_current else "#4A6374",
                                text_color="#FFFFFF", font=("Segoe UI", 18.5), command=self.show_payment)
            btn.place(x=10, y=y)
            self.sidebar_buttons[name] = btn
            y += 70
        ctk.CTkButton(self.sidebar, text="🔒 Log Out", width=160, height=50, corner_radius=0,
                      fg_color="transparent", hover_color="#f0f8ff", text_color="#fff",
                      font=("Segoe UI", 18.5), command=self.logout).place(x=10, y=950)

    def _create_toggle_button(self):
        self.toggle_btn = ctk.CTkButton(self, text="☰", width=45, height=45, corner_radius=0,
                                        fg_color="#2d3e50", bg_color="#2d3e50", hover_color="#2d3e50",
                                        text_color="#fff", font=("Segoe UI", 20), command=self.toggle_sidebar)
        self.toggle_btn.place(x=12, y=6)
        self.toggle_btn.lift()

    def _create_top_buttons(self):
        btn_size = 35
        self.cart_btn = ctk.CTkButton(self, text="🛒", width=btn_size, height=btn_size, corner_radius=0,
                                      fg_color="#2d3e50", bg_color="#2d3e50", hover_color="#1a252f",
                                      text_color="#fff", font=("Segoe UI", 20), command=lambda: print("Go to Cart"))
        self.profile_btn = ctk.CTkButton(self, text="👤", width=btn_size, height=btn_size, corner_radius=0,
                                         fg_color="#2d3e50", bg_color="#2d3e50", hover_color="#1a252f",
                                         text_color="#fff", font=("Segoe UI", 20))
        self.update_button_positions()

    def update_button_positions(self):
        btn_size = 35
        margin = 12
        panel_x = 1080
        panel_w = 525
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        px = panel_x + panel_w - margin - btn_size + x_off
        self.profile_btn.place(x=px, y=margin)
        self.cart_btn.place(x=px - (btn_size + margin), y=margin)

    def logout(self):
        self.db.close()
        self.destroy()

    def toggle_sidebar(self):
        steps, total_duration = 5, 50
        delta = self.sidebar_width // steps

        def expand(step=0):
            w = delta * step
            self.sidebar.configure(width=w)
            x_off = w
            self.toggle_btn.place_configure(x=10 + x_off)
            self.title_label.place_configure(x=120 + x_off)
            self.panel.place_configure(x=110 + x_off)
            self.update_button_positions()
            if step < steps:
                self.after(total_duration // steps, lambda: expand(step + 1))
            else:
                self.sidebar_expanded = True

        def collapse(step=steps):
            w = delta * step
            self.sidebar.configure(width=w)
            x_off = w
            self.toggle_btn.place_configure(x=10 + x_off)
            self.title_label.place_configure(x=120 + x_off)
            self.panel.place_configure(x=110 + x_off)
            self.update_button_positions()
            if step > 0:
                self.after(total_duration // steps, lambda: collapse(step - 1))
            else:
                self.sidebar.place_forget()
                self.sidebar_expanded = False
                self.update_button_positions()

        if self.sidebar_expanded:
            collapse()
        else:
            self.sidebar  .place(x=0, y=0)
            self.sidebar.lift()
            expand()

    def show_payment(self):
        self.current_page = "Payment Page"
        self.title_label.configure(text=self.current_page)
        for name, btn in self.sidebar_buttons.items():
            if name == "Payment Page":
                btn.configure(fg_color="#34495E", hover_color="#3E5870")
            else:
                btn.configure(fg_color="transparent", hover_color="#4A6374")
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.panel.place(x=110 + x_off, y=80)
        if self.sidebar_expanded:
            self.toggle_sidebar()
        else:
            self.update_button_positions()

    def _create_main_panel(self):
        self.panel = ctk.CTkFrame(self, fg_color="#fff", width=1500, height=900)
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.panel.place(x=120 + x_off, y=80)
        self.cat_frame = ctk.CTkFrame(self.panel, fg_color="#fff", corner_radius=20, width=1500, height=900)
        self.cat_frame.place(x=0, y=0)
        w = 1500 / len(self.payment_methods)
        self.cat_buttons = []
        for i, cat in enumerate(self.payment_methods):
            btn = ctk.CTkButton(self.cat_frame, text=cat, corner_radius=20,
                                fg_color="#2d3e50" if cat == self.selected_payment_method else "transparent",
                                text_color="#fff" if cat == self.selected_payment_method else "#333",
                                hover_color="#e6f0ff", font=("Arial", 40), width=500, height=100,
                                command=lambda c=cat: self.select_payment_method(c))
            btn.place(x=i * w, y=0)
            self.cat_buttons.append(btn)
        self.content_frame = ctk.CTkFrame(self.panel, fg_color="#fff", width=1500, height=800, corner_radius=20)
        self.content_frame.place(x=0, y=100)
        self.show_card_payment_fields()

    def select_payment_method(self, method):
        self.selected_payment_method = method
        for btn, cat in zip(self.cat_buttons, self.payment_methods):
            if cat == method:
                btn.configure(fg_color="#2d3e50", text_color="#fff")
            else:
                btn.configure(fg_color="transparent", text_color="#333")
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.view_receipt_button = None
        if method == "Card":
            self.show_card_payment_fields()
        elif method == "Touch'N Go":
            self.show_touchngo_payment_fields()
        elif method == "Cash":
            self.show_cash_payment_fields()

    def _cart_filepath(self):
        """Return the filename used to persist the cart."""
        return Path(__file__).parent.parent / "cart.json"

    def clear_cart(self):
        """Clear the cart.json file."""
        try:
            with open(self._cart_filepath(), "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception as e:
            print(f"Failed to clear cart.json: {e}")

    def load_cart_items(self):
        """Load cart items from cart.json."""
        cart_items = {}
        cart_filepath = self._cart_filepath()
        if os.path.exists(cart_filepath):
            try:
                with open(cart_filepath, "r", encoding="utf-8") as f:
                    cart_data = json.load(f)
                    for category, items in cart_data.items():
                        for product_id, quantity in items.items():
                            pid = int(product_id)
                            qty = int(quantity)
                            if pid in cart_items:
                                cart_items[pid] += qty
                            else:
                                cart_items[pid] = qty
            except Exception as e:
                print(f"Failed to load cart.json: {e}")
                messagebox.showerror("Error", "Could not load cart data.")
        return cart_items

    def calculate_total_amount(self):
        """Calculate the total amount including tax from cart items."""
        self.total_amount = 0.0
        for product_id, quantity in self.cart_items.items():
            product = self.db.get_product_details(product_id)
            if product:
                price = round(float(product[1]), 2) if product[1] is not None else 0.0
                self.total_amount += price * quantity
        tax_rate = 0.06
        self.total_amount = round(self.total_amount * (1 + tax_rate), 2)

    def create_initial_transaction(self):
        """Create a transaction and deduct stock on page load."""
        try:
            self.db.conn.execute("BEGIN TRANSACTION")
            self.transaction_id = self.db.insert_transaction(round(self.total_amount, 2), self.cashier_id)
            if not self.transaction_id:
                self.db.conn.rollback()
                messagebox.showerror("Error", "Failed to save initial transaction to the database.")
                return
            success, low_stock_items = self.db.deduct_stock(self.cart_items)
            if not success:
                self.db.conn.rollback()
                messagebox.showerror("Error", "Failed to update product stock. Check stock quantities.")
                self.transaction_id = None
                return
            self.db.conn.commit()
            if low_stock_items:
                self.send_low_stock_email(low_stock_items)
            self.clear_cart()
        except Exception as e:
            self.db.conn.rollback()
            messagebox.showerror("Error", f"Error creating initial transaction: {str(e)}")
            self.transaction_id = None

    def send_low_stock_email(self, low_stock_items):
        """Send an email to all admin users with low stock alert."""
        if not low_stock_items:
            return

        sender_email = "zclau4321@gmail.com"
        sender_password = "raqc juni yrvu rmov"
        receiver_emails = self.db.get_admin_emails()

        if not receiver_emails:
            print("No admin emails found in the database.")
            return

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(receiver_emails)
        msg['Subject'] = "Low Stock Alert - InvenTrack Store"

        body = "Dear Manager,\n\nThe following products have low stock (below 5 units) after a recent transaction:\n\n"
        for item in low_stock_items:
            body += f"Product ID: {item['product_id']}, Name: {item['product_name']}, Stock: {item['stock_quantity']}\n"
        body += "\nPlease take appropriate action to restock these items.\n\nBest regards,\nInvenTrack System"
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_emails, msg.as_string())
            server.quit()
            print(f"Low stock email sent successfully to {', '.join(receiver_emails)}.")
        except Exception as e:
            print(f"Failed to send low stock email: {str(e)}")

    def display_receipt(self, parent_frame):
        """Display the receipt with stored TransactionID and cart items."""
        for widget in parent_frame.winfo_children():
            widget.destroy()

        scrollable_receipt = ctk.CTkScrollableFrame(
            parent_frame,
            fg_color="#f0f0f0",
            corner_radius=0,
            width=520,
            height=650
        )
        scrollable_receipt.place(x=0, y=0, relwidth=1, relheight=1)

        y_offset = 10
        ctk.CTkLabel(
            scrollable_receipt,
            text="InvenTrack Store",
            font=("Arial", 24, "bold"),
            text_color="black",
            width=520,
            anchor="center"
        ).pack(pady=(y_offset, 0), fill="x")
        y_offset += 40

        ctk.CTkLabel(
            scrollable_receipt,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            font=("Arial", 14),
            text_color="black",
            width=520,
            anchor="center"
        ).pack(pady=(5, 0), fill="x")
        y_offset += 25

        transaction_id = self.transaction_id if self.transaction_id else "N/A"
        ctk.CTkLabel(
            scrollable_receipt,
            text=f"Transaction ID: {transaction_id}",
            font=("Arial", 14),
            text_color="black",
            width=520,
            anchor="center"
        ).pack(pady=(5, 0), fill="x")
        y_offset += 25

        ctk.CTkLabel(
            scrollable_receipt,
            text="-" * 40,
            font=("Arial", 14),
            text_color="black",
            width=520,
            anchor="center"
        ).pack(pady=(5, 0), fill="x")
        y_offset += 25

        header_frame = ctk.CTkFrame(scrollable_receipt, fg_color="#f0f0f0", width=520, height=30)
        header_frame.pack(pady=(5, 0), fill="x")
        ctk.CTkLabel(
            header_frame,
            text="Item",
            font=("Arial", 14, "bold"),
            text_color="black",
            width=200,
            wraplength=200,
            anchor="w"
        ).place(x=10, y=0)
        ctk.CTkLabel(
            header_frame,
            text="Qty",
            font=("Arial", 14, "bold"),
            text_color="black",
            width=80,
            anchor="e"
        ).place(x=210, y=0)
        ctk.CTkLabel(
            header_frame,
            text="Price",
            font=("Arial", 14, "bold"),
            text_color="black",
            width=100,
            anchor="e"
        ).place(x=290, y=0)
        ctk.CTkLabel(
            header_frame,
            text="Total",
            font=("Arial", 14, "bold"),
            text_color="black",
            width=100,
            anchor="e"
        ).place(x=390, y=0)
        y_offset += 35

        subtotal = 0.0
        for product_id, quantity in self.cart_items.items():
            product = self.db.get_product_details(product_id)
            if product is None:
                print(f"Warning: Product ID {product_id} not found in database.")
                name = "Unknown Product"
                price = 0.0
            else:
                name = product[0][:22] + "..." if len(product[0]) > 22 else product[0]
                price = round(float(product[1]), 2) if product[1] is not None else 0.0
            total = round(price * quantity, 2)
            subtotal += total

            item_frame = ctk.CTkFrame(scrollable_receipt, fg_color="#f0f0f0", width=520, height=25)
            item_frame.pack(pady=(5, 0), fill="x")
            ctk.CTkLabel(
                item_frame,
                text=name,
                font=("Arial", 13),
                text_color="black",
                width=200,
                wraplength=200,
                anchor="w"
            ).place(x=10, y=0)
            ctk.CTkLabel(
                item_frame,
                text=str(quantity),
                font=("Arial", 13),
                text_color="black",
                width=80,
                anchor="e"
            ).place(x=210, y=0)
            ctk.CTkLabel(
                item_frame,
                text=f"RM {price:.2f}",
                font=("Arial", 13),
                text_color="black",
                width=100,
                anchor="e"
            ).place(x=290, y=0)
            ctk.CTkLabel(
                item_frame,
                text=f"RM {total:.2f}",
                font=("Arial", 13),
                text_color="black",
                width=100,
                anchor="e"
            ).place(x=390, y=0)
            y_offset += 30

        ctk.CTkLabel(
            scrollable_receipt,
            text="-" * 40,
            font=("Arial", 14),
            text_color="black",
            width=520,
            anchor="center"
        ).pack(pady=(5, 0), fill="x")
        y_offset += 25

        tax_rate = 0.06
        tax = round(subtotal * tax_rate, 2)
        total_with_tax = round(subtotal + tax, 2)
        ctk.CTkLabel(
            scrollable_receipt,
            text=f"Subtotal: RM {subtotal:.2f}",
            font=("Arial", 14),
            text_color="black",
            width=520,
            anchor="w"
        ).pack(pady=(5, 0), padx=10, anchor="w")
        y_offset += 25
        ctk.CTkLabel(
            scrollable_receipt,
            text=f"Tax (6%): RM {tax:.2f}",
            font=("Arial", 14),
            text_color="black",
            width=520,
            anchor="w"
        ).pack(pady=(5, 0), padx=10, anchor="w")
        y_offset += 25
        ctk.CTkLabel(
            scrollable_receipt,
            text=f"Grand Total: RM {total_with_tax:.2f}",
            font=("Arial", 16, "bold"),
            text_color="black",
            width=520,
            anchor="w"
        ).pack(pady=(5, 10), padx=10, anchor="w")
        self.total_amount = total_with_tax

    def clear_receipt_content(self):
        """Clear the receipt content inside receipt_frame, keeping the frame intact."""
        if hasattr(self, 'receipt_frame') and self.receipt_frame:
            for widget in self.receipt_frame.winfo_children():
                widget.destroy()
            ctk.CTkLabel(
                self.receipt_frame,
                text="Transaction Completed\nClick 'View Receipt' to see details",
                font=("Arial", 24),
                text_color="green",
                wraplength=480,
                anchor="center"
            ).place(relx=0.5, rely=0.5, anchor="center")

    def view_receipt(self):
        """Re-display the receipt in the receipt_frame."""
        if hasattr(self, 'receipt_frame') and self.receipt_frame:
            self.display_receipt(self.receipt_frame)
        else:
            messagebox.showerror("Error", "Receipt frame not available.")

    def show_card_payment_fields(self):
        """Display card payment fields and receipt."""
        ctk.CTkLabel(self.content_frame, text="Enter Card Details", font=("Arial", 50)).place(x=720, y=110)
        self.receipt_frame = ctk.CTkFrame(self.content_frame, width=520, height=650, fg_color="#f0f0f0", corner_radius=10)
        self.receipt_frame.place(x=110, y=40)
        if not self.payment_completed:
            self.display_receipt(self.receipt_frame)
        else:
            self.clear_receipt_content()
        self.credit_card_picture = ctk.CTkImage(Image.open(Path(__file__).parent / "pictures/credit card logo.png"), size=(500, 100))
        self.credit_card_picture_label = ctk.CTkLabel(master=self.content_frame, image=self.credit_card_picture, text="")
        self.credit_card_picture_label.place(x=700, y=10)
        self.cardholder_label = ctk.CTkLabel(self.content_frame, text="Cardholder's Name:", font=("Arial", 24), text_color="black", anchor="w", width=200, height=40)
        self.cardholder_label.place(x=720, y=170)
        self.cardholder_entry = ctk.CTkEntry(self.content_frame, placeholder_text="Full Name", font=("Arial", 20), width=450, height=50)
        self.cardholder_entry.place(x=720, y=210)
        self.card_label = ctk.CTkLabel(self.content_frame, text="Card Number:", font=("Arial", 24), text_color="black", anchor="w", width=100, height=40)
        self.card_label.place(x=720, y=270)
        self.card_number = ctk.CTkEntry(self.content_frame, placeholder_text="Card Number", font=("Arial", 20), width=450, height=50)
        self.card_number.place(x=720, y=310)
        self.expiry_date_label = ctk.CTkLabel(self.content_frame, text="Expiry Date:", font=("Arial", 24), text_color="black", anchor="w", width=100, height=40)
        self.expiry_date_label.place(x=720, y=370)
        self.expiry_date_entry = ctk.CTkEntry(self.content_frame, placeholder_text="MM/YY", font=("Arial", 20), width=210, height=50)
        self.expiry_date_entry.place(x=720, y=410)
        self.cvvcvc_label = ctk.CTkLabel(self.content_frame, text="CVV/CVC:", font=("Arial", 24), text_color="black", anchor="w", width=100, height=40)
        self.cvvcvc_label.place(x=960, y=370)
        self.cvv = ctk.CTkEntry(self.content_frame, placeholder_text="CVV/CVC", font=("Arial", 20), show="*", width=210, height=50)
        self.cvv.place(x=960, y=410)
        self.total_charge_label = ctk.CTkLabel(self.content_frame, text="Total Charge:", font=("Arial", 24), text_color="black", anchor="w", width=100, height=40)
        self.total_charge_label.place(x=720, y=470)
        self.total_charge_entry = ctk.CTkEntry(self.content_frame, placeholder_text=f"RM {self.total_amount:.2f}", font=("Arial", 20), width=450, height=50)
        self.total_charge_entry.place(x=720, y=510)
        self.pay_button = ctk.CTkButton(self.content_frame, text="Pay Now", font=("Arial", 25), text_color="white", fg_color="#2d3e50", command=self.process_card_payment, width=200, height=60)
        self.pay_button.place(x=850, y=600)
        self.status_label = ctk.CTkLabel(self.content_frame, text="", font=("Arial", 16), text_color="red", wraplength=400)
        self.status_label.place(x=720, y=560)
        self.view_receipt_button = ctk.CTkButton(
            self.content_frame,
            text="View Receipt",
            font=("Arial", 20),
            text_color="white",
            fg_color="#2d3e50",
            command=self.view_receipt,
            width=200,
            height=60,
            state="normal" if self.payment_completed else "disabled"
        )
        self.view_receipt_button.place(x=850, y=670)

    def show_touchngo_payment_fields(self):
        """Display Touch'N Go payment fields and receipt."""
        ctk.CTkLabel(self.content_frame, text="Touch'N Go E-Wallet Payment", font=("Arial", 50), wraplength=500).place(x=900, y=50)
        self.touch_n_go_logo = ctk.CTkImage(Image.open(Path(__file__).parent / "pictures/Touch_'n_Go_eWallet_logo.png"), size=(150, 150))
        self.touch_n_go_logo_label = ctk.CTkLabel(master=self.content_frame, image=self.touch_n_go_logo, text="")
        self.touch_n_go_logo_label.place(x=720, y=20)

        qr_content = "Receipt Details:\n"
        qr_content += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        qr_content += f"Transaction ID: {self.transaction_id if self.transaction_id else 'N/A'}\n"
        qr_content += "-" * 40 + "\n"
        qr_content += f"{'Item':<22} {'Qty':>5} {'Price':>10} {'Total':>10}\n"
        subtotal = 0.0
        for product_id, quantity in self.cart_items.items():
            product = self.db.get_product_details(product_id)
            if product is None:
                name = "Unknown Product"
                price = 0.0
            else:
                name = product[0][:22] + "..." if len(product[0]) > 22 else product[0]
                price = round(float(product[1]), 2) if product[1] is not None else 0.0
            total = round(price * quantity, 2)
            subtotal += total
            qr_content += f"{name:<22} {quantity:>5} {price:>10.2f} {total:>10.2f}\n"
        tax_rate = 0.06
        tax = round(subtotal * tax_rate, 2)
        total_with_tax = round(subtotal + tax, 2)
        qr_content += "-" * 40 + "\n"
        qr_content += f"Subtotal: RM {subtotal:.2f}\n"
        qr_content += f"Tax (6%): RM {tax:.2f}\n"
        qr_content += f"Grand Total: RM {total_with_tax:.2f}\n"
        qr_content += "Message: Go back to payment page to confirm payment"
        self.total_amount = total_with_tax

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((370, 370), Image.LANCZOS)
        qr_ctk_image = ctk.CTkImage(light_image=qr_img, size=(370, 370))
        self.image_refs.append(qr_ctk_image)
        qr_label = ctk.CTkLabel(self.content_frame, image=qr_ctk_image, text="")
        qr_label.place(x=860, y=180)

        self.receipt_frame = ctk.CTkFrame(self.content_frame, width=520, height=650, fg_color="#f0f0f0", corner_radius=10)
        self.receipt_frame.place(x=110, y=40)
        if not self.payment_completed:
            self.display_receipt(self.receipt_frame)
        else:
            self.clear_receipt_content()
        self.tng_status_label = ctk.CTkLabel(self.content_frame, text="", font=("Arial", 18))
        self.tng_status_label.place(x=920, y=550)

        def confirm_payment():
            if self.payment_completed:
                messagebox.showinfo("Payment Already Made", "You have already made your payment.")
                return
            try:
                self.db.conn.execute("BEGIN TRANSACTION")
                if not self.transaction_id:
                    self.tng_status_label.configure(text="No transaction ID available.", text_color="red")
                    messagebox.showerror("Error", "No transaction ID available. Please restart the transaction.")
                    self.db.conn.rollback()
                    return
                self.db.conn.commit()
                self.tng_status_label.configure(text="Payment confirmed. Thank you!", text_color="green")
                self.payment_completed = True
                self.clear_receipt_content()
                self.view_receipt_button.configure(state="normal")
            except Exception as e:
                self.db.conn.rollback()
                self.tng_status_label.configure(text="Payment processing failed.", text_color="red")
                messagebox.showerror("Error", f"Payment processing failed: {str(e)}")

        confirm_btn = ctk.CTkButton(self.content_frame, text="Confirm Payment", width=240, height=60, fg_color="#2d3e50", font=("Arial", 24), command=confirm_payment)
        confirm_btn.place(x=930, y=590)
        self.view_receipt_button = ctk.CTkButton(
            self.content_frame,
            text="View Receipt",
            font=("Arial", 24),
            text_color="white",
            fg_color="#2d3e50",
            command=self.view_receipt,
            width=240,
            height=60,
            state="normal" if self.payment_completed else "disabled"
        )
        self.view_receipt_button.place(x=930, y=660)

    def show_cash_payment_fields(self):
        """Display cash payment fields and receipt."""
        ctk.CTkLabel(self.content_frame, text="Cash Payment", font=("Arial", 36)).place(x=810, y=40)
        self.receipt_frame = ctk.CTkFrame(self.content_frame, width=520, height=650, fg_color="#f0f0f0", corner_radius=10)
        self.receipt_frame.place(x=110, y=40)
        if not self.payment_completed:
            self.display_receipt(self.receipt_frame)
        else:
            self.clear_receipt_content()
        self.cash_entry = ctk.CTkEntry(self.content_frame, placeholder_text=f"Enter Amount (RM {self.total_amount:.2f})", width=300, height=50, font=("Arial", 24))
        self.cash_entry.place(x=780, y=100)
        self.cash_status_label = ctk.CTkLabel(self.content_frame, text="", font=("Arial", 18))
        self.cash_status_label.place(x=780, y=155)

        def add_char(char):
            current = self.cash_entry.get()
            if char == ".":
                if "." in current:
                    return
                if current == "":
                    current = "0"
            self.cash_entry.delete(0, "end")
            self.cash_entry.insert(0, current + char)

        def clear_entry():
            self.cash_entry.delete(0, "end")

        def process_cash_payment():
            if self.payment_completed:
                messagebox.showinfo("Payment Already Made", "Payment has already been made.")
                return
            try:
                value = float(self.cash_entry.get())
                if value <= 0:
                    self.cash_status_label.configure(text="Amount must be greater than 0.", text_color="red")
                    return
                if abs(value - self.total_amount) > 0.01:
                    if value < self.total_amount:
                        remaining = self.total_amount - value
                        self.cash_status_label.configure(text=f"Insufficient payment. RM {remaining:.2f} needed.", text_color="orange")
                        return
                    else:
                        self.db.conn.execute("BEGIN TRANSACTION")
                        if not self.transaction_id:
                            self.cash_status_label.configure(text="No transaction ID available.", text_color="red")
                            messagebox.showerror("Error", "No transaction ID available. Please restart the transaction.")
                            self.db.conn.rollback()
                            return
                        self.db.conn.commit()
                        change = value - self.total_amount
                        self.cash_status_label.configure(
                            text=f"Payment received. Change: RM {change:.2f}" if change > 0 else "Exact amount received. Thank you!",
                            text_color="green"
                        )
                        self.payment_completed = True
                        self.clear_receipt_content()
                        self.view_receipt_button.configure(state="normal")
                else:
                    self.db.conn.execute("BEGIN TRANSACTION")
                    if not self.transaction_id:
                        self.cash_status_label.configure(text="No transaction ID available.", text_color="red")
                        messagebox.showerror("Error", "No transaction ID available. Please restart the transaction.")
                        self.db.conn.rollback()
                        return
                    self.db.conn.commit()
                    self.cash_status_label.configure(text="Exact amount received. Thank you!", text_color="green")
                    self.payment_completed = True
                    self.clear_receipt_content()
                    self.view_receipt_button.configure(state="normal")
            except ValueError:
                self.cash_status_label.configure(text="Please enter a valid number.", text_color="red")

        btn_x, btn_y = 800, 200
        buttons = ["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0"]
        for i, char in enumerate(buttons):
            row = i // 3
            col = i % 3
            if char == "0":
                row = 3
                col = 1
            elif char == ".":
                row = 3
                col = 0
            btn = ctk.CTkButton(self.content_frame, text=char, width=80, height=60, font=("Arial", 20), text_color="#fff",
                                border_color="black", border_width=1, fg_color="#2d3e50",
                                command=lambda c=char: add_char(c))
            btn.place(x=btn_x + col * 90, y=btn_y + row * 70)
        clear_btn = ctk.CTkButton(self.content_frame, text="Clear", width=80, height=60, font=("Arial", 20),
                                  text_color="#fff", border_color="black", border_width=1, fg_color="#2d3e50",
                                  command=clear_entry)
        clear_btn.place(x=btn_x + 2 * 90, y=btn_y + 3 * 70)
        pay_btn = ctk.CTkButton(self.content_frame, text="Pay", width=260, height=60, font=("Arial", 20),
                                text_color="#fff", border_color="black", border_width=1, fg_color="#2d3e50",
                                command=process_cash_payment)
        pay_btn.place(x=btn_x, y=btn_y + 4 * 70)
        self.view_receipt_button = ctk.CTkButton(
            self.content_frame,
            text="View Receipt",
            font=("Arial", 20),
            text_color="#fff",
            border_color="black",
            border_width=1,
            fg_color="#2d3e50",
            command=self.view_receipt,
            width=260,
            height=60,
            state="normal" if self.payment_completed else "disabled"
        )
        self.view_receipt_button.place(x=btn_x, y=btn_y + 5 * 70)

    def process_card_payment(self):
        """Process card payment using existing TransactionID."""
        if self.payment_completed:
            messagebox.showinfo("Payment Already Made", "You have already made your payment.")
            return

        self.status_label.configure(text="")
        cardholder_name = self.cardholder_entry.get().strip()
        card_number = self.card_number.get().replace(" ", "").strip()
        expiry = self.expiry_date_entry.get().strip()
        cvv = self.cvv.get().strip()
        total = self.total_charge_entry.get().replace("RM ", "").strip()

        if not all([cardholder_name, card_number, expiry, cvv, total]):
            self.status_label.configure(text="Please fill in all fields.", text_color="red")
            messagebox.showerror("Error", "All fields are required.")
            return

        if len(cardholder_name) < 2 or len(cardholder_name) > 50:
            self.status_label.configure(text="Name must be 2-50 characters.", text_color="red")
            messagebox.showerror("Error", "Cardholder's name must be between 2 and 50 characters.")
            return
        if not re.match(r'^[A-Za-z\s]+$', cardholder_name):
            self.status_label.configure(text="Name must contain only letters and spaces.", text_color="red")
            messagebox.showerror("Error", "Cardholder's name must contain only letters and spaces.")
            return
        if not card_number.isdigit() or len(card_number) != 16:
            self.status_label.configure(text="Card number must be 16 digits.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid 16-digit card number.")
            return
        if len(expiry) != 5 or expiry[2] != "/" or not expiry.replace("/", "").isdigit():
            self.status_label.configure(text="Expiry date must be in MM/YY format.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid expiry date in MM/YY format.")
            return
        try:
            month, year = map(int, expiry.split("/"))
            current_year = datetime.now().year % 100
            current_month = datetime.now().month
            if not (1 <= month <= 12) or year < current_year or (year == current_year and month < current_month):
                self.status_label.configure(text="Expiry date must be in the future.", text_color="red")
                messagebox.showerror("Error", "Please enter a valid expiry date in the future.")
                return
        except ValueError:
            self.status_label.configure(text="Invalid expiry date format.", text_color="red")
            messagebox.showerror("Error", "Invalid expiry date format.")
            return
        if not cvv.isdigit() or len(cvv) != 3:
            self.status_label.configure(text="CVV must be 3 digits.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid 3-digit CVV.")
            return
        try:
            total_value = float(total)
            if total_value <= 0:
                self.status_label.configure(text="Total must be greater than 0.", text_color="red")
                messagebox.showerror("Error", "Please enter a valid total amount.")
                return
            if abs(total_value - self.total_amount) > 0.01:
                self.status_label.configure(text=f"Total must be RM {self.total_amount:.2f}.", text_color="red")
                messagebox.showerror("Error", f"Total amount must match: RM {self.total_amount:.2f}.")
                return
        except ValueError:
            self.status_label.configure(text="Total must be a valid number.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid total amount.")
            return

        try:
            self.db.conn.execute("BEGIN TRANSACTION")
            if not self.transaction_id:
                self.status_label.configure(text="No transaction ID available.", text_color="red")
                messagebox.showerror("Error", "No transaction ID available. Please restart the transaction.")
                self.db.conn.rollback()
                return

            cardholder_name_hashed = bcrypt.hashpw(cardholder_name.encode(), bcrypt.gensalt())
            card_number_hashed = bcrypt.hashpw(card_number.encode(), bcrypt.gensalt())
            expiry_hashed = bcrypt.hashpw(expiry.encode(), bcrypt.gensalt())
            cvv_hashed = bcrypt.hashpw(cvv.encode(), bcrypt.gensalt())
            if not self.db.insert_card_payment(
                    self.transaction_id,
                    cardholder_name_hashed,
                    card_number_hashed,
                    expiry_hashed,
                    cvv_hashed
            ):
                self.db.conn.rollback()
                self.status_label.configure(text="Failed to save payment details.", text_color="red")
                messagebox.showerror("Error", "Failed to save payment details.")
                return

            self.db.conn.commit()
            self.status_label.configure(text="Payment confirmed. Thank you!", text_color="green")
            messagebox.showinfo("Success", "Payment processed successfully!")
            self.payment_completed = True
            self.clear_receipt_content()
            self.view_receipt_button.configure(state="normal")
        except Exception as e:
            self.db.conn.rollback()
            self.status_label.configure(text="Payment processing failed.", text_color="red")
            messagebox.showerror("Error", f"Payment processing failed: {str(e)}")

if __name__ == "__main__":
    app = PaymentPage(cashier_id=1)
    app.mainloop()
