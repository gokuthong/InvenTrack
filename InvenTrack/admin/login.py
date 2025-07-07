import json
from pathlib import Path
from tkinter import Tk, Canvas, Entry, Button, PhotoImage, messagebox
from PIL import Image, ImageTk
import sqlite3
import os

# Import RegistrationForm from your register file
from register import RegistrationForm


class LoginForm:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="#E1E1F0")

        self.output_path = Path(__file__).parent
        self.assets_path = Path(r"C:\InvenTrack-main\InvenTrack\admin\assets\frame0")

        self.password_visible = False
        self.setup_database()

        self.show_image = self.load_resized_image("show.png", size=(40, 40))
        self.hide_image = self.load_resized_image("hide.png", size=(28, 23))

        self.build_ui()

    def setup_database(self):
        db_path = self.output_path.parent / "inventoryproject.db"
        if not db_path.exists():
            messagebox.showerror("Database Error", f"Database not found:\n{db_path}")
            raise FileNotFoundError(f"Database not found: {db_path}")
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()

    def rel_asset(self, path: str) -> Path:
        return self.assets_path / Path(path)

    def load_resized_image(self, filename, size=(25, 25)):
        image_path = self.rel_asset(filename)
        img = Image.open(image_path).resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def build_ui(self):
        self.canvas = Canvas(self.root, width=1920, height=1080, bd=0, highlightthickness=0)
        self.canvas.place(x=0, y=0)

        bg_img = Image.open(self.rel_asset("background.png")).resize((1920, 1080), Image.Resampling.LANCZOS)
        self.bg_image = ImageTk.PhotoImage(bg_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg_image)

        self.whiteimage = PhotoImage(file=self.rel_asset("fillBackground.png"))
        self.canvas.create_image(960.0, 531.0, image=self.whiteimage)

        self.canvas.create_text(850.0, 135.0, anchor="nw", text="Welcome back!",
                                fill="#333333", font=("Poppins Medium", 44 * -1))

        self.canvas.create_text(849.0, 344.0, anchor="nw", text="Email",
                                fill="#666666", font=("Segoe UI", 24 * -1))
        self.canvas.create_text(849.0, 521.0, anchor="nw", text="Password",
                                fill="#666666", font=("Segoe UI", 24 * -1))

        self.entry_image = PhotoImage(file=self.rel_asset("entry_2.png"))
        self.canvas.create_image(1222.5, 417.5, image=self.entry_image)
        self.email = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", font=("Poppins", 17))
        self.email.place(x=855.0, y=388.0, width=735.0, height=58.0)

        self.canvas.create_image(1222.5, 594.5, image=self.entry_image)
        self.password = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", show='*', font=("Poppins", 17))
        self.password.place(x=855.0, y=565.0, width=735.0, height=58.0)

        self.toggle_password_btn = Button(self.root, image=self.hide_image, bd=0, bg="#FFFFFF",
                                          activebackground="#FFFFFF",
                                          command=self.toggle_password_visibility)
        self.toggle_password_btn.place(x=1560, y=580, height=30, width=30)

        self.logo_img = PhotoImage(file=self.rel_asset("logo.png"))
        self.canvas.create_image(600.0, 667.0, image=self.logo_img)

        self.login_button_img = PhotoImage(file=self.rel_asset("LoginButton.png"))
        self.login_button = self.canvas.create_image(1100.0, 800.0, anchor="nw", image=self.login_button_img)
        self.canvas.tag_bind(self.login_button, "<ButtonPress-1>",
                             lambda event: self.canvas.move(self.login_button, 1, 1))
        self.canvas.tag_bind(self.login_button, "<ButtonRelease-1>",
                             lambda event: [self.canvas.move(self.login_button, -1, -1), self.submit()])

        # Clickable register text
        self.register_text = self.canvas.create_text(1020.0, 720.0, anchor="nw",
                                                     text="Don't have an account? Register here!",
                                                     fill="#111111", font=("Segoe UI", 24 * -1))
        self.canvas.tag_bind(self.register_text, "<Button-1>", self.open_register)

    def toggle_password_visibility(self):
        self.password_visible = not self.password_visible
        self.password.config(show='' if self.password_visible else '*')
        self.toggle_password_btn.config(image=self.show_image if self.password_visible else self.hide_image)

    def save_user_session(self, user_data):
        """Save user data to a JSON file for session management"""
        session_path = self.output_path.parent / "user_session.json"
        with open(session_path, 'w') as f:
            json.dump(user_data, f)

    def redirect_to_dashboard(self, role):
        """Redirect to appropriate dashboard based on user role"""
        self.root.destroy()  # Close the login window

        try:
            if role.lower() == "admin":
                from admindashboard import AdminDashboardUI
                app = AdminDashboardUI()
            elif role.lower() == "manager":
                from managerdashboard import ManagerDashboard
                app = ManagerDashboard()
            elif role.lower() == "cashier":
                from cashierdashboard import CashierDashboard
                app = CashierDashboard()
            else:
                raise ValueError("Unknown user role")

            app.mainloop()

        except ImportError as e:
            messagebox.showerror("Error", f"Failed to load dashboard: {e}")
            # Fallback to login
            new_root = ctk.CTk()
            LoginForm(new_root)
            new_root.mainloop()

    def submit(self):
        email = self.email.get().strip()
        password = self.password.get().strip()

        if not email or not password:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        self.cursor.execute("SELECT * FROM User WHERE Email=? AND Password=?", (email, password))
        user = self.cursor.fetchone()

        if user:
            # Create user data dictionary
            user_data = {
                "UserID": user[0],
                "Username": user[1],
                "Email": user[2],
                "Role": user[4],
                "PhoneNumber": user[5]
            }

            # Save user session
            self.save_user_session(user_data)

            # Redirect to appropriate dashboard
            self.redirect_to_dashboard(user[4])
        else:
            messagebox.showerror("Login Failed", "Invalid email or password.")

    def open_register(self, event=None):
        self.root.destroy()
        new_root = Tk()
        RegistrationForm(new_root)
        new_root.resizable(False, False)
        new_root.mainloop()


if __name__ == "__main__":
    root = Tk()
    app = LoginForm(root)
    root.resizable(False, False)
    root.mainloop()
