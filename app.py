import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime, timedelta
import pytz  # 🌟 ΝΕΟ: Εισαγωγή βιβλιοθήκης για ζώνες ώρας
import plotly.express as px
import imaplib
import email
import time
from supabase import create_client, Client
import zipfile
import io
from fpdf import FPDF

# --- 📌 ΟΔΗΓΙΕΣ ΧΡΗΣΗΣ (ΣΤΗΝ ΑΡΙΣΤΕΡΗ ΠΛΕΥΡΑ) ---
st.sidebar.markdown("---")
with st.sidebar.expander("📖 Οδηγίες Χρήσης (SOS)"):
    st.markdown("""
    ### 🗑️ Διαχείριση Παραγγελιών
    * **Διαγραφή Ολόκληρης Παραγγελίας:** Πηγαίνετε στο **Πελατολόγιο** -> Καρτέλα "Καρτέλα & Ιστορικό". Επιλέξτε τον πελάτη και πατήστε το κουμπί **"Διαγραφή Παραγγελίας"** στο ιστορικό του. 
    * **Διαγραφή Ενός Κοκτέιλ:** Πηγαίνετε στην καρτέλα **"Παραγωγή & LOT"**. Επιλέξτε την εγγραφή και πατήστε το κουμπί διαγραφής εκεί.
    
    ### ⚠️ Κανόνες Ασφαλείας
    * **Αλλαγή Ημερομηνίας:** Αν αλλάξετε ημερομηνία σε μια εγγραφή παραγωγής, **μην διαγράψετε** την παραγγελία από το Πελατολόγιο αργότερα (μπορεί να μην βρει τα υλικά για να τα σβήσει). 
    * **Συμβουλή:** Αν κάνετε λάθος στην ημερομηνία μιας παραγγελίας, προτιμήστε να **διαγράψετε την παραγγελία από το Πελατολόγιο και να την ξαναπεράσετε σωστά**, παρά να την τροποποιείτε χειροκίνητα.
    * **Μορφή Ημερομηνιών:** Σε όλα τα LOT και τις ημερομηνίες, χρησιμοποιείτε πάντα τη μορφή **ΗΗ/ΜΜ/ΕΕΕΕ** (π.χ. 20/05/2026).
    
    ### 📉 Κίνδυνοι Αλλαγών (Ιστορικότητα)
    * **Αλλαγή Τιμής Συνταγής:** Αν αλλάξετε την τιμή καταλόγου μιας συνταγής, οι **παλιές παραγγελίες** του Πελατολογίου μπορεί να επαναϋπολογιστούν με τη νέα τιμή αν πατήσετε "Επεξεργασία/Εφαρμογή". 
    * **Αλλαγή Συνταγής (Υλικά):** Αν αλλάξετε τα ml μιας συνταγής, η αποθήκη για τις **νέες παραγωγές** θα αφαιρεί τη νέα ποσότητα. Οι παλιές παραγωγές παραμένουν όπως είχαν καταγραφεί τη στιγμή της παραγωγής.
    * **Αλλαγή Πρώτης Ύλης:** Αν μετονομάσετε μια πρώτη ύλη, το σύστημα θα τη θεωρήσει "νέα". Τα παλιά LOT θα διατηρήσουν το παλιό όνομα.

    <div style="background-color: #ffe6e6; padding: 12px; border-radius: 8px; border-left: 6px solid #ff0000; margin-top: 20px;">
        <span style="color: #cc0000; font-weight: 900; font-size: 15px; line-height: 1.4; display: block;">
        🚨 ΧΡΥΣΟΣ ΚΑΝΟΝΑΣ:<br><br>
        ΑΝ ΧΡΕΙΑΣΤΕΙ ΠΟΤΕ ΝΑ ΚΑΝΕΤΕ ΔΙΟΡΘΩΣΗ ΣΕ ΜΙΑ ΠΑΛΙΑ, ΚΛΕΙΣΜΕΝΗ ΠΑΡΑΓΓΕΛΙΑ, Η ΣΩΣΤΗ ΠΡΑΚΤΙΚΗ ΕΙΝΑΙ ΝΑ ΤΗ ΔΙΑΓΡΑΨΕΤΕ ΟΛΟΚΛΗΡΗ ΚΑΙ ΝΑ ΤΗΝ ΠΕΡΑΣΕΤΕ ΞΑΝΑ ΑΠΟ ΤΗΝ ΑΡΧΗ, ΠΑΡΑ ΝΑ ΠΑΤΗΣΕΤΕ ΕΠΕΞΕΡΓΑΣΙΑ-ΕΠΑΝΥΠΟΛΟΓΙΣΜΟ!
        </span>
    </div>
    """, unsafe_allow_html=True) # Το unsafe_allow_html=True είναι απαραίτητο για να παίξουν τα χρώματα!


    

# 🌟 ΝΕΟ: Κλείδωμα Ώρας Ελλάδος (για να μην καταγράφει ώρα Αγγλίας ο server)
greece_tz = pytz.timezone('Europe/Athens')

st.set_page_config(page_title="DC Cabclub", layout="wide")

def format_gr(value, decimals=2):
    """Μετατρέπει τους αριθμούς σε ελληνική μορφή με τελεία στις χιλιάδες"""
    if pd.isna(value) or value == "":
        return "0,00" if decimals > 0 else "0"
    try:
        if decimals == 0:
            eng_format = f"{float(value):,.0f}"
        else:
            eng_format = f"{float(value):,.2f}"
        
        gr_format = eng_format.replace(",", "X").replace(".", ",").replace("X", ".")
        return gr_format
    except:
        return str(value)

def delete_order_and_production_safely(order_id, customer_name, created_at_timestamp, order_details):
    """
    Διαγράφει οριστικά μια παραγγελία από τα οικονομικά (b2b_orders)
    και καθαρίζει αυτόματα όλα τα αναλωμένα υλικά από την αποθήκη (production_log)
    Με πλήρη ασφάλεια ζώνης ώρας (Europe/Athens).
    """
    try:
        # 1. Διαγραφή από τα οικονομικά (b2b_orders)
        supabase.table("b2b_orders").delete().eq("id", order_id).execute()
        
        # 2. Ασφαλής μετατροπή timestamp σε Ώρα Ελλάδος για να μη χάσουμε την ημερομηνία
        dt = pd.to_datetime(created_at_timestamp)
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC')
        order_date = dt.tz_convert('Europe/Athens').strftime('%d/%m/%Y')
        
        # 3. Φέρνουμε όλες τις γραμμές παραγωγής αυτού του πελάτη για τη συγκεκριμένη ημέρα
        res_prod = supabase.table("production_log").select("id, cocktail_name").eq("customer", customer_name).eq("prod_date", order_date).execute()
        
        if res_prod.data:
            # Μαζεύουμε όλα τα ID που πρέπει να σβηστούν σε μια λίστα
            ids_to_delete = []
            for row in res_prod.data:
                if str(row['cocktail_name']) in str(order_details):
                    ids_to_delete.append(row['id'])
            
            # Χειρουργική και μαζική διαγραφή όλων των γραμμών μαζί (1 hit στη βάση)
            if ids_to_delete:
                supabase.table("production_log").delete().in_("id", ids_to_delete).execute()
        
        return True
    except Exception as e:
        st.error(f"Σφάλμα κατά την ασφαλή διαγραφή: {e}")
        return False

# --- 🤖 ΡΟΜΠΟΤΑΚΙ ΑΥΤΟΜΑΤΗΣ ΑΦΑΙΡΕΣΗΣ ΑΠΟΘΕΜΑΤΟΣ ---
def deduct_inventory_for_production(cocktail_name, total_pieces_made):
    """Αφαιρεί αυτόματα τα ml των υλικών από το current_stock_ml της αποθήκης"""
    try:
        # 1. Βρίσκουμε το ID της συνταγής
        res_rec = supabase.table("recipes").select("id").eq("name", cocktail_name).execute()
        if not res_rec.data: return
        rec_id = res_rec.data[0]['id']
        
        # 2. Τραβάμε τα υλικά
        res_items = supabase.table("recipe_items").select("ingredient_name, ml_per_unit").eq("recipe_id", rec_id).execute()
        
        # 3. Αφαιρούμε τα ml για κάθε υλικό
        for item in res_items.data:
            ing_name = item['ingredient_name']
            ml_used = float(item['ml_per_unit']) * total_pieces_made
            
            res_ing = supabase.table("ingredients").select("id, current_stock_ml").eq("name", ing_name).execute()
            if res_ing.data:
                ing_id = res_ing.data[0]['id']
                old_stock = float(res_ing.data[0].get('current_stock_ml') or 0.0)
                new_stock = old_stock - ml_used
                supabase.table("ingredients").update({"current_stock_ml": new_stock}).eq("id", ing_id).execute()
    except Exception as e:
        pass # Αθόρυβη λειτουργία για να μην διακοπεί ποτέ η αποθήκευση της παραγγελίας
# --------------------------------------------------
# --- ΥΒΡΙΔΙΚΗ ΣΥΝΑΡΤΗΣΗ PDF: ΣΥΓΚΕΝΤΡΩΤΙΚΑ ΠΡΟΪΟΝΤΑ & ΣΥΝΟΛΑ ---
def generate_hybrid_report(customer_name, financial_data, production_data):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf')
        f_name = 'DejaVu'
    except:
        f_name = 'Helvetica'

    # Τίτλος Report
    pdf.set_font(f_name, size=16)
    pdf.cell(0, 15, f"REPORT ΠΕΛΑΤΗ: {customer_name}", ln=1, align='C')
    pdf.ln(5)
    
    # --- ΥΠΟΛΟΓΙΣΜΟΣ ΣΥΝΟΛΙΚΟΥ ΤΖΙΡΟΥ (Χωρίς εμφάνιση πίνακα) ---
    total_euro = 0
    if financial_data:
        for order in financial_data:
            total_euro += float(order.get('total_amount', 0))

    # --- 1. ΠΙΝΑΚΑΣ ΠΑΡΑΓΩΓΗΣ (ΣΥΓΚΕΝΤΡΩΤΙΚΕΣ ΑΓΟΡΕΣ) ---
    pdf.set_font(f_name, size=12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, "Συνολικές Αγορές ανά Προϊόν (Τεμάχια)", ln=1, fill=True)
    pdf.set_font(f_name, size=10)
    
    total_pieces = 0
    if production_data:
        # Ομαδοποίηση των τεμαχίων ανά Cocktail
        cocktail_totals = {}
        for row in production_data:
            name = str(row.get('cocktail_name', 'Άγνωστο'))
            pcs = int(row.get('pieces', 0))
            cocktail_totals[name] = cocktail_totals.get(name, 0) + pcs
            total_pieces += pcs

        # Επικεφαλίδες Πίνακα
        pdf.cell(145, 10, "Προϊόν (Cocktail)", 1)
        pdf.cell(45, 10, "Συνολικά Τεμάχια", 1, 1, 'C')
        
        # Εκτύπωση των συγκεντρωτικών (από το δημοφιλέστερο στο λιγότερο)
        for cocktail, pcs in sorted(cocktail_totals.items(), key=lambda x: x[1], reverse=True):
            pdf.cell(145, 10, cocktail, 1)
            pdf.cell(45, 10, f"{pcs} τμχ", 1, 1, 'C')
    else:
        pdf.cell(0, 10, "Δεν βρέθηκε ιστορικό παραγωγής.", ln=1)

    # --- ΤΕΛΙΚΑ ΣΥΝΟΛΑ (Τζίρος & Τεμάχια) ---
    pdf.ln(10)
    pdf.set_font(f_name, size=14)
    # Εμφάνιση του συνολικού τζίρου (που περιλαμβάνει και τον θεωρητικό από το Dashboard)
    pdf.cell(0, 10, f"ΣΥΝΟΛΙΚΟΣ ΤΖΙΡΟΣ: {total_euro:.2f} EUR", ln=1, align='R')
    pdf.cell(0, 10, f"ΣΥΝΟΛΙΚΑ ΤΕΜΑΧΙΑ: {total_pieces} τμχ", ln=1, align='R')
    
    return pdf.output()

# --- ΣΥΝΔΕΣΗ ΜΕ SUPABASE ---
url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# --- ΣΥΣΤΗΜΑ LIVE STATUS ---
def update_live_status(user_name):
    with open("app_status.txt", "w", encoding="utf-8") as f:
        f.write(f"{user_name}|{time.time()}")

def get_who_is_online():
    if os.path.exists("app_status.txt"):
        with open("app_status.txt", "r", encoding="utf-8") as f:
            data = f.read().split("|")
            if len(data) == 2:
                user, last_time = data[0], float(data[1])
                if time.time() - last_time < 60:
                    return user
    return None

# --- Σύστημα Password ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "panatha1908":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        st.error("❌ Λάθος κωδικός. Προσπαθήστε ξανά.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Προσθήκη CSS (Διορθωμένο μέγεθος Metrics)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    /* Ρυθμίσεις για τα νούμερα στα κουτάκια (Metrics) */
    [data-testid="stMetricValue"] { 
        font-size: 18px !important; /* Το μικρύναμε στο 18px για να χωράνε άνετα τα εκατομμύρια! */
        color: #00ffcc; 
        white-space: nowrap !important; /* Απαγορεύει το κόψιμο στην επόμενη γραμμή */
    }
    
    div[data-testid="stMetric"] { 
        background-color: #1e2129; 
        border: 1px solid #333; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5); 
        overflow: visible !important;
    }
    
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #3e4451; color: white; border: none; }
    .stButton>button:hover { border: 1px solid #00ffcc; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# Σταθερές
TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

def format_greek(value):
    if isinstance(value, (int, float)):
        return "{:.3f}".format(value).replace('.', ',')
    return value

# --- ΣΥΝΑΡΤΗΣΕΙΣ ΦΟΡΤΩΣΗΣ ΔΕΔΟΜΕΝΩΝ (SUPABASE) ---
@st.cache_data(ttl=600) 
def load_all_ingredients():
    res = supabase.table("ingredients").select("*").order("name").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df = df.rename(columns={
            "id": "ID", "name": "Name", "price": "Price", "volume": "Volume", 
            "abv": "Αλκοόλ %", "weight_full": "Weight_Full"
        })
        df["Τιμή/ml"] = df["Price"] / df["Volume"]
        
        # 🚀 ΔΙΟΡΘΩΣΗ: Τραβάμε το πραγματικό απόθεμα από τη βάση δεδομένων
        if 'current_stock_ml' in df.columns:
            df["Απόθεμα (ml)"] = df["current_stock_ml"]
        else:
            df["Απόθεμα (ml)"] = 0.0
            
        return df
    else:
        return pd.DataFrame(columns=["ID", "Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Weight_Full", "Απόθεμα (ml)"])

@st.cache_data(ttl=600)
def load_all_recipes():
    res_rec = supabase.table("recipes").select("*").eq("is_active", True).order("name").execute()
    res_items = supabase.table("recipe_items").select("*").execute()
    
    if res_rec.data:
        df_rec = pd.DataFrame(res_rec.data)
        df_items = pd.DataFrame(res_items.data) if res_items.data else pd.DataFrame(columns=["recipe_id", "ingredient_name", "ml_per_unit"])
        
        reconstructed = []
        for _, row in df_rec.iterrows():
            rec_dict = {
                "Ονομα": row["name"],
                "Barcode": row["barcode"],
                "Τιμή Καταλόγου": row.get("catalog_price", 0.0)
            }
            items = df_items[df_items["recipe_id"] == row["id"]]
            for i, (_, item) in enumerate(items.iterrows(), start=1):
                rec_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = item["ingredient_name"]
                rec_dict[f"ML{i}"] = item["ml_per_unit"]
            reconstructed.append(rec_dict)
            
        return pd.DataFrame(reconstructed)
    else:
        cols_rec = ["Ονομα", "Barcode", "Τιμή Καταλόγου"] + [f"ΣΥΣΤΑΤΙΚΟ{i}" for i in range(1,14)] + [f"ML{i}" for i in range(1,14)]
        return pd.DataFrame(columns=cols_rec)

df_ing = load_all_ingredients()
df_rec = load_all_recipes()

ing_options = ["ΚΕΝΟ", "Νερό"] + sorted(df_ing["Name"].unique().tolist()) if not df_ing.empty else ["ΚΕΝΟ", "Νερό"]
recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

# Υπολογισμός ώρας Ελλάδος (UTC + 3)
now_athens = datetime.utcnow() + timedelta(hours=3)

# ==========================================
# --- SIDEBAR (ΑΡΙΣΤΕΡΗ ΜΠΑΡΑ) ---
# ==========================================
with st.sidebar:
    # 1. Λογότυπο και Τίτλος
    st.image("https://cabclub.gr/wp-content/uploads/2021/12/logo.png", use_container_width=True)
    st.title("DC CABCLUB 2026 🏆")
    
    st.divider()

    # --- Live Status User Selection ---
    current_user = st.selectbox("👤 Είσαι ο:", ["Χρήστης Α", "Χρήστης Β"], key="user_select")
    update_live_status(current_user)
    online_user = get_who_is_online()

    if online_user and online_user != current_user:
        st.success(f"🟢 Ο {online_user} είναι online!")
    else:
        st.info("⚪️ Μόνος στην εφαρμογή")

    st.divider()

    # 2. Κεντρικό Μενού (Το key="main_page" το βοηθάει να μην "ξεχνάει" τη σελίδα στο refresh)
    page = st.radio(
        "Μενού:", 
        [
            "📦 Αποθήκη", "🔄 Αντικατάσταση", "📝 Νέα Συνταγή", "📊 Διαχείριση", 
            "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "📦 Παραγγελίες B2B", 
            "📦 Lot Παραγωγής", "📈 Dashboard", "👥 Πελατολόγιο", "🧼 Συντήρηση & HACCP","🧪 Προσομοίωση Πωλήσεων", "🛒 Λίστα Αγορών"
        ],
        key="main_page"
    )

    st.divider()

    # 3. Επιλογή Χώρας για ΕΦΚ (Με key για να μην χάνει την επιλογή)
    country = st.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()), key="selected_country")
    tax_factor = TAX_RATES[country]

    st.divider()

    # 4. Εργαλεία Διαχείρισης (Refresh & Backup)
    st.subheader("⚙️ Διαχείριση")
    
    if st.button("🔄 Ανανέωση Δεδομένων", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- Πλήρες Backup ZIP ---
    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Προστέθηκαν ΟΛΟΙ οι πίνακες του συστήματος
            tables = {
                "Production_LOT": "production_log",
                "B2B_Orders": "b2b_orders",
                "Inventory": "ingredients",
                "HACCP_Log": "haccp_log", 
                "Recipes": "recipes",
                "Recipe_Items_Dosages": "recipe_items",
                "CRM_Customers": "customers",
                "CRM_Special_Discounts": "customer_specials"
            }
            for file_label, table_name in tables.items():
                try:
                    res = supabase.table(table_name).select("*").execute()
                    df_temp = pd.DataFrame(res.data) if res.data else pd.DataFrame()
                    csv_data = df_temp.to_csv(index=False).encode('utf-8-sig')
                    zf.writestr(f"{file_label}_{now_athens.strftime('%d_%m_%Y')}.csv", csv_data)
                except:
                    continue # Αν ένας πίνακας έχει πρόβλημα (π.χ. είναι άδειος), προχωράει στον επόμενο χωρίς να κρασάρει
        
        st.download_button(
            label="📥 Λήψη Όλων των Δεδομένων (.zip)",
            data=buf.getvalue(),
            file_name=f"FULL_BACKUP_CABCLUB_{now_athens.strftime('%d_%m_%Y')}.zip",
            mime="application/zip",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Σφάλμα Backup: {e}")
    st.divider()
    st.write(f"🕒 Ώρα Ελλάδος: {now_athens.strftime('%H:%M:%S')}")
    st.write(f"📅 Ημερομηνία: {now_athens.strftime('%d/%m/%Y')}")

# ==========================================
# ΑΠΟ ΕΔΩ ΚΑΙ ΚΑΤΩ ΞΕΚΙΝΑΕΙ ΤΟ ΜΕΝΟΥ (Αποθήκη κ.λπ.)
# (Δηλαδή το αμέσως επόμενο είναι: if page == "📦 Αποθήκη":)
# ==========================================
# --- 1. ΑΠΟΘΗΚΗ (ΦΟΡΜΑ ΑΝΤΙ ΓΙΑ ΠΙΝΑΚΑ) ---
if page == "📦 Αποθήκη":
    
    st.header("📦 Διαχείριση Υλικών")
    
    # Εξασφάλιση στηλών
    if "ID" not in df_ing.columns:
        df_ing.insert(0, "ID", range(1001, 1001 + len(df_ing)))
    for col in ["Weight_Full", "Αλκοόλ %", "Price", "Volume"]:
        if col not in df_ing.columns: df_ing[col] = 0.0

    tab1, tab2, tab3 = st.tabs(["➕ Νέο Υλικό", "📝 Επεξεργασία / Διόρθωση", "📋 Προβολή Όλων"])

    # --- TAB 1: ΕΙΣΑΓΩΓΗ ΝΕΟΥ ΥΛΙΚΟΥ ---
    with tab1:
        st.subheader("Προσθήκη Νέας Πρώτης ύλης")
        with st.form("add_ing_form", clear_on_submit=True):
            new_name = st.text_input("Όνομα Υλικού (π.χ. Gin Mare)")
            c1, c2, c3 = st.columns(3)
            new_price = c1.number_input("Τιμή Αγοράς (€)", min_value=0.0, step=0.1)
            new_vol = c2.number_input("ML Φιάλης", min_value=1.0, value=700.0)
            new_alc = c3.number_input("Alc %", min_value=0.0, max_value=100.0, step=0.1)
            
            new_weight = st.number_input("Βάρος Περιεχομένου σε Γραμμάρια (g)", min_value=0.0, help="Το βάρος μόνο του υγρού")
            
            if st.form_submit_button("💾 Αποθήκευση Νέου Υλικού"):
                if new_name:
                    try:
                        # Το ID μπαίνει αυτόματα από τη Supabase (SERIAL)
                        supabase.table("ingredients").insert({
                            "name": new_name,
                            "price": new_price,
                            "volume": new_vol,
                            "abv": new_alc,
                            "weight_full": new_weight
                        }).execute()
                        
                        st.success(f"✅ Το υλικό '{new_name}' προστέθηκε στη βάση!")
                        st.cache_data.clear() # Καθαρίζουμε τη μνήμη για να φέρει τα νέα δεδομένα
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Σφάλμα κατά την αποθήκευση (Ίσως υπάρχει ήδη;): {e}")
                else:
                    st.error("Παρακαλώ δώστε όνομα στο υλικό.")

    # --- TAB 2: ΕΠΕΞΕΡΓΑΣΙΑ / ΔΙΑΓΡΑΦΗ ---
    with tab2:
        st.subheader("Διόρθωση ή Διαγραφή Υλικού")
        if not df_ing.empty:
            ing_to_edit = st.selectbox("Επιλέξτε υλικό για επεξεργασία:", options=df_ing["Name"].unique(), index=None)
            
            if ing_to_edit:
                curr_row = df_ing[df_ing["Name"] == ing_to_edit].iloc[0]
                
                with st.form("edit_ing_form"):
                    edit_name = st.text_input("Όνομα Υλικού", value=curr_row["Name"])
                    e1, e2, e3 = st.columns(3)
                    edit_price = e1.number_input("Τιμή (€)", value=float(curr_row["Price"]), step=0.1)
                    edit_vol = e2.number_input("ML Φιάλης", value=float(curr_row["Volume"]), min_value=1.0)
                    edit_alc = e3.number_input("Alc %", value=float(curr_row["Αλκοόλ %"]), step=0.1)
                    
                    edit_weight = st.number_input("Βάρος Περιεχομένου (g)", value=float(curr_row["Weight_Full"]))
                    
                    col_btn1, col_btn2 = st.columns([1,1])
                    
                    # --- Ο ΝΕΟΣ ΚΩΔΙΚΑΣ UPDATE ---
                    if col_btn1.form_submit_button("Update ✅"):
                        try:
                            # 1. Ενημέρωση στην Αποθήκη (Supabase)
                            supabase.table("ingredients").update({
                                "name": edit_name,
                                "price": edit_price,
                                "volume": edit_vol,
                                "abv": edit_alc,
                                "weight_full": edit_weight
                            }).eq("id", int(curr_row["ID"])).execute()

                            # 2. Ενημέρωση στις Συνταγές (Αν άλλαξε το όνομα)
                            if ing_to_edit != edit_name:
                                # Η Supabase βρίσκει και ενημερώνει όλα τα υλικά με αυτό το όνομα με 1 εντολή!
                                supabase.table("recipe_items").update({
                                    "ingredient_name": edit_name
                                }).eq("ingredient_name", ing_to_edit).execute()
                                st.info("⚙️ Το νέο όνομα ενημερώθηκε αυτόματα και στις συνταγές!")

                            st.success(f"✅ Το υλικό '{edit_name}' ενημερώθηκε!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά την ενημέρωση: {e}")

                    # --- Ο ΝΕΟΣ ΚΩΔΙΚΑΣ ΔΙΑΓΡΑΦΗΣ ---
                    if col_btn2.form_submit_button("Διαγραφή 🗑️"):
                        try:
                            supabase.table("ingredients").delete().eq("id", int(curr_row["ID"])).execute()
                            st.warning(f"Το υλικό {ing_to_edit} διαγράφηκε.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά τη διαγραφή: {e}")

    # --- TAB 3: ΠΡΟΒΟΛΗ ΠΙΝΑΚΑ & HTML ---
    with tab3:
        st.subheader("Συνολική Εικόνα Αποθήκης")
        st.dataframe(df_ing[["ID", "Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Weight_Full"]], use_container_width=True)
        
        st.divider()
        
        # --- ΚΑΤΑΣΚΕΥΗ HTML ΓΙΑ ΛΙΣΤΑ ΠΡΩΤΩΝ ΥΛΩΝ ---
        import base64
        from datetime import datetime

        def get_base64_image(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
            except: return ""

        logo_base64 = get_base64_image("logo.png")

        # 1. CSS & Layout
        html_ing = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{ font-family: 'Helvetica', sans-serif; padding: 30px; color: #333; background-color: #f4f4f4; }}
                .container {{ background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; border-bottom: 4px solid #ffcc00; padding-bottom: 20px; margin-bottom: 30px; }}
                .logo-img {{ max-width: 120px; margin-bottom: 10px; }}
                h1 {{ margin: 0; color: #1a1a1a; text-transform: uppercase; letter-spacing: 2px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }}
                th {{ background-color: #ffcc00; color: #1a1a1a; padding: 12px; text-align: left; border: 1px solid #ddd; }}
                td {{ padding: 10px; border: 1px solid #eee; font-size: 14px; }}
                tr:nth-child(even) {{ background-color: #fff9e6; }}
                tr:hover {{ background-color: #f2f2f2; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }}
                .price-tag {{ font-weight: bold; color: #d32f2f; }}
            </style>
        </head>
        <body>
            <div class='container'>
                <div class='header'>
                    {f'<img src="data:image/png;base64,{logo_base64}" class="logo-img"><br>' if logo_base64 else ''}
                    <h1>CABCLUB | LISTA ΠΡΩΤΩΝ ΥΛΩΝ</h1>
                    <p>Ημερομηνία Εξαγωγής: {datetime.now(greece_tz).strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Όνομα Υλικού</th>
                            <th>Τιμή (€)</th>
                            <th>ML Φιάλης</th>
                            <th>Τιμή/ml</th>
                            <th>Alc %</th>
                            <th>Βάρος (g)</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        # 2. Προσθήκη Δεδομένων
        for _, row in df_ing.iterrows():
            html_ing += f"""
                <tr>
                    <td><b>{row['ID']}</b></td>
                    <td>{row['Name']}</td>
                    <td class='price-tag'>{row['Price']:.2f} €</td>
                    <td>{row['Volume']:.0f} ml</td>
                    <td>{row['Τιμή/ml']:.4f} €</td>
                    <td>{row['Αλκοόλ %']:.1f}%</td>
                    <td>{row['Weight_Full']:.1f} g</td>
                </tr>
            """

        html_ing += """
                    </tbody>
                </table>
                <div class='footer'>
                    © CabClub Cocktails Management System - Warehouse Report
                </div>
            </div>
        </body>
        </html>
        """

        # 3. Κουμπί Λήψης
        st.download_button(
            label="📄 Λήψη Λίστας Αποθήκης (HTML)",
            data=html_ing,
            file_name=f"CabClub_Warehouse_{datetime.now(greece_tz).strftime('%d_%m_%Y')}.html",
            mime="text/html",
            use_container_width=True
        )


# --- 2. ΝΕΑ ΣΥΝΤΑΓΗ (SUPABASE EDITION) ---
elif page == "📝 Νέα Συνταγή":
    st.header("📝 Προσθήκη Νέας Συνταγής (Cocktail)")

    with st.form("new_recipe_form", clear_on_submit=True):
        st.subheader("Βασικά Στοιχεία")
        col1, col2 = st.columns(2)
        new_rec_name = col1.text_input("Όνομα Cocktail", placeholder="π.χ. CabClub Margarita")
        new_barcode = col2.text_input("Barcode / Κωδικός", placeholder="Προαιρετικό")
        
        st.divider()
        st.subheader("🧪 Υλικά & Ποσότητες")
        
        # Δημιουργούμε πεδία για 13 υλικά (για να ταιριάζει με το παλιό σου σύστημα)
        ingredients_data = []
        cols_ing = st.columns(2)
        
        for i in range(1, 14):
            with cols_ing[i % 2]:  # Μοιράζουμε τα πεδία σε 2 στήλες για οικονομία χώρου
                c_ing, c_ml = st.columns([2, 1])
                # Το ing_options φορτώνεται στην αρχή του app.py από την Supabase!
                ing_val = c_ing.selectbox(f"Συστατικό {i}", options=ing_options, key=f"ing_{i}")
                ml_val = c_ml.number_input(f"ML {i}", min_value=0.0, step=0.5, key=f"ml_{i}")
                
                # Αν έχει επιλεγεί υλικό και έχει μπει ποσότητα, το κρατάμε στη λίστα
                if ing_val and ing_val != "ΚΕΝΟ" and ml_val > 0:
                    ingredients_data.append({"name": ing_val, "ml": ml_val})

        st.divider()
        submitted = st.form_submit_button("💾 Αποθήκευση Συνταγής", type="primary")

        if submitted:
            if not new_rec_name:
                st.error("❌ Πρέπει να δώσετε όνομα στο Cocktail!")
            elif not ingredients_data:
                st.error("❌ Πρέπει να προσθέσετε τουλάχιστον 1 υλικό με ποσότητα μεγαλύτερη από 0.")
            else:
                try:
                    # ΒΗΜΑ 1: Δημιουργία της Συνταγής (Title) στον πίνακα 'recipes'
                    res = supabase.table("recipes").insert({
                        "name": new_rec_name.strip(),
                        "barcode": new_barcode.strip() if new_barcode else ""
                    }).execute()
                    
                    # Παίρνουμε το ID που της έδωσε αυτόματα η βάση (π.χ. ID 5)
                    new_recipe_id = res.data[0]["id"]
                    
                    # ΒΗΜΑ 2: Αποθήκευση των Υλικών στον πίνακα 'recipe_items'
                    items_to_insert = []
                    for item in ingredients_data:
                        items_to_insert.append({
                            "recipe_id": new_recipe_id,
                            "ingredient_name": item["name"],
                            "ml_per_unit": float(item["ml"])
                        })
                    
                    # Τα στέλνουμε όλα μαζί στη βάση με μια κίνηση!
                    supabase.table("recipe_items").insert(items_to_insert).execute()
                    
                    st.success(f"✅ Η συνταγή '{new_rec_name}' αποθηκεύτηκε επιτυχώς με {len(items_to_insert)} υλικά!")
                    st.balloons()
                    st.cache_data.clear() # Καθαρίζουμε τη μνήμη για να τη δει αμέσως στα άλλα μενού
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    # Το πιο πιθανό σφάλμα εδώ είναι να υπάρχει ήδη συνταγή με το ίδιο όνομα (UNIQUE constraint)
                    st.error(f"⚠️ Σφάλμα αποθήκευσης. Ίσως υπάρχει ήδη συνταγή με αυτό το όνομα! Λεπτομέρειες: {e}")

# --- 5. ΔΙΑΧΕΙΡΙΣΗ ΣΥΝΤΑΓΩΝ (SUPABASE EDITION) ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία & Διαγραφή Συνταγών")

    # --- ΜΑΓΙΚΟ ΚΟΥΜΠΙ ΓΙΑ ΜΕΤΑΦΟΡΑ ΠΑΛΙΩΝ ΣΥΝΤΑΓΩΝ (ΠΡΟΣΩΡΙΝΟ) ---
    with st.expander("🚀 Εισαγωγή παλιών συνταγών από CSV"):
        st.info("Ανέβασε το αρχείο με τις συνταγές σου για να περαστούν μαζικά στη Supabase.")
        uploaded_rec = st.file_uploader("Ανέβασε το DB_RECIPES.csv", type="csv")
        if uploaded_rec and st.button("Μεταφορά Συνταγών Τώρα!", type="primary"):
            try:
                temp_df = pd.read_csv(uploaded_rec)
                for _, row in temp_df.iterrows():
                    name = str(row.get("Ονομα", "")).strip()
                    barcode = str(row.get("Barcode", "")).replace(".0", "").replace("nan", "")
                    price = float(row.get("Τιμή Καταλόγου", 0.0)) if pd.notna(row.get("Τιμή Καταλόγου")) else 0.0
                    
                    if name:
                        # 1. Φτιάχνουμε τη συνταγή
                        res = supabase.table("recipes").insert({"name": name, "barcode": barcode, "catalog_price": price}).execute()
                        rec_id = res.data[0]["id"]
                        
                        # 2. Περνάμε τα υλικά της
                        items_to_insert = []
                        for i in range(1, 14):
                            ing = str(row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                            ml = float(row.get(f"ML{i}", 0.0)) if pd.notna(row.get(f"ML{i}")) else 0.0
                            if ing and ing != "ΚΕΝΟ" and ing != "nan" and ml > 0:
                                items_to_insert.append({
                                    "recipe_id": rec_id,
                                    "ingredient_name": ing,
                                    "ml_per_unit": ml
                                })
                        if items_to_insert:
                            supabase.table("recipe_items").insert(items_to_insert).execute()
                st.success("🎉 Όλες οι συνταγές μεταφέρθηκαν!")
                st.balloons()
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Σφάλμα: {e}")

    # Ζητάμε τα βασικά στοιχεία όλων των συνταγών από τη Supabase
    res_rec = supabase.table("recipes").select("*").order("name").execute()
    
    if not res_rec.data:
        st.info("Δεν βρέθηκαν αποθηκευμένες συνταγές. Πηγαίνετε στη 'Νέα Συνταγή' ή κάντε Εισαγωγή από πάνω.")
    else:
        df_recipes_base = pd.DataFrame(res_rec.data)
        
        # 1. Επιλογή Cocktail
        recipe_to_edit = st.selectbox(
            "Αναζήτηση Cocktail:", 
            options=df_recipes_base["name"].tolist(),
            index=None,
            placeholder="Επιλέξτε ένα Cocktail..."
        )
        
        if recipe_to_edit:
            # Βρίσκουμε τη γραμμή της επιλεγμένης συνταγής
            rec_row = df_recipes_base[df_recipes_base["name"] == recipe_to_edit].iloc[0]
            rec_id = int(rec_row["id"])
            
            # Βρίσκουμε τα υλικά
            res_items = supabase.table("recipe_items").select("*").eq("recipe_id", rec_id).execute()
            items_data = res_items.data if res_items.data else []
            
            tab_edit, tab_del = st.tabs(["📝 Επεξεργασία Στοιχείων", "🗑️ Διαγραφή Συνταγής"])
            
            with tab_edit:
                with st.form(f"form_{rec_id}"): 
                    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                    edit_name = col_h1.text_input("Όνομα Cocktail", value=str(rec_row["name"]))
                    
                    current_barcode = str(rec_row.get("barcode", ""))
                    if current_barcode == "None" or current_barcode == "nan": current_barcode = ""
                    edit_barcode = col_h2.text_input("Barcode Shop", value=current_barcode)
                    
                    current_price = float(rec_row.get("catalog_price", 0.0)) if rec_row.get("catalog_price") else 0.0
                    edit_price = col_h3.number_input("Τιμή Καταλόγου (€)", value=current_price, step=0.10)
                    
                    st.write("---")
                    c1, c2 = st.columns(2)
                    
                    new_ingredients_list = []
                    
                    # Καθαρισμός επιλογών
                    clean_options = [str(opt).strip() for opt in ing_options]
                    
                    for i in range(1, 14):
                        target_col = c1 if i <= 7 else c2
                        with target_col:
                            val_from_db = "ΚΕΝΟ"
                            ml_from_db = 0.0
                            if i - 1 < len(items_data):
                                val_from_db = items_data[i-1]["ingredient_name"].strip()
                                ml_from_db = float(items_data[i-1]["ml_per_unit"])
                            
                            try:
                                current_idx = clean_options.index(val_from_db)
                            except ValueError:
                                current_idx = 0
                            
                            sub_c1, sub_c2 = st.columns([2, 1])
                            
                            ing_val = sub_c1.selectbox(
                                f"Υλικό {i}", 
                                options=ing_options, 
                                index=current_idx, 
                                key=f"s_{i}_{rec_id}"
                            )
                            ml_val = sub_c2.number_input(
                                f"ML {i}", 
                                value=ml_from_db,
                                min_value=0.0,
                                step=0.5,
                                key=f"m_{i}_{rec_id}"
                            )
                            new_ingredients_list.append({"name": ing_val, "ml": ml_val})

                    # 💡 Το Κουμπί ΠΡΕΠΕΙ να είναι ακριβώς σε αυτή την εσοχή (μέσα στο with st.form)
                    submitted = st.form_submit_button("💾 Αποθήκευση Αλλαγών Συνταγής", type="primary")

                    if submitted:
                        try:
                            # ΔΙΟΡΘΩΣΗ 1: Χρησιμοποιούμε το rec_row (και το rec_id)
                            current_version = int(rec_row.get("version", 1)) if "version" in rec_row else 1
                            
                            # 2. ΑΡΧΕΙΟΘΕΤΗΣΗ ΠΑΛΙΑΣ
                            supabase.table("recipes").update({
                                "is_active": False
                            }).eq("id", rec_id).execute()
                            
                            # 3. ΔΗΜΙΟΥΡΓΙΑ ΝΕΑΣ ΕΚΔΟΣΗΣ
                            res = supabase.table("recipes").insert({
                                "name": edit_name,
                                "barcode": edit_barcode,
                                "catalog_price": edit_price,
                                "is_active": True,
                                "version": current_version + 1
                            }).execute()
                            
                            new_recipe_id = res.data[0]["id"]
                            
                            # 4. ΑΠΟΘΗΚΕΥΣΗ ΝΕΩΝ ΥΛΙΚΩΝ
                            items_to_insert = []
                            # ΔΙΟΡΘΩΣΗ 2: Χρησιμοποιούμε το new_ingredients_list που γεμίσαμε μόλις!
                            for item in new_ingredients_list:
                                # ΔΙΟΡΘΩΣΗ 3: Αποθηκεύουμε ΜΟΝΟ αν το υλικό δεν είναι "ΚΕΝΟ" και τα ml είναι > 0
                                if item["name"] != "ΚΕΝΟ" and float(item["ml"]) > 0:
                                    items_to_insert.append({
                                        "recipe_id": new_recipe_id,
                                        "ingredient_name": item["name"],
                                        "ml_per_unit": float(item["ml"])
                                    })
                                    
                            if items_to_insert:
                                supabase.table("recipe_items").insert(items_to_insert).execute()
                            
                            st.success(f"✅ Η συνταγή αναβαθμίστηκε επιτυχώς στην Έκδοση v{current_version + 1}!")
                            st.cache_data.clear()
                            time.sleep(2)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Σφάλμα κατά την αναβάθμιση έκδοσης: {e}")

            with tab_del:
                st.warning(f"⚠️ Είστε σίγουροι ότι θέλετε να διαγράψετε το **{recipe_to_edit}**;")
                if st.button(f"🗑️ Οριστική Διαγραφή", key=f"del_{rec_id}", type="primary"):
                    supabase.table("recipes").delete().eq("id", rec_id).execute()
                    st.error(f"❌ Η συνταγή διαγράφηκε.")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()

        st.write("---")
        with st.expander("📋 Προεπισκόπηση Όλων των Ενεργών Συνταγών (Πίνακας)"):
            # --- ΜΑΓΕΙΑ: Φτιάχνουμε το df_rec δυναμικά από τη Supabase! ---
            all_items_res = supabase.table("recipe_items").select("*").execute()
            all_items = all_items_res.data if all_items_res.data else []
            
            df_rec_list = []
            for _, r in df_recipes_base.iterrows():
                # Παίρνουμε την τρέχουσα έκδοση (αν δεν υπάρχει, βάζουμε το 1)
                ver = int(r.get("version", 1)) if pd.notna(r.get("version")) else 1
                
                row_dict = {
                    "Ονομα": r["name"],
                    "Έκδοση": f"v{ver}",  # ΝΕΑ ΠΡΟΣΘΗΚΗ: Δείχνει το version της συνταγής
                    "Barcode": str(r.get("barcode", "")).replace(".0", "").replace("nan", ""),
                    "Τιμή Καταλόγου": float(r.get("catalog_price", 0.0)) if pd.notna(r.get("catalog_price")) else 0.0
                }
                
                r_items = [item for item in all_items if item["recipe_id"] == r["id"]]
                
                for i in range(1, 14):
                    if i - 1 < len(r_items):
                        row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = r_items[i-1]["ingredient_name"]
                        row_dict[f"ML{i}"] = float(r_items[i-1]["ml_per_unit"])
                    else:
                        row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = "ΚΕΝΟ"
                        row_dict[f"ML{i}"] = 0.0
                
                df_rec_list.append(row_dict)
            
            if df_rec_list:
                df_rec = pd.DataFrame(df_rec_list)
                st.dataframe(df_rec, use_container_width=True)
            else:
                st.info("Δεν υπάρχουν ενεργές συνταγές για προβολή.")

# --- 4. ΑΝΑΛΥΣΗ (ΔΙΟΡΘΩΜΕΝΗ ΓΙΑ ΣΥΜΒΑΤΟΤΗΤΑ ΜΕ SUPABASE, ΠΩΛΗΣΕΙΣ ΚΑΙ ΒΑΡΟΣ) ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")
    
    # --- ΜΑΓΕΙΑ SUPABASE: Φτιάχνουμε τα df_ing & df_rec όπως ακριβώς τα περιμένει ο κώδικάς σου! ---
    # 1. Φόρτωση Αποθήκης
    res_ing = supabase.table("ingredients").select("*").execute()
    ing_data = res_ing.data if res_ing.data else []
    df_ing_list = []
    for item in ing_data:
        df_ing_list.append({
            "Name": item["name"],
            "Price": item["price"],
            "Volume": item["volume"],
            "weight_full": item.get("weight_full", 0.0), # 👈 Φορτώνουμε το συνολικό βάρος συσκευασίας
            "Αλκοόλ %": item["abv"],
            "ABV": item["abv"], # Το χρειάζεται το HTML book πιο κάτω
            "Τιμή/ml": item["price"] / item["volume"] if item["volume"] > 0 else 0
        })
    df_ing = pd.DataFrame(df_ing_list)

    # 2. Φόρτωση & Μετατροπή Συνταγών (σε οριζόντια μορφή με 13 υλικά)
    res_rec_base = supabase.table("recipes").select("*").order("name").execute()
    rec_data = res_rec_base.data if res_rec_base.data else []
    all_items = supabase.table("recipe_items").select("*").execute().data if rec_data else []
    
    df_rec_list = []
    for r in rec_data:
        row_dict = {
            "Ονομα": r["name"],
            "Barcode": str(r.get("barcode", "")).replace(".0", "").replace("nan", ""),
            "Τιμή Καταλόγου": r.get("catalog_price", 0.0)
        }
        r_items = [item for item in all_items if item["recipe_id"] == r["id"]]
        for i in range(1, 14):
            if i - 1 < len(r_items):
                row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = r_items[i-1]["ingredient_name"]
                row_dict[f"ML{i}"] = r_items[i-1]["ml_per_unit"]
            else:
                row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = "ΚΕΝΟ"
                row_dict[f"ML{i}"] = 0.0
        df_rec_list.append(row_dict)
    df_rec = pd.DataFrame(df_rec_list)
    # --- ΤΕΛΟΣ ΦΟΡΤΩΣΗΣ SUPABASE ---

    recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

    if not df_rec.empty:
        # Sidebar Ρυθμίσεις
        st.sidebar.subheader("Ρυθμίσεις Ανάλυσης")
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        
        # ΜΟΝΑΔΙΚΗ ΕΠΙΛΟΓΗ ΚΟΚΤΕΙΛ
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        # Βασικές Τιμές
        p_retail = float(r.get("Τιμή Καταλόγου", 0))
        p_agent = p_retail * 0.74
        p_custom = p_retail * (1 - discount/100)
        
        raw_cost, pure_alc_ml, total_ml_cocktail, total_weight_cocktail = 0.0, 0.0, 0.0, 0.0
        breakdown = []
        missing_ingredients = [] # Λίστα για υλικά που δεν βρέθηκαν
        
        # --- ΣΥΛΛΟΓΗ ΔΕΔΟΜΕΝΩΝ ΣΥΝΤΑΓΗΣ ---
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
            ml = float(r.get(f"ML{i}", 0))
            
            if ing_n != "ΚΕΝΟ" and ml > 0:
                total_ml_cocktail += ml
                if ing_n == "Νερό":
                    total_weight_cocktail += ml  # 1 ml νερό = 1 γραμμάριο
                    breakdown.append({"Υλικό": "Νερό", "ML": ml, "Βάρος (g)": ml, "Κόστος": 0.0, "Alc %": 0.0})
                elif ing_n not in ["nan", ""]:
                    # Αναζήτηση στην Αποθήκη
                    match = df_ing[df_ing["Name"] == ing_n]
                    
                    if not match.empty:
                        ing_row = match.iloc[0]
                        alc_val = float(ing_row.get("Αλκοόλ %", 0))
                        actual_alc_pct = alc_val if alc_val <= 1 else alc_val / 100
                        pure_alc_ml += (ml * actual_alc_pct)
                        
                        price_ml = float(ing_row.get("Τιμή/ml", 0))
                        item_cost = ml * price_ml
                        raw_cost += item_cost
                        
                        # --- ΔΥΝΑΜΙΚΟΣ ΥΠΟΛΟΓΙΣΜΟΣ ΒΑΡΟΥΣ ΑΠΟ ΤΗΝ ΑΠΟΘΗΚΗ ---
                        pkg_weight = float(ing_row.get("weight_full", 0) or 0)
                        pkg_volume = float(ing_row.get("Volume", 0) or 0)
                        
                        if pkg_volume > 0 and pkg_weight > 0:
                            item_weight = (pkg_weight / pkg_volume) * ml
                        else:
                            item_weight = ml  # Ασφάλεια 1:1 αν λείπουν δεδομένα βάρους
                        
                        total_weight_cocktail += item_weight
                        
                        breakdown.append({
                            "Υλικό": ing_n, 
                            "ML": ml, 
                            "Βάρος (g)": item_weight, # 👈 Νέα στήλη ακριβώς μετά το ML
                            "Κόστος": item_cost, 
                            "Alc %": actual_alc_pct * 100
                        })
                    else:
                        missing_ingredients.append(ing_n)
                        total_weight_cocktail += ml  # Ασφάλεια 1:1 για το σύνολο
                        breakdown.append({
                            "Υλικό": f"⚠️ {ing_n} (Μη διαθέσιμο)", 
                            "ML": ml, 
                            "Βάρος (g)": ml,
                            "Κόστος": 0.0, 
                            "Alc %": 0.0
                        })

        if missing_ingredients:
            st.error(f"⚠️ Τα παρακάτω υλικά δεν βρέθηκαν στην Αποθήκη: {', '.join(missing_ingredients)}")

        # --- ΥΠΟΛΟΓΙΣΜΟΙ ΤΕΧΝΙΚΟΥ ΦΑΚΕΛΟΥ ---
        final_abv = (pure_alc_ml / total_ml_cocktail * 100) if total_ml_cocktail > 0 else 0
        try: efk_informational = pure_alc_ml * tax_factor
        except NameError: efk_informational = pure_alc_ml * 0.0255
        try: fixed_cost = TOTAL_FIXED
        except NameError: fixed_cost = 0.50
        
        # ΣΥΝΟΛΙΚΟ ΚΟΣΤΟΣ ΑΝΑ ΦΙΑΛΗ (Το χρησιμοποιούμε και στις πωλήσεις παρακάτω)
        total_production = raw_cost + fixed_cost 
        
        profit_retail = p_retail - total_production
        profit_agent = p_agent - total_production
        profit_custom = p_custom - total_production
        margin_retail = (profit_retail / p_retail * 100) if p_retail > 0 else 0

        # --- ΕΜΦΑΝΙΣΗ ΣΤΗΝ ΟΘΟΝΗ ---
        st.subheader(f"Στατιστικά για: {choice}")
        m_col1, m_col2, m_col3 = st.columns(3)  # Αυξήσαμε σε 3 στήλες για να χωρέσει το βάρος
        m_col1.metric("Συνολική Ποσότητα", f"{total_ml_cocktail:.1f} ml".replace('.', ','))
        m_col2.metric("Συνολικό Βάρος", f"{total_weight_cocktail:.1f} g".replace('.', ','))  # 👈 Το νέο πεδίο δίπλα στα ml
        m_col3.metric("Αλκοολικός Βαθμός (ABV)", f"{final_abv:.2f} %".replace('.', ','))
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Τιμή Λιανικής", f"{p_retail:.2f} €".replace('.', ','))
        c2.metric("Τιμή Αντιπροσώπου", f"{p_agent:.2f} €".replace('.', ','))
        c3.metric("Τιμή με Έκπτωση", f"{p_custom:.2f} €".replace('.', ','), delta=f"-{discount}%")

        st.markdown("---")
        st.write("### 🛠️ Ανάλυση Κόστους & Φόρων (Ανά Φιάλη)")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Κόστος Υλικών", f"{raw_cost:.2f} €".replace('.', ','))
        k2.metric("ΕΦΚ (Ενσωμ.)", f"{efk_informational:.2f} €".replace('.', ','))
        k3.metric("Σταθερά Έξοδα", f"{fixed_cost:.2f} €".replace('.', ','))
        k4.metric("ΣΥΝΟΛΟ ΚΟΣΤΟΥΣ", f"{total_production:.2f} €".replace('.', ','))

        # --- ΠΙΝΑΚΑΣ ΥΛΙΚΩΝ ΣΤΗΝ ΟΘΟΝΗ ---
        st.markdown("---")
        st.write("### 🍹 Σύνθεση Υλικών")
        df_screen = pd.DataFrame(breakdown)
        if not df_screen.empty:
            df_render = df_screen.copy()
            for col in ["ML", "Βάρος (g)", "Alc %", "Κόστος"]:  # Προσθέσαμε το "Βάρος (g)" στη μορφοποίηση
                if col in df_render.columns:
                    df_render[col] = df_render[col].apply(lambda x: f"{x:.2f}".replace('.', ','))
            st.table(df_render[["Υλικό", "ML", "Βάρος (g)", "Alc %", "Κόστος"]])  # Εμφάνιση της στήλης στη σωστή θέση

        # =====================================================================
        # ΝΕΑ ΕΝΟΤΗΤΑ: ΑΝΑΛΥΣΗ ΠΩΛΗΣΕΩΝ ΚΑΙ ΑΠΟΔΟΣΗΣ ΠΡΟΪΟΝΤΟΣ
        # =====================================================================
        st.markdown("---")
        st.write(f"### 📈 Οικονομική Απόδοση & Πωλήσεις ({choice})")
        
        # Τραβάμε σωστά τη στήλη "discount" των πελατών
        cust_discount_map = {}
        try:
            res_cust = supabase.table("customers").select("name, discount").execute()
            if res_cust.data:
                cust_discount_map = {str(c.get("name", "")).strip(): float(c.get("discount", 0.0) or 0.0) for c in res_cust.data}
        except Exception as e:
            pass
        
        res_sales = supabase.table("production_log").select("*").eq("cocktail_name", choice).execute()
        if res_sales.data:
            df_sales = pd.DataFrame(res_sales.data)
            
            # 1. 🚀 ΔΙΟΡΘΩΣΗ: Καθαρίζουμε τις διπλοεγγραφές προσθέτοντας το "prod_date" για να μην χάνονται σπασμένες παραγγελίες!
            if "prod_time" in df_sales.columns and "prod_date" in df_sales.columns:
                df_sales = df_sales.drop_duplicates(subset=["cocktail_name", "prod_date", "prod_time", "customer"])
            
            # 2. ΑΣΦΑΛΗΣ ΜΕΤΑΤΡΟΠΗ ΔΕΔΟΜΕΝΩΝ (Τέλος στα NaN!)
            df_sales['t_pcs'] = pd.to_numeric(df_sales.get('pieces', 0), errors='coerce').fillna(0)
            df_sales['f_pcs'] = pd.to_numeric(df_sales.get('free_pieces', 0), errors='coerce').fillna(0)
            df_sales['s_pcs'] = pd.to_numeric(df_sales.get('discounted_pieces', 0), errors='coerce').fillna(0)
            df_sales['s_pct'] = pd.to_numeric(df_sales.get('discount_pct', 0), errors='coerce').fillna(0)

            # Ασφαλής διαχωρισμός τεμαχίων
            df_sales['s_pcs'] = df_sales.apply(lambda r: min(r['s_pcs'], max(0, r['t_pcs'] - r['f_pcs'])), axis=1)
            df_sales['normal_pcs'] = df_sales['t_pcs'] - df_sales['f_pcs'] - df_sales['s_pcs']

            # Τιμή Καταλόγου
            catalog_price = 0.0
            try:
                res_rec_price = supabase.table("recipes").select("catalog_price").eq("name", choice).execute()
                if res_rec_price.data:
                    catalog_price = float(res_rec_price.data[0].get("catalog_price", 0.0) or 0.0)
            except Exception:
                pass
            
            # Γενική Έκπτωση Πελάτη
            df_sales['customer'] = df_sales.get('customer', '').astype(str).str.strip()
            df_sales['global_discount'] = df_sales['customer'].map(cust_discount_map).fillna(0)

            # 3. ΑΣΦΑΛΗΣ ΥΠΟΛΟΓΙΣΜΟΣ ΕΣΟΔΩΝ (Διαδοχικές Εκπτώσεις)
            df_sales['price_after_global'] = catalog_price * (1 - (df_sales['global_discount'] / 100))
            
            df_sales['rev_normal'] = df_sales['normal_pcs'] * df_sales['price_after_global']
            df_sales['rev_special'] = df_sales['s_pcs'] * df_sales['price_after_global'] * (1 - (df_sales['s_pct'] / 100))
            
            df_sales['Theoretical_Revenue'] = df_sales['rev_normal'] + df_sales['rev_special']
            df_sales['Theoretical_Revenue'] = df_sales['Theoretical_Revenue'].clip(lower=0)

            # 4. ΣΥΓΚΕΝΤΡΩΤΙΚΑ ΑΠΟΤΕΛΕΣΜΑΤΑ
            total_produced_pcs = int(df_sales['t_pcs'].sum())
            total_free_pcs = int(df_sales['f_pcs'].sum())
            total_real_revenue = df_sales['Theoretical_Revenue'].sum()
            
            # Υπολογισμός Κόστους (Χρησιμοποιεί το total_production = κόστος 1 τμχ, που έχεις υπολογίσει πιο πάνω)
            total_production_cost = total_produced_pcs * total_production
            total_net_profit = total_real_revenue - total_production_cost
            
            profit_percentage = 0.0
            cost_percentage = 0.0
            
            if total_real_revenue > 0:
                profit_percentage = (total_net_profit / total_real_revenue) * 100.0
                cost_percentage = (total_production_cost / total_real_revenue) * 100.0
                
            # --- ΕΜΦΑΝΙΣΗ ΔΕΔΟΜΕΝΩΝ ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(label="Συνολική Παραγωγή", value=f"{total_produced_pcs} τμχ", delta=f"{total_free_pcs} δώρα", delta_color="off")
            m2.metric(label="Τζίρος Προϊόντος", value=f"{total_real_revenue:,.2f} €")
            m3.metric(label="Συνολικό Κόστος", value=f"{total_production_cost:,.2f} €", delta=f"{cost_percentage:.1f}% επί τζίρου", delta_color="inverse")
            m4.metric(label="Καθαρό Κέρδος", value=f"{total_net_profit:,.2f} €", delta=f"{profit_percentage:.1f}% περιθώριο")
            
            st.markdown("<br>", unsafe_allow_html=True)
            g1, g2 = st.columns(2)
            with g1:
                st.markdown("**📊 Ποσοστιαία Ανάλυση Τζίρου**")
                fig_pie = px.pie(
                    names=["Καθαρό Κέρδος", "Κόστος (Υλικά & Σταθερά)"],
                    values=[max(0, total_net_profit), total_production_cost],
                    hole=0.4,
                    color_discrete_sequence=["#28a745", "#dc3545"]
                )
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                st.markdown("**🏆 Top 5 Αγοραστές (Τεμάχια)**")
                # Δείχνουμε τα "πληρωμένα" τεμάχια (Σύνολο - Δώρα) στο γράφημα
                df_sales['paid_pieces'] = df_sales['t_pcs'] - df_sales['f_pcs']
                df_cust = df_sales.groupby("customer")["paid_pieces"].sum().reset_index()
                df_cust = df_cust.sort_values(by="paid_pieces", ascending=True).tail(5)
                fig_bar = px.bar(
                    df_cust, x="paid_pieces", y="customer", orientation="h", text="paid_pieces", color_discrete_sequence=["#007bff"]
                )
                fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, xaxis_title="Πληρωμένα Τεμάχια", yaxis_title="")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Δεν βρέθηκαν καταγεγραμμένες πωλήσεις/παραγωγή για το συγκεκριμένο κοκτέιλ.")
        # =====================================================================
        # --- 📜 ΕΝΟΤΗΤΑ ΕΞΑΓΩΓΗΣ ΕΠΑΓΓΕΛΜΑΤΙΚΟΥ REPORT (HTML) ---
        st.divider()
        st.subheader("📜 Εξαγωγή Τεχνικού Φακέλου")

        try:
            current_barcode = df_rec[df_rec['Ονομα'] == choice]['Barcode'].values[0]
            if not current_barcode or str(current_barcode).lower() == 'nan':
                current_barcode = "Δεν ορίστηκε"
        except:
            current_barcode = "Δεν βρέθηκε"

        ingredients_rows = ""
        for item in breakdown:
            ingredients_rows += f"""
            <tr>
                <td>{item['Υλικό']}</td>
                <td style='text-align:right;'>{item['ML']:g} ml</td>
                <td style='text-align:right;'>{item.get('Βάρος (g)', item['ML']):.1f} g</td>
                <td style='text-align:right;'>{item.get('Alc %', 0):g}%</td>
                <td style='text-align:right;'>{item['Κόστος']:.3f} €</td>
            </tr>
            """

        report_html = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; line-height: 1.5; padding: 30px; }}
                .report-card {{ max-width: 800px; margin: auto; border: 1px solid #eee; padding: 40px; border-radius: 15px; box-shadow: 0 0 20px rgba(0,0,0,0.05); }}
                .header {{ text-align: center; border-bottom: 3px solid #d32f2f; padding-bottom: 20px; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; color: #d32f2f; font-size: 28px; text-transform: uppercase; }}
                .meta-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                .meta-item {{ font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
                th {{ background-color: #34495e; color: white; padding: 12px; text-align: left; font-size: 13px; }}
                td {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 13px; }}
                .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .stat-box {{ padding: 15px; border-radius: 8px; background: #2c3e50; color: white; }}
                .stat-label {{ font-size: 11px; text-transform: uppercase; opacity: 0.8; }}
                .stat-value {{ font-size: 18px; font-weight: bold; color: #00ffcc; }}
                .footer {{ margin-top: 40px; text-align: center; font-size: 11px; color: #95a5a6; border-top: 1px solid #eee; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class='report-card'>
                <div class='header'>
                    <h1>CABCLUB COCKTAILS</h1>
                    <div style='font-size: 12px; color: #7f8c8d;'>ΤΕΧΝΙΚΟ ΔΕΛΤΙΟ & ΑΝΑΛΥΣΗ ΚΟΣΤΟΥΣ</div>
                </div>
                <div class='meta-info'>
                    <div class='meta-item'><strong>Cocktail:</strong> {choice}</div>
                    <div class='meta-item'><strong>Barcode:</strong> {current_barcode}</div>
                    <div class='meta-item'><strong>Συνολικά ML:</strong> {total_ml_cocktail:g} ml</div>
                    <div class='meta-item'><strong>Συνολικό Βάρος:</strong> {total_weight_cocktail:.1f} g</div>
                    <div class='meta-item'><strong>Αλκοόλ (ABV):</strong> {final_abv:g}%</div>
                    <div class='meta-item'><strong>Ημερομηνία:</strong> {datetime.now(greece_tz).strftime('%d/%m/%Y')}</div>
                </div>
                <h3 style='color: #2c3e50; border-left: 4px solid #d32f2f; padding-left: 10px;'>📋 Συνταγή</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Υλικό</th>
                            <th style='text-align:right;'>Ποσότητα</th>
                            <th style='text-align:right;'>Βάρος</th>
                            <th style='text-align:right;'>ABV</th>
                            <th style='text-align:right;'>Κόστος</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ingredients_rows}
                    </tbody>
                </table>
                <h3 style='color: #2c3e50; border-left: 4px solid #d32f2f; padding-left: 10px;'>💰 Οικονομικά Στοιχεία</h3>
                <div class='summary-grid'>
                    <div class='stat-box'>
                        <div class='stat-label'>Κόστος Παραγωγής</div>
                        <div class='stat-value'>{total_production:.2f} €</div>
                    </div>
                    <div class='stat-box'>
                        <div class='stat-label'>Margin Λιανικής</div>
                        <div class='stat-value'>{margin_retail:.1f}%</div>
                    </div>
                    <div class='stat-box' style='background: #f1f2f6; color: #2c3e50;'>
                        <div class='stat-label' style='color: #7f8c8d;'>Κέρδος Λιανικής</div>
                        <div class='stat-value' style='color: #2c3e50;'>{profit_retail:.2f} €</div>
                        <div style='font-size: 9px;'>Τιμή: {p_retail:.2f} €</div>
                    </div>
                    <div class='stat-box' style='background: #f1f2f6; color: #2c3e50;'>
                        <div class='stat-label' style='color: #7f8c8d;'>Κέρδος Αντιπροσώπου</div>
                        <div class='stat-value' style='color: #2c3e50;'>{profit_agent:.2f} €</div>
                        <div style='font-size: 9px;'>Τιμή: {p_agent:.2f} €</div>
                    </div>
                </div>
                <div class='footer'>
                    Το παρόν έγγραφο αποτελεί πνευματική ιδιοκτησία της CABCLUB.<br>
                    Υπολογισμένο με σταθερά έξοδα μονάδας {fixed_cost:g} €.
                </div>
            </div>
        </body>
        </html>
        """

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            st.info(f"Το επαγγελματικό report για το {choice} είναι έτοιμο για λήψη.")
        with col_btn2:
            st.download_button(
                label="📥 Λήψη Report (HTML)",
                data=report_html,
                file_name=f"Report_{choice.replace(' ', '_')}.html",
                mime="text/html",
                key="html_report_download"
            )

        # --- 🖨️ ΕΚΤΥΠΩΣΗ ΠΛΗΡΟΥΣ ΒΙΒΛΙΟΥ ΣΥΝΤΑΓΩΝ (Yellow Theme + Logo) ---
        st.divider()
        st.subheader("🖨️ Εκτύπωση Βιβλίου Συνταγών")

        import base64

        def get_base64_image(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
            except:
                return ""

        logo_base64 = get_base64_image("logo.png") 

        html_book = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{ font-family: 'Helvetica', sans-serif; padding: 40px; color: #333; background-color: #f9f9f9; }}
                .main-title {{ text-align: center; border-bottom: 5px solid #ffcc00; padding-bottom: 10px; margin-bottom: 50px; }}
                .logo-img {{ max-width: 150px; margin-bottom: 10px; }}
                .recipe-card {{ 
                    background-color: white; 
                    border: 1px solid #ddd; 
                    border-radius: 12px; 
                    padding: 25px; 
                    margin-bottom: 40px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                    page-break-inside: avoid;
                }}
                .recipe-header {{ 
                    background-color: #ffcc00; 
                    color: #1a1a1a; 
                    padding: 15px; 
                    border-radius: 8px 8px 0 0; 
                    margin: -25px -25px 20px -25px; 
                }}
                .recipe-name {{ margin: 0; font-size: 26px; text-transform: uppercase; }}
                .barcode-label {{ font-size: 14px; opacity: 0.8; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th {{ background-color: #fff9e6; text-align: left; padding: 12px; border-bottom: 2px solid #ffcc00; color: #444; }}
                td {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 15px; }}
                .ing-name {{ font-weight: bold; color: #2c3e50; }}
                .footer {{ text-align: center; font-size: 12px; color: #7f8c8d; margin-top: 60px; border-top: 1px solid #ccc; padding-top: 10px; }}
                .analysis-box {{ 
                    margin-top:20px; 
                    padding:12px; 
                    background:#fffdf2; 
                    border-top:3px solid #ffcc00; 
                    border-radius: 0 0 8px 8px; 
                }}
            </style>
        </head>
        <body>
            <div class='main-title'>
                {f'<img src="data:image/png;base64,{logo_base64}" class="logo-img"><br>' if logo_base64 else ''}
                <h1>CABCLUB COCKTAILS</h1>
                <h2>ΟΛΟΚΛΗΡΩΜΕΝΟ ΒΙΒΛΙΟ ΣΥΝΤΑΓΩΝ</h2>
                <p>Σύνολο Συνταγών: {len(df_rec)}</p>
            </div>
        """

        for _, recipe in df_rec.iterrows():
            name = recipe.get("Ονομα", "Χωρίς Όνομα")
            bc = recipe.get("Barcode", "-")
            
            html_book += f"""
            <div class='recipe-card'>
                <div class='recipe-header'>
                    <h2 class='recipe-name'>{name}</h2>
                    <span class='barcode-label'>Shop ID: {bc}</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Συστατικό Συνταγής</th>
                            <th>Ποσότητα (ml)</th>
                            <th>Βάρος (g)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            r_total_ml = 0
            r_total_alc = 0
            r_total_weight = 0  # Νέος αθροιστής για το βιβλίο
            r_found_ing = 0
            
            for i in range(1, 14):
                raw_ing = str(recipe.get(f"ΣΥΣΤΑΤΙΚΟ{i}", ""))
                try:
                    ml_str = str(recipe.get(f"ML{i}", 0)).replace(',', '.')
                    ml = float(ml_str)
                except:
                    ml = 0
                
                ing_clean = raw_ing.strip()
                ing_check = ing_clean.upper()
                
                if ing_clean and ing_check not in ["NAN", "ΚΕΝΟ", "ΚΕΝΟ.", "-", "NONE", "0", "NULL"] and ml > 0:
                    
                    # --- Υπολογισμός Βάρους για το Βιβλίο ---
                    ing_weight = ml
                    if ing_clean == "Νερό":
                        ing_weight = ml
                    elif not df_ing.empty and ing_clean in df_ing["Name"].values:
                        ing_row = df_ing[df_ing["Name"] == ing_clean].iloc[0]
                        pkg_weight = float(ing_row.get("weight_full", 0) or 0)
                        pkg_volume = float(ing_row.get("Volume", 0) or 0)
                        if pkg_volume > 0 and pkg_weight > 0:
                            ing_weight = (pkg_weight / pkg_volume) * ml
                    
                    html_book += f"<tr><td class='ing-name'>{ing_clean}</td><td>{ml:.2f} ml</td><td>{ing_weight:.1f} g</td></tr>"
                    r_found_ing += 1
                    r_total_ml += ml
                    r_total_weight += ing_weight
                    
                    if not df_ing.empty and ing_clean in df_ing["Name"].values:
                        ing_row = df_ing[df_ing["Name"] == ing_clean].iloc[0]
                        try:
                            raw_abv = str(ing_row.get("ABV", ing_row.get("Αλκοόλ", 0)))
                            clean_abv = raw_abv.replace(',', '.').replace('%', '').strip()
                            abv = float(clean_abv)
                            if 0 < abv <= 1.0:
                                abv = abv * 100
                        except:
                            abv = 0
                        r_total_alc += ml * (abv / 100)
            
            if r_found_ing == 0:
                html_book += "<tr><td colspan='3'><i>Δεν έχουν καταχωρηθεί συστατικά.</i></td></tr>"

            r_final_abv = (r_total_alc / r_total_ml * 100) if r_total_ml > 0 else 0
            r_sugg_price = float(str(recipe.get("Τιμή Καταλόγου", 0.0)).replace(',', '.'))

            html_book += f"""
                    </tbody>
                </table>
                <div class='analysis-box'>
                    <span style='font-size:16px;'>Αλκοόλ (ABV): <b>{r_final_abv:.2f}%</b></span> | 
                    <span style='font-size:16px;'>Συνολικό Βάρος: <b>{r_total_weight:.1f} g</b></span>
                    <span style='float:right; font-size:18px; color:#b38f00;'>Προτεινόμενη Λιανική: <b>{r_sugg_price:.2f} €</b></span>
                </div>
            </div>
            """
        html_book += f"""
            <div class='footer'>
                Αυτόματη εξαγωγή από το σύστημα διαχείρισης CABCLUB: {datetime.now(greece_tz).strftime('%d/%m/%Y %H:%M')}
            </div>
        </body>
        </html>
        """

        st.download_button(
            label="📑 Λήψη Κίτρινου Βιβλίου Συνταγών (με Logo)",
            data=html_book,
            file_name=f"Recipe_Book_Yellow_{datetime.now(greece_tz).strftime('%d_%m_%Y')}.html",
            mime="text/html",
            use_container_width=True
        )
# --- 6. ΕΜΠΟΡΙΚΗ ΠΟΛΙΤΙΚΗ (COMPLETE PRO VERSION WITH GLOSSARY) ---
elif page == "📊 Εμπορική Πολιτική":
    st.header("📊 Εμπορική Πολιτική & Σύγκριση Σεναρίων")
    st.write("Συγκρίνετε τη στρατηγική Δώρων έναντι της Έκπτωσης % και δείτε την ανάλυση κερδοφορίας.")

    if not df_rec.empty:
        # 1. Επιλογή Cocktail & Υπολογισμός Κόστους
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]

        raw_cost = 0.0
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
            ml = float(r.get(f"ML{i}", 0))
            if ing_n not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty:
                    raw_cost += ml * float(match.iloc[0]["Τιμή/ml"])
        
        unit_cost = raw_cost + TOTAL_FIXED
        p_retail = float(r["Τιμή Καταλόγου"])
        p_agent_base = p_retail * 0.74  # Κανονική τιμή προ προσφορών (Αντιπροσώπου)
        
        st.divider()
        
        # --- ΝΕΟ: ΔΥΝΑΜΙΚΟ ΦΙΛΤΡΟ ΤΙΜΟΛΟΓΙΑΚΗΣ ΒΑΣΗΣ ---
        price_target = st.radio(
            "🏷️ Επιλογή Τιμολογιακής Βάσης για τη Σύγκριση:", 
            options=["Τιμή Αντιπροσώπου (Χονδρική)", "Τιμή Λιανικής (Κατάλογος)"],
            horizontal=True,
            key="commercial_policy_price_filter"
        )
        
        # Ορισμός της ενεργής τιμής με βάση το φίλτρο
        if price_target == "Τιμή Λιανικής (Κατάλογος)":
            active_base_price = p_retail
            price_label_text = "Κανονική Τιμή Λιανικής"
        else:
            active_base_price = p_agent_base
            price_label_text = "Κανονική Τιμή Αντιπρ."
            
        normal_profit_per_unit = active_base_price - unit_cost
        # ------------------------------------------------

        st.divider()

        # 2. Είσοδος Δεδομένων (Ξεκινάνε από 0)
        col_in_a, col_in_b = st.columns(2)

        with col_in_a:
            st.subheader("Σενάριο Α: Δώρα (Free Goods)")
            sA_paid = st.number_input("Τεμάχια προς Πώληση (Paid)", min_value=0, value=0, key="sa_paid")
            sA_free = st.number_input("Τεμάχια Δώρο (Free)", min_value=0, value=0, key="sa_free")
            
            sA_total_units = sA_paid + sA_free
            sA_revenue = sA_paid * active_base_price # Υπολογισμός με τη δυναμική τιμή
            sA_cost = sA_total_units * unit_cost
            sA_profit = sA_revenue - sA_cost
            sA_effective = sA_revenue / sA_total_units if sA_total_units > 0 else 0
            sA_margin = (sA_profit / sA_revenue * 100) if sA_revenue > 0 else 0
            sA_markup = (sA_profit / sA_cost * 100) if sA_cost > 0 else 0
            sA_loss = (normal_profit_per_unit * sA_total_units) - sA_profit if sA_total_units > 0 else 0

        with col_in_b:
            st.subheader("Σενάριο Β: Έκπτωση επί της Τιμής")
            sB_total_units = st.number_input("Συνολικά Τεμάχια (Β)", min_value=0, value=0, key="sb_total")
            sB_discount = st.number_input("Ποσοστό Έκπτωσης %", min_value=0.0, value=0.0, key="sb_disc")
            
            sB_price_per_unit = active_base_price * (1 - sB_discount/100) # Υπολογισμός με τη δυναμική τιμή
            sB_revenue = sB_total_units * sB_price_per_unit
            sB_cost = sB_total_units * unit_cost
            sB_profit = sB_revenue - sB_cost
            sB_effective = sB_price_per_unit
            sB_margin = (sB_profit / sB_revenue * 100) if sB_revenue > 0 else 0
            sB_markup = (sB_profit / sB_cost * 100) if sB_cost > 0 else 0
            sB_loss = (normal_profit_per_unit * sB_total_units) - sB_profit if sB_total_units > 0 else 0

        # 3. Εμφάνιση Επαγγελματικού Πίνακα
        if sA_total_units > 0 or sB_total_units > 0:
            st.divider()
            
            winner_text = "ΣΕΝΑΡΙΟ Α" if sA_profit > sB_profit else "ΣΕΝΑΡΙΟ Β"
            diff_val = abs(sA_profit - sB_profit)

            # Σχεδιασμός Πίνακα (HTML format)
            html_table = """
            <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #444;">
                <table style="width: 100%; border-collapse: collapse; color: white; font-family: sans-serif;">
                    <tr style="background-color: #1a3a5f;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #444;">ΠΕΡΙΓΡΑΦΗ ΑΝΑΛΥΣΗΣ</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #444;">ΣΕΝΑΡΙΟ Α</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #444;">ΣΕΝΑΡΙΟ Β</th>
                    </tr>
                    <tr style="background-color: #333; font-weight: bold;">
                        <td colspan="3" style="padding: 10px; border: 1px solid #444;">ΟΙΚΟΝΟΜΙΚΑ ΜΕΓΕΘΗ</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">{15}</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{0:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{0:.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Effective Τιμή/Τμχ</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{1:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{2:.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Συνολικά Έσοδα</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{3:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{4:.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Συνολικό Κόστος</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{5:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{6:.2f} €</td>
                    </tr>
                    <tr style="font-weight: bold; background-color: #222;">
                        <td style="padding: 10px; border: 1px solid #444;">ΚΑΘΑΡΟ ΚΕΡΔΟΣ</td>
                        <td style="text-align:center; color: #4caf50; font-size: 1.2em; border: 1px solid #444;">{7:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; font-size: 1.2em; border: 1px solid #444;">{8:.2f} €</td>
                    </tr>
                    <tr style="background-color: #333; font-weight: bold;">
                        <td colspan="3" style="padding: 10px; border: 1px solid #444;">ΔΕΙΚΤΕΣ</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Margin %</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{9:.1f}%</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{10:.1f}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Markup %</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{11:.1f}%</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{12:.1f}%</td>
                    </tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background-color: #1b5e20; border-radius: 8px; text-align: center; color: white;">
                    <h2 style="margin:0;">🏆 ΝΙΚΗΤΗΣ: {13}</h2>
                    <p style="margin:5px 0 0 0;">Επιπλέον κέρδος: <b>{14:.2f} €</b></p>
                </div>
            </div>
            """.format(
                active_base_price, sA_effective, sB_effective, 
                sA_revenue, sB_revenue, sA_cost, sB_cost, 
                sA_profit, sB_profit, sA_margin, sB_margin, 
                sA_markup, sB_markup, winner_text, diff_val, price_label_text
            )
            
            st.markdown(html_table, unsafe_allow_html=True)

            # --- ΝΕΟ: ΕΠΕΞΗΓΗΣΗ ΟΙΚΟΝΟΜΙΚΩΝ ΟΡΩΝ ---
            with st.expander("ℹ️ Ερμηνεία Οικονομικών Όρων & Δεικτών"):
                st.info("""
                * **Effective Τιμή:** Η πραγματική τιμή που εισπράττει η εταιρεία ανά μονάδα προϊόντος, αφού υπολογιστούν τα δώρα ή οι εκπτώσεις.
                * **Margin (Περιθώριο Κέρδους %):** Το ποσοστό του τζίρου που παραμένει ως κέρδος. Υπολογίζεται ως: `(Κέρδος / Έσοδα) * 100`.
                * **Markup (Ποσοστό Επιβάρυνσης %):** Το ποσοστό πάνω στο κόστος παραγωγής που προστίθεται για να προκύψει η τιμή πώλησης. Υπολογίζεται ως: `(Κέρδος / Κόστος) * 100`.
                * **Κόστος Εμπορικής Ενέργειας:** Το "διαφυγόν κέρδος". Πόσα χρήματα επενδύει η εταιρεία στην προσφορά σε σχέση με την κανονική τιμή πώλησης.
                """)
            
            st.divider()
            
            # 5. ΥΠΕΡ-ΑΝΑΛΥΤΙΚΟ ΕΠΑΓΓΕΛΜΑΤΙΚΟ REPORT
            if st.button("💾 Λήψη Πλήρους Φακέλου Ανάλυσης (Full Audit Report)"):
                now_str = datetime.now(greece_tz).strftime("%d/%m/%Y %H:%M")
                
                # Υπολογισμός Έμμεσης Έκπτωσης για το Σενάριο Α βάσει της ενεργής τιμής
                sA_indirect_disc = ((1 - sA_effective/active_base_price)*100) if active_base_price > 0 else 0
                
                full_audit_data = [
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ ΣΥΜΦΩΝΙΑΣ", "ΣΤΟΙΧΕΙΟ": "Cocktail / Προϊόν", "ΣΕΝΑΡΙΟ Α": choice, "ΣΕΝΑΡΙΟ Β": choice},
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ ΣΥΜΦΩΝΙΑΣ", "ΣΤΟΙΧΕΙΟ": "Ημερομηνία & Ώρα", "ΣΕΝΑΡΙΟ Α": now_str, "ΣΕΝΑΡΙΟ Β": ""},
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ ΣΥΜΦΩΝΙΑΣ", "ΣΤΟΙΧΕΙΟ": "Υπεύθυνος Ανάλυσης", "ΣΕΝΑΡΙΟ Α": "DC CABCLUB System", "ΣΕΝΑΡΙΟ Β": ""},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},
                    
                    {"ΚΑΤΗΓΟΡΙΑ": "2. ΤΙΜΟΛΟΓΙΑΚΗ ΒΑΣΗ", "ΣΤΟΙΧΕΙΟ": "Ενεργή Βάση Σύγκρισης", "ΣΕΝΑΡΙΟ Α": price_label_text, "ΣΕΝΑΡΙΟ Β": price_label_text},
                    {"ΚΑΤΗΓΟΡΙΑ": "2. ΤΙΜΟΛΟΓΙΑΚΗ ΒΑΣΗ", "ΣΤΟΙΧΕΙΟ": "Κανονική Τιμή (Gross)", "ΣΕΝΑΡΙΟ Α": f"{active_base_price:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{active_base_price:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "2. ΤΙΜΟΛΟΓΙΑΚΗ ΒΑΣΗ", "ΣΤΟΙΧΕΙΟ": "Πραγματική Τιμή Μονάδας (Net)", "ΣΕΝΑΡΙΟ Α": f"{sA_effective:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_effective:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "3. ΑΝΑΛΥΣΗ ΟΓΚΩΝ (UNITS)", "ΣΤΟΙΧΕΙΟ": "Τεμάχια προς Τιμολόγηση", "ΣΕΝΑΡΙΟ Α": f"{sA_paid} τμχ", "ΣΕΝΑΡΙΟ Β": f"{sB_total_units} τμχ"},
                    {"ΚΑΤΗΓΟΡΙΑ": "3. ΑΝΑΛΥΣΗ ΟΓΚΩΝ (UNITS)", "ΣΤΟΙΧΕΙΟ": "Δωρεάν Τεμάχια (Free Goods)", "ΣΕΝΑΡΙΟ Α": f"{sA_free} τμχ", "ΣΕΝΑΡΙΟ Β": "0 τμχ"},
                    {"ΚΑΤΗΓΟΡΙΑ": "3. ΑΝΑΛΥΣΗ ΟΓΚΩΝ (UNITS)", "ΣΤΟΙΧΕΙΟ": "Συνολικό Stock που θα φύγει", "ΣΕΝΑΡΙΟ Α": f"{sA_total_units} τμχ", "ΣΕΝΑΡΙΟ Β": f"{sB_total_units} τμχ"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Συνολικά Έσοδα (Revenue)", "ΣΕΝΑΡΙΟ Α": f"{sA_revenue:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_revenue:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Συνολικό Κόστος Παραγωγής (COGS)", "ΣΕΝΑΡΙΟ Α": f"{sA_cost:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_cost:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Μικτό Κέρδος (Gross Profit)", "ΣΕΝΑΡΙΟ Α": f"{sA_profit:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_profit:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Κόστος Εμπορικής Ενέργειας", "ΣΕΝΑΡΙΟ Α": f"{sA_loss:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_loss:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "5. KPIs & PERFORMANCE", "ΣΤΟΙΧΕΙΟ": "Margin % (Επί του Τζίρου)", "ΣΕΝΑΡΙΟ Α": f"{sA_margin:.2f}%", "ΣΕΝΑΡΙΟ Β": f"{sB_margin:.2f}%"},
                    {"ΚΑΤΗΓΟΡΙΑ": "5. KPIs & PERFORMANCE", "ΣΤΟΙΧΕΙΟ": "Markup % (Επί του Κόστους)", "ΣΕΝΑΡΙΟ Α": f"{sA_markup:.2f}%", "ΣΕΝΑΡΙΟ Β": f"{sB_markup:.2f}%"},
                    {"ΚΑΤΗΓΟΡΙΑ": "5. KPIs & PERFORMANCE", "ΣΤΟΙΧΕΙΟ": "Ποσοστό Έκπτωσης (Direct/Indirect)", "ΣΕΝΑΡΙΟ Α": f"{sA_indirect_disc:.1f}%", "ΣΕΝΑΡΙΟ Β": f"{sB_discount:.1f}%"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "Κερδοφορία ανά τμχ (Net)", "ΣΕΝΑΡΙΟ Α": f"{(sA_profit/sA_total_units):.2f} €", "ΣΕΝΑΡΙΟ Β": f"{(sB_profit/sB_total_units):.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "Διαφορά Κέρδους Συμφωνίας", "ΣΕΝΑΡΙΟ Α": f"{diff_val:.2f} €" if sA_profit > sB_profit else "-", "ΣΕΝΑΡΙΟ Β": f"{diff_val:.2f} €" if sB_profit > sA_profit else "-"},
                    {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "ΚΑΤΑΣΤΑΣΗ ΕΓΚΡΙΣΗΣ", "ΣΕΝΑΡΙΟ Α": "ΕΠΙΛΟΓΗ" if sA_profit > sB_profit else "-", "ΣΕΝΑΡΙΟ Β": "ΕΠΙΛΟΓΗ" if sB_profit > sA_profit else "-"}
                ]
                
                df_rep = pd.DataFrame(full_audit_data)
                csv = df_rep.to_csv(index=False, sep=';', encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Λήψη Πλήρους Φακέλου (CSV)", 
                    data=csv, 
                    file_name=f"Full_Audit_Report_{choice}.csv",
                    mime="text/csv"
                )
            
# --- 7. DASHBOARD (ΠΛΗΡΗΣ ΟΙΚΟΝΟΜΙΚΗ ΕΙΚΟΝΑ - ΤΕΛΙΚΗ ΕΚΔΟΣΗ ΜΕ ΔΙΑΔΟΧΙΚΕΣ ΕΚΠΤΩΣΕΙΣ) ---
elif page == "📈 Dashboard":
    st.header("📈 Business Analytics & Πωλήσεις")
    
    import plotly.express as px
    import pandas as pd
    import time

    # 1. ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ
    @st.cache_data(ttl=300) 
    def load_dashboard_data():
        log = supabase.table("production_log").select("*").execute().data
        orders = supabase.table("b2b_orders").select("*").execute().data
        rec = supabase.table("recipes").select("id, name, catalog_price").execute().data
        ing = supabase.table("ingredients").select("name, price, volume").execute().data
        items = supabase.table("recipe_items").select("recipe_id, ingredient_name, ml_per_unit").execute().data
        cust = supabase.table("customers").select("*").execute().data
        return log, orders, rec, ing, items, cust
    
    with st.spinner("Ενημέρωση στατιστικών..."):
        log_data, orders_data, rec_data, ing_data, items_data, cust_data = load_dashboard_data()
        
        class DummyRes: pass
        res_log, res_orders, res_rec, res_ing, res_items, res_cust = [DummyRes() for _ in range(6)]
        res_log.data, res_orders.data, res_rec.data, res_ing.data, res_items.data, res_cust.data = log_data, orders_data, rec_data, ing_data, items_data, cust_data
        
    if res_log.data and res_rec.data:
        df_raw = pd.DataFrame(res_log.data)
        df_recipes = pd.DataFrame(res_rec.data)
        df_customers = pd.DataFrame(res_cust.data) if res_cust.data else pd.DataFrame()
        df_orders_raw = pd.DataFrame(res_orders.data) if res_orders.data else pd.DataFrame()
        
        # --- ΚΑΘΑΡΙΣΜΟΣ & ΠΡΟΕΤΟΙΜΑΣΙΑ ΔΕΔΟΜΕΝΩΝ ---
        if not df_customers.empty:
            df_customers['name'] = df_customers.get('name', '').astype(str).str.strip()
            df_customers['discount'] = pd.to_numeric(df_customers.get('discount', 0), errors='coerce').fillna(0)
        else:
            df_customers = pd.DataFrame({'name': [], 'discount': []})

        df_sales = df_raw.drop_duplicates(subset=["prod_date", "prod_time", "customer", "cocktail_name", "lot_cocktail"]).copy()
        if 'customer' in df_sales.columns:
            df_sales['customer'] = df_sales['customer'].astype(str).str.strip()
        df_sales['Date_Obj'] = pd.to_datetime(df_sales.get('prod_date'), format='%d/%m/%Y', errors='coerce')
        df_sales['Month_Year'] = df_sales['Date_Obj'].dt.strftime('%m/%Y')

        if not df_orders_raw.empty:
            df_orders_raw['Date_Obj'] = pd.to_datetime(df_orders_raw.get('created_at'), errors='coerce')
            df_orders_raw['Month_Year'] = df_orders_raw['Date_Obj'].dt.strftime('%m/%Y')
            df_orders_raw['Date_Str'] = df_orders_raw['Date_Obj'].dt.strftime('%d/%m/%Y')
            df_orders_raw['total_amount'] = pd.to_numeric(df_orders_raw.get('total_amount', 0), errors='coerce').fillna(0)
        else:
            df_orders_raw = pd.DataFrame(columns=['customer_name', 'Month_Year', 'Date_Str', 'total_amount', 'order_details'])

        # --- ΦΙΛΤΡΑ ---
        st.markdown("### 🎯 Φίλτρα Ανάλυσης")
        col_f1, col_f2 = st.columns(2)
        all_customers = ["ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ"] + sorted(df_sales['customer'].dropna().unique().tolist())
        sel_customer = col_f1.selectbox("👤 Πελάτης:", options=all_customers)
        all_months = ["ΟΛΟΙ ΟΙ ΜΗΝΕΣ"] + sorted(df_sales['Month_Year'].dropna().unique().tolist(), reverse=True)
        sel_month = col_f2.selectbox("📅 Μήνας:", options=all_months)
        
        df_filtered = df_sales.copy()
        df_orders = df_orders_raw.copy()
        
        if sel_customer != "ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ":
            df_filtered = df_filtered[df_filtered['customer'] == sel_customer]
            if not df_orders.empty:
                df_orders = df_orders[df_orders['customer_name'] == sel_customer]
        if sel_month != "ΟΛΟΙ ΟΙ ΜΗΝΕΣ":
            df_filtered = df_filtered[df_filtered['Month_Year'] == sel_month]
            if not df_orders.empty:
                df_orders = df_orders[df_orders['Month_Year'] == sel_month]

        # --- ΥΠΟΛΟΓΙΣΜΟΣ ΚΟΣΤΟΥΣ ΥΛΙΚΩΝ ---
        FIXED_COST = 0.22 
        
        df_ing = pd.DataFrame(res_ing.data)
        df_ing['cost_per_ml'] = pd.to_numeric(df_ing.get('price', 0), errors='coerce') / pd.to_numeric(df_ing.get('volume', 1), errors='coerce')
        ing_cost_dict = dict(zip(df_ing['name'], df_ing['cost_per_ml']))
        
        df_items = pd.DataFrame(res_items.data)
        recipe_costs_by_id = {}
        for rid in df_items['recipe_id'].unique():
            sub = df_items[df_items['recipe_id'] == rid]
            mat_cost = sum(pd.to_numeric(item.get('ml_per_unit', 0), errors='coerce') * ing_cost_dict.get(item.get('ingredient_name'), 0) for _, item in sub.iterrows())
            recipe_costs_by_id[rid] = mat_cost + FIXED_COST
            
        name_to_cost = {r['name']: recipe_costs_by_id.get(r['id'], FIXED_COST) for _, r in df_recipes.iterrows()}

        # =========================================================================
        # 🚀 ΑΠΟΛΥΤΑ ΑΣΦΑΛΗΣ ΥΠΟΛΟΓΙΣΜΟΣ ΕΣΟΔΩΝ (ΔΙΑΔΟΧΙΚΕΣ ΕΚΠΤΩΣΕΙΣ)
        # =========================================================================
        recipe_price_dict = dict(zip(df_recipes['name'], pd.to_numeric(df_recipes.get('catalog_price', 0), errors='coerce')))
        cust_discount_dict = dict(zip(df_customers['name'], df_customers['discount']))

        # 1. Ανάγνωση βασικών τιμών
        df_filtered['catalog_price'] = df_filtered['cocktail_name'].map(recipe_price_dict).fillna(0)
        df_filtered['global_discount'] = df_filtered['customer'].map(cust_discount_dict).fillna(0)
        
        # 2. Ανάγνωση ποσοτήτων (Όλων των ειδών)
        df_filtered['t_pcs'] = pd.to_numeric(df_filtered.get('pieces', 0), errors='coerce').fillna(0)
        df_filtered['f_pcs'] = pd.to_numeric(df_filtered.get('free_pieces', 0), errors='coerce').fillna(0)
        df_filtered['s_pcs'] = pd.to_numeric(df_filtered.get('discounted_pieces', 0), errors='coerce').fillna(0)
        df_filtered['s_pct'] = pd.to_numeric(df_filtered.get('discount_pct', 0), errors='coerce').fillna(0)

        # 3. Ασφαλής διαχωρισμός τεμαχίων
        df_filtered['s_pcs'] = df_filtered.apply(lambda r: min(r['s_pcs'], max(0, r['t_pcs'] - r['f_pcs'])), axis=1)
        df_filtered['normal_pcs'] = df_filtered['t_pcs'] - df_filtered['f_pcs'] - df_filtered['s_pcs']

        # 4. Υπολογισμός Εσόδων (Ακριβώς όπως στο Πελατολόγιο)
        # -> Τιμή ΜΕΤΑ τη Γενική Έκπτωση του Πελάτη (π.χ. τα 4.50€)
        df_filtered['price_after_global'] = df_filtered['catalog_price'] * (1 - (df_filtered['global_discount'] / 100))
        
        # -> Έσοδα Κανονικών Τεμαχίων (Απλά πολλαπλασιάζουμε με την price_after_global)
        df_filtered['rev_normal'] = df_filtered['normal_pcs'] * df_filtered['price_after_global']
        
        # -> Έσοδα Ειδικών Τεμαχίων (Αφαιρούμε διαδοχικά ΚΑΙ την ειδική έκπτωση πάνω στην price_after_global)
        df_filtered['rev_special'] = df_filtered['s_pcs'] * df_filtered['price_after_global'] * (1 - (df_filtered['s_pct'] / 100))

        # Συνολικά Έσοδα Γραμμής
        df_filtered['Theoretical_Revenue'] = df_filtered['rev_normal'] + df_filtered['rev_special']
        df_filtered['Theoretical_Revenue'] = df_filtered['Theoretical_Revenue'].clip(lower=0)
        
        # Συνολικό Κόστος & Κέρδος
        df_filtered['Final_Unit_Cost'] = df_filtered['cocktail_name'].map(name_to_cost).fillna(FIXED_COST)
        df_filtered['Total_Cost'] = df_filtered['t_pcs'] * df_filtered['Final_Unit_Cost']
        df_filtered['Profit'] = df_filtered['Theoretical_Revenue'] - df_filtered['Total_Cost']

        # --- ΣΥΓΧΡΟΝΙΣΜΟΣ ΔΕΔΟΜΕΝΩΝ ΓΙΑ METRICS & ΓΡΑΦΗΜΑΤΑ ---
        total_rev = df_filtered['Theoretical_Revenue'].sum()
        total_cost = df_filtered['Total_Cost'].sum()
        total_profit = df_filtered['Profit'].sum()
        total_units = df_filtered['t_pcs'].sum()
        total_orders_count = df_filtered.groupby(['prod_date', 'customer']).ngroups

        df_mom_grouped = df_filtered.groupby(['customer', 'Month_Year'])['Theoretical_Revenue'].sum().reset_index()
        df_mom_grouped.rename(columns={'Theoretical_Revenue': 'Revenue', 'Month_Year': 'Month'}, inplace=True)

        # --- METRICS ΣΥΝΟΨΗΣ ---
        st.divider()
        st.subheader(f"📊 Σύνοψη & Απόδοση: {sel_customer if sel_customer != 'ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ' else 'Όλοι οι Πελάτες'}")
        
        margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
        aov = total_rev / total_orders_count if total_orders_count > 0 else 0
        
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("💰 Τζίρος", f"{format_gr(total_rev)} €")
        m2.metric("📈 Καθαρό Κέρδος", f"{format_gr(total_profit)} €", delta=f"{margin:.1f}% Margin")
        m3.metric("📉 Κόστος Υλικών", f"{format_gr(total_cost)} €")
        m4.metric("🍹 Τεμάχια", f"{format_gr(int(total_units), decimals=0)} τμχ")
        m5.metric("📦 Παραγγελίες", format_gr(total_orders_count, decimals=0))
        m6.metric("⚖️ Μέση Αξία", f"{format_gr(aov)} €")

        # --- 🕵️‍♂️ ΕΡΓΑΛΕΙΟ ΕΛΕΓΧΟΥ (ΝΕΟ AUDIT TOOL) ---
        with st.expander("🕵️‍♂️ ΕΡΓΑΛΕΙΟ ΕΛΕΓΧΟΥ: Ακτινογραφία Υπολογισμών (Κάντε κλικ)"):
            st.info("💡 Ελέγξτε πώς εφαρμόζονται οι διαδοχικές εκπτώσεις σας στην τελευταία παραγωγή.")
            if not df_filtered.empty:
                s = df_filtered.iloc[0]
                col_aud1, col_aud2, col_aud3 = st.columns(3)
                
                with col_aud1:
                    st.markdown("### 1️⃣ Υπολογισμός Εσόδων")
                    st.write(f"**Σύνολο:** {s['t_pcs']} τμχ | **Τιμή Καταλόγου:** {s['catalog_price']:.2f}€")
                    st.write(f"**Τιμή (μετά τη Γενική Έκπτωση {s['global_discount']}%):** {s['price_after_global']:.2f}€")
                    st.caption("---")
                    st.write(f"**Κανονικά:** {s['normal_pcs']} τμχ  (↪ Αξία: {s['rev_normal']:.2f}€)")
                    st.write(f"**Ειδικά:** {s['s_pcs']} τμχ *(Extra {s['s_pct']}% -> Τιμή: {s['price_after_global'] * (1 - s['s_pct']/100):.2f}€)* (↪ Αξία: {s['rev_special']:.2f}€)")
                    st.write(f"**Δωρεάν:** {s['f_pcs']} τμχ")
                    st.success(f"💰 Συνολικά Έσοδα = **{s['Theoretical_Revenue']:.2f}€**")

                with col_aud2:
                    st.markdown("### 2️⃣ Υπολογισμός Κόστους")
                    st.write(f"- **Κόστος Υλικών:** {s['Final_Unit_Cost'] - FIXED_COST:.4f}€")
                    st.write(f"- **Σταθερά Έξοδα:** {FIXED_COST:.2f}€")
                    st.markdown(f"- **Κόστος ανά τμχ: {s['Final_Unit_Cost']:.4f}€**")
                    st.caption("---")
                    st.write(f"- Παράχθηκαν: {s['t_pcs']} τμχ (πληρώνονται και τα δωρεάν)")
                    st.error(f"📉 Κόστος = {s['t_pcs']} x {s['Final_Unit_Cost']:.4f}€ = **{s['Total_Cost']:.2f}€**")

                with col_aud3:
                    st.markdown("### 3️⃣ Υπολογισμός Κέρδους")
                    st.write(f"**Έσοδα:** {s['Theoretical_Revenue']:.2f}€")
                    st.write(f"**Μείον Κόστος:** -{s['Total_Cost']:.2f}€")
                    st.caption("---")
                    st.info(f"📈 Καθαρό Κέρδος: **{s['Profit']:.2f}€**")
                    margin_perc = (s['Profit'] / s['Theoretical_Revenue'] * 100) if s['Theoretical_Revenue'] > 0 else 0
                    st.markdown(f"### Margin: {margin_perc:.1f}%")
            else:
                st.write("Δεν υπάρχουν δεδομένα.")

        # --- ΓΡΑΦΗΜΑ MoM GROWTH ---
        st.write("### 📅 Μηνιαία Εξέλιξη Τζίρου")
        if not df_mom_grouped.empty:
            mom_trend = df_mom_grouped.groupby('Month')['Revenue'].sum().reset_index()
            mom_trend['sort_date'] = pd.to_datetime(mom_trend['Month'], format='%m/%Y')
            mom_trend = mom_trend.sort_values('sort_date')
            fig_mom = px.line(mom_trend, x='Month', y='Revenue', 
                             markers=True, text=[f"{format_gr(v, decimals=0)}€" for v in mom_trend['Revenue']],
                             title="Πορεία Εσόδων (Month-over-Month)",
                             template="plotly_dark", color_discrete_sequence=["#00ffcc"])
            fig_mom.update_traces(textposition="top center")
            st.plotly_chart(fig_mom, use_container_width=True)

        # --- ABC ΑΝΑΛΥΣΗ ---
        st.divider()
        st.subheader("🏆 ABC Ανάλυση Πελατολογίου")
        if not df_mom_grouped.empty and total_rev > 0:
            customer_abc = df_mom_grouped.groupby("customer")["Revenue"].sum().sort_values(ascending=False).reset_index()
            customer_abc['Percentage'] = (customer_abc['Revenue'] / total_rev) * 100
            customer_abc['CumSum'] = customer_abc['Percentage'].cumsum()
            customer_abc['Category'] = customer_abc['CumSum'].apply(lambda x: "A" if x <= 80 else ("B" if x <= 95 else "C"))
            fig_abc = px.bar(customer_abc, x="customer", y="Revenue", color="Category", title="Ranking Πελατών", text_auto='.2s', color_discrete_map={"A": "#00ffcc", "B": "#f1c40f", "C": "#ff4b4b"})
            st.plotly_chart(fig_abc, use_container_width=True)

        # --- ΑΝΑΛΥΣΗ COCKTAIL MIX ---
        st.divider()
        st.subheader("🍸 Ανάλυση Cocktail Mix ανά Πελάτη")
        if not df_filtered.empty:
            mix_data = df_filtered.groupby(['customer', 'cocktail_name'])['t_pcs'].sum().reset_index()
            fig_mix = px.bar(mix_data, x="customer", y="t_pcs", color="cocktail_name",
                             title="Ποσοστιαία Αναλογία Προϊόντων ανά Πελάτη",
                             labels={"t_pcs": "Τεμάχια", "customer": "Πελάτης"},
                             template="plotly_dark", barmode="relative")
            fig_mix.update_layout(xaxis={'categoryorder':'total descending'})
            st.plotly_chart(fig_mix, use_container_width=True)

        # --- ΧΑΡΤΗΣ ΑΠΟΔΟΣΗΣ ---
        st.divider()
        st.subheader("🎯 Χάρτης Απόδοσης Cocktail")
        heatmap_list = []
        for name in df_filtered['cocktail_name'].unique():
            temp = df_filtered[df_filtered['cocktail_name'] == name]
            
            total_pieces = temp['t_pcs'].sum()
            paid_pieces = total_pieces - temp['f_pcs'].sum()
            
            total_prof = temp['Profit'].sum()
            unit_profit = total_prof / paid_pieces if paid_pieces > 0 else 0
            
            if total_pieces > 0:
                heatmap_list.append({
                    "Cocktail": name, 
                    "Πωλήσεις (Σύνολο)": total_pieces,
                    "Πωλήσεις (Πληρωμένα)": paid_pieces,
                    "Κέρδος/Τμχ": round(unit_profit, 2), 
                    "Συνολικό Κέρδος": round(total_prof, 2)
                })
        
        if heatmap_list:
            df_hm = pd.DataFrame(heatmap_list)
            fig_hm = px.scatter(
                df_hm, x="Πωλήσεις (Σύνολο)", y="Κέρδος/Τμχ", size="Συνολικό Κέρδος", 
                color="Cocktail", hover_name="Cocktail", text="Cocktail", size_max=50, 
                template="plotly_dark",
                labels={"Κέρδος/Τμχ": "Καθαρό Κέρδος 1 Τεμαχίου (€)", "Πωλήσεις (Σύνολο)": "Συνολικός Όγκος (τμχ)"}
            )
            fig_hm.update_traces(textposition='top center')
            min_margin = df_hm["Κέρδος/Τμχ"].min()
            fig_hm.update_layout(yaxis=dict(range=[min_margin - 0.5, df_hm["Κέρδος/Τμχ"].max() + 1.0]))
            st.plotly_chart(fig_hm, use_container_width=True)

        # =====================================================================
        # 🎁 ΔΥΝΑΜΙΚΗ ΑΝΑΛΥΣΗ ΠΡΟΣΦΟΡΩΝ 240+24
        # =====================================================================
        if not df_orders.empty and 'order_details' in df_orders.columns:
            import re
            df_dash_promos = df_orders[df_orders['order_details'].str.contains("ΠΡΟΣΦΟΡΑ 240", na=False)].copy()
            
            if not df_dash_promos.empty:
                st.divider()
                st.subheader("🎁 Ανάλυση Προωθητικών Ενεργειών (240+24)")
                
                def get_promo_cocktail_dash(detail_str):
                    match = re.search(r"ΠΡΟΣΦΟΡΑ 240\+24 ΔΩΡΟ στο ([^\]\n]+)", str(detail_str))
                    if match: return match.group(1).strip()
                    return "Γενική / Παλιό Μοντέλο"
                
                df_dash_promos['Ημερομηνία'] = pd.to_datetime(df_dash_promos['created_at']).dt.strftime('%d/%m/%Y')
                df_dash_promos['Κοκτέιλ Προσφοράς'] = df_dash_promos['order_details'].apply(get_promo_cocktail_dash)
                
                col_dash_p1, col_dash_p2 = st.columns([1, 3])
                with col_dash_p1:
                    st.metric(label="🎁 Προσφορές στο Φίλτρο", value=f"{len(df_dash_promos)} φορές")
                with col_dash_p2:
                    st.dataframe(df_dash_promos.rename(columns={"customer_name": "ΠΕΛΑΤΗΣ", "total_amount": "ΤΕΛΙΚΗ ΧΡΕΩΣΗ (€)"})[["Ημερομηνία", "ΠΕΛΑΤΗΣ", "Κοκτέιλ Προσφοράς", "ΤΕΛΙΚΗ ΧΡΕΩΣΗ (€)"]], use_container_width=True, hide_index=True)

        # --- ΑΝΑΛΥΤΙΚΟΣ ΠΙΝΑΚΑΣ ---
        with st.expander("📄 Αναλυτικό Αρχείο (LOT & Profit)"):
            display_df = df_filtered.copy()
            display_df.rename(columns={"Theoretical_Revenue": "Revenue"}, inplace=True)
            st.dataframe(display_df[["prod_date", "customer", "cocktail_name", "t_pcs", "Revenue", "Total_Cost", "Profit", "lot_cocktail"]].sort_values("prod_date", ascending=False), use_container_width=True, hide_index=True)

        # =====================================================================
        # 👤 ΑΝΑΛΥΤΙΚΟ REPORT ΠΕΛΑΤΗ 
        # =====================================================================
        st.divider()
        st.header("👤 Αναλυτικό Report ανά Πελάτη")
        
        all_customers_rep = sorted(df_sales['customer'].dropna().unique().tolist()) if not df_sales.empty else []
        
        if all_customers_rep:
            sel_cust_rep = st.selectbox("Επιλέξτε Πελάτη για Ανάλυση:", options=all_customers_rep, key="dash_cust_rep")
            cust_prod = df_filtered[df_filtered['customer'] == sel_cust_rep].copy()
            
            display_revenue = cust_prod['Theoretical_Revenue'].sum()
            total_pcs_cust = cust_prod['t_pcs'].sum()
            avg_val_cust = display_revenue / total_pcs_cust if total_pcs_cust > 0 else 0
            unique_cocktails = cust_prod['cocktail_name'].nunique()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Συνολικά Τεμάχια", f"{format_gr(int(total_pcs_cust), decimals=0)} τμχ")
            c2.metric("Συνολικός Τζίρος", f"{format_gr(display_revenue)} €")
            c3.metric("Μέση Τιμή / Τμχ", f"{format_gr(avg_val_cust)} €")
            c4.metric("Ποικιλία Cocktail", f"{unique_cocktails}")

            cust_orders = df_orders_raw[df_orders_raw['customer_name'] == sel_cust_rep] if not df_orders_raw.empty else pd.DataFrame()
            pdf_fin_data = cust_orders.to_dict('records')
            if not pdf_fin_data and display_revenue > 0:
                pdf_fin_data = [{'created_at': 'Αυτόματος Υπολογισμός', 'order_details': 'Τζίρος βάσει ιστορικού παραγωγής', 'total_amount': display_revenue}]

            try:
                cust_pdf = generate_hybrid_report(sel_cust_rep, pdf_fin_data, cust_prod.to_dict('records'))
                st.download_button(
                    label=f"🖨️ Εκτύπωση Report: {sel_cust_rep}",
                    data=bytes(cust_pdf),
                    file_name=f"Dashboard_Report_{sel_cust_rep}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Σφάλμα προετοιμασίας PDF: {e}")

            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("📈 Πορεία Αγορών (Τεμάχια)")
                if not cust_prod.empty:
                    df_trend = cust_prod.groupby('prod_date')['t_pcs'].sum().reset_index()
                    df_trend['sort_date'] = pd.to_datetime(df_trend['prod_date'], format='%d/%m/%Y', errors='coerce')
                    df_trend = df_trend.sort_values('sort_date')
                    fig_trend = px.line(df_trend, x='prod_date', y='t_pcs', markers=True, line_shape="spline", color_discrete_sequence=["#FF4B4B"])
                    st.plotly_chart(fig_trend, use_container_width=True)

            with col_chart2:
                st.subheader("🍸 Προτιμήσεις Cocktail")
                if not cust_prod.empty:
                    df_fav = cust_prod.groupby('cocktail_name')['t_pcs'].sum().reset_index()
                    fig_fav = px.pie(df_fav, values='t_pcs', names='cocktail_name', hole=0.4)
                    st.plotly_chart(fig_fav, use_container_width=True)

            with st.expander(f"📋 Δείτε όλες τις κινήσεις του {sel_cust_rep}"):
                st.dataframe(cust_prod[['prod_date', 'cocktail_name', 't_pcs', 'lot_cocktail']].sort_values(by='prod_date', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Δεν υπάρχουν ακόμα δεδομένα πελατών για ανάλυση.")

        # =========================================================================
        # 📊 ΔΥΝΑΜΙΚΟ ΓΡΑΦΗΜΑ ΠΩΛΗΣΕΩΝ & ΚΕΡΔΟΦΟΡΙΑΣ ΚΟΚΤΕΙΛ
        # =========================================================================
        st.divider()
        st.markdown("### 📈 Δυναμική Ανάλυση Πωλήσεων Cocktails")

        if df_filtered.empty:
            st.info("Δεν υπάρχουν δεδομένα παραγωγής για το επιλεγμένο φίλτρο.")
        else:
            df_grouped_chart = df_filtered.groupby("cocktail_name").agg(
                Τεμάχια_τμχ=("t_pcs", "sum"),
                Τζίρος_ευρώ=("Theoretical_Revenue", "sum"),
                Συνολικό_Κόστος_ευρώ=("Total_Cost", "sum"),
                Καθαρό_Κέρδος_ευρώ=("Profit", "sum")
            ).reset_index()

            df_grouped_chart.rename(columns={
                "Τεμάχια_τμχ": "Τεμάχια (τμχ)",
                "Τζίρος_ευρώ": "Τζίρος (€)",
                "Συνολικό_Κόστος_ευρώ": "Συνολικό Κόστος (€)",
                "Καθαρό_Κέρδος_ευρώ": "Καθαρό Κέρδος (€)"
            }, inplace=True)
            
            col_metric, col_sort = st.columns([2, 1])
            metrics_list = ["Τεμάχια (τμχ)", "Τζίρος (€)", "Καθαρό Κέρδος (€)", "Συνολικό Κόστος (€)"]
            selected_metric = col_metric.selectbox("🎯 Επιλέξτε Μετρική για Ανάλυση:", metrics_list, key="unique_metric_selector_cocktails")
            sort_order = col_sort.radio("↕️ Ταξινόμηση:", ["Φθίνουσα (Υψηλότερα πρώτα)", "Αύξουσα (Χαμηλότερα πρώτα)"], key="unique_sort_radio_cocktails")
            ascending_bool = True if sort_order == "Αύξουσα (Χαμηλότερα πρώτα)" else False
            
            df_grouped_chart = df_grouped_chart.sort_values(by=selected_metric, ascending=ascending_bool)
            
            fig = px.bar(
                df_grouped_chart, x="cocktail_name", y=selected_metric, text=selected_metric, color=selected_metric,
                color_continuous_scale="Viridis", labels={"cocktail_name": "Ονομασία Κοκτέιλ", selected_metric: selected_metric},
                hover_data=["Τεμάχια (τμχ)", "Τζίρος (€)", "Συνολικό Κόστος (€)", "Καθαρό Κέρδος (€)"]
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45, height=500, margin=dict(t=50, b=100), plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, key="unique_sales_plotly_chart_id")
            
            with st.expander("📋 Προβολή Αναλυτικού Πίνακα Δεδομένων"):
                st.dataframe(
                    df_grouped_chart.style.format({
                        "Τεμάχια (τμχ)": "{:.0f}", "Τζίρος (€)": "{:.2f} €",
                        "Συνολικό Κόστος (€)": "{:.2f} €", "Καθαρό Κέρδος (€)": "{:.2f} €"
                    }), use_container_width=True, hide_index=True
                )

    else:
        st.info("📭 Δεν υπάρχουν επαρκή δεδομένα για το επιλεγμένο φίλτρο.")
       
# --- 8. LOT ΠΑΡΑΓΩΓΗΣ (ΜΕ DROP-DOWN ΠΕΛΑΤΟΛΟΓΙΟ & SMART CART) ---
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής & Ιχνηλασιμότητα")

    # 1. ΦΟΡΤΩΣΗ ΠΕΛΑΤΩΝ ΓΙΑ ΤΟ DROP-DOWN
    try:
        res_cust = supabase.table("customers").select("name").execute()
        customer_options = sorted([c["name"] for c in res_cust.data]) if res_cust.data else []
        if "Λιανική / Άγνωστος" not in customer_options:
            customer_options.insert(0, "Λιανική / Άγνωστος")
    except Exception:
        customer_options = ["Λιανική / Άγνωστος"]

    def get_recipe_ml(row_series, idx):
        raw_val = None
        exact_key = f"ML{idx}"
        if exact_key in row_series:
            raw_val = row_series[exact_key]
        else:
            target = exact_key.lower()
            for col in row_series.index:
                if str(col).lower().replace(" ", "").replace("_", "") == target:
                    raw_val = row_series[col]
                    break
        if raw_val is None or pd.isna(raw_val):
            return 0.0
        try:
            val_str = str(raw_val).replace(',', '.').replace(' ', '')
            return float(val_str) if val_str else 0.0
        except Exception:
            return 0.0

    if 'active_b2b_order' not in st.session_state:
        st.session_state['active_b2b_order'] = None
    if 'lot_reset_key' not in st.session_state:
        st.session_state['lot_reset_key'] = 0

    active_order = st.session_state.get('active_b2b_order')
    reset_key = st.session_state['lot_reset_key']

    # --- ΕΚΚΡΕΜΟΤΗΤΕΣ ΑΠΟ B2B ---
    st.subheader("📋 Εκκρεμείς Παραγγελίες Πελατών (B2B)")
    res_b2b = supabase.table("b2b_orders").select("*").in_("status", ["ΝΕΑ", "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ"]).execute()
    
    if res_b2b.data:
        df_pending = pd.DataFrame(res_b2b.data)
        for _, order in df_pending.iterrows():
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"**Πελάτης:** {order['customer_name']} | **Προϊόντα:** {order['order_details'].replace('•', '')}")
            with col_b:
                if st.button("📥 Φόρτωση", key=f"load_{order['id']}"):
                    st.session_state['active_b2b_order'] = order.to_dict() 
                    st.success(f"Φορτώθηκε η παραγγελία του {order['customer_name']}!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.write("✅ Καμία εκκρεμής παραγγελία.")

    if active_order is not None:
        if st.button("❌ Ακύρωση Φόρτωσης"):
            st.session_state['active_b2b_order'] = None
            st.rerun()

    st.divider()

    # 1. ΚΕΝΤΡΙΚΟΣ ΟΡΙΣΜΟΣ ΗΜΕΡΟΜΗΝΙΑΣ & LOT
    col_date1, col_date2 = st.columns([2, 1])
    with col_date1:
        selected_date = st.date_input("📅 Ημερομηνία LOT", value=datetime.now(greece_tz), format="DD/MM/YYYY")
    with col_date2:
        prod_day = st.text_input("Ημερομηνία Παραγωγής", value=datetime.now(greece_tz).strftime('%d'), max_chars=2)

    formatted_date = selected_date.strftime('%d/%m/%Y')
    date_lot_label = f"{formatted_date}-{prod_day}" 
    current_time = datetime.now(greece_tz).strftime('%H:%M')

    st.divider()

    # --- ΑΡΧΙΚΟΠΟΙΗΣΗ ΜΝΗΜΗΣ ---
    if "production_batch_items" not in st.session_state:
        st.session_state.production_batch_items = []
    if 'pending_conflict' not in st.session_state:
        st.session_state['pending_conflict'] = None

    # --- ΑΥΤΟΜΑΤΗ ΑΝΑΓΝΩΣΗ ΠΑΡΑΓΓΕΛΙΑΣ B2B ΣΤΟ ΚΑΛΑΘΙ ---
    if active_order is not None and not df_rec.empty and len(st.session_state.production_batch_items) == 0:
        details = active_order.get('order_details', '')
        b2b_customer = active_order.get('customer_name', 'Λιανική / Άγνωστος')
        lines = details.split('\n')
        for line in lines:
            if not line.strip() or "[" in line or "Αρχική" in line or "Έκπτωση" in line:
                continue
            try:
                clean_line = line.replace('•', '').strip()
                if " τμχ " in clean_line:
                    parts = clean_line.split(" τμχ ")
                    qty = int(parts[0].strip())
                    c_name = parts[1].split(' (')[0].strip()
                elif "x " in clean_line:
                    parts = clean_line.split("x ")
                    qty = int(parts[0].strip())
                    c_name = parts[1].split(' (')[0].strip()
                else:
                    continue
                
                if c_name in df_rec["Ονομα"].unique():
                    found = False
                    for item in st.session_state.production_batch_items:
                        if item["Πελάτης"] == b2b_customer and item["Κοκτέιλ"] == c_name:
                            item["Τεμάχια"] += qty
                            found = True
                            break
                    if not found:
                        st.session_state.production_batch_items.append({
                            "Πελάτης": b2b_customer, "Κοκτέιλ": c_name, "Τεμάχια": qty
                        })
            except Exception:
                pass

    # 2. ΦΟΡΜΑ ΠΑΡΑΓΩΓΗΣ 
    if not df_rec.empty:
        st.subheader(f"⚖️ Οδηγίες Ζύγισης (LOT: {date_lot_label})")
        
        st.markdown("### 🛒 1. Καταχώρηση Παραγγελιών ανά Πελάτη")
        c_col1, c_col2, c_col3, c_col4 = st.columns([2, 2, 1, 1.2])
        
        sel_cust = c_col1.selectbox("👤 1. Επιλέξτε Πελάτη:", customer_options, key=f"batch_cust_{reset_key}")
        recipe_options = list(df_rec["Ονομα"].unique())
        sel_cocktail = c_col2.selectbox("🍹 2. Επιλέξτε Κοκτέιλ:", recipe_options, key=f"batch_cocktail_{reset_key}")
        sel_pcs = c_col3.number_input("📦 3. Τεμάχια:", min_value=1, step=1, value=1, key=f"batch_pcs_{reset_key}")
        
        st.write("") 
        if c_col4.button("➕ Προσθήκη", use_container_width=True, type="secondary"):
            if sel_cocktail:
                cart_qty = 0
                for item in st.session_state.production_batch_items:
                    if item["Πελάτης"] == sel_cust and item["Κοκτέιλ"] == sel_cocktail:
                        cart_qty = item["Τεμάχια"]
                        break
                
                db_qty = 0
                if cart_qty == 0:
                    try:
                        res_db = supabase.table("production_log").select("pieces").eq("prod_date", formatted_date).eq("customer", sel_cust).eq("cocktail_name", sel_cocktail).execute()
                        if res_db.data:
                            db_qty = res_db.data[0]["pieces"]
                    except Exception:
                        pass

                existing_qty = cart_qty + db_qty

                if existing_qty > 0:
                    st.session_state['pending_conflict'] = {
                        "cust": sel_cust, "cocktail": sel_cocktail,
                        "new_pcs": sel_pcs, "old_pcs": existing_qty
                    }
                    st.rerun() 
                else:
                    st.session_state.production_batch_items.append({
                        "Πελάτης": sel_cust, "Κοκτέιλ": sel_cocktail, "Τεμάχια": sel_pcs
                    })
                    st.toast(f"✅ Προστέθηκαν {sel_pcs} τμχ {sel_cocktail}!")
                    st.rerun()

        if st.session_state.get('pending_conflict'):
            conf = st.session_state['pending_conflict']
            
            st.error(f"⚠️ **Προσοχή:** Το κοκτέιλ **{conf['cocktail']}** υπάρχει ήδη καταχωρημένο για τον πελάτη **{conf['cust']}** (Σήμερα)!")
            st.write(f"📊 Ήδη υπάρχουσα ποσότητα: **{conf['old_pcs']} τμχ** | Νέα προσθήκη: **{conf['new_pcs']} τμχ**")
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            if col_btn1.button(f"➕ Άθροισμα (Σύνολο: {conf['old_pcs'] + conf['new_pcs']} τμχ)", type="primary"):
                st.session_state.production_batch_items = [i for i in st.session_state.production_batch_items if not (i["Πελάτης"] == conf['cust'] and i["Κοκτέιλ"] == conf['cocktail'])]
                st.session_state.production_batch_items.append({
                    "Πελάτης": conf['cust'], "Κοκτέιλ": conf['cocktail'], "Τεμάχια": conf['old_pcs'] + conf['new_pcs']
                })
                st.session_state['pending_conflict'] = None
                st.toast("✅ Η ποσότητα ενημερώθηκε επιτυχώς!")
                st.rerun()
                
            if col_btn2.button(f"🔄 Αντικατάσταση (Τελικό: {conf['new_pcs']} τμχ)"):
                st.session_state.production_batch_items = [i for i in st.session_state.production_batch_items if not (i["Πελάτης"] == conf['cust'] and i["Κοκτέιλ"] == conf['cocktail'])]
                st.session_state.production_batch_items.append({
                    "Πελάτης": conf['cust'], "Κοκτέιλ": conf['cocktail'], "Τεμάχια": conf['new_pcs']
                })
                st.session_state['pending_conflict'] = None
                st.toast("🔄 Η ποσότητα αντικαταστάθηκε!")
                st.rerun()
                
            if col_btn3.button("❌ Ακύρωση"):
                st.session_state['pending_conflict'] = None
                st.rerun()
            
            st.divider()

        selected_cocktails = []
        all_assignments = {}

        if st.session_state.production_batch_items:
            st.markdown("#### 📋 Στοιχεία Τρέχουσας Παρτίδας προς Παραγωγή")
            df_current_batch = pd.DataFrame(st.session_state.production_batch_items)
            st.dataframe(df_current_batch, use_container_width=True, hide_index=True)
            
            if st.button("🗑️ Καθαρισμός Παρτίδας", type="secondary"):
                st.session_state.production_batch_items = []
                st.session_state['active_b2b_order'] = None
                st.rerun()
                
            for item in st.session_state.production_batch_items:
                cocktail = item["Κοκτέιλ"]
                c_name = item["Πελάτης"]
                pcs = item["Τεμάχια"]
                
                if cocktail not in all_assignments:
                    all_assignments[cocktail] = pd.DataFrame(columns=["Πελάτης", "Τεμάχια"])
                
                new_row = pd.DataFrame([{"Πελάτης": c_name, "Τεμάχια": int(pcs)}])
                all_assignments[cocktail] = pd.concat([all_assignments[cocktail], new_row], ignore_index=True)

            selected_cocktails = list(all_assignments.keys())
        else:
            st.warning("⚠️ Η παρτίδα είναι άδεια. Προσθέστε παραγγελίες παραπάνω για να εμφανιστούν τα υλικά και τα LOT.")

        if selected_cocktails:
            unique_customers_in_batch = set()
            for cocktail_name, edited_df in all_assignments.items():
                if "Πελάτης" in edited_df.columns and "Τεμάχια" in edited_df.columns:
                    for _, row in edited_df.iterrows():
                        if int(row.get("Τεμάχια", 0)) > 0 and str(row.get("Πελάτης", "")).strip():
                            unique_customers_in_batch.add(str(row.get("Πελάτης", "")).strip())

            cust_lot_config_map = {}
            if unique_customers_in_batch:
                st.markdown("### 📅 1β. Ρύθμιση LOT Έτοιμου Κοκτέιλ ανά Πελάτη")
                st.info("💡 Αν για κάποιον πελάτη μπήκες στο εργαστήριο άλλη μέρα, άλλαξε την Ημερομηνία LOT ή την Ημέρα Παραγωγής του εδώ ΜΙΑ φορά. Θα αλλάξει αυτόματα το LOT σε όλα του τα κοκτέιλ!")
                
                cust_lot_data = [{
                    "Πελάτης": c, 
                    "Ημερομηνία LOT": formatted_date, 
                    "Ημέρα Παραγωγής": prod_day
                } for c in sorted(list(unique_customers_in_batch))]
                
                df_cust_lots = pd.DataFrame(cust_lot_data)
                
                edited_cust_lots_df = st.data_editor(
                    df_cust_lots,
                    hide_index=True,
                    use_container_width=True,
                    key=f"cust_cocktail_lot_editor_{reset_key}",
                    column_config={
                        "Πελάτης": st.column_config.TextColumn("ΠΕΛΑΤΗΣ", disabled=True),
                        "Ημερομηνία LOT": st.column_config.TextColumn("ΗΜΕΡΟΜΗΝΙΑ LOT (DD/MM/YYYY)"),
                        "Ημέρα Παραγωγής": st.column_config.TextColumn("ΗΜΕΡΑ ΠΑΡΑΓΩΓΗΣ (Διψήφιος)", max_chars=2)
                    }
                )
                
                for _, row in edited_cust_lots_df.iterrows():
                    c_name_key = row["Πελάτης"]
                    cust_lot_config_map[c_name_key] = {
                        "prod_date": str(row["Ημερομηνία LOT"]).strip(),
                        "lot_cocktail": f"{str(row['Ημερομηνία LOT']).strip()}-{str(row['Ημέρα Παραγωγής']).strip()}"
                    }

            # --- ΒΗΜΑ 2: ΥΠΟΛΟΓΙΣΜΟΣ ΜΟΝΑΔΙΚΩΝ ΥΛΙΚΩΝ ΚΑΙ ΣΥΝΟΛΙΚΩΝ ML & ΒΑΡΟΥΣ ---
            ing_weights_map = {}
            try:
                res_ing_db = supabase.table("ingredients").select("name, weight_full, volume").execute()
                if res_ing_db.data:
                    for item in res_ing_db.data:
                        ing_weights_map[item["name"]] = {
                            "weight": float(item.get("weight_full", 0) or 0),
                            "volume": float(item.get("volume", 0) or 0)
                        }
            except:
                pass

            ing_totals = {}
            for cocktail_name in selected_cocktails:
                df_assign = all_assignments[cocktail_name]
                total_qty_for_cocktail = df_assign["Τεμάχια"].sum() if "Τεμάχια" in df_assign.columns else 0
                
                if total_qty_for_cocktail > 0:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    for i in range(1, 14):
                        ing = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                        if ing not in ["ΚΕΝΟ", "nan", "", "-", "0"]: 
                            ml_u = get_recipe_ml(recipe_row, i)
                            ing_totals[ing] = ing_totals.get(ing, 0.0) + (ml_u * total_qty_for_cocktail)

            st.markdown("### 🔄 2. Συνολικά Υλικά Παραγγελίας & Γρήγορη Εκτύπωση")
            
            with st.expander("📋 Πίνακας Μοναδικών Υλικών & Συνολικών Ποσοτήτων", expanded=True):
                mh = st.columns([2, 1.5, 1.5, 1.5]) 
                mh[0].caption("ΠΡΩΤΗ ΥΛΗ")
                mh[1].caption("ΣΥΝΟΛΟ (ml / g)")
                mh[2].caption("LOT ΗΜΕΡΑΣ")
                mh[3].caption("ΛΗΞΗ ΗΜΕΡΑΣ")
                
                for ing in sorted(ing_totals.keys()):
                    total_ml = ing_totals[ing]
                    weight_g = total_ml
                    
                    if ing != "Νερό" and ing in ing_weights_map:
                        pkg_weight = ing_weights_map[ing]["weight"]
                        pkg_volume = ing_weights_map[ing]["volume"]
                        if pkg_volume > 0 and pkg_weight > 0:
                            weight_g = (pkg_weight / pkg_volume) * total_ml

                    mr = st.columns([2, 1.5, 1.5, 1.5])
                    mr[0].write(f"**{ing}**")
                    mr[1].write(f"**{total_ml:.2f} ml | {weight_g:.2f} g**".replace('.', ','))
                    mr[2].text_input("LOT", key=f"mlot_{ing}_{reset_key}", label_visibility="collapsed")
                    mr[3].text_input("EXP", key=f"mexp_{ing}_{reset_key}", label_visibility="collapsed")

            st.divider()
            
            quick_lot_html = f"""
            <html><head><meta charset='UTF-8'><style>
                body {{ font-family: sans-serif; padding: 20px; }}
                .header {{ text-align: center; border-bottom: 3px solid #333; margin-bottom: 30px; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background-color: #f0f0f0; border: 2px solid #333; padding: 12px; text-align: left; }}
                td {{ border: 1px solid #555; padding: 22px 10px; }}
            </style></head>
            <body>
                <div class='header'>
                    <h2>📝 Φύλλο Καταγραφής LOT (Live Παραγωγή)</h2>
                    <p>Ημερομηνία: <b>{formatted_date}</b></p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 40%;">Πρώτη Ύλη</th>
                            <th style="width: 20%;">Απαιτούμενα (ml / g)</th>
                            <th style="width: 20%;">LOT Number (Γράψτε)</th>
                            <th style="width: 20%;">Ημ. Λήξης (Γράψτε)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for ing in sorted(ing_totals.keys()):
                total_ml = ing_totals[ing]
                weight_g = total_ml 
                if ing != "Νερό" and ing in ing_weights_map:
                    pkg_weight = ing_weights_map[ing]["weight"]
                    pkg_volume = ing_weights_map[ing]["volume"]
                    if pkg_volume > 0 and pkg_weight > 0:
                        weight_g = (pkg_weight / pkg_volume) * total_ml

                ml_str = f"{total_ml:.2f}".replace('.', ',')
                g_str = f"{weight_g:.2f}".replace('.', ',')

                quick_lot_html += f"""
                    <tr>
                        <td><b>{ing}</b></td>
                        <td style="font-size: 16px;"><b>{ml_str} ml</b> <br><span style="font-size: 13px; color: #555;">({g_str} g)</span></td>
                        <td></td>
                        <td></td>
                    </tr>
                """
            
            quick_lot_html += "</tbody></table></body></html>"

            col1, col2 = st.columns([1, 2])
            with col1:
                st.download_button(
                    label="🖨️ Εκτύπωση Λίστας για Αποθήκη",
                    data=quick_lot_html,
                    file_name=f"Live_Prep_Sheet_{datetime.now(greece_tz).strftime('%H%M')}.html",
                    mime="text/html",
                    use_container_width=True
                )
                
            # --- ΒΗΜΑ 3: ΑΝΑΛΥΤΙΚΗ ΦΟΡΜΑ & ΟΡΙΣΤΙΚΟΠΟΙΗΣΗ ---
            st.markdown("### 🏷️ 3. Αναλυτικό Δελτίο & Οριστικοποίηση")
            lot_entries = []
            
            with st.form(f"detailed_lot_form_{reset_key}"):
                for cocktail_name in selected_cocktails:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    df_assign = all_assignments[cocktail_name]
                    
                    total_qty_this = df_assign["Τεμάχια"].sum() if "Τεμάχια" in df_assign.columns else 0
                    if total_qty_this == 0: continue

                    current_unit_cost = 0.22 
                    for idx_ing in range(1, 14):
                        tmp_ing = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{idx_ing}", "ΚΕΝΟ"))
                        if tmp_ing not in ["ΚΕΝΟ", "nan", "Νερό", ""]:
                            tmp_ml = get_recipe_ml(recipe_row, idx_ing)
                            tmp_match = df_ing[df_ing["Name"] == tmp_ing]
                            if not tmp_match.empty:
                                v = float(tmp_match.iloc[0].get("Volume", tmp_match.iloc[0].get("volume", 1)))
                                p = float(tmp_match.iloc[0].get("Price", tmp_match.iloc[0].get("price", 0))) 
                                if v > 0:
                                    current_unit_cost += tmp_ml * (p / v)

                    st.markdown(f"#### 🍹 {cocktail_name} (Σύνολο: {total_qty_this} τμχ)")
                    h = st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2])
                    for col, label in zip(h, ["Υλικό", "ml", "Βάρος(g)", "Lot 1", "Λήξη 1", "Lot 2", "Λήξη 2"]): col.caption(label)
                    
                    for i in range(1, 14):
                        ing = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        if ing in ["ΚΕΝΟ", "nan", "Νερό", ""]: continue
                        
                        ml_u = get_recipe_ml(recipe_row, i)
                        tot_ml = ml_u * total_qty_this
                        tg_g = tot_ml
                        match_ing = df_ing[df_ing["Name"] == ing]
                        if not match_ing.empty:
                            tg_g = (tot_ml / match_ing.iloc[0]["Volume"]) * match_ing.iloc[0]["Weight_Full"]

                        r = st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2])
                        r[0].write(f"**{ing}**")
                        r[1].write(f"{tot_ml:.0f}")
                        r[2].markdown(f"**{tg_g:.1f}g**")
                        
                        m_lot = st.session_state.get(f"mlot_{ing}_{reset_key}", "")
                        m_exp = st.session_state.get(f"mexp_{ing}_{reset_key}", "")
                        
                        l1 = r[3].text_input("L1", key=f"l1_{cocktail_name}_{i}_{reset_key}", placeholder=m_lot, label_visibility="collapsed")
                        e1 = r[4].text_input("E1", key=f"e1_{cocktail_name}_{i}_{reset_key}", placeholder=m_exp, label_visibility="collapsed")
                        l2 = r[5].text_input("L2", key=f"l2_{cocktail_name}_{i}_{reset_key}", label_visibility="collapsed")
                        e2 = r[6].text_input("E2", key=f"e2_{cocktail_name}_{i}_{reset_key}", label_visibility="collapsed")

                        val_l1 = l1.strip() if l1.strip() else m_lot.strip()
                        val_e1 = e1.strip() if e1.strip() else m_exp.strip()
                        val_l2 = l2.strip()
                        val_e2 = e2.strip()

                        final_lot = val_l1 if not val_l2 else f"{val_l1} / {val_l2}"
                        final_exp = val_e1 if not val_e2 else f"{val_e1} / {val_e2}"

                        for _, row_assign in df_assign.iterrows():
                            c_name = str(row_assign.get("Πελάτης", "Λιανική / Άγνωστος")).strip()
                            if not c_name: c_name = "Λιανική / Άγνωστος"
                            c_qty = int(row_assign.get("Τεμάχια", 0))
                            
                            c_config = cust_lot_config_map.get(c_name, {
                                "prod_date": formatted_date, 
                                "lot_cocktail": date_lot_label
                            })
                            
                            if c_qty > 0:
                                lot_entries.append({
                                    "prod_date": c_config["prod_date"], 
                                    "prod_time": current_time, 
                                    "customer": c_name,
                                    "cocktail_name": cocktail_name, 
                                    "lot_cocktail": c_config["lot_cocktail"], 
                                    "pieces": c_qty,
                                    "ingredient_name": ing, "total_ml": float(ml_u * c_qty), 
                                    "target_g": round(float((ml_u * c_qty) / match_ing.iloc[0]["Volume"] * match_ing.iloc[0]["Weight_Full"]), 1) if not match_ing.empty else float(ml_u * c_qty),
                                    "lot_number": final_lot, 
                                    "expiry_date": final_exp,
                                    "unit_cost": round(current_unit_cost, 4)
                                })
                
                st.divider()
                if st.form_submit_button("💾 Οριστικοποίηση & Αποθήκευση στο Cloud", type="primary"):
                    if lot_entries:
                        try:
                            # 🚀 ΑΠΟΛΥΤΗ ΣΥΓΧΩΝΕΥΣΗ (Διαγραφή παλιών και εισαγωγή νέων)
                            # Αντί να αθροίζουμε τυφλά, διαγράφουμε τη σημερινή εγγραφή του πελάτη/κοκτέιλ και βάζουμε τη νέα (που τα περιέχει όλα)
                            unique_updates = set((e["customer"], e["cocktail_name"], e["prod_date"]) for e in lot_entries)
                            for cust, cock, pdate in unique_updates:
                                supabase.table("production_log").delete().eq("prod_date", pdate).eq("customer", cust).eq("cocktail_name", cock).execute()
                            
                            supabase.table("production_log").insert(lot_entries).execute()
                            # ΝΕΟ: Αφαίρεση υλικών για την απλή παραγωγή (Κανονικά + Δώρα)
                            for entry in lot_entries:
                                # Το ρομποτάκι αφαιρεί υλικά ανά κοκτέιλ. Χρησιμοποιούμε dictionary για να μην αφαιρέσει διπλές φορές
                                # αν το ίδιο κοκτέιλ έχει πολλά υλικά (γιατί το lot_entries έχει 1 γραμμή ανά υλικό).
                                pass # (Το κάνουμε πιο έξυπνα παρακάτω για να μην υπάρξει διπλοεγγραφή)
                            
                            unique_production_tasks = {}
                            for entry in lot_entries:
                                key = f"{entry['customer']}_{entry['cocktail_name']}"
                                unique_production_tasks[key] = {
                                    "name": entry['cocktail_name'],
                                    "pieces": entry['pieces']
                                }
                            
                            for task in unique_production_tasks.values():
                                deduct_inventory_for_production(task["name"], task["pieces"])
                            
                            # 🚀 ΣΥΓΧΩΝΕΥΣΗ B2B ΟΙΚΟΝΟΜΙΚΩΝ (Αυτόματο Re-build)
                            all_recipes_res = supabase.table("recipes").select("name, catalog_price").execute()
                            all_customers_res = supabase.table("customers").select("name, discount").execute()
                            
                            recipe_prices = {r['name']: float(r.get('catalog_price') or 0.0) for r in all_recipes_res.data} if all_recipes_res.data else {}
                            customer_discounts = {c['name']: float(c.get('discount') or 0.0) for c in all_customers_res.data} if all_customers_res.data else {}

                            for cust, _, pdate in unique_updates:
                                if cust == "Λιανική / Άγνωστος": continue
                                
                                # Διαβάζουμε ΟΛΗ την παραγωγή του πελάτη για τη μέρα για να φτιάξουμε 1 απόδειξη
                                today_logs = supabase.table("production_log").select("cocktail_name, pieces").eq("prod_date", pdate).eq("customer", cust).execute()
                                
                                if today_logs.data:
                                    unique_cocktails = {}
                                    for row in today_logs.data:
                                        unique_cocktails[row["cocktail_name"]] = int(row["pieces"])
                                        
                                    total_amount = 0.0
                                    details_lines = []
                                    for cockt, pcs in unique_cocktails.items():
                                        price = recipe_prices.get(cockt, 0.0)
                                        total_amount += price * pcs
                                        details_lines.append(f"• {pcs} τμχ {cockt}")
                                        
                                    discount = customer_discounts.get(cust, 0.0)
                                    final_total = total_amount * (1 - (discount / 100))
                                    
                                    details_str = "\n".join(details_lines)
                                    if discount > 0:
                                        details_str += f"\n\n[Αρχική Αξία: {total_amount:.2f}€ | Έκπτωση CRM: {discount}%]"
                                        
                                    try:
                                        date_iso = datetime.strptime(pdate, "%d/%m/%Y").strftime("%Y-%m-%d")
                                    except:
                                        date_iso = selected_date.isoformat()

                                    # Ψάχνουμε αν υπάρχει ήδη B2B παραγγελία
                                    existing_order = supabase.table("b2b_orders").select("id").eq("customer_name", cust).gte("created_at", f"{date_iso}T00:00:00").lte("created_at", f"{date_iso}T23:59:59").execute()
                                    
                                    if existing_order.data:
                                        supabase.table("b2b_orders").update({
                                            "total_amount": round(final_total, 2),
                                            "order_details": details_str
                                        }).eq("id", existing_order.data[0]["id"]).execute()
                                    else:
                                        supabase.table("b2b_orders").insert({
                                            "customer_name": cust, "total_amount": round(final_total, 2),
                                            "order_details": details_str, "status": "ΟΛΟΚΛΗΡΩΘΗΚΕ",
                                            "created_at": f"{date_iso}T{current_time}:00"
                                        }).execute()

                            st.session_state.production_batch_items = []
                            st.session_state['active_b2b_order'] = None 
                            st.session_state['lot_reset_key'] += 1
                            st.session_state.pop('search_data_loaded', None) # 🚀 FORCES REFRESH
                            st.success("✅ Η παραγωγή αποθηκεύτηκε και συγχωνεύτηκε άψογα!")
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά την αποθήκευση: {e}")
                            
    # --- 4. ΙΣΤΟΡΙΚΟ & ΔΙΑΧΕΙΡΙΣΗ ---
    st.divider()
    st.subheader("📂 Ιστορικό Παραγωγής & Εκτυπώσεις")
    
    res_log = supabase.table("production_log").select("*").order("prod_date", desc=True).execute()
    if res_log.data:
        df_all_logs = pd.DataFrame(res_log.data)
        df_all_logs_renamed = df_all_logs.rename(columns={
            "prod_date": "Ημερομηνία", "prod_time": "Ώρα", "customer": "Πελάτης", "cocktail_name": "Cocktail",
            "lot_cocktail": "LOT_Cocktail", "pieces": "Τεμάχια", "ingredient_name": "Υλικό",
            "total_ml": "Σύνολο_ML", "target_g": "Στόχος_Γραμμάρια", "lot_number": "Lot Number", "expiry_date": "Ημ_Λήξης"
        })

        st.markdown("### 🔍 Φίλτρα Αναζήτησης")
        all_dates = sorted(df_all_logs_renamed["Ημερομηνία"].dropna().unique(), reverse=True)
        date_options = ["-- Όλες οι Ημερομηνίες --"] + list(all_dates)
        sel_hist_date = st.selectbox("📅 Φίλτρο Ημερομηνίας:", options=date_options)

        df_temp_date = df_all_logs_renamed.copy()
        if sel_hist_date != "-- Όλες οι Ημερομηνίες --":
            df_temp_date = df_temp_date[df_temp_date["Ημερομηνία"] == sel_hist_date]

        col_f2, col_f3 = st.columns(2)
        with col_f2:
            cust_options = ["-- Όλοι οι Πελάτες --"] + sorted(list(df_temp_date["Πελάτης"].dropna().unique()))
            sel_customer = st.selectbox("👤 Φίλτρο Πελάτη:", options=cust_options)

        with col_f3:
            cocktail_options = ["-- Όλα τα Cocktails --"] + sorted(list(df_temp_date["Cocktail"].dropna().unique()))
            sel_cocktail = st.selectbox("🍹 Φίλτρο ανά Cocktail:", options=cocktail_options)

        df_filtered = df_temp_date.copy()
        if sel_customer != "-- Όλοι οι Πελάτες --": df_filtered = df_filtered[df_filtered["Πελάτης"] == sel_customer]
        if sel_cocktail != "-- Όλα τα Cocktails --": df_filtered = df_filtered[df_filtered["Cocktail"] == sel_cocktail]

        df_past = df_filtered.copy()
        st.divider()

        tab_edit_batch, tab_bulk_lots, tab_mass_date = st.tabs([
            "✏️ Τροποποίηση Ποσοτήτων", "📦 Μαζική Ενημέρωση LOT Υλικών", "📅 Μαζική Αλλαγή Ημερ. Παραγωγής"
        ])

        with tab_edit_batch:
            st.markdown("### 🛠️ Επεξεργασία ανά Κοκτέιλ & Μαζική Ρύθμιση LOT")
            unique_cocktails_of_day = df_past["Cocktail"].unique() if not df_past.empty else []
            options = ["-- Επιλέξτε Κοκτέιλ για Επεξεργασία --"] + list(unique_cocktails_of_day)
            sel_cocktail_edit = st.selectbox("Διαλέξτε το Κοκτέιλ που παράγεται:", options, key="batch_edit_by_cocktail_key")
            
            if sel_cocktail_edit != "-- Επιλέξτε Κοκτέιλ για Επεξεργασία --":
                batch_id = str(hash(sel_cocktail_edit))
                cocktail_df = df_past[df_past["Cocktail"] == sel_cocktail_edit]
                unique_customers = cocktail_df["Πελάτης"].unique()
                first_cust_df = cocktail_df[cocktail_df["Πελάτης"] == unique_customers[0]]
                old_lot_cocktail = str(first_cust_df.iloc[0]["LOT_Cocktail"])
                
                if "-" in old_lot_cocktail:
                    parts_lot = old_lot_cocktail.split("-")
                    default_lot_date, default_prod_day = parts_lot[0].strip(), parts_lot[1].strip()
                else:
                    default_lot_date = str(first_cust_df.iloc[0]["Ημερομηνία"])
                    default_prod_day = default_lot_date.split("/")[0] if "/" in default_lot_date else "01"

                st.markdown(f"#### 📅 Κεντρικό LOT Παραγωγής για το {sel_cocktail_edit}")
                c_g1, c_g2 = st.columns([2, 2])
                new_global_lot_date = c_g1.text_input("📅 Κοινή Ημερομηνία LOT (DD/MM/YYYY)", value=default_lot_date, key=f"global_ldate_{batch_id}")
                new_global_prod_day = c_g2.text_input("🔢 Κοινή Ημέρα Παραγωγής (Διψήφιος)", value=default_prod_day, max_chars=2, key=f"global_pday_{batch_id}")
                global_lot_c = f"{new_global_lot_date.strip()}-{new_global_prod_day.strip()}"
                
                st.divider()
                st.markdown("#### 👥 Κατανόηση Ποσοτήτων ανά Πελάτη")
                customer_settings = {}
                
                for cust in unique_customers:
                    cust_df = cocktail_df[cocktail_df["Πελάτης"] == cust]
                    base_cust = cust_df.iloc[0]
                    old_pcs = int(base_cust["Τεμάχια"])
                    
                    st.markdown(f"**👤 Πελάτης: {cust}**")
                    c1, c2 = st.columns([2, 1])
                    new_cust_name = c1.text_input("Όνομα Πελάτη", value=cust, key=f"ed_cname_{batch_id}_{cust}")
                    new_pcs = c2.number_input("📦 Τεμάχια Παραγωγής", value=old_pcs, min_value=1, key=f"ed_pcs_{batch_id}_{cust}")
                    
                    customer_settings[cust] = {
                        "new_cust_name": new_cust_name.strip(), "new_lot_date": new_global_lot_date.strip(),
                        "new_prod_day": new_global_prod_day.strip(), "new_lot_c": global_lot_c,
                        "new_pcs": new_pcs, "old_pcs": old_pcs, "base_date_str": base_cust["Ημερομηνία"]
                    }
                    st.caption("---")

                st.markdown("#### 🧪 Έλεγχος Υλικών & LOT Πρώτων Υλών ανά Πελάτη")
                with st.form(f"edit_form_cocktail_batch_{batch_id}"):
                    h_edit = st.columns([1.2, 1.5, 0.6, 1.2, 1.2, 1.2, 1.2])
                    for col, label in zip(h_edit, ["Πελάτης", "Υλικό", "ml", "Lot 1", "Λήξη 1", "Lot 2", "Λήξη 2"]): col.caption(label)
                    
                    final_updated_rows = []
                    for i, idx in enumerate(cocktail_df.index):
                        r_d = df_past.loc[idx]
                        orig_row_in_all_logs = df_all_logs.loc[idx]
                        cust_name, ing_name, old_ml = r_d["Πελάτης"], r_d["Υλικό"], float(r_d["Σύνολο_ML"])
                        c_set = customer_settings[cust_name]
                        new_ml = old_ml * (float(c_set["new_pcs"]) / float(c_set["old_pcs"]) if c_set["old_pcs"] != 0 else 1.0)
                        
                        raw_lot, raw_exp = str(r_d["Lot Number"]), str(r_d["Ημ_Λήξης"])
                        lot_parts = raw_lot.split(" / ") if " / " in raw_lot else [raw_lot, ""]
                        exp_parts = raw_exp.split(" / ") if " / " in raw_exp else [raw_exp, ""]
                        while len(lot_parts) < 2: lot_parts.append("")
                        while len(exp_parts) < 2: exp_parts.append("")
                        
                        r = st.columns([1.2, 1.5, 0.6, 1.2, 1.2, 1.2, 1.2])
                        r[0].write(f"{cust_name}")
                        r[1].write(f"**{ing_name}**")
                        r[2].write(f"{new_ml:.0f}")
                        
                        lt1 = r[3].text_input("L1", value=lot_parts[0], key=f"ed_l1_{batch_id}_{i}", label_visibility="collapsed")
                        ex1 = r[4].text_input("E1", value=exp_parts[0], key=f"ed_e1_{batch_id}_{i}", label_visibility="collapsed")
                        lt2 = r[5].text_input("L2", value=lot_parts[1], key=f"ed_l2_{batch_id}_{i}", label_visibility="collapsed")
                        ex2 = r[6].text_input("E2", value=exp_parts[1], key=f"ed_e2_{batch_id}_{i}", label_visibility="collapsed")
                        
                        u_cost = orig_row_in_all_logs.get("unit_cost", 0.22)
                        if pd.isna(u_cost): u_cost = 0.22
                        
                        final_updated_rows.append({
                            "orig_cust": cust_name, "ing": ing_name, "ml": new_ml,
                            "lot": lt1 if not lt2 else f"{lt1} / {lt2}", "exp": ex1 if not ex2 else f"{ex1} / {ex2}", 
                            "u_cost": u_cost, "orig_id": orig_row_in_all_logs["id"], "orig_time": r_d["Ώρα"]
                        })
                    
                    st.divider()
                    col_save, col_del = st.columns(2)
                    with col_save: btn_save = st.form_submit_button("💾 Αποθήκευση Αλλαγών Κοκτέιλ", type="primary")
                    with col_del: btn_del = st.form_submit_button("🗑️ Διαγραφή Παραγωγής")
                        
                    if btn_save:
                        try:
                            ids_to_del = [f["orig_id"] for f in final_updated_rows]
                            if ids_to_del: supabase.table("production_log").delete().in_("id", ids_to_del).execute()
                            
                            new_batch = []
                            for fd in final_updated_rows:
                                c_set = customer_settings[fd["orig_cust"]]
                                g_calc = fd["ml"]
                                match_i = df_ing[df_ing["Name"] == fd["ing"]]
                                if not match_i.empty: g_calc = (fd["ml"] / match_i.iloc[0]["Volume"]) * match_i.iloc[0]["Weight_Full"]
                                
                                new_batch.append({
                                    "prod_date": c_set["new_lot_date"], "prod_time": fd["orig_time"], 
                                    "customer": c_set["new_cust_name"], "cocktail_name": sel_cocktail_edit, 
                                    "lot_cocktail": c_set["new_lot_c"], "pieces": int(c_set["new_pcs"]), 
                                    "ingredient_name": fd["ing"], "total_ml": fd["ml"], "target_g": round(g_calc, 1), 
                                    "lot_number": fd["lot"], "expiry_date": fd["exp"], "unit_cost": round(float(fd["u_cost"]), 4)
                                })
                            if new_batch: supabase.table("production_log").insert(new_batch).execute()
                            
                            for orig_c, c_set in customer_settings.items():
                                old_target_date = datetime.strptime(c_set["base_date_str"], "%d/%m/%Y").strftime("%Y-%m-%d")
                                new_target_date = datetime.strptime(c_set["new_lot_date"], "%d/%m/%Y").strftime("%Y-%m-%d")
                                res_orders = supabase.table("b2b_orders").select("*").eq("customer_name", orig_c).gte("created_at", f"{old_target_date}T00:00:00").lte("created_at", f"{old_target_date}T23:59:59").execute()
                                
                                if res_orders.data:
                                    for order in res_orders.data:
                                        if f"{c_set['old_pcs']} τμχ {sel_cocktail_edit}" in str(order.get('order_details', '')):
                                            new_catalog_price = 0.0
                                            res_p = supabase.table("recipes").select("catalog_price").eq("name", sel_cocktail_edit).execute()
                                            if res_p.data and res_p.data[0].get("catalog_price"): new_catalog_price = float(res_p.data[0].get("catalog_price"))
                                                
                                            cust_discount = 0.0
                                            res_c = supabase.table("customers").select("discount").eq("name", c_set["new_cust_name"]).execute()
                                            if res_c.data and res_c.data[0].get("discount"): cust_discount = float(res_c.data[0].get("discount"))
                                            
                                            lines = str(order.get('order_details', '')).split('\n')
                                            new_lines, total_amount_before_discount = [], 0.0
                                            
                                            for line in lines:
                                                if line.strip().startswith("•") or "τμχ" in line:
                                                    if f"{c_set['old_pcs']} τμχ {sel_cocktail_edit}" in line:
                                                        line_text, current_pcs, current_price = f"• {c_set['new_pcs']} τμχ {sel_cocktail_edit}", c_set['new_pcs'], new_catalog_price
                                                    else:
                                                        line_text = line
                                                        try:
                                                            parts = line.replace('•', '').split(' τμχ ')
                                                            current_pcs, current_cocktail = int(parts[0].strip()), parts[1].split(' (')[0].strip()
                                                            res_other_p = supabase.table("recipes").select("catalog_price").eq("name", current_cocktail).execute()
                                                            current_price = float(res_other_p.data[0].get("catalog_price")) if (res_other_p.data and res_other_p.data[0].get("catalog_price")) else 0.0
                                                        except: current_pcs, current_price = 0, 0.0
                                                    
                                                    total_amount_before_discount += current_pcs * current_price
                                                    new_lines.append(line_text)
                                            
                                            final_payable_amount = total_amount_before_discount * (1 - (cust_discount / 100))
                                            details_str = "\n".join(new_lines) + f"\n\n[Αρχική Αξία: {total_amount_before_discount:.2f}€]"
                                            if cust_discount > 0: details_str += f"\n[Έκπτωση: {cust_discount}% εφαρμόστηκε]"
                                            
                                            supabase.table("b2b_orders").update({
                                                "customer_name": c_set["new_cust_name"], "total_amount": round(final_payable_amount, 2),
                                                "order_details": details_str, "created_at": f"{new_target_date}T{fd['orig_time']}"
                                            }).eq("id", order['id']).execute()
                                            break
                            st.session_state['lot_reset_key'] += 1
                            st.session_state.pop('search_data_loaded', None)
                            st.success("✅ Επιτυχία! Το LOT και η ημερομηνία άλλαξαν και εφαρμόστηκαν σε όλους!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as save_err:
                            st.error(f"Σφάλμα κατά την αποθήκευση: {save_err}")

                    if btn_del:
                        try:
                            ids_to_del = df_all_logs.loc[cocktail_df.index, "id"].tolist()
                            if ids_to_del: supabase.table("production_log").delete().in_("id", ids_to_del).execute()
                            
                            for orig_c, c_set in customer_settings.items():
                                target_date = datetime.strptime(c_set["base_date_str"], "%d/%m/%Y").strftime("%Y-%m-%d")
                                res_orders = supabase.table("b2b_orders").select("*").eq("customer_name", orig_c).gte("created_at", f"{target_date}T00:00:00").lte("created_at", f"{target_date}T23:59:59").execute()
                                
                                if res_orders.data:
                                    for order in res_orders.data:
                                        if f"{c_set['old_pcs']} τμχ {sel_cocktail_edit}" in str(order.get('order_details', '')):
                                            lines = str(order.get('order_details', '')).split('\n')
                                            new_lines, total_amount_before_discount = [], 0.0
                                            
                                            cust_discount = 0.0
                                            res_c = supabase.table("customers").select("discount").eq("name", orig_c).execute()
                                            if res_c.data and res_c.data[0].get("discount"): cust_discount = float(res_c.data[0].get("discount"))
                                                
                                            for line in lines:
                                                if not line.strip() or "[Αρχική Αξία:" in line or "Έκπτωση:" in line: continue
                                                if line.strip().startswith("•") or "τμχ" in line:
                                                    if f"{c_set['old_pcs']} τμχ {sel_cocktail_edit}" in line: continue
                                                    else:
                                                        new_lines.append(line)
                                                        try:
                                                            parts = line.replace('•', '').split(' τμχ ')
                                                            current_pcs, current_cocktail = int(parts[0].strip()), parts[1].split(' (')[0].strip()
                                                            res_other_p = supabase.table("recipes").select("catalog_price").eq("name", current_cocktail).execute()
                                                            current_price = float(res_other_p.data[0].get("catalog_price")) if (res_other_p.data and res_other_p.data[0].get("catalog_price")) else 0.0
                                                            total_amount_before_discount += current_pcs * current_price
                                                        except: pass
                                            
                                            if not new_lines:
                                                supabase.table("b2b_orders").delete().eq("id", order['id']).execute()
                                            else:
                                                final_payable_amount = total_amount_before_discount * (1 - (cust_discount / 100))
                                                details_str = "\n".join(new_lines) + f"\n\n[Αρχική Αξία: {total_amount_before_discount:.2f}€]"
                                                if cust_discount > 0: details_str += f"\n[Έκπτωση: {cust_discount}% εφαρμόστηκε]"
                                                supabase.table("b2b_orders").update({"total_amount": round(final_payable_amount, 2), "order_details": details_str}).eq("id", order['id']).execute()
                                            break 
                            st.session_state['lot_reset_key'] += 1
                            st.session_state.pop('search_data_loaded', None)
                            st.warning("🗑️ Η παραγωγή ενημερώθηκε και το κοκτέιλ αφαιρέθηκε χειρουργικά.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά τη διαγραφή: {e}")

        with tab_bulk_lots:
            st.markdown("### 📋 Συνολικά LOT Πρώτων Υλών (Μαζική Διόρθωση)")
            st.info("💡 Αλλάξτε το Lot ή τη Λήξη σε ένα υλικό, και η αλλαγή θα περάσει αυτόματα σε ΟΛΑ τα cocktails της ημέρας!")

            # 🚀 ΚΛΕΙΣΙΜΟ ΤΡΥΠΑΣ 1: Απαγόρευση μαζικής αλλαγής αν δεν έχει επιλεγεί ημέρα!
            if sel_hist_date == "-- Όλες οι Ημερομηνίες --":
                st.warning("⚠️ Παρακαλώ επιλέξτε πρώτα μια συγκεκριμένη **Ημερομηνία** από το φίλτρο στην κορυφή της σελίδας για να κάνετε μαζική ενημέρωση. Διαφορετικά θα αλλάζατε τα LOT όλων των ετών!")
            elif df_filtered.empty:
                st.warning("Δεν βρέθηκαν εγγραφές με τα συγκεκριμένα φίλτρα.")
            else:
                # 🚀 ΚΛΕΙΣΙΜΟ ΤΡΥΠΑΣ 2: Ασφαλής συνένωση αν υπάρχουν πολλαπλά διαφορετικά LOT
                def safe_join(x):
                    vals = sorted(set(str(v).strip() for v in x if pd.notna(v) and str(v).lower() not in ['none', '', 'nan']))
                    return " / ".join(vals) if vals else ""
                
                df_grouped = df_filtered.groupby("Υλικό").agg({
                    "Σύνολο_ML": "sum", 
                    "Lot Number": safe_join,  # Πλέον δεν κρύβει τα διαφορετικά LOT
                    "Ημ_Λήξης": safe_join
                }).reset_index()
                
                edited_summary = st.data_editor(
                    df_grouped,
                    column_config={
                        "Υλικό": st.column_config.TextColumn("ΠΡΩΤΗ ΥΛΗ", disabled=True),
                        "Σύνολο_ML": st.column_config.NumberColumn("ΣΥΝΟΛΟ (ml)", disabled=True),
                        "Lot Number": st.column_config.TextColumn("LOT ΗΜΕΡΑΣ (Αλλαγή)"),
                        "Ημ_Λήξης": st.column_config.TextColumn("ΛΗΞΗ ΗΜΕΡΑΣ (Αλλαγή)")
                    },
                    hide_index=True, use_container_width=True, key=f"grouped_lot_editor_{reset_key}"
                )
                
                lot_sheet_html = f"""
                <html><head><meta charset='UTF-8'><style>
                    body {{ font-family: sans-serif; padding: 20px; }}
                    .header {{ text-align: center; border-bottom: 3px solid #333; margin-bottom: 30px; padding-bottom: 10px; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th {{ background-color: #f0f0f0; border: 2px solid #333; padding: 12px; }}
                    td {{ border: 1px solid #555; padding: 22px 10px; }}
                </style></head>
                <body>
                    <div class='header'>
                        <h2>📝 Φύλλο Καταγραφής LOT Πρώτων Υλών</h2>
                        <p>Ημερομηνία Παραγωγής: <b>{sel_hist_date}</b></p>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 40%;">Πρώτη Ύλη</th><th style="width: 15%;">Σύνολο (ml)</th><th style="width: 25%;">LOT Number (Γράψτε εδώ)</th><th style="width: 20%;">Ημ. Λήξης (Γράψτε εδώ)</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, row in df_grouped.iterrows(): lot_sheet_html += f"<tr><td><b>{row['Υλικό']}</b></td><td>{row['Σύνολο_ML']} ml</td><td></td><td></td></tr>"
                lot_sheet_html += "</tbody></table></body></html>"

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1: save_grouped = st.button("💾 Ενημέρωση LOT σε όλα τα Cocktail", type="primary", use_container_width=True, key="save_grouped_lots_btn")
                with col_btn2:
                    safe_date = sel_hist_date.replace("/", "_")
                    st.download_button(label="🖨️ Εκτύπωση Κενού Φύλλου Καταγραφής LOT", data=lot_sheet_html, file_name=f"Blank_LOT_Sheet_{safe_date}.html", mime="text/html", use_container_width=True)
                    
                if save_grouped:
                    updates_made = 0
                    try:
                        for idx, row in edited_summary.iterrows():
                            orig_lot, orig_exp = str(df_grouped.loc[idx, "Lot Number"]), str(df_grouped.loc[idx, "Ημ_Λήξης"])
                            new_lot, new_exp = str(row["Lot Number"]), str(row["Ημ_Λήξης"])
                            
                            # Ελέγχουμε αν ο χρήστης έκανε αλλαγή σε σχέση με την προβολή
                            if new_lot != orig_lot or new_exp != orig_exp:
                                clean_lot = "" if pd.isna(row["Lot Number"]) or new_lot == "nan" else new_lot.strip()
                                clean_exp = "" if pd.isna(row["Ημ_Λήξης"]) or new_exp == "nan" else new_exp.strip()
                                
                                query = supabase.table("production_log").update({"lot_number": clean_lot, "expiry_date": clean_exp}).eq("ingredient_name", row["Υλικό"]).eq("prod_date", sel_hist_date)
                                if sel_customer != "-- Όλοι οι Πελάτες --": query = query.eq("customer", sel_customer)
                                if sel_cocktail != "-- Όλα τα Cocktails --": query = query.eq("cocktail_name", sel_cocktail)
                                query.execute()
                                updates_made += 1
                        
                        if updates_made > 0:
                            st.session_state['lot_reset_key'] += 1
                            st.session_state.pop('search_data_loaded', None) 
                            st.success("✅ Τα νέα LOT περάστηκαν αυτόματα σε όλες τις συνταγές!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("Δεν εντοπίστηκαν αλλαγές για να αποθηκευτούν.")
                    except Exception as e:
                        st.error(f"Σφάλμα κατά την ενημέρωση: {e}")

        with tab_mass_date:
            st.markdown("### 🔢 Μαζική Αλλαγή Διψήφιου (Ημέρας) Παραγωγής")
            st.info("💡 Αλλάξτε ΜΟΝΟ τον διψήφιο αριθμό στο τέλος του LOT (π.χ. από -01 σε -02) για όσα κοκτέιλ θέλετε. Τα οικονομικά και τα υπόλοιπα LOT παραμένουν άθικτα!")

            if sel_hist_date == "-- Όλες οι Ημερομηνίες --":
                st.warning("⚠️ Παρακαλώ επιλέξτε πρώτα μια συγκεκριμένη Ημερομηνία από το φίλτρο στην κορυφή της σελίδας.")
            else:
                unique_cocktails_of_day = df_past["Cocktail"].dropna().unique()
                
                if len(unique_cocktails_of_day) == 0:
                    st.info("Δεν βρέθηκαν κοκτέιλ για αυτή την ημερομηνία (ή για τον επιλεγμένο πελάτη).")
                else:
                    selected_mass_cocktails = st.multiselect(
                        "🍹 1. Επιλέξτε Κοκτέιλ (μπορείτε να επιλέξετε πολλά):",
                        options=list(unique_cocktails_of_day)
                    )
                    
                    new_mass_prod_day = st.text_input("🔢 2. Νέος Διψήφιος Αριθμός (π.χ. 02):", max_chars=2)
                    
                    st.divider()
                    if st.button("💾 Αποθήκευση Νέου Διψήφιου", type="primary"):
                        if not selected_mass_cocktails:
                            st.error("Επιλέξτε τουλάχιστον ένα κοκτέιλ.")
                        elif not new_mass_prod_day.strip():
                            st.error("Παρακαλώ συμπληρώστε τον νέο διψήφιο αριθμό.")
                        elif not new_mass_prod_day.strip().isdigit():
                            st.error("⚠️ Σφάλμα: Ο διψήφιος πρέπει να περιέχει ΜΟΝΟ αριθμούς (π.χ. 01, 02).")
                        else:
                            try:
                                # 🚀 ΔΙΟΡΘΩΣΗ 2 & 3: Σωστό padding με μηδενικό
                                safe_prod_day = new_mass_prod_day.strip().zfill(2)
                                
                                # 🚀 ΔΙΟΡΘΩΣΗ 1: Σεβόμαστε το φίλτρο του πελάτη!
                                mask = (df_all_logs["prod_date"] == sel_hist_date) & (df_all_logs["cocktail_name"].isin(selected_mass_cocktails))
                                if sel_customer != "-- Όλοι οι Πελάτες --":
                                    mask = mask & (df_all_logs["customer"] == sel_customer)
                                    
                                rows_to_update = df_all_logs[mask]
                                
                                updates_count = 0
                                for idx, row in rows_to_update.iterrows():
                                    old_lot_c = str(row["lot_cocktail"])
                                    row_id = row["id"]
                                    
                                    if "-" in old_lot_c:
                                        new_lot_c = f"{old_lot_c.split('-')[0].strip()}-{safe_prod_day}"
                                    else:
                                        new_lot_c = f"{old_lot_c}-{safe_prod_day}"
                                        
                                    if new_lot_c != old_lot_c:
                                        supabase.table("production_log").update({"lot_cocktail": new_lot_c}).eq("id", row_id).execute()
                                        updates_count += 1
                                        
                                if updates_count > 0:
                                    st.session_state['lot_reset_key'] += 1
                                    st.session_state.pop('search_data_loaded', None) # Καθαρισμός μνήμης για ανανέωση
                                    st.success(f"✅ Ο διψήφιος αριθμός άλλαξε επιτυχώς σε '-{safe_prod_day}' για {updates_count} εγγραφές!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.info("Όλες οι επιλεγμένες εγγραφές έχουν ήδη αυτόν τον διψήφιο αριθμό.")
                            except Exception as e:
                                st.error(f"Σφάλμα κατά την ενημέρωση: {e}")

        st.divider()
        cust_label = f" | Πελάτης: <b>{sel_customer}</b>" if sel_customer != "-- Όλοι οι Πελάτες --" else ""
        file_suffix = f"_{sel_customer.replace(' ', '_')}" if sel_customer != "-- Όλοι οι Πελάτες --" else ""

        df_clean_customers = df_past.groupby(["Πελάτης", "Ημερομηνία", "Cocktail", "LOT_Cocktail"], as_index=False).agg({"Τεμάχια": "first"})

        html_pro = f"""<html><head><meta charset='UTF-8'><style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; margin: 20px; line-height: 1.5; }}
            .document-header {{ text-align: center; border-bottom: 3px solid #0275d8; padding-bottom: 15px; margin-bottom: 25px; }}
            .document-header h1 {{ color: #0275d8; font-size: 24px; margin: 0; }}
            .document-header h2 {{ color: #555; font-size: 16px; margin: 5px 0 0 0; font-weight: normal; }}
            .customer-section {{ background-color: #f8f9fa; padding: 12px; border: 1px solid #dee2e6; margin-top: 25px; font-size: 14px; border-left: 5px solid #0275d8; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
            th {{ background-color: #0275d8; color: white; padding: 10px; text-align: left; font-weight: bold; }}
            td {{ border: 1px solid #dee2e6; padding: 10px; }}
            tr:nth-child(even) {{ background-color: #fdfdfd; }}
            .badge {{ background-color: #e9ecef; color: #495057; padding: 3px 6px; border-radius: 4px; font-family: monospace; font-weight: bold; }}
        </style></head><body>
            <div class='document-header'><h1>CABCLUB COCKTAILS</h1><h2>📋 ΗΜΕΡΗΣΙΑ ΠΑΡΑΓΩΓΗ ΑΝΑ ΠΕΛΑΤΗ</h2><p>Ημερομηνία Φιλτραρίσματος: <b>{sel_hist_date}</b>{cust_label}</p></div>
        """
        for p in df_clean_customers["Πελάτης"].unique():
            p_df = df_clean_customers[df_clean_customers["Πελάτης"] == p]
            actual_prod_date = p_df["Ημερομηνία"].iloc[0] if "Ημερομηνία" in p_df.columns else sel_hist_date
            html_pro += f"<div class='customer-section'><strong>👤 ΠΕΛΑΤΗΣ:</strong> {p} | <strong>ΗΜΕΡΟΜΗΝΙΑ ΠΑΡΑΓΩΓΗΣ:</strong> {actual_prod_date}</div><table><thead><tr><th>🍹 Έτοιμο Cocktail</th><th>🔢 LOT Προϊόντος</th><th>📦 Ποσότητα</th></tr></thead><tbody>"
            for _, row in p_df.iterrows(): html_pro += f"<tr><td><strong>{row['Cocktail']}</strong></td><td><span class='badge'>{row['LOT_Cocktail']}</span></td><td>{int(row['Τεμάχια'])} τμχ</td></tr>"
            html_pro += "</tbody></table>"
        html_pro += "</body></html>"

        df_daily = df_past.drop_duplicates(subset=["Πελάτης", "Cocktail", "LOT_Cocktail"])
        grand_total_pcs, total_different_cocktails = df_daily["Τεμάχια"].sum(), df_daily["Cocktail"].nunique() if not df_daily.empty else 0
        total_label_text = f"ΣΥΝΟΛΙΚΗ ΠΑΡΑΓΩΓΗ ({sel_hist_date}):" if sel_customer == "-- Όλοι οι Πελάτες --" else f"ΣΥΝΟΛΙΚΗ ΠΑΡΑΓΩΓΗ ΓΙΑ {sel_customer.upper()} ({sel_hist_date}):"

        html_daily = f"""<html><head><meta charset='UTF-8'><style>
            body {{ font-family: sans-serif; padding: 20px; }}
            .header {{ text-align: center; border-bottom: 3px solid #d32f2f; margin-bottom: 30px; }}
            .cocktail-header {{ background-color: #d32f2f; color: white; padding: 10px; margin-top: 20px; border-radius: 5px 5px 0 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
            th {{ background-color: #444; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 10px; border: 1px solid #ddd; }}
            .grand-total {{ margin-top: 30px; padding: 20px; background-color: #f8f9fa; border: 2px solid #d32f2f; text-align: center; font-size: 1.4em; border-radius: 10px; line-height: 1.8; }}
            .grand-total b {{ color: #d32f2f; font-size: 1.6em; }}
            .cocktail-count {{ color: #444; font-size: 1.1em; font-weight: bold; margin-top: 5px; display: block; }}
        </style></head><body>
            <div class='header'><h1>📋 ΗΜΕΡΗΣΙΟ ΦΥΛΛΟ ΠΑΡΑΓΩΓΗΣ</h1><p>Ημερομηνία: <b>{sel_hist_date}</b>{cust_label}</p></div>
        """
        for cock in df_daily["Cocktail"].unique():
            c_data = df_daily[df_daily["Cocktail"] == cock]
            html_daily += f"<h2 class='cocktail-header'>🍹 {cock}</h2><table><thead><tr><th>LOT Number</th><th>Πελάτης</th><th>Ποσότητα (τμχ)</th></tr></thead><tbody>"
            for _, row in c_data.iterrows(): html_daily += f"<tr><td>{row['LOT_Cocktail']}</td><td>{row['Πελάτης']}</td><td>{row['Τεμάχια']}</td></tr>"
            html_daily += f"<tr style='background:#f9f9f9; font-weight:bold;'><td colspan='2' style='text-align: right;'>ΜΕΡΙΚΟ ΣΥΝΟΛΟ {cock}:</td><td>{c_data['Τεμάχια'].sum()} τμχ</td></tr></tbody></table>"

        html_daily += f"<div class='grand-total'>{total_label_text}<br><b>{grand_total_pcs} Τεμάχια</b><span class='cocktail-count'>🍹 Διαφορετικά Cocktail: {total_different_cocktails}</span></div></body></html>"
        
        df_prep = df_past.groupby("Υλικό").agg({
            "Σύνολο_ML": "sum", "Στόχος_Γραμμάρια": "sum",
            "Lot Number": lambda x: " / ".join(sorted(set(str(v).strip() for v in x if v and str(v).lower() not in ['none', '', 'nan']))),
            "Ημ_Λήξης": lambda x: " / ".join(sorted(set(str(v).strip() for v in x if v and str(v).lower() not in ['none', '', 'nan'])))
        }).reset_index()

        html_prep = f"""<html><head><meta charset='UTF-8'><style>
            body {{ font-family: sans-serif; padding: 30px; }}
            .header {{ text-align: center; border-bottom: 4px solid #2980b9; margin-bottom: 30px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background-color: #2980b9; color: white; padding: 12px; text-align: left; }}
            td {{ border: 1px solid #bdc3c7; padding: 10px; }}
            .lot-info {{ font-size: 0.9em; color: #555; }}
        </style></head><body>
            <div class='header'><h1>🧪 ΛΙΣΤΑ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ΥΛΙΚΩΝ</h1><p>Ημερομηνία: <b>{sel_hist_date}</b>{cust_label}</p></div>
            <table><thead><tr><th>Πρώτη Ύλη</th><th>Συνολική Ποσότητα (ml)</th><th>Συνολικό Βάρος (g)</th><th>Lot & Λήξη Πρ. Ύλης</th></tr></thead><tbody>
        """
        for _, row in df_prep.iterrows():
            display_parts = [p for p in [row['Lot Number'], row['Ημ_Λήξης']] if p]
            lot_text = " | ".join(display_parts) if display_parts else "-"
            html_prep += f"<tr><td><b>{row['Υλικό']}</b></td><td>{row['Σύνολο_ML']:.0f} ml</td><td>{row['Στόχος_Γραμμάρια']:.1f} g</td><td class='lot-info'>{lot_text}</td></tr>"
        html_prep += "</tbody></table></body></html>"

        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.download_button("📋 Ημερήσια Παραγωγή Ανά Πελάτη", data=html_pro, file_name=f"Prod_By_Customer_{sel_hist_date}{file_suffix}.html", mime="text/html", use_container_width=True)
        col_p2.download_button("📋 Ημερήσια Παραγωγή", data=html_daily, file_name=f"Daily_{sel_hist_date}{file_suffix}.html", mime="text/html", use_container_width=True)
        col_p3.download_button("🧪 Λίστα Προετοιμασίας", data=html_prep, file_name=f"Prep_{sel_hist_date}{file_suffix}.html", mime="text/html", use_container_width=True)
    
    # --- 5. ΣΥΝΘΕΤΗ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ & RECALL TOOL ---
    st.divider()
    st.subheader("🔍 Έλεγχος & Ιχνηλασιμότητα")
    tab_filter, tab_recall_tool = st.tabs(["📋 Αναζήτηση & Φίλτρα", "🚨 Recall Tool (Ανάκληση)"])

    with tab_filter:
        with st.expander("⚙️ Ρυθμίσεις Φίλτρων (Πελάτης, Υλικά, Lot) - Πατήστε το κουμπί για φόρτωση"):
            f1, f2, f3 = st.columns(3)
            search_cust = f1.multiselect("Πελάτης:", sorted(df_all_logs["customer"].unique()) if res_log.data else [], key="filter_cust")
            search_cock = f2.multiselect("Cocktail:", sorted(df_all_logs["cocktail_name"].unique()) if res_log.data else [], key="filter_cock")
            search_ing = f3.multiselect("Πρώτη Ύλη:", sorted(df_all_logs["ingredient_name"].unique()) if res_log.data else [], key="filter_ing")
            search_lot = st.text_input("🔢 Αναζήτηση βάσει οποιουδήποτε LOT:", placeholder="π.χ. 040526 ή L123...", key="filter_lot_txt")
            load_search = st.button("🔄 Φόρτωση Πλήρων Δεδομένων Αναζήτησης")

        if load_search or 'search_data_loaded' in st.session_state:
            st.session_state['search_data_loaded'] = True
            with st.spinner("Φόρτωση δεδομένων από το Cloud..."):
                res_all = supabase.table("production_log").select("*").order("id", desc=True).limit(2000).execute()
                
            if res_all.data:
                df_all = pd.DataFrame(res_all.data).rename(columns={
                    "prod_date": "Ημερομηνία", "customer": "Πελάτης", "cocktail_name": "Cocktail",
                    "lot_cocktail": "LOT_Cocktail", "ingredient_name": "Υλικό", "lot_number": "Lot Number", "pieces": "Τεμάχια"
                })
                dff = df_all.copy()
                if search_cust: dff = dff[dff["Πελάτης"].isin(search_cust)]
                if search_cock: dff = dff[dff["Cocktail"].isin(search_cock)]
                if search_ing: dff = dff[dff["Υλικό"].isin(search_ing)]
                if search_lot: dff = dff[dff.apply(lambda x: search_lot.lower() in str(x).lower(), axis=1)]

                st.write(f"Αποτελέσματα: **{len(dff)}** εγγραφές")
                st.dataframe(dff, use_container_width=True, hide_index=True)

    with tab_recall_tool:
        st.markdown("#### 🚨 Εργαλείο Άμεσης Ανάκλησης Πρώτων Υλών")
        st.write("Αν ένας προμηθευτής αναφέρει πρόβλημα, εισάγετε το **Lot Number** ή την **Ημερομηνία Λήξης** της πρώτης ύλης παρακάτω.")
        recall_query = st.text_input("Εισάγετε το Lot Number ή την Ημερομηνία Λήξης προς αναζήτηση:", placeholder="π.χ. LOT-GIN-2024 ή 15/12/2026", key="recall_input_final")
        
        if recall_query:
            search_val = str(recall_query).strip()
            with st.spinner("Σάρωση ιχνηλασιμότητας στο Cloud..."):
                res_affected = supabase.table("production_log").select("*").or_(f"lot_number.ilike.%{search_val}%,expiry_date.ilike.%{search_val}%").execute()
            
            if res_affected.data:
                df_affected = pd.DataFrame(res_affected.data).rename(columns={
                    "prod_date": "Ημερομηνία", "customer": "Πελάτης", "cocktail_name": "Cocktail",
                    "lot_cocktail": "LOT_Cocktail", "ingredient_name": "Υλικό", "lot_number": "Lot Number", "pieces": "Τεμάχια"
                })
                
                st.error(f"⚠️ **Βρέθηκαν {len(df_affected)} εγγραφές υλικών** στην παραγωγή που σχετίζονται με αυτό το στοιχείο!")
                detected_ingredients = df_affected["Υλικό"].dropna().unique().tolist()
                ingredient_title = ", ".join([f"{ing}" for ing in detected_ingredients]) if detected_ingredients else "Άγνωστο Υλικό"
                df_display = df_affected[["Ημερομηνία", "Πελάτης", "Cocktail", "LOT_Cocktail", "Τεμάχια"]].drop_duplicates()
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                affected_cust_list = df_display["Πελάτης"].unique().tolist()
                st.warning(f"📞 **B2B Πελάτες που πρέπει να ειδοποιηθούν άμεσα:** \n\n {', '.join([f'**{c}**' for c in affected_cust_list])}")
                
                html_content = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Αναφορά Άμεσης Ανάκλησης - Cocktail Factory</title><style>
                        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; margin: 30px; line-height: 1.6; }}
                        .header {{ border-bottom: 4px solid #d9534f; padding-bottom: 15px; margin-bottom: 25px; }}
                        .title {{ color: #d9534f; font-size: 26px; font-weight: bold; margin: 0; }}
                        .subtitle {{ color: #666; font-size: 13px; margin-top: 5px; }}
                        .target-box {{ background-color: #f7f7f7; border: 2px solid #d9534f; border-left: 8px solid #d9534f; padding: 15px; margin-bottom: 20px; border-radius: 4px; }}
                        .danger-box {{ background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 15px; margin-bottom: 30px; color: #721c24; }}
                        .cust-list {{ background: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; font-size: 16px; font-weight: bold; color: #856404; margin-bottom: 25px; border-radius: 4px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th {{ background-color: #f1f1f1; border: 1px solid #dee2e6; text-align: left; padding: 12px; font-weight: bold; color: #495057; font-size: 14px; }}
                        td {{ border: 1px solid #dee2e6; text-align: left; padding: 12px; font-size: 14px; }}
                        .badge {{ background-color: #d9534f; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
                    </style></head><body>
                    <div class="header"><div class="title">🚨 COCKTAIL FACTORY - ΕΚΘΕΣΗ ΑΝΑΚΛΗΣΗΣ ΠΡΩΤΩΝ ΥΛΩΝ</div><div class="subtitle">Ημερομηνία & Ώρα Αναφοράς: {datetime.now(greece_tz).strftime('%d/%m/%Y %H:%M')}</div></div>
                    <div class="target-box"><h2>🎯 ΣΤΟΧΟΣ ΑΝΑΚΛΗΣΗΣ</h2><p><strong>Πρώτη Ύλη:</strong> {ingredient_title}</p><p><strong>LOT / Ημ. Λήξης που αναζητήθηκε:</strong> <span class="badge" style="font-size: 14px;">{search_val}</span></p></div>
                    <div class="danger-box"><div>⚠️ ΣΤΟΙΧΕΙΑ ΕΛΕΓΧΟΥ & ΙΧΝΗΛΑΣΙΜΟΤΗΤΑΣ</div><div>Συνολικές εγγραφές παραγωγής που εντοπίστηκαν: <strong>{len(df_affected)}</strong></div></div>
                    <h3 style="color: #495057; margin-bottom: 10px;">📞 Λίστα Επείγουσας Ειδοποίησης Πελατών (B2B):</h3><div class="cust-list">{', '.join([f'{c}' for c in affected_cust_list])}</div>
                    <h3 style="color: #495057; margin-bottom: 5px;">📋 Αναλυτικό Πλάνο Διανομής Μολυσμένων Παρτίδων</h3>
                    <table><thead><tr><th>Ημερομηνία</th><th>Πελάτης B2B</th><th>Έτοιμο Προϊόν (Cocktail)</th><th>LOT Τελικού Προϊόντος</th><th>Ποσότητα (Τεμάχια)</th></tr></thead><tbody>
                """
                for _, row in df_display.iterrows(): html_content += f"<tr><td>{row['Ημερομηνία']}</td><td><strong>{row['Πελάτης']}</strong></td><td>{row['Cocktail']}</td><td><span class='badge'>{row['LOT_Cocktail']}</span></td><td>{int(row['Τεμάχια'])} τμχ</td></tr>"
                html_content += """</tbody></table><div class="footer">Το έγγραφο αυτό αποτελεί επίσημο αντίγραφο ιχνηλασιμότητας από το λογισμικό Cocktail Factory.<br>Υπεύθυνος Εργαστηρίου: ___________________________ &nbsp;&nbsp;&nbsp;&nbsp; Υπογραφή: ___________________________</div></body></html>"""
                
                safe_file_name = search_val.replace("/", "_")
                st.download_button(label="📄 Λήψη Έκθεσης Ανάκλησης (Έτοιμο HTML)", data=html_content, file_name=f"RECALL_REPORT_{safe_file_name}.html", mime="text/html", use_container_width=True)
            else:
                st.success("✅ Καμία παραγωγή δεν βρέθηκε με αυτό το Lot. Το στοκ σας είναι ασφαλές!")
    
    # --- 6. ΕΚΤΥΠΩΣΗ ΠΛΗΡΟΥΣ ΙΣΤΟΡΙΚΟΥ ---
    st.divider()
    st.subheader("📊 Γενικό Αρχείο Παραγωγής")
    
    if st.button("📑 Προετοιμασία Πλήρους Ιστορικού για Εκτύπωση"):
        with st.spinner("Λήψη όλων των δεδομένων από το Cloud..."):
            res_full_hist = supabase.table("production_log").select("*").execute()
            
        if res_full_hist.data:
            df_raw_hist = pd.DataFrame(res_full_hist.data).rename(columns={"prod_date": "Ημερομηνία", "customer": "Πελάτης", "cocktail_name": "Cocktail", "lot_cocktail": "LOT_Cocktail", "pieces": "Τεμάχια"})
            df_raw_hist['temp_date'] = pd.to_datetime(df_raw_hist['Ημερομηνία'], format='%d/%m/%Y')
            df_full_hist = df_raw_hist.sort_values(by='temp_date', ascending=False).drop_duplicates(subset=["Ημερομηνία", "Πελάτης", "Cocktail", "LOT_Cocktail"])
    
            full_html = f"""<html><head><meta charset='UTF-8'><style>
                    body {{ font-family: 'Helvetica', sans-serif; padding: 20px; }}
                    h1 {{ text-align: center; color: #2c3e50; border-bottom: 3px solid #2c3e50; }}
                    .summary {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #dee2e6; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th {{ background-color: #2c3e50; color: white; padding: 10px; font-size: 12px; text-transform: uppercase; }}
                    td {{ border: 1px solid #ddd; padding: 8px; font-size: 11px; }}
                    .badge-lot {{ background: #d32f2f; color: white; padding: 2px 5px; border-radius: 3px; font-weight: bold; }}
                </style></head><body>
                <h1>ΚΑΤΑΣΤΑΣΗ ΟΛΙΚΗΣ ΠΑΡΑΓΩΓΗΣ - CABCLUB</h1><div class='summary'>Συνολικά Cocktail: <b>{len(df_full_hist)}</b><br>Ημερομηνία: {datetime.now(greece_tz).strftime('%d/%m/%Y %H:%M')}</div>
                <table><thead><tr><th>Ημ/νία</th><th>Πελάτης</th><th>Cocktail</th><th>LOT</th><th>Τμχ</th></tr></thead><tbody>
            """
            for _, row in df_full_hist.iterrows(): full_html += f"<tr><td>{row['Ημερομηνία']}</td><td>{row['Πελάτης']}</td><td><b>{row['Cocktail']}</b></td><td><span class='badge-lot'>{row['LOT_Cocktail']}</span></td><td>{row['Τεμάχια']}</td></tr>"
            full_html += "</tbody></table></body></html>"
    
            st.download_button(label="📥 Λήψη Πλήρους Ιστορικού (HTML)", data=full_html, file_name=f"Full_Production_History_{datetime.now(greece_tz).strftime('%d_%m_%y')}.html", mime="text/html")
# --- 1.6 ΣΥΝΤΗΡΗΣΗ & HACCP (ULΤΙΜΑΤΕ VERSION) ---
elif page == "🧼 Συντήρηση & HACCP":
    st.header("🧼 Ψηφιακό Μητρώο HACCP & Καθαρισμού")

    # --- ΒΟΗΘΗΤΙΚΗ ΣΥΝΑΡΤΗΣΗ ΓΙΑ REPORT ΜΕ ΥΠΟΓΡΑΦΗ ---
    def generate_haccp_report_html(data, title="ΑΡΧΕΙΟ HACCP"):
        rows_html = ""
        for _, r in data.iterrows():
            extra_info = r['cleaner'] if r['log_type'] == "Καθαρισμός" else r['notes']
            rows_html += f"<tr><td>{r['date']}</td><td>{r['time']}</td><td>{r['item']}</td><td>{r['value']}</td><td>{r['status']}</td><td>{extra_info}</td><td>{r['user_name']}</td></tr>"
        
        return f"""
        <html><head><meta charset='UTF-8'><style>
            body {{ font-family: DejaVu Sans, Arial, sans-serif; padding: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #1e3a8a; color: white; padding: 10px; font-size: 12px; }}
            td {{ border: 1px solid #000; padding: 8px; text-align: center; font-size: 10px; }}
            h2 {{ text-align: center; color: #1e3a8a; text-transform: uppercase; }}
            .signature-section {{ margin-top: 50px; width: 100%; }}
            .sig-box {{ float: right; width: 250px; text-align: center; border-top: 1px solid #000; padding-top: 10px; margin-top: 20px; font-weight: bold; }}
            .date-box {{ float: left; width: 200px; text-align: center; border-top: 1px solid #000; padding-top: 10px; margin-top: 20px; }}
        </style></head><body>
            <h2>CABCLUB COCKTAILS - {title}</h2>
            <table><thead><tr><th>Ημ/νία</th><th>Ώρα</th><th>Στοιχείο</th><th>Τιμή/Τύπος</th><th>Κατάσταση</th><th>Λεπτομέρειες/Καθαριστικά</th><th>Υπεύθυνος</th></tr></thead>
            <tbody>{rows_html}</tbody></table>
            <div class='signature-section'>
                <div class='date-box'>Ημερομηνία Ελέγχου</div>
                <div class='sig-box'>Υπογραφή Υπευθύνου</div>
            </div>
        </body></html>"""

    # --- ΚΕΝΤΡΙΚΑ ΠΕΔΙΑ ---
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        staff_name = st.text_input("👤 Υπεύθυνος Καταγραφής:", placeholder="Ονοματεπώνυμο...")
    with col_u2:
        selected_date = st.date_input("📅 Ημερομηνία:", value=datetime.now(greece_tz))
        date_str = selected_date.strftime("%d/%m/%Y")
    
    tab1, tab2, tab3 = st.tabs(["🌡️ Θερμοκρασίες", "🧹 Checklists Καθαρισμού", "📋 Αρχείο & Εκτυπώσεις"])
    
    # --- TAB 1: ΘΕΡΜΟΚΡΑΣΙΕΣ ---
    with tab1:
        st.subheader("🌡️ Έλεγχος Ψυκτικών Θαλάμων")
        with st.form("temp_form_final_supabase"):
            c1, c2, c3 = st.columns([2, 1, 2])
            device = c1.selectbox("Συσκευή:", ["Ψυγείο 1", "Ψυγείο 2", "Ψυγείο 3", "Κατάψυξη 1", "Κατάψυξη 2"])
            is_freezer = "Κατάψυξη" in device
            temp = c2.number_input("Θερμοκρασία (°C):", value=-18.0 if is_freezer else 4.0, step=0.5)
            notes = c3.text_input("Παρατηρήσεις / Διορθωτικές Ενέργειες:")
            is_ok = not ((is_freezer and temp > -15.0) or (not is_freezer and temp > 7.0))
            
            if st.form_submit_button("💾 Αποθήκευση Μέτρησης", type="primary"):
                if staff_name:
                    log = {"date": date_str, "time": datetime.now(greece_tz).strftime("%H:%M"), "user_name": staff_name, 
                           "log_type": "Θερμοκρασία", "item": device, "value": f"{temp}°C", 
                           "status": "ΕΝΤΟΣ ΟΡΙΩΝ" if is_ok else "ΕΚΤΟΣ ΟΡΙΩΝ", "cleaner": "-", "notes": notes if notes else "-"}
                    supabase.table("haccp_log").insert([log]).execute()
                    st.success("Καταγράφηκε!")
                    time.sleep(1); st.rerun()
                else: st.error("Συμπληρώστε το όνομα!")

    # --- TAB 2: CHECKLISTS ΚΑΘΑΡΙΣΜΟΥ (ΑΚΡΙΒΩΣ ΟΙ ΕΡΓΑΣΙΕΣ ΣΟΥ) ---
    with tab2:
        # --- 📌 ΠΙΝΑΚΑΣ ΑΝΑΦΟΡΑΣ ΚΑΘΑΡΙΣΤΙΚΩΝ ---
        st.markdown("##### 📌 Πίνακας Αναφοράς Εγκεκριμένων Καθαριστικών")
        
        reference_data = {
            "Καθαριστικό / Απολυμαντικό": [
                "🧪 Drolio", 
                "🧪 P3-Steril", 
                "🧪 Eco-Bac Foam Plus", 
                "🧪 Swaz", 
                "🧪 Crystal Class Cleaner Ammonia"
            ],
            "Ενδεδειγμένη Εφαρμογή & Διαδικασία": [
                "Σκεύη, εργαλεία",
                "Εξοπλισμός, επιφάνειες που έρχονται σε επαφή με τρόφιμα, ψυγεία/καταψύκτες, ράφια",
                "Δάπεδα χώρου παρασκευής, δάπεδα αποθηκών",
                "Τουαλέτες & αποδυτήρια, τοίχοι",
                "Τζαμαρίες, παράθυρα, οροφές, φώτα, εξαερισμός"
            ]
        }
        # Εμφάνιση του πίνακα όμορφα και καθαρά
        st.table(pd.DataFrame(reference_data).set_index("Καθαριστικό / Απολυμαντικό"))
        
        st.divider()

        # Οι δικές σου αναλυτικές λίστες εργασιών
        tasks_data = {
            "Ημερήσιος Καθαρισμός": ["Σκεύη (ταψιά, πιάτα κτλ)", "Εργαλεία (μαχαίρια, κουτάλια, σπάτουλες κτλ)", "Εξοπλισμός (μηχανές τεμαχισμού, μηχανές επεξεργασίας κτλ)", "Επιφάνειες που έρχονται σε επαφή με τρόφιμα", "Δάπεδα χώρου παραγωγής, πόμολα και διακόπτες", "Τουαλέτες - Αποδυτήρια", "Απομάκρυνση απορριμμάτων", "Δάπεδα χώρου πώλησης" ],
            "Εβδομαδιαίος Καθαρισμός": ["Δάπεδα αποθηκών", "Ψυγεία - καταψύκτες", "Φούρνοι - θερμοθάλαμοι", "Τοίχοι", "Κάδοι απορριμμάτων", "Τζαμαρίες", "Καρέκλες - τραπέζια", "Ράφια"],
            "Μηνιαίος Καθαρισμός": ["Παράθυρα", "Οροφές", "Φώτα", "Εξαερισμός"]
        }
        
        # Η λίστα με τα εγκεκριμένα καθαριστικά σου για το HACCP
        approved_cleaners = [
            "Drolio", 
            "P3-Steril", 
            "Eco-Bac Foam Plus", 
            "Swaz", 
            "Crystal Class Cleaner Ammonia",
            "Αντισηπτικό Χεριών",
            "Νερό (Σκέτο)"
        ]
        
        category = st.radio("Πρόγραμμα:", list(tasks_data.keys()), horizontal=True)
        with st.form(f"cleaning_{category}"):
            st.markdown(f"#### {category}")
            responses = []
            
            # Δημιουργία των στηλών (πιο πλατιά στήλη για τα drop-downs)
            for i, task in enumerate(tasks_data[category]):
                c_task, c_clean = st.columns([0.4, 0.6])
                
                # Checkbox για το αν έγινε η εργασία
                done = c_task.checkbox(task, key=f"c_{category}_{i}")
                
                # Multiselect αντί για πληκτρολόγηση κειμένου
                selected_cleaners = c_clean.multiselect(
                    "Καθαριστικό", 
                    options=approved_cleaners,
                    key=f"cl_{category}_{i}", 
                    placeholder="Επιλέξτε καθαριστικό(ά)...", 
                    label_visibility="collapsed"
                )
                
                if done: 
                    # Φτιάχνει ένα ωραίο string με τα υλικά που επέλεξες
                    cleaners_str = ", ".join(selected_cleaners) if selected_cleaners else "Χωρίς Καθαριστικό"
                    responses.append(f"{task} ({cleaners_str})")
            
            st.divider()
            notes = st.text_input("📝 Παρατηρήσεις / Προβλήματα:", placeholder="π.χ. Έλλειψη απορρυπαντικού...", key=f"notes_{category}")
            
            if st.form_submit_button("🚀 Οριστικοποίηση"):
                if staff_name and len(responses) == len(tasks_data[category]):
                    log = {"date": date_str, "time": datetime.now(greece_tz).strftime("%H:%M"), "user_name": staff_name, 
                           "log_type": "Καθαρισμός", "item": category, "value": "ΟΛΟΚΛΗΡΩΘΗΚΕ", 
                           "status": "ΟΚ", "cleaner": " | ".join(responses), "notes": notes if notes else "-"}
                    supabase.table("haccp_log").insert([log]).execute()
                    st.success("Ενημερώθηκε!")
                    time.sleep(1)
                    st.rerun()
                else: 
                    st.error("Επιλέξτε όλες τις εργασίες (check) και βάλτε το όνομά σας πάνω-πάνω!")

    # --- TAB 3: ΑΡΧΕΙΟ & ΕΚΤΥΠΩΣΕΙΣ ---
    with tab3:
        res = supabase.table("haccp_log").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['dt_obj'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
            df = df.sort_values(by=['dt_obj', 'time'], ascending=[False, False])

            # --- ΦΙΛΤΡΑ ΕΚΤΥΠΩΣΗΣ ---
            with st.expander("🖨️ Επιλεκτική Εκτύπωση (Φίλτρα)", expanded=False):
                c1, c2 = st.columns(2)
                p_days = c1.multiselect("Ημερομηνίες:", options=df['date'].unique())
                p_types = c2.multiselect("Τύπος:", ["Θερμοκρασία", "Καθαρισμός"], default=["Θερμοκρασία", "Καθαρισμός"])
                df_rep = df.copy()
                if p_days: df_rep = df_rep[df_rep['date'].isin(p_days)]
                df_rep = df_rep[df_rep['log_type'].isin(p_types)]
                st.download_button("📥 Λήψη Επιλεγμένου Report", generate_haccp_report_html(df_rep), "HACCP_Custom.html", "text/html", use_container_width=True)

            st.divider()
            
            # --- ΙΣΤΟΡΙΚΟ ΜΕ NESTED EXPANDERS ---
            greek_months = {1:"Ιανουάριος", 2:"Φεβρουάριος", 3:"Μάρτιος", 4:"Απρίλιος", 5:"Μάιος", 6:"Ιούνιος", 
                            7:"Ιούλιος", 8:"Αύγουστος", 9:"Σεπτέμβριος", 10:"Οκτώβριος", 11:"Νοέμβριος", 12:"Δεκέμβριος"}
            df['m_label'] = df['dt_obj'].dt.month.map(greek_months) + " " + df['dt_obj'].dt.year.astype(str)

            for m in df['m_label'].unique():
                with st.expander(f"📅 {m}", expanded=False):
                    m_df = df[df['m_label'] == m]
                    for d in m_df['date'].unique():
                        with st.expander(f"🗓️ Ημέρα: {d}", expanded=False):
                            d_df = m_df[m_df['date'] == d]
                            for _, row in d_df.iterrows():
                                col_txt, col_del = st.columns([4, 1])
                                with col_txt:
                                    ic = "🌡️" if row['log_type']=="Θερμοκρασία" else "🧹"
                                    st.write(f"**{ic} {row['item']}** ({row['time']}) -> {row['value']}")
                                    if row['cleaner'] != "-": st.caption(f"🧪 {row['cleaner']}")
                                with col_del:
                                    if st.button("🗑️", key=f"del_{row['id']}"):
                                        supabase.table("haccp_log").delete().eq("id", row['id']).execute()
                                        st.rerun()

            # --- ΚΟΥΜΠΙ ΕΚΤΥΠΩΣΗΣ ΟΛΩΝ ΣΤΟ ΤΕΛΟΣ ---
            st.divider()
            st.download_button(
                label="🖨️ ΕΚΤΥΠΩΣΗ ΟΛΟΥ ΤΟΥ ΑΡΧΕΙΟΥ (Χωρίς Φίλτρα)",
                data=generate_haccp_report_html(df, "ΠΛΗΡΕΣ ΜΗΤΡΩΟ HACCP"),
                file_name="HACCP_Full_Archive.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )
        else:
            st.info("Καμία καταγραφή.")


# --- 10. ΠΕΛΑΤΟΛΟΓΙΟ (CRM - ΜΕ ΑΦΜ, ΕΚΠΤΩΣΗ & ΙΣΤΟΡΙΚΟ ΠΡΟΣΦΟΡΩΝ) ---
elif page == "👥 Πελατολόγιο":
    st.header("👥 Διαχείριση Πελατολογίου")
    
    import pandas as pd
    import time
    import re
    from datetime import datetime

    # 1. ΦΟΡΤΩΣΗ ΠΕΛΑΤΩΝ & ΣΥΝΤΑΓΩΝ
    res_cust = supabase.table("customers").select("*").order("name").execute()
    df_cust = pd.DataFrame(res_cust.data) if res_cust.data else pd.DataFrame()

    res_rec = supabase.table("recipes").select("name, catalog_price").execute()
    df_recipes = pd.DataFrame(res_rec.data) if res_rec.data else pd.DataFrame()
    recipe_prices = dict(zip(df_recipes['name'], df_recipes['catalog_price'])) if not df_recipes.empty else {}

    # ΠΡΟΣΘΗΚΗ 3ου TAB ΓΙΑ ΤΟ ΙΣΤΟΡΙΚΟ ΤΩΝ ΔΩΡΩΝ ΚΑΙ ΤΙΣ ΕΚΠΤΩΣΕΙΣ
    tab_crm1, tab_crm2, tab_crm3 = st.tabs([
        "📋 Καρτέλα & Ιστορικό Αγορών", 
        "➕ Προσθήκη Νέου Πελάτη", 
        "🏷️ Προσφορές και εκπτώσεις"
    ])

    # =========================================================================
    # TAB 1: ΚΑΡΤΕΛΑ & ΙΣΤΟΡΙΚΟ (ΜΟΝΟ ΠΡΟΒΟΛΗ & ΒΑΣΙΚΗ ΕΠΕΞΕΡΓΑΣΙΑ)
    # =========================================================================
    with tab_crm1:
        if not df_cust.empty:
            col_crm_a, col_crm_b = st.columns([1, 2.5])
            
            with col_crm_a:
                st.subheader("👤 Στοιχεία")
                sel_name = st.selectbox("Επιλέξτε Πελάτη:", options=df_cust["name"].tolist(), key="crm_select_final")
                customer_data = df_cust[df_cust["name"] == sel_name].iloc[0]
                
                st.info(f"""
                **Στοιχεία Επικοινωνίας:**
                * 📞 {customer_data.get('phone') if customer_data.get('phone') else '-'}
                * ✉️ {customer_data.get('email') if customer_data.get('email') else '-'}
                * 📍 {customer_data.get('address') if customer_data.get('address') else '-'}
                
                **Φορολογικά & Εμπορικά:**
                * 🆔 **ΑΦΜ:** {customer_data.get('afm') if customer_data.get('afm') else '-'}
                * 📉 **Τρέχουσα Γενική Έκπτωση:** {customer_data.get('discount') if customer_data.get('discount') else '0'}%
                ---
                **Σημειώσεις:**
                {customer_data.get('notes') if customer_data.get('notes') else 'Καμία σημείωση'}
                """)
                
                with st.expander("📝 Επεξεργασία Βασικών Στοιχείων"):
                    with st.form(f"edit_cust_{customer_data['id']}"):
                        e_name = st.text_input("Όνομα / Επωνυμία", value=customer_data['name'])
                        e_afm = st.text_input("ΑΦΜ", value=customer_data.get('afm', ''))
                        e_phone = st.text_input("Τηλέφωνο", value=customer_data['phone'])
                        e_email = st.text_input("Email", value=customer_data['email'])
                        e_addr = st.text_area("Διεύθυνση", value=customer_data['address'])
                        e_notes = st.text_area("Σημειώσεις", value=customer_data['notes'])
                        
                        if st.form_submit_button("💾 Ενημέρωση Στοιχείων"):
                            supabase.table("customers").update({
                                "name": e_name, "afm": e_afm, 
                                "phone": e_phone, "email": e_email, "address": e_addr, "notes": e_notes
                            }).eq("id", customer_data["id"]).execute()
                            st.success("✅ Τα στοιχεία ενημερώθηκαν! (Οι εκπτώσεις ρυθμίζονται στο 3ο Tab)")
                            st.rerun()

                st.divider()
                if st.button("🗑️ Διαγραφή Πελάτη", type="secondary"):
                    supabase.table("customers").delete().eq("id", customer_data["id"]).execute()
                    st.success("Ο πελάτης διαγράφηκε!")
                    st.rerun()

            with col_crm_b:
                st.subheader(f"📊 Ιστορικό Παραγωγής: {sel_name}")
                res_prod = supabase.table("production_log").select("prod_date, cocktail_name, pieces, lot_cocktail, prod_time").eq("customer", sel_name).order("prod_date", desc=True).execute()
                
                if res_prod.data:
                    df_p = pd.DataFrame(res_prod.data)
                    df_p_clean = df_p.drop_duplicates(subset=["prod_date", "prod_time", "lot_cocktail", "cocktail_name"])
                    
                    st.dataframe(
                        df_p_clean.rename(columns={"prod_date": "Ημερομηνία", "cocktail_name": "Cocktail", "pieces": "Τεμάχια"})[["Ημερομηνία", "Cocktail", "Τεμάχια"]],
                        use_container_width=True, hide_index=True
                    )
                    st.metric("Συνολικές Αγορές (Τεμάχια)", f"{int(df_p_clean['pieces'].sum())} τμχ")
                else:
                    st.info("Δεν βρέθηκε ιστορικό παραγωγής για αυτόν τον πελάτη.")

                st.divider()

                st.subheader("💰 Οικονομικό Ιστορικό")
                res_orders = supabase.table("b2b_orders").select("*").eq("customer_name", sel_name).order("created_at", desc=True).execute()
                
                if res_orders.data:
                    with st.expander("🖨️ Εξαγωγή & Εκτύπωση Ιστορικού (PDF/HTML)", expanded=False):
                        st.write("Δημιουργήστε μια επαγγελματική αναφορά για τον πελάτη.")
                        
                        export_mode = st.radio("Τι θέλετε να περιλαμβάνει η αναφορά;", ["Όλο το Ιστορικό Αγορών", "Συγκεκριμένη Παραγγελία"], horizontal=True)
                        
                        orders_to_export = []
                        if export_mode == "Συγκεκριμένη Παραγγελία":
                            order_dict = {o['id']: f"{str(o['created_at'])[:10]} | Αξία: {float(o['total_amount']):.2f}€" for o in res_orders.data}
                            sel_export_id = st.selectbox("Επιλέξτε Παραγγελία για εξαγωγή:", options=list(order_dict.keys()), format_func=lambda x: order_dict[x])
                            orders_to_export = [o for o in res_orders.data if o['id'] == sel_export_id]
                        else:
                            orders_to_export = res_orders.data
                            
                        if st.button("📄 Δημιουργία Αναφοράς"):
                            total_export_value = sum([float(o['total_amount']) for o in orders_to_export])
                            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                            
                            html_content = f"""
                            <!DOCTYPE html>
                            <html lang="el">
                            <head>
                                <meta charset="UTF-8">
                                <title>Καρτέλα Πελάτη - {sel_name}</title>
                                <style>
                                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; background-color: #fff; padding: 20px; }}
                                    .container {{ max-width: 900px; margin: auto; border: 1px solid #ddd; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }}
                                    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1a3a5f; padding-bottom: 10px; margin-bottom: 20px; }}
                                    .header h1 {{ color: #1a3a5f; margin: 0; font-size: 24px; }}
                                    .header p {{ margin: 0; color: #666; font-size: 12px; }}
                                    .cust-info {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #1a3a5f; }}
                                    .cust-info p {{ margin: 5px 0; font-size: 14px; }}
                                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }}
                                    th, td {{ border: 1px solid #eee; padding: 10px; text-align: left; vertical-align: top; }}
                                    th {{ background-color: #1a3a5f; color: white; font-weight: normal; }}
                                    tr:nth-child(even) {{ background-color: #fafafa; }}
                                    .total-row {{ background-color: #e8f4f8; font-weight: bold; font-size: 16px; }}
                                    .details-col {{ line-height: 1.5; }}
                                    .amount-col {{ text-align: right; white-space: nowrap; font-weight: bold; color: #2e7d32; }}
                                    .footer {{ text-align: center; margin-top: 30px; font-size: 11px; color: #999; border-top: 1px solid #ddd; padding-top: 10px; }}
                                </style>
                            </head>
                            <body>
                                <div class="container">
                                    <div class="header">
                                        <h1>Καρτέλα Κίνησης Πελάτη</h1>
                                        <p>Ημ/νια Εκτύπωσης: {now_str}<br>DC CABCLUB System</p>
                                    </div>
                                    
                                    <div class="cust-info">
                                        <strong>Στοιχεία Πελάτη:</strong><br>
                                        <p><b>Επωνυμία:</b> {sel_name} | <b>ΑΦΜ:</b> {customer_data.get('afm', '-')}</p>
                                        <p><b>Τηλέφωνο:</b> {customer_data.get('phone', '-')} | <b>Email:</b> {customer_data.get('email', '-')}</p>
                                        <p><b>Διεύθυνση:</b> {customer_data.get('address', '-')}</p>
                                    </div>
                                    
                                    <table>
                                        <thead>
                                            <tr>
                                                <th width="15%">Ημερομηνία</th>
                                                <th width="70%">Ανάλυση Παραγγελίας (Είδη & Εκπτώσεις)</th>
                                                <th width="15%" style="text-align: right;">Τελική Αξία</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                            """
                            
                            for o in orders_to_export:
                                date_str = str(o['created_at'])[:10]
                                date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
                                
                                formatted_details = str(o['order_details']).replace('\n', '<br>')
                                formatted_details = formatted_details.replace('ΔΩΡΑ', '<strong style="color:#d32f2f;">ΔΩΡΑ</strong>')
                                formatted_details = formatted_details.replace('ΕΚΠΤΩΣΕΙΣ', '<strong style="color:#1976d2;">ΕΚΠΤΩΣΕΙΣ</strong>')
                                
                                html_content += f"""
                                            <tr>
                                                <td>{date_formatted}</td>
                                                <td class="details-col">{formatted_details}</td>
                                                <td class="amount-col">{float(o['total_amount']):.2f} €</td>
                                            </tr>
                                """
                            
                            html_content += f"""
                                            <tr class="total-row">
                                                <td colspan="2" style="text-align: right;">Γενικό Σύνολο:</td>
                                                <td class="amount-col" style="color: #1a3a5f;">{total_export_value:.2f} €</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                    
                                    <div class="footer">
                                        Αυτή η αναφορά δημιουργήθηκε αυτόματα από το σύστημα διαχείρισης παραγωγής.<br>
                                        Δεν αποτελεί φορολογικό στοιχείο (τιμολόγιο/απόδειξη).
                                    </div>
                                </div>
                            </body>
                            </html>
                            """
                            
                            st.download_button(
                                label="📥 Λήψη Αναφοράς (HTML / Print to PDF)",
                                data=html_content,
                                file_name=f"Customer_Report_{sel_name.replace(' ', '_')}.html",
                                mime="text/html",
                                type="primary"
                            )
                            st.info("💡 **Οδηγία:** Ανοίξτε το αρχείο που κατέβηκε στον browser σας (Chrome/Safari) και πατήστε **Ctrl+P** (ή Cmd+P στο Mac) για να το αποθηκεύσετε ως ένα τέλειο PDF ή να το εκτυπώσετε!")
                    
                    st.divider()

                    # Εμφάνιση των παραγγελιών στο UI
                    for order in res_orders.data:
                        order_id = order['id']
                        current_amt = float(order['total_amount'])
                        details = str(order['order_details'])
                        
                        base_amt = current_amt
                        match_base = re.search(r"Αρχική Αξία:\s*([\d\.]+)", details)
                        if match_base:
                            base_amt = float(match_base.group(1))

                        with st.expander(f"🛒 Παραγγελία {str(order['created_at'])[:10]} | {current_amt:.2f}€"):
                            st.info(f"**Αρχική Αξία:** {base_amt:.2f} €\n\n**Τελική Χρέωση:** {current_amt:.2f} €")
                            st.caption(f"Λεπτομέρειες Παραγγελίας:\n{details}")
                            
                            # Κουμπί διαγραφής παραγγελίας
                            if st.button("🗑️ Διαγραφή Παραγγελίας", key=f"del_o_{order_id}"):
                                delete_order_and_production_safely(order_id, sel_name, order['created_at'], order['order_details'])
                                st.warning("🔄 Η παραγγελία και τα υλικά παραγωγής διαγράφηκαν επιτυχώς!")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.info("Δεν έχουν δημιουργηθεί ακόμα οικονομικές εγγραφές.")
        else:
            st.warning("⚠️ Η λίστα πελατών είναι άδεια.")

    # =========================================================================
    # TAB 2: ΠΡΟΣΘΗΚΗ ΝΕΟΥ ΠΕΛΑΤΗ
    # =========================================================================
    with tab_crm2:
        st.subheader("➕ Καταχώρηση Νέου Πελάτη")
        with st.form("new_customer_form_final", clear_on_submit=True):
            n_name = st.text_input("Όνομα / Επωνυμία *")
            n_afm = st.text_input("ΑΦΜ")
            n_discount = st.text_input("Αρχική Γενική Έκπτωση (%)", value="0")
            n_phone = st.text_input("Τηλέφωνο")
            n_email = st.text_input("Email")
            n_addr = st.text_area("Διεύθυνση")
            n_notes = st.text_area("Σημειώσεις")
            
            if st.form_submit_button("💾 Αποθήκευση"):
                if n_name:
                    supabase.table("customers").insert({
                        "name": n_name, "afm": n_afm, "discount": n_discount,
                        "phone": n_phone, "email": n_email, "address": n_addr, "notes": n_notes
                    }).execute()
                    st.success("✅ Ο πελάτης προστέθηκε επιτυχώς!")
                    st.rerun()
                else:
                    st.error("Το όνομα είναι υποχρεωτικό!")

    # =========================================================================
    # 🌟 TAB 3: ΤΟ ΣΤΡΑΤΗΓΕΙΟ ΤΩΝ ΕΚΠΤΩΣΕΩΝ & ΠΡΟΣΦΟΡΩΝ
    # =========================================================================
    with tab_crm3:
        st.subheader("🏷️ Κεντρική Διαχείριση Προσφορών & Εκπτώσεων")
        
        sel_cust_offers = st.selectbox("👤 Επιλέξτε Πελάτη για διαχείριση:", options=["-- Επιλέξτε --"] + sorted(df_cust["name"].tolist()) if not df_cust.empty else ["-- Επιλέξτε --"], key="offers_c")
        
        if sel_cust_offers != "-- Επιλέξτε --":
            st.divider()
            
            # --- ΕΝΟΤΗΤΑ 1: ΓΕΝΙΚΗ ΕΚΠΤΩΣΗ ---
            st.markdown("### 📉 1. Γενική Έκπτωση Πελάτη")
            current_discount = df_cust[df_cust["name"] == sel_cust_offers].iloc[0].get('discount', 0)
            if pd.isna(current_discount) or not current_discount: current_discount = 0.0
            
            col_d1, col_d2 = st.columns([1, 2])
            new_global_discount = col_d1.number_input("Σταθερή Έκπτωση (%) στο σύνολο των αγορών του:", min_value=0.0, max_value=100.0, value=float(current_discount), step=0.5)
            
            if col_d1.button("💾 Αποθήκευση Γενικής Έκπτωσης", type="secondary"):
                supabase.table("customers").update({"discount": new_global_discount}).eq("name", sel_cust_offers).execute()
                st.success(f"Η γενική έκπτωση άλλαξε σε {new_global_discount}%!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            
            st.divider()

            # --- ΕΝΟΤΗΤΑ 2: ΕΜΠΟΡΙΚΗ ΠΑΡΕΜΒΑΣΗ ΣΕ ΠΑΡΑΓΓΕΛΙΑ ---
            st.markdown("### 🎁 2. Εφαρμογή Δώρων & Ειδικών Εκπτώσεων σε Παραγγελία")
            st.write("Επιλέξτε μια παραγγελία. Για κάθε κοκτέιλ της, μπορείτε να ορίσετε δωρεάν τεμάχια ή/και ειδική έκπτωση σε συγκεκριμένο αριθμό τεμαχίων (π.χ. 10% στο Negroni).")

            res_orders = supabase.table("b2b_orders").select("*").eq("customer_name", sel_cust_offers).order("created_at", desc=True).limit(50).execute()
            if res_orders.data:
                df_orders = pd.DataFrame(res_orders.data)
                order_dict = {}
                for _, r in df_orders.iterrows():
                    dt = pd.to_datetime(r['created_at'])
                    dt_str = dt.tz_convert('Europe/Athens').strftime('%d/%m %H:%M') if dt.tzinfo else dt.strftime('%d/%m %H:%M')
                    order_dict[r['id']] = f"📅 {dt_str} | Αξία: {float(r['total_amount']):.2f}€"
                
                sel_order_id = st.selectbox("🛒 Επιλογή Παραγγελίας:", options=list(order_dict.keys()), format_func=lambda x: order_dict[x], key="gift_o")
                
                if sel_order_id:
                    selected_order = df_orders[df_orders['id'] == sel_order_id].iloc[0]
                    current_details = selected_order['order_details']
                    
                    # Προβολή καθαρών λεπτομερειών (κρύβουμε τις παλιές σημειώσεις δώρων)
                    clean_display_details = str(current_details).split("\n\n--- ΔΩΡΑ")[0].split("\n\n--- ΕΙΔΙΚΕΣ")[0]
                    st.info(f"**Περιεχόμενο Παραγγελίας:**\n{clean_display_details}")
                    
                    order_dt = pd.to_datetime(selected_order['created_at'])
                    prod_date_str = order_dt.strftime('%d/%m/%Y')
                    
                    # Διαβάζουμε και τις νέες στήλες έκπτωσης από τη Supabase
                    res_prod = supabase.table("production_log").select("cocktail_name, pieces, free_pieces, discounted_pieces, discount_pct, prod_time").eq("customer", sel_cust_offers).eq("prod_date", prod_date_str).execute()
                    
                    if res_prod.data:
                        df_prod = pd.DataFrame(res_prod.data).drop_duplicates(subset=["cocktail_name", "prod_time"])
                        
                        with st.form("apply_gifts_and_discounts_form"):
                            inputs = {}
                            st.markdown("##### ⚙️ Ρυθμίσεις ανά Κωδικό Παραγγελίας")
                            
                            h1, h2, h3, h4 = st.columns([2.5, 1, 1.2, 1])
                            h1.caption("Κοκτέιλ (Σύνολο Τμχ)")
                            h2.caption("Δωρεάν Τμχ")
                            h3.caption("Τμχ με Έκπτωση")
                            h4.caption("Έκπτωση (%)")
                            
                            for _, prow in df_prod.iterrows():
                                c_name = prow['cocktail_name']
                                t_pcs = int(prow['pieces'])
                                curr_free = int(prow.get('free_pieces', 0)) if pd.notnull(prow.get('free_pieces', 0)) else 0
                                curr_s_pcs = int(prow.get('discounted_pieces', 0)) if pd.notnull(prow.get('discounted_pieces', 0)) else 0
                                curr_s_pct = float(prow.get('discount_pct', 0.0)) if pd.notnull(prow.get('discount_pct', 0.0)) else 0.0
                                
                                c1, c2, c3, c4 = st.columns([2.5, 1, 1.2, 1])
                                c1.write(f"🍹 **{c_name}** ({t_pcs} τμχ)")
                                
                                f_pcs = c2.number_input("Δώρο", min_value=0, max_value=t_pcs, value=curr_free, step=1, key=f"f_{c_name}_{prow['prod_time']}", label_visibility="collapsed")
                                s_pcs = c3.number_input("Τμχ Έκπτωσης", min_value=0, max_value=t_pcs, value=curr_s_pcs, step=1, key=f"s_{c_name}_{prow['prod_time']}", label_visibility="collapsed")
                                s_pct = c4.number_input("% Έκπτωσης", min_value=0.0, max_value=100.0, value=curr_s_pct, step=1.0, key=f"p_{c_name}_{prow['prod_time']}", label_visibility="collapsed")
                                
                                inputs[(c_name, prow['prod_time'])] = {"t_pcs": t_pcs, "f_pcs": f_pcs, "s_pcs": s_pcs, "s_pct": s_pct}
                                
                            if st.form_submit_button("💾 Εφαρμογή & Επανυπολογισμός Παραγγελίας", type="primary"):
                                new_total = 0.0
                                gift_text = ""
                                disc_text = ""
                                
                                cust_discount = float(current_discount)
                                
                                with st.spinner("Επανυπολογισμός αξιών..."):
                                    for key, vals in inputs.items():
                                        c_name, p_time = key
                                        t_pcs = vals["t_pcs"]
                                        f_pcs = vals["f_pcs"]
                                        s_pcs = vals["s_pcs"]
                                        s_pct = vals["s_pct"]
                                        
                                        # Ασφάλεια
                                        if f_pcs + s_pcs > t_pcs:
                                            s_pcs = t_pcs - f_pcs 
                                            
                                        normal_pcs = t_pcs - f_pcs - s_pcs
                                        
                                        # Update παραγωγής
                                        supabase.table("production_log").update({
                                            "free_pieces": f_pcs,
                                            "discounted_pieces": s_pcs,
                                            "discount_pct": s_pct
                                        }).eq("customer", sel_cust_offers).eq("prod_date", prod_date_str).eq("prod_time", p_time).eq("cocktail_name", c_name).execute()
                                        
                                        catalog_p = float(recipe_prices.get(c_name, 0.0))
                                        
                                        # -------------------------------------------------------------
                                        # 🚀 ΑΣΦΑΛΗΣ & ΣΩΣΤΟΣ ΥΠΟΛΟΓΙΣΜΟΣ ΕΚΠΤΩΣΕΩΝ
                                        # -------------------------------------------------------------
                                        
                                        # 1. Βρίσκουμε την τιμή μετά τη γενική έκπτωση του πελάτη (π.χ. 26%)
                                        price_after_global = catalog_p * (1 - (cust_discount / 100))
                                        
                                        # 2. Αξία κανονικών τεμαχίων (χρεώνονται μόνο με το 26%)
                                        cost_normal = normal_pcs * price_after_global
                                        
                                        # 3. Αξία εκπτωτικών τεμαχίων (πάνω στο 26% αφαιρείται έξτρα η ειδική π.χ. 10%)
                                        cost_spec = s_pcs * price_after_global * (1 - (s_pct / 100))
                                        
                                        new_total += (cost_normal + cost_spec)
                                        
                                        if f_pcs > 0:
                                            gift_text += f"🎁 {f_pcs}x {c_name} (ΔΩΡΟ)\n"
                                        if s_pcs > 0:
                                            disc_text += f"📉 {s_pcs}x {c_name} (Έκπτωση {s_pct}%)\n"
                                            
                                    # Ενημέρωση Παραγγελίας
                                    final_details = clean_display_details
                                    if gift_text:
                                        final_details += f"\n\n--- ΔΩΡΑ ΠΟΥ ΕΦΑΡΜΟΣΤΗΚΑΝ ---\n{gift_text}"
                                    if disc_text:
                                        final_details += f"\n\n--- ΕΙΔΙΚΕΣ ΕΚΠΤΩΣΕΙΣ ΚΩΔΙΚΩΝ ---\n{disc_text}"
                                        
                                    supabase.table("b2b_orders").update({"total_amount": new_total, "order_details": final_details}).eq("id", sel_order_id).execute()
                                    
                                    st.success(f"✅ Επιτυχία! Η νέα αξία της παραγγελίας διαμορφώθηκε στα {new_total:.2f} €")
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                    else:
                        st.warning("Δεν βρέθηκε γραμμή παραγωγής (υλικά) για τη συγκεκριμένη παραγγελία.")
            else:
                st.info("Δεν βρέθηκαν προηγούμενες παραγγελίες για αυτόν τον πελάτη.")

# --- 1.5 ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΠΡΩΤΗΣ ΥΛΗΣ (FINAL VERSION - CUSTOM PRICES & CLEAN NUMBERS) ---
elif page == "🔄 Αντικατάσταση":
    st.header("🔄 Καθολική Αντικατάσταση & Οικονομική Πρόγνωση")
    st.info("Σύγκριση Τιμών: Χρησιμοποιούνται οι δικές σας καταχωρημένες τιμές λιανικής. Ο Αντιπρόσωπος υπολογίζεται στο -26%.")

    # Βοηθητική συνάρτηση για καθαρούς αριθμούς (χωρίς περιττά μηδενικά)
    def format_num(n):
        if n is None or n == 0: return "0"
        return f"{n:g}"

    # 1. Ανάκτηση δεδομένων από τη βάση
    res_all_items = supabase.table("recipe_items").select("*").execute()
    df_all_items = pd.DataFrame(res_all_items.data) if res_all_items.data else pd.DataFrame()
    
    if not df_all_items.empty and not df_ing.empty:
        # Λίστα υλικών που χρησιμοποιούνται όντως σε συνταγές
        used_ings = sorted(df_all_items["ingredient_name"].unique().tolist())
        
        col_r1, col_r2 = st.columns(2)
        old_ing = col_r1.selectbox("❌ Παλιό Υλικό:", options=used_ings, index=None, placeholder="Επιλέξτε υλικό...")
        new_ing = col_r2.selectbox("✅ Νέο Υλικό:", options=sorted(df_ing["Name"].unique().tolist()), index=None, placeholder="Από την αποθήκη...")

        if old_ing and new_ing and old_ing != new_ing:
            # Τιμές ανά ml από την αποθήκη
            price_old_ml = df_ing[df_ing["Name"] == old_ing]["Τιμή/ml"].values[0]
            price_new_ml = df_ing[df_ing["Name"] == new_ing]["Τιμή/ml"].values[0]
            diff_ml = price_new_ml - price_old_ml

            # Εύρεση συνταγών που επηρεάζονται
            affected_recipes_ids = df_all_items[df_all_items["ingredient_name"] == old_ing]["recipe_id"].unique().tolist()
            
            if affected_recipes_ids:
                # Φέρνουμε τις υπάρχουσες τιμές λιανικής από τον πίνακα recipes
                res_rec_info = supabase.table("recipes").select("id, name, catalog_price").in_("id", affected_recipes_ids).execute()
                rec_lookup = {r['id']: r for r in res_rec_info.data}

                analysis_data = []
                for rid in affected_recipes_ids:
                    r_items = df_all_items[df_all_items["recipe_id"] == rid]
                    r_name = rec_lookup[rid]['name']
                    # Η τιμή που έχεις ήδη καταχωρήσει εσύ
                    old_retail = rec_lookup[rid]['catalog_price'] or 0.0
                    old_agent = old_retail * 0.74 # -26% 
                    
                    # Υπολογισμός τρέχοντος κόστους για να βρούμε το περιθώριο κέρδους
                    current_cost = 0.22 # TOTAL_FIXED
                    ml_of_old = 0
                    for _, item in r_items.iterrows():
                        ing_n = item['ingredient_name']
                        ml = item['ml_per_unit']
                        if ing_n == old_ing: ml_of_old = ml
                        ing_info = df_ing[df_ing["Name"] == ing_n]
                        if not ing_info.empty:
                            current_cost += ml * ing_info["Τιμή/ml"].values[0]
                    
                    # Υπολογισμός Μεταβολής
                    cost_diff = ml_of_old * diff_ml
                    new_cost = current_cost + cost_diff
                    
                    # Υπολογισμός Νέας Λιανικής (διατηρώντας το ίδιο Markup: Retail/Cost)
                    # Αν δεν υπάρχει τιμή, χρησιμοποιούμε το default Food Cost 25%
                    if current_cost > 0 and old_retail > 0:
                        markup_factor = old_retail / current_cost
                        new_retail = new_cost * markup_factor
                    else:
                        new_retail = new_cost / 0.25
                        
                    new_agent = new_retail * 0.74

                    analysis_data.append({
                        "Cocktail": r_name,
                        "Μεταβολή (€)": round(cost_diff, 3),
                        "Παλιά Λιανική (€)": round(old_retail, 2),
                        "Νέα Λιανική (€)": round(new_retail, 2),
                        "Παλιά Αντιπρ. (€)": round(old_agent, 2),
                        "Νέα Αντιπρ. (€)": round(new_agent, 2)
                    })

                # Δημιουργία DataFrame
                df_res = pd.DataFrame(analysis_data)

                # Μορφοποίηση αριθμών (καθαρισμός μηδενικών)
                # Κρατάμε τη Μεταβολή ως float για το styling
                plot_df = df_res.copy()
                for col in ["Παλιά Λιανική (€)", "Νέα Λιανική (€)", "Παλιά Αντιπρ. (€)", "Νέα Αντιπρ. (€)"]:
                    plot_df[col] = plot_df[col].apply(format_num)

                # Χρωματισμός Μεταβολής
                def style_diff(val):
                    color = '#ff4b4b' if val > 0 else '#00ffcc'
                    return f'color: {color}; font-weight: bold'

                st.subheader(f"📊 Σύγκριση Τιμών: {old_ing} ➡️ {new_ing}")
                
                # Προβολή πίνακα με .map() για Pandas 2.1+
                st.dataframe(
                    plot_df.style.map(style_diff, subset=['Μεταβολή (€)']).format({"Μεταβολή (€)": lambda x: f"{x:g}"}),
                    use_container_width=True,
                    hide_index=True
                )

                st.divider()
                st.caption("💡 Η 'Νέα Λιανική' υπολογίζεται ώστε να διατηρηθεί το ίδιο ποσοστό κέρδους που είχατε με την παλιά πρώτη ύλη.")
                
                # --- ΕΚΤΕΛΕΣΗ ---
                confirm = st.checkbox(f"Επιβεβαιώνω την αντικατάσταση σε {len(df_res)} συνταγές.")
                if st.button("🚀 ΕΚΤΕΛΕΣΗ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΤΩΡΑ", type="primary", disabled=not confirm):
                    with st.spinner("Ενημέρωση συστατικών..."):
                        supabase.table("recipe_items").update({"ingredient_name": new_ing}).eq("ingredient_name", old_ing).execute()
                        st.success("✅ Η αντικατάσταση ολοκληρώθηκε!")
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()
            else:
                st.info("Το υλικό δεν βρέθηκε σε καμία συνταγή.")
    else:
        st.warning("⚠️ Δεν υπάρχουν δεδομένα στην αποθήκη ή στις συνταγές.")

# --- ΕΝΟΤΗΤΑ: ΔΙΑΧΕΙΡΙΣΗ ΠΑΡΑΓΓΕΛΙΩΝ B2B & E-SHOP ---
elif page == "📦 Παραγγελίες B2B":
    st.header("📦 Διαχείριση Παραγγελιών B2B")
    
    # --- ΛΕΙΤΟΥΡΓΙΑ WOOCOMMERCE SYNC ---
    from woocommerce import API
    try:
        wcapi = API(
            url=st.secrets["woo"]["url"],
            consumer_key=st.secrets["woo"]["ck"],
            consumer_secret=st.secrets["woo"]["cs"],
            version="wc/v3",
            timeout=20
        )
    except Exception as e:
        st.error(f"⚠️ Πρόβλημα WooCommerce: {e}")

    # Κουμπί Συγχρονισμού στην κορυφή
    col_sync1, col_sync2 = st.columns([1, 2])
    with col_sync1:
        if st.button("📥 Συγχρονισμός με E-shop", use_container_width=True, type="primary"):
            with st.spinner("Τραβάω παραγγελίες από το site..."):
                try:
                    # Τραβάμε παραγγελίες που είναι "processing" (Σε επεξεργασία στο Woo)
                    woo_orders = wcapi.get("orders", params={"status": "processing"}).json()
                    
                    new_entries = 0
                    for o in woo_orders:
                        # Έλεγχος αν η παραγγελία υπάρχει ήδη στη Supabase
                        check = supabase.table("b2b_orders").select("id").eq("woo_id", str(o['id'])).execute()
                        
                        if not check.data:
                            # Προετοιμασία κειμένου παραγγελίας
                            items = []
                            for item in o['line_items']:
                                items.append(f"{item['quantity']}x {item['name']}")
                            order_text = "\n".join(items)
                            
                            # Αποθήκευση στη Supabase
                            data = {
                                "customer_name": f"{o['billing']['first_name']} {o['billing']['last_name']}",
                                "total_amount": float(o['total']),
                                "status": "ΝΕΑ (E-shop)",
                                "order_details": order_text,
                                "notes": o.get('customer_note', ''),
                                "woo_id": str(o['id']),
                                "created_at": o['date_created']
                            }
                            supabase.table("b2b_orders").insert(data).execute()
                            
                            # ΝΕΟ: Αφαίρεση υλικών για τις παραγγελίες από E-shop
                            for item in o['line_items']:
                                deduct_inventory_for_production(item['name'], item['quantity'])

                            new_entries += 1
                    
                    if new_entries > 0:
                        st.success(f"✅ Εισήχθησαν {new_entries} νέες παραγγελίες!")
                    else:
                        st.info("Δεν βρέθηκαν νέες παραγγελίες στο E-shop.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Σφάλμα σύνδεσης: {e}")

    st.divider()
    
    tab1, tab2 = st.tabs(["🔔 Τρέχουσες Παραγγελίες", "📜 Ιστορικό & Αναζήτηση"])

    # --- TAB 1: ΤΡΕΧΟΥΣΕΣ ΠΑΡΑΓΓΕΛΙΕΣ ---
    with tab1:
        res_orders = supabase.table("b2b_orders").select("*").order("created_at", desc=True).execute()
        if res_orders.data:
            df_orders = pd.DataFrame(res_orders.data)
            
            # Φίλτρο για να περιλαμβάνει και το νέο status από το E-shop
            all_statuses = ["ΝΕΑ", "ΝΕΑ (E-shop)", "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ", "ΟΛΟΚΛΗΡΩΘΗΚΕ"]
            status_filter = st.multiselect("Φίλτρο Κατάστασης:", all_statuses, default=["ΝΕΑ", "ΝΕΑ (E-shop)", "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ"])
            
            df_filtered = df_orders[df_orders["status"].isin(status_filter)]

            for _, row in df_filtered.iterrows():
                # Εικονίδια ανάλογα με την κατάσταση
                icon = "🔵" if "ΝΕΑ" in row['status'] else "🟡" if row['status'] == "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ" else "✅"
                
                with st.expander(f"{icon} {row['customer_name']} - {row['total_amount']:.2f} €"):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.code(row['order_details'])
                        if row['notes']: st.info(f"📝 {row['notes']}")
                        st.caption(f"ID: {row['id']} | WooID: {row.get('woo_id','-')} | Ημερομηνία: {row['created_at']}")
                    
                    with c2:
                        # Επιλογή νέας κατάστασης
                        current_idx = all_statuses.index(row['status']) if row['status'] in all_statuses else 0
                        new_status = st.selectbox("Αλλαγή Κατάστασης:", all_statuses, index=current_idx, key=f"st_upd_{row['id']}")
                        
                        if st.button("Ενημέρωση", key=f"btn_upd_{row['id']}", use_container_width=True):
                            supabase.table("b2b_orders").update({"status": new_status}).eq("id", row['id']).execute()
                            st.success("Ενημερώθηκε!")
                            time.sleep(0.5)
                            st.rerun()
                        
                        st.divider()
                        if st.button("🗑️ Διαγραφή", key=f"del_b2b_{row['id']}", type="secondary", use_container_width=True):
                            supabase.table("b2b_orders").delete().eq("id", row['id']).execute()
                            st.rerun()
        else:
            st.info("Δεν υπάρχουν παραγγελίες στη βάση.")

    # --- TAB 2: ΙΣΤΟΡΙΚΟ & ΑΝΑΖΗΤΗΣΗ ---
    with tab2:
        st.subheader("🔍 Αναζήτηση στο Ιστορικό")
        if res_orders.data:
            df_hist = pd.DataFrame(res_orders.data)
            
            # --- ΔΥΝΑΜΙΚΑ ΦΙΛΤΡΑ (Ασφαλή για άδειες μέρες) ---
            if not df_hist.empty and "customer_name" in df_hist.columns:
                # 1. Βρίσκουμε τους πελάτες
                available_customers = sorted(df_hist["customer_name"].dropna().unique().tolist())
                
                # 2. Βρίσκουμε τα κοκτέιλ με τη δική σου λογική (split με 'x ')
                available_cocktails = set()
                for details in df_hist["order_details"].dropna():
                    lines = str(details).split('\n')
                    for line in lines:
                        if 'x ' in line:
                            parts = line.split('x ')
                            if len(parts) > 1:
                                name = parts[1].split(' (')[0].strip()
                                available_cocktails.add(name)
                available_cocktails = sorted(list(available_cocktails))
            else:
                available_customers = []
                available_cocktails = []

            search_col1, search_col2 = st.columns(2)
            with search_col1:
                cust_search = st.multiselect("Φίλτρο Πελάτη:", options=available_customers)
            with search_col2:
                cocktail_search = st.multiselect("Φίλτρο Κοκτέιλ:", options=available_cocktails)

            # Φιλτράρισμα
            if not df_hist.empty:
                mask = pd.Series([True] * len(df_hist))
                if cust_search: 
                    mask &= df_hist["customer_name"].isin(cust_search)
                if cocktail_search:
                    cocktail_mask = df_hist["order_details"].apply(lambda x: any(c in str(x) for c in cocktail_search))
                    mask &= cocktail_mask
                df_results = df_hist[mask]
            else:
                df_results = df_hist
            if not df_results.empty:
                st.write(f"Βρέθηκαν **{len(df_results)}** παραγγελίες.")
                for _, row in df_results.iterrows():
                    with st.expander(f"📅 {str(row['created_at'])[:10]} | {row['customer_name']} | {row['total_amount']:.2f} €"):
                        col_h1, col_h2 = st.columns([2, 1])
                        with col_h1:
                            st.markdown(f"**Κατάσταση:** {row['status']}")
                            
                            # Προβολή των κοκτέιλ (χωρίς δυνατότητα διαγραφής)
                            items = str(row['order_details']).split('\n')
                            
                            for i, item in enumerate(items):
                                if item.strip(): # Μόνο αν δεν είναι κενή γραμμή
                                    # Εμφανίζουμε απλώς το κείμενο, χωρίς στήλες και κουμπιά
                                    st.text(item)
                                    
                        with col_h2:
                            # Αφήνουμε τη στήλη κενή αφού βγάλαμε το κουμπί διαγραφής. 
                            # Το 'pass' λέει στην Python να μην κάνει τίποτα και γλιτώνεις IndentationError
                            pass 
            else:
                st.warning("Δεν βρέθηκαν παραγγελίες με αυτά τα κριτήρια.")

# --- 11. ΠΡΟΣΟΜΟΙΩΤΗΣ ΠΩΛΗΣΕΩΝ & QUOTATION GENERATOR (B2B PRO) ---
elif page == "🧪 Προσομοίωση Πωλήσεων":
    st.header("👔 B2B Στρατηγείο Προσφορών & Quotations")
    st.write("Δημιουργήστε, επεξεργαστείτε και εκτυπώστε επαγγελματικές εμπορικές προτάσεις (What-If Analysis).")

    import pandas as pd
    import plotly.express as px
    from datetime import datetime

    # --- 1. ΦΟΡΤΩΣΗ ΒΑΣΙΚΩΝ ΔΕΔΟΜΕΝΩΝ ---
    @st.cache_data(ttl=300)
    def load_simulation_data():
        rec = supabase.table("recipes").select("id, name, catalog_price").execute().data
        ing = supabase.table("ingredients").select("name, price, volume").execute().data
        items = supabase.table("recipe_items").select("recipe_id, ingredient_name, ml_per_unit").execute().data
        cust = supabase.table("customers").select("name, discount").execute().data
        return rec, ing, items, cust

    with st.spinner("Φόρτωση δεδομένων κόστους..."):
        rec_data, ing_data, items_data, cust_data = load_simulation_data()

    if rec_data:
        df_recipes = pd.DataFrame(rec_data)
        recipe_prices = dict(zip(df_recipes['name'], pd.to_numeric(df_recipes['catalog_price'], errors='coerce').fillna(0)))
        
        # Υπολογισμός Κόστους
        FIXED_COST = 0.22 
        df_ing = pd.DataFrame(ing_data)
        df_ing['cost_per_ml'] = pd.to_numeric(df_ing.get('price', 0), errors='coerce') / pd.to_numeric(df_ing.get('volume', 1), errors='coerce')
        ing_cost_dict = dict(zip(df_ing['name'], df_ing['cost_per_ml']))
        
        df_items = pd.DataFrame(items_data)
        recipe_costs_by_id = {}
        for rid in df_items['recipe_id'].unique():
            sub = df_items[df_items['recipe_id'] == rid]
            mat_cost = sum(pd.to_numeric(item.get('ml_per_unit', 0), errors='coerce') * ing_cost_dict.get(item.get('ingredient_name'), 0) for _, item in sub.iterrows())
            recipe_costs_by_id[rid] = mat_cost + FIXED_COST
            
        name_to_cost = {r['name']: recipe_costs_by_id.get(r['id'], FIXED_COST) for _, r in df_recipes.iterrows()}

        df_customers = pd.DataFrame(cust_data) if cust_data else pd.DataFrame(columns=['name', 'discount'])
        customer_list = ["-- Νέος Πελάτης (Χειροκίνητα) --"] + sorted(df_customers['name'].dropna().tolist())
        cust_discount_map = dict(zip(df_customers['name'], pd.to_numeric(df_customers.get('discount', 0), errors='coerce').fillna(0)))

        # --- 2. INITIALIZE SESSION STATE ---
        if 'sim_cart' not in st.session_state:
            st.session_state.sim_cart = []
        if 'sim_global_disc' not in st.session_state:
            st.session_state.sim_global_disc = 0.0
        if 'sim_customer' not in st.session_state:
            st.session_state.sim_customer = "-- Νέος Πελάτης (Χειροκίνητα) --"

        # --- 3. ΡΥΘΜΙΣΕΙΣ & ΠΡΟΣΘΗΚΗ ΠΡΟΪΟΝΤΩΝ ---
        st.divider()
        col_c1, col_c2 = st.columns([1, 1.5])
        
        with col_c1:
            st.markdown("### 👤 Στοιχεία Πρότασης")
            
            # Δυναμική αλλαγή πελάτη και έκπτωσης
            selected_cust = st.selectbox("Πελάτης:", customer_list, index=customer_list.index(st.session_state.sim_customer) if st.session_state.sim_customer in customer_list else 0)
            
            if selected_cust != st.session_state.sim_customer:
                st.session_state.sim_customer = selected_cust
                if selected_cust != "-- Νέος Πελάτης (Χειροκίνητα) --":
                    st.session_state.sim_global_disc = float(cust_discount_map.get(selected_cust, 0.0))
                st.rerun()

            new_global_disc = st.number_input("Γενική Έκπτωση (%) Στο Σενάριο:", min_value=0.0, max_value=100.0, value=float(st.session_state.sim_global_disc), step=1.0)
            if new_global_disc != st.session_state.sim_global_disc:
                st.session_state.sim_global_disc = new_global_disc
                st.rerun()

        with col_c2:
            st.markdown("### ➕ Προσθήκη Προϊόντος")
            with st.form("sim_add_item", clear_on_submit=True):
                sim_cocktail = st.selectbox("Επιλογή Κοκτέιλ:", options=sorted(df_recipes['name'].tolist()))
                
                c_qty, c_free, c_spcs, c_spct = st.columns(4)
                t_pcs = c_qty.number_input("Συνολικά Τμχ", min_value=1, value=24, step=1)
                f_pcs = c_free.number_input("Δωρεάν Τμχ", min_value=0, value=0, step=1)
                s_pcs = c_spcs.number_input("Τμχ σε Έκπτ.", min_value=0, value=0, step=1)
                s_pct = c_spct.number_input("% Ειδική Έκπτ.", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
                
                if st.form_submit_button("Προσθήκη στην Προσφορά", type="primary"):
                    if f_pcs + s_pcs > t_pcs:
                        st.error("⚠️ Τα δώρα και τα εκπτωτικά τεμάχια δεν μπορούν να ξεπερνούν το συνολικό αριθμό!")
                    else:
                        st.session_state.sim_cart.append({
                            "id": str(datetime.now().timestamp()), # Μοναδικό ID
                            "cocktail": sim_cocktail,
                            "t_pcs": t_pcs,
                            "f_pcs": f_pcs,
                            "s_pcs": s_pcs,
                            "s_pct": s_pct
                        })
                        st.rerun()

        # --- 4. ΤΟ ΔΥΝΑΜΙΚΟ ΚΑΛΑΘΙ (EDIT / DELETE) ---
        st.divider()
        st.markdown("### 🛒 Επεξεργασία Γραμμών Προσφοράς")
        
        if not st.session_state.sim_cart:
            st.info("📭 Η προσφορά είναι άδεια. Προσθέστε προϊόντα από πάνω.")
        else:
            for i, item in enumerate(st.session_state.sim_cart):
                with st.expander(f"🍸 {item['cocktail']} | {item['t_pcs']} τμχ (Κάντε κλικ για επεξεργασία)", expanded=False):
                    e_col1, e_col2, e_col3, e_col4, e_col5 = st.columns([2, 1, 1, 1, 1])
                    
                    with e_col1:
                        new_t_pcs = st.number_input("Σύνολο (τμχ)", min_value=1, value=item['t_pcs'], key=f"t_{item['id']}")
                    with e_col2:
                        new_f_pcs = st.number_input("Δώρα", min_value=0, value=item['f_pcs'], key=f"f_{item['id']}")
                    with e_col3:
                        new_s_pcs = st.number_input("Εκπτωτικά", min_value=0, value=item['s_pcs'], key=f"s_{item['id']}")
                    with e_col4:
                        new_s_pct = st.number_input("Extra %", min_value=0.0, max_value=100.0, value=float(item['s_pct']), key=f"pct_{item['id']}")
                    
                    with e_col5:
                        st.write("") # Κενό για ευθυγράμμιση
                        st.write("")
                        if st.button("💾 Αποθήκευση", key=f"save_{item['id']}", use_container_width=True):
                            if new_f_pcs + new_s_pcs > new_t_pcs:
                                st.error("Λάθος στις ποσότητες!")
                            else:
                                st.session_state.sim_cart[i]['t_pcs'] = new_t_pcs
                                st.session_state.sim_cart[i]['f_pcs'] = new_f_pcs
                                st.session_state.sim_cart[i]['s_pcs'] = new_s_pcs
                                st.session_state.sim_cart[i]['s_pct'] = new_s_pct
                                st.rerun()
                                
                        if st.button("🗑️ Διαγραφή", key=f"del_{item['id']}", type="secondary", use_container_width=True):
                            st.session_state.sim_cart.pop(i)
                            st.rerun()

            if st.button("🧹 Εκκαθάριση Όλης της Προσφοράς"):
                st.session_state.sim_cart = []
                st.rerun()

            # --- 5. ΥΠΟΛΟΓΙΣΜΟΙ & ΑΝΑΛΥΣΗ ---
            st.divider()
            st.markdown("### 📊 Ανάλυση Απόδοσης (Εσωτερική Χρήση)")
            
            total_sim_rev = 0.0
            total_sim_cost = 0.0
            total_list_value = 0.0 # Για να δούμε πόσο θα κόστιζαν χωρίς εκπτώσεις
            
            sim_export_data = [] # Δεδομένα για το PDF
            
            for item in st.session_state.sim_cart:
                c_name = item["cocktail"]
                t_pcs = item["t_pcs"]
                f_pcs = item["f_pcs"]
                s_pcs = item["s_pcs"]
                s_pct = item["s_pct"]
                normal_pcs = t_pcs - f_pcs - s_pcs
                
                cat_price = recipe_prices.get(c_name, 0.0)
                unit_cost = name_to_cost.get(c_name, FIXED_COST)
                
                # Διαδοχικά Μαθηματικά
                price_after_global = cat_price * (1 - (st.session_state.sim_global_disc / 100))
                rev_norm = normal_pcs * price_after_global
                rev_spec = s_pcs * price_after_global * (1 - (s_pct / 100))
                
                item_rev = rev_norm + rev_spec
                item_cost = t_pcs * unit_cost
                
                total_sim_rev += item_rev
                total_sim_cost += item_cost
                total_list_value += (t_pcs * cat_price) # Αξία καταλόγου χωρίς καμία έκπτωση
                
                sim_export_data.append({
                    "Cocktail": c_name,
                    "Τεμάχια": t_pcs,
                    "Δώρα/Εκπτώσεις": f"{f_pcs} Δώρα | {s_pcs} με -{s_pct}%",
                    "Αρχική Αξία": t_pcs * cat_price,
                    "Τελική Χρέωση": item_rev
                })

            total_sim_profit = total_sim_rev - total_sim_cost
            sim_margin = (total_sim_profit / total_sim_rev * 100) if total_sim_rev > 0 else 0
            customer_savings = total_list_value - total_sim_rev # Το "Δώρο" στον πελάτη
            
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Εκτιμώμενος Τζίρος", f"{total_sim_rev:,.2f} €", delta=f"-{customer_savings:,.2f}€ όφελος πελάτη", delta_color="normal")
            sm2.metric("Συνολικό Κόστος", f"{total_sim_cost:,.2f} €")
            
            if sim_margin >= 40:
                delta_color, status_icon = "normal", "🟢 Ασφαλής"
            elif sim_margin >= 25:
                delta_color, status_icon = "off", "🟡 Οριακή"
            else:
                delta_color, status_icon = "inverse", "🔴 Κίνδυνος"
                
            sm3.metric("Καθαρό Κέρδος (DC)", f"{total_sim_profit:,.2f} €")
            sm4.metric("Profit Margin (%)", f"{sim_margin:.1f}%", delta=f"{status_icon}", delta_color=delta_color)

            # --- 6. ΕΚΤΥΠΩΣΗ ΕΠΑΓΓΕΛΜΑΤΙΚΗΣ ΠΡΟΤΑΣΗΣ ---
            st.divider()
            st.markdown("### 🖨️ Εξαγωγή Εμπορικής Πρότασης")
            st.write("Δημιουργήστε ένα επαγγελματικό έγγραφο για να το παρουσιάσετε στον πελάτη. Στο έγγραφο φαίνεται στρατηγικά το **Συνολικό του Όφελος** για ψυχολογικούς λόγους πώλησης.")
            
            now_str = datetime.now().strftime("%d/%m/%Y")
            
            html_proposal = f"""
            <!DOCTYPE html>
            <html lang="el">
            <head>
                <meta charset="UTF-8">
                <title>Εμπορική Πρόταση - {st.session_state.sim_customer}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }}
                    .container {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #ddd; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; border-bottom: 3px solid #1a3a5f; padding-bottom: 15px; margin-bottom: 30px; }}
                    .header h1 {{ color: #1a3a5f; margin: 0; text-transform: uppercase; letter-spacing: 2px; }}
                    .info-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 30px; border-left: 5px solid #1a3a5f; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #1a3a5f; color: white; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .totals {{ width: 50%; float: right; margin-bottom: 50px; }}
                    .totals table th {{ background-color: transparent; color: #333; text-align: right; }}
                    .savings-row {{ color: #28a745; font-weight: bold; font-size: 1.1em; }}
                    .final-row {{ background-color: #1a3a5f !important; color: white; font-weight: bold; font-size: 1.2em; }}
                    .clear {{ clear: both; }}
                    .footer {{ text-align: center; color: #777; font-size: 0.9em; border-top: 1px solid #ddd; padding-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>ΕΜΠΟΡΙΚΗ ΠΡΟΤΑΣΗ ΣΥΝΕΡΓΑΣΙΑΣ</h1>
                        <p>DC CABCLUB PREMIUM COCKTAILS</p>
                    </div>
                    
                    <div class="info-box">
                        <p><strong>Προς:</strong> {st.session_state.sim_customer}</p>
                        <p><strong>Ημερομηνία:</strong> {now_str}</p>
                        <p><strong>Βασική Έκπτωση Συνεργασίας:</strong> {st.session_state.sim_global_disc}%</p>
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Προϊόν</th>
                                <th>Συνολικά Τεμάχια</th>
                                <th>Ειδικές Προσφορές</th>
                                <th style="text-align: right;">Τελική Αξία Γραμμής</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for row in sim_export_data:
                html_proposal += f"""
                            <tr>
                                <td><strong>{row['Cocktail']}</strong></td>
                                <td>{row['Τεμάχια']} τμχ</td>
                                <td style="color: #d32f2f; font-size: 0.9em;">{row['Δώρα/Εκπτώσεις']}</td>
                                <td style="text-align: right; font-weight: bold;">{row['Τελική Χρέωση']:.2f} €</td>
                            </tr>
                """
                
            html_proposal += f"""
                        </tbody>
                    </table>
                    
                    <div class="totals">
                        <table>
                            <tr>
                                <th>Αρχική Αξία Καταλόγου:</th>
                                <td style="text-align: right; text-decoration: line-through; color: #777;">{total_list_value:.2f} €</td>
                            </tr>
                            <tr class="savings-row">
                                <th>Συνολικό Όφελος / Έκπτωση:</th>
                                <td style="text-align: right;">- {customer_savings:.2f} €</td>
                            </tr>
                            <tr class="final-row">
                                <th style="color: white;">ΤΕΛΙΚΟ ΠΛΗΡΩΤΕΟ ΣΥΝΟΛΟ:</th>
                                <td style="text-align: right; color: white;">{total_sim_rev:.2f} €</td>
                            </tr>
                        </table>
                    </div>
                    <div class="clear"></div>
                    
                    <div class="footer">
                        <p>Σας ευχαριστούμε για την προτίμηση. Η προσφορά ισχύει για 30 ημέρες.</p>
                        <p>Οι τιμές δεν περιλαμβάνουν Φ.Π.Α.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            st.download_button(
                label="📥 Κατέβασμα Εμπορικής Πρότασης (Ανοίξτε το & τυπώστε σε PDF)",
                data=html_proposal,
                file_name=f"Quotation_{st.session_state.sim_customer}_{now_str.replace('/','-')}.html",
                mime="text/html",
                type="primary"
            )

# --- 13. ΔΙΑΧΕΙΡΙΣΗ ΑΠΟΘΗΚΗΣ & ΛΙΣΤΑ ΑΓΟΡΩΝ ---
elif page == "🛒 Λίστα Αγορών":
    st.header("🛒 Διαχείριση Αποθέματος & Λίστα Αγορών")
    st.write("Δημιουργήστε λίστες αγορών βάσει των πραγματικών σας παραγγελιών ή διορθώστε τα αποθέματά σας.")

    @st.cache_data(ttl=10)
    def load_live_data():
        # Διαβάζουμε φρέσκα δεδομένα αποθήκης και παραγγελιών
        ing = supabase.table("ingredients").select("*").execute().data
        plog = supabase.table("production_log").select("prod_date, prod_time, customer, cocktail_name, pieces").execute().data
        return ing, plog

    with st.spinner("Ανάγνωση δεδομένων..."):
        ing_data, plog_data = load_live_data()

    if ing_data:
        df_ing_live = pd.DataFrame(ing_data)
        col_map = {c: c.lower() for c in df_ing_live.columns}
        df_ing_live = df_ing_live.rename(columns=col_map)
        if 'current_stock_ml' not in df_ing_live.columns:
            df_ing_live['current_stock_ml'] = 0.0

        df_plog = pd.DataFrame(plog_data) if plog_data else pd.DataFrame()

        tab_inv1, tab_inv2, tab_inv3 = st.tabs(["📋 Λίστα Αγορών από Παραγγελίες", "📝 Απογραφή (Διόρθωση Αποθέματος)", "🧮 Ελεύθερος Υπολογισμός"])

        # 🚀 Η ΛΥΣΗ: Χρησιμοποιούμε τη συνολική df_rec του συστήματός σου που έχει ΉΔΗ "χτιστεί" με τα υλικά!
        global_recipes = df_rec.copy() if not df_rec.empty else pd.DataFrame()

        # ==========================================
        # TAB 1: ΑΥΤΟΜΑΤΗ ΛΙΣΤΑ ΑΠΟ ΠΑΡΑΓΓΕΛΙΕΣ
        # ==========================================
        with tab_inv1:
            st.markdown("### 🛒 Δημιουργία Λίστας βάσει Καταχωρημένων Παραγγελιών")
            
            if not df_plog.empty and not global_recipes.empty:
                available_dates = sorted(df_plog['prod_date'].dropna().unique().tolist(), reverse=True)
                sel_dates = st.multiselect("📅 Επιλέξτε Ημερομηνίες Παραγγελιών:", options=available_dates, default=[available_dates[0]] if available_dates else None)
                
                if sel_dates:
                    batch_orders = df_plog[df_plog['prod_date'].isin(sel_dates)].copy()
                    batch_orders['pieces'] = pd.to_numeric(batch_orders['pieces'], errors='coerce').fillna(0)
                    
                    if 'prod_time' in batch_orders.columns and 'customer' in batch_orders.columns:
                        batch_orders = batch_orders.drop_duplicates(subset=['prod_date', 'prod_time', 'customer', 'cocktail_name'])
                    
                    cocktail_sums = batch_orders.groupby('cocktail_name')['pieces'].sum().reset_index()
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.markdown("**Σύνοψη προς Παραγωγή:**")
                        st.dataframe(cocktail_sums.rename(columns={"cocktail_name": "Κοκτέιλ", "pieces": "Τεμάχια"}), hide_index=True)
                    
                    with c2:
                        st.markdown("**🛍️ Λίστα Αγορών Σούπερ Μάρκετ / Προμηθευτή**")
                        materials_needed = {}
                        import math
                        
                        for _, row in cocktail_sums.iterrows():
                            c_name = row['cocktail_name']
                            c_qty = row['pieces']
                            
                            # Βρίσκουμε τη συνταγή από τη global λίστα
                            rec_row = global_recipes[global_recipes['Ονομα'] == c_name]
                                
                            if not rec_row.empty:
                                r_data = rec_row.iloc[0]
                                for i in range(1, 14):
                                    ing_name = str(r_data.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                                    if ing_name in ["ΚΕΝΟ", "nan", "", "-", "0", "Νερό"]: continue
                                    
                                    # Τώρα βρίσκει με ασφάλεια τα ML!
                                    ml_u = float(r_data.get(f"ML{i}", 0) or 0)
                                    
                                    if ml_u > 0:
                                        materials_needed[ing_name] = materials_needed.get(ing_name, 0.0) + (ml_u * c_qty)
                        
                        shopping_list = []
                        for ing, required_ml in materials_needed.items():
                            ing_db = df_ing_live[df_ing_live['name'] == ing]
                            stock_ml = 0.0
                            bottle_vol = 1000.0
                            
                            if not ing_db.empty:
                                stock_ml = float(ing_db.iloc[0].get('current_stock_ml', 0.0))
                                vol = float(ing_db.iloc[0].get('volume', 1000.0))
                                if vol > 0: bottle_vol = vol
                            
                            missing_ml = required_ml - stock_ml
                            
                            if missing_ml > 0:
                                bottles_to_buy = math.ceil(missing_ml / bottle_vol)
                                status_text = f"🛒 ΠΑΡΑΓΓΕΛΙΑ: {bottles_to_buy} φιάλες"
                            else:
                                status_text = "✅ Επαρκές Απόθεμα"
                                
                            shopping_list.append({
                                "Υλικό": ing,
                                "Απαιτούμενα": f"{required_ml:.1f} ml",
                                "Απόθεμα": f"{stock_ml:.1f} ml",
                                "Λείπουν": f"{missing_ml:.1f} ml",
                                "Κατάσταση": status_text
                            })
                        
                        if shopping_list:
                            df_shop = pd.DataFrame(shopping_list)
                            st.dataframe(df_shop.style.apply(lambda x: ['background-color: #ffcccc; color: black' if 'ΠΑΡΑΓΓΕΛΙΑ' in str(v) else '' for v in x], axis=1), use_container_width=True, hide_index=True)
                        else:
                            st.success("Δεν απαιτούνται αγορές.")
            else:
                st.info("Δεν βρέθηκαν καταχωρημένες παραγγελίες ή συνταγές.")

        # ==========================================
        # TAB 2: ΕΝΗΜΕΡΩΣΗ ΑΠΟΘΕΜΑΤΟΣ (Χειροκίνητα)
        # ==========================================
        with tab_inv2:
            st.markdown("### Καταχώρηση Υπολοίπων (Απογραφή)")
            sel_ingredient = st.selectbox("Επιλέξτε Υλικό:", options=df_ing_live['name'].tolist())
            
            if sel_ingredient:
                ing_row = df_ing_live[df_ing_live['name'] == sel_ingredient].iloc[0]
                current_ml = float(ing_row.get('current_stock_ml', 0.0))
                bottle_vol = float(ing_row.get('volume', 1000))
                if pd.isna(bottle_vol) or bottle_vol <= 0: bottle_vol = 1000
                
                st.info(f"Τρέχον Απόθεμα Βάσης: **{current_ml:.1f} ml** (Περίπου {current_ml / bottle_vol:.1f} φιάλες)")
                
                new_stock = st.number_input("Νέο Πραγματικό Υπόλοιπο (σε ml):", min_value=-50000.0, value=current_ml, step=50.0)
                
                if st.button("💾 Αποθήκευση Υπολοίπου", type="primary"):
                    supabase.table("ingredients").update({"current_stock_ml": new_stock}).eq("id", ing_row['id']).execute()
                    st.success(f"Το απόθεμα για το {sel_ingredient} ενημερώθηκε στα {new_stock} ml!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()

        # ==========================================
        # TAB 3: ΥΠΟΛΟΓΙΣΤΗΣ WHAT-IF
        # ==========================================
        with tab_inv3:
            st.markdown("### 🧮 Ελεύθερος Υπολογισμός (Τι θα γίνει αν...)")
            
            if not global_recipes.empty:
                recipe_names = global_recipes['Ονομα'].tolist()
                
                with st.form("calc_order_form_2"):
                    col_p1, col_p2 = st.columns([2, 1])
                    target_cocktail = col_p1.selectbox("Κοκτέιλ προς παραγωγή:", options=recipe_names)
                    target_pcs = col_p2.number_input("Τεμάχια:", min_value=1, value=50, step=1)
                    calc_btn = st.form_submit_button("🧮 Υπολογισμός Απαιτήσεων")
                
                if calc_btn:
                    rec_row = global_recipes[global_recipes['Ονομα'] == target_cocktail]
                    
                    shopping_list = []
                    import math
                    for i in range(1, 14):
                        ing_name = str(rec_row.iloc[0].get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                        if ing_name in ["ΚΕΝΟ", "nan", "", "-", "0", "Νερό"]: continue
                        
                        ml_u = float(rec_row.iloc[0].get(f"ML{i}", 0) or 0)
                            
                        if ml_u > 0:
                            ing_db = df_ing_live[df_ing_live['name'] == ing_name]
                            if not ing_db.empty:
                                stock_ml = float(ing_db.iloc[0].get('current_stock_ml', 0.0))
                                bottle_vol = float(ing_db.iloc[0].get('volume', 1000.0))
                                if bottle_vol <= 0: bottle_vol = 1000
                                
                                missing_ml = (ml_u * target_pcs) - stock_ml
                                
                                if missing_ml > 0:
                                    bottles_to_buy = math.ceil(missing_ml / bottle_vol)
                                    shopping_list.append({"Υλικό": ing_name, "Απαιτείται": f"{(ml_u * target_pcs):.1f} ml", "Λείπουν": f"{missing_ml:.1f} ml", "Αγορά": f"🛒 {bottles_to_buy} φιάλες"})
                                else:
                                    shopping_list.append({"Υλικό": ing_name, "Απαιτείται": f"{(ml_u * target_pcs):.1f} ml", "Λείπουν": "0.0 ml", "Αγορά": "✅ Επαρκές"})
                    
                    if shopping_list:
                        st.dataframe(pd.DataFrame(shopping_list), use_container_width=True, hide_index=True)
            else:
                st.warning("Δεν βρέθηκαν συνταγές.")
    else:
        st.error("Δεν βρέθηκαν δεδομένα υλικών στη βάση.")
