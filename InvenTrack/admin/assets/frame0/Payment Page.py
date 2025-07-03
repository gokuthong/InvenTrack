from PIL import Image
import customtkinter as ctk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import bcrypt
import re
import qrcode
import io

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class PaymentPageDatabase:
    def __init__(self, db_file="inventoryproject.db"):
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
                FOREIGN KEY (TransactionID) REFERENCES TransactionDetail(TransactionID)
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

    def get_latest_transaction(self):
        self.cursor.execute("SELECT TransactionID, TotalAmount FROM `Transaction` ORDER BY DateTime DESC LIMIT 1")
        return self.cursor.fetchone()

    def get_product_details(self, product_id):
        self.cursor.execute("SELECT productName, price FROM product WHERE productID = ?", (product_id,))
        return self.cursor.fetchone()

    def close(self):
        self.conn.close()

class PaymentPage(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = PaymentPageDatabase()
        self.title("Payment Page")
        self.geometry("1920x1080")
        self.configure(fg_color="white")
        self.resizable(True, True)

        self.payment_completed = False  # Track if payment has been made
        self.view_receipt_button = None  # Initialize view_receipt_button

        self.image_refs = []
        placeholder_img = Image.new('RGB', (260, 155), color='#cccccc')
        self.default_image = ctk.CTkImage(placeholder_img, size=(260, 155))
        self.image_refs.append(self.default_image)

        try:
            pil_bg = Image.open("Pictures/background.png")
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

        self.cart_items = {"3": 3, "2": 1, "1": 1, "5": 1, "6": 1, "7": 1, "8": 1}
        self.total_amount = 0.0

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
            self.sidebar.place(x=0, y=0)
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

    def display_receipt(self, parent_frame):
        for widget in parent_frame.winfo_children():
            widget.destroy()

        # Create a scrollable frame inside the parent_frame
        scrollable_receipt = ctk.CTkScrollableFrame(
            parent_frame,
            fg_color="#f0f0f0",
            corner_radius=0,
            width=520,
            height=650
        )
        scrollable_receipt.place(x=0, y=0, relwidth=1, relheight=1)

        y_offset = 10
        # Header labels
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

        transaction = self.db.get_latest_transaction()
        transaction_id = transaction[1001] if transaction else "N/A"
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

        # Item header
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

        # Items
        self.total_amount = 0.0
        for product_id, quantity in self.cart_items.items():
            product = self.db.get_product_details(product_id)
            if product is None:
                print(f"Warning: Product ID {product_id} not found in database.")
                name = "Unknown Product"
                price = 0.0
            else:
                name = product[0][:22] + "..." if len(product[0]) > 22 else product[0]
                price = float(product[1]) if product[1] is not None else 0.0
                if price <= 0:
                    print(f"Warning: Product ID {product_id} has invalid price: {product[1]}")
            total = price * quantity
            self.total_amount += total

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

        # Footer
        ctk.CTkLabel(
            scrollable_receipt,
            text="-" * 40,
            font=("Arial", 14),
            text_color="black",
            width=520,
            anchor="center"
        ).pack(pady=(5, 0), fill="x")
        y_offset += 25
        ctk.CTkLabel(
            scrollable_receipt,
            text=f"Grand Total: RM {self.total_amount:.2f}",
            font=("Arial", 16, "bold"),
            text_color="black",
            width=520,
            anchor="w"
        ).pack(pady=(5, 10), padx=10, anchor="w")

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
        ctk.CTkLabel(self.content_frame, text="Enter Card Details", font=("Arial", 50)).place(x=720, y=110)
        self.receipt_frame = ctk.CTkFrame(self.content_frame, width=520, height=650, fg_color="#f0f0f0", corner_radius=10)
        self.receipt_frame.place(x=110, y=40)
        if not self.payment_completed:
            self.display_receipt(self.receipt_frame)
        else:
            self.clear_receipt_content()
        self.credit_card_picture = ctk.CTkImage(Image.open("Pictures/credit card logo.png"), size=(500, 100))
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
        ctk.CTkLabel(self.content_frame, text="Touch'N Go E-Wallet Payment", font=("Arial", 50), wraplength=500).place(x=900, y=50)
        self.touch_n_go_logo = ctk.CTkImage(Image.open("Pictures/Touch_'n_Go_eWallet_logo.png"), size=(150, 150))
        self.touch_n_go_logo_label = ctk.CTkLabel(master=self.content_frame, image=self.touch_n_go_logo, text="")
        self.touch_n_go_logo_label.place(x=720, y=20)

        # Generate QR code content
        qr_content = "Receipt Details:\n"
        qr_content += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        qr_content += f"Transaction ID: {self.db.get_latest_transaction()[0] if self.db.get_latest_transaction() else 'N/A'}\n"
        qr_content += "-" * 40 + "\n"
        qr_content += f"{'Item':<22} {'Qty':>5} {'Price':>10} {'Total':>10}\n"
        for product_id, quantity in self.cart_items.items():
            product = self.db.get_product_details(product_id)
            if product is None:
                name = "Unknown Product"
                price = 0.0
            else:
                name = product[0][:22] + "..." if len(product[0]) > 22 else product[0]
                price = float(product[1]) if product[1] is not None else 0.0
            total = price * quantity
            qr_content += f"{name:<22} {quantity:>5} {price:>10.2f} {total:>10.2f}\n"
        qr_content += "-" * 40 + "\n"
        qr_content += f"Grand Total: RM {self.total_amount:.2f}\n"
        qr_content += "Message: Go back to payment page to confirm payment"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Convert QR code image to CTkImage
        qr_img = qr_img.resize((370, 370), Image.LANCZOS)  # Resize to match original placeholder size
        qr_ctk_image = ctk.CTkImage(light_image=qr_img, size=(370, 370))
        self.image_refs.append(qr_ctk_image)  # Store reference to prevent garbage collection

        # Display QR code
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
            self.tng_status_label.configure(text="Payment confirmed. Thank you!", text_color="green")
            self.payment_completed = True
            self.clear_receipt_content()
            self.view_receipt_button.configure(state="normal")

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
                elif value < self.total_amount:
                    remaining = self.total_amount - value
                    self.cash_status_label.configure(text=f"Insufficient payment. RM {remaining:.2f} needed.", text_color="orange")
                else:
                    change = value - self.total_amount
                    self.cash_status_label.configure(
                        text=f"Payment received. Change: RM {change:.2f}" if change > 0 else "Exact amount received. Thank you!",
                        text_color="green"
                    )
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
            messagebox.showerror("Error", "All fields are required: cardholder's name, card number, expiry date, CVV, and total.")
            return

        if len(cardholder_name) < 2 or len(cardholder_name) > 50:
            self.status_label.configure(text="Name must be 2-50 characters.", text_color="red")
            messagebox.showerror("Error", "Cardholder's name must be between 2 and 50 characters.")
            return
        if not re.match(r'^[A-Za-z\s]+$', cardholder_name):
            self.status_label.configure(text="Name must contain only letters and spaces.", text_color="red")
            messagebox.showerror("Error", "Cardholder's name must contain only letters and spaces.")
            return

        if not card_number.isdigit():
            self.status_label.configure(text="Card number must contain only digits.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid card number with only digits.")
            return
        if len(card_number) != 16:
            self.status_label.configure(text="Card number must be 16 digits.", text_color="red")
            messagebox.showerror("Error", "Please enter a 16-digit card number.")
            return

        if len(expiry) != 5 or expiry[2] != "/" or not expiry.replace("/", "").isdigit():
            self.status_label.configure(text="Expiry date must be in MM/YY format.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid expiry date in MM/YY format (e.g., 12/25).")
            return
        try:
            month, year = map(int, expiry.split("/"))
            current_year = datetime.now().year % 100
            current_month = datetime.now().month
            if not (1 <= month <= 12) or year < current_year or (year == current_year and month < current_month):
                self.status_label.configure(text="Expiry date must be in the future.", text_color="red")
                messagebox.showerror("Error", "Please enter a valid expiry date that is in the future.")
                return
        except ValueError:
            self.status_label.configure(text="Invalid expiry date format.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid expiry date in MM/YY format.")
            return

        if not cvv.isdigit():
            self.status_label.configure(text="CVV must contain only digits.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid CVV with only digits.")
            return
        if len(cvv) != 3:
            self.status_label.configure(text="CVV must be 3 digits.", text_color="red")
            messagebox.showerror("Error", "Please enter a 3-digit CVV.")
            return

        try:
            total_value = float(total)
            if total_value <= 0:
                self.status_label.configure(text="Total must be greater than 0.", text_color="red")
                messagebox.showerror("Error", "Please enter a valid total amount greater than 0.")
                return
            if abs(total_value - self.total_amount) > 0.01:
                self.status_label.configure(text=f"Total must be RM {self.total_amount:.2f}.", text_color="red")
                messagebox.showerror("Error", f"Total amount must match the receipt total: RM {self.total_amount:.2f}.")
                return
        except ValueError:
            self.status_label.configure(text="Total must be a valid number.", text_color="red")
            messagebox.showerror("Error", "Please enter a valid total amount as a number.")
            return

        try:
            cardholder_name_hashed = bcrypt.hashpw(cardholder_name.encode(), bcrypt.gensalt())
            card_number_hashed = bcrypt.hashpw(card_number.encode(), bcrypt.gensalt())
            expiry_hashed = bcrypt.hashpw(expiry.encode(), bcrypt.gensalt())
            cvv_hashed = bcrypt.hashpw(cvv.encode(), bcrypt.gensalt())
            transaction = self.db.get_latest_transaction()
            if not transaction:
                self.status_label.configure(text="No transaction found.", text_color="red")
                messagebox.showerror("Error", "No transaction found in the database.")
                return
            transaction_id = transaction[0]
            if not self.db.insert_card_payment(
                    transaction_id,
                    cardholder_name_hashed,
                    card_number_hashed,
                    expiry_hashed,
                    cvv_hashed
            ):
                self.status_label.configure(text="Failed to save payment details.", text_color="red")
                messagebox.showerror("Error", "Failed to save payment details to the database.")
                return
            self.status_label.configure(text="Payment confirmed. Thank you!", text_color="green")
            messagebox.showinfo("Success", "Payment processed successfully!")
            self.payment_completed = True
            self.clear_receipt_content()
            self.view_receipt_button.configure(state="normal")
        except Exception as e:
            self.status_label.configure(text="Payment processing failed.", text_color="red")
            messagebox.showerror("Error", f"An error occurred during payment processing: {str(e)}")

if __name__ == "__main__":
    app = PaymentPage()
    app.mainloop()