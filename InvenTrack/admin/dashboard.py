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
                                WHEN NEW.stockQuantity < 20 THEN 'Low Stock'
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
                                WHEN NEW.stockQuantity < 20 THEN 'Low Stock'
                                ELSE 'In Stock'
                            END
                        WHERE productID = NEW.productID;
                    END;
                """)

                conn.commit()

        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, nav_commands, toggle_callback):
        super().__init__(parent, width=250, fg_color="#2d3e50")
        ctk.CTkButton(self, text="X", width=30, fg_color="transparent", hover_color="#e74c3c",
                      text_color="white", command=toggle_callback).pack(anchor="ne", padx=5, pady=5)

        ctk.CTkLabel(self, text="Admin Dashboard", font=("Segoe UI", 24), text_color="white").pack(pady=(10, 30))
        for label, cmd in nav_commands.items():
            ctk.CTkButton(self, text=label, text_color="#bdc3c7", fg_color="transparent",
                          hover_color="#1a252f", anchor="w", font=("Segoe UI", 16), corner_radius=0,
                          command=cmd).pack(fill="x", pady=5)


class Header(ctk.CTkFrame):
    def __init__(self, parent, title, sidebar_toggle_callback):
        super().__init__(parent, fg_color="#2d3e50")
        self.pack(fill="x", pady=(0, 20), padx=0)
        ctk.CTkButton(self, text="≡", text_color="white", font=("Segoe UI", 20), width=30,
                      fg_color="transparent", hover_color="#1a252f",
                      command=sidebar_toggle_callback).pack(side="left", padx=(15, 10), pady=10)
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 28), text_color="white").pack(side="left", padx=(10, 0),
                                                                                       pady=10)
        ctk.CTkButton(self, text="👤", font=("Segoe UI", 20), text_color="white", width=40,
                      fg_color="transparent", hover_color="#1a252f").pack(side="right", padx=(0, 15), pady=10)


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
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")

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
            "Register Product": self.switch_to_registration,
            "Manage Products": lambda: self.redirect_to_manage_product(),  # Updated to redirect
            "Sales Report": self.view_sales_report  # Added sales report navigation
        }

        self.sidebar = Sidebar(self, nav_cmds, self.toggle_sidebar)
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
        """Switch to product registration page"""
        messagebox.showinfo("Navigation", "Switching to Register Product page")

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

    # ADDED METHOD FOR SALES REPORT
    def view_sales_report(self):
        """Handle sales report viewing"""
        # Confirm with user
        if messagebox.askyesno("Confirm", "Leave this page and view sales reports?"):
            # Redirect to salesReport.py
            self.redirect_to_sales_report()

    def redirect_to_sales_report(self):
        """Launch salesReport.py in a new process"""
        try:
            # Get current script directory
            current_dir = Path(__file__).parent
            report_script = current_dir / "salesReport.py"

            # Check if file exists
            if not report_script.exists():
                messagebox.showerror("Error", "Sales report module not found!")
                return

            # Close current window
            self.destroy()

            # Launch new process
            if sys.platform == "win32":
                subprocess.Popen(['python', str(report_script)])
            else:
                subprocess.Popen(['python3', str(report_script)])

        except Exception as e:
            logging.error(f"Redirection failed: {e}")
            messagebox.showerror("Error", "Could not launch sales report")
            # Reopen dashboard if redirection fails
            app = AdminDashboardUI()
            app.mainloop()

    def build_ui(self):
        """Build the main UI components"""
        # Main container frame
        self.container = ctk.CTkFrame(self.main, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=65, pady=(20, 50))

        # Configure grid rows - give more weight to charts/alerts section
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=0)  # Welcome message
        self.container.grid_rowconfigure(1, weight=0)  # Summary cards
        self.container.grid_rowconfigure(2, weight=1)  # Charts/Low stock alerts (now gets more space)
        self.container.grid_rowconfigure(3, weight=0)  # Recent activity

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

        # Charts and alerts container
        charts_alerts_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        charts_alerts_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))  # Reduced top padding
        charts_alerts_frame.columnconfigure(0, weight=3)
        charts_alerts_frame.columnconfigure(1, weight=2)
        charts_alerts_frame.rowconfigure(0, weight=1)

        # Inventory chart - make larger
        chart_frame = ctk.CTkFrame(charts_alerts_frame, fg_color="white", corner_radius=15)
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
        alerts_frame = ctk.CTkFrame(charts_alerts_frame, fg_color="white", corner_radius=15)
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
            corner_radius=10
        )
        self.alerts_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10), ipadx=10, ipady=10)

        # Placeholder for alerts
        self.low_stock_items = []

        # Recent activity
        activity_frame = ctk.CTkFrame(self.container, fg_color="white", corner_radius=15)
        activity_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 20))  # Adjusted top padding
        activity_frame.grid_rowconfigure(1, weight=1)
        activity_frame.grid_columnconfigure(0, weight=1)

        # Activity header
        activity_header = ctk.CTkFrame(activity_frame, fg_color="transparent", height=50)
        activity_header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)

        ctk.CTkLabel(activity_header, text="Recent Activity",
                     font=("Segoe UI", 20, "bold"), text_color="#2c3e50").pack(side="left")

        ctk.CTkButton(activity_header, text="View All",
                      width=100, height=30, font=("Segoe UI", 14),
                      fg_color="transparent", border_width=1, border_color="#3498db",
                      text_color="#3498db", hover_color="#e1f0fa").pack(side="right")

        # Activity content
        activity_content = ctk.CTkFrame(activity_frame, fg_color="transparent")
        activity_content.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Placeholder for recent activities
        self.activity_items = []

        # Add a frame to hold activity entries
        self.activities_frame = ctk.CTkFrame(activity_content, fg_color="transparent")
        self.activities_frame.pack(fill="both", expand=True)

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
                    WHERE stockQuantity <= 10 OR status = 'Low Stock' OR status = 'Out of Stock'
                """)
                low_stock_count = cursor.fetchone()[0] or 0

                # Get low stock items (stock <= 10 or status = 'Low Stock')
                cursor.execute("""
                    SELECT productID, productName, category, stockQuantity, status 
                    FROM product 
                    WHERE stockQuantity <= 10 OR status = 'Low Stock' OR status = 'Out of Stock'
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
                    elif stock <= 5:
                        status = "Critical Stock"
                    elif stock <= 10:
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
                    WHERE stockQuantity <= 10 OR status = 'Low Stock' OR status = 'Out of Stock'
                    ORDER BY stockQuantity ASC
                """)
                low_stock_items = cursor.fetchall()

                # Add low stock alerts
                for item in low_stock_items:
                    product_id, product_name, category, stock, status = item
                    if stock <= 0:
                        status = "Out of Stock"
                    elif stock <= 5:
                        status = "Critical Stock"
                    elif stock <= 10:
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

            response = messagebox.askyesno(
                "Confirm Restock",
                f"Leave this page to manage '{product_name}'?\nYou'll be able to restock it on the next page."
            )

            if response:
                self.redirect_to_manage_product(product_id)

        except Exception as e:
            logging.error(f"Error redirecting to manage product: {e}")
            messagebox.showerror("Error", "Could not redirect to product management")

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
            messagebox.showerror("Error", "Could not launch product management")
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
        messagebox.showerror("Critical Error", f"The application encountered an error and will close.\nError: {str(e)}")