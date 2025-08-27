import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
from datetime import datetime, timedelta
from tkcalendar import DateEntry, Calendar

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Szyfrowanie plików (punkt 7) - biblioteka "cryptography"
from cryptography.fernet import Fernet

import hashlib  # do hashowania haseł userów (punkt 1)
import json     # do pliku z użytkownikami i hasłami
import uuid     # do generowania ID transakcji cyklicznych

########################
# USTAWIENIA / STAŁE
########################
USER_FILE = "users.json"
TRANSACTIONS_FILE_ENCRYPTED = "transactions_encrypted.bin"  # zaszyfrowany plik
TRANSACTIONS_FILE_DECRYPTED = "transactions_temp.csv"        # roboczo odszyfrowany
BUDGETS_FILE = "budgets.csv"
RECURRING_FILE = "recurring.json"
KEY_FILE = "secret.key"

########################
# FUNKCJE NARZĘDZIOWE
########################

def load_users():
    """Wczytuje użytkowników z pliku JSON (USER_FILE)."""
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users_dict):
    """Zapisuje słownik userów do pliku JSON."""
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_dict, f, indent=2, ensure_ascii=False)

def hash_password(password: str) -> str:
    """Zwraca skrót SHA256 hasła."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_key():
    """Generuje klucz szyfrujący i zapisuje do KEY_FILE."""
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    return key

def load_key() -> bytes:
    """Wczytuje klucz szyfrujący z pliku KEY_FILE (lub tworzy nowy, jeśli brak)."""
    if not os.path.exists(KEY_FILE):
        return generate_key()
    with open(KEY_FILE, 'rb') as f:
        return f.read()

def encrypt_csv(plaintext_csv_path, encrypted_path, key):
    """Szyfruje plik CSV do postaci binarnej za pomocą klucza Fernet."""
    fernet = Fernet(key)
    if not os.path.exists(plaintext_csv_path):
        return
    with open(plaintext_csv_path, 'rb') as file:
        data = file.read()
    encrypted_data = fernet.encrypt(data)
    with open(encrypted_path, 'wb') as file:
        file.write(encrypted_data)

def decrypt_csv(encrypted_path, plaintext_csv_path, key):
    """Odszyfrowuje plik binarny do CSV."""
    if not os.path.exists(encrypted_path):
        return
    fernet = Fernet(key)
    with open(encrypted_path, 'rb') as file:
        encrypted_data = file.read()
    data = fernet.decrypt(encrypted_data)
    with open(plaintext_csv_path, 'wb') as file:
        file.write(data)

########################
# GŁÓWNA KLASA APLIKACJI
########################
class BudgetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Domowy Budżet - Rozszerzona Wersja")
        self.geometry("1200x700")

        # Domyślnie ustawiamy styl "clam", później w zakładce Ustawienia będzie można zmienić
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.current_user = None
        self.users = load_users()  # {username: {'password_hash':...}, ...}
        self.global_key = load_key()

        self.login_window = None
        self.show_login_window()

    ########################
    #   OBSŁUGA LOGOWANIA
    ########################
    def show_login_window(self):
        """Pokazuje okno logowania (Toplevel)."""
        if self.login_window is not None:
            self.login_window.destroy()

        self.login_window = tk.Toplevel(self)
        self.login_window.title("Logowanie")
        self.login_window.geometry("300x200")
        self.login_window.grab_set()  # blokuje fokus

        ttk.Label(self.login_window, text="Nazwa użytkownika:").pack(pady=5)
        self.login_user_var = tk.StringVar()
        ttk.Entry(self.login_window, textvariable=self.login_user_var).pack()

        ttk.Label(self.login_window, text="Hasło:").pack(pady=5)
        self.login_pass_var = tk.StringVar()
        ttk.Entry(self.login_window, textvariable=self.login_pass_var, show="*").pack()

        frame_btn = ttk.Frame(self.login_window)
        frame_btn.pack(pady=10)

        ttk.Button(frame_btn, text="Zaloguj", command=self.attempt_login).grid(row=0, column=0, padx=5)
        ttk.Button(frame_btn, text="Rejestracja", command=self.show_register_window).grid(row=0, column=1, padx=5)

        self.login_window.protocol("WM_DELETE_WINDOW", self.on_login_window_close)

    def on_login_window_close(self):
        """Jeśli user zamknie okno logowania, wyjdź z aplikacji."""
        self.destroy()

    def attempt_login(self):
        username = self.login_user_var.get().strip()
        password = self.login_pass_var.get().strip()

        if username in self.users:
            stored_hash = self.users[username]['password_hash']
            if stored_hash == hash_password(password):
                self.current_user = username
                messagebox.showinfo("Sukces", f"Zalogowano: {username}")
                self.login_window.destroy()
                self.init_main_app()
            else:
                messagebox.showwarning("Błąd logowania", "Niepoprawne hasło.")
        else:
            messagebox.showwarning("Błąd logowania", "Taki użytkownik nie istnieje.")

    def show_register_window(self):
        reg_win = tk.Toplevel(self.login_window)
        reg_win.title("Rejestracja")
        reg_win.geometry("300x200")

        ttk.Label(reg_win, text="Nazwa użytkownika:").pack(pady=5)
        reg_user_var = tk.StringVar()
        ttk.Entry(reg_win, textvariable=reg_user_var).pack()

        ttk.Label(reg_win, text="Hasło:").pack(pady=5)
        reg_pass_var = tk.StringVar()
        ttk.Entry(reg_win, textvariable=reg_pass_var, show="*").pack()

        def do_register():
            user = reg_user_var.get().strip()
            pwd = reg_pass_var.get().strip()
            if not user or not pwd:
                messagebox.showwarning("Błąd", "Pola nie mogą być puste.")
                return
            if user in self.users:
                messagebox.showwarning("Błąd", "Taki użytkownik już istnieje.")
                return
            self.users[user] = {
                'password_hash': hash_password(pwd)
            }
            save_users(self.users)
            messagebox.showinfo("OK", f"Utworzono użytkownika: {user}")
            reg_win.destroy()

        ttk.Button(reg_win, text="Zarejestruj", command=do_register).pack(pady=10)

    ########################
    #   INICJALIZACJA APLIKACJI (po zalogowaniu)
    ########################
    def init_main_app(self):
        # Odszyfrowujemy główny plik transakcji
        decrypt_csv(TRANSACTIONS_FILE_ENCRYPTED, TRANSACTIONS_FILE_DECRYPTED, self.global_key)

        # Wczytujemy transakcje
        self.transactions = []
        self.load_transactions()

        # Wczytujemy budżety
        self.budgets = {}
        self.load_budgets()

        # Wczytujemy transakcje cykliczne
        self.recurring = self.load_recurring()

        # Przetwarzamy ewentualne zaległe transakcje cykliczne
        self.process_recurring_transactions()

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Zakładka Transakcje
        self.tab_transactions = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_transactions, text="Transakcje")
        self.create_transactions_tab()

        # Zakładka Analizy
        self.tab_analysis = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_analysis, text="Analizy")
        self.create_analysis_tab()

        # Zakładka Budżet
        self.tab_budget = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_budget, text="Planowanie Budżetu")
        self.create_budget_tab()

        # Zakładka Kalendarz
        self.tab_calendar = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_calendar, text="Kalendarz")
        self.create_calendar_tab()

        # NOWE: Zakładka „Cykliczne” (obsługa usuwania/edycji transakcji cyklicznych)
        self.tab_recurring = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_recurring, text="Cykliczne")
        self.create_recurring_tab()

        # NOWE: Zakładka „Ustawienia” (wybór motywu – 10 propozycji)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_settings, text="Ustawienia")
        self.create_settings_tab()

        # Menu
        menubar = tk.Menu(self)
        usermenu = tk.Menu(menubar, tearoff=0)
        usermenu.add_command(label="Wyloguj", command=self.logout)
        usermenu.add_command(label="Zamknij", command=self.exit_app)
        menubar.add_cascade(label=f"Użytkownik: {self.current_user}", menu=usermenu)
        self.config(menu=menubar)

        # Odśwież wykresy
        self.update_analysis_charts()

    def exit_app(self):
        self.save_and_encrypt_on_exit()
        self.destroy()

    def logout(self):
        self.save_and_encrypt_on_exit()
        self.current_user = None
        self.notebook.destroy()
        self.show_login_window()

    def save_and_encrypt_on_exit(self):
        self.save_transactions()
        encrypt_csv(TRANSACTIONS_FILE_DECRYPTED, TRANSACTIONS_FILE_ENCRYPTED, self.global_key)
        if os.path.exists(TRANSACTIONS_FILE_DECRYPTED):
            os.remove(TRANSACTIONS_FILE_DECRYPTED)
        self.save_budgets()
        self.save_recurring()

    ########################
    # ODCZYT / ZAPIS TRANSAKCJI
    ########################
    def load_transactions(self):
        self.transactions.clear()
        if not os.path.exists(TRANSACTIONS_FILE_DECRYPTED):
            return
        with open(TRANSACTIONS_FILE_DECRYPTED, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["kwota"] = float(row["kwota"])
                self.transactions.append(row)

    def save_transactions(self):
        fieldnames = ["user", "data", "rodzaj", "kategoria", "opis", "kwota"]
        with open(TRANSACTIONS_FILE_DECRYPTED, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for t in self.transactions:
                writer.writerow(t)

    def load_budgets(self):
        self.budgets.clear()
        if not os.path.exists(BUDGETS_FILE):
            return
        with open(BUDGETS_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 2:
                    cat, limit_str = row
                    try:
                        self.budgets[cat] = float(limit_str)
                    except ValueError:
                        pass

    def save_budgets(self):
        with open(BUDGETS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for cat, limit_ in self.budgets.items():
                writer.writerow([cat, limit_])

    ########################
    # TRANSAKCJE CYKLICZNE
    ########################
    def load_recurring(self):
        if not os.path.exists(RECURRING_FILE):
            return {}
        with open(RECURRING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_recurring(self):
        with open(RECURRING_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.recurring, f, indent=2, ensure_ascii=False)

    def process_recurring_transactions(self):
        today_str = datetime.today().strftime("%Y-%m-%d")
        today_date = datetime.strptime(today_str, "%Y-%m-%d")
        changed = False

        for rec_id, rec_data in self.recurring.items():
            next_date_str = rec_data["next_date"]
            interval_days = rec_data["interval_days"]
            try:
                next_date_obj = datetime.strptime(next_date_str, "%Y-%m-%d")
            except ValueError:
                continue

            while next_date_obj <= today_date:
                # dodajemy transakcję
                t = {
                    "user": rec_data["user"],
                    "data": next_date_obj.strftime("%Y-%m-%d"),
                    "rodzaj": rec_data["rodzaj"],
                    "kategoria": rec_data["kategoria"],
                    "opis": f"[Cykliczna] {rec_data.get('opis','')}",
                    "kwota": float(rec_data["kwota"])
                }
                self.transactions.append(t)
                changed = True

                next_date_obj += timedelta(days=interval_days)

            self.recurring[rec_id]["next_date"] = next_date_obj.strftime("%Y-%m-%d")

        if changed:
            self.save_transactions()

    ########################
    # ZAKŁADKA TRANSAKCJE
    ########################
    def create_transactions_tab(self):
        self.tab_transactions.rowconfigure(2, weight=1)
        self.tab_transactions.columnconfigure(0, weight=1)

        # Filtry
        filter_frame = ttk.LabelFrame(self.tab_transactions, text="Filtry dat")
        filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(filter_frame, text="Od (data):").grid(row=0, column=0, padx=5)
        self.filter_from_var = tk.StringVar()
        self.filter_from_date = DateEntry(filter_frame, textvariable=self.filter_from_var, date_pattern="yyyy-mm-dd")
        self.filter_from_date.grid(row=0, column=1, padx=5)

        ttk.Label(filter_frame, text="Do (data):").grid(row=0, column=2, padx=5)
        self.filter_to_var = tk.StringVar()
        self.filter_to_date = DateEntry(filter_frame, textvariable=self.filter_to_var, date_pattern="yyyy-mm-dd")
        self.filter_to_date.grid(row=0, column=3, padx=5)

        ttk.Button(filter_frame, text="Zastosuj filtr", command=self.apply_filter).grid(row=0, column=4, padx=5)

        # Formularz
        form_frame = ttk.LabelFrame(self.tab_transactions, text="Dodaj / Edytuj transakcję")
        form_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # form: data
        ttk.Label(form_frame, text="Data:").grid(row=0, column=0, padx=5, sticky="e")
        self.date_var = tk.StringVar()
        self.date_entry = DateEntry(form_frame, textvariable=self.date_var, date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=0, column=1, padx=5)

        # rodzaj
        ttk.Label(form_frame, text="Rodzaj:").grid(row=0, column=2, padx=5, sticky="e")
        self.type_var = tk.StringVar(value="Wydatek")
        self.type_menu = ttk.OptionMenu(form_frame, self.type_var, "Wydatek", "Wydatek", "Przychód")
        self.type_menu.grid(row=0, column=3, padx=5)

        # kategoria
        ttk.Label(form_frame, text="Kategoria:").grid(row=0, column=4, padx=5, sticky="e")
        self.category_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.category_var).grid(row=0, column=5, padx=5)

        # kwota
        ttk.Label(form_frame, text="Kwota:").grid(row=1, column=0, padx=5, sticky="e")
        self.amount_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.amount_var).grid(row=1, column=1, padx=5)

        # opis
        ttk.Label(form_frame, text="Opis:").grid(row=1, column=2, padx=5, sticky="e")
        self.desc_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.desc_var, width=50).grid(row=1, column=3, columnspan=3, padx=5)

        self.add_button = ttk.Button(form_frame, text="Dodaj", command=self.add_transaction)
        self.add_button.grid(row=0, column=6, rowspan=2, padx=5, pady=5, sticky="ns")

        self.edit_button = ttk.Button(form_frame, text="Edytuj zazn.", command=self.edit_transaction)
        self.edit_button.grid(row=0, column=7, rowspan=2, padx=5, pady=5, sticky="ns")

        self.save_edit_button = ttk.Button(form_frame, text="Zapisz zmiany", command=self.save_edited_transaction)
        self.save_edit_button.grid(row=0, column=8, rowspan=2, padx=5, pady=5, sticky="ns")
        self.save_edit_button["state"] = "disabled"

        # Tabela
        table_frame = ttk.Frame(self.tab_transactions)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("data","rodzaj","kategoria","opis","kwota")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("data", text="Data")
        self.tree.heading("rodzaj", text="Rodzaj")
        self.tree.heading("kategoria", text="Kategoria")
        self.tree.heading("opis", text="Opis")
        self.tree.heading("kwota", text="Kwota (zł)")

        self.tree.column("data", width=100, anchor="center")
        self.tree.column("rodzaj", width=80, anchor="center")
        self.tree.column("kategoria", width=120, anchor="w")
        self.tree.column("opis", width=300, anchor="w")
        self.tree.column("kwota", width=80, anchor="e")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.delete_button = ttk.Button(table_frame, text="Usuń zaznaczoną transakcję", command=self.remove_transaction)
        self.delete_button.grid(row=1, column=0, pady=5, sticky="we")

        self.show_transactions_in_tree(self.transactions)

    def show_transactions_in_tree(self, trans_list):
        for row_id in self.tree.get_children():
            self.tree.delete(row_id)
        for t in trans_list:
            if t["user"] == self.current_user:
                self.tree.insert("", "end", values=(
                    t["data"], t["rodzaj"], t["kategoria"], t["opis"], f"{t['kwota']:.2f}"
                ))

    def apply_filter(self):
        from_date_str = self.filter_from_var.get().strip()
        to_date_str = self.filter_to_var.get().strip()
        if not from_date_str or not to_date_str:
            self.show_transactions_in_tree(self.transactions)
            return
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawny format daty.")
            return
        filtered = []
        for t in self.transactions:
            if t["user"] == self.current_user:
                t_date = datetime.strptime(t["data"], "%Y-%m-%d")
                if from_date <= t_date <= to_date:
                    filtered.append(t)
        self.show_transactions_in_tree(filtered)

    def add_transaction(self):
        date_val = self.date_var.get().strip()
        rodzaj = self.type_var.get()
        kategoria = self.category_var.get().strip()
        opis = self.desc_var.get().strip()
        kwota_str = self.amount_var.get().strip()
        try:
            kwota = float(kwota_str)
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawna kwota.")
            return
        if not date_val:
            messagebox.showwarning("Błąd", "Data nie może być pusta.")
            return
        transaction = {
            "user": self.current_user,
            "data": date_val,
            "rodzaj": rodzaj,
            "kategoria": kategoria if kategoria else "Brak",
            "opis": opis if opis else "Brak",
            "kwota": kwota
        }
        self.transactions.append(transaction)
        self.save_transactions()

        self.apply_filter()

        # Sprawdź przekroczenie budżetu
        if rodzaj == "Wydatek" and transaction["kategoria"] in self.budgets:
            limit = self.budgets[transaction["kategoria"]]
            spent = sum(t["kwota"] for t in self.transactions
                        if t["user"]==self.current_user and t["rodzaj"]=="Wydatek"
                        and t["kategoria"]==transaction["kategoria"])
            if spent > limit:
                messagebox.showwarning("Przekroczenie budżetu!",
                    f"Kategoria '{transaction['kategoria']}' przekroczyła limit {limit:.2f} zł.\n"
                    f"Obecnie wydano: {spent:.2f} zł.")

        self.update_analysis_charts()

        # Czyścimy pola
        self.category_var.set("")
        self.desc_var.set("")
        self.amount_var.set("")

    def remove_transaction(self):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        self.tree.delete(item_id)

        data_str, rodzaj, kategoria, opis, kwota_str = values
        kwota = float(kwota_str)
        for t in self.transactions:
            if (t["user"]==self.current_user and t["data"]==data_str and t["rodzaj"]==rodzaj
                and t["kategoria"]==kategoria and t["opis"]==opis
                and abs(t["kwota"] - kwota)<1e-9):
                self.transactions.remove(t)
                break
        self.save_transactions()
        self.update_analysis_charts()

    def edit_transaction(self):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        data_str, rodzaj, kategoria, opis, kwota_str = values

        self.date_var.set(data_str)
        self.type_var.set(rodzaj)
        self.category_var.set(kategoria)
        self.desc_var.set(opis)
        self.amount_var.set(kwota_str)

        self.current_edit_item_id = item_id
        self.save_edit_button["state"] = "normal"

    def save_edited_transaction(self):
        if not hasattr(self, 'current_edit_item_id'):
            return
        new_date = self.date_var.get().strip()
        rodzaj = self.type_var.get()
        kat = self.category_var.get().strip()
        opis = self.desc_var.get().strip()
        kwota_str = self.amount_var.get().strip()
        try:
            kwota = float(kwota_str)
        except ValueError:
            return

        old_values = self.tree.item(self.current_edit_item_id, "values")
        old_date, old_rodzaj, old_kat, old_opis, old_kwota_str = old_values
        old_kwota = float(old_kwota_str)

        for t in self.transactions:
            if (t["user"]==self.current_user and t["data"]==old_date and t["rodzaj"]==old_rodzaj
                and t["kategoria"]==old_kat and t["opis"]==old_opis
                and abs(t["kwota"] - old_kwota)<1e-9):
                t["data"] = new_date
                t["rodzaj"] = rodzaj
                t["kategoria"] = kat
                t["opis"] = opis
                t["kwota"] = kwota
                break

        self.save_transactions()
        self.tree.item(self.current_edit_item_id, values=(new_date,rodzaj,kat,opis,f"{kwota:.2f}"))
        self.save_edit_button["state"] = "disabled"
        del self.current_edit_item_id

        self.category_var.set("")
        self.desc_var.set("")
        self.amount_var.set("")
        self.update_analysis_charts()

    ########################
    # ZAKŁADKA ANALIZY
    ########################
    def create_analysis_tab(self):
        self.tab_analysis.rowconfigure(1, weight=1)
        self.tab_analysis.columnconfigure(0, weight=1)

        # Wykres liniowy
        self.fig_line = plt.Figure(figsize=(6,3), dpi=100)
        self.ax_line = self.fig_line.add_subplot(111)
        self.canvas_line = FigureCanvasTkAgg(self.fig_line, master=self.tab_analysis)
        self.canvas_line.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Dół – dwa wykresy (kołowy i słupkowy)
        bottom_frame = ttk.Frame(self.tab_analysis)
        bottom_frame.grid(row=1, column=0, sticky="nsew")
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)
        bottom_frame.rowconfigure(0, weight=1)

        # Kołowy
        self.fig_pie = plt.Figure(figsize=(3,3), dpi=100)
        self.ax_pie = self.fig_pie.add_subplot(111)
        self.canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=bottom_frame)
        self.canvas_pie.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Słupkowy
        self.fig_bar = plt.Figure(figsize=(3,3), dpi=100)
        self.ax_bar = self.fig_bar.add_subplot(111)
        self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=bottom_frame)
        self.canvas_bar.get_tk_widget().grid(row=0, column=1, sticky="nsew")

    def update_analysis_charts(self):
        user_trans = [t for t in self.transactions if t["user"]==self.current_user]

        # Kołowy (przychody vs wydatki)
        total_income = sum(t["kwota"] for t in user_trans if t["rodzaj"]=="Przychód")
        total_expense = sum(t["kwota"] for t in user_trans if t["rodzaj"]=="Wydatek")

        self.ax_pie.clear()
        if total_income==0 and total_expense==0:
            self.ax_pie.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        else:
            values = [total_income, total_expense]
            labels = ["Przychody","Wydatki"]
            colors = ["green","red"]
            self.ax_pie.pie(values, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90)
        self.ax_pie.set_title("Przychody vs Wydatki")
        self.ax_pie.axis("equal")
        self.canvas_pie.draw()

        # Słupkowy (wydatki wg kategorii)
        self.ax_bar.clear()
        expenses_by_cat = {}
        for t in user_trans:
            if t["rodzaj"]=="Wydatek":
                cat = t["kategoria"]
                expenses_by_cat[cat] = expenses_by_cat.get(cat,0)+t["kwota"]
        if not expenses_by_cat:
            self.ax_bar.text(0.5,0.5,"Brak wydatków", ha="center", va="center")
        else:
            cats = list(expenses_by_cat.keys())
            sums = list(expenses_by_cat.values())
            self.ax_bar.bar(cats, sums, color="orange")
            self.ax_bar.set_xticklabels(cats, rotation=45, ha="right")
            self.ax_bar.set_title("Wydatki wg kategorii")
        self.fig_bar.tight_layout()
        self.canvas_bar.draw()

        # Liniowy (saldo miesięczne)
        self.ax_line.clear()
        monthly_data = {}
        for t in user_trans:
            month_key = t["data"][:7]  # YYYY-MM
            monthly_data.setdefault(month_key, 0)
            if t["rodzaj"]=="Przychód":
                monthly_data[month_key]+=t["kwota"]
            else:
                monthly_data[month_key]-=t["kwota"]
        if not monthly_data:
            self.ax_line.text(0.5,0.5,"Brak danych", ha="center", va="center")
        else:
            sorted_months = sorted(monthly_data.keys())
            x_vals = range(len(sorted_months))
            y_vals = [monthly_data[m] for m in sorted_months]
            self.ax_line.plot(x_vals,y_vals,marker='o')
            self.ax_line.set_xticks(x_vals)
            self.ax_line.set_xticklabels(sorted_months, rotation=45, ha="right")
            self.ax_line.set_title("Saldo miesięczne (Przychody - Wydatki)")
            self.ax_line.set_xlabel("Miesiąc")
            self.ax_line.set_ylabel("Saldo")
        self.fig_line.tight_layout()
        self.canvas_line.draw()

    ########################
    # ZAKŁADKA BUDŻET
    ########################
    def create_budget_tab(self):
        top_frame = ttk.Frame(self.tab_budget)
        top_frame.pack(side="top", fill="x", padx=5, pady=5)

        ttk.Label(top_frame, text="Kategoria:").pack(side="left", padx=5)
        self.budget_cat_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.budget_cat_var, width=20).pack(side="left", padx=5)

        ttk.Label(top_frame, text="Limit (zł):").pack(side="left", padx=5)
        self.budget_limit_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.budget_limit_var, width=10).pack(side="left", padx=5)

        ttk.Button(top_frame, text="Ustaw / Zmień limit", command=self.set_budget).pack(side="left", padx=5)

        self.budget_text = tk.Text(self.tab_budget, wrap="none")
        self.budget_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        scroll_y = ttk.Scrollbar(self.tab_budget, orient="vertical", command=self.budget_text.yview)
        self.budget_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")

        self.update_budget_text()

    def set_budget(self):
        cat = self.budget_cat_var.get().strip()
        limit_str = self.budget_limit_var.get().strip()
        if not cat or not limit_str:
            return
        try:
            limit_val = float(limit_str)
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawna wartość limitu.")
            return
        self.budgets[cat] = limit_val
        self.save_budgets()
        self.budget_cat_var.set("")
        self.budget_limit_var.set("")
        self.update_budget_text()

    def update_budget_text(self):
        self.budget_text.config(state="normal")
        self.budget_text.delete("1.0", tk.END)

        self.budget_text.insert(tk.END, f"{'Kategoria':15s} | {'Limit':>10s} | {'Wydano':>10s} | {'Różnica':>10s}\n")
        self.budget_text.insert(tk.END, "-"*60 + "\n")

        user_trans = [t for t in self.transactions if t["user"]==self.current_user and t["rodzaj"]=="Wydatek"]
        expenses_by_cat = {}
        for t in user_trans:
            cat = t["kategoria"]
            expenses_by_cat[cat] = expenses_by_cat.get(cat,0)+t["kwota"]

        all_cats = set(self.budgets.keys())|set(expenses_by_cat.keys())

        for cat in sorted(all_cats):
            limit_val = self.budgets.get(cat, 0.0)
            spent = expenses_by_cat.get(cat, 0.0)
            diff = limit_val - spent
            line = f"{cat:15s} | {limit_val:10.2f} | {spent:10.2f} | {diff:10.2f}"
            if diff<0:
                line+="  (Przekroczono!)"
            line+="\n"
            self.budget_text.insert(tk.END, line)

        self.budget_text.config(state="disabled")

    ########################
    # ZAKŁADKA KALENDARZ
    ########################
    def create_calendar_tab(self):
        self.tab_calendar.rowconfigure(0, weight=1)
        self.tab_calendar.columnconfigure(1, weight=1)

        self.calendar = Calendar(self.tab_calendar, selectmode="day", date_pattern="yyyy-mm-dd")
        self.calendar.grid(row=0, column=0, sticky="ns", padx=5, pady=5)

        self.calendar.bind("<<CalendarSelected>>", self.on_calendar_day_selected)

        self.calendar_text = tk.Text(self.tab_calendar, wrap="none")
        self.calendar_text.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        scroll_y = ttk.Scrollbar(self.tab_calendar, orient="vertical", command=self.calendar_text.yview)
        self.calendar_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.grid(row=0, column=2, sticky="ns")

        # Domyślnie pokazujemy dzisiejsze
        self.show_calendar_day_transactions(datetime.today().strftime("%Y-%m-%d"))

    def on_calendar_day_selected(self, event):
        date_str = self.calendar.get_date()
        self.show_calendar_day_transactions(date_str)

    def show_calendar_day_transactions(self, date_str):
        user_trans = [t for t in self.transactions if t["user"]==self.current_user and t["data"]==date_str]
        self.calendar_text.config(state="normal")
        self.calendar_text.delete("1.0", tk.END)
        self.calendar_text.insert(tk.END, f"Transakcje z dnia {date_str}:\n")
        self.calendar_text.insert(tk.END, "-"*40+"\n")
        if not user_trans:
            self.calendar_text.insert(tk.END, "Brak transakcji.\n")
        else:
            for t in user_trans:
                line = f"{t['rodzaj']} | {t['kategoria']} | {t['opis']} | {t['kwota']:.2f} zł\n"
                self.calendar_text.insert(tk.END, line)
        self.calendar_text.config(state="disabled")

    ########################
    # NOWA ZAKŁADKA CYKLICZNE (edycja/usuwanie)
    ########################
    def create_recurring_tab(self):
        self.tab_recurring.rowconfigure(1, weight=1)
        self.tab_recurring.columnconfigure(0, weight=1)

        # Formularz
        form_frame = ttk.LabelFrame(self.tab_recurring, text="Dodaj / Edytuj transakcję cykliczną")
        form_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Data startowa (next_date)
        ttk.Label(form_frame, text="Data startu:").grid(row=0, column=0, padx=5, sticky="e")
        self.rec_next_date_var = tk.StringVar()
        self.rec_next_date_entry = DateEntry(form_frame, textvariable=self.rec_next_date_var, date_pattern="yyyy-mm-dd")
        self.rec_next_date_entry.grid(row=0, column=1, padx=5)

        # interval_days
        ttk.Label(form_frame, text="Odstęp dni:").grid(row=0, column=2, padx=5, sticky="e")
        self.rec_interval_var = tk.StringVar(value="30")
        ttk.Entry(form_frame, textvariable=self.rec_interval_var, width=5).grid(row=0, column=3, padx=5)

        # Rodzaj
        ttk.Label(form_frame, text="Rodzaj:").grid(row=0, column=4, padx=5, sticky="e")
        self.rec_type_var = tk.StringVar(value="Wydatek")
        self.rec_type_menu = ttk.OptionMenu(form_frame, self.rec_type_var, "Wydatek", "Wydatek", "Przychód")
        self.rec_type_menu.grid(row=0, column=5, padx=5)

        # Kategoria
        ttk.Label(form_frame, text="Kategoria:").grid(row=1, column=0, padx=5, sticky="e")
        self.rec_cat_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.rec_cat_var).grid(row=1, column=1, padx=5)

        # Kwota
        ttk.Label(form_frame, text="Kwota:").grid(row=1, column=2, padx=5, sticky="e")
        self.rec_amount_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.rec_amount_var, width=10).grid(row=1, column=3, padx=5)

        # Opis
        ttk.Label(form_frame, text="Opis:").grid(row=1, column=4, padx=5, sticky="e")
        self.rec_desc_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.rec_desc_var, width=30).grid(row=1, column=5, padx=5, sticky="w")

        self.rec_add_button = ttk.Button(form_frame, text="Dodaj", command=self.add_recurring)
        self.rec_add_button.grid(row=0, column=6, rowspan=2, padx=5, pady=5, sticky="ns")

        self.rec_edit_button = ttk.Button(form_frame, text="Edytuj zazn.", command=self.edit_recurring)
        self.rec_edit_button.grid(row=0, column=7, rowspan=2, padx=5, pady=5, sticky="ns")

        self.rec_save_button = ttk.Button(form_frame, text="Zapisz zmiany", command=self.save_edited_recurring)
        self.rec_save_button.grid(row=0, column=8, rowspan=2, padx=5, pady=5, sticky="ns")
        self.rec_save_button["state"] = "disabled"

        # Tabela
        table_frame = ttk.Frame(self.tab_recurring)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        rec_columns = ("next_date", "interval", "rodzaj", "kategoria", "kwota", "opis", "id")
        self.rec_tree = ttk.Treeview(table_frame, columns=rec_columns, show="headings")
        self.rec_tree.heading("next_date", text="Nast. Data")
        self.rec_tree.heading("interval", text="Odstęp(dni)")
        self.rec_tree.heading("rodzaj", text="Rodzaj")
        self.rec_tree.heading("kategoria", text="Kategoria")
        self.rec_tree.heading("kwota", text="Kwota")
        self.rec_tree.heading("opis", text="Opis")
        self.rec_tree.heading("id", text="ID")

        self.rec_tree.column("next_date", width=100, anchor="center")
        self.rec_tree.column("interval", width=80, anchor="center")
        self.rec_tree.column("rodzaj", width=80, anchor="center")
        self.rec_tree.column("kategoria", width=120, anchor="w")
        self.rec_tree.column("kwota", width=80, anchor="e")
        self.rec_tree.column("opis", width=200, anchor="w")
        self.rec_tree.column("id", width=100, anchor="center")

        scroll_rec = ttk.Scrollbar(table_frame, orient="vertical", command=self.rec_tree.yview)
        self.rec_tree.configure(yscrollcommand=scroll_rec.set)

        self.rec_tree.grid(row=0, column=0, sticky="nsew")
        scroll_rec.grid(row=0, column=1, sticky="ns")

        self.rec_delete_button = ttk.Button(table_frame, text="Usuń zaznaczoną cykliczną", command=self.remove_recurring)
        self.rec_delete_button.grid(row=1, column=0, pady=5, sticky="we")

        self.update_recurring_table()

    def update_recurring_table(self):
        # Czyścimy
        for row_id in self.rec_tree.get_children():
            self.rec_tree.delete(row_id)
        # Dodajemy tylko dla zalogowanego usera
        for rec_id, rec_data in self.recurring.items():
            if rec_data["user"] == self.current_user:
                self.rec_tree.insert("", "end", values=(
                    rec_data["next_date"],
                    rec_data["interval_days"],
                    rec_data["rodzaj"],
                    rec_data["kategoria"],
                    f"{rec_data['kwota']:.2f}",
                    rec_data.get("opis",""),
                    rec_id
                ))

    def add_recurring(self):
        next_date_str = self.rec_next_date_var.get().strip()
        interval_str = self.rec_interval_var.get().strip()
        rodzaj = self.rec_type_var.get()
        kat = self.rec_cat_var.get().strip()
        kwota_str = self.rec_amount_var.get().strip()
        opis = self.rec_desc_var.get().strip()

        if not next_date_str or not interval_str or not kwota_str:
            messagebox.showwarning("Błąd", "Wypełnij wymagane pola (data, odstęp, kwota).")
            return
        try:
            interval_days = int(interval_str)
            kwota = float(kwota_str)
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawne wartości (odstęp, kwota).")
            return

        rec_id = uuid.uuid4().hex
        new_data = {
            "user": self.current_user,
            "next_date": next_date_str,
            "interval_days": interval_days,
            "rodzaj": rodzaj,
            "kategoria": kat if kat else "Brak",
            "kwota": kwota,
            "opis": opis
        }
        self.recurring[rec_id] = new_data
        self.save_recurring()
        self.update_recurring_table()

        # Czyścimy formularz
        self.rec_next_date_var.set("")
        self.rec_interval_var.set("30")
        self.rec_cat_var.set("")
        self.rec_amount_var.set("")
        self.rec_desc_var.set("")

    def remove_recurring(self):
        selection = self.rec_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.rec_tree.item(item_id, "values")
        # values = (next_date, interval, rodzaj, kategoria, kwota, opis, rec_id)
        rec_id = values[-1]  # ost. element
        self.rec_tree.delete(item_id)

        if rec_id in self.recurring:
            del self.recurring[rec_id]
            self.save_recurring()

    def edit_recurring(self):
        selection = self.rec_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.rec_tree.item(item_id, "values")
        # (next_date, interval, rodzaj, kategoria, kwota, opis, rec_id)
        next_date, interval_str, rodzaj, kat, kwota_str, opis, rec_id = values

        self.rec_next_date_var.set(next_date)
        self.rec_interval_var.set(interval_str)
        self.rec_type_var.set(rodzaj)
        self.rec_cat_var.set(kat)
        self.rec_amount_var.set(kwota_str)
        self.rec_desc_var.set(opis)

        self.current_edit_rec_id = rec_id
        self.rec_save_button["state"] = "normal"

    def save_edited_recurring(self):
        if not hasattr(self, 'current_edit_rec_id'):
            return
        rec_id = self.current_edit_rec_id

        new_date = self.rec_next_date_var.get().strip()
        new_interval_str = self.rec_interval_var.get().strip()
        new_rodzaj = self.rec_type_var.get()
        new_kat = self.rec_cat_var.get().strip()
        new_kwota_str = self.rec_amount_var.get().strip()
        new_opis = self.rec_desc_var.get().strip()

        try:
            new_interval = int(new_interval_str)
            new_kwota = float(new_kwota_str)
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawne wartości.")
            return

        if rec_id in self.recurring:
            self.recurring[rec_id]["next_date"] = new_date
            self.recurring[rec_id]["interval_days"] = new_interval
            self.recurring[rec_id]["rodzaj"] = new_rodzaj
            self.recurring[rec_id]["kategoria"] = new_kat if new_kat else "Brak"
            self.recurring[rec_id]["kwota"] = new_kwota
            self.recurring[rec_id]["opis"] = new_opis

        self.save_recurring()
        self.update_recurring_table()

        self.rec_save_button["state"] = "disabled"
        del self.current_edit_rec_id

        # Czyścimy formularz
        self.rec_next_date_var.set("")
        self.rec_interval_var.set("30")
        self.rec_cat_var.set("")
        self.rec_amount_var.set("")
        self.rec_desc_var.set("")

    ########################
    # NOWA ZAKŁADKA USTAWIENIA (wybór motywu - 10 propozycji)
    ########################
    def create_settings_tab(self):
        settings_frame = ttk.LabelFrame(self.tab_settings, text="Motywy (Themes)")
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Przygotuj listę motywów (niektóre mogą nie istnieć w danym systemie)
        self.available_themes = [
            "clam", "alt", "default", "classic",
            "vista", "xpnative", "winnative",
            "plastik",  # często nie jest domyślnie zainstalowany
            "breeze",   # j.w.
            "radiance"  # j.w.
        ]

        ttk.Label(settings_frame, text="Wybierz motyw:").pack(pady=5)

        self.theme_var = tk.StringVar(value=self.style.theme_use())
        self.theme_combo = ttk.Combobox(settings_frame, textvariable=self.theme_var,
                                        values=self.available_themes, state="readonly")
        self.theme_combo.pack(pady=5)

        ttk.Button(settings_frame, text="Zastosuj", command=self.apply_theme).pack(pady=5)

    def apply_theme(self):
        chosen_theme = self.theme_var.get()
        try:
            self.style.theme_use(chosen_theme)
        except tk.TclError:
            messagebox.showwarning("Błąd motywu",
                                   f"Motyw '{chosen_theme}' nie jest dostępny w tym systemie.")
        # W niektórych przypadkach trzeba odświeżyć widżety (przeładowanie stylów).
        # Najprostsze to np. unmap/ponowne mapowanie okna, ewentualnie "update".

########################
#   URUCHOMIENIE
########################
if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()

