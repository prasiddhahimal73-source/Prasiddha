"""
Spicy Bites - Payment & Loyalty Points System (Suraj)
Meets SOFT605 Assignment requirements:
 - GUI using Tkinter (Learning Outcome: GUI)
 - OOP: PaymentSystem, DatabaseManager (LO1 & LO2)
 - Database: SQLite - tables for customers, sales, promo codes (LO: Database Design & Script)
 - Functional: record processed_by, loyalty points, promo codes, transaction history
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

DB_FILE = "spicybites.db"

# -------------------------
# Database manager (Encapsulation)
# -------------------------
class DatabaseManager:
    """Encapsulates all DB operations. This class demonstrates encapsulation and abstraction."""
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self._create_tables()

    def _create_tables(self):
        """Create tables if they do not exist"""
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            contact TEXT,
            membership TEXT DEFAULT 'regular',
            loyalty_points INTEGER DEFAULT 0
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            discount_rate REAL  -- fraction e.g., 0.10 for 10%
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            customer_name TEXT,
            processed_by TEXT,
            subtotal REAL,
            discount_amount REAL,
            loyalty_redeemed INTEGER,
            final_total REAL,
            points_earned INTEGER
        )""")
        self.conn.commit()
        # Insert some default promo codes if not present
        cur.execute("INSERT OR IGNORE INTO promo_codes (code, discount_rate) VALUES (?, ?)", ("SPICY10", 0.10))
        cur.execute("INSERT OR IGNORE INTO promo_codes (code, discount_rate) VALUES (?, ?)", ("HOT20", 0.20))
        self.conn.commit()

    # Customers
    def get_customer(self, name):
        cur = self.conn.cursor()
        cur.execute("SELECT name, membership, loyalty_points FROM customers WHERE name = ?", (name,))
        return cur.fetchone()

    def add_or_update_customer(self, name, contact=None, membership='regular', points=0):
        cur = self.conn.cursor()
        # try insert, otherwise update
        cur.execute("INSERT OR IGNORE INTO customers (name, contact, membership, loyalty_points) VALUES (?, ?, ?, ?)",
                    (name, contact or '', membership, points))
        cur.execute("UPDATE customers SET membership = ?, loyalty_points = ? WHERE name = ?",
                    (membership, points, name))
        self.conn.commit()

    def update_loyalty_points(self, name, points):
        cur = self.conn.cursor()
        cur.execute("UPDATE customers SET loyalty_points = ? WHERE name = ?", (points, name))
        self.conn.commit()

    # Promo codes
    def get_promo_discount(self, code):
        cur = self.conn.cursor()
        cur.execute("SELECT discount_rate FROM promo_codes WHERE code = ?", (code,))
        res = cur.fetchone()
        return res[0] if res else 0.0

    # Sales
    def record_sale(self, sale_record: dict):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO sales (timestamp, customer_name, processed_by, subtotal, discount_amount, loyalty_redeemed, final_total, points_earned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sale_record['timestamp'],
            sale_record['customer_name'],
            sale_record['processed_by'],
            sale_record['subtotal'],
            sale_record['discount_amount'],
            sale_record['loyalty_redeemed'],
            sale_record['final_total'],
            sale_record['points_earned']
        ))
        self.conn.commit()

    def close(self):
        self.conn.close()


# -------------------------
# Payment System GUI (Uses OOP: Abstraction & Inheritance idea can extend later)
# -------------------------
class PaymentSystem:
    """
    GUI class that handles payment computations and interactions.
    Demonstrates: encapsulation (DB inside DatabaseManager), OOP design for extension.
    """
    def __init__(self, root, db: DatabaseManager):
        self.root = root
        self.db = db
        self.root.title("Spicy Bites - Payment & Loyalty System (Suraj)")
        self.root.geometry("480x520")
        self.build_gui()

        # last processed results
        self.last_final_total = None
        self.last_points_earned = 0
        self.last_discount_amount = 0
        self.last_loyalty_redeemed = 0

    def build_gui(self):
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill='both', expand=True)

        # Staff / processed_by (shows who processed the sale)
        tk.Label(frame, text="Processed by (staff username):").grid(row=0, column=0, sticky='w')
        self.staff_entry = tk.Entry(frame)
        self.staff_entry.grid(row=0, column=1, pady=6)

        # Customer name (lookup or create)
        tk.Label(frame, text="Customer Name:").grid(row=1, column=0, sticky='w')
        self.customer_entry = tk.Entry(frame)
        self.customer_entry.grid(row=1, column=1, pady=6)

        tk.Button(frame, text="Load Customer", command=self.load_customer).grid(row=1, column=2, padx=6)

        self.customer_info_label = tk.Label(frame, text="Customer info: (not loaded yet)", anchor='w', justify='left')
        self.customer_info_label.grid(row=2, column=0, columnspan=3, sticky='w')

        # Subtotal / Amount
        tk.Label(frame, text="Order Subtotal ($):").grid(row=3, column=0, sticky='w')
        self.subtotal_entry = tk.Entry(frame)
        self.subtotal_entry.grid(row=3, column=1, pady=6)

        # Promo code
        tk.Label(frame, text="Promo Code (optional):").grid(row=4, column=0, sticky='w')
        self.promo_entry = tk.Entry(frame)
        self.promo_entry.grid(row=4, column=1, pady=6)

        # Redeem loyalty points checkbox and amount
        self.redeem_var = tk.IntVar()
        tk.Checkbutton(frame, text="Redeem loyalty points", variable=self.redeem_var).grid(row=5, column=0, sticky='w')
        self.redeem_label = tk.Label(frame, text="(Redemption rule: each point = $0.05, max 20% of subtotal)")
        self.redeem_label.grid(row=5, column=1, columnspan=2, sticky='w')

        # Buttons to process and show receipt
        tk.Button(frame, text="Process Payment", command=self.process_payment, width=18).grid(row=6, column=0, pady=14)
        tk.Button(frame, text="Show Receipt", command=self.show_receipt, width=18).grid(row=6, column=1, pady=14)
        tk.Button(frame, text="Add/Update Customer", command=self.add_update_customer, width=18).grid(row=6, column=2)

        # Output area
        self.output_text = tk.Text(frame, height=10, width=58)
        self.output_text.grid(row=7, column=0, columnspan=3, pady=8)
        self.output_text.insert('end', "Ready.\n")

    def load_customer(self):
        name = self.customer_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter customer name to load.")
            return
        data = self.db.get_customer(name)
        if data:
            # data = (name, membership, loyalty_points)
            self.customer_info_label.config(text=f"Name: {data[0]} | Membership: {data[1]} | Points: {data[2]}")
        else:
            self.customer_info_label.config(text=f"Customer '{name}' not found. You can add them using 'Add/Update Customer'.")

    def add_update_customer(self):
        name = self.customer_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter customer name to add/update.")
            return
        # For simplicity, add default membership regular and current points 0
        self.db.add_or_update_customer(name, membership='regular', points=0)
        messagebox.showinfo("Customer", f"Customer '{name}' added/updated.")
        self.load_customer()

    def process_payment(self):
        # Input validation
        staff = self.staff_entry.get().strip()
        if not staff:
            messagebox.showwarning("Staff required", "Enter staff username (processed_by).")
            return
        name = self.customer_entry.get().strip()
        if not name:
            messagebox.showwarning("Customer required", "Enter customer name.")
            return
        try:
            subtotal = float(self.subtotal_entry.get())
            if subtotal < 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid amount", "Enter a valid positive subtotal amount.")
            return

        # promo code discount
        promo = self.promo_entry.get().upper().strip()
        promo_rate = self.db.get_promo_discount(promo) if promo else 0.0
        promo_discount = round(subtotal * promo_rate, 2)

        # loyalty redemption
        customer = self.db.get_customer(name)
        current_points = customer[2] if customer else 0
        loyalty_redeemed = 0
        loyalty_value = 0.0
        if self.redeem_var.get() and current_points > 0:
            # Each point = $0.05, but redemption capped at 20% of subtotal
            max_redeem_value = round(subtotal * 0.20, 2)
            possible_value = round(current_points * 0.05, 2)
            loyalty_value = min(max_redeem_value, possible_value)
            # points to redeem (floor)
            loyalty_redeemed = int(loyalty_value / 0.05)

        # Apply discounts
        intermediate_total = subtotal - promo_discount - loyalty_value
        if intermediate_total < 0:
            intermediate_total = 0.0

        # Earn points: 5% of final payment (rounded down to int)
        points_earned = int(intermediate_total * 0.05)

        # Update DB:
        # - If customer not present, add them
        if not customer:
            self.db.add_or_update_customer(name, membership='regular', points=0)
            current_points = 0
        new_points = current_points - loyalty_redeemed + points_earned
        if new_points < 0:
            new_points = 0
        self.db.update_loyalty_points(name, new_points)

        final_total = round(intermediate_total, 2)

        # Record sale
        sale_record = {
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'customer_name': name,
            'processed_by': staff,
            'subtotal': subtotal,
            'discount_amount': round(promo_discount + loyalty_value, 2),
            'loyalty_redeemed': loyalty_redeemed,
            'final_total': final_total,
            'points_earned': points_earned
        }
        self.db.record_sale(sale_record)

        # Save last values for receipt
        self.last_final_total = final_total
        self.last_points_earned = points_earned
        self.last_discount_amount = round(promo_discount + loyalty_value, 2)
        self.last_loyalty_redeemed = loyalty_redeemed

        # Output to GUI text
        self.output_text.delete('1.0', 'end')
        self.output_text.insert('end', f"Processed by: {staff}\n")
        self.output_text.insert('end', f"Customer: {name}\n")
        self.output_text.insert('end', f"Subtotal: ${subtotal:.2f}\n")
        self.output_text.insert('end', f"Promo discount: ${promo_discount:.2f} (code: {promo if promo else 'N/A'})\n")
        self.output_text.insert('end', f"Loyalty redeemed: {loyalty_redeemed} points -> ${loyalty_value:.2f}\n")
        self.output_text.insert('end', f"Final total: ${final_total:.2f}\n")
        self.output_text.insert('end', f"Points earned this sale: {points_earned}\n")
        self.output_text.insert('end', f"Customer new loyalty balance: {new_points}\n")
        self.output_text.insert('end', "Sale recorded in DB.\n")

    def show_receipt(self):
        if self.last_final_total is None:
            messagebox.showwarning("No sale", "Process a payment first.")
            return
        # Build receipt text
        receipt = (
            "----- Spicy Bites Receipt -----\n"
            f"Processed by: {self.staff_entry.get().strip()}\n"
            f"Customer: {self.customer_entry.get().strip()}\n"
            f"Final Total: ${self.last_final_total:.2f}\n"
            f"Discount Applied: ${self.last_discount_amount:.2f}\n"
            f"Loyalty points redeemed: {self.last_loyalty_redeemed}\n"
            f"Points earned: {self.last_points_earned}\n"
            "Thank you for dining with Spicy Bites!\n"
            "-------------------------------"
        )
        messagebox.showinfo("Receipt", receipt)


# -------------------------
# Main runnable section
# -------------------------
def main():
    db = DatabaseManager()  # creates DB and default promo codes
    root = tk.Tk()
    app = PaymentSystem(root, db)
    root.protocol("WM_DELETE_WINDOW", lambda: (db.close(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
