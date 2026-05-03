import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime
import plotly.express as px
import imaplib
import email

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")
# --- Σύστημα Password ---
def check_password():
    """Επιστρέφει True αν ο χρήστης έδωσε σωστό κωδικό."""
    def password_entered():
        # panatha1908
        if st.session_state["password"] == "panatha1908":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Διαγραφή κωδικού από το state για ασφάλεια
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Πρώτη φορά που ανοίγει η εφαρμογή
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Λάθος κωδικός
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        st.error("❌ Λάθος κωδικός. Προσπαθήστε ξανά.")
        return False
    else:
        # Σωστός κωδικός
        return True

if not check_password():
    st.stop()  # Σταματάει την εκτέλεση της εφαρμογής εδώ αν δεν είναι σωστός ο κωδικός

# Προσθήκη CSS
st.markdown("""
    <style>
    /* Φόντο όλης της εφαρμογής */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Στυλ για τα Metrics (Κέρδος, Κόστος κλπ) */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00ffcc; /* Ένα neon κυανό χρώμα για τις τιμές */
    }
    
    /* Στυλ για τα κουτιά των metrics */
    div[data-testid="stMetric"] {
        background-color: #1e2129;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }

    /* Κουμπιά με πιο έντονο στυλ */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #3e4451;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        border: 1px solid #00ffcc;
        color: #00ffcc;
    }
    </style>
    """, unsafe_allow_html=True)

# Αρχεία Βάσης
DB_INGREDIENTS = "db_ingredients.csv"
DB_RECIPES = "db_recipes.csv"
DB_ORDERS = "db_orders.csv"
DB_HISTORY = "db_history.csv"

TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

def format_greek(value):
    if isinstance(value, (int, float)):
        return "{:.3f}".format(value).replace('.', ',')
    return value

def load_data():
    if os.path.exists(DB_INGREDIENTS):
        ing = pd.read_csv(DB_INGREDIENTS)
    else:
        ing = pd.DataFrame(columns=["Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Απόθεμα (ml)"])
    
    for col in ["Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Απόθεμα (ml)"]:
        if col not in ing.columns:
            ing[col] = 0.0 if col != "Name" else "Νέο Υλικό"
            
    if os.path.exists(DB_RECIPES):
        rec = pd.read_csv(DB_RECIPES)
    else:
        cols_rec = ["Ονομα", "Τιμή Καταλόγου"] + [f"ΣΥΣΤΑΤΙΚΟ{i}" for i in range(1,14)] + [f"ML{i}" for i in range(1,14)]
        rec = pd.DataFrame(columns=cols_rec)
        
    if os.path.exists(DB_ORDERS):
        orders = pd.read_csv(DB_ORDERS, dtype={"Πελάτης": str, "Cocktail": str})
    else:
        orders = pd.DataFrame(columns=["Πελάτης", "Cocktail", "Τεμάχια"])
    orders["Πελάτης"] = orders["Πελάτης"].astype(str).replace("nan", "")

    if os.path.exists(DB_HISTORY):
        history = pd.read_csv(DB_HISTORY)
    else:
        history = pd.DataFrame(columns=["Ημερομηνία", "Πελάτης", "Cocktail", "Τεμάχια"])
        
    return ing, rec, orders, history

df_ing, df_rec, df_orders, df_history = load_data()
ing_options = ["ΚΕΝΟ", "Νερό"] + sorted(df_ing["Name"].unique().tolist()) if not df_ing.empty else ["ΚΕΝΟ", "Νερό"]
recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

# --- Sidebar ---
st.sidebar.image("https://cabclub.gr/wp-content/uploads/2021/12/logo.png", use_container_width=True)
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "🔄 Αντικατάσταση","📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "🛒 Παραγγελίες", "🌐 Shop Sync", "📦 Lot Παραγωγής", "📈 Dashboard"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ (ΜΕ ΑΥΤΟΜΑΤΟ ID & ΒΑΡΟΣ) ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών & Τιμών")
    
    # 1. Έλεγχος και δημιουργία στήλης ID αν δεν υπάρχει
    if "ID" not in df_ing.columns:
        # Αν η βάση είναι παλιά, δίνουμε IDs ξεκινώντας από το 1001
        df_ing.insert(0, "ID", range(1001, 1001 + len(df_ing)))
    
    if "Weight_Full" not in df_ing.columns:
        df_ing["Weight_Full"] = 0.0

    # Στήλες που θα εμφανίζονται (το ID είναι disabled για να μην αλλάζει κατά λάθος)
    cols_to_show = ["ID", "Name", "Price", "Volume", "Weight_Full", "Τιμή/ml", "Αλκοόλ %"]
    
    column_config_ing = {
        "ID": st.column_config.NumberColumn("ID", disabled=True, format="%d"),
        "Name": st.column_config.TextColumn("Όνομα Υλικού"),
        "Price": st.column_config.NumberColumn("Τιμή Αγοράς (€)", format="%.2f €"),
        "Volume": st.column_config.NumberColumn("ML Φιάλης (ml)", min_value=1),
        "Weight_Full": st.column_config.NumberColumn("Βάρος Περιεχομένου (g)", help="Πόσο ζυγίζουν τα ML της φιάλης στη ζυγαριά", format="%d g"),
        "Τιμή/ml": st.column_config.NumberColumn("Τιμή/ml", disabled=True, format="%.4f €"),
        "Αλκοόλ %": st.column_config.NumberColumn("Alc %", format="%.1f %%")
    }
    
    # Επεξεργασία υλικών
    edited_ing = st.data_editor(
        df_ing[cols_to_show], 
        column_config=column_config_ing, 
        num_rows="dynamic", 
        use_container_width=True,
        key="ing_editor"
    )
    
    if st.button("💾 Αποθήκευση Υλικών"):
        # Δημιουργούμε ένα αντίγραφο των αλλαγών
        temp_df = edited_ing.copy()
        
        # 2. ΑΥΤΟΜΑΤΗ ΠΑΡΑΓΩΓΗ ID ΓΙΑ ΝΕΕΣ ΓΡΑΜΜΕΣ
        if temp_df["ID"].isnull().any():
            max_id = df_ing["ID"].max() if not df_ing.empty else 1000
            null_mask = temp_df["ID"].isnull()
            new_ids = range(int(max_id) + 1, int(max_id) + 1 + null_mask.sum())
            temp_df.loc[null_mask, "ID"] = list(new_ids)
        
        # Υπολογισμός τιμής ανά ml
        temp_df["Τιμή/ml"] = temp_df["Price"] / temp_df["Volume"].replace(0, 1)
        
        # Διατήρηση υπολοίπων στηλών
        if "Απόθεμα (ml)" in df_ing.columns:
            final_df = temp_df.merge(df_ing[["ID", "Απόθεμα (ml)"]], on="ID", how="left")
            final_df["Απόθεμα (ml)"] = final_df["Απόθεμα (ml)"].fillna(0.0)
        else:
            final_df = temp_df
            
        final_df.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')
        st.success(f"✅ Η αποθήκη ενημερώθηκε! (Τελευταίο ID: {int(final_df['ID'].max())})")
        st.rerun()
