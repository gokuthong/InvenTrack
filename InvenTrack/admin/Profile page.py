import customtkinter as ctk
import sqlite3
from PIL import Image
from tkinter import messagebox
import re

ctk.set_default_color_theme("blue")

class Database:
    def __init__(self, db_file="inventoryproject.db"):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def get_user_data(self, user_id=1):
        try:
            self.cursor.execute("SELECT UserID, Username, Email, Password, Role FROM User WHERE UserID = ?", (user_id,))
            return self.cursor.fetchone()
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}. Ensure the 'User' table exists with columns UserID, Username, Email, Password, Role.")
            return None

    def update_user_data(self, user_id, username, password):
        try:
            self.cursor.execute("UPDATE User SET Username = ?, Password = ? WHERE UserID = ?", (username, password, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database update error: {e}")
            return False

    def close(self):
        self.conn.close()

class ProfilePage(ctk.CTk):
    def __init__(self, previous_window=None):
        super().__init__()
        self.db = Database()
        self.previous_window = previous_window  # Store reference to previous window
        self.title("Profile Page")
        self.geometry("1920x1080")
        self.configure(fg_color="white")
        self.resizable(True, True)

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

        self.user_data = self.db.get_user_data(user_id=1001)
        if self.user_data:
            self.user_id, self.username, self.email, self.password, self.role = self.user_data
        else:
            self.user_id = None
            self.username = "N/A"
            self.email = "N/A"
            self.password = None
            self.role = "N/A"
            print("Warning: No data found for UserID=1001. Check if the 'Users' table is populated or exists in inventoryproject.db.")

        self.is_editing = False
        self.create_main_profile_frame()

    def create_main_profile_frame(self):
        self.panel = ctk.CTkFrame(self, fg_color="#2d3e50", bg_color="#2d3e50", width=1500, height=800)
        self.panel.place(x=120, y=80)

        self.profile_frame = ctk.CTkFrame(self.panel, fg_color="#fff", bg_color="#fff", width=400, height=800)
        self.profile_frame.place(x=0, y=0)

        try:
            self.profile_picture = ctk.CTkImage(Image.open("Pictures/profile image placeholder.png"), size=(300, 300))
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

        # Add Back button next to Logout button
        self.back_button = ctk.CTkButton(self.profile_frame, text="Back", font=("Arial", 22), width=120, height=50, command=self.back)
        self.back_button.place(x=190, y=720)

        self.my_user_profile = ctk.CTkLabel(self.panel, text="My User Profile", font=("Trebuchet MS", 80), text_color="light blue", width=200, height=80, anchor="center")
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
        self.password_value_label = ctk.CTkLabel(master=self.panel, text=self.password, font=("Trebuchet MS", 45), text_color="#fff", width=400, height=80, anchor="w")
        self.password_value_label.place(x=750, y=310)

        self.mobile_number_label = ctk.CTkLabel(master=self.panel, text="Mobile Number:", font=("Arial", 45), text_color="#fff", width=200, height=80, anchor="w")
        self.mobile_number_label.place(x=450, y=390)
        self.mobile_number_value_label = ctk.CTkLabel(master=self.panel, text="N/A", font=("Trebuchet MS", 45), text_color="#fff", width=400, height=80, anchor="w")
        self.mobile_number_value_label.place(x=850, y=390)

        self.edit_button = ctk.CTkButton(self.panel, text="Edit", font=("Arial", 22), width=120, height=50, command=self.toggle_edit_mode)
        self.edit_button.place(x=1300, y=720)

    def toggle_edit_mode(self):
        if not self.is_editing:
            self.is_editing = True
            # Replace labels with entry fields
            self.name_value_label.destroy()
            self.password_value_label.destroy()

            self.name_entry = ctk.CTkEntry(master=self.panel, font=("Arial", 45), width=400, height=80)
            self.name_entry.insert(0, self.username)
            self.name_entry.place(x=650, y=150)

            self.password_entry = ctk.CTkEntry(master=self.panel, font=("Arial", 45), width=400, height=80)
            self.password_entry.insert(0, self.password)
            self.password_entry.place(x=750, y=310)

            # Replace edit button with finish button
            self.edit_button.destroy()
            self.finish_button = ctk.CTkButton(self.panel, text="Finish", font=("Arial", 22), width=120, height=50, command=self.save_changes)
            self.finish_button.place(x=1300, y=720)
        else:
            self.save_changes()

    def save_changes(self):
        # Validate inputs
        new_username = self.name_entry.get().strip()
        new_password = self.password_entry.get().strip()

        # Error checking
        if not new_username:
            messagebox.showerror(title="Error", message="Username cannot be empty.", icon="warning")
            return
        if len(new_username) < 3:
            messagebox.showerror(title="Error", message="Username must be at least 3 characters long.", icon="warning")
            return
        if not re.match(r"^[a-zA-Z0-9_]+$", new_username):
            messagebox.showerror(title="Error", message="Username can only contain letters, numbers, and underscores.", icon="warning")
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
            self.edit_button = ctk.CTkButton(self.panel, text="Edit", font=("Arial", 22), width=120, height=50, command=self.toggle_edit_mode)
            self.edit_button.place(x=1300, y=720)
        if not re.search(r"[\W_]", new_password):
            messagebox.showerror("Missing Symbols", "Password must include at least one symbol (e.g., !@#$%).")
            return

        # Update database
        if self.db.update_user_data(self.user_id, new_username, new_password):
            self.username = new_username
            self.password = new_password
            # Update UI
            self.username_label.configure(text=self.username)
            self.name_value_label = ctk.CTkLabel(master=self.panel, text=self.username, font=("Arial", 45), text_color="#fff", width=400, height=80, anchor="w")
            self.name_value_label.place(x=650, y=150)
            self.password_value_label = ctk.CTkLabel(master=self.panel, text=self.password, font=("Arial", 45), text_color="#fff", width=400, height=80, anchor="w")
            self.password_value_label.place(x=750, y=310)

            # Destroy entry fields and finish button
            self.name_entry.destroy()
            self.password_entry.destroy()
            self.finish_button.destroy()

            # Recreate edit button
            self.edit_button = ctk.CTkButton(self.panel, text="Edit", font=("Arial", 22), width=120, height=50, command=self.toggle_edit_mode)
            self.edit_button.place(x=1300, y=720)
            self.is_editing = False
        else:
            messagebox.showerror(title="Error", message="Failed to update profile. Please try again.", icon="error")

    def logout(self):
        self.db.close()
        self.destroy()

    def back(self):
        # Close current window and show previous window
        self.db.close()
        self.destroy()
        if self.previous_window:
            self.previous_window.deiconify()  # Show the previous window

    def __del__(self):
        self.db.close()

if __name__ == "__main__":
    app = ProfilePage()
    app.mainloop()