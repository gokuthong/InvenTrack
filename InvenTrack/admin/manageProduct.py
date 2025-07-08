import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageOps
from pathlib import Path
import sqlite3
import io
import qrcode
import logging
import subprocess
from datetime import datetime
from tkinter import filedialog


# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, nav_commands):
        super().__init__(parent, fg_color="#2d3e50", corner_radius=0, width=180, height=1080)
        self.pack_propagate(False)

        # Sidebar title
        ctk.CTkLabel(
            self,
            text="InvenTrack",
            font=("Segoe UI", 28, "bold"),
            text_color="#fff"
        ).place(x=20, y=20)

        # Navigation buttons
        self.sidebar_buttons = {}
        y = 80
        for name, cmd in nav_commands.items():
            is_current = (name == "Manage Products")
            btn = ctk.CTkButton(
                self,
                text=name,
                width=160,
                height=50,
                corner_radius=10,
                fg_color="#34495E" if is_current else "transparent",
                hover_color="#3E5870" if is_current else "#4A6374",
                text_color="#FFFFFF",
                font=("Segoe UI", 18.5),
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
            font=("Segoe UI", 18.5),
            command=lambda: print("Logging out...")
        ).place(x=10, y=950)


class Header(ctk.CTkFrame):
    def __init__(self, parent, title, sidebar_toggle_callback):
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
            font=("Segoe UI", 20),
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
            font=("Segoe UI", 25),
            text_color="#fff"
        )
        self.title_label.place(x=115, y=10)

        # Profile button
        ctk.CTkButton(
            self,
            text="👤",
            width=40,
            height=40,
            corner_radius=0,
            fg_color="transparent",
            hover_color="#1a252f",
            text_color="#fff",
            font=("Segoe UI", 20)
        ).place(x=1880, y=10)  # Positioned at top-right corner


class ProductCard(ctk.CTkFrame):
    def __init__(self, parent, product_data, view_callback):  # Removed delete_callback parameter
        super().__init__(parent, fg_color="#ffffff", corner_radius=15, border_width=2, border_color="#e0e0e0")
        self.product_data = product_data
        self.view_callback = view_callback  # Only keep view_callback

        # Create layout
        self.grid_columnconfigure(0, weight=1)

        # Increase card dimensions
        self.card_width = 230  # Increased from ~200
        self.card_height = 330  # Increased from ~300
        self.img_width = 225  # Increased from 200
        self.img_height = 200  # Increased from 180

        # Product image or QR code
        self.img_frame = ctk.CTkFrame(self, fg_color="transparent", height=self.img_height)
        self.img_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Load product image with fallback options
        img = self.load_product_image(product_data)

        # Resize and create thumbnail using CTkImage
        img = ImageOps.contain(img, (self.img_width, self.img_height))
        self.photo = ctk.CTkImage(light_image=img, size=(self.img_width, self.img_height))
        self.img_label = ctk.CTkLabel(self.img_frame, image=self.photo, text="")
        self.img_label.pack(fill="both", expand=True)

        # Product name - increased font size and wraplength
        name_label = ctk.CTkLabel(self, text=product_data[1], font=("Segoe UI", 20, "bold"),
                                  wraplength=self.card_width - 20, justify="left")
        name_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        # Category and price - increased font sizes
        cat_price_frame = ctk.CTkFrame(self, fg_color="transparent")
        cat_price_frame.grid(row=2, column=0, padx=10, sticky="ew")

        ctk.CTkLabel(cat_price_frame, text=product_data[2],
                     font=("Segoe UI", 16), text_color="#555555").pack(side="left")
        ctk.CTkLabel(cat_price_frame, text=f"RM{product_data[4]:.2f}",
                     font=("Segoe UI", 18, "bold"), text_color="black").pack(side="right")

        # Stock and status - increased font sizes
        stock_frame = ctk.CTkFrame(self, fg_color="transparent")
        stock_frame.grid(row=3, column=0, padx=10, sticky="ew", pady=(5, 10))

        stock_text = f"Stock: {product_data[5]}"
        status = product_data[7] if product_data[7] else "In Stock"
        status_color = "#27ae60"  # Green for in stock
        if status and "Low" in status:
            status_color = "#f39c12"  # Orange for low stock
        elif status and "Out" in status:
            status_color = "#e74c3c"  # Red for out of stock

        ctk.CTkLabel(stock_frame, text=stock_text, font=("Segoe UI", 16)).pack(side="left")
        ctk.CTkLabel(stock_frame, text=status, font=("Segoe UI", 16, "bold"),
                     text_color=status_color).pack(side="right")

        # Action buttons - increased button sizes
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=10, pady=(0, 15), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)  # Center the button

        # Only keep the View button, now centered and labeled "Modify"
        ctk.CTkButton(
            btn_frame,
            text="Manage",
            width=80,
            height=35,  # Increased dimensions
            font=("Segoe UI", 15),
            command=lambda: view_callback(product_data[0])
        ).grid(row=0, column=0, sticky="nsew")  # Centered in the frame
    def load_product_image(self, product_data):
        """Load product image with fallback to placeholder"""
        try:
            # First try to load the product image
            if product_data[6] and product_data[6] != "-":
                try:
                    return Image.open(product_data[6])
                except:
                    pass

            # Then try to load QR code
            if product_data[3]:
                try:
                    return Image.open(io.BytesIO(product_data[3])).resize((200, 180))
                except:
                    pass

            # Finally generate a QR code if nothing else works
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr_data = (
                f"Item: {product_data[1]}\n"
                f"Category: {product_data[2]}\n"
                f"Quantity: {product_data[5]}\n"
                f"Price: RM{product_data[4]:.2f}\n"
                f"Status: {product_data[7] if product_data[7] else 'In Stock'}\n"
                f"Date: {product_data[8] if len(product_data) > 8 else 'N/A'}"
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            return qr.make_image(fill_color="black", back_color="white").convert('RGB')

        except Exception as e:
            logging.error(f"Error loading product image: {e}")
            return Image.new('RGB', (200, 180), (230, 230, 230))


class ProductManagementUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Product Management")
        self.geometry("1920x1080")
        self.attributes('-fullscreen', True)
        self.configure(fg_color="#f4f7fa")
        self.output_path = Path(__file__).parent
        self.db_path = self.output_path.parent / "inventoryproject.db"
        self.products = []
        self.filtered_products = []
        self.current_category = "All Categories"
        self.pending_image_path = None

        # Load button images
        try:
            # Plus button image
            plus_img_path = self.output_path / "assets/frame0/plus.png"
            plus_img = Image.open(plus_img_path)
            self.plus_icon = ctk.CTkImage(light_image=plus_img, size=(30, 30))

            # Minus button image
            minus_img_path = self.output_path / "assets/frame0/minus.png"
            minus_img = Image.open(minus_img_path)
            self.minus_icon = ctk.CTkImage(light_image=minus_img, size=(32, 33))
        except Exception as e:
            logging.error(f"Error loading button images: {e}")
            self.plus_icon = None
            self.minus_icon = None

        # Background setup
        try:
            bg_path = self.output_path / "assets/frame0/adminBackground.png"
            bg = Image.open(bg_path).resize((1920, 1080))
            self._bg_image = ImageTk.PhotoImage(bg)
        except Exception as e:
            logging.error(f"Error loading background image: {e}")
            self._bg_image = None

        nav_cmds = {
            "Dashboard": lambda: self.switch_to_dashboard(),
            "Register Product": lambda:self.switch_to_registration(),
            "Manage Products": lambda: None
        }

        self.sidebar_visible = True  # Add this line
        self.sidebar = Sidebar(self, nav_cmds)  # Modified this line
        self.sidebar.pack(side="left", fill="y")

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(side="left", fill="both", expand=True)

        # Add background to main frame if available
        if self._bg_image:
            bg_label = tk.Label(self.main, image=self._bg_image)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.header = Header(self.main, "Product Management", self.toggle_sidebar)
        self.build_ui()
        self.load_products()

    def switch_to_dashboard(self):
        """Switch to product registration page without confirmation popup"""
        try:
            # Close current window
            self.destroy()

            # Launch registration page
            current_dir = Path(__file__).parent
            dashboard_script = current_dir / "admindashboard.py"

            if dashboard_script.exists():
                subprocess.Popen(['python', str(dashboard_script)])
            else:
                # Fallback to reopening dashboard if script not found
                app = ProductManagementUI()
                app.mainloop()

        except Exception as e:
            logging.error(f"Error switching to dashboard: {e}")
            messagebox.showerror("Navigation Error", "Failed to open dashboard page")
            # Reopen dashboard if redirection fails
            app = ProductManagementUI()
            app.mainloop()

    def switch_to_registration(self):
        """Switch to product registration page without confirmation popup"""
        try:
            # Close current window
            self.destroy()

            # Launch registration page
            current_dir = Path(__file__).parent
            register_script = current_dir / "registerProduct.py"

            if register_script.exists():
                subprocess.Popen(['python', str(register_script)])
            else:
                # Fallback to reopening dashboard if script not found
                app = ProductManagementUI()
                app.mainloop()



        except Exception as e:
            logging.error(f"Error switching to registration: {e}")
            messagebox.showerror("Navigation Error", "Failed to open registration page")
            # Reopen dashboard if redirection fails
            app = ProductManagementUI()
            app.mainloop()


    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self.sidebar_visible:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", fill="y", before=self.main)
        self.sidebar_visible = not self.sidebar_visible

    def build_ui(self):
        """Build the main UI components"""
        # Main container frame
        self.container = ctk.CTkFrame(self.main, fg_color="#ffffff", corner_radius=20)
        self.container.pack(fill="both", expand=True, padx=65, pady=(20, 50))
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)

        # Top bar with search and actions
        top_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        top_frame.grid_columnconfigure(1, weight=1)

        # Title
        ctk.CTkLabel(top_frame, text="Product Inventory", font=("Segoe UI", 28, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 20))

        # Search and filter
        search_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        search_frame.grid(row=0, column=1, sticky="e")

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search products...",
            width=250,
            height=40,
            font=("Segoe UI", 16)
        )
        self.search_entry.pack(side="left", padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", self.search_products)

        # Add search button
        ctk.CTkButton(
            search_frame,
            text="Search",
            width=80,
            height=40,
            font=("Segoe UI", 16),
            command=self.search_products
        ).pack(side="left", padx=(0, 10))

        # Add filter button with icon
        try:
            # Load filter icon image
            filter_icon_path = self.output_path / "assets/frame0/filtericon.png"
            filter_icon = Image.open(filter_icon_path)
            filter_icon = filter_icon.resize((20, 20))  # Resize to fit button
            self.filter_photo = ctk.CTkImage(light_image=filter_icon)

            # Create filter button
            self.filter_button = ctk.CTkButton(
                search_frame,
                text="",  # No text, just icon
                image=self.filter_photo,
                width=40,
                height=40,
                fg_color="transparent",
                hover_color="#e0e0e0",
                command=self.show_filter_menu
            )
            self.filter_button.pack(side="left", padx=(0, 5))

            # Label to show current filter
            self.current_filter_label = ctk.CTkLabel(
                search_frame,
                text=self.current_category,
                font=("Segoe UI", 14),
                width=120
            )
            self.current_filter_label.pack(side="left", padx=(0, 10))

        except Exception as e:
            logging.error(f"Error loading filter icon: {e}")
            # Fallback to text button if icon fails to load
            self.filter_button = ctk.CTkButton(
                search_frame,
                text="Filter",
                width=80,
                height=40,
                font=("Segoe UI", 16),
                command=self.show_filter_menu
            )
            self.filter_button.pack(side="left", padx=(0, 10))

            self.current_filter_label = ctk.CTkLabel(
                search_frame,
                text=self.current_category,
                font=("Segoe UI", 14),
                width=120
            )
            self.current_filter_label.pack(side="left", padx=(0, 10))

        # Add product button
        ctk.CTkButton(
            top_frame,
            text="+ Add Product",
            width=150,
            height=40,
            font=("Segoe UI", 16),
            fg_color="#27ae60",
            hover_color="#219653",
            command=self.add_new_product
        ).grid(row=0, column=2, padx=(20, 0))

        # Generate report button
        ctk.CTkButton(
            top_frame,
            text="Generate Report",
            width=150,
            height=40,
            font=("Segoe UI", 16),
            command=self.generate_report
        ).grid(row=0, column=3, padx=(10, 0))

        # Products container with scrollbar
        self.products_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.products_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        # Create a canvas and scrollbar
        self.canvas = tk.Canvas(self.products_frame, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(self.products_frame, orientation="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to scroll
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Status bar
        self.status_bar = ctk.CTkLabel(self.container, text="0 products found",
                                       font=("Segoe UI", 14), text_color="#555555")
        self.status_bar.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 10))

    def show_filter_menu(self):
        """Show the filter menu when filter button is clicked"""
        try:
            # Create filter menu (will be shown when button is clicked)
            self.filter_menu = tk.Menu(self, tearoff=0)
            self.filter_menu.add_command(
                label="All Categories",
                command=lambda: self.apply_category_filter("All Categories")
            )

            # Add categories to menu
            for category in self.get_categories_from_db():
                self.filter_menu.add_command(
                    label=category,
                    command=lambda c=category: self.apply_category_filter(c)
                )

            # Get current position of filter button
            x = self.filter_button.winfo_rootx()
            y = self.filter_button.winfo_rooty() + self.filter_button.winfo_height()

            # Show menu at button position
            self.filter_menu.tk_popup(x, y)
        except Exception as e:
            logging.error(f"Error showing filter menu: {e}")
            messagebox.showerror("Error", "Could not show filter options")

    def apply_category_filter(self, category):
        """Apply the selected category filter"""
        self.current_category = category
        self.current_filter_label.configure(text=category)
        self.search_products()  # Apply the filter

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def get_categories_from_db(self):
        """Fetch categories from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT category_name FROM Category")
                categories = [row[0] for row in cursor.fetchall()]
            return categories
        except Exception as e:
            logging.error(f"Error fetching categories: {e}")
            messagebox.showerror("Error", "Could not load categories from database")
            return []

    def load_products(self):
        """Load products from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT productID, productName, category, barcode, price, stockQuantity, imagepath, status 
                    FROM product
                    ORDER BY productName
                """)
                self.products = cursor.fetchall()

            self.filtered_products = self.products[:]
            self.display_products()
            self.update_status_bar()
        except Exception as e:
            logging.error(f"Error loading products: {e}")
            messagebox.showerror("Error", "Could not load products from database")

    def display_products(self):
        """Display products in a grid layout with proper margins"""
        # Clear existing products
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.filtered_products:
            # Show message if no products found
            no_products = ctk.CTkLabel(self.scrollable_frame, text="No products found",
                                       font=("Segoe UI", 20), text_color="#777777")
            no_products.pack(pady=100)
            return

        # Create a container frame with margins
        margin_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        margin_frame.pack(fill="both", expand=True, padx=33)  # Added 50px padding on left and right

        # Calculate number of columns based on window width
        num_cols = 5  # Default to 5 columns

        # Create a grid of product cards
        for i, product in enumerate(self.filtered_products):
            row = i // num_cols
            col = i % num_cols

            if col == 0:
                row_frame = ctk.CTkFrame(margin_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=(0, 20))

            card = ProductCard(
                row_frame,
                product,
                self.view_product_details  # Only pass view_callback
            )
            card.grid(row=0, column=col, padx=25)

    def update_status_bar(self):
        """Update the status bar with product count"""
        count = len(self.filtered_products)
        self.status_bar.configure(text=f"{count} product{'s' if count != 1 else ''} found")

    def search_products(self, event=None):
        """Search products by name and apply category filter"""
        search_term = self.search_entry.get().lower()
        selected_category = self.current_category

        # Filter by both search term and category
        self.filtered_products = [
            p for p in self.products
            if (not search_term or search_term in p[1].lower()) and
               (selected_category == "All Categories" or p[2] == selected_category)
        ]

        self.display_products()
        self.update_status_bar()

    def add_new_product(self):
        """Switch to product registration page"""
        self.switch_to_registration()

    def view_product_details(self, product_id):
        """Show detailed view of selected product with QR code and table format"""
        # Find the product by ID
        product = next((p for p in self.products if p[0] == product_id), None)

        if not product:
            messagebox.showerror("Error", "Product not found")
            return

        # Create detail window
        detail_window = ctk.CTkToplevel(self)
        detail_window.title(f"Product Details - {product[1]}")

        # Set window size and position it in the center of the screen
        window_width = 1300
        window_height = 900
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate position coordinates
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        detail_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        detail_window.grab_set()

        # Main frame
        detail_frame = ctk.CTkFrame(detail_window, fg_color="#ffffff")
        detail_frame.pack(fill="both", expand=True, padx=40, pady=30)
        detail_frame.grid_columnconfigure(1, weight=1)
        detail_frame.grid_rowconfigure(0, weight=1)

        # Status indicator
        status = product[7] if product[7] else "In Stock"
        status_color = "#27ae60"
        if "Low" in status:
            status_color = "#f39c12"
        elif "Out" in status:
            status_color = "#e74c3c"

        status_indicator = ctk.CTkLabel(detail_frame, text=status,
                                        font=("Arial", 20, "bold"),
                                        fg_color=status_color, text_color="white",
                                        corner_radius=5, width=150, height=40)
        status_indicator.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="ne")

        # Left column for image and QR code
        left_frame = ctk.CTkFrame(detail_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, rowspan=2, padx=(40, 40), pady=50, sticky="nw")

        # Product Image at top-left
        img_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        img_frame.pack(fill="x", pady=(0, 30))

        # Load product image
        try:
            if product[6] and product[6] != "-":
                prod_img = Image.open(product[6])
            else:
                prod_img = Image.new('RGB', (400, 300), (240, 240, 240))
        except Exception as e:
            logging.error(f"Error loading product image: {e}")
            prod_img = Image.new('RGB', (400, 300), (240, 240, 240))

        prod_img = ImageOps.contain(prod_img, (350, 300))
        prod_photo = ctk.CTkImage(light_image=prod_img, size=(350, 300))

        # Store the label in the detail window
        detail_window.prod_img_label = ctk.CTkLabel(img_frame, image=prod_photo, text="")
        detail_window.prod_img_label.image = prod_photo
        detail_window.prod_img_label.pack()

        # Change image button - pass the detail_window to the method
        ctk.CTkButton(
            img_frame,
            text="Change Product Image",
            width=200,
            height=40,
            font=("Arial", 16),
            command=lambda: self.change_product_image(product_id, detail_window)
        ).pack(pady=(20, 0))

        # QR Code at bottom-left
        qr_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        qr_frame.pack(fill="x", pady=(30, 20))

        # Generate QR code
        try:
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr_data = (
                f"Product: {product[1]}\n"
                f"Category: {product[2]}\n"
                f"Price: RM{product[4]:.2f}\n"
                f"Stock: {product[5]}\n"
                f"Status: {status}"
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        except Exception as e:
            logging.error(f"Error generating QR code: {e}")
            qr_img = Image.new('RGB', (250, 250), (240, 240, 240))

        qr_img = ImageOps.contain(qr_img, (300, 300))
        qr_photo = ctk.CTkImage(light_image=qr_img, size=(300, 300))
        qr_label = ctk.CTkLabel(qr_frame, image=qr_photo, text="")
        qr_label.image = qr_photo
        qr_label.pack()

        # Right side - Product Details with buttons
        details_frame = ctk.CTkFrame(detail_frame, fg_color="transparent")
        details_frame.grid(row=0, column=1, sticky="nsew", padx=(100, 20), pady=40)

        # Title - Product Name
        ctk.CTkLabel(
            details_frame,
            text=product[1],
            font=("Arial", 32, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 30))

        # Main content frame for product details
        content_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)

        # Details in table format with consistent alignment
        table_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        table_frame.pack(fill="both", expand=True)

        # Create table rows using product attributes
        rows = [
            ("Product ID:", str(product[0]), False),
            ("Category:", product[2], True),
            ("Price:", f"RM{product[4]:.2f}", True),
            ("Status:", status, False)
        ]

        # Configure consistent layout parameters
        label_width = 200
        field_width = 300
        field_height = 48
        field_font = ("Arial", 22)

        self.editable_fields = {}
        for i, (label, value, editable) in enumerate(rows):
            row_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=25)

            # Label - fixed width and alignment
            ctk.CTkLabel(
                row_frame,
                text=label,
                font=field_font,
                anchor="w",
                width=label_width
            ).pack(side="left", padx=(0, 20))

            if editable:
                # Create editable field with consistent sizing
                if label == "Category:":
                    field = ctk.CTkComboBox(
                        row_frame,
                        values=self.get_categories_from_db(),
                        font=field_font,
                        width=field_width,
                        height=field_height
                    )
                    field.set(value)
                else:
                    field = ctk.CTkEntry(
                        row_frame,
                        font=field_font,
                        width=field_width,
                        height=field_height
                    )
                    field.insert(0, value)

                field.pack(side="left")
                self.editable_fields[label.lower().replace(" ", "_").replace(":", "")] = field
            else:
                # Non-editable field with same width as entry fields
                ctk.CTkLabel(
                    row_frame,
                    text=value,
                    font=field_font,
                    width=field_width,
                    anchor="w"
                ).pack(side="left")

        # Handle Stock Quantity separately with + and - buttons
        stock_row_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        stock_row_frame.pack(fill="x", pady=25)

        ctk.CTkLabel(
            stock_row_frame,
            text="Stock Quantity:",
            font=field_font,
            anchor="w",
            width=label_width
        ).pack(side="left", padx=(0, 20))

        # Create a frame for the quantity controls
        quantity_frame = ctk.CTkFrame(stock_row_frame, fg_color="transparent")
        quantity_frame.pack(side="left")

        # Create - button with minus icon
        minus_button = ctk.CTkButton(
            quantity_frame,
            text="",  # Empty text since we're using an image
            image=self.minus_icon if self.minus_icon else None,
            width=40,
            height=field_height,
            font=field_font,
            fg_color="transparent",
            hover_color="#f0f0f0",
            text_color="white" if not self.minus_icon else None
        )
        minus_button.pack(side="left")
        if not self.minus_icon:  # Fallback text if image fails
            minus_button.configure(text="-")

        # Create entry field
        stock_entry = ctk.CTkEntry(
            quantity_frame,
            font=field_font,
            width=field_width - 250,  # Reduce width to make space for buttons
            height=field_height
        )
        stock_entry.insert(0, str(product[5]))
        stock_entry.pack(side="left", padx=5)
        self.editable_fields["stock_quantity"] = stock_entry

        # Create + button with plus icon
        plus_button = ctk.CTkButton(
            quantity_frame,
            text="",  # Empty text since we're using an image
            image=self.plus_icon if self.plus_icon else None,
            width=40,
            height=field_height,
            font=field_font,
            fg_color="Light Cyan" if not self.plus_icon else "transparent",
            hover_color="#219653" if not self.plus_icon else "#f0f0f0"
        )
        plus_button.pack(side="left")
        if not self.plus_icon:  # Fallback text if image fails
            plus_button.configure(text="+")

        # Add button commands
        def increment_stock():
            try:
                current = int(stock_entry.get())
                stock_entry.delete(0, tk.END)
                stock_entry.insert(0, str(current + 1))
            except ValueError:
                pass

        def decrement_stock():
            try:
                current = int(stock_entry.get())
                if current > 0:  # Prevent negative stock
                    stock_entry.delete(0, tk.END)
                    stock_entry.insert(0, str(current - 1))
            except ValueError:
                pass

        plus_button.configure(command=increment_stock)
        minus_button.configure(command=decrement_stock)

        # Button container frame at the bottom of content_frame
        button_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_container.pack(fill="x", pady=(0, 0), side="bottom")

        # Create buttons with consistent sizing
        button_width = 200
        button_height = 45
        button_font = ("Arial", 20)

        # Update button on the left
        ctk.CTkButton(
            button_container,
            text="Update Product",
            width=button_width,
            height=button_height,
            font=button_font,
            fg_color="green",
            hover_color="dark green",
            command=lambda: self.update_product(product, detail_window)
        ).pack(side="left", padx=20)

        # Delete button on the right
        ctk.CTkButton(
            button_container,
            text="Delete Product",
            width=button_width,
            height=button_height,
            font=button_font,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=lambda: self.delete_product(product, detail_window)
        ).pack(side="right", padx=(0, 20))

    def update_product(self, product, window):
        """Handle update functionality, now including image."""
        try:
            # Gather the fields the user edited
            updates = {
                "category": self.editable_fields["category"].get(),
                "price": float(self.editable_fields["price"].get().replace("RM", "").replace(",", "")),
                "stock_quantity": int(self.editable_fields["stock_quantity"].get())
            }

            sql_parts = ["category = ?", "price = ?", "stockQuantity = ?"]
            params = [updates["category"], updates["price"], updates["stock_quantity"]]

            # If they picked a new image, include it
            if self.pending_image_path:
                sql_parts.append("imagepath = ?")
                params.append(self.pending_image_path)

            params.append(product[0])  # WHERE productID = ?

            sql = f"""
                UPDATE product
                SET {', '.join(sql_parts)}
                WHERE productID = ?
            """

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()

            messagebox.showinfo("Success", "Product updated successfully")
            self.load_products()
            window.destroy()

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for price and quantity")
        except Exception as e:
            logging.error(f"Error updating product: {e}")
            messagebox.showerror("Error", "Failed to update product in database")

    def delete_product(self, product, window):
        """Handle delete functionality"""
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this product?"):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM product WHERE productID=?", (product[0],))
                    conn.commit()

                messagebox.showinfo("Success", "Product deleted successfully")
                self.load_products()
                window.destroy()
            except Exception as e:
                logging.error(f"Error deleting product: {e}")
                messagebox.showerror("Error", "Failed to delete product from database")

    def change_product_image(self, product_id, window):
        """Let user pick a new image for the product in the given window"""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select Product Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
        )

        if file_path:
            # Remember the image path for the update
            self.pending_image_path = file_path

            # Update the thumbnail preview in the window
            try:
                new_img = Image.open(file_path)
                new_img = ImageOps.contain(new_img, (350, 300))
                new_photo = ctk.CTkImage(light_image=new_img, size=(350, 300))

                # Access the label through the window parameter
                window.prod_img_label.configure(image=new_photo)
                window.prod_img_label.image = new_photo
            except Exception as e:
                logging.error(f"Error updating product image preview: {e}")

    def generate_report(self):
        """Generate a professional inventory report"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get category summary
                cursor.execute("""
                    SELECT category, COUNT(*) as count, SUM(price*stockQuantity) as total_value 
                    FROM product 
                    GROUP BY category
                    ORDER BY category
                """)
                category_data = cursor.fetchall()

                # Get overall summary
                cursor.execute("""
                    SELECT COUNT(*), SUM(price*stockQuantity), 
                    SUM(CASE WHEN status = 'Out of Stock' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status = 'Low Stock' THEN 1 ELSE 0 END)
                    FROM product
                """)
                total_products, total_value, out_of_stock, low_stock = cursor.fetchone()

            # Create report window
            report_window = ctk.CTkToplevel(self)
            report_window.title("Inventory Report")
            report_window.geometry("800x600")
            report_window.transient(self)
            report_window.grab_set()

            # Header
            header_frame = ctk.CTkFrame(report_window, fg_color="#2d3e50")
            header_frame.pack(fill="x", padx=20, pady=20)

            ctk.CTkLabel(
                header_frame,
                text="Inventory Report",
                font=("Arial", 24, "bold"),
                text_color="white"
            ).pack(pady=10)

            # Report date
            ctk.CTkLabel(
                header_frame,
                text=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                font=("Arial", 14),
                text_color="#bdc3c7"
            ).pack(pady=(0, 10))

            # Summary stats
            stats_frame = ctk.CTkFrame(report_window, fg_color="transparent")
            stats_frame.pack(fill="x", padx=20, pady=(0, 20))

            stats = [
                ("Total Products", total_products),
                ("Total Inventory Value", f"RM{total_value:.2f}"),
                ("Out of Stock", out_of_stock),
                ("Low Stock", low_stock)
            ]

            for i, (label, value) in enumerate(stats):
                frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
                frame.grid(row=i // 2, column=i % 2, sticky="w", padx=20, pady=10)

                ctk.CTkLabel(
                    frame,
                    text=label + ":",
                    font=("Arial", 14, "bold"),
                    width=150,
                    anchor="w"
                ).pack(side="left")

                ctk.CTkLabel(
                    frame,
                    text=str(value),
                    font=("Arial", 14),
                    width=100,
                    anchor="w"
                ).pack(side="left")

            # Category table
            table_frame = ctk.CTkFrame(report_window, fg_color="transparent")
            table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

            # Configure table_frame as a grid
            table_frame.grid_columnconfigure(0, weight=1)  # Category column
            table_frame.grid_columnconfigure(1, weight=0)  # Items column
            table_frame.grid_columnconfigure(2, weight=0)  # Total Value column

            # Table header
            header_frame = ctk.CTkFrame(table_frame, fg_color="#e0e0e0")
            header_frame.grid(row=0, column=0, columnspan=3, sticky="ew")

            headers = ["Category", "Items", "Total Value"]
            column_widths = [400, 150, 200]  # Adjust these values as needed

            for col, (header, width) in enumerate(zip(headers, column_widths)):
                ctk.CTkLabel(
                    header_frame,
                    text=header,
                    font=("Arial", 14, "bold"),
                    width=width,
                    anchor="w",
                    padx=10
                ).grid(row=0, column=col, sticky="w")

            # Table rows with alternating colors
            for i, (category, count, value) in enumerate(category_data):
                row_idx = i + 1
                row_color = "#ffffff" if i % 2 == 0 else "#f5f5f5"

                # Create a frame for the entire row
                row_frame = ctk.CTkFrame(table_frame, fg_color=row_color)
                row_frame.grid(row=row_idx, column=0, columnspan=3, sticky="ew")

                # Configure columns within the row frame
                row_frame.grid_columnconfigure(0, weight=1)
                row_frame.grid_columnconfigure(1, weight=0)
                row_frame.grid_columnconfigure(2, weight=0)

                # Category name
                ctk.CTkLabel(
                    row_frame,
                    text=category,
                    font=("Arial", 14),
                    anchor="w",
                    padx=10,
                    width=column_widths[0]
                ).grid(row=0, column=0, sticky="w")

                # Item count
                ctk.CTkLabel(
                    row_frame,
                    text=str(count),
                    font=("Arial", 14),
                    anchor="w",
                    padx=10,
                    width=column_widths[1]
                ).grid(row=0, column=1, sticky="w")

                # Total value
                ctk.CTkLabel(
                    row_frame,
                    text=f"RM{value:.2f}",
                    font=("Arial", 14),
                    anchor="w",
                    padx=10,
                    width=column_widths[2]
                ).grid(row=0, column=2, sticky="w")

            # Export button
            btn_frame = ctk.CTkFrame(report_window, fg_color="transparent")
            btn_frame.pack(fill="x", padx=20, pady=20)

            ctk.CTkButton(
                btn_frame,
                text="Export to Text File",
                width=200,
                height=40,
                font=("Arial", 16),
                fg_color="#27ae60",
                hover_color="#219653",
                command=lambda: self.export_report(
                    category_data,
                    total_products,
                    total_value,
                    out_of_stock,
                    low_stock
                )
            ).pack(side="right")

        except Exception as e:
            logging.error(f"Error generating report: {e}")
            messagebox.showerror("Error", "Could not generate report")

    def export_report(self, category_data, total_products, total_value, out_of_stock, low_stock):
        """Export the report to a text file"""
        try:
            # Get save file location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")],
                title="Save Report As"
            )

            if not file_path:
                return  # User canceled

            with open(file_path, "w") as f:
                # Write header
                f.write("=" * 50 + "\n")
                f.write("INVENTORY REPORT\n".center(50) + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 50 + "\n\n")

                # Write summary
                f.write("SUMMARY\n")
                f.write("-" * 50 + "\n")
                f.write(f"Total Products: {total_products}\n")
                f.write(f"Total Inventory Value: RM{total_value:.2f}\n")
                f.write(f"Out of Stock Items: {out_of_stock}\n")
                f.write(f"Low Stock Items: {low_stock}\n")
                f.write("\n")

                # Write category details
                f.write("CATEGORY DETAILS\n")
                f.write("-" * 50 + "\n")
                f.write(f"{'Category':<30}{'Items':>10}{'Total Value':>15}\n")
                f.write("-" * 50 + "\n")

                for category, count, value in category_data:
                    f.write(f"{category:<30}{count:>10}{f'RM{value:.2f}':>15}\n")

                f.write("-" * 50 + "\n")
                f.write(f"{'TOTAL':<30}{total_products:>10}{f'RM{total_value:.2f}':>15}\n")
                f.write("=" * 50 + "\n")

            messagebox.showinfo("Export Successful", f"Report saved to:\n{file_path}")
        except Exception as e:
            logging.error(f"Error exporting report: {e}")
            messagebox.showerror("Export Error", "Failed to save report")


if __name__ == '__main__':
    try:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        app = ProductManagementUI()
        app.mainloop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        messagebox.showerror("Critical Error", f"The application encountered an error and will close.\nError: {str(e)}")
