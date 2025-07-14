import logging
import sqlite3
import os
import subprocess
from tkinter import messagebox

from PIL import Image
import customtkinter as ctk
from customtkinter import CTkImage
import json
import tkinter as tk
from InvenTrack.cashier.dashboard import create_dashboard_widgets
from flask import Flask, request
import threading, queue
from pathlib import Path
from PIL import ImageTk

# Load current user ID
session_path = Path(__file__).resolve().parent.parent / "user_session.json"
try:
    if session_path.exists():
        with open(session_path, "r", encoding="utf-8") as uf:
            user_data = json.load(uf)
        CURRENT_USER_ID = str(user_data.get("UserID", ""))
    else:
        logging.error(f"Session file not found: {session_path}")
        CURRENT_USER_ID = ""
except Exception as e:
    logging.error(f"Error loading session: {e}")
    CURRENT_USER_ID = ""

# a thread‐safe queue to shuttle scan codes into Tk
scan_queue = queue.Queue()

# Flask endpoint
flask_app = Flask(__name__)

@flask_app.route("/scan")
def scan():
    code = request.args.get("code")
    if code:
        scan_queue.put(code)
    return "", 204

def run_flask():
    # listen on all interfaces so your phone (on same LAN) can reach it
    flask_app.run(host="0.0.0.0", port=5000, debug=False)
# ───────────────────────────────────────────────────────────────────────────


# Initialize CustomTkinter appearance
ctk.set_appearance_mode("light")
ctk.set_default_color_theme ("blue")

class POSApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cashier Terminal")
        self.geometry("1920x1080")
        self.configure(fg_color="#2d3e50")


        # Keep references to CTkImage to prevent garbage collection
        self.image_refs = []

        # keep a list of currently showing toast windows
        self._active_toasts = []

        # Default placeholder
        placeholder_img = Image.new('RGB', (260,155), color='#cccccc')
        self.default_image = CTkImage(placeholder_img, size=(260,155))
        self.image_refs.append(self.default_image)

        # Tax rate (e.g., 6%)
        self.tax_rate = 0.06

        # Current page
        self.current_page = "Cashier Terminal"

        # Background
        try:
            pil_bg = Image.open(Path(__file__).parent / "pictures/background.png")
            ctk_bg = CTkImage(pil_bg, size=(1920,1080))
            self.image_refs.append(ctk_bg)
            bg_label = ctk.CTkLabel(self, image=ctk_bg, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Background load error: {e}")

        # Sidebar
        self.sidebar_expanded = False
        self.sidebar_width = 180

        # Load products
        self.products = {}
        self.low_stock_threshold = 5
        self._load_products_from_db()

        # Categories
        self.categories = ["All Items"] + sorted({p["category"] for p in self.products.values()})
        self.selected_category = "All Items"
        self.low_active = False

        # Cart
        self.cart = {}

        # → Load cart from file if it exists
        self._load_cart_file()

        # ─── start phone‐scan server ────────────────────────────
        threading.Thread(target=run_flask, daemon=True).start()
        # ─── poll scan_queue every 100ms ───────────────────────
        self.after(100, self._check_scans)

        # Build UI

        self.header_frame = ctk.CTkFrame(
            self,
            fg_color="#2d3e50",
            width=(1920),
            height=55
        )
        # place it right beside the sidebar, spanning the rest of the window
        self.header_frame.place(
            x=0,
            y=0
        )



        # title_label will show whichever page is “current”
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=self.current_page,    # initially “Cashier Terminal”
            font=("Acumin Pro", 25),
            text_color="#fff"
        )
        # give about 20px left padding, ~8px top so it’s vertically centered
        self.title_label.place(x=120, y=10)
        self._create_sidebar()
        self._create_toggle_button()
        self._create_top_buttons()

        x_off = self.sidebar_width if self.sidebar_expanded else 0
        dash_x = 116 + x_off
        dash_y = 100
        dash_w = 908 - dash_x
        dash_h = 850 - dash_y

        # Create a frame for the dashboard, with width/height set up front—
        # then place it at (dash_x, dash_y). We lower() it so it's hidden initially.
        self.dashboard_frame = ctk.CTkFrame(
            self,
            fg_color="#E8EDF2",
            corner_radius=8,
            width=dash_w,
            height=dash_h
        )
        self.dashboard_frame.place(
            x=dash_x,
            y=dash_y,
            relwidth=dash_w / 900,
            relheight=dash_h / 850
        )
        self.dashboard_frame.lower()

        try:
            logo_img = Image.open(Path(__file__).parent.parent / "admin/assets/frame0/logo_header.png")
            logo_img = logo_img.resize((40, 40))  # Resize as needed
            # Replace ImageTk.PhotoImage with CTkImage
            self.logo_ctk_image = CTkImage(logo_img, size=(40, 40))
            self.image_refs.append(self.logo_ctk_image)  # Add to references
            self.logo_label = ctk.CTkLabel(self, image=self.logo_ctk_image, text="")
            self.logo_label.place(x=65, y=5)  # Position left of title
        except Exception as e:
            logging.error(f"Failed to load logo: {e}")
            self.logo_label = None

        self._create_left_panel()
        self._create_right_panel()
        self._populate_products()
        self._refresh_cart()
        self.show_dashboard()

    def _load_products_from_db(self):
        db_path = Path(__file__).parent.parent / "inventoryproject.db"
        if not os.path.exists(db_path):
            ctk.CTkMessageBox(title="Error", message="Database not found.")
            return
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ProductID, ProductName, category,barcode2, price, stockQuantity, imagepath FROM product"
        )
        for pid, name, cat,barcode2, price, qty, raw_path in cursor.fetchall():
            path = str(raw_path or "").strip()
            exists = os.path.exists(path)
            try:
                if exists:
                    pil_img = Image.open(path).resize((262, 170))
                    ctk_img = CTkImage(pil_img, size=(262,170))
                    thumb_img = Image.open(path).resize((50,50))
                    ctk_thumb = CTkImage(thumb_img, size=(50,50))
                else:
                    ctk_img = self.default_image
                    ctk_thumb = self.default_image
            except Exception:
                ctk_img = self.default_image
                ctk_thumb = self.default_image

            self.image_refs.extend([ctk_img, ctk_thumb])
            self.products[pid] = {
                "name": name,
                "category": cat,
                "barcode2": barcode2,
                "price": price,
                "quantity": qty,
                "image": ctk_img,
                "thumb": ctk_thumb,
            }
        print("[DB] Loaded products:", {
            pid: info["barcode2"]
            for pid, info in self.products.items()
        })

        conn.close()


    def _cart_filepath(self):
        """Return the single cart.json file used to persist all users' carts."""
        return Path(__file__).parent / "cart.json"

    def _load_cart_file(self):
        """Load the saved cart for the current user from cart.json, if it exists."""
        path = self._cart_filepath()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    all_carts = json.load(f)
                # get only this user's cart, defaulting to empty
                user_cart = all_carts.get(CURRENT_USER_ID, {})
                # keys are product‑IDs as strings → convert to ints
                self.cart = {int(k): int(v) for k, v in user_cart.items()}
            except Exception as e:
                print(f"Failed to load cart.json: {e}")
                self.cart = {}
        else:
            self.cart = {}


    def _save_cart_file(self):
        """Write the current user's cart into cart.json alongside other users' carts."""
        path = self._cart_filepath()
        all_carts = {}
        # load existing data if any
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    all_carts = json.load(f)
            except Exception as e:
                print(f"Failed to read existing cart.json: {e}")
        # overwrite only this user's entry
        all_carts[CURRENT_USER_ID] = {str(pid): qty for pid, qty in self.cart.items()}
        # write back
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(all_carts, f, indent=2)
        except Exception as e:
            print(f"Failed to save cart.json: {e}")

    def _delete_cart_file(self):
        """Remove only the current user's cart from cart.json."""
        path = self._cart_filepath()
        if os.path.exists(path):
            try:
                # Read all carts
                with open(path, "r", encoding="utf-8") as f:
                    all_carts = json.load(f)
                # Remove only this user's entry
                if CURRENT_USER_ID in all_carts:
                    all_carts.pop(CURRENT_USER_ID)
                    # Write back the rest
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(all_carts, f, indent=2)
            except Exception as e:
                print(f"Failed to remove current user's cart: {e}")


    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            fg_color="#2d3e50",
            corner_radius=0,
            width=self.sidebar_width,
            height=1080,
            border_width=0,
            border_color="#ddd"
        )
        # ↓ Remove any self.sidebar.place(...) here—so it stays hidden until toggled.

        ctk.CTkLabel(
            self.sidebar,
            text="InvenTrack",
            font=("Acumin Pro", 28, "bold"),
            text_color="#fff"
        ).place(x=20, y=20)

        # Keep references to each button so we can toggle fg_color/text_color later
        self.sidebar_buttons = {}

        y = 80
        for name in ["Dashboard", "Cashier Terminal"]:
            is_current = (name == self.current_page)

            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                width=160,
                height=50,
                corner_radius=10,
                fg_color="#34495E" if is_current else "transparent",
                hover_color="#3E5870" if is_current else "#4A6374",
                text_color="#FFFFFF" if is_current else "#FFFFFF",
                font=("Acumin Pro", 18.5),
                command=(self.show_dashboard if name == "Dashboard" else self.show_cashier)
            )
            btn.place(x=10, y=y)
            self.sidebar_buttons[name] = btn
            y += 70

        logout_y = 950  # 20px bottom margin
        ctk.CTkButton(
            self.sidebar,
            text="🔒 Log Out",
            width=160,
            height=50,
            corner_radius=0,
            fg_color="transparent",
            hover_color="lightblue",
            text_color="#fff",
            font=("Acumin Pro", 18.5),
            command=self.logout
        ).place(x=10, y=logout_y)

    def clear_user_session(self):
        """Clear the user session data"""
        session_file = Path(__file__).parent.parent / "user_session.json"
        try:
            if session_file.exists():
                os.remove(session_file)
        except Exception as e:
            logging.error(f"Error clearing session: {e}")

    def logout(self):
        """Handle logout process"""
        try:
            # Clear the user session
            self.clear_user_session()

            # Close current window
            self.destroy()

            # Launch login page
            current_dir = Path(__file__).parent.parent  # Go up to parent directory
            login_script = current_dir / "admin/login.py"  # Assuming login.py is in parent directory

            if login_script.exists():
                subprocess.Popen(['python', str(login_script)])
            else:
                messagebox.showerror("Error", "Login page not found!")
        except Exception as e:
            logging.error(f"Error during logout: {e}")
            messagebox.showerror("Logout Error", "Failed to logout properly")



    def _create_toggle_button(self):
        self.toggle_btn = ctk.CTkButton(self, text="☰", width=45, height=45,
                                         corner_radius=0, fg_color="#2d3e50",
                                         hover_color="#2d3e50", text_color="#fff",
                                         font=("Acumin Pro",20), command=self.toggle_sidebar)
        self.toggle_btn.place(x=12,y=6)
        self.toggle_btn.lift()


    def show_dashboard(self):
        # 1) Hide the cashier panels
        self.left_panel.place_forget()
        self.right_panel.place_forget()

        # 2) If this is the first time, build the dashboard inside dashboard_frame
        if not hasattr(self, "_dashboard_built"):
            create_dashboard_widgets(self.dashboard_frame)
            self._dashboard_built = True

        # 3) Bring dashboard_frame to front (so it’s visible)
        self.dashboard_frame.lift()

        # 4) Update header text & sidebar button colors
        self.current_page = "Dashboard"
        self.title_label.configure(text=self.current_page)
        for name, btn in self.sidebar_buttons.items():
            if name == "Dashboard":
                btn.configure(fg_color="#34495E", hover_color="#3E5870")
            else:
                btn.configure(fg_color="transparent", hover_color="#4A6374")

        if self.sidebar_expanded:
            self.toggle_sidebar()

    def show_cashier(self):
        # 1) Hide dashboard
        self.dashboard_frame.lower()

        # 2) Re-show the left and right panels in their original positions
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.left_panel.place(x=116 + x_off, y=100)
        self.right_panel.place(x=1279 + x_off, y=100)

        # 3) Update header text & sidebar button colors
        self.current_page = "Cashier Terminal"
        self.title_label.configure(text=self.current_page)
        for name, btn in self.sidebar_buttons.items():
            if name == "Cashier Terminal":
                btn.configure(fg_color="#34495E", hover_color="#3E5870")
            else:
                btn.configure(fg_color="transparent", hover_color="#4A6374")

        if self.sidebar_expanded:
            self.toggle_sidebar()

    def _create_top_buttons(self):
        # same size as the sidebar toggle
        btn_size = 35
        # Cart button
        self.cart_btn = ctk.CTkButton(
            self,
            text="🛒",
            width=btn_size,
            height=btn_size,
            corner_radius=0,
            fg_color="#2d3e50",
            hover_color="#1a252f",
            text_color="#fff",
            font=("Acumin Pro", 25),
            command= self.goto_payment
        )
        # Profile button
        self.profile_btn = ctk.CTkButton(
            self,
            text="👤",
            width=btn_size,
            height=btn_size,
            corner_radius=0,
            fg_color="#2d3e50",
            hover_color="#1a252f",
            text_color="#fff",
            font=("Acumin Pro", 25),
            command=self.goto_profile  # Changed to use the new method
        )
        # compute x-offset for right panel
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        panel_x = 1295 + x_off  # left edge of right panel
        panel_w = 525  # width of right panel
        margin = 12  # margin from edges

        # place the profile button flush right
        px = panel_x + panel_w - margin - btn_size
        self.profile_btn.place(x=px, y=margin)
        # place the cart button just to the left of it
        self.cart_btn.place(x=px - (btn_size + margin), y=margin)

    def goto_profile(self):
        """Close current window and open Profile page"""
        try:
            # Close current window
            self.destroy()

            # Launch profile page
            current_dir = Path(__file__).parent.parent
            profile_script = current_dir / "admin/Profile page.py"

            if profile_script.exists():
                subprocess.Popen(['python', str(profile_script)])
            else:
                # Fallback to reopening dashboard if script not found
                messagebox.showerror("Error", "Profile page not found!")
                app = POSApp()
                app.mainloop()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open profile: {e}")
            # Reopen the current app as fallback
            app = POSApp()
            app.mainloop()

    def goto_payment(self):
        """Close current window and open Profile page"""
        self.destroy()
        try:
            # Launch profile page
            current_dir = Path(__file__).parent
            profile_script = current_dir / "payment page.py"

            if profile_script.exists():
                subprocess.Popen(['python', str(profile_script)])
            else:
                # Fallback to reopening dashboard if script not found
                messagebox.showerror("Error", "Profile page not found!")
                app = POSApp()
                app.mainloop()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open profile: {e}")
            # Reopen the current app as fallback
            app = POSApp()
            app.mainloop()


    def _create_left_panel(self):
        x_off = self.sidebar_width if self.sidebar_expanded else 0
        self.left_panel = ctk.CTkFrame(self, fg_color="#E8EDF2", corner_radius=0,
                                       width=1147, height=890)
        self.left_panel.place(x=116+x_off,y=100)
        # Categories
        cat_frame=ctk.CTkFrame(self.left_panel, fg_color="#fff", width=1147, height=60)
        cat_frame.place(x=0,y=0)
        w=1147/len(self.categories)
        self.cat_buttons=[]
        for i,cat in enumerate(self.categories):
            btn=ctk.CTkButton(cat_frame,text=cat,corner_radius=24,
                              fg_color="#2d3e50" if cat==self.selected_category else "transparent",
                              text_color="#fff" if cat==self.selected_category else "#333",
                              hover_color="#D6DDE5",font=("Acumin Pro",19), width=w-10, height=60,
                              command=lambda c=cat: self.select_category(c))
            btn.place(x=i*w+5,y=0)
            self.cat_buttons.append(btn)
        # Search & Filter
        sf=ctk.CTkFrame(self.left_panel, fg_color="#fff", width=1147, height=80)
        sf.place(x=0,y=60)
        self.search_var=ctk.StringVar()
        entry=ctk.CTkEntry(sf, textvariable=self.search_var,
                           placeholder_text="Search by ID or Name...",
                           width=900, height=50, font=("Acumin Pro",20))
        entry.place(x=20,y=15)
        entry.bind("<KeyRelease>", lambda e: self._populate_products())
        self.filter_var=ctk.StringVar(value="All Items")
        filter_menu=ctk.CTkOptionMenu(sf, variable=self.filter_var,
                                      values=["All Items","Low Stock"],
                                      fg_color="#2d3e50",  # ← left‐side background
                                      button_color="#2d3e50",  # ← arrow background
                                      button_hover_color="#1a252f",
                                      text_color="#fff", dropdown_fg_color="#2d3e50",
                                      dropdown_text_color="#fff", font=("Acumin Pro",19),
                                      width=200, height=50, corner_radius=24,
                                      command=self.select_filter)
        filter_menu.place(x=940,y=15)
        # Product grid
        self.prod_scroll=ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent",
                                                 width=1147,height=750)
        self.prod_scroll.place(x=0,y=140)

    def _create_right_panel(self):
        x_off=self.sidebar_width if self.sidebar_expanded else 0
        self.right_panel=ctk.CTkFrame(self, fg_color="#E8EDF2", corner_radius=8,
                                      width=525, height=890)
        self.right_panel.place(x=1279+x_off,y=100)
        hdr=ctk.CTkFrame(self.right_panel, fg_color="#fff", width=525, height=64)
        hdr.place(x=0,y=0)
        ctk.CTkLabel(hdr,text="Current Order",
                     font=("Acumin Pro",22,"bold"), text_color="#333").place(x=16,y=16)
        ctk.CTkButton(hdr,text="Clear All",width=120,height=36,fg_color="#2d3e50",hover_color="#1a252f",
                      font=("Acumin Pro",18),command=self._clear_cart).place(x=390,y=16)
        self.cart_scroll=ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent",
                                                 width=525,height=650)
        self.cart_scroll.place(x=0,y=64)
        ftr = ctk.CTkFrame(self.right_panel, fg_color="#fff", width=525, height=176)
        ftr.place(x=0, y=714)

        # ← inline stock‐warning label
        self.stock_msg = ctk.CTkLabel(
            ftr,
            text="",
            font=("Acumin Pro", 14),
            text_color="#ff6b6b"
        )
        self.stock_msg.place(x=16, y=0)

        # adjust totals down a bit
        self.lbl_sub = ctk.CTkLabel(ftr, text="Subtotal: RM0.00", font=("Acumin Pro", 16))
        self.lbl_sub.place(x=16,y = 35)
        self.lbl_tax = ctk.CTkLabel(ftr, text="Tax: RM0.00", font=("Acumin Pro", 16))
        self.lbl_tax.place(x=350, y=35)
        self.lbl_tot = ctk.CTkLabel(ftr, text="Total: RM0.00", font=("Acumin Pro", 16, "bold"))
        self.lbl_tot.place(x=16, y=75)

        ctk.CTkButton(
            ftr,
            text="Add to Cart",
            width=500,
            height=45,
            fg_color="#2d3e50",
            hover_color="#1a252f",
            font=("Acumin Pro", 18),
            command=self._pay
        ).place(x= 12,y=120)

    def toggle_sidebar(self):
        steps, total_duration = 5, 50
        delta = self.sidebar_width // steps

        def expand(step=0):
            w = delta * step
            self.sidebar.configure(width=w)
            x_off = w

            # If on Cashier page, re-place left/right panels
            if self.current_page == "Cashier Terminal":
                self.left_panel.place_configure(x=116 + x_off)
                self.right_panel.place_configure(x=1279 + x_off)
            # If on Dashboard, re-place dashboard_frame
            elif self.current_page == "Dashboard":
                self.dashboard_frame.place_configure(x=116 + x_off)

            self.toggle_btn.place_configure(x=10 + x_off)
            self.title_label.place_configure(x=120 + x_off)

            if step < steps:
                self.after(total_duration // steps, lambda: expand(step + 1))
            else:
                self.sidebar_expanded = True

        def collapse(step=steps):
            w = delta * step
            self.sidebar.configure(width=w)
            x_off = w

            if self.current_page == "Cashier Terminal":
                self.left_panel.place_configure(x=116 + x_off)
                self.right_panel.place_configure(x=1279 + x_off)
            elif self.current_page == "Dashboard":
                self.dashboard_frame.place_configure(x=116 + x_off)

            self.toggle_btn.place_configure(x=10 + x_off)
            self.title_label.place_configure(x=120 + x_off)

            if step > 0:
                self.after(total_duration // steps, lambda: collapse(step - 1))
            else:
                self.sidebar.place_forget()
                self.sidebar_expanded = False

        if self.sidebar_expanded:
            collapse()
        else:
            self.sidebar.place(x=0, y=0)
            self.sidebar.lift()
            expand()

    def select_category(self,cat):
        self.selected_category=cat
        for btn in self.cat_buttons:
            btn.configure(
                fg_color="#2d3e50" if btn.cget('text')==cat else "transparent",
                text_color="#fff" if btn.cget('text')==cat else "#333"
            )
        self._populate_products()

    def select_filter(self,choice):
        self.low_active=False
        if choice=="Low Stock": self.low_active=True
        self._populate_products()

    def _populate_products(self):
        for w in self.prod_scroll.winfo_children():
            w.destroy()
        cols, pad = 4, 10
        card_width = 265
        for i in range(cols):
            self.prod_scroll.grid_columnconfigure(i, weight=0, minsize=card_width + pad*2)
        x = y = 0
        q = self.search_var.get().lower().strip()
        for pid, info in self.products.items():
            if q:
                if q.isdigit():
                    if pid != int(q):
                        continue
                else:
                    if q not in info['name'].lower():
                        continue
            if self.selected_category != "All Items" and info['category'] != self.selected_category:
                continue
            if self.low_active and info['quantity'] > self.low_stock_threshold:
                continue


            card = ctk.CTkFrame(self.prod_scroll,
                                fg_color=("#fdecea" if info['quantity']<=self.low_stock_threshold else "#fff"), corner_radius=0,
                                border_width=0, width=card_width, height=340)
            card.grid(row=y, column=x, padx=pad, pady=pad, sticky="nw")
            card.grid_propagate(False)

            # Top: image spans full width, center-aligned
            img_label = ctk.CTkLabel(card, image=info['image'], text="")
            img_label.place(relx=0.498, y=3, anchor="n")

            # Bottom: info frame (fixed position)
            info_f = ctk.CTkFrame(card, fg_color="transparent", width=260, height=180)
            info_f.place(x=0, y=160)

            # Product details with larger fonts and left padding
            ctk.CTkLabel(info_f, text=info['name'],
                         font=("Acumin Pro",18,"bold"),
                         anchor="w").pack(fill="x", padx=12, pady=(8,0))
            ctk.CTkLabel(info_f, text=f"Category: {info['category']}",
                         font=("Acumin Pro",16),
                         anchor="w").pack(fill="x", padx=12)
            ctk.CTkLabel(info_f, text=f"Price: RM{info['price']:.2f}",
                         font=("Acumin Pro",16),
                         anchor="w").pack(fill="x", padx=12)
            stock_text = f"Low Stock! ({info['quantity']})" if info['quantity'] <= self.low_stock_threshold else f"Stock: {info['quantity']}"
            text_color = "#ff6b6b" if info['quantity'] <= self.low_stock_threshold else "#333"
            ctk.CTkLabel(info_f, text=stock_text,
                         font=("Acumin Pro",16), text_color=text_color,
                         anchor="w").pack(fill="x", padx=12)

            # Add button larger and fully visible aligned bottom-right
            add_btn = ctk.CTkButton(info_f, text="Add",
                                    width=265, height=40,
                                   font=("Acumin Pro",16),fg_color="#2d3e50",hover_color="#1a252f",
                                    command=lambda p=pid: self._add_cart(p))
            add_btn.pack(fill="x", pady=20)

            x += 1
            if x == cols:
                x = 0
                y += 1

    def _add_cart(self, pid):
        current_qty = self.cart.get(pid, 0)
        max_qty = self.products[pid]["quantity"]
        if current_qty < max_qty:
            self.cart[pid] = current_qty + 1
            self.stock_msg.configure(text="")  # clear any prior warning
            # ← Show success toast
            self._show_toast(f"Added to cart: {self.products[pid]['name']}")

        else:
            self._show_temporary_stock_msg(
                f"Cannot add more than {max_qty} of '{self.products[pid]['name']}'",
                duration=3000
            )
        # → Persist to disk
        self._save_cart_file()
        self._refresh_cart()

    def _clear_cart(self):
        messagebox.showinfo(title="Alert", message="Cart has been cleared!")
        self.cart.clear()
        # → Delete the cart file when “Clear All” is pressed
        self._delete_cart_file()
        self._refresh_cart()

    def _show_temporary_stock_msg(self, text, duration=3000):
        """Show a stock‐warning for `duration` ms, then auto‐clear."""
        self.stock_msg.configure(text=text)
        # schedule a clear
        self.after(duration, lambda: self.stock_msg.configure(text=""))

    def _show_toast(self, message, emoji="✅"):
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg="white")
        lbl = ctk.CTkLabel(
            toast,
            text=f"{emoji} {message}",
            font=("Acumin Pro", 18),
            text_color="#333",
            fg_color="white"
        )
        lbl.pack(padx=10, pady=5)

        # Position toasts stacked from bottom up
        self.update_idletasks()
        width = toast.winfo_reqwidth()
        height = toast.winfo_reqheight()
        x = self.winfo_x() + (self.winfo_width() - width) // 2

        # compute y based on how many are already showing
        idx = len(self._active_toasts)
        base_y = self.winfo_y() + self.winfo_height() - height - 50
        y = base_y - idx * (height + 10)

        toast.geometry(f"{width}x{height}+{x}+{y}")

        # keep track of it
        self._active_toasts.append(toast)

        # when it’s time to destroy, also remove from the list
        def _cleanup():
            if toast in self._active_toasts:
                self._active_toasts.remove(toast)
            toast.destroy()

        toast.after(2000, _cleanup)

    def _refresh_cart(self):
        # ──────────────────────────────────────────────────────────────────────────
        # Replace your existing entire _refresh_cart method with this:
        for w in self.cart_scroll.winfo_children():
            w.destroy()
        subtotal = 0
        for pid, qty in self.cart.items():
            info = self.products[pid]
            subtotal += info['price'] * qty

            # create each cart-item row
            item = ctk.CTkFrame(self.cart_scroll,border_width=0, fg_color="#fff", corner_radius=8, height=70)
            item.pack(fill="x", padx=0, pady=7)

            # thumbnail on the far left
            if info['thumb']:
                ctk.CTkLabel(item, image=info['thumb'], text="").place(x=16, y=10)

            # Item name beside thumbnail
            ctk.CTkLabel(item, text=info['name'], font=("Acumin Pro", 18)).place(x=80, y=18)

            # quantity controls (grid‐based qf frame)
            qf = ctk.CTkFrame(item, fg_color="transparent", width=140, height=30)
            qf.place(x=260, y=20)
            qf.grid_propagate(False)

            # Quantity entry
            minus_btn = ctk.CTkButton(
                qf, text="–", width=24, height=24, font=("Acumin Pro", 16),
                fg_color="#2d3e50", hover_color="#1a252f",
                command=lambda p=pid: self._set_qty(p, self.cart.get(p, 1) - 1)
            )
            minus_btn.grid(row=0, column=2, padx=(2, 5))

            qty_var = ctk.StringVar(value=str(qty))
            entry = ctk.CTkEntry(
                qf, textvariable=qty_var, width=60, height=28,
                font=("Acumin Pro", 16), justify="center"
            )
            entry.grid(row=0, column=1)
            entry.bind(
                "<Return>",
                lambda e, p=pid, v=qty_var: self._set_qty(p, int(v.get() or 0))
            )

            plus_btn = ctk.CTkButton(
                qf, text="+", width=24, height=24, font=("Acumin Pro", 16),
                fg_color="#2d3e50", hover_color="#1a252f",
                command=lambda p=pid: self._add_cart(p)
            )
            plus_btn.grid(row=0, column=0, padx=(5, 2))
            # Total price
            ctk.CTkLabel(item, text=f"RM{info['price'] * qty:.2f}",
                         font=("Acumin Pro", 18)).place(x=400, y=20)
        # ──────────────────────────────────────────────────────────────────────────

        # then your existing tax/total footer logic:
        tax = subtotal * self.tax_rate
        total = subtotal + tax
        self.lbl_sub.configure(text=f"Subtotal: RM{subtotal:.2f}", font=("Acumin Pro", 18))
        self.lbl_tax.configure(text=f"Tax (6%): RM{tax:.2f}", font=("Acumin Pro", 18))
        self.lbl_tot.configure(text=f"Total: RM{total:.2f}", font=("Acumin Pro", 18))

    def _set_qty(self, pid, new_qty):
        max_qty = self.products[pid]['quantity']
        if 0 < new_qty <= max_qty:
            self.cart[pid] = new_qty
        elif new_qty <= 0:
            self.cart.pop(pid, None)
        else:
            self._show_temporary_stock_msg(
                f"Cannot add more than {max_qty} of '{self.products[pid]['name']}'",
                duration=3000
            )
        # → Persist to disk
        if self.cart:
            self._save_cart_file()
        else:
            # if cart is empty after adjustment, delete the file
            self._delete_cart_file()
        self._refresh_cart()

    def _pay(self):
        messagebox.showinfo(title="Alert", message="Products successfully added to cart!")
        print("Payment processed!")

    def _check_scans(self):
        """Called every 100ms to pull any incoming codes from your phone."""
        while not scan_queue.empty():
            code = scan_queue.get()
            # find matching productID by barcode
            pid = next((pid for pid,info in self.products.items()
                        if info.get("barcode2") == code), None)
            if pid:
                self._add_cart(pid)
            else:
                self._show_temporary_stock_msg(f"No product for code {code!r}", 3000)
        # re‐schedule
        self.after(100, self._check_scans)

if __name__=="__main__":
    app=POSApp()
    app.mainloop()
