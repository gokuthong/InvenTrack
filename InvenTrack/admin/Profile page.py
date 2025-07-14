import sqlite3
from PIL import Image
from tkinter import messagebox
import re
import subprocess
import sys
import os
from pathlib import Path
import json
import customtkinter as ctk

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class ProfilePageDatabase:
    def __init__(self, db_file = Path(__file__).parent.parent / "inventoryproject.db"):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def get_user_data(self, user_id):  # Removed default value
        try:
            self.cursor.execute("SELECT UserID, Username, Email, Password, Role, PhoneNumber FROM User WHERE UserID = ?", (user_id,))
            return self.cursor.fetchone()
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}. Ensure the 'User' table exists with columns UserID, Username, Email, Password, Role, PhoneNumber")
            return None

    def update_user_data(self, user_id, username, password):
        try:
            self.cursor.execute("UPDATE User SET Username = ?, Password = ? WHERE UserID = ?", (username, password, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database update error: {e}")
            return False

    def check_duplicate_username(self, new_username, current_user_id):
        try:
            self.cursor.execute(
                "SELECT UserID FROM User WHERE Username = ? AND UserID != ?",
                (new_username, current_user_id)
            )
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Database error while checking duplicate username: {e}")
            return False

    def close(self):
        self.conn.close()

class ProfilePage(ctk.CTk):
    def __init__(self, previous_window=None):
        super().__init__()
        self.db = ProfilePageDatabase()
        self.previous_window = previous_window
        self.title("Profile Page")
        self.geometry("1920x1080")
        self.configure(fg_color="white")
        self.resizable(True, True)

        self.image_refs = []

        try:
            pil_bg = Image.open(Path(__file__).parent / "assets/frame0/background.png")
            ctk_bg = ctk.CTkImage(pil_bg, size=(1920, 1080))
            self.image_refs.append(ctk_bg)
            bg_label = ctk.CTkLabel(self, image=ctk_bg, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Background load error: {e}")

        # Get user ID from session
        self.user_id = self.get_user_id_from_session()
        if self.user_id is None:
            messagebox.showerror("Session Error", "Failed to load user session. Please log in again.")
            self.after(100, self.logout)
            return

        # Load user data using session ID
        self.user_data = self.db.get_user_data(self.user_id)
        if self.user_data:
            self.user_id, self.username, self.email, self.password, self.role, self.phone_number = self.user_data
        else:
            messagebox.showerror("Error", "User data not found!")
            self.username = "N/A"
            self.email = "N/A"
            self.password = None
            self.role = "N/A"
            self.phone_number = "N/A"

        self.sidebar_expanded = False
        self.sidebar_width = 180
        self.current_page = "Profile Page"

        self._create_header()
        self._create_sidebar()
        self._create_toggle_button()
        self._create_top_buttons()

        self.is_editing = False
        self.create_main_profile_frame()

    def get_user_id_from_session(self):
        """Read user ID from session file"""
        session_file = Path(__file__).parent.parent / "user_session.json"
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
                return data.get("UserID")
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Session error: {e}")
            return None

    def _create_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="#2d3e50", bg_color="#2d3e50", width=1920, height=55)
        self.header_frame.place(x=0, y=0)

        self.title_label = ctk.CTkLabel(self.header_frame, text=self.current_page, font=("Acumin Pro", 25), text_color="#fff")
        self.title_label.place(x=120, y=10)

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color="#2d3e50", corner_radius=0, width=self.sidebar_width, height=1080,
                                    border_width=0, border_color="#ddd")
        ctk.CTkLabel(self.sidebar, text="InvenTrack", font=("Acumin Pro", 28, "bold"), text_color="#fff").place(x=20, y=20)
        self.sidebar_buttons = {}
        y = 80
        for name in ["Profile Page"]:  # Updated to include only Profile Page
            is_current = (name == self.current_page)
            btn = ctk.CTkButton(self.sidebar, text=name, width=160, height=50, corner_radius=10,
                                fg_color="#34495E" if is_current else "transparent",
                                hover_color="#3E5870" if is_current else "#4A6374",
                                text_color="#FFFFFF", font=("Acumin Pro", 18.5), command=self.show_profile)
            btn.place(x=10, y=y)
            self.sidebar_buttons[name] = btn
            y += 70
        ctk.CTkButton(self.sidebar, text="🔒 Log Out", width=160, height=50, corner_radius=0,
                      fg_color="transparent", hover_color="#f0f8ff", text_color="#fff",
                      font=("Acumin Pro", 18.5), command=self.logout).place(x=10, y=950)

    def _create_toggle_button(self):
        self.toggle_btn = ctk.CTkButton(self, text="☰", width=45, height=45, corner_radius=0,
                                        fg_color="#2d3e50", bg_color="#2d3e50", hover_color="#2d3e50",
                                        text_color="#fff", font=("Acumin Pro", 20), command=self.toggle_sidebar)
        self.toggle_btn.place(x=12, y=6)
        self.toggle_btn.lift()

    def _create_top_buttons(self):
        btn_size = 35
        self.cart_btn = ctk.CTkButton(self, text="🛒", width=btn_size, height=btn_size, corner_radius=0,
                                      fg_color="#2d3e50", bg_color="#2d3e50", hover_color="#1a252f",
                                      text_color="#fff", font=("Acumin Pro", 20), command=lambda: print("Go to Cart"))
        self.profile_btn = ctk.CTkButton(self, text="👤", width=btn_size, height=btn_size, corner_radius=0,
                                         fg_color="#2d3e50", bg_color="#2d3e50", hover_color="#1a252f",
                                         text_color="#fff", font=("Acumin Pro", 20))
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

    def toggle_sidebar(self):
        steps, total_duration = 5, 50
        delta = self.sidebar_width // steps

        def expand(step=0):
            w = delta * step
            self.sidebar.configure(width=w)
            x_off = w
            self.toggle_btn.place_configure(x=10 + x_off)
            self.title_label.place_configure(x=120 + x_off)
            self.panel.place_configure(x=120 + x_off)  # Adjusted to match AddCashierPage
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
            self.panel.place_configure(x=120 + x_off)  # Adjusted to match AddCashierPage
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

    def show_profile(self):
        self.current_page = "Profile Page"
        self.title_label.configure(text=self.current_page)
        for name, btn in self.sidebar_buttons.items():
            if name == "Profile Page":
                btn.configure(fg_color="#34495E", hover_color="#3E5870")
            else:
                btn.configure(fg_color="transparent", hover_color="#4A6374")
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.panel.place(x=120 + x_off, y=80)  # Adjusted to match AddCashierPage
        if self.sidebar_expanded:
            self.toggle_sidebar()
        else:
            self.update_button_positions()

    def create_main_profile_frame(self):
        self.panel = ctk.CTkFrame(self, fg_color="#2d3e50", bg_color="#2d3e50", width=1500, height=800)
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.panel.place(x=120 + x_off, y=80)

        self.profile_frame = ctk.CTkFrame(self.panel, fg_color="#fff", bg_color="#fff", width=400, height=800)
        self.profile_frame.place(x=0, y=0)

        try:
            self.profile_picture = ctk.CTkImage(Image.open(Path(__file__).parent / "assets/frame0/profile image placeholder.png"), size=(300, 300))
            self.image_refs.append(self.profile_picture)
            self.profile_picture_label = ctk.CTkLabel(master=self.profile_frame, image=self.profile_picture, text="")
            self.profile_picture_label.place(x=50, y=50)
        except Exception as e:
            print(f"Profile picture load error: {e}")

        self.welcome_label = ctk.CTkLabel(self.profile_frame, text="Welcome", font=("Arial", 45), width=200, height=80)
        self.welcome_label.place(x=100, y=350)

        self.username_label = ctk.CTkLabel(self.profile_frame, text=self.username, font=("Trebuchet MS", 45), width=200, height=80, anchor="center")
        self.username_label.place(x=100, y=420)

        self.role_label = ctk.CTkLabel(self.profile_frame, text=self.role, font=("Trebuchet MS", 45), width=200, height=80, anchor="center")
        self.role_label.place(x=100, y=490)

        self.logout_button = ctk.CTkButton(self.profile_frame, text="Logout", font=("Arial", 22), width=120, height=50, command=self.logout)
        self.logout_button.place(x=50, y=720)

        self.back_button = ctk.CTkButton(self.profile_frame, text="Back", font=("Arial", 22), width=120, height=50, command=self.back)
        self.back_button.place(x=190, y=720)

        self.my_user_profile=ctk.CTkLabel(self.panel, text="My User Profile", font=("Trebuchet MS", 80), text_color="light blue", width=200, height=80, anchor="center")
        self.my_user_profile.place(x=450, y=40)

        self.name_label = ctk.CTkLabel(master=self.panel, text="Name:", font=("Arial", 45), text_color="#fff", width=200, height=80, anchor="w")
        self.name_label.place(x=450, y=150)
        self.name_value_label = ctk.CTkLabel(master=self.panel, text=self.username, font=("Trebuchet MS", 45), text_color="#fff", width=400, height=80, anchor="w")
        self.name_value_label.place(x=650, y=150)

        self.email_label = ctk.CTkLabel(master=self.panel, text="Email:", font=("Arial", 45), text_color="#fff", width=200, height=80, anchor="w")
        self.email_label.place(x=450, y=230)
        self.email_value_label = ctk.CTkLabel(master=self.panel, text=self.email, font=("Trebuchet MS", 45), text_color="#fff", width=400, height=80, anchor="w")
        self.email_value_label.place(x=650, y=230)

        self.password_label = ctk.CTkLabel(master=self.panel, text="Password:", font=("Arial", 45), text_color="#fff", width=200, height=80, anchor="w")
        self.password_label.place(x=450, y=310)
        self.password_value_label = ctk.CTkLabel(master=self.panel, text=self.censor_password(self.password),
                                                 font=("Trebuchet MS", 45), text_color="#fff", width=400, height=80,
                                                 anchor="w")
        self.password_value_label.place(x=750, y=310)

        self.password_hidden = True

        self.password_value_label.configure(text=self.censor_password(self.password))

        self.mobile_number_label = ctk.CTkLabel(master=self.panel, text="Mobile Number:", font=("Arial", 45), text_color="#fff", width=200, height=80, anchor="w")
        self.mobile_number_label.place(x=450, y=390)
        self.mobile_number_value_label = ctk.CTkLabel(master=self.panel, text=self.phone_number, font=("Trebuchet MS", 45), text_color="#fff", width=400, height=80, anchor="w")
        self.mobile_number_value_label.place(x=850, y=390)

        self.edit_button = ctk.CTkButton(self.panel, text="Edit", font=("Arial", 22), width=120, height=50, command=self.toggle_edit_mode)
        self.edit_button.place(x=1300, y=720)

    def censor_password(self, password):
        return "*" * len(password) if password else ""

    def toggle_password_visibility(self):
        if self.password_hidden:
            self.password_value_label.configure(text=self.password)
            self.toggle_password_btn.configure(text="🙈 Hide")
        else:
            self.password_value_label.configure(text=self.censor_password(self.password))
            self.toggle_password_btn.configure(text="👁 Show")
        self.password_hidden = not self.password_hidden

    def toggle_edit_mode(self):
        if not self.is_editing:
            self.is_editing = True
            self.name_value_label.destroy()
            self.password_value_label.destroy()

            self.name_entry = ctk.CTkEntry(master=self.panel, font=("Arial", 45), width=400, height=80)
            self.name_entry.insert(0, self.username)
            self.name_entry.place(x=650, y=150)

            self.password_entry = ctk.CTkEntry(master=self.panel, font=("Arial", 45), width=400, height=80, show="*")
            self.password_entry.insert(0, self.password)
            self.password_entry.place(x=750, y=310)

            self.password_visible = False
            self.toggle_password_btn = ctk.CTkButton(
                master=self.panel,
                text="👁 Show",
                font=("Arial", 20),
                width=100,
                height=40,
                command=self.toggle_password_entry_visibility
            )
            self.toggle_password_btn.place(x=1170, y=330)

            self.edit_button.destroy()
            self.finish_button = ctk.CTkButton(self.panel, text="Finish", font=("Arial", 22), width=120, height=50, command=self.save_changes)
            self.finish_button.place(x=1300, y=720)
        else:
            self.save_changes()

    def toggle_password_entry_visibility(self):
        if self.password_visible:
            self.password_entry.configure(show="*")
            self.toggle_password_btn.configure(text="👁 Show")
        else:
            self.password_entry.configure(show="")
            self.toggle_password_btn.configure(text="🙈 Hide")
        self.password_visible = not self.password_visible

    def save_changes(self):
        new_username = self.name_entry.get().strip()
        new_password = self.password_entry.get().strip()

        if not new_username:
            messagebox.showerror(title="Error", message="Username cannot be empty.", icon="warning")
            return
        if len(new_username) < 3:
            messagebox.showerror(title="Error", message="Username must be at least 3 characters long.", icon="warning")
            return
        if not re.match(r"^[a-zA-Z0-9_]+$", new_username):
            messagebox.showerror(title="Error", message="Username can only contain letters, numbers, and underscores.",
                                 icon="warning")
            return
        if self.db.check_duplicate_username(new_username, self.user_id):
            messagebox.showerror("Error", "Username is already taken. Please choose a different one.")
            return

        if len(new_password) < 8:
            messagebox.showerror("Password Too Short", "Password must be at least 8 characters long.")
            return
        if not re.search(r"[A-Za-z]", new_password):
            messagebox.showerror("Missing Letters", "Password must include at least one letter.")
            return
        if not re.search(r"[0-9]", new_password):
            messagebox.showerror("Missing Numbers", "Password must include at least one number.")
            return
        if not re.search(r"[\W_]", new_password):
            messagebox.showerror("Missing Symbols", "Password must include at least one symbol (e.g., !@#$%).")
            return

        if self.db.update_user_data(self.user_id, new_username, new_password):
            self.username = new_username
            self.password = new_password
            self.username_label.configure(text=self.username)

            self.name_value_label = ctk.CTkLabel(
                master=self.panel,
                text=self.username,
                font=("Trebuchet MS", 45),
                text_color="#fff",
                width=400,
                height=80,
                anchor="w"
            )
            self.name_value_label.place(x=650, y=150)

            self.password_value_label = ctk.CTkLabel(
                master=self.panel,
                text=self.censor_password(self.password),
                font=("Trebuchet MS", 45),
                text_color="#fff",
                width=400,
                height=80,
                anchor="w"
            )
            self.password_value_label.place(x=750, y=310)

            self.name_entry.destroy()
            self.password_entry.destroy()
            self.finish_button.destroy()
            self.toggle_password_btn.destroy()

            self.edit_button = ctk.CTkButton(
                self.panel,
                text="Edit",
                font=("Arial", 22),
                width=120,
                height=50,
                command=self.toggle_edit_mode
            )
            self.edit_button.place(x=1300, y=720)

            self.is_editing = False
        else:
            messagebox.showerror(title="Error", message="Failed to update profile. Please try again.", icon="error")

    def logout(self):
        """Handle logout process"""
        try:
            # Clear the user session
            session_file = Path(__file__).parent.parent / "user_session.json"
            if session_file.exists():
                session_file.unlink()

            # Close current window
            self.destroy()

            # Launch login page
            current_dir = Path(__file__).parent
            login_script = current_dir / "login.py"  # Go up one level to find login.py

            if login_script.exists():
                subprocess.Popen([sys.executable, str(login_script)])
            else:
                messagebox.showerror("Error", "Login page not found!")
        except Exception as e:
            print(f"Error during logout: {e}")
            messagebox.showerror("Logout Error", "Failed to logout properly")

    def back(self):
        """Read user role from database and open appropriate dashboard"""
        try:
            # Get user role from database using the db cursor
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT Role FROM User WHERE UserID = ?", (self.user_id,))
            role = cursor.fetchone()[0]
            cursor.close()

            # Close current window
            self.db.close()
            self.destroy()

            # Determine which dashboard to open based on role
            current_dir = Path(__file__).parent
            if role.lower() == "cashier":
                dashboard_script = current_dir.parent / "cashier/cart.py"
            elif role.lower() == "admin":
                dashboard_script = current_dir / "admindashboard.py"
            elif role.lower() == "manager":
                dashboard_script = current_dir.parent / "manager/manager.py"
            else:
                # Default to login page if role is not recognized
                messagebox.showwarning("Unknown Role", "Your user role is not recognized. Returning to login page.")
                dashboard_script = current_dir / "login.py"

            # Launch the appropriate dashboard
            if dashboard_script.exists():
                subprocess.Popen([sys.executable, str(dashboard_script)])
            else:
                messagebox.showerror("Error", f"{role} dashboard not found!")

        except Exception as e:
            print(f"Error during back navigation: {e}")
            messagebox.showerror("Error", "Failed to navigate back properly")
            # Fallback to login page
            self.logout()

    def __del__(self):
        self.db.close()

if __name__ == "__main__":
    app = ProfilePage()
    app.mainloop()
