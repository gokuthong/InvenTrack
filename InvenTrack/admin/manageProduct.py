import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from pathlib import Path
import sqlite3
import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from datetime import datetime
import subprocess
import sys

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# CUSTOM MESSAGEBOX WITH LARGER SIZE (ONLY FOR RESTOCK CONFIRMATION)
class CustomMessageBox(ctk.CTkToplevel):
    def __init__(self, parent, title, message, buttons=("OK",), icon=None, width=500, height=300):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create content frame
        content_frame = ctk.CTkFrame(self, corner_radius=10)
        content_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)

        # Add icon if provided
        if icon:
            icon_label = ctk.CTkLabel(content_frame, text=icon, font=("Arial", 32))
            icon_label.grid(row=0, column=0, pady=(20, 10))

        # Add message with larger font
        message_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=("Segoe UI", 18),
            wraplength=width - 80,
            justify="center"
        )
        message_label.grid(row=1, column=0, padx=20, pady=10)

        # Add buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, pady=(10, 20))

        self.result = None
        for i, btn_text in enumerate(buttons):
            btn = ctk.CTkButton(
                button_frame,
                text=btn_text,
                width=120,
                height=40,
                font=("Segoe UI", 16, "bold"),
                command=lambda t=btn_text: self.on_button_click(t)
            )
            btn.grid(row=0, column=i, padx=10)

    def on_button_click(self, text):
        self.result = text
        self.destroy()

    def show(self):
        self.wait_window()
        return self.result


# DATABASE MANAGER CLASS WITH ENHANCED ERROR HANDLING
class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.initialize_database()

    def initialize_database(self):
        """Initialize database tables and triggers with better error handling"""
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

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

                # Create user table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user (
                        UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Username TEXT NOT NULL,
                        Email TEXT UNIQUE NOT NULL,
                        Password TEXT NOT NULL,
                        Role TEXT NOT NULL,
                        PhoneNumber TEXT
                    );
                """)

                # Add default categories if empty
                cursor.execute("SELECT COUNT(*) FROM Category")
                if cursor.fetchone()[0] == 0:
                    default_categories = ["Electronics", "Furniture", "Sports", "Stationery"]
                    for cat in default_categories:
                        try:
                            cursor.execute("INSERT INTO Category (category_name) VALUES (?)", (cat,))
                        except sqlite3.IntegrityError:
                            pass  # Ignore if category already exists

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

        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            # Use standard message box for errors
            messagebox.showerror("Database Error", f"Failed to initialize database:\n{str(e)}")


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
            is_current = (name == "Dashboard")
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


class SummaryCard(ctk.CTkFrame):
    def __init__(self, parent, title, initial_value, icon, color, trend=None):
        super().__init__(parent, fg_color="white", corner_radius=15, border_width=1, border_color="#e0e0e0")
        self.grid_propagate(False)
        self.configure(width=280, height=200)

        # Create layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main content frame
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)

        # Icon and title
        icon_frame = ctk.CTkFrame(content_frame, fg_color=color, corner_radius=10, width=50, height=50)
        icon_frame.grid(row=0, column=0, rowspan=2, padx=(0, 15), pady=5, sticky="nw")
        ctk.CTkLabel(icon_frame, text=icon, font=("Arial", 20), text_color="white").place(relx=0.5, rely=0.5,
                                                                                          anchor="center")

        # Title and value
        title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=("Segoe UI", 18),
            text_color="#7f8c8d",
            anchor="w"
        )
        title_label.grid(row=0, column=1, sticky="w")

        self.value_label = ctk.CTkLabel(
            content_frame,
            text=initial_value,
            font=("Segoe UI", 32, "bold"),
            text_color="#2c3e50",
            anchor="w"
        )
        self.value_label.grid(row=1, column=1, sticky="w")

        # Trend indicator
        if trend:
            trend_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            trend_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

            trend_color = "#27ae60" if trend[0] == "+" else "#e74c3c"
            trend_icon = "↑" if trend[0] == "+" else "↓"

            ctk.CTkLabel(trend_frame, text=trend_icon, font=("Arial", 14), text_color=trend_color).pack(side="left",
                                                                                                        padx=(0, 5))
            self.trend_label = ctk.CTkLabel(
                trend_frame,
                text=trend,
                font=("Segoe UI", 14),
                text_color=trend_color
            )
            self.trend_label.pack(side="left")

    def update_value(self, new_value):
        self.value_label.configure(text=new_value)

    def update_trend(self, new_trend):
        if hasattr(self, 'trend_label'):
            trend_color = "#27ae60" if new_trend[0] == "+" else "#e74c3c"
            self.trend_label.configure(text=new_trend, text_color=trend_color)


class LowStockItem(ctk.CTkFrame):
    def __init__(self, parent, product_name, category, current_stock, status, on_restock):
        super().__init__(parent, fg_color="white", corner_radius=10, border_width=1, border_color="#e0e0e0")
        self.configure(height=60)

        # Status indicator
        status_color = "#f39c12" if status == "Low Stock" else "#e74c3c"
        status_indicator = ctk.CTkLabel(
            self,
            text="",
            width=5,
            height=60,
            fg_color=status_color,
            corner_radius=10
        )
        status_indicator.pack(side="left", fill="y", padx=(0, 15))

        # Product details
        details_frame = ctk.CTkFrame(self, fg_color="transparent")
        details_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Product name and category
        name_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        name_frame.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(name_frame, text=product_name, font=("Segoe UI", 16, "bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(name_frame, text=category, font=("Segoe UI", 14), text_color="#7f8c8d", anchor="w").pack(
            side="right", padx=10)

        # Stock information
        stock_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        stock_frame.pack(fill="x")

        ctk.CTkLabel(stock_frame, text=f"Current Stock: {current_stock}", font=("Segoe UI", 14), anchor="w").pack(
            side="left")
        ctk.CTkLabel(stock_frame, text=status, font=("Segoe UI", 14, "bold"), text_color=status_color, anchor="w").pack(
            side="right", padx=10)

        # Restock button
        restock_btn = ctk.CTkButton(
            self,
            text="Restock",
            width=100,
            height=30,
            font=("Segoe UI", 15),
            fg_color="#27ae60",
            hover_color="#219653",
            command=on_restock
        )
        restock_btn.pack(side="right", padx=(0, 15))


class AdminDashboardUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Admin Dashboard")
        self.geometry("1920x1080")
        self.attributes('-fullscreen', True)
        self.configure(fg_color="#f4f7fa")
        self.output_path = Path(__file__).parent
        self.db_path = self.output_path.parent / "inventoryproject.db"

        # Initialize database
        try:
            self.db_manager = DatabaseManager(self.db_path)
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            messagebox.showerror("Database Error", f"Failed to initialize database:\n{str(e)}")

        # Background setup
        try:
            bg_path = self.output_path / "assets/frame0/adminBackground.png"
            if bg_path.exists():
                bg = Image.open(bg_path).resize((1920, 1080))
                self._bg_image = ImageTk.PhotoImage(bg)
            else:
                self._bg_image = None
        except Exception as e:
            logging.error(f"Error loading background image: {e}")
            self._bg_image = None

        self.sidebar_visible = True
        nav_cmds = {
            "Dashboard": lambda: None,
            "Register Product": lambda: self.switch_to_registration(),
            "Manage Products": lambda: self.redirect_to_manage_product()
        }

        self.sidebar = Sidebar(self, nav_cmds)
        self.sidebar.pack(side="left", fill="y")

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(side="left", fill="both", expand=True)

        # Add background to main frame if available
        if self._bg_image:
            bg_label = tk.Label(self.main, image=self._bg_image)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.header = Header(self.main, "Admin Dashboard", self.toggle_sidebar)
        self.build_ui()
        self.load_dashboard_data()

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
                app = AdminDashboardUI()
                app.mainloop()

        except Exception as e:
            logging.error(f"Error switching to registration: {e}")
            messagebox.showerror("Navigation Error", "Failed to open registration page")
            # Reopen dashboard if redirection fails
            app = AdminDashboardUI()
            app.mainloop()

    def switch_to_management(self):
        """Switch to product management page"""
        self.redirect_to_manage_product()

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
        self.container = ctk.CTkFrame(self.main, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=65, pady=(20, 50))

        # Configure grid rows - give more weight to charts/alerts section
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=0)  # Welcome message
        self.container.grid_rowconfigure(1, weight=0)  # Summary cards
        self.container.grid_rowconfigure(2, weight=3)  # Charts/Low stock alerts (now gets more space)
        self.container.grid_rowconfigure(3, weight=1)  # Recent activity (smaller)

        # Welcome message
        welcome_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        welcome_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkLabel(welcome_frame, text="Welcome Back, Admin!",
                     font=("Segoe UI", 36, "bold"), text_color="#2c3e50").pack(side="left")

        ctk.CTkLabel(welcome_frame, text="Here's your inventory overview",
                     font=("Segoe UI", 23), text_color="#7f8c8d").pack(side="left", padx=20)

        # Summary cards
        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))  # Reduced bottom padding

        # Create 4 columns for cards
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1, uniform="cards")

        # Create cards with proper update methods
        self.summary_cards = {
            "products": SummaryCard(cards_frame, "Total Products", "0", "📦", "#3498db"),
            "categories": SummaryCard(cards_frame, "Categories", "0", "📋", "#9b59b6"),
            "value": SummaryCard(cards_frame, "Inventory Value", "RM0", "💰", "#2ecc71", "+0%"),
            "low_stock": SummaryCard(cards_frame, "Low Stock Items", "0", "⚠️", "#f39c12")
        }

        # Position cards
        self.summary_cards["products"].grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.summary_cards["categories"].grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.summary_cards["value"].grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        self.summary_cards["low_stock"].grid(row=0, column=3, padx=10, pady=10, sticky="nsew")

        # Charts and alerts container - LARGER SECTION
        charts_alerts_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        charts_alerts_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))  # Reduced top padding
        charts_alerts_frame.columnconfigure(0, weight=3)
        charts_alerts_frame.columnconfigure(1, weight=2)
        charts_alerts_frame.rowconfigure(0, weight=1)

        # Inventory chart - make larger
        chart_frame = ctk.CTkFrame(charts_alerts_frame, fg_color="white", corner_radius=15,
                                   height=500)  # Increased height
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        chart_frame.grid_propagate(False)

        # Configure chart frame layout
        chart_frame.grid_rowconfigure(0, weight=0)  # Header
        chart_frame.grid_rowconfigure(1, weight=1)  # Chart content
        chart_frame.grid_columnconfigure(0, weight=1)

        # Chart header (smaller)
        chart_header = ctk.CTkFrame(chart_frame, fg_color="transparent", height=40)  # Reduced height
        chart_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)  # Reduced padding

        ctk.CTkLabel(chart_header, text="Inventory Distribution",
                     font=("Segoe UI", 20, "bold"), text_color="#2c3e50").pack(side="left")

        # Chart canvas area (larger)
        self.chart_canvas_frame = ctk.CTkFrame(chart_frame, fg_color="#f8f9fa", corner_radius=10)
        self.chart_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10), ipadx=10, ipady=10)

        # Low stock alerts - make larger
        alerts_frame = ctk.CTkFrame(charts_alerts_frame, fg_color="white", corner_radius=15,
                                    height=500)  # Increased height
        alerts_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        alerts_frame.grid_propagate(False)

        # Configure alerts frame layout
        alerts_frame.grid_rowconfigure(0, weight=0)  # Header
        alerts_frame.grid_rowconfigure(1, weight=1)  # Content
        alerts_frame.grid_columnconfigure(0, weight=1)

        # Alerts header (smaller)
        alerts_header = ctk.CTkFrame(alerts_frame, fg_color="transparent", height=40)  # Reduced height
        alerts_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)  # Reduced padding

        ctk.CTkLabel(alerts_header, text="Low Stock Alerts",
                     font=("Segoe UI", 20, "bold"), text_color="#2c3e50").pack(side="left")

        ctk.CTkLabel(alerts_header, text="Action Needed",
                     font=("Segoe UI", 14), text_color="#e74c3c").pack(side="right")

        # Scrollable frame for alerts (larger)
        self.alerts_scroll_frame = ctk.CTkScrollableFrame(
            alerts_frame,
            fg_color="#f8f9fa",
            corner_radius=10,
            height=400  # Increased height
        )
        self.alerts_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10), ipadx=10, ipady=10)

        # Placeholder for alerts
        self.low_stock_items = []

        # Recent activity - SMALLER SECTION
        activity_frame = ctk.CTkFrame(self.container, fg_color="white", corner_radius=15,
                                      height=250)  # Decreased height
        activity_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 20))  # Adjusted top padding
        activity_frame.grid_rowconfigure(1, weight=1)
        activity_frame.grid_columnconfigure(0, weight=1)

        # Activity header
        activity_header = ctk.CTkFrame(activity_frame, fg_color="transparent", height=50)
        activity_header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)

        ctk.CTkLabel(activity_header, text="Recent Activity",
                     font=("Segoe UI", 20, "bold"), text_color="#2c3e50").pack(side="left")

        # ADDED COMMAND TO VIEW ALL ACTIVITIES
        view_all_btn = ctk.CTkButton(
            activity_header,
            text="View All",
            width=100,
            height=30,
            font=("Segoe UI", 14),
            fg_color="transparent",
            border_width=1,
            border_color="#3498db",
            text_color="#3498db",
            hover_color="#e1f0fa",
            command=self.view_all_activities  # ADDED COMMAND
        )
        view_all_btn.pack(side="right")

        # Activity content
        activity_content = ctk.CTkFrame(activity_frame, fg_color="transparent")
        activity_content.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Placeholder for recent activities
        self.activity_items = []

        # Add a frame to hold activity entries
        self.activities_frame = ctk.CTkFrame(activity_content, fg_color="transparent")
        self.activities_frame.pack(fill="both", expand=True)

    def view_all_activities(self):
        """Show all recent activities in a new window"""
        try:
            # Create a new top-level window
            activities_window = ctk.CTkToplevel(self)
            activities_window.title("All Recent Activities")
            activities_window.geometry("800x600")
            activities_window.transient(self)
            activities_window.grab_set()

            # Center the window
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            window_width = 800
            window_height = 600
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            activities_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # Create header
            header_frame = ctk.CTkFrame(activities_window, fg_color="#2d3e50")
            header_frame.pack(fill="x", padx=0, pady=0)

            ctk.CTkLabel(
                header_frame,
                text="All Recent Activities",
                font=("Segoe UI", 24, "bold"),
                text_color="white"
            ).pack(padx=20, pady=15)

            # Create scrollable content area
            scroll_frame = ctk.CTkScrollableFrame(
                activities_window,
                fg_color="white"
            )
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

            # Get all activities from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT productName, date 
                    FROM product 
                    ORDER BY date DESC 
                """)
                all_activities = cursor.fetchall()

            # Display all activities
            if not all_activities:
                ctk.CTkLabel(
                    scroll_frame,
                    text="No activities found",
                    font=("Segoe UI", 16),
                    text_color="#7f8c8d"
                ).pack(pady=20)
            else:
                for i, activity in enumerate(all_activities):
                    product_name, date_str = activity

                    # Format activity text
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%B %d, %Y")
                    except:
                        formatted_date = date_str

                    activity_text = f"Added {product_name} on {formatted_date}"

                    # Create activity frame
                    activity_frame = ctk.CTkFrame(
                        scroll_frame,
                        fg_color="#f8f9fa" if i % 2 == 0 else "white",
                        height=50
                    )
                    activity_frame.pack(fill="x", pady=2)

                    # Add activity text
                    ctk.CTkLabel(
                        activity_frame,
                        text=activity_text,
                        font=("Segoe UI", 16),
                        anchor="w",
                        text_color="#2c3e50"
                    ).pack(side="left", padx=15, pady=10)

                    # Add time ago indicator
                    try:
                        time_ago = self.format_time_ago(date_obj)
                        ctk.CTkLabel(
                            activity_frame,
                            text=time_ago,
                            font=("Segoe UI", 14),
                            anchor="e",
                            text_color="#7f8c8d"
                        ).pack(side="right", padx=15, pady=10)
                    except:
                        pass

        except Exception as e:
            logging.error(f"Error showing all activities: {e}")
            messagebox.showerror("Error", "Could not load all activities")

    def load_dashboard_data(self):
        """Load data for the dashboard from database with better error handling"""
        try:
            # Check if database file exists
            if not self.db_path.exists():
                error_msg = f"Database file not found at {self.db_path}"
                logging.error(error_msg)
                messagebox.showerror("Database Error", error_msg)
                return

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get total products
                cursor.execute("SELECT COUNT(*) FROM product")
                total_products = cursor.fetchone()[0] or 0

                # Get total categories
                cursor.execute("SELECT COUNT(*) FROM Category")
                total_categories = cursor.fetchone()[0] or 0

                # Get inventory value
                cursor.execute("SELECT SUM(price * stockQuantity) FROM product")
                inventory_value = cursor.fetchone()[0] or 0.0

                # Get low stock items count
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM product 
                    WHERE stockQuantity < 5 OR status = 'Low Stock' OR status = 'Out of Stock'
                """)
                low_stock_count = cursor.fetchone()[0] or 0

                # Get low stock items (stock <= 10 or status = 'Low Stock')
                cursor.execute("""
                    SELECT productID, productName, category, stockQuantity, status 
                    FROM product 
                    WHERE stockQuantity < 5 OR status = 'Low Stock' OR status = 'Out of Stock'
                    ORDER BY stockQuantity ASC
                    LIMIT 10
                """)
                low_stock_items = cursor.fetchall()

                # Update summary cards using new method
                self.summary_cards["products"].update_value(str(total_products))
                self.summary_cards["categories"].update_value(str(total_categories))
                self.summary_cards["value"].update_value(f"RM{inventory_value:,.2f}")
                # UPDATE LOW STOCK COUNT CARD
                self.summary_cards["low_stock"].update_value(str(low_stock_count))

                # Clear existing alerts
                for widget in self.alerts_scroll_frame.winfo_children():
                    widget.destroy()

                # Add low stock alerts
                for item in low_stock_items:
                    product_id, product_name, category, stock, status = item
                    if stock <= 0:
                        status = "Out of Stock"
                    elif stock <= 1:
                        status = "Critical Stock"
                    elif stock <= 5:
                        status = "Low Stock"

                    # Create callback for restock button
                    restock_callback = lambda pid=product_id: self.restock_product(pid)

                    item_frame = LowStockItem(
                        self.alerts_scroll_frame,
                        product_name,
                        category,
                        stock,
                        status,
                        restock_callback
                    )
                    item_frame.pack(fill="x", pady=5)
                    self.low_stock_items.append(item_frame)

                # Generate inventory distribution chart
                self.generate_inventory_chart()

                # Load recent activities
                self.load_recent_activities()

        except sqlite3.Error as e:
            error_msg = f"SQL error: {str(e)}"
            logging.error(f"SQL error in load_dashboard_data: {error_msg}")
            messagebox.showerror("Database Error", error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(f"Error in load_dashboard_data: {error_msg}")
            messagebox.showerror("Error", error_msg)

    # NEW METHOD TO HANDLE LOW STOCK VIEWING
    def view_low_stock(self):
        """Handle viewing all low stock items"""
        # Clear existing alerts
        for widget in self.alerts_scroll_frame.winfo_children():
            widget.destroy()

        # Add a label indicating we're showing all low stock items
        ctk.CTkLabel(
            self.alerts_scroll_frame,
            text="All Low Stock Items:",
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(5, 10))

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT productID, productName, category, stockQuantity, status 
                    FROM product 
                    WHERE stockQuantity < 5 OR status = 'Low Stock' OR status = 'Out of Stock'
                    ORDER BY stockQuantity ASC
                """)
                low_stock_items = cursor.fetchall()

                # Add low stock alerts
                for item in low_stock_items:
                    product_id, product_name, category, stock, status = item
                    if stock <= 0:
                        status = "Out of Stock"
                    elif stock <= 1:
                        status = "Critical Stock"
                    elif stock <= 4:
                        status = "Low Stock"

                    # Create callback for restock button
                    restock_callback = lambda pid=product_id: self.restock_product(pid)

                    item_frame = LowStockItem(
                        self.alerts_scroll_frame,
                        product_name,
                        category,
                        stock,
                        status,
                        restock_callback
                    )
                    item_frame.pack(fill="x", pady=5)
                    self.low_stock_items.append(item_frame)

        except Exception as e:
            logging.error(f"Error loading low stock items: {e}")
            ctk.CTkLabel(
                self.alerts_scroll_frame,
                text="Error loading low stock items",
                text_color="#e74c3c",
                font=("Segoe UI", 14)
            ).pack(pady=10)

    def restock_product(self, product_id):
        """Redirect to manage products page for restocking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT productName FROM product WHERE productID=?", (product_id,))
                product_name = cursor.fetchone()[0]

            # Use our custom message box for confirmation (ONLY FOR RESTOCK)
            response = CustomMessageBox(
                self,
                "Confirm Restock",
                f"Leave this page to manage '{product_name}'?\nYou'll be able to restock it on the next page.",
                buttons=("Yes", "No"),
                width=450,
                height=180
            ).show()

            if response == "Yes":
                self.redirect_to_manage_product(product_id)

        except Exception as e:
            logging.error(f"Error redirecting to manage product: {e}")
            messagebox.showerror("Navigation Error", "Could not redirect to product management")

    def redirect_to_manage_product(self, product_id=None):
        """Launch manageProduct.py in a new process"""
        try:
            current_dir = Path(__file__).parent
            manage_script = current_dir / "manageProduct.py"

            if not manage_script.exists():
                messagebox.showerror("Error", "Product management module not found!")
                return

            # Close current window
            self.destroy()

            # Prepare command with product ID if available
            command = ['python', str(manage_script)]
            if product_id:
                command.append(str(product_id))

            # Launch new process
            subprocess.Popen(command)

        except Exception as e:
            logging.error(f"Redirection failed: {e}")
            messagebox.showerror("Navigation Error", "Could not launch product management")
            # Reopen dashboard if redirection fails
            app = AdminDashboardUI()
            app.mainloop()

    def generate_inventory_chart(self):
        """Generate inventory distribution chart by category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get product count by category
                cursor.execute("""
                    SELECT c.category_name, COUNT(p.productID) 
                    FROM Category c 
                    LEFT JOIN product p ON c.category_name = p.category 
                    GROUP BY c.category_name
                """)
                category_data = cursor.fetchall()

                # Prepare data for chart
                categories = [row[0] for row in category_data]
                counts = [row[1] for row in category_data]

                # Create pie chart
                fig, ax = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
                colors = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#e74c3c', '#1abc9c']
                wedges, texts, autotexts = ax.pie(
                    counts,
                    labels=categories,
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=colors,
                    textprops={'fontsize': 11}
                )

                # Equal aspect ratio ensures that pie is drawn as a circle
                ax.axis('equal')
                ax.set_title('Products by Category', fontsize=14)

                # Add legend
                ax.legend(wedges, categories, title="Categories", loc="center left",
                          bbox_to_anchor=(0.85, 0.5), fontsize=9)

                # Clear existing chart if any
                for widget in self.chart_canvas_frame.winfo_children():
                    widget.destroy()

                # Embed chart in Tkinter
                canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        except Exception as e:
            logging.error(f"Error generating inventory chart: {e}")
            # Show error message instead of chart
            ctk.CTkLabel(
                self.chart_canvas_frame,
                text="Could not load chart data",
                text_color="#e74c3c",
                font=("Segoe UI", 14)
            ).pack(expand=True)

    def load_recent_activities(self):
        """Load recent activities from the database"""
        try:
            # Clear existing activities
            for widget in self.activities_frame.winfo_children():
                widget.destroy()

            # Get actual recent activities from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT productName, date 
                    FROM product 
                    ORDER BY date DESC 
                    LIMIT 5
                """)
                products = cursor.fetchall()

            activities = []
            for product in products:
                product_name, date_str = product
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    time_ago = self.format_time_ago(date_obj)
                except:
                    time_ago = "recently"
                activities.append((f"Added {product_name}", time_ago))

            for i, (activity, time) in enumerate(activities):
                activity_frame = ctk.CTkFrame(self.activities_frame, fg_color="#f8f9fa" if i % 2 == 0 else "white")
                activity_frame.pack(fill="x", pady=2)

                ctk.CTkLabel(activity_frame, text=activity, font=("Segoe UI", 15),
                             anchor="w", text_color="#2c3e50").pack(side="left", padx=15, pady=10)
                ctk.CTkLabel(activity_frame, text=time, font=("Segoe UI", 14),
                             anchor="e", text_color="#7f8c8d").pack(side="right", padx=15, pady=10)

        except Exception as e:
            logging.error(f"Error loading activities: {e}")

    def format_time_ago(self, date_obj):
        """Format how long ago an event occurred"""
        now = datetime.now()
        diff = now - date_obj

        if diff.days > 365:
            years = diff.days // 365
            return f"{years} {'year' if years == 1 else 'years'} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} {'month' if months == 1 else 'months'} ago"
        elif diff.days > 0:
            return f"{diff.days} {'day' if diff.days == 1 else 'days'} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
        else:
            minutes = diff.seconds // 60
            return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"

    def add_activity(self, activity_text):
        """Add a new activity to the log"""
        try:
            # Get current time
            current_time = datetime.now().strftime("%I:%M %p")

            activity_frame = ctk.CTkFrame(self.activities_frame, fg_color="#f8f9fa")
            activity_frame.pack(fill="x", pady=2)

            ctk.CTkLabel(activity_frame, text=activity_text, font=("Segoe UI", 15),
                         anchor="w", text_color="#2c3e50").pack(side="left", padx=15, pady=10)
            ctk.CTkLabel(activity_frame, text=f"{current_time}", font=("Segoe UI", 14),
                         anchor="e", text_color="#7f8c8d").pack(side="right", padx=15, pady=10)

        except Exception as e:
            logging.error(f"Error adding activity: {e}")


if __name__ == '__main__':
    try:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        app = AdminDashboardUI()
        app.mainloop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        # Use standard message box for critical errors
        root = tk.Tk()
        root.withdraw()
        root.destroy()
