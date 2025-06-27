from pathlib import Path
from tkinter import ttk, Tk, Canvas, Entry, Button, PhotoImage, StringVar, messagebox
from PIL import Image, ImageTk
import sqlite3
import re


class RegistrationForm:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="#E1E1F0")

        # Paths
        self.output_path = Path(__file__).parent
        self.assets_path = Path(r"C:\InvenTrack-main\InvenTrack\admin\assets\frame0")

        # Flags for show/hide password
        self.password_visible = False
        self.confirm_password_visible = False

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
                           fill="#666666", font=("Segoe UI", 24 * -1))
        canvas.create_text(738.0, 211.0, anchor="nw", text="Phone Number",
                           fill="#666666", font=("Segoe UI", 24 * -1))
        canvas.create_text(349.0, 344.0, anchor="nw", text="Email",
                           fill="#666666", font=("Segoe UI", 24 * -1))
        canvas.create_text(349.0, 478.0, anchor="nw", text="Role",
                           fill="#666666", font=("Segoe UI", 24 * -1))
        canvas.create_text(349.0, 621.0, anchor="nw", text="Password",
                           fill="#666666", font=("Segoe UI", 24 * -1))
        canvas.create_text(349.0, 755.0, anchor="nw", text="Confirm Password",
                           fill="#666666", font=("Segoe UI", 24 * -1))
        canvas.create_text(345.0, 869.0, anchor="nw",
                           text="Use 8 or more characters with a mix of letters, numbers & symbols",
                           fill="#666666", font=("Segoe UI", 22 * -1))
        canvas.create_text(345.0, 942.0, anchor="nw", text="Already have an account? Log in",
                           fill="#111111", font=("Segoe UI", 24 * -1))
        canvas.create_text(789.0, 936.0, anchor="nw", text="Create an account",
                           fill="#FFFFFF", font=("Segoe UI", 30 * -1))

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

        self.role_var = StringVar()
        self.role = ttk.Combobox(self.root, textvariable=self.role_var, values=["Admin", "Cashier", "Manager"],
                                 font=("Poppins", 17), state="readonly")
        self.role.place(x=345.0, y=519.0, width=760.0, height=63.0)
        self.role.set("Select Role")

        self.entry_image_5 = PhotoImage(file=self.rel_asset("entry_2.png"))
        canvas.create_image(722.5, 694.5, image=self.entry_image_5)
        self.password = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", show='*', highlightthickness=0,
                              font=("Poppins", 17))
        self.password.place(x=355.0, y=665.0, width=735.0, height=58.0)
        self.toggle_password_btn = Button(self.root, image=self.hide_image, bd=0, bg="#FFFFFF",
                                          activebackground="#FFFFFF",
                                          command=self.toggle_password_visibility)
        self.toggle_password_btn.place(x=1060, y=680, height=30, width=30)

        self.entry_image_6 = PhotoImage(file=self.rel_asset("entry_2.png"))
        canvas.create_image(722.5, 828.5, image=self.entry_image_6)
        self.confirm_password = Entry(self.root, bd=0, bg="#FFFFFF", fg="#000716", show='*',
                                      highlightthickness=0, font=("Poppins", 17))
        self.confirm_password.place(x=355.0, y=799.0, width=735.0, height=58.0)
        self.toggle_confirm_password_btn = Button(
            self.root, image=self.hide_image, bd=0, bg="#FFFFFF", activebackground="#FFFFFF",
            command=self.toggle_confirm_password_visibility
        )
        self.toggle_confirm_password_btn.place(x=1060, y=814, height=30, width=30)

        self.image_3 = PhotoImage(file=self.rel_asset("logo.png"))
        canvas.create_image(1445.0, 667.0, image=self.image_3)

        self.submit_img = PhotoImage(file=self.rel_asset("createButton.png"))
        self.submit_button = canvas.create_image(773.0, 923.0, anchor="nw", image=self.submit_img)
        canvas.tag_bind(self.submit_button, "<ButtonPress-1>", lambda event: self.on_submit_press())
        canvas.tag_bind(self.submit_button, "<ButtonRelease-1>", lambda event: self.on_submit_release())

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

    def submit(self):
        username = self.username.get().strip()
        phone = self.phone.get().strip()
        email = self.email.get().strip()
        role = self.role_var.get()
        password = self.password.get()
        confirm_password = self.confirm_password.get()

        if not username or not phone or not email or role == "Select Role" or not password or not confirm_password:
            messagebox.showerror("Error", "All fields are required.")
            return

        if len(password) < 8:
            messagebox.showerror("Password Too Short", "Password must be at least 8 characters long.")
            return

        if not re.search(r"[A-Za-z]", password):
            messagebox.showerror("Missing Letters", "Password must include at least one letter.")
            return

        if not re.search(r"[0-9]", password):
            messagebox.showerror("Missing Numbers", "Password must include at least one number.")
            return

        if not re.search(r"[\W_]", password):
            messagebox.showerror("Missing Symbols", "Password must include at least one symbol (e.g., !@#$%).")
            return

        if password != confirm_password:
            messagebox.showerror("Password Mismatch", "Passwords do not match.")
            return

        try:
            self.cursor.execute(
                "INSERT INTO User (Username, Email, Password, Role, PhoneNumber) VALUES (?, ?, ?, ?, ?)",
                (username, email, password, role, phone)
            )
            self.conn.commit()
            messagebox.showinfo("Success", "Account created successfully.")
            self.clear_fields()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Email already exists.")

    def clear_fields(self):
        self.username.delete(0, "end")
        self.phone.delete(0, "end")
        self.email.delete(0, "end")
        self.role.set("Select Role")
        self.password.delete(0, "end")
        self.confirm_password.delete(0, "end")

if __name__ == "__main__":
    window = Tk()
    app = RegistrationForm(window)
    window.resizable(False, False)
    window.mainloop()
