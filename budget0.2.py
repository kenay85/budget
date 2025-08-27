# --- IMPORTY STANDARDOWE I ZEWNĘTRZNE ---
import tkinter as tk  # główna biblioteka GUI
from tkinter import ttk, messagebox  # widżety ttk i okna dialogowe
import csv  # obsługa plików CSV
import os  # operacje na plikach/ścieżkach
from datetime import datetime, timedelta  # daty i operacje na nich
from tkcalendar import DateEntry, Calendar  # kalendarze/wybór daty

import matplotlib  # biblioteka wykresów
matplotlib.use("TkAgg")  # backend Tkinter dla matplotlib
import matplotlib.pyplot as plt  # API pyplot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # osadzanie wykresów w Tk

from cryptography.fernet import Fernet  # szyfrowanie/odszyfrowywanie plików

import hashlib  # haszowanie haseł
import json     # pliki JSON (użytkownicy, cykliczne)
import uuid     # generowanie unikalnych ID dla cyklicznych

# --- STAŁE / ŚCIEŻKI PLIKÓW ---
USER_FILE = "users.json"                               # plik z użytkownikami i hashami
TRANSACTIONS_FILE_ENCRYPTED = "transactions_encrypted.bin"  # zaszyfrowane transakcje
TRANSACTIONS_FILE_DECRYPTED = "transactions_temp.csv"       # tymczasowy CSV po odszyfrowaniu
BUDGETS_FILE = "budgets.csv"                          # budżety (CSV)
RECURRING_FILE = "recurring.json"                     # transakcje cykliczne (JSON)
KEY_FILE = "secret.key"                               # klucz do Fernet

# --- FUNKCJE NARZĘDZIOWE: UŻYTKOWNICY I HASŁA ---
def load_users():
    """Wczytuje użytkowników (dict) z USER_FILE lub zwraca pusty dict."""
    if not os.path.exists(USER_FILE):  # jeśli plik nie istnieje
        return {}                      # zwróć pustą strukturę
    with open(USER_FILE, 'r', encoding='utf-8') as f:  # otwórz JSON do odczytu
        return json.load(f)                            # wczytaj i zwróć dict

def save_users(users_dict):
    """Zapisuje słownik użytkowników do USER_FILE (pretty JSON)."""
    with open(USER_FILE, 'w', encoding='utf-8') as f:            # otwórz do zapisu
        json.dump(users_dict, f, indent=2, ensure_ascii=False)   # zapisz ładnie sformatowany

def hash_password(password: str) -> str:
    """Zwraca SHA256 hasła (hex)."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()  # oblicz hash

# --- FUNKCJE NARZĘDZIOWE: KLUCZ I SZYFROWANIE ---
def generate_key():
    """Generuje klucz Fernet i zapisuje do KEY_FILE; zwraca bytes."""
    key = Fernet.generate_key()              # wygeneruj losowy klucz
    with open(KEY_FILE, 'wb') as f:          # zapisz do pliku binarnie
        f.write(key)                         # zapisz klucz
    return key                               # zwróć klucz

def load_key() -> bytes:
    """Wczytuje klucz z KEY_FILE; jeśli brak, tworzy nowy."""
    if not os.path.exists(KEY_FILE):   # jeśli brak klucza
        return generate_key()          # wygeneruj nowy
    with open(KEY_FILE, 'rb') as f:    # wczytaj klucz
        return f.read()                # zwróć bytes

def encrypt_csv(plaintext_csv_path, encrypted_path, key):
    """Szyfruje CSV (bytes) do pliku binarnego Fernet."""
    fernet = Fernet(key)                                    # obiekt Fernet
    if not os.path.exists(plaintext_csv_path):              # jeśli nie ma CSV
        return                                              # nie rób nic
    with open(plaintext_csv_path, 'rb') as file:            # czytaj CSV binarnie
        data = file.read()                                  # wczytaj treść
    encrypted_data = fernet.encrypt(data)                   # zaszyfruj
    with open(encrypted_path, 'wb') as file:                # zapisz binarnie
        file.write(encrypted_data)                          # zapisz szyfrogram

def decrypt_csv(encrypted_path, plaintext_csv_path, key):
    """Odszyfrowuje plik binarny Fernet do CSV."""
    if not os.path.exists(encrypted_path):          # jeśli nie ma szyfrogramu
        return                                      # pomiń
    fernet = Fernet(key)                            # obiekt Fernet
    with open(encrypted_path, 'rb') as file:        # czytaj szyfrogram
        encrypted_data = file.read()                # wczytaj bytes
    data = fernet.decrypt(encrypted_data)           # odszyfruj do bytes
    with open(plaintext_csv_path, 'wb') as file:    # zapisz CSV binarnie
        file.write(data)                            # zapisz jawny CSV

# --- LOGIN: OSOBNE OKNO ROOT PRZED STARTEM APLIKACJI ---
def run_login_dialog(users_dict):
    """
    Pokazuje proste okno logowania (osobny root).
    Zwraca nazwę użytkownika po sukcesie albo None przy anulowaniu.
    """
    root = tk.Tk()                                     # osobny root tylko do logowania
    root.title("Logowanie")                            # tytuł okna
    root.geometry("320x210")                           # początkowy rozmiar

    # wycentruj okno na ekranie (po aktualizacji rozmiarów)
    root.update_idletasks()                            # odśwież dane geometryczne
    w, h = 320, 210                                    # szer. i wys. okna
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()  # rozmiar ekranu
    x, y = (sw - w)//2, (sh - h)//3                    # pozycja okna
    root.geometry(f"{w}x{h}+{x}+{y}")                  # ustaw geometrię

    user_var = tk.StringVar()                          # zmienna na login
    pass_var = tk.StringVar()                          # zmienna na hasło
    result = {"user": None}                            # pojemnik na wynik (domknięcie)

    # nagłówek/etykiety + pola
    ttk.Label(root, text="Nazwa użytkownika:").pack(pady=(12,4))  # etykieta login
    ttk.Entry(root, textvariable=user_var).pack()                 # pole login
    ttk.Label(root, text="Hasło:").pack(pady=(10,4))              # etykieta hasło
    ent_pwd = ttk.Entry(root, textvariable=pass_var, show="*")    # pole hasło
    ent_pwd.pack()                                                # pokaż pole

    # przyciski w ramce
    btns = ttk.Frame(root)                          # kontener na przyciski
    btns.pack(pady=12)                              # pokaż ramkę
    # funkcja logowania (sprawdzenie hasha)
    def on_login():
        u = user_var.get().strip()                  # pobierz login
        p = pass_var.get().strip()                  # pobierz hasło
        if u in users_dict and users_dict[u]['password_hash'] == hash_password(p):  # weryfikacja
            result["user"] = u                      # zapisz wynik
            root.destroy()                          # zamknij okno logowania
        else:
            messagebox.showwarning("Błąd", "Niepoprawne dane logowania.")  # komunikat

    # funkcja rejestracji (dodaje nowego usera do users.json)
    def on_register():
        reg = tk.Toplevel(root)                                   # podrzędne okno rejestracji
        reg.title("Rejestracja")                                  # tytuł
        reg.geometry("320x200")                                   # rozmiar
        reg.transient(root)                                       # powiązanie z login
        reg.lift()                                                # do góry
        # pola rejestracji
        usr_v = tk.StringVar()                                    # zmienna login
        pwd_v = tk.StringVar()                                    # zmienna hasło
        ttk.Label(reg, text="Nowy użytkownik:").pack(pady=(12,4)) # etykieta
        ttk.Entry(reg, textvariable=usr_v).pack()                 # pole login
        ttk.Label(reg, text="Hasło:").pack(pady=(10,4))           # etykieta
        ttk.Entry(reg, textvariable=pwd_v, show="*").pack()       # pole hasło
        # zapisz użytkownika
        def do_register():
            u = usr_v.get().strip()                               # odczytaj login
            p = pwd_v.get().strip()                               # odczytaj hasło
            if not u or not p:                                    # walidacja pustych pól
                messagebox.showwarning("Błąd", "Pola nie mogą być puste.")  # ostrzeżenie
                return                                            # przerwij
            if u in users_dict:                                   # czy istnieje?
                messagebox.showwarning("Błąd", "Taki użytkownik już istnieje.")  # ostrzeżenie
                return                                            # przerwij
            users_dict[u] = {'password_hash': hash_password(p)}   # dodaj usera z hashem
            save_users(users_dict)                                # zapisz do pliku
            messagebox.showinfo("Sukces", f"Utworzono użytkownika: {u}")  # info
            reg.destroy()                                         # zamknij rejestrację
        ttk.Button(reg, text="Zarejestruj", command=do_register).pack(pady=12)  # przycisk
        reg.focus_set()                                           # fokus na okno

    ttk.Button(btns, text="Zaloguj", command=on_login).grid(row=0, column=0, padx=6)   # przycisk Loguj
    ttk.Button(btns, text="Rejestracja", command=on_register).grid(row=0, column=1, padx=6)  # przycisk Rejestracja

    ent_pwd.focus_set()                                  # ustaw fokus na haśle
    root.protocol("WM_DELETE_WINDOW", root.destroy)      # zamknięcie = wyjście z logowania
    root.mainloop()                                      # uruchom pętlę okna logowania
    return result["user"]                                # zwróć nazwę użytkownika lub None

# --- GŁÓWNA KLASA APLIKACJI (BEZ LOGOWANIA W ŚRODKU) ---
class BudgetApp(tk.Tk):
    def __init__(self):
        super().__init__()                              # inicjalizacja Tk
        self.title("Domowy Budżet - Rozszerzona Wersja")# tytuł okna
        self.geometry("1200x700")                       # wymiary okna

        self.style = ttk.Style(self)                    # styl ttk
        self.style.theme_use("clam")                    # motyw domyślny

        self.current_user = None                        # aktualny użytkownik (ustawiony po logowaniu)
        self.users = load_users()                       # słownik użytkowników
        self.global_key = load_key()                    # klucz Fernet

        # UWAGA: nie tworzymy UI tutaj — zrobimy to dopiero w init_main_app()  # komentarz

    # --- START APLIKACJI PO ZALOGOWANIU ---
    def init_main_app(self):
        """Inicjuje wszystkie zakładki i dane po zalogowaniu."""
        decrypt_csv(TRANSACTIONS_FILE_ENCRYPTED, TRANSACTIONS_FILE_DECRYPTED, self.global_key)  # odszyfruj CSV

        self.transactions = []          # lista transakcji
        self.load_transactions()        # wczytaj transakcje z CSV

        self.budgets = {}               # słownik budżetów
        self.load_budgets()             # wczytaj budżety z CSV

        self.recurring = self.load_recurring()  # wczytaj cykliczne z JSON
        self.process_recurring_transactions()   # dopisz zaległe wystąpienia

        self.notebook = ttk.Notebook(self)  # główny notebook z zakładkami
        self.notebook.pack(fill="both", expand=True)  # rozciągnij w oknie

        self.tab_transactions = ttk.Frame(self.notebook)       # zakładka transakcji
        self.notebook.add(self.tab_transactions, text="Transakcje")  # dodaj zakładkę
        self.create_transactions_tab()                         # zbuduj UI zakładki

        self.tab_analysis = ttk.Frame(self.notebook)           # zakładka analizy
        self.notebook.add(self.tab_analysis, text="Analizy")   # dodaj
        self.create_analysis_tab()                             # zbuduj

        self.tab_budget = ttk.Frame(self.notebook)             # zakładka budżetu
        self.notebook.add(self.tab_budget, text="Planowanie Budżetu")  # dodaj
        self.create_budget_tab()                               # zbuduj

        self.tab_calendar = ttk.Frame(self.notebook)           # zakładka kalendarza
        self.notebook.add(self.tab_calendar, text="Kalendarz") # dodaj
        self.create_calendar_tab()                             # zbuduj

        self.tab_recurring = ttk.Frame(self.notebook)          # zakładka cyklicznych
        self.notebook.add(self.tab_recurring, text="Cykliczne")# dodaj
        self.create_recurring_tab()                            # zbuduj

        self.tab_settings = ttk.Frame(self.notebook)           # zakładka ustawień
        self.notebook.add(self.tab_settings, text="Ustawienia")# dodaj
        self.create_settings_tab()                             # zbuduj

        menubar = tk.Menu(self)                                # menu główne
        usermenu = tk.Menu(menubar, tearoff=0)                 # podmenu użytkownika
        usermenu.add_command(label="Wyloguj", command=self.logout)  # pozycja „Wyloguj”
        usermenu.add_command(label="Zamknij", command=self.exit_app) # pozycja „Zamknij”
        menubar.add_cascade(label=f"Użytkownik: {self.current_user}", menu=usermenu)  # wstaw do paska
        self.config(menu=menubar)                              # ustaw menubar

        self.update_analysis_charts()                          # odśwież wykresy

    # --- WYJŚCIE / WYLOGOWANIE ---
    def exit_app(self):
        """Zapisuje, szyfruje i zamyka aplikację."""
        self.save_and_encrypt_on_exit()  # zapisz i zaszyfruj
        self.destroy()                   # zamknij okno aplikacji

    def logout(self):
        """Wylogowuje użytkownika i wraca do ekranu logowania."""
        self.save_and_encrypt_on_exit()  # zapisz i zaszyfruj
        self.current_user = None         # wyczyść użytkownika
        if hasattr(self, "notebook"):    # jeśli notebook istnieje
            self.notebook.destroy()      # zniszcz UI
        # Po wylogowaniu znów pokaż ekran logowania jako osobne okno:   # komentarz
        user = run_login_dialog(self.users)            # wywołaj login
        if not user:                                   # jeśli anulowano
            self.destroy()                             # zamknij aplikację
            return                                     # wyjdź z funkcji
        self.current_user = user                       # ustaw zalogowanego
        self.init_main_app()                           # ponownie zbuduj UI

    def save_and_encrypt_on_exit(self):
        """Zapisuje dane i szyfruje CSV, usuwa tymczasowy plik."""
        self.save_transactions()  # zapisz CSV jawny
        encrypt_csv(TRANSACTIONS_FILE_DECRYPTED, TRANSACTIONS_FILE_ENCRYPTED, self.global_key)  # zaszyfruj
        if os.path.exists(TRANSACTIONS_FILE_DECRYPTED):  # jeśli istnieje tymczasowy CSV
            os.remove(TRANSACTIONS_FILE_DECRYPTED)       # usuń go
        self.save_budgets()      # zapisz budżety
        self.save_recurring()    # zapisz cykliczne

    # --- ODCZYT / ZAPIS TRANSAKCJI ---
    def load_transactions(self):
        """Wczytuje transakcje z CSV do listy self.transactions."""
        self.transactions.clear()                                           # wyczyść listę
        if not os.path.exists(TRANSACTIONS_FILE_DECRYPTED):                 # jeśli brak CSV
            return                                                          # pomiń
        with open(TRANSACTIONS_FILE_DECRYPTED, 'r', newline='', encoding='utf-8') as f:  # otwórz CSV
            reader = csv.DictReader(f)                                      # czytnik wierszy
            for row in reader:                                              # iteruj wiersze
                row["kwota"] = float(row["kwota"])                          # rzutuj kwotę
                self.transactions.append(row)                               # dodaj do listy

    def save_transactions(self):
        """Zapisuje listę transakcji do CSV jawnego (tymczasowego)."""
        fieldnames = ["user", "data", "rodzaj", "kategoria", "opis", "kwota"]    # nagłówki
        with open(TRANSACTIONS_FILE_DECRYPTED, 'w', newline='', encoding='utf-8') as f:  # otwórz do zapisu
            writer = csv.DictWriter(f, fieldnames=fieldnames)                      # pisarz CSV
            writer.writeheader()                                                   # nagłówek
            for t in self.transactions:                                            # iteruj transakcje
                writer.writerow(t)                                                 # zapisz wiersz

    # --- ODCZYT / ZAPIS BUDŻETÓW ---
    def load_budgets(self):
        """Wczytuje budżety z CSV do self.budgets (dict)."""
        self.budgets.clear()                                           # wyczyść dict
        if not os.path.exists(BUDGETS_FILE):                           # jeśli brak pliku
            return                                                     # pomiń
        with open(BUDGETS_FILE, 'r', newline='', encoding='utf-8') as f:  # otwórz do odczytu
            reader = csv.reader(f)                                         # czytnik CSV
            for row in reader:                                             # iteruj wiersze
                if len(row) == 2:                                          # spodziewamy się 2 kolumn
                    cat, limit_str = row                                   # odczytaj
                    try:
                        self.budgets[cat] = float(limit_str)               # rzutuj na float
                    except ValueError:
                        pass                                               # pomiń błędne

    def save_budgets(self):
        """Zapisuje self.budgets (dict) do CSV."""
        with open(BUDGETS_FILE, 'w', newline='', encoding='utf-8') as f:  # otwórz do zapisu
            writer = csv.writer(f)                                         # pisarz CSV
            for cat, limit_ in self.budgets.items():                       # iteruj po dict
                writer.writerow([cat, limit_])                             # zapisz wiersz

    # --- ODCZYT / ZAPIS CYKLICZNYCH ---
    def load_recurring(self):
        """Wczytuje transakcje cykliczne z JSON (dict)."""
        if not os.path.exists(RECURRING_FILE):         # jeśli brak pliku
            return {}                                   # zwróć pusty dict
        with open(RECURRING_FILE, 'r', encoding='utf-8') as f:  # wczytaj JSON
            return json.load(f)                         # zwróć dict

    def save_recurring(self):
        """Zapisuje self.recurring (dict) do JSON (ładny format)."""
        with open(RECURRING_FILE, 'w', encoding='utf-8') as f:       # otwórz do zapisu
            json.dump(self.recurring, f, indent=2, ensure_ascii=False)  # zapisz pretty

    def process_recurring_transactions(self):
        """Dopisuje zaległe wystąpienia transakcji cyklicznych do self.transactions."""
        today_str = datetime.today().strftime("%Y-%m-%d")      # dzisiejsza data jako string
        today_date = datetime.strptime(today_str, "%Y-%m-%d")  # obiekt datetime dzisiejszy
        changed = False                                        # flaga zmian

        for rec_id, rec_data in self.recurring.items():        # iteruj po cyklicznych
            next_date_str = rec_data.get("next_date", "")      # data kolejnego wystąpienia
            interval_days = rec_data.get("interval_days", 0)   # odstęp w dniach
            try:
                next_date_obj = datetime.strptime(next_date_str, "%Y-%m-%d")  # parsuj datę
            except ValueError:
                continue                                       # błędna data -> pomiń

            while next_date_obj <= today_date:                 # dopóki „zalega”
                t = {                                          # zbuduj transakcję
                    "user": rec_data["user"],                  # użytkownik
                    "data": next_date_obj.strftime("%Y-%m-%d"),# data wystąpienia
                    "rodzaj": rec_data["rodzaj"],              # rodzaj (Przychód/Wydatek)
                    "kategoria": rec_data["kategoria"],        # kategoria
                    "opis": f"[Cykliczna] {rec_data.get('opis','')}",  # opis z prefiksem
                    "kwota": float(rec_data["kwota"])          # kwota (float)
                }
                self.transactions.append(t)                    # dopisz do listy
                changed = True                                 # ustaw flagę
                next_date_obj += timedelta(days=interval_days) # przesuń na kolejną datę

            self.recurring[rec_id]["next_date"] = next_date_obj.strftime("%Y-%m-%d")  # zaktualizuj next_date

        if changed:                         # jeśli były dopisane
            self.save_transactions()        # zapisz CSV

    # --- ZAKŁADKA: TRANSAKCJE ---
    def create_transactions_tab(self):
        """Buduje UI zakładki 'Transakcje'."""
        self.tab_transactions.rowconfigure(2, weight=1)   # rozciąganie wiersza tabeli
        self.tab_transactions.columnconfigure(0, weight=1)  # rozciąganie kolumny

        filter_frame = ttk.LabelFrame(self.tab_transactions, text="Filtry dat")  # ramka filtrów
        filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)          # umieść na siatce

        ttk.Label(filter_frame, text="Od (data):").grid(row=0, column=0, padx=5)  # etykieta od
        self.filter_from_var = tk.StringVar()                                     # zmienna od
        self.filter_from_date = DateEntry(filter_frame, textvariable=self.filter_from_var, date_pattern="yyyy-mm-dd")  # wybór daty
        self.filter_from_date.grid(row=0, column=1, padx=5)                       # pozycja

        ttk.Label(filter_frame, text="Do (data):").grid(row=0, column=2, padx=5)  # etykieta do
        self.filter_to_var = tk.StringVar()                                       # zmienna do
        self.filter_to_date = DateEntry(filter_frame, textvariable=self.filter_to_var, date_pattern="yyyy-mm-dd")  # wybór daty
        self.filter_to_date.grid(row=0, column=3, padx=5)                         # pozycja

        ttk.Button(filter_frame, text="Zastosuj filtr", command=self.apply_filter).grid(row=0, column=4, padx=5)  # przycisk filtra

        form_frame = ttk.LabelFrame(self.tab_transactions, text="Dodaj / Edytuj transakcję")  # ramka formularza
        form_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)                         # pozycja na siatce

        ttk.Label(form_frame, text="Data:").grid(row=0, column=0, padx=5, sticky="e")   # etykieta data
        self.date_var = tk.StringVar()                                                  # zmienna data
        self.date_entry = DateEntry(form_frame, textvariable=self.date_var, date_pattern='yyyy-mm-dd')  # wybór daty
        self.date_entry.grid(row=0, column=1, padx=5)                                   # pozycja

        ttk.Label(form_frame, text="Rodzaj:").grid(row=0, column=2, padx=5, sticky="e") # etykieta rodzaj
        self.type_var = tk.StringVar(value="Wydatek")                                   # domyślnie Wydatek
        self.type_menu = ttk.OptionMenu(form_frame, self.type_var, "Wydatek", "Wydatek", "Przychód")  # menu rodzaju
        self.type_menu.grid(row=0, column=3, padx=5)                                     # pozycja

        ttk.Label(form_frame, text="Kategoria:").grid(row=0, column=4, padx=5, sticky="e")  # etykieta kategoria
        self.category_var = tk.StringVar()                                                  # zmienna kategoria
        ttk.Entry(form_frame, textvariable=self.category_var).grid(row=0, column=5, padx=5) # pole kategoria

        ttk.Label(form_frame, text="Kwota:").grid(row=1, column=0, padx=5, sticky="e")  # etykieta kwota
        self.amount_var = tk.StringVar()                                                # zmienna kwota
        ttk.Entry(form_frame, textvariable=self.amount_var).grid(row=1, column=1, padx=5)  # pole kwota

        ttk.Label(form_frame, text="Opis:").grid(row=1, column=2, padx=5, sticky="e")   # etykieta opis
        self.desc_var = tk.StringVar()                                                  # zmienna opis
        ttk.Entry(form_frame, textvariable=self.desc_var, width=50).grid(row=1, column=3, columnspan=3, padx=5)  # pole opis

        self.add_button = ttk.Button(form_frame, text="Dodaj", command=self.add_transaction)  # przycisk Dodaj
        self.add_button.grid(row=0, column=6, rowspan=2, padx=5, pady=5, sticky="ns")         # pozycja przycisku

        self.edit_button = ttk.Button(form_frame, text="Edytuj zazn.", command=self.edit_transaction)  # przycisk Edytuj
        self.edit_button.grid(row=0, column=7, rowspan=2, padx=5, pady=5, sticky="ns")                 # pozycja

        self.save_edit_button = ttk.Button(form_frame, text="Zapisz zmiany", command=self.save_edited_transaction)  # przycisk Zapisz
        self.save_edit_button.grid(row=0, column=8, rowspan=2, padx=5, pady=5, sticky="ns")                         # pozycja
        self.save_edit_button["state"] = "disabled"                                                                  # nieaktywny na start

        table_frame = ttk.Frame(self.tab_transactions)                   # ramka tabeli
        table_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5) # pozycja ramki
        table_frame.rowconfigure(0, weight=1)                            # rozciągaj w pionie
        table_frame.columnconfigure(0, weight=1)                         # rozciągaj w poziomie

        columns = ("data","rodzaj","kategoria","opis","kwota")           # kolumny tabeli
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")  # tabela
        self.tree.heading("data", text="Data")                           # nagłówek kolumny
        self.tree.heading("rodzaj", text="Rodzaj")                       # j.w.
        self.tree.heading("kategoria", text="Kategoria")                 # j.w.
        self.tree.heading("opis", text="Opis")                           # j.w.
        self.tree.heading("kwota", text="Kwota (zł)")                    # j.w.

        self.tree.column("data", width=100, anchor="center")             # parametry kolumn
        self.tree.column("rodzaj", width=80, anchor="center")            # j.w.
        self.tree.column("kategoria", width=120, anchor="w")             # j.w.
        self.tree.column("opis", width=300, anchor="w")                  # j.w.
        self.tree.column("kwota", width=80, anchor="e")                  # j.w.

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)  # scrollbar pionowy
        self.tree.configure(yscrollcommand=scrollbar.set)                                    # powiąż scroll

        self.tree.grid(row=0, column=0, sticky="nsew")                # umieść tabelę
        scrollbar.grid(row=0, column=1, sticky="ns")                  # umieść scroll

        self.delete_button = ttk.Button(table_frame, text="Usuń zaznaczoną transakcję", command=self.remove_transaction)  # przycisk Usuń
        self.delete_button.grid(row=1, column=0, pady=5, sticky="we")                                                      # pozycja

        self.show_transactions_in_tree(self.transactions)             # pokaż dane w tabeli

    def show_transactions_in_tree(self, trans_list):
        """Wyświetla przekazaną listę transakcji w tabeli (tylko bieżącego usera)."""
        for row_id in self.tree.get_children():                   # iteruj istniejące wiersze
            self.tree.delete(row_id)                              # usuń każdy (czyszczenie)
        for t in trans_list:                                      # iteruj transakcje
            if t["user"] == self.current_user:                    # filtruj po userze
                self.tree.insert("", "end", values=(              # dodaj wiersz
                    t["data"], t["rodzaj"], t["kategoria"], t["opis"], f"{t['kwota']:.2f}"
                ))

    def apply_filter(self):
        """Filtruje transakcje po zakresie dat i odświeża tabelę."""
        from_date_str = self.filter_from_var.get().strip()            # data od
        to_date_str = self.filter_to_var.get().strip()                # data do
        if not from_date_str or not to_date_str:                      # jeśli brak dat
            self.show_transactions_in_tree(self.transactions)         # pokaż wszystko
            return                                                    # wyjdź
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d")  # parsuj od
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d")      # parsuj do
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawny format daty.")  # ostrzeżenie
            return
        filtered = []                                                # lista wyników
        for t in self.transactions:                                  # iteruj transakcje
            if t["user"] == self.current_user:                       # filtr user
                t_date = datetime.strptime(t["data"], "%Y-%m-%d")    # parsuj datę
                if from_date <= t_date <= to_date:                   # sprawdź zakres
                    filtered.append(t)                               # dodaj do wyniku
        self.show_transactions_in_tree(filtered)                     # pokaż przefiltrowane

    def add_transaction(self):
        """Dodaje transakcję z formularza i odświeża."""
        date_val = self.date_var.get().strip()                   # data
        rodzaj = self.type_var.get()                             # rodzaj
        kategoria = self.category_var.get().strip()              # kategoria
        opis = self.desc_var.get().strip()                       # opis
        kwota_str = self.amount_var.get().strip()                # kwota (tekst)
        try:
            kwota = float(kwota_str)                             # rzutuj na float
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawna kwota.") # ostrzeżenie
            return
        if not date_val:                                         # pusta data?
            messagebox.showwarning("Błąd", "Data nie może być pusta.")  # ostrzeżenie
            return
        transaction = {                                          # słownik transakcji
            "user": self.current_user,                           # user
            "data": date_val,                                    # data
            "rodzaj": rodzaj,                                    # rodzaj
            "kategoria": kategoria if kategoria else "Brak",     # kategoria
            "opis": opis if opis else "Brak",                    # opis
            "kwota": kwota                                       # kwota
        }
        self.transactions.append(transaction)                    # dodaj do listy
        self.save_transactions()                                 # zapisz CSV

        self.apply_filter()                                      # odśwież tabelę (z filtrami)

        if rodzaj == "Wydatek" and transaction["kategoria"] in self.budgets:  # jeśli kontrolujemy budżet
            limit = self.budgets[transaction["kategoria"]]                    # limit kategorii
            spent = sum(t["kwota"] for t in self.transactions                 # suma wydatków w kat.
                        if t["user"]==self.current_user and t["rodzaj"]=="Wydatek"
                        and t["kategoria"]==transaction["kategoria"])
            if spent > limit:                                                 # przekroczono?
                messagebox.showwarning("Przekroczenie budżetu!",
                    f"Kategoria '{transaction['kategoria']}' przekroczyła limit {limit:.2f} zł.\n"
                    f"Obecnie wydano: {spent:.2f} zł.")                      # ostrzeżenie

        self.update_analysis_charts()                          # odśwież wykresy

        self.category_var.set("")                              # wyczyść pola
        self.desc_var.set("")                                  # j.w.
        self.amount_var.set("")                                # j.w.

    def remove_transaction(self):
        """Usuwa zaznaczoną transakcję z tabeli i listy."""
        selection = self.tree.selection()                                  # pobierz zaznaczenie
        if not selection:                                                  # jeśli brak
            return                                                         # wyjdź
        item_id = selection[0]                                             # id wiersza
        values = self.tree.item(item_id, "values")                         # pobierz wartości
        self.tree.delete(item_id)                                          # usuń wiersz z tabeli

        data_str, rodzaj, kategoria, opis, kwota_str = values              # rozpakuj wartości
        kwota = float(kwota_str)                                           # rzutuj kwotę
        for t in self.transactions:                                        # szukaj w liście
            if (t["user"]==self.current_user and t["data"]==data_str and t["rodzaj"]==rodzaj
                and t["kategoria"]==kategoria and t["opis"]==opis
                and abs(t["kwota"] - kwota)<1e-9):                         # dopasowanie po polach
                self.transactions.remove(t)                                # usuń z listy
                break                                                      # zakończ
        self.save_transactions()                                           # zapisz CSV
        self.update_analysis_charts()                                      # odśwież wykresy

    def edit_transaction(self):
        """Ładuje zaznaczoną transakcję do formularza do edycji."""
        selection = self.tree.selection()                          # zaznaczenie
        if not selection:                                          # jeśli brak
            return                                                 # wyjdź
        item_id = selection[0]                                     # id wiersza
        values = self.tree.item(item_id, "values")                 # wartości wiersza
        data_str, rodzaj, kategoria, opis, kwota_str = values      # rozpakuj

        self.date_var.set(data_str)                                # ustaw datę
        self.type_var.set(rodzaj)                                  # ustaw rodzaj
        self.category_var.set(kategoria)                           # ustaw kategorię
        self.desc_var.set(opis)                                    # ustaw opis
        self.amount_var.set(kwota_str)                             # ustaw kwotę

        self.current_edit_item_id = item_id                        # zapamiętaj edytowany wiersz
        self.save_edit_button["state"] = "normal"                  # włącz przycisk zapisu

    def save_edited_transaction(self):
        """Zapisuje edytowaną transakcję (formularz -> lista -> tabela)."""
        if not hasattr(self, 'current_edit_item_id'):  # brak aktywnej edycji?
            return                                    # wyjdź
        new_date = self.date_var.get().strip()        # nowa data
        rodzaj = self.type_var.get()                  # nowy rodzaj
        kat = self.category_var.get().strip()         # nowa kategoria
        opis = self.desc_var.get().strip()            # nowy opis
        kwota_str = self.amount_var.get().strip()     # nowa kwota (tekst)
        try:
            kwota = float(kwota_str)                  # rzutuj
        except ValueError:
            return                                    # wyjdź przy błędzie

        old_values = self.tree.item(self.current_edit_item_id, "values")  # stare wartości wiersza
        old_date, old_rodzaj, old_kat, old_opis, old_kwota_str = old_values  # rozpakuj
        old_kwota = float(old_kwota_str)                                    # rzutuj

        for t in self.transactions:                                         # znajdź transakcję
            if (t["user"]==self.current_user and t["data"]==old_date and t["rodzaj"]==old_rodzaj
                and t["kategoria"]==old_kat and t["opis"]==old_opis
                and abs(t["kwota"] - old_kwota)<1e-9):
                t["data"] = new_date                                       # zaktualizuj pola
                t["rodzaj"] = rodzaj                                       # j.w.
                t["kategoria"] = kat                                        # j.w.
                t["opis"] = opis                                            # j.w.
                t["kwota"] = kwota                                          # j.w.
                break                                                       # zakończ pętlę

        self.save_transactions()                                            # zapisz CSV
        self.tree.item(self.current_edit_item_id, values=(new_date,rodzaj,kat,opis,f"{kwota:.2f}"))  # odśwież wiersz
        self.save_edit_button["state"] = "disabled"                         # wyłącz zapis
        del self.current_edit_item_id                                       # usuń znacznik edycji

        self.category_var.set("")                                           # wyczyść pola
        self.desc_var.set("")
        self.amount_var.set("")
        self.update_analysis_charts()                                       # odśwież wykresy

    # --- ZAKŁADKA: ANALIZY ---
    def create_analysis_tab(self):
        """Buduje UI zakładki 'Analizy' (3 wykresy)."""
        self.tab_analysis.rowconfigure(1, weight=1)               # rozciąganie w pionie
        self.tab_analysis.columnconfigure(0, weight=1)            # rozciąganie w poziomie

        self.fig_line = plt.Figure(figsize=(6,3), dpi=100)        # figura wykresu liniowego
        self.ax_line = self.fig_line.add_subplot(111)             # osie do linii
        self.canvas_line = FigureCanvasTkAgg(self.fig_line, master=self.tab_analysis)  # płótno Tk
        self.canvas_line.get_tk_widget().grid(row=0, column=0, sticky="nsew")         # umieść

        bottom_frame = ttk.Frame(self.tab_analysis)               # dolna ramka (kołowy+słupkowy)
        bottom_frame.grid(row=1, column=0, sticky="nsew")         # pozycja
        bottom_frame.columnconfigure(0, weight=1)                 # rozciąganie kolumn
        bottom_frame.columnconfigure(1, weight=1)                 # j.w.
        bottom_frame.rowconfigure(0, weight=1)                    # rozciąganie wiersza

        self.fig_pie = plt.Figure(figsize=(3,3), dpi=100)         # figura kołowa
        self.ax_pie = self.fig_pie.add_subplot(111)               # osie
        self.canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=bottom_frame)  # płótno
        self.canvas_pie.get_tk_widget().grid(row=0, column=0, sticky="nsew")   # umieść

        self.fig_bar = plt.Figure(figsize=(3,3), dpi=100)         # figura słupkowa
        self.ax_bar = self.fig_bar.add_subplot(111)               # osie
        self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=bottom_frame) # płótno
        self.canvas_bar.get_tk_widget().grid(row=0, column=1, sticky="nsew")   # umieść

    def update_analysis_charts(self):
        """Aktualizuje wszystkie 3 wykresy na podstawie danych usera."""
        user_trans = [t for t in self.transactions if t["user"]==self.current_user]  # filtr user

        total_income = sum(t["kwota"] for t in user_trans if t["rodzaj"]=="Przychód")  # suma przychodów
        total_expense = sum(t["kwota"] for t in user_trans if t["rodzaj"]=="Wydatek")  # suma wydatków

        self.ax_pie.clear()                                                       # wyczyść kołowy
        if total_income==0 and total_expense==0:                                  # brak danych?
            self.ax_pie.text(0.5, 0.5, "Brak danych", ha="center", va="center")   # tekst
        else:
            values = [total_income, total_expense]                                # wartości
            labels = ["Przychody","Wydatki"]                                      # etykiety
            colors = ["green","red"]                                              # kolory
            self.ax_pie.pie(values, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90)  # wykres
        self.ax_pie.set_title("Przychody vs Wydatki")                             # tytuł
        self.ax_pie.axis("equal")                                                 # koło jako okrąg
        self.canvas_pie.draw()                                                    # narysuj

        self.ax_bar.clear()                                                       # wyczyść słupkowy
        expenses_by_cat = {}                                                      # słownik sum per kategoria
        for t in user_trans:                                                      # iteruj transakcje
            if t["rodzaj"]=="Wydatek":                                           # tylko wydatki
                cat = t["kategoria"]                                             # kategoria
                expenses_by_cat[cat] = expenses_by_cat.get(cat,0)+t["kwota"]     # sumuj
        if not expenses_by_cat:                                                  # brak?
            self.ax_bar.text(0.5,0.5,"Brak wydatków", ha="center", va="center")  # komunikat
        else:
            cats = list(expenses_by_cat.keys())                                  # nazwy kategorii
            sums = list(expenses_by_cat.values())                                # sumy
            self.ax_bar.bar(cats, sums, color="orange")                          # słupki
            self.ax_bar.set_xticklabels(cats, rotation=45, ha="right")           # etykiety pod kątem
            self.ax_bar.set_title("Wydatki wg kategorii")                         # tytuł
        self.fig_bar.tight_layout()                                               # dopasuj
        self.canvas_bar.draw()                                                    # rysuj

        self.ax_line.clear()                                                      # wyczyść liniowy
        monthly_data = {}                                                         # słownik saldo miesięczne
        for t in user_trans:                                                      # iteruj transakcje
            month_key = t["data"][:7]                                            # YYYY-MM
            monthly_data.setdefault(month_key, 0)                                 # init 0
            if t["rodzaj"]=="Przychód":                                          # jeśli przychód
                monthly_data[month_key]+=t["kwota"]                               # dodaj
            else:
                monthly_data[month_key]-=t["kwota"]                               # odejmij
        if not monthly_data:                                                      # brak?
            self.ax_line.text(0.5,0.5,"Brak danych", ha="center", va="center")    # komunikat
        else:
            sorted_months = sorted(monthly_data.keys())                           # posortuj miesiące
            x_vals = range(len(sorted_months))                                    # oś X
            y_vals = [monthly_data[m] for m in sorted_months]                     # salda
            self.ax_line.plot(x_vals,y_vals,marker='o')                           # wykres linii
            self.ax_line.set_xticks(x_vals)                                       # ticki
            self.ax_line.set_xticklabels(sorted_months, rotation=45, ha="right")  # etykiety X
            self.ax_line.set_title("Saldo miesięczne (Przychody - Wydatki)")      # tytuł
            self.ax_line.set_xlabel("Miesiąc")                                    # podpis X
            self.ax_line.set_ylabel("Saldo")                                      # podpis Y
        self.fig_line.tight_layout()                                              # dopasuj
        self.canvas_line.draw()                                                   # rysuj

    # --- ZAKŁADKA: BUDŻET ---
    def create_budget_tab(self):
        """Buduje UI zakładki 'Planowanie Budżetu'."""
        top_frame = ttk.Frame(self.tab_budget)                       # górna ramka
        top_frame.pack(side="top", fill="x", padx=5, pady=5)         # umieść

        ttk.Label(top_frame, text="Kategoria:").pack(side="left", padx=5)  # etykieta
        self.budget_cat_var = tk.StringVar()                                # zmienna kat
        ttk.Entry(top_frame, textvariable=self.budget_cat_var, width=20).pack(side="left", padx=5)  # pole

        ttk.Label(top_frame, text="Limit (zł):").pack(side="left", padx=5)  # etykieta
        self.budget_limit_var = tk.StringVar()                               # zmienna limit
        ttk.Entry(top_frame, textvariable=self.budget_limit_var, width=10).pack(side="left", padx=5)  # pole

        ttk.Button(top_frame, text="Ustaw / Zmień limit", command=self.set_budget).pack(side="left", padx=5)  # przycisk

        self.budget_text = tk.Text(self.tab_budget, wrap="none")     # pole tekstowe
        self.budget_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)  # umieść

        scroll_y = ttk.Scrollbar(self.tab_budget, orient="vertical", command=self.budget_text.yview)  # scroll pionowy
        self.budget_text.configure(yscrollcommand=scroll_y.set)      # powiąż scroll
        scroll_y.pack(side="right", fill="y")                        # umieść scroll

        self.update_budget_text()                                    # wyświetl budżety

    def set_budget(self):
        """Ustawia/zmienia limit budżetu dla kategorii."""
        cat = self.budget_cat_var.get().strip()                 # kategoria
        limit_str = self.budget_limit_var.get().strip()         # limit (tekst)
        if not cat or not limit_str:                            # walidacja
            return                                              # wyjdź
        try:
            limit_val = float(limit_str)                        # rzutuj
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawna wartość limitu.")  # ostrzeżenie
            return
        self.budgets[cat] = limit_val                           # ustaw w dict
        self.save_budgets()                                     # zapisz CSV
        self.budget_cat_var.set("")                             # wyczyść pola
        self.budget_limit_var.set("")
        self.update_budget_text()                               # odśwież widok

    def update_budget_text(self):
        """Wyświetla podsumowanie budżetów i wydatków w Text."""
        self.budget_text.config(state="normal")                                              # włącz edycję
        self.budget_text.delete("1.0", tk.END)                                               # wyczyść

        self.budget_text.insert(tk.END, f"{'Kategoria':15s} | {'Limit':>10s} | {'Wydano':>10s} | {'Różnica':>10s}\n")  # nagłówek
        self.budget_text.insert(tk.END, "-"*60 + "\n")                                       # linia

        user_trans = [t for t in self.transactions if t["user"]==self.current_user and t["rodzaj"]=="Wydatek"]  # wydatki usera
        expenses_by_cat = {}                                                                 # sumy per kategoria
        for t in user_trans:                                                                 # iteruj wydatki
            cat = t["kategoria"]                                                             # kategoria
            expenses_by_cat[cat] = expenses_by_cat.get(cat,0)+t["kwota"]                    # sumuj

        all_cats = set(self.budgets.keys())|set(expenses_by_cat.keys())                     # unia kategorii

        for cat in sorted(all_cats):                                                         # iteruj kategorie
            limit_val = self.budgets.get(cat, 0.0)                                          # limit
            spent = expenses_by_cat.get(cat, 0.0)                                           # wydano
            diff = limit_val - spent                                                        # różnica
            line = f"{cat:15s} | {limit_val:10.2f} | {spent:10.2f} | {diff:10.2f}"          # zbuduj linię
            if diff<0:                                                                       # przekroczono?
                line+="  (Przekroczono!)"                                                   # dopisz ostrzeżenie
            line+="\n"                                                                       # nowa linia
            self.budget_text.insert(tk.END, line)                                           # wstaw linię

        self.budget_text.config(state="disabled")                                           # zablokuj edycję

    # --- ZAKŁADKA: KALENDARZ ---
    def create_calendar_tab(self):
        """Buduje UI zakładki 'Kalendarz'."""
        self.tab_calendar.rowconfigure(0, weight=1)                   # rozciąganie w pionie
        self.tab_calendar.columnconfigure(1, weight=1)                # kolumna tekstu rozciągana

        self.calendar = Calendar(self.tab_calendar, selectmode="day", date_pattern="yyyy-mm-dd")  # kalendarz
        self.calendar.grid(row=0, column=0, sticky="ns", padx=5, pady=5)                          # pozycja

        self.calendar.bind("<<CalendarSelected>>", self.on_calendar_day_selected)  # obsługa kliknięcia dnia

        self.calendar_text = tk.Text(self.tab_calendar, wrap="none")           # pole tekstowe
        self.calendar_text.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)  # umieść

        scroll_y = ttk.Scrollbar(self.tab_calendar, orient="vertical", command=self.calendar_text.yview)  # scroll
        self.calendar_text.configure(yscrollcommand=scroll_y.set)                  # powiąż scroll
        scroll_y.grid(row=0, column=2, sticky="ns")                                # umieść

        self.show_calendar_day_transactions(datetime.today().strftime("%Y-%m-%d")) # pokaż dzisiejsze

    def on_calendar_day_selected(self, event):
        """Obsługuje wybór dnia w kalendarzu."""
        date_str = self.calendar.get_date()                # pobierz datę
        self.show_calendar_day_transactions(date_str)      # pokaż transakcje z dnia

    def show_calendar_day_transactions(self, date_str):
        """Wstawia do pola tekstowego transakcje z wybranego dnia."""
        user_trans = [t for t in self.transactions if t["user"]==self.current_user and t["data"]==date_str]  # filtr
        self.calendar_text.config(state="normal")           # włącz edycję
        self.calendar_text.delete("1.0", tk.END)            # czyść
        self.calendar_text.insert(tk.END, f"Transakcje z dnia {date_str}:\n")  # nagłówek
        self.calendar_text.insert(tk.END, "-"*40+"\n")      # linia
        if not user_trans:                                  # brak transakcji?
            self.calendar_text.insert(tk.END, "Brak transakcji.\n")            # info
        else:
            for t in user_trans:                            # iteruj transakcje
                line = f"{t['rodzaj']} | {t['kategoria']} | {t['opis']} | {t['kwota']:.2f} zł\n"  # linia
                self.calendar_text.insert(tk.END, line)     # wstaw
        self.calendar_text.config(state="disabled")         # zablokuj

    # --- ZAKŁADKA: CYKLICZNE ---
    def create_recurring_tab(self):
        """Buduje UI zakładki 'Cykliczne'."""
        self.tab_recurring.rowconfigure(1, weight=1)               # rozciąganie w pionie
        self.tab_recurring.columnconfigure(0, weight=1)            # rozciąganie w poziomie

        form_frame = ttk.LabelFrame(self.tab_recurring, text="Dodaj / Edytuj transakcję cykliczną")  # ramka formularza
        form_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)                                # pozycja

        ttk.Label(form_frame, text="Data startu:").grid(row=0, column=0, padx=5, sticky="e")         # etykieta data
        self.rec_next_date_var = tk.StringVar()                                                       # zmienna data
        self.rec_next_date_entry = DateEntry(form_frame, textvariable=self.rec_next_date_var, date_pattern="yyyy-mm-dd")  # wybór daty
        self.rec_next_date_entry.grid(row=0, column=1, padx=5)                                        # pozycja

        ttk.Label(form_frame, text="Odstęp dni:").grid(row=0, column=2, padx=5, sticky="e")          # etykieta odstęp
        self.rec_interval_var = tk.StringVar(value="30")                                              # domyślne 30 dni
        ttk.Entry(form_frame, textvariable=self.rec_interval_var, width=5).grid(row=0, column=3, padx=5)  # pole odstępu

        ttk.Label(form_frame, text="Rodzaj:").grid(row=0, column=4, padx=5, sticky="e")              # etykieta rodzaj
        self.rec_type_var = tk.StringVar(value="Wydatek")                                            # domyślnie wydatek
        self.rec_type_menu = ttk.OptionMenu(form_frame, self.rec_type_var, "Wydatek", "Wydatek", "Przychód")  # menu
        self.rec_type_menu.grid(row=0, column=5, padx=5)                                             # pozycja

        ttk.Label(form_frame, text="Kategoria:").grid(row=1, column=0, padx=5, sticky="e")           # etykieta kategoria
        self.rec_cat_var = tk.StringVar()                                                             # zmienna kategoria
        ttk.Entry(form_frame, textvariable=self.rec_cat_var).grid(row=1, column=1, padx=5)            # pole

        ttk.Label(form_frame, text="Kwota:").grid(row=1, column=2, padx=5, sticky="e")                # etykieta kwota
        self.rec_amount_var = tk.StringVar()                                                          # zmienna kwota
        ttk.Entry(form_frame, textvariable=self.rec_amount_var, width=10).grid(row=1, column=3, padx=5)  # pole

        ttk.Label(form_frame, text="Opis:").grid(row=1, column=4, padx=5, sticky="e")                 # etykieta opis
        self.rec_desc_var = tk.StringVar()                                                            # zmienna opis
        ttk.Entry(form_frame, textvariable=self.rec_desc_var, width=30).grid(row=1, column=5, padx=5, sticky="w")  # pole

        self.rec_add_button = ttk.Button(form_frame, text="Dodaj", command=self.add_recurring)        # przycisk dodaj
        self.rec_add_button.grid(row=0, column=6, rowspan=2, padx=5, pady=5, sticky="ns")             # pozycja

        self.rec_edit_button = ttk.Button(form_frame, text="Edytuj zazn.", command=self.edit_recurring)  # przycisk edytuj
        self.rec_edit_button.grid(row=0, column=7, rowspan=2, padx=5, pady=5, sticky="ns")               # pozycja

        self.rec_save_button = ttk.Button(form_frame, text="Zapisz zmiany", command=self.save_edited_recurring)  # przycisk zapisz
        self.rec_save_button.grid(row=0, column=8, rowspan=2, padx=5, pady=5, sticky="ns")                       # pozycja
        self.rec_save_button["state"] = "disabled"                                                                # nieaktywny

        table_frame = ttk.Frame(self.tab_recurring)                    # ramka tabeli
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)  # pozycja
        table_frame.rowconfigure(0, weight=1)                           # rozciągaj pion
        table_frame.columnconfigure(0, weight=1)                        # rozciągaj poziom

        rec_columns = ("next_date", "interval", "rodzaj", "kategoria", "kwota", "opis", "id")  # kolumny
        self.rec_tree = ttk.Treeview(table_frame, columns=rec_columns, show="headings")        # tabela
        self.rec_tree.heading("next_date", text="Nast. Data")                                  # nagłówek
        self.rec_tree.heading("interval", text="Odstęp(dni)")                                  # j.w.
        self.rec_tree.heading("rodzaj", text="Rodzaj")                                         # j.w.
        self.rec_tree.heading("kategoria", text="Kategoria")                                   # j.w.
        self.rec_tree.heading("kwota", text="Kwota")                                           # j.w.
        self.rec_tree.heading("opis", text="Opis")                                             # j.w.
        self.rec_tree.heading("id", text="ID")                                                 # j.w.

        self.rec_tree.column("next_date", width=100, anchor="center")                          # kolumny parametry
        self.rec_tree.column("interval", width=80, anchor="center")                            # j.w.
        self.rec_tree.column("rodzaj", width=80, anchor="center")                              # j.w.
        self.rec_tree.column("kategoria", width=120, anchor="w")                               # j.w.
        self.rec_tree.column("kwota", width=80, anchor="e")                                    # j.w.
        self.rec_tree.column("opis", width=200, anchor="w")                                    # j.w.
        self.rec_tree.column("id", width=100, anchor="center")                                 # j.w.

        scroll_rec = ttk.Scrollbar(table_frame, orient="vertical", command=self.rec_tree.yview)  # scroll
        self.rec_tree.configure(yscrollcommand=scroll_rec.set)                                    # powiąż scroll

        self.rec_tree.grid(row=0, column=0, sticky="nsew")             # umieść tabelę
        scroll_rec.grid(row=0, column=1, sticky="ns")                  # umieść scroll

        self.rec_delete_button = ttk.Button(table_frame, text="Usuń zaznaczoną cykliczną", command=self.remove_recurring)  # przycisk usuń
        self.rec_delete_button.grid(row=1, column=0, pady=5, sticky="we")                                                   # pozycja

        self.update_recurring_table()                                   # wstaw dane do tabeli

    def update_recurring_table(self):
        """Odświeża tabelę cyklicznych (tylko bieżącego usera)."""
        for row_id in self.rec_tree.get_children():                 # usuń stare wiersze
            self.rec_tree.delete(row_id)                            # kasuj
        for rec_id, rec_data in self.recurring.items():             # iteruj cykliczne
            if rec_data["user"] == self.current_user:               # filtr user
                self.rec_tree.insert("", "end", values=(            # wstaw wiersz
                    rec_data["next_date"],
                    rec_data["interval_days"],
                    rec_data["rodzaj"],
                    rec_data["kategoria"],
                    f"{rec_data['kwota']:.2f}",
                    rec_data.get("opis",""),
                    rec_id
                ))

    def add_recurring(self):
        """Dodaje transakcję cykliczną na podstawie formularza."""
        next_date_str = self.rec_next_date_var.get().strip()    # data
        interval_str = self.rec_interval_var.get().strip()      # odstęp
        rodzaj = self.rec_type_var.get()                        # rodzaj
        kat = self.rec_cat_var.get().strip()                    # kategoria
        kwota_str = self.rec_amount_var.get().strip()           # kwota (tekst)
        opis = self.rec_desc_var.get().strip()                  # opis

        if not next_date_str or not interval_str or not kwota_str:   # walidacja wymaganych
            messagebox.showwarning("Błąd", "Wypełnij wymagane pola (data, odstęp, kwota).")  # ostrzeżenie
            return
        try:
            interval_days = int(interval_str)                  # rzutuj odstęp
            kwota = float(kwota_str)                           # rzutuj kwotę
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawne wartości (odstęp, kwota).")  # ostrzeżenie
            return

        rec_id = uuid.uuid4().hex                              # unikalne ID
        new_data = {                                           # dane cyklicznej
            "user": self.current_user,
            "next_date": next_date_str,
            "interval_days": interval_days,
            "rodzaj": rodzaj,
            "kategoria": kat if kat else "Brak",
            "kwota": kwota,
            "opis": opis
        }
        self.recurring[rec_id] = new_data                      # zapisz w dict
        self.save_recurring()                                  # zapisz plik
        self.update_recurring_table()                          # odśwież tabelę

        self.rec_next_date_var.set("")                         # wyczyść pola
        self.rec_interval_var.set("30")
        self.rec_cat_var.set("")
        self.rec_amount_var.set("")
        self.rec_desc_var.set("")

    def remove_recurring(self):
        """Usuwa zaznaczoną transakcję cykliczną."""
        selection = self.rec_tree.selection()        # zaznaczenie
        if not selection:                            # jeśli brak
            return                                   # wyjdź
        item_id = selection[0]                       # id wiersza
        values = self.rec_tree.item(item_id, "values")  # wartości wiersza
        rec_id = values[-1]                          # ostatnia kolumna to ID
        self.rec_tree.delete(item_id)                # usuń z tabeli

        if rec_id in self.recurring:                 # jeśli istnieje w dict
            del self.recurring[rec_id]               # usuń
            self.save_recurring()                    # zapisz plik

    def edit_recurring(self):
        """Ładuje zaznaczoną cykliczną do formularza do edycji."""
        selection = self.rec_tree.selection()                # zaznaczenie
        if not selection:                                    # jeśli brak
            return                                           # wyjdź
        item_id = selection[0]                               # id wiersza
        values = self.rec_tree.item(item_id, "values")       # wartości (krotka)
        next_date, interval_str, rodzaj, kat, kwota_str, opis, rec_id = values  # rozpakuj

        self.rec_next_date_var.set(next_date)                # ustaw datę
        self.rec_interval_var.set(interval_str)              # ustaw odstęp
        self.rec_type_var.set(rodzaj)                        # ustaw rodzaj
        self.rec_cat_var.set(kat)                            # ustaw kategorię
        self.rec_amount_var.set(kwota_str)                   # ustaw kwotę
        self.rec_desc_var.set(opis)                          # ustaw opis

        self.current_edit_rec_id = rec_id                    # zapamiętaj ID edytowane
        self.rec_save_button["state"] = "normal"             # włącz zapis

    def save_edited_recurring(self):
        """Zapisuje zmiany w edytowanej cyklicznej transakcji."""
        if not hasattr(self, 'current_edit_rec_id'):         # brak aktywnej edycji?
            return                                           # wyjdź
        rec_id = self.current_edit_rec_id                    # ID edytowane

        new_date = self.rec_next_date_var.get().strip()      # nowa data
        new_interval_str = self.rec_interval_var.get().strip()  # nowy odstęp (tekst)
        new_rodzaj = self.rec_type_var.get()                 # nowy rodzaj
        new_kat = self.rec_cat_var.get().strip()             # nowa kategoria
        new_kwota_str = self.rec_amount_var.get().strip()    # nowa kwota (tekst)
        new_opis = self.rec_desc_var.get().strip()           # nowy opis

        try:
            new_interval = int(new_interval_str)             # rzutuj odstęp
            new_kwota = float(new_kwota_str)                 # rzutuj kwotę
        except ValueError:
            messagebox.showwarning("Błąd", "Niepoprawne wartości.")  # ostrzeżenie
            return

        if rec_id in self.recurring:                         # jeśli ID istnieje
            self.recurring[rec_id]["next_date"] = new_date   # zapisz nową datę
            self.recurring[rec_id]["interval_days"] = new_interval  # nowy odstęp
            self.recurring[rec_id]["rodzaj"] = new_rodzaj    # nowy rodzaj
            self.recurring[rec_id]["kategoria"] = new_kat if new_kat else "Brak"  # nowa kat
            self.recurring[rec_id]["kwota"] = new_kwota      # nowa kwota
            self.recurring[rec_id]["opis"] = new_opis        # nowy opis

        self.save_recurring()                                 # zapisz plik
        self.update_recurring_table()                         # odśwież tabelę

        self.rec_save_button["state"] = "disabled"            # wyłącz przycisk
        del self.current_edit_rec_id                          # usuń znacznik

        self.rec_next_date_var.set("")                        # wyczyść formularz
        self.rec_interval_var.set("30")
        self.rec_cat_var.set("")
        self.rec_amount_var.set("")
        self.rec_desc_var.set("")

    # --- ZAKŁADKA: USTAWIENIA ---
    def create_settings_tab(self):
        """Buduje UI zakładki 'Ustawienia' (motywy ttk)."""
        settings_frame = ttk.LabelFrame(self.tab_settings, text="Motywy (Themes)")  # ramka
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)             # umieść

        self.available_themes = [                     # lista motywów (nie wszystkie dostępne)
            "clam", "alt", "default", "classic",
            "vista", "xpnative", "winnative",
            "plastik", "breeze", "radiance"
        ]

        ttk.Label(settings_frame, text="Wybierz motyw:").pack(pady=5)               # etykieta

        self.theme_var = tk.StringVar(value=self.style.theme_use())                 # aktualny motyw
        self.theme_combo = ttk.Combobox(settings_frame, textvariable=self.theme_var,
                                        values=self.available_themes, state="readonly")  # combo motywów
        self.theme_combo.pack(pady=5)                                               # umieść

        ttk.Button(settings_frame, text="Zastosuj", command=self.apply_theme).pack(pady=5)  # przycisk zastosuj

    def apply_theme(self):
        """Ustawia wybrany motyw ttk, jeśli dostępny."""
        chosen_theme = self.theme_var.get()         # pobierz z comboboxa
        try:
            self.style.theme_use(chosen_theme)      # ustaw motyw
        except tk.TclError:
            messagebox.showwarning("Błąd motywu", f"Motyw '{chosen_theme}' nie jest dostępny w tym systemie.")  # ostrzeżenie

# --- WEJŚCIE PROGRAMU: NAJPIERW LOGOWANIE, POTEM APLIKACJA ---
if __name__ == "__main__":                              # uruchomiono bezpośrednio?
    users = load_users()                                # wczytaj użytkowników
    current = run_login_dialog(users)                   # pokaż logowanie i pobierz usera
    if not current:                                     # jeśli anulowano
        raise SystemExit(0)                             # zakończ program

    app = BudgetApp()                                   # utwórz aplikację
    app.current_user = current                          # ustaw zalogowanego
    app.init_main_app()                                 # zbuduj UI i wczytaj dane
    app.mainloop()                                      # uruchom pętlę główną GUI
