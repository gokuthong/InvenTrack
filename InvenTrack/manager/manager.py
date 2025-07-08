import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from tkcalendar import DateEntry
import customtkinter as ctk
import sys
import sqlite3
import os
from datetime import datetime, timedelta
import csv
import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pathlib import Path
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
import seaborn as sns

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
        """Initialize database with better error handling"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")

    def execute_query(self, query, params=()):
        """Execute SQL query with error handling"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.commit()
            conn.close()
            return result
        except Exception as e:
            logging.error(f"Database query failed: {e}")
            messagebox.showerror("Database Error", f"Query failed: {str(e)}")
            return []


# UI COMPONENTS
class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, nav_commands, toggle_callback):
        super().__init__(parent, width=180, fg_color="#2d3e50", corner_radius=0)

        ctk.CTkLabel(
            self,
            text="InvenTrack",
            font=("Segoe UI", 28, "bold"),
            text_color="#fff"
        ).place(x=20, y=20)

        # Keep references to each button so we can toggle fg_color/text_color later
        self.sidebar_buttons = {}
        self.current_button = "Dashboard"  # Track currently selected button

        y = 80
        # Add "Log Out" to the list of buttons but with special handling
        for name in ["Dashboard", "Inventory Report", "Sales Report", "Data Analytics", "Log Out"]:
            is_current = (name == "Dashboard")  # Default to Dashboard being current

            # Special handling for Log Out button
            if name == "Log Out":
                btn = ctk.CTkButton(
                    self,
                    text="🔒 " + name,
                    width=160,
                    height=50,
                    corner_radius=10,
                    fg_color="transparent",  # Always transparent for Log Out
                    hover_color="#4A6374",
                    text_color="#FFFFFF",
                    font=("Segoe UI", 18.5),
                    command=lambda: print("Logging out...")
                )
                # Position at bottom with some margin
                btn.place(x=10, y=900)
            else:
                btn = ctk.CTkButton(
                    self,
                    text=name,
                    width=160,
                    height=50,
                    corner_radius=10,
                    fg_color="#34495E" if is_current else "transparent",
                    hover_color="#3E5870" if is_current else "#4A6374",
                    text_color="#FFFFFF" if is_current else "#FFFFFF",
                    font=("Segoe UI", 18.5),
                    command=lambda n=name: self.button_clicked(n, nav_commands.get(n.lower().replace(" ", "_"),
                                                                                   lambda: None))
                )
                btn.place(x=10, y=y)
                y += 70

            self.sidebar_buttons[name] = btn

    def button_clicked(self, button_name, command):
        """Handle button click and update styles"""
        # Skip style updates for Log Out button
        if button_name == "Log Out":
            command()
            return

        # Update styles for all buttons except Log Out
        for name, btn in self.sidebar_buttons.items():
            if name != "Log Out":  # Skip Log Out button
                is_current = (name == button_name)
                btn.configure(
                    fg_color="#34495E" if is_current else "transparent",
                    hover_color="#3E5870" if is_current else "#4A6374",
                    text_color="#FFFFFF" if is_current else "#FFFFFF"
                )

        # Update current button
        self.current_button = button_name

        # Execute the associated command
        command()


class Header(ctk.CTkFrame):
    def __init__(self, parent, title, sidebar_toggle_callback, open_profile_callback):
        super().__init__(parent, fg_color="#2d3e50", width=1920, height=55)

        # Toggle button
        self.toggle_btn = ctk.CTkButton(
            self,
            text="☰",
            width=45,
            height=45,
            corner_radius=0,
            fg_color="#2d3e50",
            hover_color="#2d3e50",
            text_color="#fff",
            font=("Segoe UI", 20),
            command=sidebar_toggle_callback
        )
        self.toggle_btn.place(x=12, y=6)

        # ADDED LOGO
        try:
            logo_img = Image.open(r"C:\Users\InvenTrack-main\InvenTrack\manager\pictures\logo.png")
            logo_img = logo_img.resize((40, 40))  # Resize as needed
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            self.logo_label = ctk.CTkLabel(self, image=self.logo_photo, text="")
            self.logo_label.place(x=65, y=5)  # Position left of title
        except Exception as e:
            logging.error(f"Failed to load logo: {e}")
            self.logo_label = None

        # MODIFIED: Title label position adjusted to right of logo
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=("Segoe UI", 25),
            text_color="#fff"
        )
        # Position moved right to accommodate logo
        self.title_label.place(x=115, y=10)  # Changed from x=120 to x=115

        # Profile button
        self.profile_btn = ctk.CTkButton(
            self,
            text="👤",
            width=35,
            height=35,
            corner_radius=0,
            fg_color="#2d3e50",
            hover_color="#1a252f",
            text_color="#fff",
            font=("Segoe UI", 20),
            command=open_profile_callback
        )
        self.profile_btn.place(x=1800, y=10)


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
    def __init__(self, parent, product_name, category, current_stock, status):
        super().__init__(parent, fg_color="white", corner_radius=10, border_width=1, border_color="#e0e0e0")
        self.configure(height=60)

        # Status indicator
        status_color = "#f39c12" if status == "Low" else "#e74c3c"
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


# MAIN APPLICATION
class AnalyticsPage(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent, fg_color="transparent")
        self.db_manager = db_manager

        # Main container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=65, pady=(20, 50))

        # Title
        ctk.CTkLabel(
            container,
            text="Data & Analytics",
            font=("Segoe UI", 30, "bold"),
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 20))

        # Filter controls
        filter_frame = ctk.CTkFrame(container, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 20))

        self.time_filter_var = ctk.StringVar(value="This Month")
        options = ["Today", "This Week", "This Month", "This Quarter", "This Year", "All Time"]
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.time_filter_var,
            values=options,
            command=self.update_analytics,
            width=150
        ).pack(side="left", padx=(0, 10))

        # Chart selection
        self.chart_type_var = ctk.StringVar(value="Revenue Trend")
        chart_options = ["Revenue Trend", "Top Products", "Category Performance", "Stock Forecast"]
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.chart_type_var,
            values=chart_options,
            command=self.update_analytics,
            width=200
        ).pack(side="left", padx=(0, 10))

        # Export button
        ctk.CTkButton(
            filter_frame,
            text="Export Data",
            command=self.export_analytics_data,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="right")

        # Charts container
        charts_frame = ctk.CTkFrame(container, fg_color="transparent")
        charts_frame.pack(fill="both", expand=True)
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_rowconfigure(0, weight=1)

        # Primary chart frame
        self.chart_frame = ctk.CTkFrame(charts_frame, fg_color="white", corner_radius=15)
        self.chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.chart_frame.grid_rowconfigure(1, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        # Secondary chart frame
        self.secondary_chart_frame = ctk.CTkFrame(charts_frame, fg_color="white", corner_radius=15)
        self.secondary_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.secondary_chart_frame.grid_rowconfigure(1, weight=1)
        self.secondary_chart_frame.grid_columnconfigure(0, weight=1)

        # KPIs frame
        self.kpi_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(20, 0))

        # Initialize charts
        self.create_charts()

        # Load initial data
        self.update_analytics()

    def create_charts(self):
        # Primary chart header
        self.primary_header = ctk.CTkFrame(self.chart_frame, fg_color="transparent", height=40)
        self.primary_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)
        self.primary_title = ctk.CTkLabel(
            self.primary_header,
            text="",
            font=("Segoe UI", 18, "bold"),
            text_color="#2c3e50"
        )
        self.primary_title.pack(side="left")

        # Primary chart canvas
        self.primary_chart_canvas_frame = ctk.CTkFrame(
            self.chart_frame,
            fg_color="#f8f9fa",
            corner_radius=10
        )
        self.primary_chart_canvas_frame.grid(
            row=1, column=0,
            sticky="nsew",
            padx=15, pady=(0, 10),
            ipadx=10, ipady=10
        )

        # Secondary chart header
        self.secondary_header = ctk.CTkFrame(self.secondary_chart_frame, fg_color="transparent", height=40)
        self.secondary_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)
        self.secondary_title = ctk.CTkLabel(
            self.secondary_header,
            text="",
            font=("Segoe UI", 18, "bold"),
            text_color="#2c3e50"
        )
        self.secondary_title.pack(side="left")

        # Secondary chart canvas
        self.secondary_chart_canvas_frame = ctk.CTkFrame(
            self.secondary_chart_frame,
            fg_color="#f8f9fa",
            corner_radius=10
        )
        self.secondary_chart_canvas_frame.grid(
            row=1, column=0,
            sticky="nsew",
            padx=15, pady=(0, 10),
            ipadx=10, ipady=10
        )

    def update_analytics(self, event=None):
        time_filter = self.time_filter_var.get()
        chart_type = self.chart_type_var.get()

        # Clear existing charts
        for widget in self.primary_chart_canvas_frame.winfo_children():
            widget.destroy()
        for widget in self.secondary_chart_canvas_frame.winfo_children():
            widget.destroy()

        # Clear KPIs
        for widget in self.kpi_frame.winfo_children():
            widget.destroy()

        # Fetch data based on chart type
        if chart_type == "Revenue Trend":
            self.show_revenue_trend(time_filter)
        elif chart_type == "Top Products":
            self.show_top_products(time_filter)
        elif chart_type == "Category Performance":
            self.show_category_performance(time_filter)
        elif chart_type == "Stock Forecast":
            self.show_stock_forecast()

    def show_revenue_trend(self, time_filter):
        # Set titles
        self.primary_title.configure(text="Revenue Trend")
        self.secondary_title.configure(text="Sales Volume")

        # Fetch revenue data
        revenue_data = fetch_revenue_data(self.db_manager, time_filter)

        if not revenue_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No revenue data available",
                text_color="#7f8c8d",
                font=("Segoe UI", 14)
            ).pack(expand=True)
            return

        # Prepare data
        dates = [row[0] for row in revenue_data]
        revenues = [row[1] for row in revenue_data]
        volumes = [row[2] for row in revenue_data]

        # Create primary chart (Revenue)
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax1.plot(dates, revenues, marker='o', color='#3498db', linewidth=2.5)
        ax1.set_title('Revenue Trend', fontsize=14)
        ax1.set_ylabel('Revenue (RM)')
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.xaxis.set_major_formatter(DateFormatter("%b %d"))
        plt.setp(ax1.get_xticklabels(), rotation=45)

        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Create secondary chart (Sales Volume)
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax2.bar(dates, volumes, color='#2ecc71')
        ax2.set_title('Sales Volume', fontsize=14)
        ax2.set_ylabel('Items Sold')
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.xaxis.set_major_formatter(DateFormatter("%b %d"))
        plt.setp(ax2.get_xticklabels(), rotation=45)

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate KPIs
        total_revenue = sum(revenues)
        avg_daily = total_revenue / len(revenues) if revenues else 0
        max_revenue = max(revenues) if revenues else 0
        growth = ((revenues[-1] - revenues[0]) / revenues[0] * 100) if len(revenues) > 1 and revenues[0] != 0 else 0

        # Create KPI cards
        kpi_data = [
            ("Total Revenue", f"RM{total_revenue:,.2f}", "#2ecc71"),
            ("Avg Daily", f"RM{avg_daily:,.2f}", "#3498db"),
            ("Peak Revenue", f"RM{max_revenue:,.2f}", "#9b59b6"),
            ("Growth", f"{growth:.1f}%", "#27ae60" if growth >= 0 else "#e74c3c")
        ]

        for i, (title, value, color) in enumerate(kpi_data):
            card = SummaryCard(self.kpi_frame, title, value, "", color)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

    def show_top_products(self, time_filter):
        # Set titles
        self.primary_title.configure(text="Top Selling Products")
        self.secondary_title.configure(text="Revenue Contribution")

        # Fetch product data
        product_data = fetch_top_products(self.db_manager, time_filter)

        if not product_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No product data available",
                text_color="#7f8c8d",
                font=("Segoe UI", 14)
            ).pack(expand=True)
            return

        # Prepare data
        products = [row[0] for row in product_data]
        quantities = [row[1] for row in product_data]
        revenues = [row[2] for row in product_data]

        # Create primary chart (Top Products)
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax1.barh(products, quantities, color='#3498db')
        ax1.set_title('Top Selling Products', fontsize=14)
        ax1.set_xlabel('Quantity Sold')
        ax1.grid(True, linestyle='--', alpha=0.7)

        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Create secondary chart (Revenue Contribution)
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax2.pie(revenues, labels=products, autopct='%1.1f%%',
                startangle=90, colors=plt.cm.Pastel1.colors)
        ax2.set_title('Revenue Contribution', fontsize=14)
        ax2.axis('equal')

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate KPIs
        total_revenue = sum(revenues)
        top_product = products[0]
        top_revenue = revenues[0]
        top_percent = (top_revenue / total_revenue * 100) if total_revenue > 0 else 0

        # Create KPI cards
        kpi_data = [
            ("Total Revenue", f"RM{total_revenue:,.2f}", "#2ecc71"),
            ("Top Product", top_product, "#3498db"),
            ("Top Product Revenue", f"RM{top_revenue:,.2f}", "#9b59b6"),
            ("Top Product Share", f"{top_percent:.1f}%", "#f39c12")
        ]

        for i, (title, value, color) in enumerate(kpi_data):
            card = SummaryCard(self.kpi_frame, title, value, "", color)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

    def show_category_performance(self, time_filter):
        # Set titles
        self.primary_title.configure(text="Category Sales")
        self.secondary_title.configure(text="Category Revenue")

        # Fetch category data
        category_data = fetch_category_performance(self.db_manager, time_filter)

        if not category_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No category data available",
                text_color="#7f8c8d",
                font=("Segoe UI", 14)
            ).pack(expand=True)
            return

        # Prepare data
        categories = [row[0] for row in category_data]
        quantities = [row[1] for row in category_data]
        revenues = [row[2] for row in category_data]

        # Create primary chart (Category Sales)
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax1.bar(categories, quantities, color='#3498db')
        ax1.set_title('Category Sales Volume', fontsize=14)
        ax1.set_ylabel('Items Sold')
        ax1.grid(True, linestyle='--', alpha=0.7)
        plt.setp(ax1.get_xticklabels(), rotation=45)

        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Create secondary chart (Category Revenue)
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax2.bar(categories, revenues, color='#2ecc71')
        ax2.set_title('Category Revenue', fontsize=14)
        ax2.set_ylabel('Revenue (RM)')
        ax2.grid(True, linestyle='--', alpha=0.7)
        plt.setp(ax2.get_xticklabels(), rotation=45)

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate KPIs
        total_revenue = sum(revenues)
        top_category = categories[0]
        top_category_rev = revenues[0]
        top_percent = (top_category_rev / total_revenue * 100) if total_revenue > 0 else 0

        # Create KPI cards
        kpi_data = [
            ("Total Revenue", f"RM{total_revenue:,.2f}", "#2ecc71"),
            ("Top Category", top_category, "#3498db"),
            ("Top Category Revenue", f"RM{top_category_rev:,.2f}", "#9b59b6"),
            ("Top Category Share", f"{top_percent:.1f}%", "#f39c12")
        ]

        for i, (title, value, color) in enumerate(kpi_data):
            card = SummaryCard(self.kpi_frame, title, value, "", color)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

    def show_stock_forecast(self):
        # Set titles
        self.primary_title.configure(text="Stock Level Analysis")
        self.secondary_title.configure(text="Demand Forecast")

        # Fetch stock data
        stock_data = fetch_stock_data(self.db_manager)

        if not stock_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No stock data available",
                text_color="#7f8c8d",
                font=("Segoe UI", 14)
            ).pack(expand=True)
            return

        # Prepare data
        products = [row[0] for row in stock_data]
        current_stock = [row[1] for row in stock_data]
        avg_daily_sales = [row[2] for row in stock_data]

        # Calculate days of supply
        days_of_supply = [stock / sales if sales > 0 else 0 for stock, sales in zip(current_stock, avg_daily_sales)]

        # Create primary chart (Stock Levels)
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')

        # Color based on days of supply
        colors = []
        for days in days_of_supply:
            if days < 7:
                colors.append('#e74c3c')  # Red for critical
            elif days < 14:
                colors.append('#f39c12')  # Orange for low
            else:
                colors.append('#2ecc71')  # Green for sufficient

        ax1.barh(products, current_stock, color=colors)
        ax1.set_title('Current Stock Levels', fontsize=14)
        ax1.set_xlabel('Quantity in Stock')
        ax1.grid(True, linestyle='--', alpha=0.7)

        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Create secondary chart (Demand Forecast)
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')

        # Forecast days of supply
        sorted_indices = np.argsort(days_of_supply)
        sorted_products = [products[i] for i in sorted_indices]
        sorted_days = [days_of_supply[i] for i in sorted_indices]

        ax2.barh(sorted_products, sorted_days, color=colors)
        ax2.set_title('Days of Supply Forecast', fontsize=14)
        ax2.set_xlabel('Days Remaining')
        ax2.axvline(x=7, color='#e74c3c', linestyle='--', alpha=0.7)
        ax2.axvline(x=14, color='#f39c12', linestyle='--', alpha=0.7)
        ax2.text(7.5, len(products) - 0.5, 'Critical', color='#e74c3c')
        ax2.text(14.5, len(products) - 0.5, 'Low', color='#f39c12')
        ax2.grid(True, linestyle='--', alpha=0.7)

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate KPIs
        low_stock_count = sum(1 for days in days_of_supply if days < 14)
        critical_count = sum(1 for days in days_of_supply if days < 7)
        avg_days_supply = sum(days_of_supply) / len(days_of_supply) if days_of_supply else 0

        # Create KPI cards
        kpi_data = [
            ("Products Analyzed", str(len(products)), "#3498db"),
            ("Low Stock Items", str(low_stock_count), "#f39c12"),
            ("Critical Items", str(critical_count), "#e74c3c"),
            ("Avg Days Supply", f"{avg_days_supply:.1f} days", "#2ecc71")
        ]

        for i, (title, value, color) in enumerate(kpi_data):
            card = SummaryCard(self.kpi_frame, title, value, "", color)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

    def export_analytics_data(self):
        chart_type = self.chart_type_var.get()
        time_filter = self.time_filter_var.get()

        # Get data based on chart type
        if chart_type == "Revenue Trend":
            data = fetch_revenue_data(self.db_manager, time_filter)
            headers = ["Date", "Revenue", "Quantity Sold"]
            filename = f"revenue_trend_{time_filter.replace(' ', '_')}.csv"
        elif chart_type == "Top Products":
            data = fetch_top_products(self.db_manager, time_filter)
            headers = ["Product", "Quantity Sold", "Revenue"]
            filename = f"top_products_{time_filter.replace(' ', '_')}.csv"
        elif chart_type == "Category Performance":
            data = fetch_category_performance(self.db_manager, time_filter)
            headers = ["Category", "Quantity Sold", "Revenue"]
            filename = f"category_performance_{time_filter.replace(' ', '_')}.csv"
        elif chart_type == "Stock Forecast":
            data = fetch_stock_data(self.db_manager)
            headers = ["Product", "Current Stock", "Avg Daily Sales"]
            filename = "stock_forecast.csv"
        else:
            return

        # Export to CSV
        filepath = tk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=filename
        )
        if filepath:
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerows(data)
            messagebox.showinfo("Export Successful", f"Data exported to {filepath}")


class ManagerDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Manager Dashboard")
        # Fullscreen
        width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{width}x{height}+0+0")

        # Database
        self.db_path = Path(__file__).parent.parent / "inventoryproject.db"
        self.db_manager = DatabaseManager(self.db_path)
        self.sidebar_visible = True

        # Navigation commands
        nav_cmds = {
            "dashboard": lambda: self.show_page("dashboard"),
            "inventory_report": lambda: self.show_page("inventory_report"),
            "sales_report": lambda: self.show_page("sales_report"),
            "data_analytics": lambda: self.show_page("data_analytics")
        }

        # Header and Sidebar
        self.header = Header(self, "Manager Dashboard", self.toggle_sidebar, self.open_profile)
        self.header.pack(side="top", fill="x")
        self.sidebar = Sidebar(self, nav_cmds, self.toggle_sidebar)
        self.sidebar.pack(side="left", fill="y")

        # Main frame (transparent) with background image
        self.main = ctk.CTkFrame(self, fg_color="lightblue")
        self.main.pack(side="right", fill="both", expand=True)
        self._set_main_background(r"C:\Users\InvenTrack-main\InvenTrack\manager\pictures\wmremove-transformed.jpeg")

        # Container for pages
        self.page_container = ctk.CTkFrame(self.main, fg_color="transparent")
        self.page_container.pack(fill="both", expand=True)

        # Create and show pages
        self.pages = {}
        self.create_dashboard_page()
        self.create_inventory_report_page()
        self.create_sales_report_page()
        self.create_data_analytics_page()
        self.show_page("dashboard")

    def _set_main_background(self, bg_path):
        """Load, fade, and place the background image onto self.main"""
        try:
            img = Image.open(bg_path).convert("RGBA")
            img = img.resize((self.winfo_screenwidth(), self.winfo_screenheight()))
            alpha = img.split()[3].point(lambda p: int(p * 0.85))
            img.putalpha(alpha)
            self._main_bg_img = ImageTk.PhotoImage(img)
            # Place behind other widgets
            self.main_bg_label = ctk.CTkLabel(self.main, image=self._main_bg_img, text="")
            self.main_bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            logging.error(f"Failed to load main background: {e}")

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", fill="y")
        self.sidebar_visible = not self.sidebar_visible

    def create_data_analytics_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["data_analytics"] = page
        AnalyticsPage(page, self.db_manager).pack(fill="both", expand=True)

    def show_page(self, page_name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[page_name].pack(fill="both", expand=True)

        # Update the sidebar button states
        button_names = {
            "dashboard": "Dashboard",
            "inventory_report": "Inventory Report",
            "sales_report": "Sales Report",
            "data_analytics": "Data Analytics"
        }
        if page_name in button_names:
            self.sidebar.button_clicked(button_names[page_name], lambda: None)

        titles = {
            "dashboard": "Manager Dashboard",
            "inventory_report": "Inventory Report",
            "sales_report": "Sales Report",
            "data_analytics": "Data Analytics"
        }
        self.header.title_label.configure(text=titles.get(page_name, ""))

    def open_profile(self):
        messagebox.showinfo("Profile", "User profile management coming soon!")

    def get_low_stock_count(self):
        try:
            query = """
                SELECT COUNT(*)
                FROM product
                WHERE stockQuantity < 5 OR status IN ('Low Stock', 'Out of Stock')
            """
            result = self.db_manager.execute_query(query)
            return result[0][0] if result else 0
        except Exception as e:
            logging.error(f"Error getting low stock count: {e}")
            return 0

    def create_dashboard_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["dashboard"] = page

        # Main container
        container = ctk.CTkFrame(page, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=65, pady=(20, 50))

        # Configure grid rows
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=0)  # Welcome message
        container.grid_rowconfigure(1, weight=0)  # Summary cards
        container.grid_rowconfigure(2, weight=1)  # Charts/Low stock
        container.grid_rowconfigure(3, weight=0)  # Recent transactions

        # Welcome message
        welcome_frame = ctk.CTkFrame(container, fg_color="transparent")
        welcome_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            welcome_frame,
            text="Welcome to Manager Dashboard",
            font=("Segoe UI", 36, "bold"),
            text_color="#2c3e50"
        ).pack(side="left")

        # Summary cards
        cards_frame = ctk.CTkFrame(container, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        for i in range(3):
            cards_frame.columnconfigure(i, weight=1, uniform="cards")

        # Get data for cards
        total_sales, total_revenue, avg_order_value = fetch_sales_data(self.db_manager, "All Time")
        low_count = self.get_low_stock_count()

        # Create cards
        self.summary_cards = {
            "revenue": SummaryCard(cards_frame, "Total Revenue", f"RM{total_revenue:,.2f}", "💰", "#2ecc71"),
            "sales": SummaryCard(cards_frame, "Products Sold", str(total_sales), "📦", "#3498db"),
            "low_stock": SummaryCard(cards_frame, "Low Stock Items", str(low_count), "⚠️", "#f39c12")
        }

        # Position cards
        self.summary_cards["revenue"].grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.summary_cards["sales"].grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.summary_cards["low_stock"].grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # Charts and alerts container
        charts_alerts_frame = ctk.CTkFrame(container, fg_color="transparent")
        charts_alerts_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
        charts_alerts_frame.columnconfigure(0, weight=2)
        charts_alerts_frame.columnconfigure(1, weight=1)
        charts_alerts_frame.rowconfigure(0, weight=1)

        # Sales chart frame
        chart_frame = ctk.CTkFrame(charts_alerts_frame, fg_color="white", corner_radius=15)
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        chart_frame.grid_rowconfigure(0, weight=0)
        chart_frame.grid_rowconfigure(1, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)

        # Chart header
        chart_header = ctk.CTkFrame(chart_frame, fg_color="transparent", height=40)
        chart_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(
            chart_header,
            text="Sales Overview",
            font=("Segoe UI", 20, "bold"),
            text_color="#2c3e50"
        ).pack(side="left")

        # Chart canvas area
        self.chart_canvas_frame = ctk.CTkFrame(chart_frame, fg_color="#f8f9fa", corner_radius=10)
        self.chart_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10), ipadx=10, ipady=10)
        self.generate_sales_chart()

        # Low stock alerts frame
        alerts_frame = ctk.CTkFrame(charts_alerts_frame, fg_color="white", corner_radius=15)
        alerts_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        alerts_frame.grid_rowconfigure(0, weight=0)
        alerts_frame.grid_rowconfigure(1, weight=1)
        alerts_frame.grid_columnconfigure(0, weight=1)

        # Alerts header
        alerts_header = ctk.CTkFrame(alerts_frame, fg_color="transparent", height=40)
        alerts_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(
            alerts_header,
            text="Low Stock Alerts",
            font=("Segoe UI", 20, "bold"),
            text_color="#2c3e50"
        ).pack(side="left")

        # Scrollable frame for alerts
        self.alerts_scroll_frame = ctk.CTkScrollableFrame(
            alerts_frame,
            fg_color="#f8f9fa",
            corner_radius=10
        )
        self.alerts_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10), ipadx=10, ipady=10)
        self.load_low_stock_items()

        # Recent transactions
        activity_frame = ctk.CTkFrame(container, fg_color="white", corner_radius=15)
        activity_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 20))
        activity_frame.grid_rowconfigure(1, weight=1)
        activity_frame.grid_columnconfigure(0, weight=1)

        # Activity header
        activity_header = ctk.CTkFrame(activity_frame, fg_color="transparent", height=50)
        activity_header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(
            activity_header,
            text="Recent Transactions",
            font=("Segoe UI", 20, "bold"),
            text_color="#2c3e50"
        ).pack(side="left")

        # Transactions content
        activity_content = ctk.CTkFrame(activity_frame, fg_color="transparent")
        activity_content.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Transactions table
        cols = ("Transaction ID", "Date & Time", "User", "Total Amount", "Payment Method")
        tv = ttk.Treeview(activity_content, columns=cols, show="headings", height=5)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=150)
        tv.pack(fill="x", pady=10)

        # Load recent transactions
        try:
            transactions = fetch_recent_transactions(self.db_manager, "Today")
            for trans in transactions[:5]:
                tv.insert("", "end", values=trans)
        except Exception as e:
            logging.error(f"Error loading transactions: {e}")

        ctk.CTkButton(
            activity_content,
            text="View More",
            command=lambda: self.show_page("sales_report")
        ).pack(pady=5)

    def generate_sales_chart(self):
        """Generate sales chart for dashboard"""
        try:
            # Get sales data
            transactions = fetch_recent_transactions(self.db_manager, "This Week")
            dates = [trans[1][:10] for trans in transactions]
            amounts = [trans[3] for trans in transactions]

            # Create bar chart
            fig, ax = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
            ax.bar(dates, amounts, color='#3498db')
            ax.set_title('Weekly Sales', fontsize=14)
            ax.set_ylabel('Amount (RM)')
            ax.tick_params(axis='x', rotation=45)

            # Clear existing chart
            for widget in self.chart_canvas_frame.winfo_children():
                widget.destroy()

            # Embed chart
            canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        except Exception as e:
            logging.error(f"Error generating sales chart: {e}")
            ctk.CTkLabel(
                self.chart_canvas_frame,
                text="Could not load chart data",
                text_color="#e74c3c",
                font=("Segoe UI", 14)
            ).pack(expand=True)

    def load_low_stock_items(self):
        """Load low stock items into alerts section"""
        try:
            # Clear existing alerts
            for widget in self.alerts_scroll_frame.winfo_children():
                widget.destroy()

            # Fetch low stock items
            query = """
                SELECT productName, category, stockQuantity, status
                FROM product
                WHERE stockQuantity < 5 OR status = 'Low Stock' OR status = 'Out of Stock'
                ORDER BY stockQuantity ASC
                LIMIT 10
            """
            items = self.db_manager.execute_query(query)

            # Add low stock alerts
            for item in items:
                product_name, category, stock, status = item
                item_frame = LowStockItem(
                    self.alerts_scroll_frame,
                    product_name,
                    category,
                    stock,
                    status
                )
                item_frame.pack(fill="x", pady=5)

        except Exception as e:
            logging.error(f"Error loading low stock items: {e}")
            ctk.CTkLabel(
                self.alerts_scroll_frame,
                text="Error loading low stock items",
                text_color="#e74c3c",
                font=("Segoe UI", 14)
            ).pack(pady=10)

    def create_inventory_report_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["inventory_report"] = page

        # ADDED TITLE FRAME
        title_frame = ctk.CTkFrame(page, fg_color="transparent")
        title_frame.pack(fill="x", padx=65, pady=(20, 0))

        # ADDED TITLE LABEL
        ctk.CTkLabel(
            title_frame,
            text="Inventory Report",
            font=("Segoe UI", 36, "bold"),
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))

        # Content frame
        content_frame = ctk.CTkFrame(page, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 50))

        # Main section
        sec = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=15)
        sec.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            sec,
            text="Detailed Inventory Report",
            font=("Segoe UI", 20, "bold"),
            text_color="#2c3e50"
        ).pack(anchor="w", padx=15, pady=10)

        # Inventory table
        cols = ("Name", "Category", "Stock Qty", "Status")
        tv = ttk.Treeview(sec, columns=cols, show="headings", height=15)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=200)
        scrollbar = ttk.Scrollbar(sec, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=scrollbar.set)
        tv.pack(side="left", fill="both", expand=True, padx=15, pady=(0, 15))
        scrollbar.pack(side="right", fill="y", padx=(0, 15), pady=(0, 15))

        # Load inventory data
        try:
            rows = fetch_inventory_data(self.db_manager)
            for row in rows:
                tv.insert("", "end", values=row)
        except Exception as e:
            logging.error(f"Error loading inventory: {e}")

        # Export button
        btn_frame = ctk.CTkFrame(sec, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(
            btn_frame,
            text="Export CSV",
            command=lambda: export_inventory_csv(self.db_manager),
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="right")

    def create_sales_report_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["sales_report"] = page

        # ADDED TITLE FRAME
        title_frame = ctk.CTkFrame(page, fg_color="transparent")
        title_frame.pack(fill="x", padx=65, pady=(20, 0))

        # ADDED TITLE LABEL
        ctk.CTkLabel(
            title_frame,
            text="Sales Report",
            font=("Segoe UI", 36, "bold"),
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))

        # Content frame
        content_frame = ctk.CTkFrame(page, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 50))

        # Main section
        sec = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=15)
        sec.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            sec,
            text="Detailed Sales Report",
            font=("Segoe UI", 20, "bold"),
            text_color="#2c3e50"
        ).pack(anchor="w", padx=15, pady=10)

        # Filter controls
        filter_frame = ctk.CTkFrame(sec, fg_color="transparent")
        filter_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.time_filter_var = ctk.StringVar(value="Today")
        options = ["Today", "This Week", "This Month", "All Time", "Custom"]
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.time_filter_var,
            values=options,
            command=self.update_sales_report
        ).pack(side="left", padx=(0, 10))

        # Custom date range (hidden by default)
        self.custom_date_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        self.custom_date_frame.pack(side="left", fill="x", expand=True)
        self.custom_date_frame.pack_forget()

        ctk.CTkLabel(self.custom_date_frame, text="From:").pack(side="left", padx=(0, 5))
        self.start_date_entry = DateEntry(
            self.custom_date_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.start_date_entry.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.custom_date_frame, text="To:").pack(side="left", padx=(0, 5))
        self.end_date_entry = DateEntry(
            self.custom_date_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.end_date_entry.pack(side="left", padx=(0, 15))

        ctk.CTkButton(
            self.custom_date_frame,
            text="Apply",
            command=lambda: self.update_sales_report(custom=True),
            width=80
        ).pack(side="left")

        # Export button
        ctk.CTkButton(
            filter_frame,
            text="Export CSV",
            command=self.export_sales_report,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="right")

        # KPIs frame
        kpi_frame = ctk.CTkFrame(sec, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.kpi_cards = {
            "sales": SummaryCard(kpi_frame, "Total Sales", "0", "📊", "#9b59b6"),
            "revenue": SummaryCard(kpi_frame, "Total Revenue", "RM0", "💰", "#2ecc71"),
            "avg": SummaryCard(kpi_frame, "Avg. Order", "RM0", "📈", "#3498db")
        }

        self.kpi_cards["sales"].grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.kpi_cards["revenue"].grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.kpi_cards["avg"].grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        # Transactions table
        cols = ("Transaction ID", "Date & Time", "User", "Total Amount", "Payment Method")
        self.tv = ttk.Treeview(sec, columns=cols, show="headings", height=15)
        for c in cols:
            self.tv.heading(c, text=c)
            self.tv.column(c, width=200)
        scrollbar = ttk.Scrollbar(sec, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=scrollbar.set)
        self.tv.pack(side="left", fill="both", expand=True, padx=15, pady=(0, 15))
        scrollbar.pack(side="right", fill="y", padx=(0, 15), pady=(0, 15))

        # Initial data load
        self.update_sales_report()

    def update_sales_report(self, event=None, custom=False):
        """Update sales report based on selected filter"""
        time_filter = self.time_filter_var.get()

        # Show/hide custom date controls
        if time_filter == "Custom":
            self.custom_date_frame.pack(side="left", fill="x", expand=True)
        else:
            self.custom_date_frame.pack_forget()

        # Get dates if custom
        start_date = end_date = None
        if time_filter == "Custom" and custom:
            start_date = self.start_date_entry.get_date().strftime("%Y-%m-%d")
            end_date = self.end_date_entry.get_date().strftime("%Y-%m-%d")

        # Fetch data
        total_sales, total_revenue, avg_order_value = fetch_sales_data(self.db_manager, time_filter, start_date,
                                                                       end_date)
        transactions = fetch_recent_transactions(self.db_manager, time_filter, start_date, end_date)

        # Update KPIs
        self.kpi_cards["sales"].update_value(str(total_sales))
        self.kpi_cards["revenue"].update_value(f"RM{total_revenue:,.2f}")
        self.kpi_cards["avg"].update_value(f"RM{avg_order_value:,.2f}")

        # Update transactions table
        for row in self.tv.get_children():
            self.tv.delete(row)
        for trans in transactions:
            self.tv.insert("", "end", values=trans)

    def export_sales_report(self):
        """Export sales report to CSV"""
        time_filter = self.time_filter_var.get()
        start_date = end_date = None

        if time_filter == "Custom":
            start_date = self.start_date_entry.get_date().strftime("%Y-%m-%d")
            end_date = self.end_date_entry.get_date().strftime("%Y-%m-%d")

        export_sales_csv(self.db_manager, time_filter, start_date, end_date)

    def show_page(self, page_name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[page_name].pack(fill="both", expand=True)

        titles = {
            "dashboard": "Manager Dashboard",
            "inventory_report": "Inventory Report",
            "sales_report": "Sales Report"
            ""
        }
        self.header.title_label.configure(text=titles[page_name])

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.pack_forget()
            self.sidebar_visible = False
        else:
            self.sidebar.pack(side="left", fill="y")
            self.sidebar_visible = True

    def open_profile(self):
        messagebox.showinfo("Profile", "User profile management coming soon!")


# DATABASE FUNCTIONS
def fetch_inventory_data(db_manager):
    query = """
        SELECT productName, category, stockQuantity, status
        FROM product
    """
    return db_manager.execute_query(query)


def fetch_recent_transactions(db_manager, time_filter="Today", start_date=None, end_date=None):
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    if time_filter == "All Time":
        query = """
            SELECT t.TransactionID, t.DateTime, u.Username, t.TotalAmount, 'N/A' as payment_method
            FROM `Transaction` t
            JOIN `User` u ON t.CashierID = u.UserID
            ORDER BY DateTime ASC
            LIMIT 20
        """
        cursor.execute(query)
    elif time_filter == "Custom" and start_date and end_date:
        query = """
            SELECT t.TransactionID, t.DateTime, u.Username, t.TotalAmount, 'N/A' as payment_method
            FROM `Transaction` t
            JOIN `User` u ON t.CashierID = u.UserID
            WHERE DateTime BETWEEN ? AND ?
            ORDER BY DateTime ASC
            LIMIT 20
        """
        cursor.execute(query, (start_date, end_date))
    else:
        now = datetime.now()
        if time_filter == "Today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "This Week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "This Month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = datetime.min

        query = """
            SELECT t.TransactionID, t.DateTime, u.Username, t.TotalAmount, 'N/A' as payment_method
            FROM `Transaction` t
            JOIN `User` u ON t.CashierID = u.UserID
            WHERE DateTime >= ?
            ORDER BY DateTime ASC
            LIMIT 20
        """
        cursor.execute(query, (start.strftime("%Y-%m-%d %H:%M:%S"),))

    results = cursor.fetchall()
    conn.close()
    return results


def fetch_sales_data(db_manager, time_filter="Today", start_date=None, end_date=None):
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    if time_filter == "Custom" and start_date and end_date:
        query = """
            SELECT COUNT(t.TransactionID), 
                   COALESCE(SUM(t.TotalAmount), 0), 
                   CASE WHEN COUNT(t.TransactionID) > 0 
                        THEN ROUND(SUM(t.TotalAmount) / COUNT(t.TransactionID), 2) 
                        ELSE 0 END
            FROM `Transaction` t
            WHERE DateTime BETWEEN ? AND ?
        """
        cursor.execute(query, (start_date, end_date))
    else:
        if time_filter == "All Time":
            query = """
                SELECT COUNT(t.TransactionID), 
                       COALESCE(SUM(t.TotalAmount), 0), 
                       CASE WHEN COUNT(t.TransactionID) > 0 
                            THEN ROUND(SUM(t.TotalAmount) / COUNT(t.TransactionID), 2) 
                            ELSE 0 END
                FROM `Transaction` t
            """
            cursor.execute(query)
        else:
            now = datetime.now()
            if time_filter == "Today":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == "This Week":
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == "This Month":
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start = datetime.min

            query = """
                SELECT COUNT(t.TransactionID), 
                       COALESCE(SUM(t.TotalAmount), 0), 
                       CASE WHEN COUNT(t.TransactionID) > 0 
                            THEN ROUND(SUM(t.TotalAmount) / COUNT(t.TransactionID), 2) 
                            ELSE 0 END
                FROM `Transaction` t
                WHERE DateTime >= ?
            """
            cursor.execute(query, (start.strftime("%Y-%m-%d %H:%M:%S"),))

    result = cursor.fetchone()
    conn.close()

    total_sales = result[0] or 0
    total_revenue = result[1] or 0
    avg_order_value = result[2] or 0
    return total_sales, total_revenue, avg_order_value


def fetch_revenue_data(db_manager, time_filter="This Month"):
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    # Determine date range based on filter
    now = datetime.now()
    if time_filter == "Today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        group_format = "%H:00"
    elif time_filter == "This Week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m-%d"
    elif time_filter == "This Month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m-%d"
    elif time_filter == "This Quarter":
        quarter_start = (now.month - 1) // 3 * 3 + 1
        start_date = now.replace(month=quarter_start, day=1, hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m-%d"
    elif time_filter == "This Year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m"
    else:  # All Time
        start_date = datetime.min
        group_format = "%Y-%m"

    # Build query
    query = f"""
        SELECT 
            strftime('{group_format}', DateTime) as time_period,
            SUM(TotalAmount) as revenue,
            SUM((
                SELECT SUM(Quantity) 
                FROM TransactionDetail td 
                WHERE td.TransactionID = t.TransactionID
            )) as quantity
        FROM `Transaction` t
        WHERE DateTime >= ?
        GROUP BY time_period
        ORDER BY DateTime ASC
    """

    cursor.execute(query, (start_date.strftime("%Y-%m-%d %H:%M:%S"),))
    results = cursor.fetchall()
    conn.close()

    # Format dates for display
    formatted_results = []
    for row in results:
        period = row[0]
        # Format based on grouping
        if time_filter == "Today":
            period = datetime.strptime(period, "%H:00").strftime("%I %p")
        elif time_filter in ["This Week", "This Month", "This Quarter"]:
            period = datetime.strptime(period, "%Y-%m-%d").strftime("%b %d")
        elif time_filter in ["This Year", "All Time"]:
            period = datetime.strptime(period, "%Y-%m").strftime("%b %Y")
        formatted_results.append((period, row[1] or 0, row[2] or 0))

    return formatted_results


def fetch_top_products(db_manager, time_filter="This Month", limit=10):
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    # Determine date range based on filter
    now = datetime.now()
    if time_filter == "Today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Quarter":
        quarter_start = (now.month - 1) // 3 * 3 + 1
        start_date = now.replace(month=quarter_start, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # All Time
        start_date = datetime.min

    query = """
        SELECT 
            p.productName,
            SUM(td.Quantity) as total_quantity,
            SUM(td.Quantity * td.Price) as total_revenue
        FROM TransactionDetail td
        JOIN Product p ON td.ProductID = p.ProductID
        JOIN `Transaction` t ON td.TransactionID = t.TransactionID
        WHERE t.DateTime >= ?
        GROUP BY p.productName
        ORDER BY total_quantity DESC
        LIMIT ?
    """

    cursor.execute(query, (start_date.strftime("%Y-%m-%d %H:%M:%S"), limit))
    results = cursor.fetchall()
    conn.close()
    return results


def fetch_category_performance(db_manager, time_filter="This Month"):
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    # Determine date range based on filter
    now = datetime.now()
    if time_filter == "Today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Quarter":
        quarter_start = (now.month - 1) // 3 * 3 + 1
        start_date = now.replace(month=quarter_start, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == "This Year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # All Time
        start_date = datetime.min

    query = """
        SELECT 
            p.category,
            SUM(td.Quantity) as total_quantity,
            SUM(td.Quantity * td.Price) as total_revenue
        FROM TransactionDetail td
        JOIN Product p ON td.ProductID = p.ProductID
        JOIN `Transaction` t ON td.TransactionID = t.TransactionID
        WHERE t.DateTime >= ?
        GROUP BY p.category
        ORDER BY total_revenue DESC
    """

    cursor.execute(query, (start_date.strftime("%Y-%m-%d %H:%M:%S"),))
    results = cursor.fetchall()
    conn.close()
    return results


def fetch_stock_data(db_manager):
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    # Get current stock and 30-day sales average
    query = """
        SELECT 
            p.productName,
            p.stockQuantity,
            COALESCE((
                SELECT AVG(daily_sales) 
                FROM (
                    SELECT SUM(td.Quantity) as daily_sales
                    FROM TransactionDetail td
                    JOIN `Transaction` t ON td.TransactionID = t.TransactionID
                    WHERE td.ProductID = p.ProductID 
                    AND t.DateTime >= date('now', '-30 days')
                    GROUP BY date(t.DateTime)
                )
            ), 0) as avg_daily_sales
        FROM Product p
        WHERE p.stockQuantity > 0
        ORDER BY p.stockQuantity ASC
        LIMIT 15
    """

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results


# EXPORT FUNCTIONS
def export_inventory_csv(db_manager):
    rows = fetch_inventory_data(db_manager)
    filepath = tk.filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")]
    )
    if filepath:
        with open(filepath, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Name", "Category", "Stock Qty", "Status"])
            writer.writerows(rows)
        messagebox.showinfo("Export Successful", f"Inventory exported to {filepath}")


def export_sales_csv(db_manager, time_filter="Today", start_date=None, end_date=None):
    transactions = fetch_recent_transactions(db_manager, time_filter, start_date, end_date)
    filepath = tk.filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")]
    )
    if filepath:
        with open(filepath, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Transaction ID", "Date & Time", "User", "Total Amount", "Payment Method"])
            writer.writerows(transactions)
        messagebox.showinfo("Export Successful", f"Sales data exported to {filepath}")


# MAIN APPLICATION
if __name__ == "__main__":
    try:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        app = ManagerDashboard()
        app.mainloop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        messagebox.showerror("Critical Error", f"The application encountered an error and will close.\nError: {str(e)}")