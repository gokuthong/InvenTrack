from pathlib import Path
from tkinter import ttk, Tk, Canvas, Entry, Button, PhotoImage, StringVar, messagebox, Label, Toplevel
from PIL import Image, ImageTk
import sqlite3
import re
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import time
import threading
import subprocess


class RegistrationForm:
    def __init__(self, root):
        self.root = root
        width, height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}+0+0")
        self.root.configure(bg="#E1E1F0")

        # Paths
        self.output_path = Path(__file__).parent
        self.assets_path = Path(r"C:\Users\InvenTrack-main\InvenTrack\admin\assets\frame0")

        # Flags for show/hide password
        self.password_visible = False
        self.confirm_password_visible = False

        # Email verification state
        self.verification_code = None
        self.verification_window = None
        self.verification_sent_time = 0
        self.verification_data = None
        self.can_resend = True

        # Setup DB connection
        self.setup_database()

        # Load icons
        self.show_image = self.load_resized_image("show.png", size=(40, 40))
        self.hide_image = self.load_resized_image("hide.png", size=(28, 23))

        # Build UI
        self.build_ui()

    def setup_database(self):
        db_path = self.output_path.parent / "inventoryproject.db"
        if not db_path.exists():
            messagebox.showerror("Database Error", f"Database not found:\n{db_path}")
            raise FileNotFoundError(f"Database not found: {db_path}")
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS User (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT NOT NULL,
                Email TEXT NOT NULL UNIQUE,
                Password TEXT NOT NULL,
                Role TEXT NOT NULL,
                PhoneNumber TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def rel_asset(self, path: str) -> Path:
        return self.assets_path / Path(path)

    def load_resized_image(self, filename, size=(25, 25)):
        image_path = self.rel_asset(filename)
        img = Image.open(image_path).resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def build_ui(self):
        canvas = Canvas(
            self.root,
            height=1080,
            width=1920,
            bd=0,
            highlightthickness=0,
            relief="ridge"
        )
        canvas.place(x=0, y=0)
        self.canvas = canvas

        img_path = self.rel_asset("background.png")
        bg_pil_image = Image.open(img_path).resize((1920, 1080), Image.Resampling.LANCZOS)
        self.bg_image = ImageTk.PhotoImage(bg_pil_image)
        canvas.create_image(0, 0, image=self.bg_image, anchor="nw")

        self.whiteimage = PhotoImage(file=self.rel_asset("fillBackground.png"))
        canvas.create_image(960.0, 531.0, image=self.whiteimage)

        canvas.create_text(345.0, 94.0, anchor="nw", text="Create an account",
                           fill="#333333", font=("Poppins Medium", 42 * -1))
        canvas.create_text(349.0, 211.0, anchor="nw", text="Username",
                           fill="#666666", font=("Acumin Pro", 24 * -1))
        canvas.create_text(738.0, 211.0, anchor="nw", text="Phone Number",
                           fill="#666666", font=("Acumin Pro", 24 * -1))
        canvas.create_text(349.0, 344.0, anchor="nw", text="Email",
                           fill="#666666", font=("Acumin Pro", 24 * -1))
        canvas.create_text(349.0, 498.0, anchor="nw", text="Role",
                           fill="#666666", font=("Acumin Pro", 24 * -1))
        canvas.create_text(349.0, 621.0, anchor="nw", text="Password",
                           fill="#666666", font=("Acumin Pro", 24 * -1))

        # Create the static text part
        canvas.create_text(345.0, 942.0, anchor="nw", text="Already have an account? ",
                           fill="#111111", font=("Acumin Pro", 24 * -1), tags=("login_text",))

        # Create the clickable "Log in" part
        login_text_id = canvas.create_text(625.0, 942.0, anchor="nw", text="Log in",
                                           fill="black", font=("Acumin Pro", 24 * -1, "underline", "italic"),
                                           tags=("login_link",))

        # Add click binding to the "Log in" text
        canvas.tag_bind("login_link", "<Button-1>", lambda e: self.open_login_page())
        canvas.tag_bind("login_link", "<Enter>", lambda e: canvas.config(cursor="hand2"))
        canvas.tag_bind("login_link", "<Leave>", lambda e: canvas.config(cursor=""))

        canvas.create_text(789.0, 936.0, anchor="nw", text="Create an account",
                           fill="#FFFFFF", font=("Acumin Pro", 30 * -1))

        self.entry_image_1 = PhotoImage(file=self.rel_asset("entry_1.png"))
        canvas.create_image(528.0, 284.5, image=self.entry_image_1)
        self.username = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716",
                              highlightthickness=0, font=("Poppins", 17))
        self.username.place(x=355.0, y=255.0, width=346.0, height=58.0)

        self.entry_image_2 = PhotoImage(file=self.rel_asset("entry_1.png"))
        canvas.create_image(917.0, 284.5, image=self.entry_image_2)
        self.phone = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", highlightthickness=0, font=("Poppins", 17))
        self.phone.place(x=744.0, y=255.0, width=346.0, height=58.0)

        self.entry_image_3 = PhotoImage(file=self.rel_asset("entry_2.png"))
        canvas.create_image(722.5, 417.5, image=self.entry_image_3)
        self.email = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", highlightthickness=0, font=("Poppins", 17))
        self.email.place(x=355.0, y=388.0, width=735.0, height=58.0)

        # Email validation feedback label
        self.email_feedback = Label(self.root, text="", fg="red", bg="#F5F5F5", font=("Acumin Pro", 14))
        self.email_feedback.place(x=350, y=454, width=735, height=25)
        self.email.bind("<KeyRelease>", self.validate_email)

        # Create role display (fixed "Manager" text)
        self.role_frame = Canvas(self.root, bg="#FFFFFF", bd=0, highlightthickness=0)
        self.role_frame.place(x=345.0, y=539.0, width=760.0, height=63.0)
        self.role_frame.create_text(
            20, 31.5,
            anchor="w",
            text="Manager",
            fill="#000716",
            font=("Poppins", 17)
        )

        self.entry_image_5 = PhotoImage(file=self.rel_asset("entry_2.png"))
        canvas.create_image(722.5, 694.5, image=self.entry_image_5)
        self.password = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", show='*', highlightthickness=0,
                              font=("Poppins", 17))
        self.password.place(x=355.0, y=665.0, width=735.0, height=58.0)
        self.toggle_password_btn = Button(self.root, image=self.hide_image, bd=0, bg="#FFFFFF",
                                          activebackground="#FFFFFF",
                                          command=self.toggle_password_visibility)
        self.toggle_password_btn.place(x=1060, y=680, height=30, width=30)

        # Password validation feedback label
        self.password_feedback = Label(self.root, text="", fg="#666666", bg="#F5F5F5", font=("Acumin Pro", 14))
        self.password_feedback.place(x=350, y=729, width=735, height=25)
        self.password.bind("<KeyRelease>", self.validate_password)
        self.show_password_hint()  # Show initial hint

        self.entry_image_6 = PhotoImage(file=self.rel_asset("entry_2.png"))
        canvas.create_image(722.5, 848.5, image=self.entry_image_6)
        self.confirm_password = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", show='*',
                                      highlightthickness=0, font=("Poppins", 17))
        self.confirm_password.place(x=355.0, y=819.0, width=735.0, height=58.0)
        self.toggle_confirm_password_btn = Button(
            self.root, image=self.hide_image, bd=0, bg="#FFFFFF", activebackground="#FFFFFF",
            command=self.toggle_confirm_password_visibility
        )
        self.toggle_confirm_password_btn.place(x=1060, y=834, height=30, width=30)

        self.image_3 = PhotoImage(file=self.rel_asset("logo.png"))
        canvas.create_image(1445.0, 667.0, image=self.image_3)

        self.submit_img = PhotoImage(file=self.rel_asset("createButton.png"))
        self.submit_button = canvas.create_image(773.0, 923.0, anchor="nw", image=self.submit_img)
        canvas.tag_bind(self.submit_button, "<ButtonPress-1>", lambda event: self.on_submit_press())
        canvas.tag_bind(self.submit_button, "<ButtonRelease-1>", lambda event: self.on_submit_release())

    def open_login_page(self):
        """Open the login page by launching login.py"""
        try:
            # Get the path to login.py (in the same directory as this file)
            login_script = self.output_path / "login.py"

            if login_script.exists():
                # Use Popen to start the new process
                subprocess.Popen(['python', str(login_script)])
            else:
                messagebox.showerror("Error", "Login module not found!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open login page: {str(e)}")

    def on_submit_press(self):
        self.canvas.move(self.submit_button, 1, 1)

    def on_submit_release(self):
        self.canvas.move(self.submit_button, -1, -1)
        self.submit()

    def toggle_password_visibility(self):
        self.password_visible = not self.password_visible
        self.password.config(show='' if self.password_visible else '*')
        self.toggle_password_btn.config(image=self.show_image if self.password_visible else self.hide_image)

    def toggle_confirm_password_visibility(self):
        self.confirm_password_visible = not self.confirm_password_visible
        self.confirm_password.config(show='' if self.confirm_password_visible else '*')
        self.toggle_confirm_password_btn.config(
            image=self.show_image if self.confirm_password_visible else self.hide_image
        )

    def is_valid_email(self, email):
        """Validate that email is a valid Gmail address"""
        email = email.strip().lower()

        # Basic Gmail format check
        if not re.fullmatch(r"[a-z0-9][a-z0-9.]{4,28}[a-z0-9]@gmail\.com", email):
            return False

        # Additional Gmail-specific validations
        local_part = email.split('@')[0]
        if local_part.startswith('.') or local_part.endswith('.'):
            return False
        if '..' in local_part:
            return False

        return True

    def validate_email(self, event=None):
        email = self.email.get().strip()
        if not email:
            self.email_feedback.config(text="")
            return False

        if self.is_valid_email(email):
            self.email_feedback.config(text="✓ Valid Gmail address", fg="green")
            return True
        else:
            self.email_feedback.config(
                text="✗ Please enter a valid Gmail address (6-30 chars, letters/numbers/dots)",
                fg="red"
            )
            return False

    def validate_password(self, event=None):
        password = self.password.get()

        if not password:
            self.show_password_hint()
            return False

        valid = True
        messages = []

        if len(password) < 8:
            messages.append("at least 8 characters")
            valid = False

        if not re.search(r"[A-Za-z]", password):
            messages.append("at least one letter")
            valid = False

        if not re.search(r"[0-9]", password):
            messages.append("at least one number")
            valid = False

        if not re.search(r"[\W_]", password):
            messages.append("at least one symbol")
            valid = False

        if valid:
            self.password_feedback.config(text="✓ Strong password", fg="green")
        else:
            self.password_feedback.config(
                text=f"✗ Password must have: {', '.join(messages)}",
                fg="red"
            )

        return valid

    def show_password_hint(self):
        """Show the initial password hint"""
        self.password_feedback.config(
            text="Use 8 or more characters with a mix of letters, numbers & symbols",
            fg="#666666"  # Gray color for hint text
        )

    def passwords_match(self):
        """Check if password and confirm password match (without showing feedback)"""
        password = self.password.get()
        confirm = self.confirm_password.get()
        return password == confirm

    def generate_verification_code(self):
        """Generate a 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))

    def send_verification_email(self, email, code):
        """Send verification email with the code"""
        # Use environment variables for credentials
        sender_email = os.getenv("SENDER_EMAIL", "zclau4321@gmail.com")
        sender_password = os.getenv("SENDER_PASSWORD", "raqc juni yrvu rmov")

        if not sender_email or not sender_password:
            return False, "Email credentials not configured"

        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = "InvenTrack Account Verification"

            body = f"""
            <html>
            <body>
                <h2>InvenTrack Account Verification</h2>
                <p>Your verification code is:</p>
                <h1 style="font-size: 24px; color: #333333; padding: 10px; border: 1px solid #ccc; display: inline-block;">
                    {code}
                </h1>
                <p>This code will expire in 30 seconds.</p>  <!-- Changed from 10 minutes -->
                <p>If you didn't request this, please ignore this email.</p>
                <hr>
                <p style="color: #666666; font-size: 12px;">
                    InvenTrack Inventory Management System
                </p>
            </body>
            </html>
            """

            msg.attach(MIMEText(body, 'html'))

            # Send email using SMTP
            try:
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
            except Exception as e:
                return False, f"Connection to email server failed: {str(e)}"

            try:
                server.login(sender_email, sender_password)
            except Exception as e:
                server.quit()
                return False, f"Email login failed: {str(e)}"

            try:
                server.sendmail(sender_email, email, msg.as_string())
            except Exception as e:
                server.quit()
                return False, f"Email sending failed: {str(e)}"

            server.quit()
            return True, "Email sent successfully"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def show_verification_window(self):
        """Show verification code input window"""
        self.root.attributes('-disabled', True)

        self.verification_window = Toplevel(self.root)
        self.verification_window.title("Email Verification")
        self.verification_window.geometry("500x400")
        self.verification_window.configure(bg="#E1E1F0")
        self.verification_window.resizable(False, False)

        self.verification_window.attributes('-topmost', True)

        # Center the window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 500) // 2
        y = (screen_height - 400) // 2
        self.verification_window.geometry(f"500x400+{x}+{y}")

        # Window content
        Label(
            self.verification_window,
            text="Email Verification",
            font=("Poppins Medium", 24),
            bg="#E1E1F0"
        ).pack(pady=20)

        Label(
            self.verification_window,
            text=f"A verification code has been sent to:\n{self.verification_data['email']}\nThe code will expire in 30 seconds.",
            font=("Acumin Pro", 14),
            bg="#E1E1F0",
            justify="center"
        ).pack(pady=0)

        Label(
            self.verification_window,
            text="Please enter the code below:",
            font=("Acumin Pro", 14),
            bg="#E1E1F0"
        ).pack(pady=3)

        # Verification code entry
        self.code_entry = Entry(
            self.verification_window,
            font=("Poppins", 20),
            justify="center",
            width=10
        )
        self.code_entry.pack(pady=10)
        self.code_entry.focus_set()

        # Submit button
        Button(
            self.verification_window,
            text="Verify Account",
            font=("Acumin Pro", 14),
            bg="#4CAF50",
            fg="white",
            width=15,
            command=self.verify_code
        ).pack(pady=20)

        # Resend button and timer
        self.resend_button = Button(
            self.verification_window,
            text="Resend Code",
            font=("Acumin Pro", 12),
            state="disabled",
            command=self.resend_verification
        )
        self.resend_button.pack()

        # Countdown label
        self.countdown_label = Label(
            self.verification_window,
            text="Resend available in: 0:30",
            font=("Acumin Pro", 12),
            bg="#E1E1F0",
            fg="#666666"
        )
        self.countdown_label.pack(pady=5)

        # Start countdown timer
        self.verification_sent_time = time.time()
        self.update_resend_timer()

        # Handle window close
        self.verification_window.protocol("WM_DELETE_WINDOW", self.close_verification_window)

    def update_resend_timer(self):
        """Update the resend countdown timer"""
        if not self.verification_window or not self.verification_window.winfo_exists():
            return

        elapsed = time.time() - self.verification_sent_time
        remaining = max(30 - int(elapsed), 0)  # Changed to 30 seconds

        if remaining <= 0:
            self.countdown_label.config(text="You can now resend the code")
            self.resend_button.config(state="normal")
            self.can_resend = True
            return

        self.countdown_label.config(text=f"Resend available in: {remaining:02d}")
        self.verification_window.after(1000, self.update_resend_timer)

    def resend_verification(self):
        """Resend verification email"""
        if not self.can_resend:
            return

        self.can_resend = False
        self.resend_button.config(state="disabled")

        # Generate new code
        self.verification_code = self.generate_verification_code()

        # Try to send email in a separate thread
        threading.Thread(target=self.send_verification_in_thread, args=(True,), daemon=True).start()

    def send_verification_in_thread(self, is_resend=False):
        """Send verification email in a background thread"""
        try:
            success, message = self.send_verification_email(
                self.verification_data['email'],
                self.verification_code
            )

            if success:
                self.verification_sent_time = time.time()
                if is_resend:
                    # Removed the popup message here
                    # Restart the timer and bring window to front
                    self.root.after(0, self.update_resend_timer)
                    if self.verification_window:
                        self.root.after(0, lambda: self.verification_window.lift())
                        self.root.after(0, lambda: self.verification_window.focus_force())
                else:
                    self.root.after(0, self.show_verification_window)
            else:
                error_msg = f"Failed to send verification email: {message}\n\nPlease check:"

                if is_resend:
                    self.root.after(0, lambda: messagebox.showerror("Email Error", error_msg))
                    self.root.after(0, lambda: self.resend_button.config(state="normal"))
                    self.can_resend = True
                    if self.verification_window:
                        self.root.after(0, lambda: self.verification_window.lift())
                else:
                    self.root.after(0, lambda: messagebox.showerror("Email Error", error_msg))
                    self.root.after(0, self.close_verification_window)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if is_resend:
                self.root.after(0, lambda: messagebox.showerror("Email Error", error_msg))
                self.root.after(0, lambda: self.resend_button.config(state="normal"))
                self.can_resend = True
                if self.verification_window:
                    self.root.after(0, lambda: self.verification_window.lift())
            else:
                self.root.after(0, lambda: messagebox.showerror("Email Error", error_msg))
                self.root.after(0, self.close_verification_window)

    def verify_code(self):
        """Verify the entered code"""
        entered_code = self.code_entry.get().strip()

        if not entered_code:
            messagebox.showerror("Error", "Please enter the verification code", parent=self.verification_window)
            return

        if entered_code == self.verification_code:
            # First check if email already exists
            self.cursor.execute("SELECT Email FROM User WHERE Email = ?", (self.verification_data['email'],))
            if self.cursor.fetchone():
                # Create a new toplevel for the error message
                error_window = Toplevel(self.verification_window)
                error_window.title("Error")
                error_window.geometry("300x120")
                error_window.resizable(False, False)
                error_window.transient(self.verification_window)  # Set as child of verification window
                error_window.grab_set()  # Make it modal

                # Center the error window
                screen_width = error_window.winfo_screenwidth()
                screen_height = error_window.winfo_screenheight()
                x = (screen_width - 300) // 2
                y = (screen_height - 120) // 2
                error_window.geometry(f"300x120+{x}+{y}")

                Label(error_window, text="This email is already registered.",
                      font=("Acumin Pro", 12), pady=20).pack()
                Button(error_window, text="OK", command=error_window.destroy,
                       width=10).pack(pady=10)

                # Bring to front and focus
                error_window.lift()
                error_window.focus_force()
                return

            # Code is correct and email is unique, create account
            try:
                self.cursor.execute(
                    "INSERT INTO User (Username, Email, Password, Role, PhoneNumber) VALUES (?, ?, ?, ?, ?)",
                    (
                        self.verification_data['username'],
                        self.verification_data['email'],
                        self.verification_data['password'],
                        "Manager",
                        self.verification_data['phone']
                    )
                )
                self.conn.commit()
                self.close_verification_window()
                self.clear_fields()
                messagebox.showinfo("Success", "Manager account created successfully.")

                # Schedule the window destruction and login page opening
                self.root.after(100, lambda: [self.root.destroy(), self.open_login_page()])

            except sqlite3.IntegrityError:
                # This should theoretically never happen since we checked first
                messagebox.showerror("Error", "This email is already registered.", parent=self.verification_window)
                self.close_verification_window()
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}",
                                     parent=self.verification_window)
                self.close_verification_window()
        else:
            messagebox.showerror("Error", "Invalid verification code. Please try again.",
                                 parent=self.verification_window)

    def close_verification_window(self):
        """Close verification window and re-enable main window"""
        if self.verification_window:
            self.verification_window.destroy()
            self.verification_window = None
        self.root.attributes('-disabled', False)
        self.verification_data = None
        self.verification_code = None

    def submit(self):
        # Update validation states
        email_valid = self.validate_email()
        password_valid = self.validate_password()

        username = self.username.get().strip()
        phone = self.phone.get().strip()
        email = self.email.get().strip().lower()
        password = self.password.get()
        confirm_password = self.confirm_password.get()

        # Check for empty fields
        if not username or not phone or not email or not password or not confirm_password:
            messagebox.showerror("Error", "All fields are required.")
            return

        # Check if email and password validations passed
        if not all([email_valid, password_valid]):
            messagebox.showerror("Validation Error", "Please fix the validation errors highlighted in red.")
            return

        # Check if passwords match (without showing feedback)
        if not self.passwords_match():
            messagebox.showerror("Error", "Passwords do not match.")
            return

        # Store user data for verification
        self.verification_data = {
            'username': username,
            'phone': phone,
            'email': email,
            'password': password
        }

        # Generate verification code
        self.verification_code = self.generate_verification_code()

        # Send verification email in a background thread
        threading.Thread(target=self.send_verification_in_thread, daemon=True).start()

        # Show loading message
        messagebox.showinfo("Verification Sent",
                            "A verification code has been sent to your email. Please check your inbox.")

    def clear_fields(self):
        self.username.delete(0, "end")
        self.phone.delete(0, "end")
        self.email.delete(0, "end")
        self.password.delete(0, "end")
        self.confirm_password.delete(0, "end")

        # Clear validation messages and show hints
        self.email_feedback.config(text="")
        self.show_password_hint()


if __name__ == "__main__":
    window = Tk()
    app = RegistrationForm(window)
    window.resizable(False, False)
    window.mainloop()
