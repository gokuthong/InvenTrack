# Sales and Inventory Management System - InvenTrack

![InvenTrack Logo](InvenTrack/manager/pictures/logo.png)

InvenTrack is a comprehensive Sales and Inventory Management System designed for retail stores to streamline product registration, sales transactions, and inventory monitoring. The system provides role-based access for managers, administrators, and cashiers with specialized modules for each role.

## Key Features

- **Manager Module**: Monitor stock levels, generate sales reports, and analyze business performance
- **Admin Module**: Register products, generate QR codes, and manage inventory
- **Cashier Module**: Process sales transactions, generate receipts, and update inventory in real-time
- **Automated Notifications**: Low stock alerts when inventory falls below threshold
- **Data Analytics**: Visualize sales trends, category performance, and stock forecasts
- **Secure Authentication**: Email verification and role-based access control

## System Requirements

- Python 3.8+
- SQLite database
- Required Python packages:
  ```
  pip install customtkinter pillow qrcode smtplib sqlite3 matplotlib pandas seaborn fpdf
  ```

## Getting Started

### 1. Registration (Manager Only)
The system requires a manager to register first:

1. Run the registration script:
   ```bash
   python registration.py
   ```
2. Fill in manager details (username, phone, email, password)
3. Verify your email with the 6-digit code sent to your Gmail
4. After successful registration, you'll be redirected to the login page

### 2. Logging In
1. Run the login script:
   ```bash
   python login.py
   ```
2. Enter your credentials (email and password)
3. Select your role (Manager, Admin, or Cashier)

### 3. Manager Dashboard
After logging in as a manager:
1. Access the dashboard to view key metrics
2. Add new admins or cashiers using the "Add Cashier" button
3. Navigate to:
   - **Inventory Report**: View detailed inventory status
   - **Sales Report**: Analyze sales performance
   - **Data Analytics**: Visualize business metrics

### 4. Admin Module
1. Log in with admin credentials
2. Access product management features:
   - Register new products with QR codes
   - Update existing product details
   - Manage product categories
   - Generate inventory reports

### 5. Cashier Module
1. Log in with cashier credentials
2. Process sales transactions:
   - Scan products using QR codes
   - Add items to cart
   - Calculate totals including tax
   - Generate receipts
   - Update inventory automatically

## System Architecture

```
project-root/
│
├── admin/        # Admin module files
│   ├── assets/
│     ├── frame0/ # Image directory
│     └── ...     # Images
│   ├── register.py          # Register page
│   ├── login.py             # Login page
│   ├── admindashboard.py    # Admmin dashboard
│   ├── manageProduct.py     # Update existing products 
│   ├── registerProduct.py   # Add new products
│   └── Profile page.py      # User profile
│
├── cashier/     # Cashier module files
│   ├── pictures # Image directory
│   └── ...      # Images
│   ├── cart.py           # Cashier terminal
│   ├── dashboard.py      # Cashier dashboard
│   └── payment_page.py   # Payment processing 
│
├── manager/     # Manager module files
│   ├── pictures # Image directory
│   └── ...      # Images
│   ├── manager.py             # Manager daashboard
│   └── add admin cashier.py   # Add new admins/cashiers
│
├── inventoryproject.db     # SQLite database
└── user_session.json       # User session data
```

## Database Schema

The system uses a SQLite database with the following tables:

1. **User** (UserID, Username, Email, Password, Role, PhoneNumber)
2. **Product** (ProductID, ProductName, Category, Barcode, Price, StockQuantity, ImagePath, Status)
3. **Transaction** (TransactionID, DateTime, CashierID, TotalAmount, PaymentMethod)
4. **TransactionDetail** (DetailID, TransactionID, ProductID, Quantity, Price)
5. **Category** (CategoryID, CategoryName)

## Troubleshooting

1. **Email Verification Issues**:
   - Ensure correct email credentials in registration.py
   - Check spam folder for verification codes
   - Verify internet connection

2. **Database Connection Errors**:
   - Ensure inventoryproject.db exists in project root
   - Check file permissions

3. **UI Rendering Problems**:
   - Verify all assets are in correct directories
   - Ensure required Python packages are installed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributors

- Bryan Tey
- Lau Zi Chen
- Thong Wai Kit
- Wong Goon Hee

---

**InvenTrack** - Streamlining retail operations since 2025
