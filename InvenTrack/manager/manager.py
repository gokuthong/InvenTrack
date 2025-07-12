from tkinter import ttk, messagebox, filedialog
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
from matplotlib.dates import DateFormatter, HourLocator
import seaborn as sns
import subprocess
from InvenTrack.admin import login
import tempfile
from fpdf import FPDF
import tkinter as tk

# Global font configuration for consistent UI styling
FONT_CONFIG = {
    "title": ("Acumin Pro", 40, "bold"),
    "header": ("Acumin Pro", 28, "bold"),
    "subheader": ("Acumin Pro", 24, "bold"),
    "sidebar": ("Acumin Pro", 19),
    "card_title": ("Acumin Pro", 22),
    "card_value": ("Acumin Pro", 38, "bold"),
    "card_trend": ("Acumin Pro", 18),
    "table": ("Acumin Pro", 16),
    "button": ("Acumin Pro", 20),
    "label": ("Acumin Pro", 18),
    "small": ("Acumin Pro", 16)
}

# Configure application-wide logging
logging.basicConfig(
    filename='app.log',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class DatabaseManager:
    """Handles all database operations with proper error handling and connection management"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.initialize_database()

    def initialize_database(self):
        """Ensure database directory exists and is accessible"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")

    def execute_query(self, query, params=()):
        """Execute SQL query with proper connection handling and error reporting"""
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


class Sidebar(ctk.CTkFrame):
    """Navigation sidebar with interactive buttons and visual state tracking"""

    def __init__(self, parent, nav_commands, toggle_callback, logout_command):
        super().__init__(parent, width=180, fg_color="#2d3e50", corner_radius=0)

        # Sidebar title
        ctk.CTkLabel(
            self,
            text="InvenTrack",
            font=FONT_CONFIG["header"],
            text_color="#fff"
        ).place(x=20, y=20)

        # Track button states for visual feedback
        self.sidebar_buttons = {}
        self.current_button = "Dashboard"

        # Create navigation buttons
        y = 80
        for name in ["Dashboard", "Inventory Report", "Sales Report", "Data Analytics", "Log Out"]:
            if name == "Log Out":
                btn = ctk.CTkButton(
                    self,
                    text="🔒 " + name,
                    width=160,
                    height=50,
                    corner_radius=10,
                    fg_color="transparent",
                    hover_color="#4A6374",
                    text_color="#FFFFFF",
                    font=FONT_CONFIG["sidebar"],
                    command=logout_command
                )
                btn.place(x=10, y=900)
            else:
                btn = ctk.CTkButton(
                    self,
                    text=name,
                    width=160,
                    height=50,
                    corner_radius=10,
                    fg_color="#34495E" if name == "Dashboard" else "transparent",
                    hover_color="#3E5870" if name == "Dashboard" else "#4A6374",
                    text_color="#FFFFFF" if name == "Dashboard" else "#FFFFFF",
                    font=FONT_CONFIG["sidebar"],
                    command=lambda n=name: self.button_clicked(n, nav_commands.get(n.lower().replace(" ", "_"),
                                                                                   lambda: None))
                )
                btn.place(x=10, y=y)
                y += 70
            self.sidebar_buttons[name] = btn

    def button_clicked(self, button_name, command):
        """Update button states and execute navigation command"""
        if button_name == "Log Out":
            command()
            return

        for name, btn in self.sidebar_buttons.items():
            if name != "Log Out":
                is_current = (name == button_name)
                btn.configure(
                    fg_color="#34495E" if is_current else "transparent",
                    hover_color="#3E5870" if is_current else "#4A6374",
                    text_color="#FFFFFF" if is_current else "#FFFFFF"
                )
        self.current_button = button_name
        command()


class Header(ctk.CTkFrame):
    """Application header with title, sidebar toggle, and profile button"""

    def __init__(self, parent, title, sidebar_toggle_callback, profile_command=None):
        super().__init__(parent, fg_color="#2d3e50", width=1920, height=55)

        # Sidebar toggle button
        self.toggle_btn = ctk.CTkButton(
            self,
            text="☰",
            width=45,
            height=45,
            corner_radius=0,
            fg_color="#2d3e50",
            hover_color="#2d3e50",
            text_color="#fff",
            font=FONT_CONFIG["button"],
            command=sidebar_toggle_callback
        )
        self.toggle_btn.place(x=12, y=6)

        # Application logo
        try:
            logo_img = Image.open(Path(__file__).parent / "pictures/logo.png")
            logo_img = logo_img.resize((40, 40))
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            self.logo_label = ctk.CTkLabel(self, image=self.logo_photo, text="")
            self.logo_label.place(x=65, y=5)
        except Exception as e:
            logging.error(f"Failed to load logo: {e}")
            self.logo_label = None

        # Title display
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=FONT_CONFIG["header"],
            text_color="#fff"
        )
        self.title_label.place(x=115, y=10)

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
            font=FONT_CONFIG["button"],
            command=profile_command
        )
        self.profile_btn.place(x=1800, y=10)


class SummaryCard(ctk.CTkFrame):
    """Reusable card component for displaying key metrics with icons and trends"""

    def __init__(self, parent, title, initial_value, icon, color, trend=None):
        super().__init__(parent, fg_color="white", corner_radius=15, border_width=1, border_color="#e0e0e0")
        self.grid_propagate(False)
        self.configure(width=280, height=200)

        # Card layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)

        # Icon display
        icon_frame = ctk.CTkFrame(content_frame, fg_color=color, corner_radius=10, width=50, height=50)
        icon_frame.grid(row=0, column=0, rowspan=2, padx=(0, 15), pady=5, sticky="nw")
        ctk.CTkLabel(icon_frame, text=icon, font=FONT_CONFIG["button"], text_color="white").place(relx=0.5, rely=0.5,
                                                                                                  anchor="center")

        # Title and value display
        title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=FONT_CONFIG["card_title"],
            text_color="#7f8c8d",
            anchor="w"
        )
        title_label.grid(row=0, column=1, sticky="w")

        self.value_label = ctk.CTkLabel(
            content_frame,
            text=initial_value,
            font=FONT_CONFIG["card_value"],
            text_color="#2c3e50",
            anchor="w"
        )
        self.value_label.grid(row=1, column=1, sticky="w")

        # Trend indicator (optional)
        if trend:
            trend_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            trend_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

            trend_color = "#27ae60" if trend[0] == "+" else "#e74c3c"
            trend_icon = "↑" if trend[0] == "+" else "↓"

            ctk.CTkLabel(trend_frame, text=trend_icon, font=FONT_CONFIG["small"], text_color=trend_color).pack(
                side="left", padx=(0, 5))
            self.trend_label = ctk.CTkLabel(
                trend_frame,
                text=trend,
                font=FONT_CONFIG["card_trend"],
                text_color=trend_color
            )
            self.trend_label.pack(side="left")

    def update_value(self, new_value):
        """Update the displayed metric value"""
        self.value_label.configure(text=new_value)

    def update_trend(self, new_trend):
        """Update the trend indicator if present"""
        if hasattr(self, 'trend_label'):
            trend_color = "#27ae60" if new_trend[0] == "+" else "#e74c3c"
            self.trend_label.configure(text=new_trend, text_color=trend_color)


class LowStockItem(ctk.CTkFrame):
    """Compact display component for low stock items with status indicators"""

    def __init__(self, parent, product_name, category, current_stock, status):
        super().__init__(parent, fg_color="white", corner_radius=10, border_width=1, border_color="#e0e0e0")
        self.configure(height=60)

        # Status indicator with color coding
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

        # Product details layout
        details_frame = ctk.CTkFrame(self, fg_color="transparent")
        details_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Name and category display
        name_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        name_frame.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(name_frame, text=product_name, font=("Acumin Pro", 18, "bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(name_frame, text=category, font=FONT_CONFIG["small"], text_color="#7f8c8d", anchor="w").pack(
            side="right", padx=10)

        # Stock information display
        stock_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        stock_frame.pack(fill="x")

        ctk.CTkLabel(stock_frame, text=f"Current Stock: {current_stock}", font=FONT_CONFIG["small"], anchor="w").pack(
            side="left")
        ctk.CTkLabel(stock_frame, text=status, font=FONT_CONFIG["small"], text_color=status_color, anchor="w").pack(
            side="right", padx=10)


class AnalyticsPage(ctk.CTkFrame):
    """Interactive data analytics dashboard with multiple visualization options"""

    def __init__(self, parent, db_manager):
        super().__init__(parent, fg_color="transparent")
        self.db_manager = db_manager

        # Main container layout
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=65, pady=(20, 50))

        # Page title
        ctk.CTkLabel(
            container,
            text="Data & Analytics",
            font=FONT_CONFIG["title"],
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 20))

        # Filter controls section
        filter_frame = ctk.CTkFrame(container, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 20))

        # Time period filter
        self.time_filter_var = ctk.StringVar(value="This Month")
        options = ["Today", "This Week", "This Month", "This Quarter", "This Year", "All Time"]
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.time_filter_var,
            values=options,
            command=self.update_analytics,
            width=150,
            font=FONT_CONFIG["button"]
        ).pack(side="left", padx=(0, 10))

        # Chart type selector
        self.chart_type_var = ctk.StringVar(value="Revenue Trend")
        chart_options = ["Revenue Trend", "Top Products", "Category Performance", "Stock Forecast"]
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.chart_type_var,
            values=chart_options,
            command=self.update_analytics,
            width=200,
            font=FONT_CONFIG["button"]
        ).pack(side="left", padx=(0, 10))

        # Data export buttons
        ctk.CTkButton(
            filter_frame,
            text="Export Data",
            command=self.export_analytics_data,
            fg_color="#3498db",
            hover_color="#2980b9",
            font=FONT_CONFIG["button"]
        ).pack(side="right")

        ctk.CTkButton(
            filter_frame,
            text="Export PDF",
            command=self.export_analytics_pdf,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=FONT_CONFIG["button"]
        ).pack(side="right", padx=(0, 10))

        # Charts display area
        charts_frame = ctk.CTkFrame(container, fg_color="transparent")
        charts_frame.pack(fill="both", expand=True)
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_rowconfigure(0, weight=1)

        # Primary chart container
        self.chart_frame = ctk.CTkFrame(charts_frame, fg_color="white", corner_radius=15)
        self.chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.chart_frame.grid_rowconfigure(1, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        # Secondary chart container
        self.secondary_chart_frame = ctk.CTkFrame(charts_frame, fg_color="white", corner_radius=15)
        self.secondary_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.secondary_chart_frame.grid_rowconfigure(1, weight=1)
        self.secondary_chart_frame.grid_columnconfigure(0, weight=1)

        # KPI metrics display area
        self.kpi_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(20, 0))

        # Initialize chart display
        self.create_charts()
        self.update_analytics()

    def create_charts(self):
        """Setup the chart display areas with headers and controls"""
        # Primary chart header and controls
        self.primary_header = ctk.CTkFrame(self.chart_frame, fg_color="transparent", height=40)
        self.primary_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)
        self.primary_title = ctk.CTkLabel(
            self.primary_header,
            text="",
            font=FONT_CONFIG["subheader"],
            text_color="#2c3e50"
        )
        self.primary_title.pack(side="left")

        # Primary chart canvas area
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

        # Secondary chart header and controls
        self.secondary_header = ctk.CTkFrame(self.secondary_chart_frame, fg_color="transparent", height=40)
        self.secondary_header.grid(row=0, column=0, sticky="ew", padx=15, pady=5)
        self.secondary_title = ctk.CTkLabel(
            self.secondary_header,
            text="",
            font=FONT_CONFIG["subheader"],
            text_color="#2c3e50"
        )
        self.secondary_title.pack(side="left")

        # Secondary chart canvas area
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

        # Chart zoom controls
        primary_zoom_btn = ctk.CTkButton(
            self.primary_header,
            text="🔍",
            width=30,
            height=30,
            command=lambda: self.zoom_chart("primary")
        )
        primary_zoom_btn.pack(side="right", padx=5)

        secondary_zoom_btn = ctk.CTkButton(
            self.secondary_header,
            text="🔍",
            width=30,
            height=30,
            command=lambda: self.zoom_chart("secondary")
        )
        secondary_zoom_btn.pack(side="right", padx=5)

    def export_analytics_pdf(self):
        """Generate a PDF report of the current analytics view"""
        chart_type = self.chart_type_var.get()
        time_filter = self.time_filter_var.get()

        try:
            # Generate appropriate charts based on current view
            if chart_type == "Revenue Trend":
                fig1, fig2, kpi_data = self.generate_revenue_trend_chart(time_filter, full_size=True, for_pdf=True)
            elif chart_type == "Top Products":
                fig1, fig2, kpi_data = self.generate_top_products_chart(time_filter, full_size=True, for_pdf=True)
            elif chart_type == "Category Performance":
                fig1, fig2, kpi_data = self.generate_category_performance_chart(time_filter, full_size=True,
                                                                                for_pdf=True)
            elif chart_type == "Stock Forecast":
                fig1, fig2, kpi_data = self.generate_stock_forecast_chart(full_size=True, for_pdf=True)
            else:
                return

            # Create PDF document
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Analytics Report: {chart_type} - {time_filter}", 0, 1, 'C')

            # Save charts to temporary files and embed in PDF
            with tempfile.TemporaryDirectory() as tmpdir:
                fig1_path = os.path.join(tmpdir, "chart1.png")
                fig1.savefig(fig1_path, bbox_inches='tight')
                pdf.image(fig1_path, x=10, y=30, w=190)

                fig2_path = os.path.join(tmpdir, "chart2.png")
                fig2.savefig(fig2_path, bbox_inches='tight')
                pdf.image(fig2_path, x=10, y=160, w=190)

                # Add KPI metrics section
                pdf.set_y(300)
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Key Performance Indicators", 0, 1)
                pdf.set_font("Arial", '', 12)
                for title, value in kpi_data:
                    pdf.cell(0, 10, f"{title}: {value}", 0, 1)

                # Save PDF to user-selected location
                filename = f"analytics_{chart_type}_{time_filter}.pdf".replace(" ", "_")
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf")],
                    initialfile=filename
                )
                if filepath:
                    pdf.output(filepath)
                    messagebox.showinfo("Success", f"Exported to {filepath}")

            plt.close(fig1)
            plt.close(fig2)

        except Exception as e:
            logging.error(f"PDF export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export PDF: {str(e)}")

    def generate_revenue_trend_chart(self, time_filter, full_size=False, for_pdf=False):
        """Generate revenue trend visualization with time series data"""
        data = fetch_revenue_data(self.db_manager, time_filter)
        if not data:
            return None, None, None

        dates = [row[0] for row in data]
        revenues = [row[1] for row in data]
        volumes = [row[2] for row in data]

        # Create figures with appropriate sizing
        fig_size = (12, 8) if full_size else (6, 4)
        fig1, ax1 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')
        fig2, ax2 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')

        # Revenue trend line chart
        ax1.plot(dates, revenues, marker='o', color='#3498db', linewidth=2.5)
        ax1.set_title('Revenue Trend', fontsize=14)
        ax1.set_ylabel('Revenue (RM)')
        ax1.grid(True, linestyle='--', alpha=0.7)

        # Sales volume bar chart
        ax2.bar(dates, volumes, color='#2ecc71')
        ax2.set_title('Sales Volume', fontsize=14)
        ax2.set_ylabel('Items Sold')
        ax2.grid(True, linestyle='--', alpha=0.7)

        # Format x-axis based on time period
        if time_filter == "Today":
            ax1.xaxis.set_major_locator(HourLocator(interval=2))
            ax1.xaxis.set_major_formatter(DateFormatter("%I %p"))
            ax2.xaxis.set_major_locator(HourLocator(interval=2))
            ax2.xaxis.set_major_formatter(DateFormatter("%I %p"))
        elif time_filter in ["This Week", "This Month"]:
            ax1.xaxis.set_major_formatter(DateFormatter("%b %d"))
            ax2.xaxis.set_major_formatter(DateFormatter("%b %d"))
        elif time_filter == "This Quarter":
            ax1.xaxis.set_major_formatter(DateFormatter("%b"))
            ax2.xaxis.set_major_formatter(DateFormatter("%b"))
        elif time_filter == "This Year":
            ax1.xaxis.set_major_formatter(DateFormatter("%b"))
            ax2.xaxis.set_major_formatter(DateFormatter("%b"))

        plt.setp(ax1.get_xticklabels(), rotation=45)
        plt.setp(ax2.get_xticklabels(), rotation=45)

        # Calculate KPIs for display
        total_revenue = sum(revenues)
        avg_daily = total_revenue / len(revenues) if revenues else 0
        max_revenue = max(revenues) if revenues else 0
        growth = ((revenues[-1] - revenues[0]) / revenues[0] * 100) if len(revenues) > 1 and revenues[0] != 0 else 0

        kpi_data = [
            ("Total Revenue", f"RM{total_revenue:,.2f}"),
            ("Avg Daily", f"RM{avg_daily:,.2f}"),
            ("Peak Revenue", f"RM{max_revenue:,.2f}"),
            ("Growth", f"{growth:.1f}%")
        ]

        return fig1, fig2, kpi_data

    def generate_top_products_chart(self, time_filter, full_size=False, for_pdf=False):
        """Generate visualizations for top performing products"""
        data = fetch_top_products(self.db_manager, time_filter)
        if not data:
            return None, None, None

        products = [row[0] for row in data]
        quantities = [row[1] for row in data]
        revenues = [row[2] for row in data]

        fig_size = (12, 8) if full_size else (6, 4)
        fig1, ax1 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')
        fig2, ax2 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')

        # Horizontal bar chart of top products
        ax1.barh(products, quantities, color='#3498db')
        ax1.set_title('Top Selling Products', fontsize=14)
        ax1.set_xlabel('Quantity Sold')
        ax1.grid(True, linestyle='--', alpha=0.7)

        # Pie chart of revenue contribution
        ax2.pie(revenues, labels=products, autopct='%1.1f%%',
                startangle=90, colors=plt.cm.Pastel1.colors)
        ax2.set_title('Revenue Contribution', fontsize=14)
        ax2.axis('equal')

        # Calculate KPIs
        total_revenue = sum(revenues)
        top_product = products[0] if products else "N/A"
        top_revenue = revenues[0] if revenues else 0
        top_percent = (top_revenue / total_revenue * 100) if total_revenue > 0 else 0

        kpi_data = [
            ("Total Revenue", f"RM{total_revenue:,.2f}"),
            ("Top Product", top_product),
            ("Top Product Revenue", f"RM{top_revenue:,.2f}"),
            ("Top Product Share", f"{top_percent:.1f}%")
        ]

        return fig1, fig2, kpi_data

    def generate_category_performance_chart(self, time_filter, full_size=False, for_pdf=False):
        """Generate category performance comparison charts"""
        data = fetch_category_performance(self.db_manager, time_filter)
        if not data:
            return None, None, None

        categories = [row[0] for row in data]
        quantities = [row[1] for row in data]
        revenues = [row[2] for row in data]

        fig_size = (12, 8) if full_size else (6, 4)
        fig1, ax1 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')
        fig2, ax2 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')

        # Category sales volume
        ax1.bar(categories, quantities, color='#3498db')
        ax1.set_title('Category Sales Volume', fontsize=14)
        ax1.set_ylabel('Items Sold')
        ax1.grid(True, linestyle='--', alpha=0.7)
        plt.setp(ax1.get_xticklabels(), rotation=45)

        # Category revenue comparison
        ax2.bar(categories, revenues, color='#2ecc71')
        ax2.set_title('Category Revenue', fontsize=14)
        ax2.set_ylabel('Revenue (RM)')
        ax2.grid(True, linestyle='--', alpha=0.7)
        plt.setp(ax2.get_xticklabels(), rotation=45)

        # Calculate KPIs
        total_revenue = sum(revenues)
        top_category = categories[0] if categories else "N/A"
        top_category_rev = revenues[0] if revenues else 0
        top_percent = (top_category_rev / total_revenue * 100) if total_revenue > 0 else 0

        kpi_data = [
            ("Total Revenue", f"RM{total_revenue:,.2f}"),
            ("Top Category", top_category),
            ("Top Category Revenue", f"RM{top_category_rev:,.2f}"),
            ("Top Category Share", f"{top_percent:.1f}%")
        ]

        return fig1, fig2, kpi_data

    def generate_stock_forecast_chart(self, full_size=False, for_pdf=False):
        """Generate inventory stock level and forecast visualizations"""
        data = fetch_stock_data(self.db_manager)
        if not data:
            return None, None, None

        products = [row[0] for row in data]
        current_stock = [row[1] for row in data]
        avg_daily_sales = [row[2] for row in data]

        # Calculate days of supply remaining
        days_of_supply = [stock / sales if sales > 0 else 0 for stock, sales in zip(current_stock, avg_daily_sales)]

        fig_size = (12, 8) if full_size else (6, 4)
        fig1, ax1 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')
        fig2, ax2 = plt.subplots(figsize=fig_size, facecolor='#f8f9fa')

        # Color coding based on stock status
        colors = []
        for days in days_of_supply:
            if days < 7:
                colors.append('#e74c3c')  # Critical (red)
            elif days < 14:
                colors.append('#f39c12')  # Low (orange)
            else:
                colors.append('#2ecc71')  # Sufficient (green)

        # Current stock levels visualization
        ax1.barh(products, current_stock, color=colors)
        ax1.set_title('Current Stock Levels', fontsize=14)
        ax1.set_xlabel('Quantity in Stock')
        ax1.grid(True, linestyle='--', alpha=0.7)

        # Days of supply forecast visualization
        sorted_indices = np.argsort(days_of_supply)
        sorted_products = [products[i] for i in sorted_indices]
        sorted_days = [days_of_supply[i] for i in sorted_indices]

        ax2.barh(sorted_products, sorted_days, color=[colors[i] for i in sorted_indices])
        ax2.set_title('Days of Supply Forecast', fontsize=14)
        ax2.set_xlabel('Days Remaining')
        ax2.axvline(x=7, color='#e74c3c', linestyle='--', alpha=0.7)
        ax2.axvline(x=14, color='#f39c12', linestyle='--', alpha=0.7)
        ax2.text(7.5, len(products) - 0.5, 'Critical', color='#e74c3c')
        ax2.text(14.5, len(products) - 0.5, 'Low', color='#f39c12')
        ax2.grid(True, linestyle='--', alpha=0.7)

        # Calculate inventory KPIs
        low_stock_count = sum(1 for days in days_of_supply if days < 14)
        critical_count = sum(1 for days in days_of_supply if days < 7)
        avg_days_supply = sum(days_of_supply) / len(days_of_supply) if days_of_supply else 0

        kpi_data = [
            ("Products Analyzed", str(len(products))),
            ("Low Stock Items", str(low_stock_count)),
            ("Critical Items", str(critical_count)),
            ("Avg Days Supply", f"{avg_days_supply:.1f} days")
        ]

        return fig1, fig2, kpi_data

    def create_full_size_chart(self, chart_type):
        """Generate a larger version of a chart for zoomed view"""
        time_filter = self.time_filter_var.get()
        chart_type_name = self.chart_type_var.get()

        if chart_type_name == "Revenue Trend":
            fig1, fig2, kpi_data = self.generate_revenue_trend_chart(time_filter, full_size=True)
            return fig1 if chart_type == "primary" else fig2
        elif chart_type_name == "Top Products":
            fig1, fig2, kpi_data = self.generate_top_products_chart(time_filter, full_size=True)
            return fig1 if chart_type == "primary" else fig2
        elif chart_type_name == "Category Performance":
            fig1, fig2, kpi_data = self.generate_category_performance_chart(time_filter, full_size=True)
            return fig1 if chart_type == "primary" else fig2
        elif chart_type_name == "Stock Forecast":
            fig1, fig2, kpi_data = self.generate_stock_forecast_chart(full_size=True)
            return fig1 if chart_type == "primary" else fig2
        return None

    def zoom_chart(self, chart_type):
        """Display a larger version of the selected chart in a new window"""
        zoom_window = ctk.CTkToplevel(self)
        zoom_window.geometry("800x600")
        zoom_window.title(f"Zoomed Chart - {chart_type.capitalize()} View")

        fig = self.create_full_size_chart(chart_type)
        if fig:
            canvas = FigureCanvasTkAgg(fig, master=zoom_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(zoom_window, text="No chart data available").pack()

    def update_analytics(self, event=None):
        """Refresh all analytics displays based on current filters"""
        time_filter = self.time_filter_var.get()
        chart_type = self.chart_type_var.get()

        # Clear existing displays
        for widget in self.primary_chart_canvas_frame.winfo_children():
            widget.destroy()
        for widget in self.secondary_chart_canvas_frame.winfo_children():
            widget.destroy()
        for widget in self.kpi_frame.winfo_children():
            widget.destroy()

        # Load appropriate visualization based on selection
        if chart_type == "Revenue Trend":
            self.show_revenue_trend(time_filter)
        elif chart_type == "Top Products":
            self.show_top_products(time_filter)
        elif chart_type == "Category Performance":
            self.show_category_performance(time_filter)
        elif chart_type == "Stock Forecast":
            self.show_stock_forecast()

    def show_revenue_trend(self, time_filter):
        """Display revenue trend visualization"""
        self.primary_title.configure(text="Revenue Trend")
        self.secondary_title.configure(text="Sales Volume")

        revenue_data = fetch_revenue_data(self.db_manager, time_filter)

        if not revenue_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No revenue data available",
                text_color="#7f8c8d",
                font=FONT_CONFIG["label"]
            ).pack(expand=True)
            return

        dates = [row[0] for row in revenue_data]
        revenues = [row[1] for row in revenue_data]
        volumes = [row[2] for row in revenue_data]

        # Primary chart - Revenue trend
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax1.plot(dates, revenues, marker='o', color='#3498db', linewidth=2.5)
        ax1.set_title('Revenue Trend', fontsize=14)
        ax1.set_ylabel('Revenue (RM)')
        ax1.grid(True, linestyle='--', alpha=0.7)

        # Secondary chart - Sales volume
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax2.bar(dates, volumes, color='#2ecc71')
        ax2.set_title('Sales Volume', fontsize=14)
        ax2.set_ylabel('Items Sold')
        ax2.grid(True, linestyle='--', alpha=0.7)

        # Format time axis appropriately
        if time_filter == "Today":
            ax1.xaxis.set_major_locator(HourLocator(interval=2))
            ax1.xaxis.set_major_formatter(DateFormatter("%I %p"))
            ax2.xaxis.set_major_locator(HourLocator(interval=2))
            ax2.xaxis.set_major_formatter(DateFormatter("%I %p"))
        elif time_filter in ["This Week", "This Month"]:
            ax1.xaxis.set_major_formatter(DateFormatter("%b %d"))
            ax2.xaxis.set_major_formatter(DateFormatter("%b %d"))
        elif time_filter == "This Quarter":
            ax1.xaxis.set_major_formatter(DateFormatter("%b"))
            ax2.xaxis.set_major_formatter(DateFormatter("%b"))
        elif time_filter == "This Year":
            ax1.xaxis.set_major_formatter(DateFormatter("%b"))
            ax2.xaxis.set_major_formatter(DateFormatter("%b"))

        plt.setp(ax1.get_xticklabels(), rotation=45)
        plt.setp(ax2.get_xticklabels(), rotation=45)

        # Display charts in UI
        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate and display KPIs
        total_revenue = sum(revenues)
        avg_daily = total_revenue / len(revenues) if revenues else 0
        max_revenue = max(revenues) if revenues else 0
        growth = ((revenues[-1] - revenues[0]) / revenues[0] * 100) if len(revenues) > 1 and revenues[0] != 0 else 0

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
        """Display top products visualization"""
        self.primary_title.configure(text="Top Selling Products")
        self.secondary_title.configure(text="Revenue Contribution")

        product_data = fetch_top_products(self.db_manager, time_filter)

        if not product_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No product data available",
                text_color="#7f8c8d",
                font=FONT_CONFIG["label"]
            ).pack(expand=True)
            return

        products = [row[0] for row in product_data]
        quantities = [row[1] for row in product_data]
        revenues = [row[2] for row in product_data]

        # Primary chart - Top products bar chart
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax1.barh(products, quantities, color='#3498db')
        ax1.set_title('Top Selling Products', fontsize=14)
        ax1.set_xlabel('Quantity Sold')
        ax1.grid(True, linestyle='--', alpha=0.7)

        # Secondary chart - Revenue pie chart
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax2.pie(revenues, labels=products, autopct='%1.1f%%',
                startangle=90, colors=plt.cm.Pastel1.colors)
        ax2.set_title('Revenue Contribution', fontsize=14)
        ax2.axis('equal')

        # Display charts
        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate and display KPIs
        total_revenue = sum(revenues)
        top_product = products[0]
        top_revenue = revenues[0]
        top_percent = (top_revenue / total_revenue * 100) if total_revenue > 0 else 0

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
        """Display category performance visualization"""
        self.primary_title.configure(text="Category Sales")
        self.secondary_title.configure(text="Category Revenue")

        category_data = fetch_category_performance(self.db_manager, time_filter)

        if not category_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No category data available",
                text_color="#7f8c8d",
                font=FONT_CONFIG["label"]
            ).pack(expand=True)
            return

        categories = [row[0] for row in category_data]
        quantities = [row[1] for row in category_data]
        revenues = [row[2] for row in category_data]

        # Primary chart - Category sales volume
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax1.bar(categories, quantities, color='#3498db')
        ax1.set_title('Category Sales Volume', fontsize=14)
        ax1.set_ylabel('Items Sold')
        ax1.grid(True, linestyle='--', alpha=0.7)
        plt.setp(ax1.get_xticklabels(), rotation=45)

        # Secondary chart - Category revenue
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax2.bar(categories, revenues, color='#2ecc71')
        ax2.set_title('Category Revenue', fontsize=14)
        ax2.set_ylabel('Revenue (RM)')
        ax2.grid(True, linestyle='--', alpha=0.7)
        plt.setp(ax2.get_xticklabels(), rotation=45)

        # Display charts
        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate and display KPIs
        total_revenue = sum(revenues)
        top_category = categories[0]
        top_category_rev = revenues[0]
        top_percent = (top_category_rev / total_revenue * 100) if total_revenue > 0 else 0

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
        """Display inventory stock forecast visualization"""
        self.primary_title.configure(text="Stock Level Analysis")
        self.secondary_title.configure(text="Demand Forecast")

        stock_data = fetch_stock_data(self.db_manager)

        if not stock_data:
            ctk.CTkLabel(
                self.primary_chart_canvas_frame,
                text="No stock data available",
                text_color="#7f8c8d",
                font=FONT_CONFIG["label"]
            ).pack(expand=True)
            return

        products = [row[0] for row in stock_data]
        current_stock = [row[1] for row in stock_data]
        avg_daily_sales = [row[2] for row in stock_data]

        # Calculate days of supply remaining
        days_of_supply = [stock / sales if sales > 0 else 0 for stock, sales in zip(current_stock, avg_daily_sales)]

        # Color coding based on stock status
        colors = []
        for days in days_of_supply:
            if days < 7:
                colors.append('#e74c3c')  # Critical
            elif days < 14:
                colors.append('#f39c12')  # Low
            else:
                colors.append('#2ecc71')  # Sufficient

        # Primary chart - Current stock levels
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        ax1.barh(products, current_stock, color=colors)
        ax1.set_title('Current Stock Levels', fontsize=14)
        ax1.set_xlabel('Quantity in Stock')
        ax1.grid(True, linestyle='--', alpha=0.7)

        # Secondary chart - Days of supply forecast
        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#f8f9fa')
        sorted_indices = np.argsort(days_of_supply)
        sorted_products = [products[i] for i in sorted_indices]
        sorted_days = [days_of_supply[i] for i in sorted_indices]

        ax2.barh(sorted_products, sorted_days, color=[colors[i] for i in sorted_indices])
        ax2.set_title('Days of Supply Forecast', fontsize=14)
        ax2.set_xlabel('Days Remaining')
        ax2.axvline(x=7, color='#e74c3c', linestyle='--', alpha=0.7)
        ax2.axvline(x=14, color='#f39c12', linestyle='--', alpha=0.7)
        ax2.text(7.5, len(products) - 0.5, 'Critical', color='#e74c3c')
        ax2.text(14.5, len(products) - 0.5, 'Low', color='#f39c12')
        ax2.grid(True, linestyle='--', alpha=0.7)

        # Display charts
        canvas1 = FigureCanvasTkAgg(fig1, master=self.primary_chart_canvas_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        canvas2 = FigureCanvasTkAgg(fig2, master=self.secondary_chart_canvas_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Calculate and display KPIs
        low_stock_count = sum(1 for days in days_of_supply if days < 14)
        critical_count = sum(1 for days in days_of_supply if days < 7)
        avg_days_supply = sum(days_of_supply) / len(days_of_supply) if days_of_supply else 0

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
        """Export current analytics data to CSV file"""
        chart_type = self.chart_type_var.get()
        time_filter = self.time_filter_var.get()

        # Get appropriate data based on current view
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

        # Save to user-selected file
        filepath = filedialog.asksaveasfilename(
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
    """Main application window with navigation and content management"""

    def __init__(self):
        super().__init__()
        self.title("Manager Dashboard")
        # Fullscreen setup
        width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{width}x{height}+0+0")

        # Database setup
        self.db_path = Path(__file__).parent.parent / "inventoryproject.db"
        self.db_manager = DatabaseManager(self.db_path)
        self.sidebar_visible = True

        # Navigation commands mapping
        nav_cmds = {
            "dashboard": lambda: self.show_page("dashboard"),
            "inventory_report": lambda: self.show_page("inventory_report"),
            "sales_report": lambda: self.show_page("sales_report"),
            "data_analytics": lambda: self.show_page("data_analytics")
        }

        # UI components
        self.header = Header(self, "Manager Dashboard", self.toggle_sidebar, self.goto_profile)
        self.header.pack(side="top", fill="x")
        self.sidebar = Sidebar(self, nav_cmds, self.toggle_sidebar, self.logout_command)
        self.sidebar.pack(side="left", fill="y")

        # Main content area with background
        self.main = ctk.CTkFrame(self, fg_color="lightblue")
        self.main.pack(side="right", fill="both", expand=True)
        self._set_main_background(Path(__file__).parent / "pictures/wmremove-transformed.jpeg")

        # Page container
        self.page_container = ctk.CTkFrame(self.main, fg_color="transparent")
        self.page_container.pack(fill="both", expand=True)

        # Initialize all pages
        self.pages = {}
        self.create_dashboard_page()
        self.create_inventory_report_page()
        self.create_sales_report_page()
        self.create_data_analytics_page()
        self.show_page("dashboard")

    def logout_command(self):
        """Handle user logout by clearing session and returning to login screen"""
        session_file = self.db_path.parent / "user_session.json"
        try:
            with open(session_file, "w") as f:
                f.write("{}")  # Clear session data
        except Exception as e:
            logging.error(f"Failed to clear session: {e}")

        # Launch login screen
        login_script = Path(__file__).parent.parent / "admin/login.py"
        if os.path.exists(login_script):
            subprocess.Popen(['python', login_script])
            self.destroy()
        else:
            messagebox.showerror("Error", "Login page not found!")

    def goto_profile(self):
        """Navigate to user profile screen"""
        try:
            self.destroy()
            current_dir = Path(__file__).parent.parent
            profile_script = current_dir / "admin/Profile page.py"

            if profile_script.exists():
                subprocess.Popen(['python', str(profile_script)])
            else:
                messagebox.showerror("Error", "Profile page not found!")
                app = ManagerDashboard()
                app.mainloop()
        except Exception as e:
            logging.error(f"Error switching to profile: {e}")
            messagebox.showerror("Navigation Error", "Failed to open profile page")
            app = ManagerDashboard()
            app.mainloop()

    def _set_main_background(self, bg_path):
        """Set the faded background image for main content area"""
        try:
            img = Image.open(bg_path).convert("RGBA")
            img = img.resize((self.winfo_screenwidth(), self.winfo_screenheight()))
            alpha = img.split()[3].point(lambda p: int(p * 0.85))
            img.putalpha(alpha)
            self._main_bg_img = ImageTk.PhotoImage(img)
            self.main_bg_label = ctk.CTkLabel(self.main, image=self._main_bg_img, text="")
            self.main_bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            logging.error(f"Failed to load main background: {e}")

    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self.sidebar_visible:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", fill="y")
        self.sidebar_visible = not self.sidebar_visible

    def create_data_analytics_page(self):
        """Initialize the data analytics page"""
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["data_analytics"] = page
        AnalyticsPage(page, self.db_manager).pack(fill="both", expand=True)

    def show_page(self, page_name):
        """Switch between application pages"""
        for page in self.pages.values():
            page.pack_forget()
        self.pages[page_name].pack(fill="both", expand=True)

        # Update sidebar button states
        button_names = {
            "dashboard": "Dashboard",
            "inventory_report": "Inventory Report",
            "sales_report": "Sales Report",
            "data_analytics": "Data Analytics"
        }
        if page_name in button_names:
            self.sidebar.button_clicked(button_names[page_name], lambda: None)

        # Update header title
        titles = {
            "dashboard": "Manager Dashboard",
            "inventory_report": "Inventory Report",
            "sales_report": "Sales Report",
            "data_analytics": "Data Analytics"
        }
        self.header.title_label.configure(text=titles.get(page_name, ""))

    def open_profile(self):
        """Placeholder for profile functionality"""
        messagebox.showinfo("Profile", "User profile management coming soon!")

    def get_low_stock_count(self):
        """Get count of low stock items from database"""
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

    def open_add_cashier(self):
        """Navigate to add cashier screen"""
        try:
            self.destroy()
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cashier_script = os.path.join(current_dir, "Add cashier.py")

            if os.path.exists(cashier_script):
                subprocess.Popen(['python', cashier_script])
            else:
                messagebox.showerror("Error", "Add cashier.py not found in the same directory!")
                app = ManagerDashboard()
                app.mainloop()
        except Exception as e:
            logging.error(f"Error opening Add Cashier: {e}")
            messagebox.showerror("Error", f"Failed to open Add Cashier page: {str(e)}")
            app = ManagerDashboard()
            app.mainloop()

    def create_dashboard_page(self):
        """Initialize the dashboard page with summary cards and charts"""
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["dashboard"] = page

        # Main container layout
        container = ctk.CTkFrame(page, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=65, pady=(20, 50))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=0)
        container.grid_rowconfigure(1, weight=0)
        container.grid_rowconfigure(2, weight=1)
        container.grid_rowconfigure(3, weight=0)

        # Welcome section
        welcome_frame = ctk.CTkFrame(container, fg_color="transparent")
        welcome_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            welcome_frame,
            text="Welcome to Manager Dashboard",
            font=FONT_CONFIG["title"],
            text_color="#2c3e50"
        ).pack(side="left")

        # Add Cashier button
        add_cashier_btn = ctk.CTkButton(
            welcome_frame,
            text="Add Cashier",
            font=FONT_CONFIG["button"],
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=self.open_add_cashier
        )
        add_cashier_btn.pack(side="right", padx=20)

        # Summary cards section
        cards_frame = ctk.CTkFrame(container, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        for i in range(3):
            cards_frame.columnconfigure(i, weight=1, uniform="cards")

        # Get data for cards
        total_sales, total_revenue, avg_order_value = fetch_sales_data(self.db_manager, "All Time")
        low_count = self.get_low_stock_count()

        # Create and position summary cards
        self.summary_cards = {
            "revenue": SummaryCard(cards_frame, "Total Revenue", f"RM{total_revenue:,.2f}", "💰", "#2ecc71"),
            "sales": SummaryCard(cards_frame, "Products Sold", str(total_sales), "📦", "#3498db"),
            "low_stock": SummaryCard(cards_frame, "Low Stock Items", str(low_count), "⚠️", "#f39c12")
        }
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
            font=FONT_CONFIG["subheader"],
            text_color="#2c3e50"
        ).pack(side="left")

        # Chart display area
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
            font=FONT_CONFIG["subheader"],
            text_color="#2c3e50"
        ).pack(side="left")

        # Scrollable alerts content
        self.alerts_scroll_frame = ctk.CTkScrollableFrame(
            alerts_frame,
            fg_color="#f8f9fa",
            corner_radius=10
        )
        self.alerts_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10), ipadx=10, ipady=10)
        self.load_low_stock_items()

        # Recent transactions section
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
            font=FONT_CONFIG["subheader"],
            text_color="#2c3e50"
        ).pack(side="left")

        # Transactions content
        activity_content = ctk.CTkFrame(activity_frame, fg_color="transparent")
        activity_content.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Transactions table
        cols = ("Transaction ID", "Date & Time", "User", "Total Amount", "Payment Method")
        tv = ttk.Treeview(activity_content, columns=cols, show="headings", height=5)

        # Configure table style
        style = ttk.Style()
        style.configure("Treeview", font=FONT_CONFIG["table"], rowheight=30)
        style.configure("Treeview.Heading", font=("Acumin Pro", 18, "bold"))

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

        # View more button
        ctk.CTkButton(
            activity_content,
            text="View More",
            font=FONT_CONFIG["button"],
            fg_color="#1ecadc",
            hover_color="#0895a4",
            command=lambda: self.show_page("sales_report")
        ).pack(pady=5)

    def generate_sales_chart(self):
        """Generate sales chart for dashboard overview"""
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

            # Clear and redraw chart
            for widget in self.chart_canvas_frame.winfo_children():
                widget.destroy()

            canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        except Exception as e:
            logging.error(f"Error generating sales chart: {e}")
            ctk.CTkLabel(
                self.chart_canvas_frame,
                text="Could not load chart data",
                text_color="#e74c3c",
                font=FONT_CONFIG["label"]
            ).pack(expand=True)

    def load_low_stock_items(self):
        """Load and display low stock items in alerts section"""
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

            # Create alert items
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
                font=FONT_CONFIG["label"]
            ).pack(pady=10)

    def create_inventory_report_page(self):
        """Initialize the inventory report page with data table"""
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["inventory_report"] = page

        # Title section
        title_frame = ctk.CTkFrame(page, fg_color="transparent")
        title_frame.pack(fill="x", padx=65, pady=(20, 0))

        ctk.CTkLabel(
            title_frame,
            text="Inventory Report",
            font=FONT_CONFIG["title"],
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))

        # Main content
        content_frame = ctk.CTkFrame(page, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 50))

        # Inventory table section
        sec = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=15)
        sec.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            sec,
            text="Detailed Inventory Report",
            font=FONT_CONFIG["subheader"],
            text_color="#2c3e50"
        ).pack(anchor="w", padx=15, pady=10)

        # Configure table style
        style = ttk.Style()
        style.configure("Treeview", font=FONT_CONFIG["table"], rowheight=30)
        style.configure("Treeview.Heading", font=("Acumin Pro", 18, "bold"))

        # Create inventory table
        cols = ("Name", "Category", "Stock Qty", "Status")
        tv = ttk.Treeview(sec, columns=cols, show="headings", height=15)
        for c in cols:
            tv.heading(c, text=c, command=lambda _col=c: treeview_sort_column(tv, _col, False))
            tv.column(c, width=200)

        # Store reference for export
        self.inventory_tree = tv

        # Add scrollbar
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

        # Export buttons
        btn_frame = ctk.CTkFrame(sec, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="Export PDF",
            command=lambda: self.export_inventory_pdf(self.inventory_tree),
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=FONT_CONFIG["button"]
        ).pack(side="right", padx=(0, 10))

    def export_inventory_pdf(self):
        """Export inventory report to PDF format"""
        try:
            rows = fetch_inventory_data(self.db_manager)

            # Create PDF document
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Inventory Report", 0, 1, 'C')

            # Add table headers
            pdf.set_font("Arial", 'B', 12)
            col_widths = [70, 40, 35, 35]
            headers = ["Name", "Category", "Stock Qty", "Status"]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
            pdf.ln()

            # Add table data
            pdf.set_font("Arial", '', 12)
            for row in rows:
                for i in range(4):
                    pdf.cell(col_widths[i], 10, str(row[i]), 1, 0, 'C')
                pdf.ln()

            # Save to user-selected location
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile="inventory_report.pdf"
            )
            if filepath:
                pdf.output(filepath)
                messagebox.showinfo("Success", f"Exported to {filepath}")

        except Exception as e:
            logging.error(f"Inventory PDF export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export inventory PDF: {str(e)}")

    def export_inventory_csv(db_manager, tree):
        """Export inventory data to CSV format"""
        try:
            # Get all rows from the treeview
            rows = []
            for item in tree.get_children():
                rows.append(tree.item(item)['values'])

            # Prompt user for save location
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile="inventory_report.csv"
            )

            if filepath:
                # Write data to CSV file
                with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Name", "Category", "Stock Qty", "Status"])
                    writer.writerows(rows)
                messagebox.showinfo("Export Successful", f"Inventory data exported to {filepath}")

        except Exception as e:
            logging.error(f"Inventory CSV export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export inventory CSV: {str(e)}")

    def create_sales_report_page(self):
        """Initialize the sales report page with filtering and data table"""
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["sales_report"] = page

        # Title section
        title_frame = ctk.CTkFrame(page, fg_color="transparent")
        title_frame.pack(fill="x", padx=65, pady=(20, 0))

        ctk.CTkLabel(
            title_frame,
            text="Sales Report",
            font=FONT_CONFIG["title"],
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))

        # Main content
        content_frame = ctk.CTkFrame(page, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 50))

        # Sales table section
        sec = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=15)
        sec.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            sec,
            text="Detailed Sales Report",
            font=FONT_CONFIG["subheader"],
            text_color="#2c3e50"
        ).pack(anchor="w", padx=15, pady=10)

        # Configure table style
        style = ttk.Style()
        style.configure("Treeview", font=FONT_CONFIG["table"], rowheight=30)
        style.configure("Treeview.Heading", font=("Acumin Pro", 18, "bold"))

        # Filter controls
        filter_frame = ctk.CTkFrame(sec, fg_color="transparent")
        filter_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.time_filter_var = ctk.StringVar(value="Today")
        options = ["Today", "This Week", "This Month", "All Time", "Custom"]
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.time_filter_var,
            values=options,
            command=self.update_sales_report,
            font=FONT_CONFIG["button"]
        ).pack(side="left", padx=(0, 10))

        # Custom date range controls (hidden by default)
        self.custom_date_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        self.custom_date_frame.pack(side="left", fill="x", expand=True)
        self.custom_date_frame.pack_forget()

        ctk.CTkLabel(self.custom_date_frame, text="From:", font=FONT_CONFIG["label"]).pack(side="left", padx=(0, 5))
        self.start_date_entry = DateEntry(
            self.custom_date_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            font=FONT_CONFIG["table"]
        )
        self.start_date_entry.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.custom_date_frame, text="To:", font=FONT_CONFIG["label"]).pack(side="left", padx=(0, 5))
        self.end_date_entry = DateEntry(
            self.custom_date_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            font=FONT_CONFIG["table"]
        )
        self.end_date_entry.pack(side="left", padx=(0, 15))

        ctk.CTkButton(
            self.custom_date_frame,
            text="Apply",
            command=lambda: self.update_sales_report(custom=True),
            width=80,
            font=FONT_CONFIG["button"]
        ).pack(side="left")

        # Export buttons
        ctk.CTkButton(
            filter_frame,
            text="Export CSV",
            command=self.export_sales_report,
            fg_color="#3498db",
            hover_color="#2980b9",
            font=FONT_CONFIG["button"]
        ).pack(side="right")

        ctk.CTkButton(
            filter_frame,
            text="Export PDF",
            command=self.export_sales_pdf,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=FONT_CONFIG["button"]
        ).pack(side="right", padx=(0, 10))

        # KPI cards
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
            self.tv.heading(c, text=c, command=lambda _col=c: treeview_sort_column(self.tv, _col, False))
            self.tv.column(c, width=200)
        scrollbar = ttk.Scrollbar(sec, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=scrollbar.set)
        self.tv.pack(side="left", fill="both", expand=True, padx=15, pady=(0, 15))
        scrollbar.pack(side="right", fill="y", padx=(0, 15), pady=(0, 15))

        # Initial data load
        self.update_sales_report()

    def export_sales_pdf(self):
        """Export sales report to PDF format"""
        try:
            # Get transactions from table
            transactions = []
            for item in self.tv.get_children():
                transactions.append(self.tv.item(item)['values'])

            # Get KPIs based on current filter
            time_filter = self.time_filter_var.get()
            start_date = end_date = None
            if time_filter == "Custom":
                start_date = self.start_date_entry.get_date().strftime("%Y-%m-%d")
                end_date = self.end_date_entry.get_date().strftime("%Y-%m-%d")

            total_sales, total_revenue, avg_order_value = fetch_sales_data(
                self.db_manager, time_filter, start_date, end_date
            )

            # Create PDF document
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Sales Report - {time_filter}", 0, 1, 'C')

            # Add summary section
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Summary", 0, 1)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Total Sales: {total_sales}", 0, 1)
            pdf.cell(0, 10, f"Total Revenue: RM{total_revenue:,.2f}", 0, 1)
            pdf.cell(0, 10, f"Avg. Order Value: RM{avg_order_value:,.2f}", 0, 1)
            pdf.ln(10)

            # Add transactions table
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Recent Transactions", 0, 1)

            # Table headers
            pdf.set_font("Arial", 'B', 12)
            col_widths = [40, 50, 30, 40, 40]
            headers = ["ID", "Date & Time", "User", "Amount", "Payment"]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
            pdf.ln()

            # Table data
            pdf.set_font("Arial", '', 10)
            for trans in transactions:
                for i in range(5):
                    pdf.cell(col_widths[i], 10, str(trans[i]), 1, 0, 'C')
                pdf.ln()

            # Save to user-selected location
            filename = f"sales_report_{time_filter}.pdf".replace(" ", "_")
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=filename
            )
            if filepath:
                pdf.output(filepath)
                messagebox.showinfo("Success", f"Exported to {filepath}")

        except Exception as e:
            logging.error(f"Sales PDF export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export sales PDF: {str(e)}")

    def update_sales_report(self, event=None, custom=False):
        """Refresh sales report based on current filters"""
        time_filter = self.time_filter_var.get()

        # Show/hide custom date controls
        if time_filter == "Custom":
            self.custom_date_frame.pack(side="left", fill="x", expand=True)
        else:
            self.custom_date_frame.pack_forget()

        # Get date range if custom
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
        """Export sales report to CSV format"""
        rows = []
        for item in self.tv.get_children():
            rows.append(self.tv.item(item)['values'])

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if filepath:
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Transaction ID", "Date & Time", "User", "Total Amount", "Payment Method"])
                writer.writerows(rows)
            messagebox.showinfo("Export Successful", f"Sales data exported to {filepath}")


# Database helper functions
def fetch_inventory_data(db_manager):
    """Retrieve all inventory data from database"""
    query = """
        SELECT productName, category, stockQuantity, status
        FROM product
    """
    return db_manager.execute_query(query)


def fetch_recent_transactions(db_manager, time_filter="Today", start_date=None, end_date=None):
    """Retrieve transaction data based on time filter"""
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    if time_filter == "All Time":
        query = """
            SELECT t.TransactionID, t.DateTime, u.Username, t.TotalAmount, t.PaymentMethod
            FROM `Transaction` t
            JOIN `User` u ON t.CashierID = u.UserID
            ORDER BY DateTime DESC
            LIMIT 20
        """
        cursor.execute(query)
    elif time_filter == "Custom" and start_date and end_date:
        query = """
            SELECT t.TransactionID, t.DateTime, u.Username, t.TotalAmount, t.PaymentMethod
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
        elif time_filter == "This Quarter":
            quarter_start = (now.month - 1) // 3 * 3 + 1
            start = now.replace(month=quarter_start, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "This Year":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = datetime.min

        query = """
            SELECT t.TransactionID, t.DateTime, u.Username, t.TotalAmount, t.PaymentMethod
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
    """Retrieve sales summary data based on time filter"""
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
            elif time_filter == "This Quarter":
                quarter_start = (now.month - 1) // 3 * 3 + 1
                start = now.replace(month=quarter_start, day=1, hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == "This Year":
                start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
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
    """Retrieve revenue trend data with dynamic start date based on earliest transaction"""
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

    # Get the current datetime
    now = datetime.now()

    # Determine period end (current datetime)
    period_end = now

    # Calculate period start based on time_filter
    if time_filter == "Today":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        group_format = "%H"  # Hourly grouping
    elif time_filter == "This Week":
        period_start = now - timedelta(days=now.weekday())
        period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m-%d"  # Daily grouping
    elif time_filter == "This Month":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m-%d"  # Daily grouping
    elif time_filter == "This Quarter":
        quarter_start = (now.month - 1) // 3 * 3 + 1
        period_start = now.replace(month=quarter_start, day=1, hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m-%d"  # Daily grouping
    elif time_filter == "This Year":
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        group_format = "%Y-%m"  # Monthly grouping
    else:  # All Time
        period_start = datetime.min
        group_format = "%Y-%m"  # Monthly grouping

    # Query to find the earliest transaction date in the period
    min_date_query = """
        SELECT MIN(DateTime)
        FROM `Transaction`
        WHERE DateTime >= ?
    """
    cursor.execute(min_date_query, (period_start.strftime("%Y-%m-%d %H:%M:%S"),))
    min_date_result = cursor.fetchone()[0]

    # Use earliest transaction date if available
    if min_date_result:
        try:
            actual_start = datetime.strptime(min_date_result, "%Y-%m-%d %H:%M:%S")
        except:
            actual_start = datetime.strptime(min_date_result, "%Y-%m-%d")
    else:
        actual_start = period_start

    # Build and execute main query
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
        WHERE DateTime BETWEEN ? AND ?
        GROUP BY time_period
        ORDER BY DateTime ASC
    """

    cursor.execute(query, (
        actual_start.strftime("%Y-%m-%d %H:%M:%S"),
        period_end.strftime("%Y-%m-%d %H:%M:%S")
    ))
    results = cursor.fetchall()
    conn.close()

    # Format results for display
    formatted_results = []
    for row in results:
        period = row[0]
        if time_filter == "Today":
            hour = int(period)
            period = f"{hour}:00"
        elif time_filter in ["This Week", "This Month", "This Quarter"]:
            period_date = datetime.strptime(period, "%Y-%m-%d")
            period = period_date.strftime("%b-%d")
        elif time_filter == "This Year":
            period_date = datetime.strptime(period, "%Y-%m")
            period = period_date.strftime("%b")
        else:  # All Time
            period_date = datetime.strptime(period + "-01", "%Y-%m-%d")
            period = period_date.strftime("%b-%Y")
        formatted_results.append((period, row[1] or 0, row[2] or 0))

    return formatted_results


def fetch_top_products(db_manager, time_filter="This Month", limit=10):
    """Retrieve top performing products data"""
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
    """Retrieve category performance data"""
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
    """Retrieve stock level and forecast data"""
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()

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


# Export helper functions
def export_inventory_pdf(self, tree):
    """Export inventory data to PDF (legacy method)"""
    try:
        rows = []
        for item in tree.get_children():
            rows.append(tree.item(item)['values'])

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Inventory Report", 0, 1, 'C')

        pdf.set_font("Arial", 'B', 12)
        col_widths = [70, 40, 35, 35]
        headers = ["Name", "Category", "Stock Qty", "Status"]
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()

        pdf.set_font("Arial", '', 12)
        for row in rows:
            for i in range(4):
                pdf.cell(col_widths[i], 10, str(row[i]), 1, 0, 'C')
            pdf.ln()

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="inventory_report.pdf"
        )
        if filepath:
            pdf.output(filepath)
            messagebox.showinfo("Success", f"Exported to {filepath}")

    except Exception as e:
        logging.error(f"Inventory PDF export failed: {e}")
        messagebox.showerror("Export Error", f"Failed to export inventory PDF: {str(e)}")


def export_sales_csv(db_manager, time_filter="Today", start_date=None, end_date=None):
    """Export sales data to CSV format"""
    transactions = fetch_recent_transactions(db_manager, time_filter, start_date, end_date)
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")]
    )
    if filepath:
        with open(filepath, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Transaction ID", "Date & Time", "User", "Total Amount", "Payment Method"])
            writer.writerows(transactions)
        messagebox.showinfo("Export Successful", f"Sales data exported to {filepath}")


# UI helper function
def treeview_sort_column(tree, col, reverse):
    """Enable sorting functionality for treeview columns"""
    data = [(tree.set(item, col), item) for item in tree.get_children('')]
    try:
        data = [(float(val), item) for val, item in data]
    except ValueError:
        pass
    data.sort(reverse=reverse)

    for index, (val, item) in enumerate(data):
        tree.move(item, '', index)

    tree.heading(col, command=lambda: treeview_sort_column(tree, col, not reverse))


# Application entry point
if __name__ == "__main__":
    try:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        app = ManagerDashboard()
        app.mainloop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        messagebox.showerror("Critical Error", f"The application encountered an error and will close.\nError: {str(e)}")
