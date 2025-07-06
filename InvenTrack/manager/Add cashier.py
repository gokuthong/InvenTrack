import customtkinter as ctk
import sqlite3
from PIL import Image
from tkinter import messagebox
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class AddCashierPageDatabase:
    def __init__(self, db_file="inventoryproject.db"):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS User (
                    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT NOT NULL UNIQUE,
                    Email TEXT NOT NULL UNIQUE,
                    Password TEXT NOT NULL,
                    Role TEXT DEFAULT 'Cashier',
                    PhoneNumber TEXT NOT NULL
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")

    def add_cashier(self, username, email, password, phone_number):
        try:
            self.cursor.execute("""
                INSERT INTO User (Username, Email, Password, Role, PhoneNumber)
                VALUES (?, ?, ?, 'Cashier', ?)
            """, (username, email, password, phone_number))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database insert error: {e}")
            return False

    def is_duplicate(self, username, email, phone_number):
        self.cursor.execute("SELECT * FROM User WHERE Username=? OR Email=? OR PhoneNumber=?",
                            (username, email, phone_number))
        return self.cursor.fetchone() is not None

    def close(self):
        self.conn.close()

class AddCashierPage(ctk.CTk):
    def __init__(self, previous_window=None):
        super().__init__()
        self.db = AddCashierPageDatabase()
        self.previous_window = previous_window
        self.title("Add Cashier")
        self.geometry("1920x1080")
        self.configure(fg_color="white")
        self.resizable(True, True)

        self.image_refs = []
        placeholder_img = Image.new('RGB', (260, 155), color='#cccccc')
        self.default_image = ctk.CTkImage(placeholder_img, size=(260, 155))
        self.image_refs.append(self.default_image)

        try:
            pil_bg = Image.open("cashier/pictures/background.png")
            ctk_bg = ctk.CTkImage(pil_bg, size=(1920, 1080))
            self.image_refs.append(ctk_bg)
            bg_label = ctk.CTkLabel(self, image=ctk_bg, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Background load error: {e}")

        self.sidebar_expanded = False
        self.sidebar_width = 180
        self.current_page = "Add Cashier"

        self._create_header()
        self._create_sidebar()
        self._create_toggle_button()
        self._create_top_buttons()
        self.create_main_add_cashier_frame()

    def _create_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="#2d3e50", bg_color="#2d3e50", width=1920, height=55)
        self.header_frame.place(x=0, y=0)

        self.title_label = ctk.CTkLabel(self.header_frame, text=self.current_page, font=("Segoe UI", 25), text_color="#fff")
        self.title_label.place(x=120, y=10)

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color="#2d3e50", corner_radius=0, width=self.sidebar_width, height=1080,
                                    border_width=0, border_color="#ddd")
        ctk.CTkLabel(self.sidebar, text="InvenTrack", font=("Segoe UI", 28, "bold"), text_color="#fff").place(x=20,
                                                                                                              y=20)
        self.sidebar_buttons = {}
        y = 80
        for name in ["Add Cashier"]:
            is_current = (name == self.current_page)
            btn = ctk.CTkButton(self.sidebar, text=name, width=160, height=50, corner_radius=10,
                                fg_color="#34495E" if is_current else "transparent",
                                hover_color="#3E5870" if is_current else "#4A6374",
                                text_color="#FFFFFF", font=("Segoe UI", 18.5), command=self.show_add_cashier)
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
            self.form_frame.place_configure(x=300 + x_off)
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
            self.form_frame.place_configure(x=300 + x_off)
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

    def show_add_cashier(self):
        self.current_page = "Add Cashier"
        self.title_label.configure(text=self.current_page)
        for name, btn in self.sidebar_buttons.items():
            if name == "Add Cashier":
                btn.configure(fg_color="#34495E", hover_color="#3E5870")
            else:
                btn.configure(fg_color="transparent", hover_color="#4A6374")
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.form_frame.place(x=300 + x_off, y=80)
        if self.sidebar_expanded:
            self.toggle_sidebar()
        else:
            self.update_button_positions()

    def toggle_password_visibility(self):
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.password_entry.configure(show="")
            self.toggle_password_btn.configure(text="🙈 Hide")
        else:
            self.password_entry.configure(show="*")
            self.toggle_password_btn.configure(text="👁 Show")

    def create_main_add_cashier_frame(self):
        # Form frame with increased size to better display contents
        self.form_frame = ctk.CTkFrame(self, fg_color="#fff", bg_color="#fff", width=1000, height=700)  # Increased width to 800, height to 700
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.form_frame.place(x=300 + x_off, y=80)

        ctk.CTkLabel(self.form_frame, text="Add New Cashier", font=("Trebuchet MS", 50), text_color="light blue").place(x=300, y=50)  # Centered title

        # Username
        self.username_label = ctk.CTkLabel(self.form_frame, text="Username:", font=("Arial", 30), text_color="#000")
        self.username_label.place(x=100, y=150)
        self.username_entry = ctk.CTkEntry(self.form_frame, font=("Arial", 30), width=500, height=50)  # Increased width
        self.username_entry.place(x=340, y=145)

        # Email
        self.email_label = ctk.CTkLabel(self.form_frame, text="Email:", font=("Arial", 30), text_color="#000")
        self.email_label.place(x=100, y=230)
        self.email_entry = ctk.CTkEntry(self.form_frame, font=("Arial", 30), width=500, height=50)  # Increased width
        self.email_entry.place(x=340, y=225)

        # Password
        self.password_label = ctk.CTkLabel(self.form_frame, text="Password:", font=("Arial", 30), text_color="#000")
        self.password_label.place(x=100, y=310)
        self.password_entry = ctk.CTkEntry(self.form_frame, font=("Arial", 30), width=390, height=50, show="*")  # Increased width
        self.password_entry.place(x=340, y=305)

        self.password_visible = False

        self.toggle_password_btn = ctk.CTkButton(
            self.form_frame,
            text="👁 Show",
            font=("Arial", 20),
            width=100,
            height=40,
            command=self.toggle_password_visibility
        )
        self.toggle_password_btn.place(x=740, y=310)

        # Phone Number
        self.phone_label = ctk.CTkLabel(self.form_frame, text="Phone Number:", font=("Arial", 30), text_color="#000")
        self.phone_label.place(x=100, y=390)
        self.phone_entry = ctk.CTkEntry(self.form_frame, font=("Arial", 30), width=500, height=50)  # Increased width
        self.phone_entry.place(x=340, y=385)

        button_y = 500
        self.add_button = ctk.CTkButton(self.form_frame, text="Add Cashier", font=("Arial", 22), width=180, height=50,
                                        command=self.add_cashier)
        self.add_button.place(x=220, y=button_y)

        self.clear_button = ctk.CTkButton(self.form_frame, text="Clear", font=("Arial", 22), width=180, height=50,
                                          command=self.clear_fields)
        self.clear_button.place(x=420, y=button_y)

        self.back_button = ctk.CTkButton(self.form_frame, text="Back", font=("Arial", 22), width=180, height=50,
                                         command=self.back)
        self.back_button.place(x=620, y=button_y)

    def add_cashier(self):
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        phone_number = self.phone_entry.get().strip()

        # Duplicate checks
        if self.db.is_duplicate("Username", username):
            messagebox.showerror("Error", "Username already exists.")
            return
        if self.db.is_duplicate("Email", email):
            messagebox.showerror("Error", "Email already exists.")
            return
        if self.db.is_duplicate("PhoneNumber", phone_number):
            messagebox.showerror("Error", "Phone number already exists.")
            return

        # Validation checks
        if not username:
            messagebox.showerror("Error", "Username cannot be empty.")
            return
        if len(username) < 3:
            messagebox.showerror("Error", "Username must be at least 3 characters long.")
            return
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            messagebox.showerror("Error", "Username can only contain letters, numbers, and underscores.")
            return

        if not email:
            messagebox.showerror("Error", "Email cannot be empty.")
            return
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            messagebox.showerror("Error", "Invalid email format.")
            return

        if not password:
            messagebox.showerror("Error", "Password cannot be empty.")
            return
        if len(password) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters long.")
            return
        if not re.search(r"[A-Za-z]", password):
            messagebox.showerror("Error", "Password must include at least one letter.")
            return
        if not re.search(r"[0-9]", password):
            messagebox.showerror("Error", "Password must include at least one number.")
            return
        if not re.search(r"[\W_]", password):
            messagebox.showerror("Error", "Password must include at least one symbol (e.g., !@#$%).")
            return

        if not phone_number:
            messagebox.showerror("Error", "Phone number cannot be empty.")
            return
        if not re.match(r"^\+?\d{10,15}$", phone_number):
            messagebox.showerror("Error", "Invalid phone number format. Use 10-15 digits, optionally starting with +.")
            return

        if self.db.add_cashier(username, email, password, phone_number):
            messagebox.showinfo("Success", "Cashier added successfully!")
            self.send_verification_email(email, username)
            self.username_entry.delete(0, 'end')
            self.email_entry.delete(0, 'end')
            self.password_entry.delete(0, 'end')
            self.phone_entry.delete(0, 'end')
        else:
            messagebox.showerror("Error", "Failed to add cashier. Username or email may already exist.")

    def clear_fields(self):
        self.username_entry.delete(0, 'end')
        self.email_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.phone_entry.delete(0, 'end')
        if not self.password_visible:
            self.password_entry.configure(show="*")  # ensure it's reset

    def send_verification_email(self, recipient_email, username):
        sender_email = "youremail@example.com"
        sender_password = "your_app_password"

        message = MIMEMultipart("alternative")
        message["Subject"] = "Cashier Account Verification"
        message["From"] = sender_email
        message["To"] = recipient_email

        text = f"""\
    Hi {username},

    Your account has been successfully created as a cashier.
    This is a confirmation email from InvenTrack.

    Thank you,
    InvenTrack Team
    """
        html = f"""\
    <html>
      <body>
        <p>Hi {username},<br><br>
           Your account has been <b>successfully created</b> as a cashier.<br><br>
           This is a confirmation email from <b>InvenTrack</b>.<br><br>
           Thank you,<br>
           <b>InvenTrack Team</b>
        </p>
      </body>
    </html>
    """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            server.quit()
            print("Verification email sent successfully.")
        except Exception as e:
            print(f"Failed to send verification email: {e}")

    def logout(self):
        self.db.close()
        self.destroy()

    def back(self):
        self.db.close()
        self.destroy()
        if self.previous_window:
            self.previous_window.deiconify()

    def __del__(self):
        self.db.close()

if __name__ == "__main__":
    app = AddCashierPage()
    app.mainloop()
