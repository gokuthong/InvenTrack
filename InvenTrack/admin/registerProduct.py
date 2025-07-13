import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
from pathlib import Path
from datetime import datetime
import sqlite3
import qrcode
import io
import logging
import subprocess
import json

# Set appearance mode and color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, nav_commands, logout_command):
        super().__init__(parent, fg_color="#2d3e50", corner_radius=0, width=180, height=1080)
        self.pack_propagate(False)

        # Sidebar title
        ctk.CTkLabel(
            self,
            text="InvenTrack",
            font=("Acumin Pro", 28, "bold"),
            text_color="#fff"
        ).place(x=20, y=20)

        # Navigation buttons
        self.sidebar_buttons = {}
        y = 80
        for name, cmd in nav_commands.items():
            is_current = (name == "Register Product")
            btn = ctk.CTkButton(
                self,
                text=name,
                width=160,
                height=50,
                corner_radius=10,
                fg_color="#34495E" if is_current else "transparent",
                hover_color="#3E5870" if is_current else "#4A6374",
                text_color="#FFFFFF",
                font=("Acumin Pro", 18.5),
                command=cmd
            )
            btn.place(x=10, y=y)
            self.sidebar_buttons[name] = btn
            y += 70

        # Logout button
        ctk.CTkButton(
            self,
            text="🔒 Log Out",
            width=160,
            height=50,
            corner_radius=0,
            fg_color="transparent",
            hover_color="#f0f8ff",
            text_color="#fff",
            font=("Acumin Pro", 18.5),
            command=logout_command
        ).place(x=10, y=950)


class Header(ctk.CTkFrame):
    def __init__(self, parent, title, sidebar_toggle_callback, profile_command=None):
        super().__init__(parent, fg_color="#2d3e50", height=55)
        self.pack(fill="x", pady=(0, 20), padx=0)

        # Toggle button
        self.toggle_btn = ctk.CTkButton(
            self,
            text="☰",
            width=45,
            height=45,
            corner_radius=0,
            fg_color="#2d3e50",
            hover_color="#1a252f",
            text_color="#fff",
            font=("Acumin Pro", 20),
            command=sidebar_toggle_callback
        )
        self.toggle_btn.place(x=12, y=6)

        try:
            logo_img = Image.open(r"C:\Users\InvenTrack-main\InvenTrack\admin\assets\frame0\logo_header.png")
            logo_img = logo_img.resize((40, 40))  # Resize as needed
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            self.logo_label = ctk.CTkLabel(self, image=self.logo_photo, text="")
            self.logo_label.place(x=65, y=5)  # Position left of title
        except Exception as e:
            logging.error(f"Failed to load logo: {e}")
            self.logo_label = None

        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=("Acumin Pro", 25),
            text_color="#fff"
        )
        self.title_label.place(x=115, y=10)

        # Profile button
        self.profile_btn = ctk.CTkButton(
            self,
            text="👤",
            width=40,
            height=40,
            corner_radius=0,
            fg_color="#2d3e50",
            hover_color="#1a252f",
            text_color="#fff",
            font=("Acumin Pro", 25),
            command=profile_command
        )
        self.profile_btn.place(x=1650, y=10)

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.initialize_database()

    def initialize_database(self):
        """Initialize database tables and triggers"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create product table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product (
                    productID INTEGER PRIMARY KEY AUTOINCREMENT,
                    productName TEXT NOT NULL,
                    category TEXT NOT NULL,
                    barcode BLOB,
                    price REAL NOT NULL,
                    stockQuantity INTEGER NOT NULL,
                    imagepath TEXT,
                    status TEXT,
                    date TEXT
                );
            """)

            # Create category table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Category (
                    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT UNIQUE
                );
            """)

            # Add default categories if empty
            cursor.execute("SELECT COUNT(*) FROM Category")
            if cursor.fetchone()[0] == 0:
                default_categories = ["Electronics", "Furniture", "Sports", "Stationery"]
                for cat in default_categories:
                    cursor.execute("INSERT INTO Category (category_name) VALUES (?)", (cat,))

            # Create triggers for automatic status updates
            # Trigger for INSERT operations
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS set_initial_status
                AFTER INSERT ON product
                FOR EACH ROW
                BEGIN
                    UPDATE product SET status = 
                        CASE 
                            WHEN NEW.stockQuantity = 0 THEN 'Out of Stock'
                            WHEN NEW.stockQuantity < 5 THEN 'Low Stock'
                            ELSE 'In Stock'
                        END
                    WHERE productID = NEW.productID;
                END;
            """)

            # Trigger for UPDATE operations
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_product_status
                AFTER UPDATE OF stockQuantity ON product
                FOR EACH ROW
                BEGIN
                    UPDATE product SET status = 
                        CASE 
                            WHEN NEW.stockQuantity = 0 THEN 'Out of Stock'
                            WHEN NEW.stockQuantity < 5 THEN 'Low Stock'
                            ELSE 'In Stock'
                        END
                    WHERE productID = NEW.productID;
                END;
            """)

            conn.commit()


class ProductRegistrationUI(ctk.CTk):
    def __init__(self, on_close_callback=None):
        super().__init__()
        self.on_close_callback = on_close_callback
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.title("Product Registration")
        width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{width}x{height}+0+0")
        self.configure(fg_color="#f4f7fa")

        # Initialize paths and database
        self.output_path = Path(__file__).parent
        self.db_path = self.output_path.parent / "inventoryproject.db"
        self.db_manager = DatabaseManager(self.db_path)
        self.image_path = None
        self.sidebar_visible = True

        # Load background image
        bg_path = self.output_path / "assets/frame0/adminBackground.png"
        bg = Image.open(bg_path).resize((1920, 1080))
        self._bg_image = ImageTk.PhotoImage(bg)

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Initialize all UI components"""
        nav_cmds = {
            "Dashboard": self.switch_to_dashboard,
            "Register Product": lambda: None,
            "Manage Products": self.switch_to_manage_product
        }

        # Create sidebar with new polished design
        self.sidebar = Sidebar(self, nav_cmds, self.logout)  # Pass logout method as command
        self.sidebar.pack(side="left", fill="y")

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(side="left", fill="both", expand=True)

        # Add background
        bg_label = tk.Label(self.main, image=self._bg_image)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Create header with new polished design
        self.header = Header(self.main, "Product Registration", self.toggle_sidebar, self.goto_profile)

        self.build_registration_form()

    def clear_user_session(self):
        """Clear the user session data"""
        session_file = Path(__file__).parent.parent / "user_session.json"
        try:
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            logging.error(f"Error clearing user session: {e}")

    def logout(self):
        """Handle logout process"""
        try:
            # Clear the user session
            self.clear_user_session()

            # Close current window
            self.destroy()

            # Launch login page
            current_dir = Path(__file__).parent
            login_script = current_dir / "login.py"  # Assuming login.py is in parent directory

            if login_script.exists():
                subprocess.Popen(['python', str(login_script)])
            else:
                messagebox.showerror("Error", "Login page not found!")
        except Exception as e:
            logging.error(f"Error during logout: {e}")
            messagebox.showerror("Logout Error", "Failed to logout properly")

    def goto_profile(self):
        """Close current window and open Profile page"""
        try:
            # Close current window
            self.destroy()

            # Launch profile page
            current_dir = Path(__file__).parent
            profile_script = current_dir / "Profile page.py"

            if profile_script.exists():
                subprocess.Popen(['python', str(profile_script)])
            else:
                # Fallback to reopening dashboard if script not found
                messagebox.showerror("Error", "Profile page not found!")
                app = ProductRegistrationUI()
                app.mainloop()

        except Exception as e:
            logging.error(f"Error switching to profile: {e}")
            messagebox.showerror("Navigation Error", "Failed to open profile page")
            # Reopen dashboard if redirection fails
            app = ProductRegistrationUI()
            app.mainloop()

    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self.sidebar_visible:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", fill="y", before=self.main)
        self.sidebar_visible = not self.sidebar_visible

    def switch_to_dashboard(self):
        """Switch to dashboard page"""
        try:
            # Close current window
            self.destroy()

            # Launch dashboard page
            current_dir = Path(__file__).parent
            dashboard_script = current_dir / "admindashboard.py"

            if dashboard_script.exists():
                subprocess.Popen(['python', str(dashboard_script)])
            else:
                # Fallback to reopening registration if script not found
                app = ProductRegistrationUI()
                app.mainloop()

        except Exception as e:
            logging.error(f"Error switching to dashboard: {e}")
            messagebox.showerror("Navigation Error", "Failed to open dashboard page")
            # Reopen registration if redirection fails
            app = ProductRegistrationUI()
            app.mainloop()

    def switch_to_manage_product(self):
        """Switch to manage product page"""
        try:
            # Close current window
            self.destroy()

            # Launch manage products page
            current_dir = Path(__file__).parent
            manage_script = current_dir / "manageProduct.py"

            if manage_script.exists():
                subprocess.Popen(['python', str(manage_script)])
            else:
                # Fallback to reopening registration if script not found
                app = ProductRegistrationUI()
                app.mainloop()

        except Exception as e:
            logging.error(f"Error switching to manage products: {e}")
            messagebox.showerror("Navigation Error", "Failed to open manage products page")
            # Reopen registration if redirection fails
            app = ProductRegistrationUI()
            app.mainloop()

    def build_registration_form(self):
        """Build the product registration form"""
        label_font = ("Acumin Pro", 26)
        input_font = ("Acumin Pro", 24)

        # Main form frame
        self.form_frame = ctk.CTkFrame(self.main, fg_color="#ffffff", corner_radius=20, width=1400, height=900)
        self.form_frame.place(relx=0.5, rely=0.52, anchor="center")
        self.form_frame.pack_propagate(False)

        # Left side - form entries
        left_frame = ctk.CTkFrame(self.form_frame, fg_color="#ffffff", corner_radius=0)
        left_frame.place(relx=0.04, rely=0.05)

        ctk.CTkLabel(left_frame, text="Add Products Here", font=("Acumin Pro", 32, "bold"),
                     fg_color="#ffffff").grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Form fields
        self.item_name = ctk.CTkEntry(left_frame, font=input_font, height=48, width=420, corner_radius=10)
        self.category = ctk.CTkComboBox(left_frame, values=["-"] + self.get_categories(), font=input_font,
                                        height=48, width=420, corner_radius=10)
        self.quantity = ctk.CTkEntry(left_frame, font=input_font, height=48, width=420, corner_radius=10)
        self.price = ctk.CTkEntry(left_frame, font=input_font, height=48, width=420, corner_radius=10)

        # Arrange form fields
        fields = [
            ("Item Name", self.item_name),
            ("Category", self.category),
            ("Quantity", self.quantity),
            ("Price (RM)", self.price)
        ]

        for idx, (label_text, widget) in enumerate(fields, start=1):
            ctk.CTkLabel(left_frame, text=label_text, font=label_font).grid(
                row=idx, column=0, sticky="e", padx=15, pady=(40, 40))
            widget.grid(row=idx, column=1, pady=(28, 28), padx=12)

        # Buttons
        ctk.CTkButton(left_frame, text="Add New Category", font=("Acumin Pro", 20),
                      fg_color="#808080", hover_color="#696969", text_color="white", width=300, height=40,
                      command=self.add_new_category).grid(row=5, column=0, columnspan=2, pady=(50, 10))

        ctk.CTkButton(left_frame, text="Add Item", font=input_font,
                      fg_color="#008000", hover_color="#006400", text_color="white", height=45, width=300,
                      corner_radius=10, command=self.register_product).grid(
            row=6, column=0, columnspan=2, pady=(20, 10))

        # Right side - image and QR code
        right_frame = ctk.CTkFrame(self.form_frame, fg_color="#ffffff", corner_radius=0)
        right_frame.place(relx=0.6, rely=0.05)

        # Product image
        default_img_path = self.output_path / "assets/frame0/registerProductBG.png"
        img = Image.open(default_img_path).resize((460, 330))
        self.default_img = ImageTk.PhotoImage(img)
        self.image_label = tk.Label(right_frame, image=self.default_img, bg="#ffffff", width=460, height=330)
        self.image_label.pack(pady=(10, 10))

        # Image upload button
        tk.Button(right_frame, text="Add Product Image", font=("Acumin Pro", 12),
                  command=self.upload_product_image).pack()

        # QR Code section
        self.qr_text_label = tk.Label(right_frame, text="Product QR Code", font=("Acumin Pro", 15, "bold"), bg="#ffffff")
        self.qr_text_label.pack(pady=(60, 5))
        self.qr_label = tk.Label(right_frame, bg="#ffffff")
        self.qr_label.pack()

    def get_categories(self):
        """Get categories from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category_name FROM Category")
            return [row[0] for row in cursor.fetchall()]

    def upload_product_image(self):
        """Handle product image upload"""
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
        if file_path:
            self.image_path = file_path
            product_img = Image.open(file_path).convert("RGBA").resize((448, 316))
            bg_img = Image.open(self.output_path / "assets/frame0/registerProductBG.png").convert("RGBA").resize(
                (460, 330))
            bg_img.paste(product_img, (7, 7), product_img)
            self.preview_photo = ImageTk.PhotoImage(bg_img)
            self.image_label.configure(image=self.preview_photo)
            self.image_label.image = self.preview_photo

    def register_product(self):
        """Register a new product in the database"""
        try:
            # Get form values
            name = self.item_name.get()
            category = self.category.get()
            quantity = int(self.quantity.get())
            price = float(self.price.get())
            img_path = self.image_path if self.image_path else "-"
            date = datetime.today().strftime('%Y-%m-%d')

            # Validate inputs
            if not name or category == "-":
                messagebox.showerror("Input Error", "Item name and category are required.")
                return
            if price <= 0 or quantity < 0:
                messagebox.showerror("Input Error", "Price must be > 0 and quantity cannot be negative.")
                return

            # Determine status based on quantity
            if quantity == 0:
                status = "Out of Stock"
            elif quantity < 5:
                status = "Low Stock"
            else:
                status = "In Stock"

            # Generate QR code with status
            qr_text = f"Item: {name}\nCategory: {category}\nQuantity: {quantity}\nPrice: RM{price}\nStatus: {status}\nDate: {date}"
            qr = qrcode.make(qr_text)
            qr_bytes = io.BytesIO()
            qr.save(qr_bytes, format='PNG')
            qr_bytes = qr_bytes.getvalue()

            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO product (productName, category, barcode, price, stockQuantity, imagepath, status, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, category, qr_bytes, price, quantity, img_path, status, date))
                conn.commit()

            # Display QR code
            qr_img = qr.resize((300, 300))
            self.qr_img = ImageTk.PhotoImage(qr_img)
            self.qr_label.configure(image=self.qr_img)
            self.qr_label.image = self.qr_img

            messagebox.showinfo("Success", "Product added successfully!")
        except ValueError:
            messagebox.showerror("Value Error", "Ensure price and quantity are valid numbers.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def add_new_category(self):
        """Add a new product category"""
        popup = tk.Toplevel(self)
        popup.title("Add New Category")
        popup.geometry("300x150")
        popup.grab_set()

        tk.Label(popup, text="Enter New Category:", font=("Acumin Pro", 12)).pack(pady=10)
        entry = tk.Entry(popup, font=("Acumin Pro", 12))
        entry.pack(pady=5)

        def save_category():
            new_cat = entry.get().strip()
            if new_cat:
                if new_cat in self.get_categories():
                    messagebox.showerror("Duplicate", "Category already exists.")
                    return

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO Category (category_name) VALUES (?)", (new_cat,))
                        conn.commit()
                        self.category.configure(values=["-"] + self.get_categories())
                        self.category.set(new_cat)
                        popup.destroy()
                    except sqlite3.IntegrityError:
                        messagebox.showerror("Error", "Category already exists in database.")
            else:
                messagebox.showerror("Input Error", "Category name cannot be empty.")

        tk.Button(popup, text="Save", font=("Acumin Pro", 12), command=save_category).pack(pady=10)

    def on_close(self):
        """Handle window close event"""
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


if __name__ == '__main__':
    app = ProductRegistrationUI()
    app.mainloop()
