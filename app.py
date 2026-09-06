import streamlit as st
import pandas as pd
import re
import os
import math
from datetime import datetime, timedelta
import pytz  # 🌟 ΝΕΟ: Εισαγωγή βιβλιοθήκης για ζώνες ώρας
import plotly.express as px
import imaplib
import email
import time
import zipfile
import io
from fpdf import FPDF

# 🚀 ΕΔΩ ΕΙΝΑΙ ΤΟ ΚΛΕΙΔΙ: Φορτώνουμε τη Supabase ΠΡΙΝ τη χρησιμοποιήσουμε
from supabase import create_client, Client

# --- ΣΥΝΔΕΣΗ ΜΕ SUPABASE ---
# Η σύνδεση γίνεται αμέσως, στην κορυφή του αρχείου!
url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

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
# --- 🔧 FIX: ανθεκτική εύρεση υπάρχουσας παραγγελίας B2B (πελάτης+ημέρα) ---
def find_existing_b2b_order(cust, date_iso):
    """Βρίσκει την ΥΠΑΡΧΟΥΣΑ εγγραφή b2b_orders για συγκεκριμένο πελάτη+ημέρα.
    Πριν, ο έλεγχος γινόταν με gte/lte πάνω σε ωρολογιακό εύρος (created_at),
    κάτι που μπορούσε να αποτύχει λόγω ζώνης ώρας/μορφής και να δημιουργεί
    ΔΙΠΛΟΤΥΠΕΣ εγγραφές αντί να ενημερώνει τη σωστή. Τώρα φέρνει όλες τις
    εγγραφές του πελάτη και συγκρίνει την ΗΜΕΡΟΜΗΝΙΑ (όχι ώρα) στη μνήμη —
    ανθεκτικό σε τέτοιες αποκλίσεις. Αν βρεθούν ήδη πολλαπλές (παλιά
    διπλότυπα), επιστρέφει τη ΠΙΟ ΠΡΟΣΦΑΤΗ (μεγαλύτερο id)."""
    try:
        res = supabase.table("b2b_orders").select("id, created_at").eq("customer_name", cust).execute()
    except Exception:
        return None
    if not res.data:
        return None
    matches = []
    for row in res.data:
        try:
            row_date = pd.to_datetime(row["created_at"]).strftime("%Y-%m-%d")
        except Exception:
            continue
        if row_date == date_iso:
            matches.append(row)
    if not matches:
        return None
    return max(matches, key=lambda r: r["id"])

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

# --- 🚀 PERFORMANCE FIX: BATCH ΑΦΑΙΡΕΣΗ ΑΠΟΘΕΜΑΤΟΣ (αντί για select+update ανά υλικό/κοκτέιλ) ---
def compute_inventory_deductions(cocktail_name, total_pieces_made, df_recipes, deductions):
    """Υπολογίζει ΣΤΗ ΜΝΗΜΗ (χωρίς κλήση στη βάση) τα ml που πρέπει να αφαιρεθούν για ένα
    κοκτέιλ, και τα προσθέτει στο συγκεντρωτικό dict `deductions`
    {όνομα_υλικού: σύνολο_ml_προς_αφαίρεση}. Χρησιμοποιεί το ήδη φορτωμένο df_rec (cached)
    αντί να ξαναρωτά τη βάση για κάθε κοκτέιλ ξεχωριστά."""
    match = df_recipes[df_recipes["Ονομα"] == cocktail_name]
    if match.empty:
        return
    recipe_row = match.iloc[0]
    for i in range(1, 14):
        ing_name = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
        if ing_name in ["ΚΕΝΟ", "nan", "None", "", "Νερό"]:
            continue
        try:
            ml_per_unit = float(recipe_row.get(f"ML{i}", 0.0))
        except (TypeError, ValueError):
            continue
        if ml_per_unit <= 0:
            continue
        ml_used = ml_per_unit * total_pieces_made
        deductions[ing_name] = deductions.get(ing_name, 0.0) + ml_used

def commit_inventory_deductions(deductions):
    """Εφαρμόζει ΟΛΕΣ τις αφαιρέσεις αποθέματος σε ΕΝΑ batch call στη Supabase (αντί για
    2 κλήσεις -select + update- ανά υλικό). Επιστρέφει (ok, failed_names)."""
    if not deductions:
        return True, []
    try:
        res_ing_fresh = supabase.table("ingredients").select("id, name, current_stock_ml").execute()
    except Exception as e:
        return False, [f"Σφάλμα φόρτωσης αποθέματος: {e}"]
    fresh_by_name = {str(r["name"]).strip(): r for r in (res_ing_fresh.data or [])}

    updates = []
    failed = []
    for ing_name, ml_used in deductions.items():
        row = fresh_by_name.get(str(ing_name).strip())
        if row is None:
            failed.append(ing_name)
            continue
        old_stock = float(row.get("current_stock_ml") or 0.0)
        updates.append({"id": row["id"], "current_stock_ml": old_stock - ml_used})

    if updates:
        try:
            supabase.table("ingredients").upsert(updates, on_conflict="id").execute()
        except Exception as e:
            return False, failed + [f"Σφάλμα batch ενημέρωσης: {e}"]

    return (len(failed) == 0), failed
# --------------------------------------------------
# --- 🔧 FIX: Εύρεση γραμματοσειράς Unicode (ελληνικά) για τα PDF, σε πολλαπλές πιθανές τοποθεσίες ---
def _find_unicode_font_path():
    """Ψάχνει DejaVuSans.ttf σε κοινές τοποθεσίες, ώστε τα PDF με ελληνικό κείμενο
    να μη σκάνε με 'Character outside range... helvetica'. Επιστρέφει None αν δεν βρεθεί πουθενά
    (τότε γίνεται graceful fallback σε Helvetica, όπως πριν)."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "DejaVuSans.ttf"),
        os.path.join(os.getcwd(), "DejaVuSans.ttf"),
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            if os.path.isfile(path):
                return path
        except Exception:
            continue
    try:
        import matplotlib
        mpl_font = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", "DejaVuSans.ttf")
        if os.path.isfile(mpl_font):
            return mpl_font
    except Exception:
        pass
    return None

_UNICODE_FONT_PATH = _find_unicode_font_path()

# --- ΥΒΡΙΔΙΚΗ ΣΥΝΑΡΤΗΣΗ PDF: ΣΥΓΚΕΝΤΡΩΤΙΚΑ ΠΡΟΪΟΝΤΑ & ΣΥΝΟΛΑ ---
def generate_hybrid_report(customer_name, financial_data, production_data):
    pdf = FPDF()
    pdf.add_page()
    if _UNICODE_FONT_PATH:
        try:
            pdf.add_font('DejaVu', '', _UNICODE_FONT_PATH)
            f_name = 'DejaVu'
        except Exception:
            f_name = 'Helvetica'
    else:
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

# --- 📐 PDF REPORT ΓΙΑ MARKUP & MARGIN (ΚΑΛΑΙΣΘΗΤΟ ΣΧΕΔΙΟ) ---
def generate_markup_margin_pdf(cocktail_name, data):
    """Δημιουργεί ένα καλαίσθητο PDF με όλους τους δείκτες markup/margin της καρτέλας.
    `data` είναι dict με όλα τα νούμερα (κόστος, τιμές, markup/margin, σενάριο)."""
    pdf = FPDF()
    pdf.add_page()
    if _UNICODE_FONT_PATH:
        try:
            pdf.add_font('DejaVu', '', _UNICODE_FONT_PATH)
            pdf.add_font('DejaVu', 'B', _UNICODE_FONT_PATH)
            f_name = 'DejaVu'
        except Exception:
            f_name = 'Helvetica'
    else:
        f_name = 'Helvetica'

    GREEN = (30, 122, 52)
    DARK = (30, 30, 30)
    GREY = (110, 110, 110)
    LIGHTGREY = (245, 245, 245)
    BLUE = (27, 94, 158)

    # --- ΚΕΦΑΛΙΔΑ ---
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 0, 210, 28, 'F')
    pdf.set_xy(10, 7)
    pdf.set_font(f_name, 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "CABCLUB COCKTAILS", ln=1)
    pdf.set_x(10)
    pdf.set_font(f_name, size=11)
    pdf.cell(0, 6, "Αναφορά Markup & Margin", ln=1)

    pdf.set_text_color(*DARK)
    pdf.ln(14)
    pdf.set_font(f_name, 'B', 15)
    pdf.cell(0, 8, f"Κοκτέιλ: {cocktail_name}", ln=1)
    pdf.set_font(f_name, size=9)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, f"Ημερομηνία αναφοράς: {data['now_str']}", ln=1)
    pdf.set_text_color(*DARK)
    pdf.ln(4)

    def section_title(text):
        pdf.set_font(f_name, 'B', 12)
        pdf.set_text_color(*BLUE)
        pdf.cell(0, 9, text, ln=1)
        pdf.set_text_color(*DARK)

    def indicator_table(rows):
        # rows: list of (label, value) tuples
        pdf.set_font(f_name, size=10)
        col_w = 95
        for i, (label, value) in enumerate(rows):
            fill = (i % 2 == 0)
            pdf.set_fill_color(*LIGHTGREY) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(col_w, 8, label, border=1, fill=True)
            pdf.set_font(f_name, 'B', 10)
            pdf.cell(col_w, 8, value, border=1, ln=1, fill=True, align='R')
            pdf.set_font(f_name, size=10)

    # --- ΕΝΟΤΗΤΑ 1 ---
    section_title("1) Cabclub -> Αντιπρόσωπος (Χονδρική)")
    indicator_table([
        ("Κόστος μου (ανά τεμάχιο)", f"{data['my_cost']:.2f} EUR"),
        ("Τιμή Αντιπροσώπου", f"{data['agent_price']:.2f} EUR"),
        ("Markup", f"{data['markup1']:.1f} %"),
        ("Margin", f"{data['margin1']:.1f} %"),
    ])
    pdf.ln(4)

    # --- ΕΝΟΤΗΤΑ 2 ---
    section_title("2) Αντιπρόσωπος -> Τελικός Πελάτης (Λιανική)")
    indicator_table([
        ("Κόστος Αντιπροσώπου (= τιμή αγοράς)", f"{data['agent_price']:.2f} EUR"),
        ("Τιμή Λιανικής", f"{data['retail_price']:.2f} EUR"),
        ("Markup", f"{data['markup2']:.1f} %"),
        ("Margin", f"{data['margin2']:.1f} %"),
    ])
    pdf.ln(4)

    # --- ΕΝΟΤΗΤΑ 3 ---
    section_title("3) Cabclub -> Τελικός Πελάτης (Απευθείας Λιανική)")
    indicator_table([
        ("Κόστος μου (ανά τεμάχιο)", f"{data['my_cost']:.2f} EUR"),
        ("Τιμή Λιανικής", f"{data['retail_price']:.2f} EUR"),
        ("Markup", f"{data['markup3']:.1f} %"),
        ("Margin", f"{data['margin3']:.1f} %"),
    ])
    pdf.ln(6)

    # --- ΣΕΝΑΡΙΟ (αν υπάρχει) ---
    if data.get('scenario_ran'):
        section_title(f"Σενάριο: Επιθυμητό {data['scenario_mode']}")
        pdf.set_font(f_name, size=9)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(0, 5, f"Επίπεδο 1: {data['desired1']:.2f}   |   Επίπεδο 2: {data['desired2']:.2f}   |   Επίπεδο 3: {data['desired3']:.2f}")
        pdf.set_text_color(*DARK)
        pdf.ln(1)

        if data.get('new_agent_price') is not None:
            indicator_table([
                ("Νέα Τιμή Αντιπροσώπου", f"{data['new_agent_price']:.2f} EUR"),
                ("Μεταβολή vs Σήμερα", f"{data['delta_agent']:+.2f} EUR ({data['delta_agent_pct']:+.1f}%)"),
                ("Νέο Markup / Margin", f"{data['new_markup1']:.1f}% / {data['new_margin1']:.1f}%"),
            ])
            pdf.ln(3)
        if data.get('new_retail_price') is not None:
            indicator_table([
                ("Νέα Τιμή Λιανικής", f"{data['new_retail_price']:.2f} EUR"),
                ("Μεταβολή vs Σήμερα", f"{data['delta_retail']:+.2f} EUR ({data['delta_retail_pct']:+.1f}%)"),
                ("Νέο Markup / Margin", f"{data['new_markup2']:.1f}% / {data['new_margin2']:.1f}%"),
            ])
            pdf.ln(3)
        if data.get('new_direct_price') is not None:
            indicator_table([
                ("Νέα Τιμή Απευθείας Πώλησης", f"{data['new_direct_price']:.2f} EUR"),
                ("Μεταβολή vs Σήμερα", f"{data['delta_direct']:+.2f} EUR ({data['delta_direct_pct']:+.1f}%)"),
                ("Νέο Markup / Margin", f"{data['new_markup3']:.1f}% / {data['new_margin3']:.1f}%"),
            ])
            pdf.ln(4)

        if data.get('total_change_text'):
            pdf.set_fill_color(230, 244, 234)
            pdf.set_draw_color(*GREEN)
            pdf.set_font(f_name, 'B', 10)
            pdf.set_text_color(*GREEN)
            pdf.multi_cell(0, 8, data['total_change_text'], border=1, fill=True, align='C')
            pdf.set_text_color(*DARK)

    # --- ΥΠΟΣΕΛΙΔΟ ---
    pdf.set_y(-18)
    pdf.set_font(f_name, size=8)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, "CabClub Cocktails - Αυτόματη Αναφορά Markup & Margin", align='C')

    return pdf.output()

# --- 📚 PDF: ΑΝΑΛΥΤΙΚΗ ΑΝΑΦΟΡΑ ΟΛΩΝ ΤΩΝ ΣΥΝΤΑΓΩΝ (ΥΛΙΚΑ + ΚΟΣΤΟΣ + MARKUP/MARGIN) ---
def generate_full_recipe_report_pdf(df_recipes, df_ingredients, cost_fn):
    """Δημιουργεί ένα πολυσέλιδο PDF με ΟΛΕΣ τις συνταγές: πρώτες ύλες (ml & gr ανά
    τεμάχιο), πλήρες κόστος, τιμές, και markup/margin και στα δύο επίπεδα διανομής.
    `cost_fn` είναι η get_unit_cost_for_cocktail (περνιέται ως παράμετρος για καθαρότητα)."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    if _UNICODE_FONT_PATH:
        try:
            pdf.add_font('DejaVu', '', _UNICODE_FONT_PATH)
            pdf.add_font('DejaVu', 'B', _UNICODE_FONT_PATH)
            f_name = 'DejaVu'
        except Exception:
            f_name = 'Helvetica'
    else:
        f_name = 'Helvetica'

    GREEN = (30, 122, 52)
    DARK = (30, 30, 30)
    GREY = (110, 110, 110)
    LIGHTGREY = (245, 245, 245)
    WHITE = (255, 255, 255)

    def _markup(cost, price):
        return round((price - cost) / cost * 100, 2) if cost > 0 else 0.0

    def _margin(cost, price):
        return round((price - cost) / price * 100, 2) if price > 0 else 0.0

    try:
        now_str = datetime.now(greece_tz).strftime("%d/%m/%Y %H:%M")
    except Exception:
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    # --- ΕΞΩΦΥΛΛΟ ---
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_xy(10, 12)
    pdf.set_font(f_name, 'B', 22)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 10, "CABCLUB COCKTAILS", ln=1)
    pdf.set_x(10)
    pdf.set_font(f_name, size=13)
    pdf.cell(0, 8, "Αναλυτική Αναφορά Όλων των Συνταγών", ln=1)
    pdf.set_text_color(*DARK)
    pdf.ln(16)
    pdf.set_font(f_name, size=10)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, f"Ημερομηνία αναφοράς: {now_str}   |   Σύνολο συνταγών: {len(df_recipes)}", ln=1)
    pdf.set_text_color(*DARK)
    pdf.ln(4)

    recipe_names = sorted(df_recipes["Ονομα"].unique())

    for cocktail_name in recipe_names:
        r = df_recipes[df_recipes["Ονομα"] == cocktail_name].iloc[0]
        retail_price = float(r.get("Τιμή Καταλόγου", 0.0) or 0.0)
        agent_price = retail_price * 0.74

        # --- Συλλογή υλικών + υπολογισμός κόστους υλικών ---
        ingredient_rows = []
        raw_cost = 0.0
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
            ml = float(r.get(f"ML{i}", 0) or 0)
            if ing_n in ["ΚΕΝΟ", "nan", ""] or ml <= 0:
                continue
            match = df_ingredients[df_ingredients["Name"] == ing_n]
            gr = 0.0
            if not match.empty:
                vol = float(match.iloc[0].get("Volume", 0) or 0)
                wt = float(match.iloc[0].get("Weight_Full", 0) or 0)
                if vol > 0:
                    gr = (ml / vol) * wt
                if ing_n != "Νερό":
                    raw_cost += ml * float(match.iloc[0].get("Τιμή/ml", 0) or 0)
            ingredient_rows.append((ing_n, ml, gr))

        my_cost = cost_fn(cocktail_name, raw_cost)
        markup1, margin1 = _markup(my_cost, agent_price), _margin(my_cost, agent_price)
        markup2, margin2 = _markup(agent_price, retail_price), _margin(agent_price, retail_price)

        # --- Επικεφαλίδα κοκτέιλ ---
        pdf.set_fill_color(*GREEN)
        pdf.set_text_color(*WHITE)
        pdf.set_font(f_name, 'B', 12)
        pdf.cell(0, 8, cocktail_name, ln=1, fill=True)
        pdf.set_text_color(*DARK)

        # --- Πίνακας υλικών ---
        pdf.set_font(f_name, 'B', 9)
        pdf.set_fill_color(*LIGHTGREY)
        pdf.cell(100, 6, "Πρώτη Ύλη", border=1, fill=True)
        pdf.cell(45, 6, "ml / τεμάχιο", border=1, fill=True, align='R')
        pdf.cell(45, 6, "gr / τεμάχιο", border=1, ln=1, fill=True, align='R')
        pdf.set_font(f_name, size=9)
        if ingredient_rows:
            for idx, (ing_n, ml, gr) in enumerate(ingredient_rows):
                fill = (idx % 2 == 0)
                pdf.set_fill_color(250, 250, 250) if fill else pdf.set_fill_color(*WHITE)
                pdf.cell(100, 6, ing_n, border=1, fill=True)
                pdf.cell(45, 6, f"{ml:.1f}", border=1, fill=True, align='R')
                pdf.cell(45, 6, f"{gr:.1f}" if gr > 0 else "-", border=1, ln=1, fill=True, align='R')
        else:
            pdf.cell(190, 6, "Δεν βρέθηκαν πρώτες ύλες.", border=1, ln=1)

        # --- Κόστος & Τιμές ---
        pdf.ln(1)
        pdf.set_font(f_name, size=9)
        pdf.cell(0, 5.5, f"Κόστος Πρώτων Υλών: {raw_cost:.2f} EUR   |   Πλήρες Κόστος (δικό μου): {my_cost:.2f} EUR", ln=1)
        pdf.cell(0, 5.5, f"Τιμή Αντιπροσώπου: {agent_price:.2f} EUR   |   Τιμή Λιανικής: {retail_price:.2f} EUR", ln=1)

        # --- Markup / Margin ---
        pdf.set_font(f_name, 'B', 9)
        pdf.set_text_color(*GREEN)
        pdf.cell(0, 5.5, f"Cabclub -> Αντιπρόσωπος:  Markup {markup1:.1f}%  /  Margin {margin1:.1f}%", ln=1)
        pdf.cell(0, 5.5, f"Αντιπρόσωπος -> Πελάτης:  Markup {markup2:.1f}%  /  Margin {margin2:.1f}%", ln=1)
        pdf.set_text_color(*DARK)
        pdf.set_font(f_name, size=9)
        pdf.ln(5)

    # --- ΥΠΟΣΕΛΙΔΟ (μόνο τελευταία σελίδα) ---
    pdf.set_y(-15)
    pdf.set_font(f_name, size=8)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, "CabClub Cocktails - Αναλυτική Αναφορά Συνταγών", align='C')

    return pdf.output()

# --- 📑 PDF: ΑΝΑΦΟΡΑ ΕΣΟΔΩΝ - ΕΞΟΔΩΝ (P&L) ---
def generate_pl_report_pdf(period_label, data):
    """Δημιουργεί ένα καλαίσθητο PDF με πλήρη αναφορά Εσόδων-Εξόδων για μια περίοδο
    (μήνα ή έτος). `data` περιέχει όλα τα νούμερα (τζίρος, COGS, σταθερά έξοδα ανά
    κατηγορία, καθαρό κέρδος)."""
    pdf = FPDF()
    pdf.add_page()
    if _UNICODE_FONT_PATH:
        try:
            pdf.add_font('DejaVu', '', _UNICODE_FONT_PATH)
            pdf.add_font('DejaVu', 'B', _UNICODE_FONT_PATH)
            f_name = 'DejaVu'
        except Exception:
            f_name = 'Helvetica'
    else:
        f_name = 'Helvetica'

    GREEN = (30, 122, 52)
    RED = (176, 0, 32)
    DARK = (30, 30, 30)
    GREY = (110, 110, 110)
    LIGHTGREY = (245, 245, 245)
    WHITE = (255, 255, 255)

    # --- ΚΕΦΑΛΙΔΑ ---
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_xy(10, 7)
    pdf.set_font(f_name, 'B', 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 8, "CABCLUB COCKTAILS", ln=1)
    pdf.set_x(10)
    pdf.set_font(f_name, size=12)
    pdf.cell(0, 7, f"Αναφορά Εσόδων - Εξόδων  |  Περίοδος: {period_label}", ln=1)
    pdf.set_text_color(*DARK)
    pdf.ln(16)

    def row(label, value, bold=False, color=None, indent=0):
        pdf.set_font(f_name, 'B' if bold else '', 10)
        pdf.set_text_color(*(color or DARK))
        pdf.cell(10 * indent, 7)
        pdf.cell(130 - 10 * indent, 7, label)
        pdf.cell(50, 7, value, align='R', ln=1)
        pdf.set_text_color(*DARK)

    def divider():
        pdf.ln(1)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    # --- ΕΣΟΔΑ ---
    pdf.set_fill_color(*LIGHTGREY)
    pdf.set_font(f_name, 'B', 12)
    pdf.cell(0, 8, "ΕΣΟΔΑ", ln=1, fill=True)
    pdf.ln(1)
    row("Τζίρος (Θεωρητικά Έσοδα)", f"{data['total_revenue']:,.2f} EUR", bold=True, color=GREEN)
    row("Τεμάχια Πωληθέντα (πληρωμένα)", f"{data['total_paid_pieces']:,} τμχ", indent=1)
    row("Δωρεάν Τεμάχια (Κιβωτιακή Πολιτική)", f"{data['total_gift_pieces']:,} τμχ", indent=1)
    divider()

    # --- ΜΕΤΑΒΛΗΤΟ ΚΟΣΤΟΣ ---
    pdf.set_font(f_name, 'B', 12)
    pdf.cell(0, 8, "ΜΕΤΑΒΛΗΤΟ ΚΟΣΤΟΣ (COGS)", ln=1, fill=True)
    pdf.ln(1)
    row("Κόστος Πωληθέντων", f"-{data['total_cogs']:,.2f} EUR", color=RED)
    row("Μικτό Κέρδος", f"{data['gross_profit']:,.2f} EUR", bold=True, color=GREEN if data['gross_profit'] >= 0 else RED)
    row("Περιθώριο Μικτού Κέρδους", f"{data['gross_margin_pct']:.1f} %", indent=1)
    divider()

    # --- ΣΤΑΘΕΡΑ ΕΞΟΔΑ ---
    pdf.set_font(f_name, 'B', 12)
    pdf.cell(0, 8, "ΣΤΑΘΕΡΑ ΕΞΟΔΑ ΕΠΙΧΕΙΡΗΣΗΣ", ln=1, fill=True)
    pdf.ln(1)
    row("Ενοίκιο", f"-{data['be_rent']:,.2f} EUR", indent=1)
    row("Μισθοδοσία", f"-{data['be_labor']:,.2f} EUR", indent=1)
    row("Ασφάλιστρα", f"-{data['be_insurance']:,.2f} EUR", indent=1)
    row("Λογιστικά / Διοικητικά", f"-{data['be_admin']:,.2f} EUR", indent=1)
    row("ΔΕΗ / Ρεύμα / Νερό", f"-{data['be_utilities']:,.2f} EUR", indent=1)
    row("Λοιπά Σταθερά", f"-{data['be_other']:,.2f} EUR", indent=1)
    row("Σύνολο Σταθερών Εξόδων", f"-{data['period_fixed']:,.2f} EUR", bold=True, color=RED)
    divider()

    # --- ΚΑΘΑΡΟ ΑΠΟΤΕΛΕΣΜΑ (προ φόρων) + ΦΟΡΟΛΟΓΙΑ ---
    row("Καθαρό Αποτέλεσμα (προ φόρων)", f"{data['net_profit']:,.2f} EUR", bold=True, color=GREEN if data['net_profit'] >= 0 else RED)
    row(f"Φόρος Εισοδήματος ({data.get('tax_rate', 22):.0f}%)", f"-{data.get('tax_amount', 0):,.2f} EUR", color=RED)
    divider()

    net_after_tax = data.get('net_after_tax', data['net_profit'])
    net_color = GREEN if net_after_tax >= 0 else RED
    pdf.set_fill_color(*(230, 244, 234) if net_after_tax >= 0 else (250, 230, 230))
    pdf.set_draw_color(*net_color)
    pdf.set_font(f_name, 'B', 13)
    pdf.set_text_color(*net_color)
    pdf.cell(130, 10, "ΚΑΘΑΡΟ ΑΠΟΤΕΛΕΣΜΑ (μετά φόρων)", border=1, fill=True)
    pdf.cell(50, 10, f"{net_after_tax:,.2f} EUR", border=1, fill=True, align='R', ln=1)
    pdf.set_text_color(*DARK)
    pdf.ln(2)
    pdf.set_font(f_name, size=9)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, f"Περιθώριο Καθαρού Κέρδους (προ φόρων): {data['net_margin_pct']:.1f} %", ln=1)
    pdf.set_text_color(*DARK)

    # --- ΥΠΟΣΕΛΙΔΟ ---
    pdf.set_y(-18)
    pdf.set_font(f_name, size=8)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, f"CabClub Cocktails - Αναφορά Εσόδων-Εξόδων - Δημιουργήθηκε: {data['now_str']}", align='C')

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
    
# 🚀 ΠΡΟΣΘΗΚΗ ΕΔΩ: Εμφανίζεται μόνο αν ο κωδικός είναι σωστός!
st.markdown(
    """
    <h2 style='color: #009b3a; text-align: center; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); margin-top: 10px;'>
        "Κοκτέιλ τόσο καλά, που ανασταίνουν και... Zombie!"
    </h2>
    <br>
    """, 
    unsafe_allow_html=True
)


st.divider()

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
_TOTAL_FIXED_FALLBACK = 0.22  # παλιό, αρχικό fallback — χρησιμοποιείται όταν το χειροκίνητο σενάριο κόστους είναι ΑΝΕΝΕΡΓΟ
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

@st.cache_data(ttl=90)
def load_cost_settings():
    """Φορτώνει το ΕΝΕΡΓΟ/ΑΝΕΝΕΡΓΟ σενάριο + το λειτουργικό κόστος (ίδιο για όλα τα κοκτέιλ).
    Επιστρέφει None αν δεν έχει ρυθμιστεί ακόμα (ή ο πίνακας δεν υπάρχει)."""
    try:
        res = supabase.table("cost_settings").select("*").eq("id", 1).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return None

@st.cache_data(ttl=90)
def load_cocktail_costs():
    """Φορτώνει το χειροκίνητο 'βιομηχανικό κόστος' ανά κοκτέιλ.
    Επιστρέφει dict {cocktail_name: industrial_cost}."""
    try:
        res = supabase.table("cocktail_costs").select("*").execute()
        return {r["cocktail_name"]: float(r.get("industrial_cost") or 0.0) for r in (res.data or [])}
    except Exception:
        return {}

@st.cache_data(ttl=60)
def load_box_gift_offers():
    """Φορτώνει τους κωδικούς που τρέχουν σε πολιτική 'X κούτες = Ν δώρο' (πίνακας
    box_gift_offers). Cached μόνο 60 δευτ. γιατί ελέγχεται συχνά στο Lot Παραγωγής."""
    try:
        res = supabase.table("box_gift_offers").select("*").eq("active", True).execute()
        return {r["cocktail_name"]: r for r in (res.data or [])}
    except Exception:
        return {}

@st.cache_data(ttl=300)
def load_customer_names():
    """Λίστα ονομάτων πελατών για το dropdown του Lot Παραγωγής.
    🚀 PERFORMANCE FIX: πριν ξαναφορτωνόταν από τη βάση σε ΚΑΘΕ κλικ στην καρτέλα."""
    try:
        res_cust = supabase.table("customers").select("name").execute()
        names = sorted([c["name"] for c in res_cust.data]) if res_cust.data else []
        if "Λιανική / Άγνωστος" not in names:
            names.insert(0, "Λιανική / Άγνωστος")
        return names
    except Exception:
        return ["Λιανική / Άγνωστος"]

@st.cache_data(ttl=90)
def load_production_log_snapshot():
    """Στιγμιότυπο του production_log για τον έλεγχο εκκρεμοτήτων LOT/λήξης στο Lot
    Παραγωγής. 🚀 PERFORMANCE FIX: πριν ξαναφόρτωνε έως 100.000 γραμμές ΣΕ ΚΑΘΕ κλικ.
    Τώρα φορτώνεται μία φορά και ξαναχρησιμοποιείται για 90 δευτερόλεπτα (ή μέχρι το
    επόμενο st.cache_data.clear() μετά από αποθήκευση)."""
    res = supabase.table("production_log").select("*").order("id", desc=True).limit(100000).execute()
    return res.data if res.data else []

_cost_settings = load_cost_settings()
_cocktail_costs_map = load_cocktail_costs()
_manual_cost_active = bool(_cost_settings and _cost_settings.get("active"))

def get_unit_cost_for_cocktail(cocktail_name, raw_cost=0.0):
    """Το πλήρες κόστος/τεμάχιο για ΣΥΓΚΕΚΡΙΜΕΝΟ κοκτέιλ.
    - Αν το χειροκίνητο σενάριο κόστους (καρτέλα «💰 Κοστολόγιο») είναι ΕΝΕΡΓΟ:
      επιστρέφει raw_cost (αυτόματο κόστος πρώτων υλών) + εργατικά[κοκτέιλ] +
      κόστος_συσκευασίας (και τα δύο χειροκίνητα καταχωρημένα) — τώρα ΠΡΟΣΤΙΘΕΤΑΙ
      πάνω στο αυτόματο κόστος υλικών, δεν το αντικαθιστά πια.
    - Αν είναι ΑΝΕΝΕΡΓΟ: επιστρέφει raw_cost (αυτόματο κόστος υλικών) + 0,22€
      (η αρχική, προεπιλεγμένη συμπεριφορά της εφαρμογής)."""
    if _manual_cost_active:
        operational = float((_cost_settings or {}).get("operational_cost") or 0.0)
        industrial = float(_cocktail_costs_map.get(cocktail_name, 0.0))
        return round(float(raw_cost or 0.0) + industrial + operational, 4)
    return round(float(raw_cost or 0.0) + _TOTAL_FIXED_FALLBACK, 4)

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
        
        # Μετονομασία στηλών για να είναι ωραίος ο πίνακας
        df = df.rename(columns={
            "id": "ID", "name": "Name", "price": "Price", "volume": "Volume", 
            "abv": "Αλκοόλ %", "weight_full": "Weight_Full", "current_stock_ml": "Απόθεμα (ml)"
        })
        
        # Αν η στήλη "Απόθεμα (ml)" δεν υπάρχει καν στη βάση, την δημιουργούμε εδώ για να μην κρασάρει
        if "Απόθεμα (ml)" not in df.columns:
            df["Απόθεμα (ml)"] = 0.0
            
        df["Τιμή/ml"] = df["Price"] / df["Volume"]
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
            "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "📐 Markup & Margin", "💰 Κοστολόγιο & Σταθερά Έξοδα", "🎯 Νεκρό Σημείο", "📑 Έσοδα - Έξοδα", "🎁 Κιβωτιακή Πολιτική", "📦 Παραγγελίες B2B", 
            "📦 Lot Παραγωγής", "📈 Dashboard", "👥 Πελατολόγιο", "🧼 Συντήρηση & HACCP","🧪 Προσομοίωση Πωλήσεων", "🛒 Λίστα Αγορών", "🚚 Παραλαβές", "🧪 Δοκιμαστικές Παραγωγές"
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
        
        # 🚀 ΔΙΟΡΘΩΣΗ: Προστέθηκε το 'Απόθεμα (ml)' στη λίστα των στηλών
        display_columns = ["ID", "Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Weight_Full"]
        if "Απόθεμα (ml)" in df_ing.columns:
            display_columns.append("Απόθεμα (ml)")
            
        st.dataframe(df_ing[display_columns], use_container_width=True)
        
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
                            <th>Απόθεμα (ml)</th> </tr>
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
                    <td>{row.get('Απόθεμα (ml)', 0.0):.1f} ml</td> </tr>
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
        col1, col2, col3 = st.columns(3)
        new_rec_name = col1.text_input("Όνομα Cocktail", placeholder="π.χ. CabClub Margarita")
        new_barcode = col2.text_input("Barcode / Κωδικός", placeholder="Προαιρετικό")
        new_catalog_price = col3.number_input("Τιμή Καταλόγου (€)", min_value=0.0, step=0.10, help="Χρησιμοποιείται σε Ανάλυση, Markup & Margin, Εμπορική Πολιτική. Αν μείνει 0, θα δείχνει αρνητικά περιθώρια μέχρι να τη συμπληρώσεις.")
        
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
                if new_catalog_price <= 0:
                    st.warning("⚠️ Η τιμή καταλόγου είναι 0€ — η συνταγή θα αποθηκευτεί, αλλά η Ανάλυση/Markup & Margin θα δείχνουν αρνητικό περιθώριο μέχρι να ορίσεις τιμή στη Διαχείριση.")
                try:
                    # ΒΗΜΑ 1: Δημιουργία της Συνταγής (Title) στον πίνακα 'recipes'
                    res = supabase.table("recipes").insert({
                        "name": new_rec_name.strip(),
                        "barcode": new_barcode.strip() if new_barcode else "",
                        "catalog_price": new_catalog_price
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
    # 🔧 FIX: πριν έπαιρνε ΟΛΕΣ τις συνταγές (και τις αρχειοθετημένες _OLD_v.. από επεξεργασίες),
    # γεμίζοντας το dropdown με "φαντάσματα". Τώρα παίρνει μόνο τις ενεργές.
    res_rec = supabase.table("recipes").select("*").eq("is_active", True).order("name").execute()
    
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
                            current_version = int(rec_row.get("version", 1)) if "version" in rec_row else 1
                            
                            # 🚀 ΛΥΣΗ ΣΦΑΛΜΑΤΟΣ: Αλλάζουμε το όνομα της παλιάς συνταγής για να "ελευθερωθεί" το κανονικό όνομα!
                            old_safe_name = f"{rec_row['name']}_OLD_v{current_version}_{rec_id}"
                            
                            # 2. ΑΡΧΕΙΟΘΕΤΗΣΗ ΠΑΛΙΑΣ ΚΑΙ ΜΕΤΟΝΟΜΑΣΙΑ
                            supabase.table("recipes").update({
                                "is_active": False,
                                "name": old_safe_name  # <--- Η ΜΑΓΙΚΗ ΛΥΣΗ
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
                            for item in new_ingredients_list:
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
            "Name": str(item["name"]).strip(),
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
        # 🚀 ΔΗΜΙΟΥΡΓΙΑ TABS ΕΔΩ
        tab1, tab2 = st.tabs(["🍸 Ανάλυση Συνταγών & Πωλήσεων", "🍾 Εις Βάθος Ανάλυση Πρώτων Υλών"])
        
        # =========================================================================
        # TAB 1: Ο ΠΑΛΙΟΣ ΣΟΥ ΚΩΔΙΚΑΣ (ΑΚΡΙΒΩΣ ΟΠΩΣ ΗΤΑΝ)
        # =========================================================================
        with tab1:
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
            missing_ingredients = [] 
            
            # --- ΣΥΛΛΟΓΗ ΔΕΔΟΜΕΝΩΝ ΣΥΝΤΑΓΗΣ ---
            for i in range(1, 14):
                ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                ml = float(r.get(f"ML{i}", 0))
                
                if ing_n != "ΚΕΝΟ" and ml > 0:
                    total_ml_cocktail += ml
                    if ing_n == "Νερό":
                        total_weight_cocktail += ml 
                        breakdown.append({"Υλικό": "Νερό", "ML": ml, "Βάρος (g)": ml, "Κόστος": 0.0, "Alc %": 0.0})
                    elif ing_n not in ["nan", ""]:
                        match = df_ing[df_ing["Name"] == ing_n]
                        
                        if not match.empty:
                            ing_row = match.iloc[0]
                            alc_val = float(ing_row.get("Αλκοόλ %", 0))
                            actual_alc_pct = alc_val if alc_val <= 1 else alc_val / 100
                            pure_alc_ml += (ml * actual_alc_pct)
                            
                            price_ml = float(ing_row.get("Τιμή/ml", 0))
                            item_cost = ml * price_ml
                            raw_cost += item_cost
                            
                            # --- ΔΥΝΑΜΙΚΟΣ ΥΠΟΛΟΓΙΣΜΟΣ ΒΑΡΟΥΣ ---
                            pkg_weight = float(ing_row.get("weight_full", 0) or 0)
                            pkg_volume = float(ing_row.get("Volume", 0) or 0)
                            
                            if pkg_volume > 0 and pkg_weight > 0:
                                item_weight = (pkg_weight / pkg_volume) * ml
                            else:
                                item_weight = ml 
                            
                            total_weight_cocktail += item_weight
                            
                            breakdown.append({
                                "Υλικό": ing_n, 
                                "ML": ml, 
                                "Βάρος (g)": item_weight, 
                                "Κόστος": item_cost, 
                                "Alc %": actual_alc_pct * 100
                            })
                        else:
                            missing_ingredients.append(ing_n)
                            total_weight_cocktail += ml
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
            total_production = get_unit_cost_for_cocktail(choice, raw_cost)
            if _manual_cost_active:
                # 🔧 FIX: πριν έδειχνε ΜΟΝΟ το Κόστος Συσκευασίας, αγνοώντας τα Εργατικά — το
                # άθροισμα k1+k3 δεν έβγαινε ίσο με το k4. Τώρα δείχνει και τα δύο μαζί
                # (η λεπτομερής ανάλυση παραμένει στη γραμμή διαφάνειας από κάτω).
                fixed_cost = float((_cost_settings or {}).get("operational_cost") or 0.0) + float(_cocktail_costs_map.get(choice, 0.0))
            else:
                fixed_cost = _TOTAL_FIXED_FALLBACK  # ίδιο πάντα (0,22€), όπως ήταν εξ αρχής
            
            profit_retail = p_retail - total_production
            profit_agent = p_agent - total_production
            profit_custom = p_custom - total_production
            margin_retail = (profit_retail / p_retail * 100) if p_retail > 0 else 0

            # --- ΕΜΦΑΝΙΣΗ ΣΤΗΝ ΟΘΟΝΗ ---
            st.subheader(f"Στατιστικά για: {choice}")
            m_col1, m_col2, m_col3 = st.columns(3) 
            m_col1.metric("Συνολική Ποσότητα", f"{total_ml_cocktail:.1f} ml".replace('.', ','))
            m_col2.metric("Συνολικό Βάρος", f"{total_weight_cocktail:.1f} g".replace('.', ',')) 
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
            k3.metric("Εργατικά + Συσκευασία" if _manual_cost_active else "Σταθερά Έξοδα", f"{fixed_cost:.2f} €".replace('.', ','))
            k4.metric("ΣΥΝΟΛΟ ΚΟΣΤΟΥΣ", f"{total_production:.2f} €".replace('.', ','))
            # 🔍 ΔΙΑΦΑΝΕΙΑ ΥΠΟΛΟΓΙΣΜΟΥ — δείχνει ΑΚΡΙΒΩΣ πώς προέκυψε το Σύνολο Κόστους.
            if _manual_cost_active:
                _ind_dbg = float(_cocktail_costs_map.get(choice, 0.0))
                _op_dbg = float((_cost_settings or {}).get("operational_cost") or 0.0)
                st.caption(f"🔧 Χειροκίνητο Κοστολόγιο ΕΝΕΡΓΟ: {raw_cost:.4f}€ πρώτες ύλες + {_ind_dbg:.4f}€ Εργατικά + {_op_dbg:.4f}€ Κόστος Συσκευασίας = {total_production:.4f} €/τμχ.")
            else:
                st.caption(f"🔧 Χειροκίνητο Κοστολόγιο ΑΝΕΝΕΡΓΟ: {raw_cost:.4f}€ αυτόματο κόστος υλικών + {_TOTAL_FIXED_FALLBACK:.2f}€ προεπιλογή = {total_production:.4f} €/τμχ.")

            # --- 🆚 ΣΥΓΚΡΙΣΗ: ΕΝΕΡΓΟ vs ΑΝΕΝΕΡΓΟ σενάριο (πάντα ορατή, ό,τι κι αν είναι ενεργό τώρα) ---
            _op_cost_cmp = float((_cost_settings or {}).get("operational_cost") or 0.0)
            _ind_cost_cmp = float(_cocktail_costs_map.get(choice, 0.0))
            _cost_when_active = round(raw_cost + _ind_cost_cmp + _op_cost_cmp, 4)
            _cost_when_inactive = round(raw_cost + _TOTAL_FIXED_FALLBACK, 4)

            if _cost_when_inactive > 0:
                _diff_pct = round((_cost_when_active - _cost_when_inactive) / _cost_when_inactive * 100, 1)
            else:
                _diff_pct = 0.0

            with st.expander(f"🆚 Σύγκριση Ενεργό vs Ανενεργό Σενάριο — {choice}", expanded=True):
                dc1, dc2, dc3 = st.columns(3)
                dc1.metric(
                    "⛔ Κόστος (Ανενεργό)",
                    f"{_cost_when_inactive:.4f} €",
                    help=f"{raw_cost:.4f}€ υλικά + {_TOTAL_FIXED_FALLBACK:.2f}€ προεπιλογή"
                )
                dc2.metric(
                    "✅ Κόστος (Ενεργό)",
                    f"{_cost_when_active:.4f} €",
                    help=f"{_ind_cost_cmp:.4f}€ εργατικά + {_op_cost_cmp:.4f}€ κόστος συσκευασίας"
                )
                dc3.metric(
                    "Διαφορά Κόστους",
                    f"{_diff_pct:+.1f}%",
                    delta=f"{_cost_when_active - _cost_when_inactive:+.4f} €",
                    delta_color="inverse"
                )

                # Διαφορά και στο ΠΕΡΙΘΩΡΙΟ (κέρδος), όχι μόνο στο κόστος
                if p_retail > 0:
                    _profit_inactive = p_retail - _cost_when_inactive
                    _profit_active = p_retail - _cost_when_active
                    _profit_diff_pct = round((_profit_active - _profit_inactive) / abs(_profit_inactive) * 100, 1) if _profit_inactive != 0 else 0.0
                    st.caption(
                        f"💰 Περιθώριο Λιανικής: Ανενεργό {_profit_inactive:.2f}€ → Ενεργό {_profit_active:.2f}€ "
                        f"({_profit_diff_pct:+.1f}%), με βάση τιμή καταλόγου {p_retail:.2f}€."
                    )
                st.caption(f"👉 Το τρέχον ΕΝΕΡΓΟ σενάριο στην εφαρμογή αυτή τη στιγμή είναι: **{'✅ Ενεργό (Χειροκίνητο)' if _manual_cost_active else '⛔ Ανενεργό (Αυτόματο)'}**")


            # --- ΠΙΝΑΚΑΣ ΥΛΙΚΩΝ ΣΤΗΝ ΟΘΟΝΗ ---
            st.markdown("---")
            st.write("### 🍹 Σύνθεση Υλικών")
            df_screen = pd.DataFrame(breakdown)
            if not df_screen.empty:
                df_render = df_screen.copy()
                for col in ["ML", "Βάρος (g)", "Alc %", "Κόστος"]: 
                    if col in df_render.columns:
                        df_render[col] = df_render[col].apply(lambda x: f"{x:.2f}".replace('.', ','))
                st.table(df_render[["Υλικό", "ML", "Βάρος (g)", "Alc %", "Κόστος"]])

            # =====================================================================
            # ΑΝΑΛΥΣΗ ΠΩΛΗΣΕΩΝ ΚΑΙ ΑΠΟΔΟΣΗΣ ΠΡΟΪΟΝΤΟΣ
            # =====================================================================
            st.markdown("---")
            st.write(f"### 📈 Οικονομική Απόδοση & Πωλήσεις ({choice})")
            
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
                
                if "prod_time" in df_sales.columns and "prod_date" in df_sales.columns:
                    df_sales = df_sales.drop_duplicates(subset=["cocktail_name", "prod_date", "prod_time", "customer"])
                
                df_sales['t_pcs'] = pd.to_numeric(df_sales.get('pieces', 0), errors='coerce').fillna(0)
                df_sales['f_pcs'] = pd.to_numeric(df_sales.get('free_pieces', 0), errors='coerce').fillna(0)
                df_sales['s_pcs'] = pd.to_numeric(df_sales.get('discounted_pieces', 0), errors='coerce').fillna(0)
                df_sales['s_pct'] = pd.to_numeric(df_sales.get('discount_pct', 0), errors='coerce').fillna(0)

                df_sales['s_pcs'] = df_sales.apply(lambda r: min(r['s_pcs'], max(0, r['t_pcs'] - r['f_pcs'])), axis=1)
                df_sales['normal_pcs'] = df_sales['t_pcs'] - df_sales['f_pcs'] - df_sales['s_pcs']

                catalog_price = 0.0
                try:
                    res_rec_price = supabase.table("recipes").select("catalog_price").eq("name", choice).execute()
                    if res_rec_price.data:
                        catalog_price = float(res_rec_price.data[0].get("catalog_price", 0.0) or 0.0)
                except Exception:
                    pass
                
                df_sales['customer'] = df_sales.get('customer', '').astype(str).str.strip()
                df_sales['global_discount'] = df_sales['customer'].map(cust_discount_map).fillna(0)

                df_sales['price_after_global'] = catalog_price * (1 - (df_sales['global_discount'] / 100))
                
                df_sales['rev_normal'] = df_sales['normal_pcs'] * df_sales['price_after_global']
                df_sales['rev_special'] = df_sales['s_pcs'] * df_sales['price_after_global'] * (1 - (df_sales['s_pct'] / 100))
                
                df_sales['Theoretical_Revenue'] = df_sales['rev_normal'] + df_sales['rev_special']
                df_sales['Theoretical_Revenue'] = df_sales['Theoretical_Revenue'].clip(lower=0)

                total_produced_pcs = int(df_sales['t_pcs'].sum())
                total_free_pcs = int(df_sales['f_pcs'].sum())
                total_real_revenue = df_sales['Theoretical_Revenue'].sum()
                
                # 🔧 FIX: πριν πολλαπλασίαζε ΟΛΗ την ιστορική παραγωγή με το ΣΗΜΕΡΙΝΟ κόστος
                # (λάθος αν το κόστος άλλαξε στο μεταξύ). Τώρα χρησιμοποιεί το πραγματικό,
                # καταγεγραμμένο κόστος ανά παρτίδα (applied_cost) — πέφτει στο σημερινό μόνο
                # για παλιές εγγραφές που δεν έχουν αυτό το πεδίο καταγεγραμμένο.
                df_sales['_hist_applied_cost'] = pd.to_numeric(df_sales.get('applied_cost'), errors='coerce')
                df_sales['_cost_per_batch'] = df_sales['_hist_applied_cost'].fillna(total_production) * df_sales['t_pcs']
                total_production_cost = df_sales['_cost_per_batch'].sum()
                total_net_profit = total_real_revenue - total_production_cost
                
                profit_percentage = 0.0
                cost_percentage = 0.0
                
                if total_real_revenue > 0:
                    profit_percentage = (total_net_profit / total_real_revenue) * 100.0
                    cost_percentage = (total_production_cost / total_real_revenue) * 100.0
                    
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

            # =========================================================================
            # 🖨️ ΚΕΝΤΡΟ ΕΚΤΥΠΩΣΕΩΝ: ΕΡΓΑΣΤΗΡΙΟ & ΚΑΤΑΛΟΓΟΣ ΠΕΛΑΤΩΝ
            # =========================================================================
            st.divider()
            st.subheader("🖨️ Κέντρο Εκτυπώσεων")
            
            if 'df_rec' in locals() and not df_rec.empty:
                # 1. Κοινή Επιλογή Κοκτέιλ (Ισχύει και για τα δύο βιβλία!)
                available_cocktails_print = sorted(df_rec['Ονομα'].astype(str).unique().tolist())
                selected_to_print = st.multiselect(
                    "🍸 Επιλέξτε τα Κοκτέιλ που θέλετε να συμπεριληφθούν στις εκτυπώσεις:",
                    options=available_cocktails_print,
                    default=available_cocktails_print
                )
                
                # Φιλτράρισμα του πίνακα βάσει επιλογής
                df_print = df_rec[df_rec['Ονομα'].isin(selected_to_print)]

                col_print1, col_print2 = st.columns(2)

                # -------------------------------------------------------------------------
                # ΣΤΗΛΗ 1: ΚΙΤΡΙΝΟ ΒΙΒΛΙΟ (Εσωτερική Χρήση)
                # -------------------------------------------------------------------------
                with col_print1:
                    st.markdown("#### 📒 Εσωτερικό Συνταγολόγιο")
                    st.caption("Αναλυτικά βάρη, ml, μέθοδοι & κιβώτια.")
                    
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
                            .recipe-card {{ background-color: white; border: 1px solid #ddd; border-radius: 12px; padding: 25px; margin-bottom: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); page-break-inside: avoid; }}
                            .recipe-header {{ background-color: #ffcc00; color: #1a1a1a; padding: 15px; border-radius: 8px 8px 0 0; margin: -25px -25px 20px -25px; }}
                            .recipe-name {{ margin: 0; font-size: 26px; text-transform: uppercase; }}
                            .barcode-label {{ font-size: 14px; opacity: 0.8; font-weight: bold; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                            th {{ background-color: #fff9e6; text-align: left; padding: 12px; border-bottom: 2px solid #ffcc00; color: #444; }}
                            td {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 15px; }}
                            .ing-name {{ font-weight: bold; color: #2c3e50; }}
                            .footer {{ text-align: center; font-size: 12px; color: #7f8c8d; margin-top: 60px; border-top: 1px solid #ccc; padding-top: 10px; }}
                            .analysis-box {{ margin-top:20px; padding:12px; background:#fffdf2; border-top:3px solid #ffcc00; border-radius: 0 0 8px 8px; }}
                        </style>
                    </head>
                    <body>
                        <div class='main-title'>
                            {f'<img src="data:image/png;base64,{logo_base64}" class="logo-img"><br>' if logo_base64 else ''}
                            <h1>CABCLUB COCKTAILS</h1>
                            <h2>ΟΛΟΚΛΗΡΩΜΕΝΟ ΒΙΒΛΙΟ ΣΥΝΤΑΓΩΝ</h2>
                            <p>Σύνολο Συνταγών: {len(df_print)}</p>
                        </div>
                    """

                    for _, recipe in df_print.iterrows():
                        name = recipe.get("Ονομα", "Χωρίς Όνομα")
                        bc = recipe.get("Barcode", "-")
                        
                        name_upper = str(name).strip().upper()
                        is_special = "PINA COLADA" in name_upper or "ZOMBIE" in name_upper
                        qty1 = 12 if is_special else 24
                        qty2 = 24 if is_special else 48
                        
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
                                        <th>Βάρος για {qty1} (g)</th>
                                        <th>Βάρος για {qty2} (g)</th>
                                        <th>Κόστος / τμχ (€)</th>
                                    </tr>
                                </thead>
                                <tbody>
                        """
                        
                        r_total_ml = 0
                        r_total_alc = 0
                        r_total_weight = 0 
                        r_total_cost = 0.0
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
                                ing_weight = ml
                                ing_cost = 0.0
                                
                                if ing_clean == "Νερό":
                                    ing_weight = ml
                                elif not df_ing.empty and ing_clean in df_ing["Name"].values:
                                    ing_row = df_ing[df_ing["Name"] == ing_clean].iloc[0]
                                    pkg_weight = float(ing_row.get("weight_full", 0) or 0)
                                    pkg_volume = float(ing_row.get("Volume", 0) or 0)
                                    
                                    # Υπολογισμός Κόστους
                                    try:
                                        pkg_price = float(str(ing_row.get("Price", ing_row.get("Τιμή", 0))).replace(',', '.'))
                                    except:
                                        pkg_price = 0.0
                                        
                                    if pkg_volume > 0:
                                        if pkg_weight > 0:
                                            ing_weight = (pkg_weight / pkg_volume) * ml
                                        ing_cost = (pkg_price / pkg_volume) * ml
                                
                                weight_qty1 = ing_weight * qty1
                                weight_qty2 = ing_weight * qty2
                                
                                html_book += f"""
                                    <tr>
                                        <td class='ing-name'>{ing_clean}</td>
                                        <td>{ml:.2f} ml</td>
                                        <td>{ing_weight:.1f} g</td>
                                        <td style='color:#d32f2f;'>{weight_qty1:.1f} g</td>
                                        <td style='color:#d32f2f;'>{weight_qty2:.1f} g</td>
                                        <td style='font-weight:bold; color:#2c3e50;'>{ing_cost:.3f} €</td>
                                    </tr>
                                """
                                r_found_ing += 1
                                r_total_ml += ml
                                r_total_weight += ing_weight
                                r_total_cost += ing_cost
                                
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
                            html_book += "<tr><td colspan='6'><i>Δεν έχουν καταχωρηθεί συστατικά.</i></td></tr>"

                        r_final_abv = (r_total_alc / r_total_ml * 100) if r_total_ml > 0 else 0
                        r_sugg_price = float(str(recipe.get("Τιμή Καταλόγου", 0.0)).replace(',', '.'))

                        html_book += f"""
                                </tbody>
                            </table>
                            <div class='analysis-box'>
                                <span style='font-size:16px;'>Αλκοόλ (ABV): <b>{r_final_abv:.2f}%</b></span> | 
                                <span style='font-size:16px;'>Βάρος (1 τμχ): <b>{r_total_weight:.1f} g</b></span> | 
                                <span style='font-size:16px; color:#d32f2f;'>Κόστος Υλικών (1 τμχ): <b>{r_total_cost:.2f} €</b></span>
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
                        label="📑 Λήψη Συνταγολογίου (Εργαστήριο)",
                        data=html_book,
                        file_name=f"Recipe_Book_Yellow_{datetime.now(greece_tz).strftime('%d_%m_%Y')}.html",
                        mime="text/html",
                        use_container_width=True
                    )

                # -------------------------------------------------------------------------
                # ΣΤΗΛΗ 2: ΚΩΔΙΚΟΛΟΓΙΟ (Για Πελάτες)
                # -------------------------------------------------------------------------
                with col_print2:
                    st.markdown("#### 📜 Κωδικολόγιο Πελατών")
                    st.caption("Όνομα, καθαρά συστατικά & τιμή.")
                    show_prices = st.checkbox("Εμφάνιση Τιμών Λιανικής;", value=True)
                    
                    cocktails_html = ""
                    for _, recipe in df_print.iterrows():
                        c_name = str(recipe.get("Ονομα", "Χωρίς Όνομα")).strip()
                        
                        # Εύρεση Τιμής
                        c_price = 0.0
                        try:
                            if 'recipe_prices' in globals() or 'recipe_prices' in locals():
                                c_price = float(recipe_prices.get(c_name, 0.0))
                            if c_price == 0.0:
                                c_price = float(str(recipe.get("Τιμή Καταλόγου", 0.0)).replace(',', '.'))
                        except:
                            pass
                        
                        price_html = f"<div class='cocktail-price'>{c_price:.2f} €</div>" if show_prices and c_price > 0 else ""
                        
                        # Εύρεση Πεντακάθαρων Συστατικών (χωρίς ml)
                        clean_ing_list = []
                        for i in range(1, 14):
                            ing_clean = str(recipe.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "")).strip()
                            ing_check = ing_clean.upper()
                            if ing_clean and ing_check not in ["NAN", "ΚΕΝΟ", "ΚΕΝΟ.", "-", "NONE", "0", "NULL"]:
                                clean_ing_list.append(ing_clean)
                        
                        final_ingredients = ", ".join(clean_ing_list) if clean_ing_list else "Μυστική Συνταγή"
                        
                        cocktails_html += f"""
                        <div class="cocktail-item">
                            <div class="cocktail-header">
                                <div class="cocktail-title">{c_name}</div>
                                {price_html}
                            </div>
                            <p class="cocktail-desc"><em>Συστατικά:</em> {final_ingredients}</p>
                        </div>
                        """
                        
                    html_menu = """
                    <!DOCTYPE html>
                    <html lang="el">
                    <head>
                    <meta charset="UTF-8">
                    <style>
                        *, *::before, *::after { box-sizing: border-box; }
                        @page { size: A4; margin: 15mm 15mm 20mm 15mm; background-color: #fcfbfa; }
                        body { margin: 0; padding: 20px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #2c3e50; background-color: #fcfbfa; max-width: 800px; margin: auto; }
                        .header-banner { margin-bottom: 30px; padding: 20px; background-color: #1b2a4a; color: white; text-align: center; border-bottom: 4px solid #c59b27; border-radius: 5px; }
                        .header-banner h1 { margin: 0; font-size: 24pt; letter-spacing: 2px; text-transform: uppercase; font-weight: 300; }
                        .header-banner p { margin: 5px 0 0 0; font-size: 11pt; color: #d4ac0d; font-style: italic; }
                        .cocktail-container { display: flex; flex-direction: column; gap: 15px; }
                        .cocktail-item { background-color: white; border: 1px solid #e0e0e0; border-radius: 4px; padding: 15px; border-left: 5px solid #1b2a4a; box-shadow: 0 2px 4px rgba(0,0,0,0.05); page-break-inside: avoid; }
                        .cocktail-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px; border-bottom: 1px dashed #ecf0f1; padding-bottom: 5px; }
                        .cocktail-title { font-size: 14pt; font-weight: bold; color: #1b2a4a; margin: 0; }
                        .cocktail-price { font-size: 13pt; font-weight: bold; color: #c59b27; margin: 0; }
                        .cocktail-desc { font-size: 10pt; color: #555; line-height: 1.5; margin: 0; }
                        @media print { body { padding: 0; background-color: white; } .cocktail-item { box-shadow: none; border: 1px solid #ccc; border-left: 5px solid #1b2a4a; } }
                    </style>
                    </head>
                    <body>
                        <div class="header-banner">
                            <h1>ΚΩΔΙΚΟΛΟΓΙΟ</h1>
                            <p>Premium Cocktail Collection</p>
                        </div>
                        <div class="cocktail-container">
                            """ + cocktails_html + """
                        </div>
                    </body>
                    </html>
                    """
                    
                    st.download_button(
                        label="📥 Λήψη Κωδικολογίου (Πελάτες)",
                        data=html_menu.encode('utf-8'),
                        file_name=f"Menu_Pelaton_{datetime.now(greece_tz).strftime('%d_%m_%Y')}.html",
                        mime="text/html",
                        use_container_width=True
                    )

        # =========================================================================
        # TAB 2: ΝΕΑ ΕΙΣ ΒΑΘΟΣ ΑΝΑΛΥΣΗ ΠΡΩΤΩΝ ΥΛΩΝ (ΑΠΟΛΥΤΗ ΤΑΥΤΙΣΗ ΜΕ DASHBOARD)
        # =========================================================================
        with tab2:
            st.subheader("🍾 Ανάλυση Κατανάλωσης Πρώτων Υλών (Ιστορικά Δεδομένα)")
            
            with st.spinner("Φόρτωση ιστορικών δεδομένων..."):
                try:
                    # 🚀 Φορτώνουμε τα ιστορικά δεδομένα ΑΚΡΙΒΩΣ όπως τα φορτώνει το Dashboard
                    res_raw = supabase.table("production_log").select("*").execute()
                    df_tab2 = pd.DataFrame(res_raw.data)
                except Exception as e:
                    df_tab2 = pd.DataFrame()
                    st.error(f"Σφάλμα φόρτωσης: {e}")
            
            if not df_ing.empty and not df_tab2.empty:
                ing_names = sorted(df_ing['Name'].dropna().unique().tolist())
                selected_ing = st.selectbox("🔍 Επιλέξτε Πρώτη Ύλη προς ανάλυση:", ing_names, key="ing_analysis_select")
                
                if selected_ing:
                    ing_info = df_ing[df_ing['Name'] == selected_ing].iloc[0]
                    bottle_vol = float(ing_info['Volume'])
                    price_per_ml = float(ing_info['Τιμή/ml'])
                    
                    if 'ingredient_name' in df_tab2.columns:
                        df_ing_history = df_tab2[df_tab2['ingredient_name'] == selected_ing].copy()
                        
                        # 🚀 ΚΑΘΑΡΙΣΜΟΣ ΔΙΠΛΟΕΓΓΡΑΦΩΝ
                        if not df_ing_history.empty and "prod_time" in df_ing_history.columns and "prod_date" in df_ing_history.columns:
                            df_ing_history = df_ing_history.drop_duplicates(subset=["cocktail_name", "prod_date", "prod_time", "customer", "ingredient_name"])
                            
                        if not df_ing_history.empty:
                            df_ing_history['total_ml'] = pd.to_numeric(df_ing_history.get('total_ml', 0), errors='coerce').fillna(0)
                            
                            if 'pieces' not in df_ing_history.columns:
                                df_ing_history['pieces'] = 0
                            else:
                                df_ing_history['pieces'] = pd.to_numeric(df_ing_history['pieces'], errors='coerce').fillna(0)
                            
                            group_col = 'cocktail_name' if 'cocktail_name' in df_ing_history.columns else 'recipe_name' if 'recipe_name' in df_ing_history.columns else None
                            
                            if group_col:
                                df_breakdown = df_ing_history.groupby(group_col).agg(
                                    Κατανάλωση_ml=('total_ml', 'sum'),
                                    Παραχθέντα_Τεμάχια=('pieces', 'sum')
                                ).reset_index()
                                df_breakdown.rename(columns={group_col: 'Κοκτέιλ', 'Κατανάλωση_ml': 'Κατανάλωση (ml)', 'Παραχθέντα_Τεμάχια': 'Παραχθέντα Τεμάχια'}, inplace=True)
                            else:
                                df_breakdown = pd.DataFrame([{
                                    "Κοκτέιλ": "Ιστορικό / Διάφορα",
                                    "Παραχθέντα Τεμάχια": df_ing_history['pieces'].sum(),
                                    "Κατανάλωση (ml)": df_ing_history['total_ml'].sum()
                                }])
                                
                            df_breakdown = df_breakdown[df_breakdown['Κατανάλωση (ml)'] > 0]
                            total_ml_used = df_breakdown['Κατανάλωση (ml)'].sum()
                            
                            total_bottles = total_ml_used / bottle_vol if bottle_vol > 0 else 0
                            total_cost = total_ml_used * price_per_ml 

                            st.divider()
                            m1, m2, m3 = st.columns(3)
                            m1.metric("📦 Φιάλες που καταναλώθηκαν", f"{total_bottles:.2f} μπουκάλια".replace('.', ','))
                            m2.metric("💶 Κόστος στη ΣΗΜΕΡΙΝΗ Τιμή", f"{total_cost:.2f} €".replace('.', ','), help="Υπολογισμένο με τη σημερινή τιμή/ml του υλικού — όχι το πραγματικό ιστορικό κόστος αγοράς.")
                            m3.metric("💧 Συνολικά ml", f"{total_ml_used:,.0f} ml".replace(',', 'X').replace('.', ',').replace('X', '.'))

                            if not df_breakdown.empty:
                                df_breakdown['Αναλογία (%)'] = (df_breakdown['Κατανάλωση (ml)'] / total_ml_used) * 100
                                
                                # 🚀 ΝΕΟ: Υπολογισμός Κόστους της πρώτης ύλης ανά Κοκτέιλ
                                df_breakdown['Κόστος (€)'] = df_breakdown['Κατανάλωση (ml)'] * price_per_ml
                                
                                st.markdown(f"#### 🍹 Πού καταναλώθηκε το {selected_ing};")
                                
                                # 1. Ο ΠΙΝΑΚΑΣ (Πιάνει πλέον όλο το πλάτος της οθόνης)
                                st.dataframe(
                                    df_breakdown.style.format({
                                        "Παραχθέντα Τεμάχια": "{:,.0f} τμχ",
                                        "Κατανάλωση (ml)": lambda x: f"{x:,.1f} ml ({x/bottle_vol:.1f} φιάλες)" if bottle_vol > 0 else f"{x:,.1f} ml",
                                        "Αναλογία (%)": "{:.1f}%",
                                        # 🚀 ΔΙΟΡΘΩΣΗ: Χρήση lambda για ασφαλή μετατροπή νομίσματος!
                                        "Κόστος (€)": lambda x: f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
                                    }).background_gradient(subset=['Κατανάλωση (ml)'], cmap='Blues'),
                                    use_container_width=True, hide_index=True
                                )
                                
                                st.markdown("<br><br>", unsafe_allow_html=True) # Κενό για να ανασαίνει το μάτι
                                
                                # 2. Η ΠΙΤΑ (Ακριβώς από κάτω, κεντραρισμένη)
                                fig = px.pie(
                                    df_breakdown, 
                                    values='Κατανάλωση (ml)', 
                                    names='Κοκτέιλ', 
                                    hole=0.4, 
                                    color_discrete_sequence=px.colors.sequential.Teal
                                )
                                fig.update_traces(textinfo='percent+label')
                                # Αυξήσαμε λίγο το ύψος (height=400) για να φαίνεται εντυπωσιακή
                                fig.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=400)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info(f"💡 Το υλικό '{selected_ing}' δεν έχει καταγραφεί ακόμα στο ιστορικό παραγωγής.")
                        else:
                            st.info(f"💡 Το υλικό '{selected_ing}' δεν έχει χρησιμοποιηθεί ακόμα σύμφωνα με το ιστορικό παραγωγής.")
                    else:
                        st.info("Δεν υπάρχει ιστορικό υλικών (total_ml) καταγεγραμμένο στον πίνακα παραγωγής.")
            else:
                st.warning("Δεν βρέθηκαν δεδομένα ιστορικού παραγωγής (df_raw) για ανάλυση.")

# =========================================================================
            # --- ΝΕΟ: ΜΑΖΙΚΗ ΕΞΑΓΩΓΗ HTML ΓΙΑ ΠΡΩΤΕΣ ΥΛΕΣ ---
            # =========================================================================
            st.divider()
            st.subheader("📑 Μαζική Εξαγωγή Αναφορών (Interactive HTML)")
            st.write("Δημιουργήστε ένα πλήρες, διαδραστικό report με πίνακες και γραφήματα για επιλεγμένες ή και για όλες τις πρώτες ύλες ταυτόχρονα.")

            col_e1, col_e2 = st.columns([3, 1])
            with col_e2:
                st.write("") # Spacer για να έρθει στο ίδιο ύψος
                st.write("")
                export_all = st.checkbox("Επιλογή Όλων των Υλών", value=False)
            
            with col_e1:
                if export_all:
                    export_selection = ing_names
                    st.info(f"Επιλέχθηκαν αυτόματα και τα {len(ing_names)} διαθέσιμα υλικά.")
                else:
                    export_selection = st.multiselect("Επιλέξτε υλικά για εξαγωγή στο Report:", ing_names, default=[selected_ing] if selected_ing else None)

            if export_selection:
                # Κουμπί για να χτιστεί το report (απαιτεί επεξεργασία αν είναι πολλά)
                if st.button("⚙️ Δημιουργία Διαδραστικού Report"):
                    with st.spinner("Ανάλυση δεδομένων & δημιουργία γραφημάτων (μπορεί να διαρκέσει λίγο)..."):
                        try:
                            now_str = datetime.now(greece_tz).strftime("%d/%m/%Y %H:%M")
                        except:
                            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                            
                        # Χτίζουμε τον "σκελετό" (κεφαλίδα) της HTML σελίδας
                        html_report = f"""
                        <!DOCTYPE html>
                        <html lang="el">
                        <head>
                            <meta charset="UTF-8">
                            <title>Report Πρώτων Υλών - CABCLUB</title>
                            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                            <style>
                                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f8; color: #333; padding: 20px; line-height: 1.6; }}
                                .container {{ max-width: 1000px; margin: auto; }}
                                .header {{ text-align: center; margin-bottom: 40px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
                                .header h1 {{ margin: 0; color: #1a3a5f; letter-spacing: 1px; }}
                                .material-card {{ background: white; margin-bottom: 40px; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-top: 5px solid #1a3a5f; page-break-inside: avoid; }}
                                .material-title {{ font-size: 24px; color: #1a3a5f; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; }}
                                .metrics {{ display: flex; justify-content: space-between; margin-top: 20px; margin-bottom: 30px; flex-wrap: wrap; gap: 15px; }}
                                .metric-box {{ text-align: center; background: #f8f9fa; padding: 15px; border-radius: 8px; flex: 1; border: 1px solid #ddd; min-width: 200px; }}
                                .metric-value {{ font-size: 22px; font-weight: bold; color: #2e7d32; margin-top: 5px; }}
                                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                                th, td {{ border: 1px solid #e0e0e0; padding: 12px; text-align: left; }}
                                th {{ background-color: #1a3a5f; color: white; text-align: center; font-weight: 500; }}
                                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                                .chart-container {{ margin-top: 30px; text-align: center; display: flex; justify-content: center; }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="header">
                                    <h1>CABCLUB COCKTAILS</h1>
                                    <h2>ΣΥΓΚΕΝΤΡΩΤΙΚΗ ΑΝΑΦΟΡΑ ΚΑΤΑΝΑΛΩΣΕΩΝ</h2>
                                    <p style="color: #666;">Ημερομηνία Εξαγωγής: {now_str}</p>
                                </div>
                        """

                        # Λούπα για κάθε υλικό που επιλέχθηκε
                        for ing in export_selection:
                            ing_info = df_ing[df_ing['Name'] == ing].iloc[0]
                            bottle_vol = float(ing_info['Volume'])
                            price_per_ml = float(ing_info['Τιμή/ml'])
                            
                            if 'ingredient_name' in df_tab2.columns:
                                df_ing_history = df_tab2[df_tab2['ingredient_name'] == ing].copy()
                            else:
                                df_ing_history = pd.DataFrame()
                            
                            # Καθαρισμός διπλοεγγραφών
                            if not df_ing_history.empty and "prod_time" in df_ing_history.columns and "prod_date" in df_ing_history.columns:
                                df_ing_history = df_ing_history.drop_duplicates(subset=["cocktail_name", "prod_date", "prod_time", "customer", "ingredient_name"])
                            
                            if not df_ing_history.empty:
                                df_ing_history['total_ml'] = pd.to_numeric(df_ing_history.get('total_ml', 0), errors='coerce').fillna(0)
                                df_ing_history['pieces'] = pd.to_numeric(df_ing_history.get('pieces', 0), errors='coerce').fillna(0)
                                
                                group_col = 'cocktail_name' if 'cocktail_name' in df_ing_history.columns else 'recipe_name' if 'recipe_name' in df_ing_history.columns else None
                                
                                if group_col:
                                    df_breakdown = df_ing_history.groupby(group_col).agg(
                                        Κατανάλωση_ml=('total_ml', 'sum'),
                                        Παραχθέντα_Τεμάχια=('pieces', 'sum')
                                    ).reset_index()
                                    df_breakdown.rename(columns={group_col: 'Κοκτέιλ', 'Κατανάλωση_ml': 'Κατανάλωση (ml)', 'Παραχθέντα_Τεμάχια': 'Παραχθέντα Τεμάχια'}, inplace=True)
                                else:
                                    df_breakdown = pd.DataFrame([{"Κοκτέιλ": "Ιστορικό", "Παραχθέντα Τεμάχια": df_ing_history['pieces'].sum(), "Κατανάλωση (ml)": df_ing_history['total_ml'].sum()}])
                                    
                                df_breakdown = df_breakdown[df_breakdown['Κατανάλωση (ml)'] > 0]
                                total_ml_used = df_breakdown['Κατανάλωση (ml)'].sum()
                                
                                if total_ml_used > 0:
                                    total_bottles = total_ml_used / bottle_vol if bottle_vol > 0 else 0
                                    total_cost = total_ml_used * price_per_ml
                                    
                                    df_breakdown['Αναλογία (%)'] = (df_breakdown['Κατανάλωση (ml)'] / total_ml_used) * 100
                                    df_breakdown['Κόστος (€)'] = df_breakdown['Κατανάλωση (ml)'] * price_per_ml
                                    
                                    # --- 1. Δημιουργία HTML Πίνακα για το συγκεκριμένο υλικό ---
                                    table_html = "<table><thead><tr><th>Κοκτέιλ</th><th style='text-align:center;'>Τεμάχια</th><th style='text-align:center;'>Κατανάλωση (ml)</th><th style='text-align:center;'>Φιάλες</th><th style='text-align:center;'>Αναλογία</th><th style='text-align:center;'>Κόστος</th></tr></thead><tbody>"
                                    
                                    for _, row in df_breakdown.sort_values(by='Κατανάλωση (ml)', ascending=False).iterrows():
                                        bottles_str = f"{(row['Κατανάλωση (ml)'] / bottle_vol):.1f}" if bottle_vol > 0 else "-"
                                        table_html += f"<tr><td>{row['Κοκτέιλ']}</td><td style='text-align:center;'>{row['Παραχθέντα Τεμάχια']:g}</td><td style='text-align:center;'>{row['Κατανάλωση (ml)']:,.1f}</td><td style='text-align:center;'>{bottles_str}</td><td style='text-align:center;'>{row['Αναλογία (%)']:.1f}%</td><td style='text-align:center;'>{row['Κόστος (€)']:.2f} €</td></tr>"
                                    table_html += "</tbody></table>"
                                    
                                    # --- 2. Δημιουργία Plotly Γραφήματος (Πίτα) και μετατροπή σε HTML ---
                                    fig_pie = px.pie(df_breakdown, values='Κατανάλωση (ml)', names='Κοκτέιλ', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                                    fig_pie.update_traces(textinfo='percent+label')
                                    fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=350, showlegend=False)
                                    
                                    # include_plotlyjs=False επειδή το φορτώσαμε ήδη μια φορά στο Head (κάνει το αρχείο πολύ πιο ελαφρύ!)
                                    graph_div = fig_pie.to_html(full_html=False, include_plotlyjs=False)
                                    
                                    # --- 3. Σύνθεση της "Κάρτας" του υλικού ---
                                    html_report += f"""
                                    <div class="material-card">
                                        <h2 class="material-title">🍾 {ing}</h2>
                                        <div class="metrics">
                                            <div class="metric-box">
                                                <div style="color: #666; font-size: 13px; text-transform: uppercase;">Συνολικά ml</div>
                                                <div class="metric-value">{total_ml_used:,.1f}</div>
                                            </div>
                                            <div class="metric-box">
                                                <div style="color: #666; font-size: 13px; text-transform: uppercase;">Φιάλες</div>
                                                <div class="metric-value">{total_bottles:.2f}</div>
                                            </div>
                                            <div class="metric-box">
                                                <div style="color: #666; font-size: 13px; text-transform: uppercase;">Συνολικό Κόστος</div>
                                                <div class="metric-value">{total_cost:.2f} €</div>
                                            </div>
                                        </div>
                                        {table_html}
                                        <div class="chart-container">
                                            {graph_div}
                                        </div>
                                    </div>
                                    """
                                else:
                                    html_report += f"<div class='material-card'><h2 class='material-title'>🍾 {ing}</h2><p style='color: #666; font-style: italic;'>Δεν καταγράφηκε κατανάλωση (0 ml).</p></div>"
                            else:
                                html_report += f"<div class='material-card'><h2 class='material-title'>🍾 {ing}</h2><p style='color: #666; font-style: italic;'>Δεν υπάρχει καταγεγραμμένο ιστορικό για αυτό το υλικό.</p></div>"
                                
                        # Κλείσιμο HTML
                        html_report += "</div></body></html>"
                        
                        # Αποθήκευση του report στη μνήμη του Streamlit
                        st.session_state['material_export_html_data'] = html_report
                        
                # Εμφάνιση του κουμπιού λήψης αν το Report είναι έτοιμο
                if 'material_export_html_data' in st.session_state:
                    st.success("✅ Το Διαδραστικό Report είναι έτοιμο για λήψη!")
                    st.download_button(
                        label="📥 Κατέβασμα Full Report (HTML)",
                        data=st.session_state['material_export_html_data'],
                        file_name=f"CABCLUB_Materials_Report_{datetime.now().strftime('%d%m%Y')}.html",
                        mime="text/html",
                        type="primary",
                        use_container_width=True
                    )


# --- 6. ΕΜΠΟΡΙΚΗ ΠΟΛΙΤΙΚΗ (COMPLETE PRO VERSION WITH MULTISELECT, NET PROFIT & HTML EXPORT) ---
# --- 💰 ΚΟΣΤΟΛΟΓΙΟ & ΣΤΑΘΕΡΑ ΕΞΟΔΑ ---
elif page == "💰 Κοστολόγιο & Σταθερά Έξοδα":
    st.header("💰 Κοστολόγιο")
    st.caption(
        "Χειροκίνητο κόστος ανά κοκτέιλ: Εργατικά (ανά κοκτέιλ) + Κόστος Συσκευασίας (ίδιο για όλα) = Σύνολο. "
        "Το σύνολο αυτό ενημερώνει αυτόματα ΟΛΕΣ τις καρτέλες (Ανάλυση, Εμπορική Πολιτική, Dashboard, Πελατολόγιο, Lot Παραγωγής, κ.λπ.) όταν είναι ενεργό."
    )

    try:
        _t1 = supabase.table("cost_settings").select("id, operational_cost, active").limit(1).execute()
        _t2 = supabase.table("cocktail_costs").select("cocktail_name, industrial_cost").limit(1).execute()
        tables_exist = True
    except Exception as _e:
        tables_exist = False
        _schema_error = str(_e)

    if not tables_exist:
        st.error("⚠️ Ο πίνακας `cost_settings` υπάρχει αλλά του λείπουν οι νέες στήλες (`active`, `operational_cost`), ή/και λείπει ο πίνακας `cocktail_costs`. Τρέξε το SQL παρακάτω μία φορά — είναι ασφαλές ακόμα κι αν το ξανατρέξεις:")
        st.code(
            "alter table cost_settings\n"
            "  add column if not exists operational_cost numeric not null default 0;\n"
            "alter table cost_settings\n"
            "  add column if not exists active boolean not null default false;\n\n"
            "insert into cost_settings (id, operational_cost, active)\n"
            "values (1, 0, false)\n"
            "on conflict (id) do nothing;\n\n"
            "create table if not exists cocktail_costs (\n"
            "  cocktail_name text primary key,\n"
            "  industrial_cost numeric not null default 0,\n"
            "  updated_at timestamptz not null default now()\n"
            ");",
            language="sql"
        )
        with st.expander("🔍 Τεχνική λεπτομέρεια σφάλματος"):
            st.caption(_schema_error)
    else:
        s = load_cost_settings() or {}
        cc_map = load_cocktail_costs()

        # --- 📥 ΓΡΗΓΟΡΗ ΕΙΣΑΓΩΓΗ ΚΟΣΤΟΥΣ ΑΠΟ EXCEL ---
        st.subheader("📥 Γρήγορη Εισαγωγή Κόστους από Excel")
        st.caption(
            "Ανέβασε αρχείο Excel με στήλες: COCKTAILS, A. ΥΛΙΚΑ, B. ΣΥΣΚΕΥΑΣΙΕΣ, Γ. ΕΡΓΑΤΙΚΑ — "
            "θα γεμίσει αυτόματα τα Εργατικά (Υλικά+Εργατικά, ανά κοκτέιλ) και το "
            "Κόστος Συσκευασίας (ίδιο για όλα) χωρίς να χρειάζεται να τα πληκτρολογήσεις ένα-ένα."
        )
        uploaded_cost_file = st.file_uploader("Επίλεξε αρχείο .xlsx", type=["xlsx"], key="cost_excel_uploader")
        if uploaded_cost_file is not None:
            try:
                xls_cost = pd.ExcelFile(uploaded_cost_file)
                sheet_to_use = "ΠΡΟΤΑΣΗ" if "ΠΡΟΤΑΣΗ" in xls_cost.sheet_names else xls_cost.sheet_names[0]

                # Βρίσκουμε αυτόματα ΠΟΙΑ γραμμή έχει το "COCKTAILS" header — ανθεκτικό σε
                # μικρές αλλαγές διάταξης (extra κενές γραμμές, τίτλοι σεναρίου, κ.λπ.)
                raw_preview = pd.read_excel(xls_cost, sheet_name=sheet_to_use, header=None, nrows=15)
                header_row_idx = None
                for idx, row in raw_preview.iterrows():
                    if row.apply(lambda v: str(v).strip()).eq("COCKTAILS").any():
                        header_row_idx = idx
                        break

                if header_row_idx is None:
                    st.error("Δεν βρέθηκε στήλη «COCKTAILS» στις πρώτες γραμμές του αρχείου/φύλλου. Έλεγξε ότι είναι το σωστό sheet.")
                else:
                    header_vals = [str(v).strip() for v in raw_preview.iloc[header_row_idx].tolist()]
                    col_map = {}
                    for i, h in enumerate(header_vals):
                        if h == "COCKTAILS": col_map[i] = "Cocktail"
                        elif h.startswith("A. ΥΛΙΚΑ") or h.startswith("Α. ΥΛΙΚΑ"): col_map[i] = "Ylika"
                        elif h.startswith("B. ΣΥΣΚΕΥΑΣΙΕΣ") or h.startswith("Β. ΣΥΣΚΕΥΑΣΙΕΣ"): col_map[i] = "Syskevasies"
                        elif h.startswith("Γ. ΕΡΓΑΤΙΚΑ"): col_map[i] = "Ergatika"

                    if not {"Cocktail", "Ylika", "Ergatika"}.issubset(set(col_map.values())):
                        st.error(f"Δεν βρέθηκαν όλες οι απαραίτητες στήλες (COCKTAILS, A. ΥΛΙΚΑ, Γ. ΕΡΓΑΤΙΚΑ). Βρέθηκαν: {list(col_map.values())}")
                    else:
                        df_import = pd.read_excel(xls_cost, sheet_name=sheet_to_use, header=None, skiprows=header_row_idx + 1)
                        keep_idx = list(col_map.keys())
                        df_import = df_import[keep_idx]
                        df_import.columns = [col_map[i] for i in keep_idx]
                        df_import = df_import.dropna(subset=["Cocktail"]).reset_index(drop=True)
                        df_import["Cocktail"] = df_import["Cocktail"].astype(str).str.strip()
                        df_import["Ylika"] = pd.to_numeric(df_import["Ylika"], errors="coerce").fillna(0)
                        df_import["Ergatika"] = pd.to_numeric(df_import["Ergatika"], errors="coerce").fillna(0)

                        if "Syskevasies" in df_import.columns:
                            df_import["Syskevasies"] = pd.to_numeric(df_import["Syskevasies"], errors="coerce").fillna(0)
                            _mode = df_import["Syskevasies"].mode()
                            detected_packaging = float(_mode.iloc[0]) if not _mode.empty else 0.0
                        else:
                            detected_packaging = 0.0

                        df_import["Βιομηχανικό (Υλικά+Εργατικά)"] = df_import["Ylika"] + df_import["Ergatika"]

                        # Αντιστοίχιση με τα ονόματα συνταγών της εφαρμογής (χωρίς διάκριση πεζών/κεφαλαίων ή κενών άκρων)
                        app_names_norm = {n.strip().upper(): n for n in (df_rec["Ονομα"].unique() if not df_rec.empty else [])}
                        df_import["Αντιστοίχιση"] = df_import["Cocktail"].apply(lambda x: app_names_norm.get(x.strip().upper()))
                        matched = df_import[df_import["Αντιστοίχιση"].notna()]
                        unmatched = df_import[df_import["Αντιστοίχιση"].isna()]

                        st.success(f"✅ Βρέθηκαν {len(df_import)} κοκτέιλ στο αρχείο — {len(matched)} ταιριάζουν με συνταγές της εφαρμογής.")
                        st.info(f"📦 Ανιχνεύθηκε κόστος συσκευασίας: **{detected_packaging:.4f}€** (θα μπει ως Κόστος Συσκευασίας, ίδιο για όλα).")
                        st.dataframe(
                            matched[["Cocktail", "Ylika", "Ergatika", "Βιομηχανικό (Υλικά+Εργατικά)"]].rename(columns={"Cocktail": "Κοκτέιλ (Excel)"}),
                            use_container_width=True, hide_index=True
                        )
                        if not unmatched.empty:
                            with st.expander(f"⚠️ {len(unmatched)} κοκτέιλ του αρχείου ΔΕΝ βρέθηκαν στις συνταγές της εφαρμογής (δεν θα εισαχθούν)"):
                                st.dataframe(unmatched[["Cocktail"]], use_container_width=True, hide_index=True)

                        if st.button("📥 Εφαρμογή Εισαγωγής", type="primary"):
                            try:
                                updates = [
                                    {"cocktail_name": r["Αντιστοίχιση"], "industrial_cost": round(float(r["Βιομηχανικό (Υλικά+Εργατικά)"]), 4)}
                                    for _, r in matched.iterrows()
                                ]
                                if updates:
                                    supabase.table("cocktail_costs").upsert(updates, on_conflict="cocktail_name").execute()
                                supabase.table("cost_settings").upsert({
                                    "id": 1,
                                    "operational_cost": round(detected_packaging, 4),
                                    "active": bool(s.get("active", False)),
                                    "be_rent": float(s.get("be_rent", 0.0)), "be_labor": float(s.get("be_labor", 0.0)),
                                    "be_insurance": float(s.get("be_insurance", 0.0)), "be_admin": float(s.get("be_admin", 0.0)),
                                    "be_utilities": float(s.get("be_utilities", 0.0)), "be_other": float(s.get("be_other", 0.0)),
                                }).execute()
                                st.cache_data.clear()
                                st.success(f"✅ Εισήχθησαν {len(updates)} κοκτέιλ! Κόστος Συσκευασίας: {detected_packaging:.4f}€.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Σφάλμα εισαγωγής: {e}")
            except Exception as e:
                st.error(f"Σφάλμα ανάγνωσης αρχείου: {e}")

        st.divider()

        # --- 1. ΔΙΑΚΟΠΤΗΣ ΕΝΕΡΓΟΠΟΙΗΣΗΣ ---
        st.subheader("1️⃣ Ενεργοποίηση Σεναρίου Χειροκίνητου Κόστους")
        is_active_now = bool(s.get("active", False))
        toggle_col1, toggle_col2 = st.columns([1, 3])
        with toggle_col1:
            new_active = st.toggle("✅ Ενεργό" if is_active_now else "⛔ Ανενεργό", value=is_active_now, key="cost_scenario_toggle")
        with toggle_col2:
            if new_active:
                st.success("Ενεργό: χρησιμοποιείται το χειροκίνητο κόστος (Εργατικά + Κόστος Συσκευασίας) ανά κοκτέιλ, παντού στην εφαρμογή.")
            else:
                st.info("Ανενεργό: η εφαρμογή χρησιμοποιεί το παλιό, προεπιλεγμένο κόστος 0,22€ (+ αυτόματο κόστος υλικών) όπως πριν.")

        if new_active != is_active_now:
            try:
                supabase.table("cost_settings").upsert({
                    "id": 1, "operational_cost": float(s.get("operational_cost") or 0.0), "active": new_active
                }).execute()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Σφάλμα αποθήκευσης: {e}")

        st.divider()

        # --- 2. ΛΕΙΤΟΥΡΓΙΚΟ ΚΟΣΤΟΣ (ΚΟΙΝΟ ΓΙΑ ΟΛΑ) ---
        st.subheader("2️⃣ Κόστος Συσκευασίας (ίδιο για όλα τα κοκτέιλ)")
        op_cost = st.number_input(
            "Λειτουργικό κόστος ανά τεμάχιο (€):",
            min_value=0.0, value=float(s.get("operational_cost", 0.0)), step=0.01, format="%.4f",
            key="operational_cost_input"
        )
        if st.button("💾 Αποθήκευση Λειτουργικού Κόστους"):
            try:
                supabase.table("cost_settings").upsert({
                    "id": 1, "operational_cost": op_cost, "active": new_active
                }).execute()
                st.cache_data.clear()
                st.success("✅ Αποθηκεύτηκε!")
                st.rerun()
            except Exception as e:
                st.error(f"Σφάλμα αποθήκευσης: {e}")

        st.divider()

        # --- 3. ΠΙΝΑΚΑΣ ΒΙΟΜΗΧΑΝΙΚΟΥ ΚΟΣΤΟΥΣ ΑΝΑ ΚΟΚΤΕΪΛ ---
        st.subheader("3️⃣ Εργατικά ανά Κοκτέιλ")
        st.caption("Καταχώρησε το κόστος παρασκευής για κάθε κοκτέιλ. Το «Σύνολο» υπολογίζεται αυτόματα (Εργατικά + Κόστος Συσκευασίας).")
        st.warning("⚠️ Αν χρειάζεται να αλλάξεις και το Κόστος Συσκευασίας (Βήμα 2), αποθήκευσέ το **πρώτα** και μετά επεξεργάσου τον παρακάτω πίνακα — αλλιώς μπορεί να χαθούν μη-αποθηκευμένες αλλαγές στον πίνακα.")

        if df_rec.empty:
            st.warning("Δεν βρέθηκαν συνταγές.")
        else:
            table_rows = []
            for cname in sorted(df_rec["Ονομα"].unique()):
                industrial = float(cc_map.get(cname, 0.0))
                table_rows.append({
                    "Κοκτέιλ": cname,
                    "Εργατικά (€)": industrial,
                    "Κόστος Συσκευασίας (€)": op_cost,
                    "Σύνολο (€)": round(industrial + op_cost, 4)
                })
            df_cost_table = pd.DataFrame(table_rows)

            edited_df = st.data_editor(
                df_cost_table,
                column_config={
                    "Κοκτέιλ": st.column_config.TextColumn(disabled=True),
                    "Εργατικά (€)": st.column_config.NumberColumn(min_value=0.0, step=0.01, format="%.4f"),
                    "Κόστος Συσκευασίας (€)": st.column_config.NumberColumn(disabled=True, format="%.4f", help="Αλλάζει μόνο από το πεδίο πιο πάνω — ίδιο για όλα τα κοκτέιλ."),
                    "Σύνολο (€)": st.column_config.NumberColumn(disabled=True, format="%.4f"),
                },
                hide_index=True,
                use_container_width=True,
                key="cost_editor_industrial"  # 🔧 FIX: σταθερό key (πριν βασιζόταν στον αριθμό γραμμών — riskάριζε reset σε αλλαγή πλήθους κοκτέιλ)
            )

            if st.button("💾 Αποθήκευση Εργατικών", type="primary"):
                try:
                    updates = []
                    for _, r in edited_df.iterrows():
                        updates.append({
                            "cocktail_name": r["Κοκτέιλ"],
                            "industrial_cost": float(r["Εργατικά (€)"])
                        })
                    if updates:
                        supabase.table("cocktail_costs").upsert(updates, on_conflict="cocktail_name").execute()
                    st.cache_data.clear()
                    st.success(f"✅ Αποθηκεύτηκαν {len(updates)} κοκτέιλ!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Σφάλμα αποθήκευσης: {e}")

# --- 📐 MARKUP & MARGIN: CABCLUB → ΑΝΤΙΠΡΟΣΩΠΟΣ → ΠΕΛΑΤΗΣ ---
elif page == "📐 Markup & Margin":
    st.header("📐 Markup & Margin ανά Επίπεδο Διανομής")
    st.caption(
        "Επίπεδο 1: Cabclub → Αντιπρόσωπος (χονδρική)  |  Επίπεδο 2: Αντιπρόσωπος → Τελικός Πελάτης (λιανική). "
        "Δείχνει τους τρέχοντες δείκτες, και σου επιτρέπει να τρέξεις σενάριο βάζοντας το επιθυμητό markup/margin."
    )

    if df_rec.empty:
        st.warning("Δεν βρέθηκαν συνταγές.")
    else:
        choice = st.selectbox("🍹 Επιλέξτε Κοκτέιλ:", sorted(df_rec["Ονομα"].unique()), key="mm_choice")
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]

        # --- Κόστος (ίδια λογική με Ανάλυση/Εμπορική Πολιτική) ---
        raw_cost = 0.0
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
            ml = float(r.get(f"ML{i}", 0))
            if ing_n not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty:
                    raw_cost += ml * float(match.iloc[0]["Τιμή/ml"])
        my_cost = get_unit_cost_for_cocktail(choice, raw_cost)

        retail_price = float(r.get("Τιμή Καταλόγου", 0.0))
        agent_price = retail_price * 0.74  # ίδια σύμβαση με την Εμπορική Πολιτική/Αντικατάσταση (τιμή αντιπροσώπου)

        def _markup(cost, price):
            return round((price - cost) / cost * 100, 2) if cost > 0 else 0.0

        def _margin(cost, price):
            return round((price - cost) / price * 100, 2) if price > 0 else 0.0

        markup1, margin1 = _markup(my_cost, agent_price), _margin(my_cost, agent_price)
        markup2, margin2 = _markup(agent_price, retail_price), _margin(agent_price, retail_price)
        markup3, margin3 = _markup(my_cost, retail_price), _margin(my_cost, retail_price)

        st.divider()
        st.subheader("📊 Τρέχοντες Δείκτες")

        st.markdown("**1️⃣ Cabclub → Αντιπρόσωπος**")
        l1c1, l1c2, l1c3, l1c4 = st.columns(4)
        l1c1.metric("Κόστος μου", f"{my_cost:.2f} €")
        l1c2.metric("Τιμή Αντιπροσώπου", f"{agent_price:.2f} €")
        l1c3.metric("Markup", f"{markup1:.1f} %", help="(Τιμή - Κόστος) / Κόστος")
        l1c4.metric("Margin", f"{margin1:.1f} %", help="(Τιμή - Κόστος) / Τιμή")

        st.markdown("**2️⃣ Αντιπρόσωπος → Τελικός Πελάτης**")
        l2c1, l2c2, l2c3, l2c4 = st.columns(4)
        l2c1.metric("Κόστος Αντιπρ. (=τιμή αγοράς)", f"{agent_price:.2f} €")
        l2c2.metric("Τιμή Λιανικής", f"{retail_price:.2f} €")
        l2c3.metric("Markup", f"{markup2:.1f} %", help="(Τιμή - Κόστος) / Κόστος")
        l2c4.metric("Margin", f"{margin2:.1f} %", help="(Τιμή - Κόστος) / Τιμή")

        st.markdown("**3️⃣ Cabclub → Τελικός Πελάτης (Απευθείας Λιανική)**")
        st.caption("Πουλάς εσύ ο ίδιος απευθείας στον τελικό πελάτη, χωρίς αντιπρόσωπο — στην τιμή λιανικής.")
        l3c1, l3c2, l3c3, l3c4 = st.columns(4)
        l3c1.metric("Κόστος μου", f"{my_cost:.2f} €")
        l3c2.metric("Τιμή Λιανικής", f"{retail_price:.2f} €")
        l3c3.metric("Markup", f"{markup3:.1f} %", help="(Τιμή - Κόστος) / Κόστος")
        l3c4.metric("Margin", f"{margin3:.1f} %", help="(Τιμή - Κόστος) / Τιμή")

        st.divider()
        st.subheader("🎯 Σενάριο: Ορισμός Επιθυμητού Markup ή Margin")
        st.caption("Το markup και το margin είναι μαθηματικά συνδεδεμένα — δεν μπορείς να ορίσεις και τα δύο ανεξάρτητα για την ίδια τιμή. Διάλεξε ποιο θες να οδηγεί τον υπολογισμό.")

        scenario_mode = st.radio("Τι θα ορίσεις;", ["Markup %", "Margin %"], horizontal=True, key="mm_scenario_mode")

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown("**Επίπεδο 1: Cabclub → Αντιπρόσωπος**")
            default1 = markup1 if scenario_mode == "Markup %" else margin1
            desired1 = st.number_input(f"Επιθυμητό {scenario_mode}:", value=float(default1), step=0.5, format="%.2f", key="mm_desired1")
        with sc2:
            st.markdown("**Επίπεδο 2: Αντιπρόσωπος → Πελάτης**")
            default2 = markup2 if scenario_mode == "Markup %" else margin2
            desired2 = st.number_input(f"Επιθυμητό {scenario_mode}:", value=float(default2), step=0.5, format="%.2f", key="mm_desired2")
        with sc3:
            st.markdown("**Επίπεδο 3: Cabclub → Πελάτης (Απευθείας)**")
            default3 = markup3 if scenario_mode == "Markup %" else margin3
            desired3 = st.number_input(f"Επιθυμητό {scenario_mode}:", value=float(default3), step=0.5, format="%.2f", key="mm_desired3")

        # --- Υπολογισμός νέων τιμών από τα επιθυμητά markup/margin ---
        if scenario_mode == "Markup %":
            new_agent_price = my_cost * (1 + desired1 / 100)
            new_retail_price = new_agent_price * (1 + desired2 / 100)
            new_direct_price = my_cost * (1 + desired3 / 100)
        else:  # Margin %
            new_agent_price = my_cost / (1 - desired1 / 100) if desired1 < 100 else float('inf')
            new_retail_price = new_agent_price / (1 - desired2 / 100) if desired2 < 100 and new_agent_price != float('inf') else float('inf')
            new_direct_price = my_cost / (1 - desired3 / 100) if desired3 < 100 else float('inf')

        new_markup1, new_margin1 = _markup(my_cost, new_agent_price), _margin(my_cost, new_agent_price)
        new_markup2, new_margin2 = _markup(new_agent_price, new_retail_price), _margin(new_agent_price, new_retail_price)
        new_markup3, new_margin3 = _markup(my_cost, new_direct_price), _margin(my_cost, new_direct_price)

        st.markdown("### 💡 Αποτέλεσμα Σεναρίου")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            if new_agent_price == float('inf'):
                st.error("⚠️ Το επιθυμητό margin (100%+) δεν είναι εφικτό μαθηματικά.")
            else:
                delta_agent = new_agent_price - agent_price
                delta_agent_pct = (delta_agent / agent_price * 100) if agent_price > 0 else 0
                st.metric("Νέα Τιμή Αντιπροσώπου", f"{new_agent_price:.2f} €", delta=f"{delta_agent:+.2f} € ({delta_agent_pct:+.1f}%)")
                st.caption(f"Markup: {markup1:.1f}% → **{new_markup1:.1f}%**  |  Margin: {margin1:.1f}% → **{new_margin1:.1f}%**")
        with rc2:
            if new_retail_price == float('inf'):
                st.error("⚠️ Το επιθυμητό margin (100%+) δεν είναι εφικτό μαθηματικά.")
            else:
                delta_retail = new_retail_price - retail_price
                delta_retail_pct = (delta_retail / retail_price * 100) if retail_price > 0 else 0
                st.metric("Νέα Τιμή Λιανικής", f"{new_retail_price:.2f} €", delta=f"{delta_retail:+.2f} € ({delta_retail_pct:+.1f}%)")
                st.caption(f"Markup: {markup2:.1f}% → **{new_markup2:.1f}%**  |  Margin: {margin2:.1f}% → **{new_margin2:.1f}%**")
        with rc3:
            if new_direct_price == float('inf'):
                st.error("⚠️ Το επιθυμητό margin (100%+) δεν είναι εφικτό μαθηματικά.")
            else:
                delta_direct = new_direct_price - retail_price
                delta_direct_pct = (delta_direct / retail_price * 100) if retail_price > 0 else 0
                st.metric("Νέα Τιμή Απευθείας Πώλησης", f"{new_direct_price:.2f} €", delta=f"{delta_direct:+.2f} € ({delta_direct_pct:+.1f}%)")
                st.caption(f"Markup: {markup3:.1f}% → **{new_markup3:.1f}%**  |  Margin: {margin3:.1f}% → **{new_margin3:.1f}%**")

        if new_agent_price != float('inf') and new_retail_price != float('inf'):
            total_change_text = (
                f"Συνολική αλλαγή τιμής λιανικής από σήμερα: {(new_retail_price - retail_price):+.2f} EUR "
                f"({((new_retail_price - retail_price) / retail_price * 100 if retail_price > 0 else 0):+.1f}%)"
            )
            st.info(f"👉 {total_change_text}")
        else:
            total_change_text = None

        # =====================================================================
        # 🌐 ΕΠΙΔΡΑΣΗ ΣΕΝΑΡΙΟΥ ΣΕ ΟΛΑ ΤΑ ΚΟΚΤΕΪΛ (βάσει πραγματικών πωλήσεων)
        # =====================================================================
        st.divider()
        st.subheader("🌐 Επίδραση Σεναρίου σε ΟΛΑ τα Κοκτέιλ")
        st.caption(
            f"Εφαρμόζοντας το ίδιο επιθυμητό {scenario_mode} ({desired1:.1f}% / {desired2:.1f}% / {desired3:.1f}%) "
            f"σε **κάθε** κοκτέιλ ξεχωριστά, με βάση το δικό του κόστος — όχι μόνο στο «{choice}»."
        )

        # --- 1. Υπολογισμός νέων τιμών για ΟΛΑ τα κοκτέιλ ---
        all_scenario_rows = []
        cocktail_new_prices = {}  # {cocktail_name: {"retail_old":.., "retail_new":.., "agent_old":.., "agent_new":..}}
        for _, r_all in df_rec.iterrows():
            c_name_all = r_all["Ονομα"]
            raw_cost_all = 0.0
            for i in range(1, 14):
                ing_n_all = str(r_all.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                ml_all = float(r_all.get(f"ML{i}", 0) or 0)
                if ing_n_all not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml_all > 0:
                    match_all = df_ing[df_ing["Name"] == ing_n_all]
                    if not match_all.empty:
                        raw_cost_all += ml_all * float(match_all.iloc[0]["Τιμή/ml"])
            my_cost_all = get_unit_cost_for_cocktail(c_name_all, raw_cost_all)
            retail_old_all = float(r_all.get("Τιμή Καταλόγου", 0.0))
            agent_old_all = retail_old_all * 0.74

            if scenario_mode == "Markup %":
                agent_new_all = my_cost_all * (1 + desired1 / 100)
                retail_new_all = agent_new_all * (1 + desired2 / 100)
                direct_new_all = my_cost_all * (1 + desired3 / 100)
            else:
                agent_new_all = my_cost_all / (1 - desired1 / 100) if desired1 < 100 else float('inf')
                retail_new_all = agent_new_all / (1 - desired2 / 100) if desired2 < 100 and agent_new_all != float('inf') else float('inf')
                direct_new_all = my_cost_all / (1 - desired3 / 100) if desired3 < 100 else float('inf')

            cocktail_new_prices[c_name_all] = {
                "retail_old": retail_old_all, "retail_new": retail_new_all,
                "agent_old": agent_old_all, "agent_new": agent_new_all,
                "direct_new": direct_new_all,
                "my_cost": my_cost_all,
            }
            all_scenario_rows.append({
                "Κοκτέιλ": c_name_all,
                "Κόστος (€)": round(my_cost_all, 4),
                "Τιμή Αντιπρ. Τώρα (€)": round(agent_old_all, 2),
                "Νέα Τιμή Αντιπρ. (€)": round(agent_new_all, 2) if agent_new_all != float('inf') else None,
                "Τιμή Λιανικής Τώρα (€)": round(retail_old_all, 2),
                "Νέα Τιμή Λιανικής (€)": round(retail_new_all, 2) if retail_new_all != float('inf') else None,
                "Νέα Τιμή Απευθείας (€)": round(direct_new_all, 2) if direct_new_all != float('inf') else None,
            })

        df_all_scenario = pd.DataFrame(all_scenario_rows)

        # 🎨 ΟΠΤΙΚΗ ΣΗΜΑΝΣΗ: κόκκινο αν η νέα τιμή ανεβαίνει, πράσινο αν κατεβαίνει (χρώμα + βελάκι)
        _price_pairs = [
            ("Τιμή Αντιπρ. Τώρα (€)", "Νέα Τιμή Αντιπρ. (€)"),
            ("Τιμή Λιανικής Τώρα (€)", "Νέα Τιμή Λιανικής (€)"),
        ]

        def _add_arrow(row):
            row = row.copy()
            for old_col, new_col in _price_pairs:
                old_v, new_v = row[old_col], row[new_col]
                if pd.notna(old_v) and pd.notna(new_v):
                    if new_v > old_v:
                        row[new_col] = f"↑ {new_v:.2f}"
                    elif new_v < old_v:
                        row[new_col] = f"↓ {new_v:.2f}"
                    else:
                        row[new_col] = f"= {new_v:.2f}"
            return row

        def _highlight_price_change(row):
            styles = [''] * len(row)
            for old_col, new_col in _price_pairs:
                old_v = df_all_scenario.loc[row.name, old_col]
                new_v = df_all_scenario.loc[row.name, new_col]
                idx = row.index.get_loc(new_col)
                if pd.notna(old_v) and pd.notna(new_v):
                    if new_v > old_v:
                        styles[idx] = 'background-color: #4d1f1f; color: #ff6b6b; font-weight: 600;'
                    elif new_v < old_v:
                        styles[idx] = 'background-color: #1f4d24; color: #6fd67f; font-weight: 600;'
            return styles

        df_display = df_all_scenario.apply(_add_arrow, axis=1)
        styled_scenario = df_display.style.apply(_highlight_price_change, axis=1)
        st.dataframe(styled_scenario, use_container_width=True, hide_index=True)
        st.caption("↑ κόκκινο = η τιμή ανεβαίνει  |  ↓ πράσινο = η τιμή κατεβαίνει  |  = αμετάβλητη")

        # --- 2. Φόρτωση πραγματικού ιστορικού πωλήσεων (για σταθμισμένο μέσο όρο + P&L) ---
        try:
            res_mm_hist = supabase.table("production_log").select(
                "cocktail_name, customer, pieces, free_pieces, discounted_pieces, discount_pct, applied_cost, lot_cocktail, prod_time, prod_date"
            ).execute()
            res_mm_cust = supabase.table("customers").select("name, discount").execute()
            df_mm_cust = pd.DataFrame(res_mm_cust.data) if res_mm_cust.data else pd.DataFrame(columns=["name", "discount"])
        except Exception as e:
            res_mm_hist = None
            st.error(f"Σφάλμα φόρτωσης ιστορικού πωλήσεων: {e}")

        if res_mm_hist and res_mm_hist.data:
            df_mm_hist = pd.DataFrame(res_mm_hist.data).drop_duplicates(subset=["prod_date", "prod_time", "customer", "cocktail_name", "lot_cocktail"])
            df_mm_hist["pieces"] = pd.to_numeric(df_mm_hist["pieces"], errors="coerce").fillna(0)
            df_mm_hist["free_pieces"] = pd.to_numeric(df_mm_hist.get("free_pieces", 0), errors="coerce").fillna(0)
            df_mm_hist["applied_cost"] = pd.to_numeric(df_mm_hist.get("applied_cost", 0), errors="coerce").fillna(0)
            cust_disc_mm = dict(zip(df_mm_cust["name"], pd.to_numeric(df_mm_cust.get("discount", 0), errors="coerce").fillna(0))) if not df_mm_cust.empty else {}

            df_mm_hist["global_discount"] = pd.to_numeric(df_mm_hist["customer"].map(cust_disc_mm), errors="coerce").fillna(0)
            df_mm_hist["s_pcs"] = pd.to_numeric(df_mm_hist.get("discounted_pieces", 0), errors="coerce").fillna(0)
            df_mm_hist["s_pct"] = pd.to_numeric(df_mm_hist.get("discount_pct", 0), errors="coerce").fillna(0)
            df_mm_hist["s_pcs"] = df_mm_hist.apply(lambda r: min(r["s_pcs"], max(0, r["pieces"] - r["free_pieces"])), axis=1)
            df_mm_hist["normal_pcs"] = df_mm_hist["pieces"] - df_mm_hist["free_pieces"] - df_mm_hist["s_pcs"]
            df_mm_hist["paid_pieces"] = df_mm_hist["normal_pcs"] + df_mm_hist["s_pcs"]

            # Τιμή καταλόγου ΤΩΡΑ και ΜΕΤΑ το σενάριο, ανά κοκτέιλ
            df_mm_hist["retail_old"] = df_mm_hist["cocktail_name"].map(lambda c: cocktail_new_prices.get(c, {}).get("retail_old", 0.0))
            df_mm_hist["retail_new"] = df_mm_hist["cocktail_name"].map(lambda c: cocktail_new_prices.get(c, {}).get("retail_new", 0.0))
            df_mm_hist["retail_new"] = pd.to_numeric(df_mm_hist["retail_new"], errors="coerce").fillna(0)
            df_mm_hist["direct_new"] = df_mm_hist["cocktail_name"].map(lambda c: cocktail_new_prices.get(c, {}).get("direct_new", 0.0))
            df_mm_hist["direct_new"] = pd.to_numeric(df_mm_hist["direct_new"], errors="coerce").fillna(0)

            # ΠΡΑΓΜΑΤΙΚΟΣ τζίρος (τώρα): ίδια μεθοδολογία με Dashboard/Έσοδα-Έξοδα
            df_mm_hist["price_after_global_old"] = df_mm_hist["retail_old"] * (1 - (df_mm_hist["global_discount"] / 100))
            df_mm_hist["rev_normal_old"] = df_mm_hist["normal_pcs"] * df_mm_hist["price_after_global_old"]
            df_mm_hist["rev_special_old"] = df_mm_hist["s_pcs"] * df_mm_hist["price_after_global_old"] * (1 - (df_mm_hist["s_pct"] / 100))
            df_mm_hist["revenue_actual"] = (df_mm_hist["rev_normal_old"] + df_mm_hist["rev_special_old"]).clip(lower=0)

            # --- 🆕 Επιλογή καναλιού για το ΥΠΟΘΕΤΙΚΟ σενάριο ---
            st.markdown("#### 🔀 Κανάλι Πώλησης για το Σενάριο")
            channel_choice = st.radio(
                "Οι ΙΔΙΕΣ ιστορικές πωλήσεις (τεμάχια) θα γίνονταν:",
                ["🤝 Μέσω Αντιπροσώπου (με τις σημερινές εκπτώσεις πελατών)", "🎯 Απευθείας στον Τελικό Πελάτη (χωρίς αντιπρόσωπο)"],
                key="mm_pl_channel"
            )
            _direct_mode = channel_choice.startswith("🎯")

            if _direct_mode:
                st.caption("⚠️ Στο απευθείας κανάλι δεν εφαρμόζεται καμία έκπτωση πελάτη/αντιπροσώπου — κάθε τεμάχιο τιμολογείται στην πλήρη «Τιμή Απευθείας Πώλησης».")
                # Καμία έκπτωση πελάτη/ειδική έκπτωση — πουλάς απευθείας, χωρίς τη μεσολάβηση αντιπροσώπου.
                df_mm_hist["revenue_scenario"] = (df_mm_hist["pieces"] - df_mm_hist["free_pieces"]) * df_mm_hist["direct_new"]
                df_mm_hist["revenue_scenario"] = df_mm_hist["revenue_scenario"].clip(lower=0)
            else:
                # ΥΠΟΘΕΤΙΚΟΣ τζίρος (ΜΕΤΑ το σενάριο) — ΙΔΙΑ τεμάχια/εκπτώσεις, ΝΕΑ τιμή καταλόγου
                df_mm_hist["price_after_global_new"] = df_mm_hist["retail_new"] * (1 - (df_mm_hist["global_discount"] / 100))
                df_mm_hist["rev_normal_new"] = df_mm_hist["normal_pcs"] * df_mm_hist["price_after_global_new"]
                df_mm_hist["rev_special_new"] = df_mm_hist["s_pcs"] * df_mm_hist["price_after_global_new"] * (1 - (df_mm_hist["s_pct"] / 100))
                df_mm_hist["revenue_scenario"] = (df_mm_hist["rev_normal_new"] + df_mm_hist["rev_special_new"]).clip(lower=0)

            # Κόστος — ΔΕΝ αλλάζει στο σενάριο (το σενάριο αφορά τιμολόγηση, όχι κόστος)
            df_mm_hist["cost_total"] = df_mm_hist["pieces"] * df_mm_hist["applied_cost"]

            total_paid_pieces_mm = df_mm_hist["paid_pieces"].sum()
            total_revenue_actual = df_mm_hist["revenue_actual"].sum()
            total_revenue_scenario = df_mm_hist["revenue_scenario"].sum()
            total_cost_mm = df_mm_hist["cost_total"].sum()

            gross_profit_actual = total_revenue_actual - total_cost_mm
            gross_profit_scenario = total_revenue_scenario - total_cost_mm

            # Σταθερά έξοδα από το ήδη υπάρχον Νεκρό Σημείο (μηνιαία ×12 = ετήσια, για ενδεικτική σύγκριση)
            _mm_settings = load_cost_settings() or {}
            _mm_fixed_monthly = sum(float(_mm_settings.get(k, 0.0) or 0.0) for k in ["be_rent", "be_labor", "be_insurance", "be_admin", "be_utilities", "be_other"])
            _mm_fixed_annual = _mm_fixed_monthly * 12

            net_profit_actual = gross_profit_actual - _mm_fixed_annual
            net_profit_scenario = gross_profit_scenario - _mm_fixed_annual

            st.markdown("### 📊 Μέσος Όρος (σταθμισμένος με πραγματικές πωλήσεις)")
            if total_paid_pieces_mm > 0:
                avg_price_old = total_revenue_actual / total_paid_pieces_mm
                avg_price_new = total_revenue_scenario / total_paid_pieces_mm
                avg_markup_old = _markup(total_cost_mm / total_paid_pieces_mm if total_paid_pieces_mm else 0, avg_price_old)
                avg_markup_new = _markup(total_cost_mm / total_paid_pieces_mm if total_paid_pieces_mm else 0, avg_price_new)
                avg_margin_old = _margin(total_cost_mm / total_paid_pieces_mm if total_paid_pieces_mm else 0, avg_price_old)
                avg_margin_new = _margin(total_cost_mm / total_paid_pieces_mm if total_paid_pieces_mm else 0, avg_price_new)

                ac1, ac2, ac3 = st.columns(3)
                ac1.metric("Μέση Τιμή Πώλησης", f"{avg_price_new:.2f} €", delta=f"{(avg_price_new-avg_price_old):+.2f} € vs {avg_price_old:.2f} € τώρα")
                ac2.metric("Μέσο Markup", f"{avg_markup_new:.1f} %", delta=f"{(avg_markup_new-avg_markup_old):+.1f} pp")
                ac3.metric("Μέσο Margin", f"{avg_margin_new:.1f} %", delta=f"{(avg_margin_new-avg_margin_old):+.1f} pp")
                st.caption(f"Βάσει {int(total_paid_pieces_mm):,} πληρωμένων τεμαχίων ιστορικά (όλες οι ημερομηνίες, όλα τα κοκτέιλ).")
            else:
                st.warning("Δεν βρέθηκε αρκετό ιστορικό πωλήσεων για σταθμισμένο μέσο όρο.")

            st.markdown("### 💰 Επίδραση στα Έσοδα - Έξοδα (βάσει ιστορικών πωλήσεων)")
            if _direct_mode:
                st.caption("Τι θα γινόταν αν οι ΙΔΙΕΣ πωλήσεις (ίδια τεμάχια) γίνονταν ΑΠΕΥΘΕΙΑΣ στον τελικό πελάτη, χωρίς αντιπρόσωπο και χωρίς εκπτώσεις. Το κόστος δεν αλλάζει.")
            else:
                st.caption("Τι θα γινόταν αν οι ΙΔΙΕΣ πωλήσεις (ίδια τεμάχια, ίδιες εκπτώσεις) είχαν γίνει με τις ΝΕΕΣ τιμές του σεναρίου μέσω αντιπροσώπου. Το κόστος δεν αλλάζει — το σενάριο αφορά μόνο τιμολόγηση.")

            st.caption(
                "ℹ️ Σε αυτό το σενάριο αλλάζει **μόνο** ο τζίρος (η τιμολόγηση) — το κόστος και τα σταθερά έξοδα "
                "παραμένουν ίδια. Γι' αυτό η μεταβολή σε Τζίρο, Μικτό και Καθαρό Κέρδος βγαίνει το **ίδιο ποσό σε ευρώ** "
                "— είναι μαθηματικά αναμενόμενο, όχι σφάλμα."
            )

            # 🆕 ΦΟΡΟΛΟΓΙΑ ΕΙΣΟΔΗΜΑΤΟΣ
            tax_rate_mm = st.number_input("Συντελεστής Φόρου Εισοδήματος (%)", min_value=0.0, max_value=100.0, value=22.0, step=1.0, key="mm_tax_rate", help="Προεπιλογή 22% (τρέχων συντελεστής φορολογίας νομικών προσώπων στην Ελλάδα) — άλλαξέ το αν χρειάζεται.")
            tax_actual = max(0.0, net_profit_actual) * (tax_rate_mm / 100)
            tax_scenario = max(0.0, net_profit_scenario) * (tax_rate_mm / 100)
            net_after_tax_actual = net_profit_actual - tax_actual
            net_after_tax_scenario = net_profit_scenario - tax_scenario

            def _delta_str(old_v, new_v, is_currency=True):
                diff = new_v - old_v
                pct = (diff / abs(old_v) * 100) if old_v != 0 else 0
                if is_currency:
                    return f"{diff:+,.2f} € ({pct:+.1f}%)"
                return f"{diff:+.1f} pp"

            pl1, pl2 = st.columns(2)
            with pl1:
                st.markdown("**Τώρα (πραγματικό)**")
                st.metric("Τζίρος", f"{total_revenue_actual:,.2f} €")
                st.metric("Μικτό Κέρδος", f"{gross_profit_actual:,.2f} €")
                st.metric("Καθαρό Κέρδος (προ φόρων)", f"{net_profit_actual:,.2f} €", help=f"Μετά από {_mm_fixed_annual:,.0f}€ ετήσια σταθερά έξοδα (από το Νεκρό Σημείο)")
                st.metric(f"Φόρος Εισοδήματος ({tax_rate_mm:.0f}%)", f"-{tax_actual:,.2f} €")
                st.metric("Καθαρό Κέρδος (μετά φόρων)", f"{net_after_tax_actual:,.2f} €")
            with pl2:
                st.markdown("**Με το Σενάριο**")
                st.metric("Τζίρος", f"{total_revenue_scenario:,.2f} €", delta=_delta_str(total_revenue_actual, total_revenue_scenario))
                st.metric("Μικτό Κέρδος", f"{gross_profit_scenario:,.2f} €", delta=_delta_str(gross_profit_actual, gross_profit_scenario))
                st.metric("Καθαρό Κέρδος (προ φόρων)", f"{net_profit_scenario:,.2f} €", delta=_delta_str(net_profit_actual, net_profit_scenario))
                st.metric(f"Φόρος Εισοδήματος ({tax_rate_mm:.0f}%)", f"-{tax_scenario:,.2f} €", delta=_delta_str(-tax_actual, -tax_scenario))
                st.metric("Καθαρό Κέρδος (μετά φόρων)", f"{net_after_tax_scenario:,.2f} €", delta=_delta_str(net_after_tax_actual, net_after_tax_scenario))

            if _mm_fixed_annual == 0:
                st.info("ℹ️ Δεν έχουν καταχωρηθεί σταθερά έξοδα στο «🎯 Νεκρό Σημείο» — το Καθαρό Κέρδος εδώ ισούται προσωρινά με το Μικτό.")
        else:
            st.warning("Δεν βρέθηκε ιστορικό πωλήσεων για υπολογισμό της επίδρασης στα Έσοδα-Έξοδα.")

        # --- 📄 ΛΗΨΗ PDF ---
        st.divider()
        try:
            now_str = datetime.now(greece_tz).strftime("%d/%m/%Y %H:%M")
        except Exception:
            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

        pdf_data = {
            "now_str": now_str,
            "my_cost": my_cost, "agent_price": agent_price, "retail_price": retail_price,
            "markup1": markup1, "margin1": margin1, "markup2": markup2, "margin2": margin2,
            "markup3": markup3, "margin3": margin3,
            "scenario_ran": True, "scenario_mode": scenario_mode,
            "desired1": desired1, "desired2": desired2, "desired3": desired3,
            "new_agent_price": new_agent_price if new_agent_price != float('inf') else None,
            "new_retail_price": new_retail_price if new_retail_price != float('inf') else None,
            "new_direct_price": new_direct_price if new_direct_price != float('inf') else None,
            "new_markup1": new_markup1, "new_margin1": new_margin1,
            "new_markup2": new_markup2, "new_margin2": new_margin2,
            "new_markup3": new_markup3, "new_margin3": new_margin3,
            "delta_agent": (new_agent_price - agent_price) if new_agent_price != float('inf') else 0,
            "delta_agent_pct": ((new_agent_price - agent_price) / agent_price * 100) if agent_price > 0 and new_agent_price != float('inf') else 0,
            "delta_retail": (new_retail_price - retail_price) if new_retail_price != float('inf') else 0,
            "delta_retail_pct": ((new_retail_price - retail_price) / retail_price * 100) if retail_price > 0 and new_retail_price != float('inf') else 0,
            "delta_direct": (new_direct_price - retail_price) if new_direct_price != float('inf') else 0,
            "delta_direct_pct": ((new_direct_price - retail_price) / retail_price * 100) if retail_price > 0 and new_direct_price != float('inf') else 0,
            "total_change_text": total_change_text,
        }

        try:
            pdf_bytes = generate_markup_margin_pdf(choice, pdf_data)
            st.download_button(
                "📄 Λήψη Αναφοράς PDF (αυτό το κοκτέιλ)",
                data=bytes(pdf_bytes),
                file_name=f"Markup_Margin_{choice.replace(' ', '_')}_{now_str.replace('/', '-').replace(':', 'h')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Σφάλμα προετοιμασίας PDF: {e}")

        st.divider()
        st.caption("📚 Ή, αν θέλεις πλήρη αναφορά με όλες τις συνταγές μαζί (υλικά σε ml/gr, κόστος, markup/margin):")
        if st.button("📚 Δημιουργία Πλήρους Αναφοράς Όλων των Συνταγών", use_container_width=True):
            try:
                with st.spinner("Δημιουργία αναφοράς για όλες τις συνταγές..."):
                    full_pdf_bytes = generate_full_recipe_report_pdf(df_rec, df_ing, get_unit_cost_for_cocktail)
                st.session_state['full_recipe_pdf'] = bytes(full_pdf_bytes)
                st.session_state['full_recipe_pdf_name'] = now_str.replace('/', '-').replace(':', 'h')
            except Exception as e:
                st.error(f"Σφάλμα προετοιμασίας πλήρους αναφοράς: {e}")

        if st.session_state.get('full_recipe_pdf'):
            st.download_button(
                "📥 Λήψη Πλήρους Αναφοράς (όλες οι συνταγές)",
                data=st.session_state['full_recipe_pdf'],
                file_name=f"Cabclub_Πλήρης_Αναφορά_Συνταγών_{st.session_state.get('full_recipe_pdf_name', now_str)}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

elif page == "📊 Εμπορική Πολιτική":
    st.header("📊 Εμπορική Πολιτική & Σύγκριση Σεναρίων")
    st.write("Συγκρίνετε τη στρατηγική Δώρων έναντι της Έκπτωσης % και δείτε την ανάλυση κερδοφορίας.")

    # --- ΜΑΓΕΙΑ SUPABASE: Φόρτωση φρέσκων δεδομένων για την Εμπορική Πολιτική ---
    res_ing = supabase.table("ingredients").select("*").execute()
    ing_data = res_ing.data if res_ing.data else []
    df_ing_list = []
    for item in ing_data:
        df_ing_list.append({
            "Name": str(item["name"]).strip(), # 👈 Η διόρθωση για τα αόρατα κενά!
            "Price": item["price"],
            "Volume": item["volume"],
            "weight_full": item.get("weight_full", 0.0), 
            "Αλκοόλ %": item["abv"],
            "ABV": item["abv"], 
            "Τιμή/ml": item["price"] / item["volume"] if item["volume"] > 0 else 0
        })
    df_ing = pd.DataFrame(df_ing_list)

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

    if not df_rec.empty:
        # 1. 🚀 ΠΟΛΛΑΠΛΗ ΕΠΙΛΟΓΗ ΚΟΚΤΕΙΛ
        choices = st.multiselect("Επιλέξτε Cocktail(s) για Σύγκριση:", df_rec["Ονομα"].unique())

        if choices:
            st.divider()
            
            # --- ΔΥΝΑΜΙΚΟ ΦΙΛΤΡΟ ΤΙΜΟΛΟΓΙΑΚΗΣ ΒΑΣΗΣ (GLOBAL) ---
            price_target = st.radio(
                "🏷️ Επιλογή Τιμολογιακής Βάσης για τη Σύγκριση:", 
                options=["Τιμή Αντιπροσώπου (Χονδρική)", "Τιμή Λιανικής (Κατάλογος)"],
                horizontal=True,
                key="commercial_policy_price_filter"
            )
            
            # 2. 🚀 ΠΑΡΑΜΕΤΡΟΙ ΣΕΝΑΡΙΩΝ (Εφαρμόζονται σε ΟΛΑ τα επιλεγμένα κοκτέιλ)
            st.markdown("### ⚙️ Παράμετροι Σεναρίων (Εφαρμόζονται σε όλα τα επιλεγμένα)")
            col_in_a, col_in_b = st.columns(2)

            with col_in_a:
                st.subheader("Σενάριο Α: Δώρα (Free Goods)")
                sA_paid = st.number_input("Τεμάχια προς Πώληση (Paid)", min_value=0, value=0, key="sa_paid")
                sA_free = st.number_input("Τεμάχια Δώρο (Free)", min_value=0, value=0, key="sa_free")

            with col_in_b:
                st.subheader("Σενάριο Β: Έκπτωση επί της Τιμής")
                sB_total_units = st.number_input("Συνολικά Τεμάχια (Β)", min_value=0, value=0, key="sb_total")
                sB_discount = st.number_input("Ποσοστό Έκπτωσης %", min_value=0.0, value=0.0, key="sb_disc")

            st.divider()

            # 3. 🚀 ΛΟΥΠΑ ΥΠΟΛΟΓΙΣΜΟΥ ΚΑΙ ΕΜΦΑΝΙΣΗΣ ΓΙΑ ΚΑΘΕ ΚΟΚΤΕΙΛ
            for choice in choices:
                st.markdown(f"## 🍹 Ανάλυση: {choice}")
                
                r = df_rec[df_rec["Ονομα"] == choice].iloc[0]

                raw_cost = 0.0
                for i in range(1, 14):
                    ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                    ml = float(r.get(f"ML{i}", 0))
                    if ing_n not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                        match = df_ing[df_ing["Name"] == ing_n]
                        if not match.empty:
                            raw_cost += ml * float(match.iloc[0]["Τιμή/ml"])
                
                unit_cost = get_unit_cost_for_cocktail(choice, raw_cost)
                p_retail = float(r["Τιμή Καταλόγου"])
                p_agent_base = p_retail * 0.74  
                
                if price_target == "Τιμή Λιανικής (Κατάλογος)":
                    active_base_price = p_retail
                    price_label_text = "Κανονική Τιμή Λιανικής"
                else:
                    active_base_price = p_agent_base
                    price_label_text = "Κανονική Τιμή Αντιπρ."
                    
                normal_profit_per_unit = active_base_price - unit_cost
                
                # --- Υπολογισμοί Σεναρίου Α ---
                sA_total_units = sA_paid + sA_free
                sA_revenue = sA_paid * active_base_price
                sA_cost = sA_total_units * unit_cost
                sA_profit = sA_revenue - sA_cost
                sA_effective = sA_revenue / sA_total_units if sA_total_units > 0 else 0
                sA_margin = (sA_profit / sA_revenue * 100) if sA_revenue > 0 else 0
                sA_markup = (sA_profit / sA_cost * 100) if sA_cost > 0 else 0
                sA_loss = (normal_profit_per_unit * sA_total_units) - sA_profit if sA_total_units > 0 else 0
                
                # --- Υπολογισμοί Σεναρίου Β ---
                sB_price_per_unit = active_base_price * (1 - sB_discount/100)
                sB_revenue = sB_total_units * sB_price_per_unit
                sB_cost = sB_total_units * unit_cost
                sB_profit = sB_revenue - sB_cost
                sB_effective = sB_price_per_unit
                sB_margin = (sB_profit / sB_revenue * 100) if sB_revenue > 0 else 0
                sB_markup = (sB_profit / sB_cost * 100) if sB_cost > 0 else 0
                sB_loss = (normal_profit_per_unit * sB_total_units) - sB_profit if sB_total_units > 0 else 0

                # --- 🚀 Υπολογισμός Net Κέρδους ανά τμχ (Με Χρώματα) ---
                net_profit_a = (sA_profit / sA_total_units) if sA_total_units > 0 else 0
                net_profit_b = (sB_profit / sB_total_units) if sB_total_units > 0 else 0
                
                color_a = "#ff4d4d" if net_profit_a < 0 else "#4caf50"
                color_b = "#ff4d4d" if net_profit_b < 0 else "#2196f3"

                if sA_total_units > 0 or sB_total_units > 0:
                    winner_text = "ΣΕΝΑΡΙΟ Α" if sA_profit > sB_profit else "ΣΕΝΑΡΙΟ Β"
                    diff_val = abs(sA_profit - sB_profit)

                    # 4. Σχεδιασμός Πίνακα (HTML format) - Τραβηγμένο τέρμα αριστερά για το Streamlit
                    html_table = """
<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #444; margin-bottom: 15px;">
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
            <td style="padding: 10px; border: 1px solid #444;">Net Κέρδος / τμχ (Αρχικό)</td>
            <td style="text-align:center; color: #ddd; border: 1px solid #444;">{16:.2f} €</td>
            <td style="text-align:center; color: #ddd; border: 1px solid #444;">{16:.2f} €</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #444;">Net Κέρδος / τμχ (Τελικό)</td>
            <td style="text-align:center; color: {19}; font-weight: bold; border: 1px solid #444;">{17:.2f} €</td>
            <td style="text-align:center; color: {20}; font-weight: bold; border: 1px solid #444;">{18:.2f} €</td>
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
                        sA_markup, sB_markup, winner_text, diff_val, price_label_text,
                        normal_profit_per_unit, net_profit_a, net_profit_b, color_a, color_b 
                    )
                    
                    st.markdown(html_table, unsafe_allow_html=True)

                    # 5. ΥΠΕΡ-ΑΝΑΛΥΤΙΚΟ ΕΠΑΓΓΕΛΜΑΤΙΚΟ REPORT (ΕΞΑΓΩΓΗ ΣΕ HTML)
                    try:
                        now_str = datetime.now(greece_tz).strftime("%d/%m/%Y %H:%M")
                    except:
                        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                        
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
                        
                        {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "Net Κέρδος ανά τμχ (Αρχικό)", "ΣΕΝΑΡΙΟ Α": f"{normal_profit_per_unit:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{normal_profit_per_unit:.2f} €"},
                        {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "Net Κέρδος ανά τμχ (Τελικό)", "ΣΕΝΑΡΙΟ Α": f"{net_profit_a:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{net_profit_b:.2f} €"},
                        {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "Διαφορά Κέρδους Συμφωνίας", "ΣΕΝΑΡΙΟ Α": f"{diff_val:.2f} €" if sA_profit > sB_profit else "-", "ΣΕΝΑΡΙΟ Β": f"{diff_val:.2f} €" if sB_profit > sA_profit else "-"},
                        {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "ΚΑΤΑΣΤΑΣΗ ΕΓΚΡΙΣΗΣ", "ΣΕΝΑΡΙΟ Α": "ΕΠΙΛΟΓΗ" if sA_profit > sB_profit else "-", "ΣΕΝΑΡΙΟ Β": "ΕΠΙΛΟΓΗ" if sB_profit > sA_profit else "-"}
                    ]
                    
                    # --- Δημιουργία HTML Πίνακα από τα Δεδομένα ---
                    html_rows = ""
                    for row in full_audit_data:
                        if row["ΣΤΟΙΧΕΙΟ"] == "":
                            html_rows += "<tr style='background-color: #f8f9fa;'><td colspan='4'>&nbsp;</td></tr>"
                        else:
                            html_rows += f"""
                            <tr>
                                <td><strong>{row['ΚΑΤΗΓΟΡΙΑ']}</strong></td>
                                <td>{row['ΣΤΟΙΧΕΙΟ']}</td>
                                <td style='text-align: center; font-weight: bold;'>{row['ΣΕΝΑΡΙΟ Α']}</td>
                                <td style='text-align: center; font-weight: bold;'>{row['ΣΕΝΑΡΙΟ Β']}</td>
                            </tr>
                            """

                    report_html = f"""
                    <!DOCTYPE html>
                    <html lang="el">
                    <head>
                        <meta charset="UTF-8">
                        <title>Audit Report - {choice}</title>
                        <style>
                            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; padding: 30px; background-color: #f4f6f8; }}
                            .container {{ max-width: 900px; margin: auto; background-color: white; border: 1px solid #ddd; padding: 40px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
                            .header {{ text-align: center; border-bottom: 3px solid #1a3a5f; padding-bottom: 20px; margin-bottom: 30px; }}
                            .header h1 {{ color: #1a3a5f; margin: 0; font-size: 28px; letter-spacing: 1px; }}
                            .header h2 {{ color: #555; font-size: 16px; font-weight: 400; margin-top: 5px; text-transform: uppercase; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                            th, td {{ border: 1px solid #e0e0e0; padding: 12px; text-align: left; }}
                            th {{ background-color: #1a3a5f; color: white; text-align: center; font-weight: 600; text-transform: uppercase; }}
                            tr:nth-child(even) {{ background-color: #fcfcfc; }}
                            .winner-box {{ background-color: #e8f5e9; border-left: 5px solid #4caf50; padding: 15px; margin-top: 30px; border-radius: 4px; }}
                            .footer {{ text-align: center; margin-top: 40px; font-size: 11px; color: #999; border-top: 1px solid #eee; padding-top: 15px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>CABCLUB COCKTAILS</h1>
                                <h2>AUDIT REPORT ΕΜΠΟΡΙΚΗΣ ΠΟΛΙΤΙΚΗΣ: {choice}</h2>
                            </div>
                            
                            <table>
                                <thead>
                                    <tr>
                                        <th>ΚΑΤΗΓΟΡΙΑ</th>
                                        <th>ΣΤΟΙΧΕΙΟ / ΠΕΡΙΓΡΑΦΗ</th>
                                        <th>ΣΕΝΑΡΙΟ Α (ΔΩΡΑ)</th>
                                        <th>ΣΕΝΑΡΙΟ Β (ΕΚΠΤΩΣΗ)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {html_rows}
                                </tbody>
                            </table>
                            
                            <div class="winner-box">
                                <h3 style="color: #2e7d32; margin-top: 0;">🏆 Τελικό Συμπέρασμα: Επικρατεί το {winner_text}</h3>
                                <p style="margin-bottom: 0;">Βάσει της ανάλυσης, η συγκεκριμένη επιλογή αποφέρει επιπλέον καθαρό κέρδος <b>{diff_val:.2f} €</b> για την εταιρεία.</p>
                            </div>

                            <div class="footer">
                                Το έγγραφο δημιουργήθηκε αυτόματα από το σύστημα διαχείρισης DC CABCLUB στις {now_str}.
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    col_btn1, col_btn2 = st.columns([1, 2])
                    with col_btn1:
                        st.download_button(
                            label=f"📥 Λήψη Φακέλου (HTML): {choice}", 
                            data=report_html, 
                            file_name=f"Audit_Report_{choice.replace(' ', '_')}.html",
                            mime="text/html",
                            key=f"dl_audit_{choice}"
                        )
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    
            # 6. ΕΠΕΞΗΓΗΣΗ ΟΙΚΟΝΟΜΙΚΩΝ ΟΡΩΝ
            st.divider()
            with st.expander("ℹ️ Ερμηνεία Οικονομικών Όρων & Δεικτών"):
                st.info("""
                * **Net Κέρδος/τμχ (Αρχικό):** Το καθαρό κέρδος που βγάζεις ανά τεμάχιο ΧΩΡΙΣ καμία προσφορά (Τιμή - Κόστος).
                * **Net Κέρδος/τμχ (Τελικό):** Το πραγματικό σου κέρδος ανά τεμάχιο, έχοντας συνυπολογίσει τη "χασούρα" από τα δώρα ή την έκπτωση. Αν είναι κόκκινο, μπαίνεις μέσα!
                * **Effective Τιμή:** Η πραγματική τιμή που εισπράττει η εταιρεία ανά μονάδα προϊόντος, αφού υπολογιστούν τα δώρα ή οι εκπτώσεις.
                * **Margin (Περιθώριο Κέρδους %):** Το ποσοστό του τζίρου που παραμένει ως κέρδος. Υπολογίζεται ως: `(Κέρδος / Έσοδα) * 100`.
                * **Markup (Ποσοστό Επιβάρυνσης %):** Το ποσοστό πάνω στο κόστος παραγωγής που προστίθεται για να προκύψει η τιμή πώλησης. Υπολογίζεται ως: `(Κέρδος / Κόστος) * 100`.
                * **Κόστος Εμπορικής Ενέργειας:** Το "διαφυγόν κέρδος". Πόσα χρήματα επενδύει η εταιρεία στην προσφορά σε σχέση με την κανονική τιμή πώλησης.
                """)
            
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
        # --- ΚΑΘΑΡΙΣΜΟΣ & ΠΡΟΕΤΟΙΜΑΣΙΑ ΔΕΔΟΜΕΝΩΝ ---
        if not df_customers.empty:
            df_customers['name'] = df_customers.get('name', '').astype(str).str.strip()
            df_customers['discount'] = pd.to_numeric(df_customers.get('discount', 0), errors='coerce').fillna(0)
        else:
            df_customers = pd.DataFrame({'name': [], 'discount': []})

        # 🚀 ΜΑΓΙΚΗ ΑΣΠΙΔΑ DASHBOARD: Αντί για απλό drop_duplicates, κάνουμε έξυπνη Ομαδοποίηση!
        for col in ['pieces', 'free_pieces', 'discounted_pieces', 'discount_pct']:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)

        if 'applied_cost' not in df_raw.columns:
            df_raw['applied_cost'] = None

        # Σκανάρουμε όλα τα υλικά για να δούμε αν κάποιο ήταν "Έτοιμο Προϊόν" (για τα παλιά Στοκ)
        df_raw['is_stock_legacy'] = df_raw.get('ingredient_name', '').astype(str).str.contains("Έτοιμο Προϊόν", na=False)

        # Συμπιέζουμε σε 1 γραμμή ανά παραγωγή διατηρώντας το μικρότερο κόστος (το 0)
        df_sales = df_raw.groupby(["prod_date", "prod_time", "customer", "cocktail_name", "lot_cocktail"], dropna=False, as_index=False).agg(
            pieces=("pieces", "max"),
            free_pieces=("free_pieces", "max"),
            discounted_pieces=("discounted_pieces", "max"),
            discount_pct=("discount_pct", "max"),
            applied_cost=("applied_cost", "min"), 
            has_legacy_stock=("is_stock_legacy", "max") 
        )

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
        df_ing = pd.DataFrame(res_ing.data)
        df_ing['cost_per_ml'] = pd.to_numeric(df_ing.get('price', 0), errors='coerce') / pd.to_numeric(df_ing.get('volume', 1), errors='coerce')
        ing_cost_dict = dict(zip(df_ing['name'], df_ing['cost_per_ml']))
        
        df_items = pd.DataFrame(res_items.data)
        mat_cost_by_id = {}
        for rid in df_items['recipe_id'].unique():
            sub = df_items[df_items['recipe_id'] == rid]
            # 🔧 FIX: εξαίρεση "Νερό" ρητά, για συνέπεια με Νεκρό Σημείο/Έσοδα-Έξοδα
            # (εκεί ήδη εξαιρείται — αν το Νερό έχει καταχωρημένη τιμή >0, θα διέφερε το κόστος).
            mat_cost_by_id[rid] = sum(pd.to_numeric(item.get('ml_per_unit', 0), errors='coerce') * ing_cost_dict.get(item.get('ingredient_name'), 0) for _, item in sub.iterrows() if str(item.get('ingredient_name')).strip() != "Νερό")
            
        # 🔧 FIX: πριν χρησιμοποιούσε hardcoded 0.22 ασύνδετο από το Κοστολόγιο· τώρα κόστος ανά κοκτέιλ
        name_to_cost = {r['name']: get_unit_cost_for_cocktail(r['name'], mat_cost_by_id.get(r['id'], 0.0)) for _, r in df_recipes.iterrows()}

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
        def get_actual_cost(row):
            catalog_c = name_to_cost.get(row['cocktail_name'], get_unit_cost_for_cocktail(row['cocktail_name'], 0.0))
            
            # 1. Κοιτάμε τη ΝΕΑ στήλη applied_cost (κρατάει το 0 αν είναι Στοκ)
            if pd.notna(row.get('applied_cost')):
                return float(row['applied_cost'])
            
            # 2. Ασφαλιστική δικλείδα για τα παλιά Στοκ που πιάσαμε με την ομαδοποίηση
            if row.get('has_legacy_stock'):
                return 0.0
                
            return catalog_c

        df_filtered['Final_Unit_Cost'] = df_filtered.apply(get_actual_cost, axis=1)
        df_filtered['Total_Cost'] = df_filtered['t_pcs'] * df_filtered['Final_Unit_Cost']
        df_filtered['Profit'] = df_filtered['Theoretical_Revenue'] - df_filtered['Total_Cost']

        # --- ΣΥΓΧΡΟΝΙΣΜΟΣ ΔΕΔΟΜΕΝΩΝ ΓΙΑ METRICS & ΓΡΑΦΗΜΑΤΑ ---
        total_rev = df_filtered['Theoretical_Revenue'].sum()
        total_cost = df_filtered['Total_Cost'].sum()
        total_profit = df_filtered['Profit'].sum()
        total_units = df_filtered['t_pcs'].sum()
        total_orders_count = df_filtered.groupby(['prod_date', 'customer']).ngroups
        # 🔧 Ξεχωριστό μέτρημα ΜΟΝΟ B2B παραγγελιών (χωρίς λιανική) — ίδια λογική με το
        # tab "📦 Παραγγελίες B2B", όπου η «Λιανική / Άγνωστος» εξαιρείται σκόπιμα από τιμολόγια.
        b2b_only_count = df_filtered[df_filtered['customer'] != "Λιανική / Άγνωστος"].groupby(['prod_date', 'customer']).ngroups if not df_filtered.empty else 0

        df_mom_grouped = df_filtered.groupby(['customer', 'Month_Year'])['Theoretical_Revenue'].sum().reset_index()
        df_mom_grouped.rename(columns={'Theoretical_Revenue': 'Revenue', 'Month_Year': 'Month'}, inplace=True)

        # --- METRICS ΣΥΝΟΨΗΣ ---
        st.divider()
        st.subheader(f"📊 Σύνοψη & Απόδοση: {sel_customer if sel_customer != 'ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ' else 'Όλοι οι Πελάτες'}")
        
        margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
        aov = total_rev / total_orders_count if total_orders_count > 0 else 0
        total_gifts_given = int(df_filtered['f_pcs'].sum()) if not df_filtered.empty else 0
        
        m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
        m1.metric("💰 Τζίρος", f"{format_gr(total_rev)} €")
        m2.metric("📈 Μικτό Κέρδος", f"{format_gr(total_profit)} €", delta=f"{margin:.1f}% Margin", help="Τζίρος − Κόστος Υλικών. ΔΕΝ αφαιρεί τα Σταθερά Έξοδα Επιχείρησης (ενοίκιο, μισθοδοσία κ.λπ.) — για το πραγματικό καθαρό κέρδος δες την καρτέλα «📑 Έσοδα - Έξοδα».")
        m3.metric("📉 Συνολικό Κόστος", f"{format_gr(total_cost)} €", help="Περιλαμβάνει υλικά + λειτουργικό/σταθερό κόστος ανά τεμάχιο.")
        m4.metric("🍹 Τεμάχια", f"{format_gr(int(total_units), decimals=0)} τμχ")
        m5.metric("🎁 Δώρα", f"{total_gifts_given} τμχ", help="Δωρεάν τεμάχια (Κιβωτιακή Πολιτική) μέσα στο τρέχον φίλτρο.")
        m6.metric("📦 Παραγγελίες", format_gr(total_orders_count, decimals=0), delta=f"{format_gr(b2b_only_count, decimals=0)} μόνο B2B (χωρίς λιανική)", delta_color="off", help="Το κύριο νούμερο περιλαμβάνει και λιανική. Το κάτω νούμερο ταιριάζει με την καρτέλα «📦 Παραγγελίες B2B».")
        m7.metric("⚖️ Μέση Αξία", f"{format_gr(aov)} €")

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
                    if s['Final_Unit_Cost'] == 0.0:
                        st.write("📦 **Άντληση από Στοκ (Χωρίς χρέωση)**")
                        st.markdown("**Κόστος ανά τμχ: 0.00€**")
                    elif _manual_cost_active:
                        _ind = float(_cocktail_costs_map.get(s['cocktail_name'], 0.0))
                        _op = float((_cost_settings or {}).get("operational_cost") or 0.0)
                        _raw_derived = s['Final_Unit_Cost'] - _ind - _op  # 🔧 FIX: πρόσθεσε το κόστος υλικών, που τώρα μπαίνει και αυτό στο σύνολο
                        st.write(f"- **Κόστος Υλικών:** {_raw_derived:.4f}€")
                        st.write(f"- **Εργατικά:** {_ind:.4f}€")
                        st.write(f"- **Κόστος Συσκευασίας:** {_op:.4f}€")
                        st.markdown(f"- **Κόστος ανά τμχ: {s['Final_Unit_Cost']:.4f}€**")
                    else:
                        st.write(f"- **Κόστος Υλικών:** {s['Final_Unit_Cost'] - _TOTAL_FIXED_FALLBACK:.4f}€")
                        st.write(f"- **Σταθερά Έξοδα:** {_TOTAL_FIXED_FALLBACK:.2f}€")
                        st.markdown(f"- **Κόστος ανά τμχ: {s['Final_Unit_Cost']:.4f}€**")
                    st.caption("---")
                    st.write(f"- Παράχθηκαν: {s['t_pcs']} τμχ")
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

        # --- ΚΟΣΤΟΣ ΑΝΑ ΠΡΩΤΗ ΥΛΗ ---
        st.divider()
        st.subheader("🛒 Συνολικό Κόστος & Ανάλωση ανά Πρώτη Ύλη")
        
        df_ing_raw = df_raw.copy()
        df_ing_raw['Date_Obj'] = pd.to_datetime(df_ing_raw.get('prod_date'), format='%d/%m/%Y', errors='coerce')
        df_ing_raw['Month_Year'] = df_ing_raw['Date_Obj'].dt.strftime('%m/%Y')
        
        if sel_customer != "ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ":
            df_ing_raw = df_ing_raw[df_ing_raw['customer'] == sel_customer]
        if sel_month != "ΟΛΟΙ ΟΙ ΜΗΝΕΣ":
            df_ing_raw = df_ing_raw[df_ing_raw['Month_Year'] == sel_month]
            
        df_ing_raw = df_ing_raw[~df_ing_raw['ingredient_name'].astype(str).str.contains("Έτοιμο Προϊόν", na=False)]
        df_ing_raw = df_ing_raw.dropna(subset=['ingredient_name'])
        
        if not df_ing_raw.empty:
            df_ing_raw['total_ml'] = pd.to_numeric(df_ing_raw['total_ml'], errors='coerce').fillna(0)
            
            # 🚀 ΝΕΟ: Φορτώνουμε και τους όγκους (Volume) των φιαλών από τη βάση
            df_ing_for_vol = pd.DataFrame(supabase.table("ingredients").select("name, volume").execute().data)
            ing_vol_dict = dict(zip(df_ing_for_vol['name'], pd.to_numeric(df_ing_for_vol.get('volume', 1), errors='coerce')))
            
            df_ing_costs = df_ing_raw.groupby('ingredient_name').agg(Total_ML=('total_ml', 'sum')).reset_index()
            df_ing_costs['Unit_Cost_per_ml'] = df_ing_costs['ingredient_name'].map(ing_cost_dict).fillna(0)
            df_ing_costs['Total_Cost'] = df_ing_costs['Total_ML'] * df_ing_costs['Unit_Cost_per_ml']
            
            # 🚀 ΝΕΟ: Υπολογισμός των φιαλών (Διαιρούμε τα συνολικά ml με τα ml της μίας φιάλης)
            df_ing_costs['Bottle_Vol'] = df_ing_costs['ingredient_name'].map(ing_vol_dict).fillna(1)
            # Προστασία για διαίρεση με το μηδέν
            df_ing_costs['Bottle_Vol'] = df_ing_costs['Bottle_Vol'].apply(lambda x: 1 if x == 0 else x) 
            df_ing_costs['Φιάλες'] = df_ing_costs['Total_ML'] / df_ing_costs['Bottle_Vol']
            
            # Ταξινόμηση "Αύξουσα" (γιατί στα οριζόντια γραφήματα το μεγαλύτερο πάει πάνω)
            df_ing_costs = df_ing_costs[df_ing_costs['Total_Cost'] > 0.01].sort_values('Total_Cost', ascending=True)
            
            if not df_ing_costs.empty:
                # Χωρίζουμε την οθόνη (γραφικό και πίνακας)
                col_chart, col_table = st.columns([2.5, 2.0]) # Μεγάλωσα λίγο τον πίνακα για να χωρέσει η νέα στήλη
                
                # Δυναμικό ύψος! 35 pixels για κάθε υλικό, ώστε να μην στριμώχνονται ποτέ.
                dynamic_height = max(400, len(df_ing_costs) * 35)
                
                with col_chart:
                    # Οριζόντιο γράφημα (orientation='h') για τέλεια ανάγνωση
                    fig_ing = px.bar(df_ing_costs, 
                                     x="Total_Cost", y="ingredient_name", orientation='h',
                                     title="Οπτική Κατανομή Κόστους (€)",
                                     labels={"ingredient_name": "", "Total_Cost": "Κόστος (€)"},
                                     text_auto='.2f', color="Total_Cost", color_continuous_scale="Reds")
                    
                    fig_ing.update_traces(textposition='outside')
                    fig_ing.update_layout(template="plotly_dark", height=dynamic_height, showlegend=False, margin=dict(l=10, r=20, t=40, b=20))
                    st.plotly_chart(fig_ing, use_container_width=True)
                
                with col_table:
                    st.markdown("#### 📋 Αναλυτικά Ποσά & Φιάλες")
                    # Για τον πίνακα τα θέλουμε με φθίνουσα σειρά (τα ακριβά πάνω)
                    df_display = df_ing_costs.sort_values('Total_Cost', ascending=False)
                    st.dataframe(
                        df_display[['ingredient_name', 'Φιάλες', 'Total_Cost']].rename(
                            columns={'ingredient_name': 'Πρώτη Ύλη', 'Total_Cost': 'Κόστος'}
                        ).style.format({
                            'Κόστος': "{:.2f} €",
                            'Φιάλες': "{:.1f}" # 🚀 Μορφοποίηση με 1 δεκαδικό (π.χ. 2.4)
                        }),
                        hide_index=True,
                        use_container_width=True,
                        height=dynamic_height # Ο πίνακας παίρνει ακριβώς το ίδιο ύψος με το γράφημα!
                    )
            else:
                st.info("Δεν προέκυψε κόστος πρώτων υλών για αυτή την επιλογή.")
        else:
            st.info("Δεν βρέθηκαν αναλυτικά υλικά για αυτή την επιλογή.")

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
            
            # Δημιουργούμε μια "ασφαλή" στήλη για το μέγεθος της φούσκας (όχι αρνητικά/μηδενικά νούμερα)
            df_hm["Μέγεθος Φούσκας"] = df_hm["Συνολικό Κέρδος"].apply(lambda x: x if x > 0 else 0.5)
            
            fig_hm = px.scatter(
                df_hm, 
                x="Πωλήσεις (Σύνολο)", 
                y="Κέρδος/Τμχ", 
                size="Μέγεθος Φούσκας", # 🚀 Παίρνει το ασφαλές μέγεθος για να μην κρασάρει
                color="Cocktail", 
                hover_name="Cocktail", 
                text="Cocktail", 
                hover_data={"Μέγεθος Φούσκας": False, "Συνολικό Κέρδος": True}, # 🚀 Δείχνει το πραγματικό κέρδος/χασούρα στο ποντίκι
                size_max=50, 
                template="plotly_dark",
                labels={
                    "Κέρδος/Τμχ": "Καθαρό Κέρδος 1 Τεμαχίου (€)", 
                    "Πωλήσεις (Σύνολο)": "Συνολικός Όγκος (τμχ)"
                }
            )
            fig_hm.update_traces(textposition='top center')
            min_margin = df_hm["Κέρδος/Τμχ"].min()
            fig_hm.update_layout(yaxis=dict(range=[min_margin - 0.5, df_hm["Κέρδος/Τμχ"].max() + 1.0]))
            st.plotly_chart(fig_hm, use_container_width=True)

        # =====================================================================
        # 🎁 ΕΝΟΠΟΙΗΜΕΝΗ ΑΝΑΛΥΣΗ ΔΩΡΩΝ (ΠΑΛΙΟ ΣΥΣΤΗΜΑ + ΝΕΑ ΚΙΒΩΤΙΑΚΗ ΠΟΛΙΤΙΚΗ)
        # =====================================================================
        # 🔧 FIX: πριν έδειχνε ΜΟΝΟ τα δώρα του παλιού χειροκίνητου συστήματος (κείμενο
        # "ΠΡΟΣΦΟΡΑ 240" μέσα στο order_details). Τα αυτόματα δώρα της νέας Κιβωτιακής
        # Πολιτικής (πεδίο free_pieces) ήταν ΑΟΡΑΤΑ εδώ. Τώρα δείχνει και τα δύο μαζί.
        import re

        df_dash_promos = pd.DataFrame()
        if not df_orders.empty and 'order_details' in df_orders.columns:
            df_dash_promos = df_orders[df_orders['order_details'].str.contains("ΠΡΟΣΦΟΡΑ 240", na=False)].copy()

        df_new_gifts = df_filtered[df_filtered['f_pcs'] > 0].copy() if not df_filtered.empty else pd.DataFrame()

        if not df_dash_promos.empty or not df_new_gifts.empty:
            st.divider()
            st.subheader("🎁 Ενοποιημένη Ανάλυση Δώρων (Παλιό + Νέο Σύστημα)")

            gcol1, gcol2 = st.columns(2)
            gcol1.metric("🎁 Παλιό Σύστημα (χειροκίνητο)", f"{len(df_dash_promos)} παραγγελίες")
            gcol2.metric("🎁 Νέο Σύστημα (Κιβωτιακή Πολιτική)", f"{int(df_new_gifts['f_pcs'].sum()) if not df_new_gifts.empty else 0} δωρεάν τμχ")

            if not df_dash_promos.empty:
                st.markdown("**Παλιό σύστημα** (χειροκίνητη σημείωση στην παραγγελία):")
                def get_promo_cocktail_dash(detail_str):
                    match = re.search(r"ΠΡΟΣΦΟΡΑ 240\+24 ΔΩΡΟ στο ([^\]\n]+)", str(detail_str))
                    if match: return match.group(1).strip()
                    return "Γενική / Παλιό Μοντέλο"

                df_dash_promos['Ημερομηνία'] = pd.to_datetime(df_dash_promos['created_at']).dt.strftime('%d/%m/%Y')
                df_dash_promos['Κοκτέιλ Προσφοράς'] = df_dash_promos['order_details'].apply(get_promo_cocktail_dash)
                st.dataframe(
                    df_dash_promos.rename(columns={"customer_name": "ΠΕΛΑΤΗΣ", "total_amount": "ΤΕΛΙΚΗ ΧΡΕΩΣΗ (€)"})[["Ημερομηνία", "ΠΕΛΑΤΗΣ", "Κοκτέιλ Προσφοράς", "ΤΕΛΙΚΗ ΧΡΕΩΣΗ (€)"]],
                    use_container_width=True, hide_index=True
                )

            if not df_new_gifts.empty:
                st.markdown("**Νέο σύστημα** (αυτόματο, Κιβωτιακή Πολιτική):")
                st.dataframe(
                    df_new_gifts.rename(columns={"prod_date": "Ημερομηνία Παραγωγής", "customer": "ΠΕΛΑΤΗΣ", "cocktail_name": "Κοκτέιλ", "f_pcs": "Δωρεάν Τεμάχια"})[["Ημερομηνία Παραγωγής", "ΠΕΛΑΤΗΣ", "Κοκτέιλ", "Δωρεάν Τεμάχια"]].sort_values("Ημερομηνία Παραγωγής", ascending=False),
                    use_container_width=True, hide_index=True
                )

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
# --- 🎁 ΚΙΒΩΤΙΑΚΗ ΠΟΛΙΤΙΚΗ ΔΩΡΩΝ ---
# --- 🎯 ΝΕΚΡΟ ΣΗΜΕΙΟ (BREAK-EVEN) ---
elif page == "🎯 Νεκρό Σημείο":
    st.header("🎯 Υπολογιστής Νεκρού Σημείου (Break-Even)")
    st.caption(
        "Πόσα τεμάχια πρέπει να πουλήσεις ανά μήνα / έτος για να καλύψεις τα σταθερά σου έξοδα "
        "(ενοίκιο, μισθοδοσία, ασφάλιστρα κ.λπ. — ό,τι ΔΕΝ αλλάζει ανάλογα με το πόσο πουλάς)."
    )

    _be_settings = load_cost_settings() or {}

    # --- 1. ΣΤΑΘΕΡΑ ΕΞΟΔΑ (ανά κατηγορία, μηνιαία — αθροίζονται αυτόματα) ---
    st.subheader("1️⃣ Σταθερά Έξοδα Επιχείρησης (μηνιαία, ανά κατηγορία)")
    st.caption("Συμπλήρωσε ό,τι ισχύει για την επιχείρησή σου — το σύνολο υπολογίζεται αυτόματα από κάτω.")

    if _manual_cost_active:
        st.warning(
            "⚠️ **Προσοχή στη Μισθοδοσία — χειροκίνητο κόστος ΕΝΕΡΓΟ:** Στο «💰 Κοστολόγιο» τα "
            "\"Εργατικά\" ανά κοκτέιλ περιλαμβάνουν ήδη το κόστος των εργατών παραγωγής. Αν βάλεις "
            "**ξανά** τους ίδιους μισθούς εδώ στο \"Μισθοδοσία\", θα μετρηθούν **δύο φορές** — μία ανά "
            "τεμάχιο (μέσα στο περιθώριο) και μία ως σταθερό έξοδο — υπερεκτιμώντας τα τεμάχια που "
            "χρειάζεσαι για να καλύψεις τα έξοδά σου. Βάλε εδώ **μόνο** μισθούς προσωπικού που ΔΕΝ "
            "μπαίνουν ήδη στα Εργατικά (π.χ. διοικητικό/πωλήσεων), όχι της παραγωγής."
        )

    fc1, fc2 = st.columns(2)
    be_rent = fc1.number_input("🏠 Ενοίκιο", min_value=0.0, value=float(_be_settings.get("be_rent", 0.0)), step=50.0, key="be_rent")
    be_labor = fc2.number_input("👷 Μισθοδοσία (ΜΗ παραγωγικό προσωπικό αν είναι ενεργό το χειροκίνητο κόστος)" if _manual_cost_active else "👷 Μισθοδοσία", min_value=0.0, value=float(_be_settings.get("be_labor", 0.0)), step=50.0, key="be_labor")
    be_insurance = fc1.number_input("🛡️ Ασφάλιστρα", min_value=0.0, value=float(_be_settings.get("be_insurance", 0.0)), step=50.0, key="be_insurance")
    be_admin = fc2.number_input("📋 Λογιστικά / Διοικητικά", min_value=0.0, value=float(_be_settings.get("be_admin", 0.0)), step=50.0, key="be_admin")
    be_utilities = fc1.number_input("💡 ΔΕΗ / Ρεύμα / Νερό", min_value=0.0, value=float(_be_settings.get("be_utilities", 0.0)), step=50.0, key="be_utilities")
    be_other = fc2.number_input("➕ Λοιπά Σταθερά", min_value=0.0, value=float(_be_settings.get("be_other", 0.0)), step=50.0, key="be_other")

    monthly_fixed = be_rent + be_labor + be_insurance + be_admin + be_utilities + be_other
    yearly_fixed = monthly_fixed * 12

    st.info(f"💶 **Σύνολο Σταθερών Εξόδων:** {monthly_fixed:,.2f} €/μήνα   ➜   {yearly_fixed:,.2f} €/έτος")

    if st.button("💾 Αποθήκευση Σταθερών Εξόδων"):
        try:
            supabase.table("cost_settings").upsert({
                "id": 1,
                "operational_cost": float(_be_settings.get("operational_cost") or 0.0),
                "active": bool(_be_settings.get("active", False)),
                "be_rent": be_rent, "be_labor": be_labor, "be_insurance": be_insurance,
                "be_admin": be_admin, "be_utilities": be_utilities, "be_other": be_other,
            }).execute()
            st.cache_data.clear()
            st.success("✅ Αποθηκεύτηκε!")
            st.rerun()
        except Exception as e:
            st.error(f"Σφάλμα αποθήκευσης: {e} — ίσως χρειάζεται να προστεθούν οι στήλες (δες παρακάτω).")
            st.code(
                "alter table cost_settings add column if not exists be_rent numeric not null default 0;\n"
                "alter table cost_settings add column if not exists be_labor numeric not null default 0;\n"
                "alter table cost_settings add column if not exists be_insurance numeric not null default 0;\n"
                "alter table cost_settings add column if not exists be_admin numeric not null default 0;\n"
                "alter table cost_settings add column if not exists be_utilities numeric not null default 0;\n"
                "alter table cost_settings add column if not exists be_other numeric not null default 0;",
                language="sql"
            )

    st.divider()

    # --- 2. ΠΕΡΙΘΩΡΙΟ ΣΥΝΕΙΣΦΟΡΑΣ (Contribution Margin) ---
    st.subheader("2️⃣ Περιθώριο Συνεισφοράς ανά Τεμάχιο")
    be_mode = st.radio(
        "Υπολογισμός με βάση:",
        options=["specific", "blended"],
        format_func=lambda x: "🍹 Συγκεκριμένο Κοκτέιλ" if x == "specific" else "📊 Μέσο Μείγμα Πωλήσεων (βάσει ιστορικού)",
        horizontal=True,
        key="be_mode"
    )

    contribution_margin = 0.0
    ref_price = 0.0
    calc_note = ""

    if be_mode == "specific":
        if df_rec.empty:
            st.warning("Δεν βρέθηκαν συνταγές.")
        else:
            be_choice = st.selectbox("Επίλεξε κοκτέιλ:", sorted(df_rec["Ονομα"].unique()), key="be_choice")
            r_be = df_rec[df_rec["Ονομα"] == be_choice].iloc[0]
            ref_price = float(r_be.get("Τιμή Καταλόγου", 0.0) or 0.0)
            raw_cost_be = 0.0
            for i in range(1, 14):
                ing_n = str(r_be.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                ml = float(r_be.get(f"ML{i}", 0) or 0)
                if ing_n in ["ΚΕΝΟ", "nan", "", "Νερό"] or ml <= 0:
                    continue
                match_be = df_ing[df_ing["Name"] == ing_n]
                if not match_be.empty:
                    raw_cost_be += ml * float(match_be.iloc[0].get("Τιμή/ml", 0) or 0)
            unit_cost_be = get_unit_cost_for_cocktail(be_choice, raw_cost_be)
            contribution_margin = ref_price - unit_cost_be
            calc_note = f"Τιμή {ref_price:.2f}€ − Κόστος {unit_cost_be:.2f}€ = {contribution_margin:.2f}€ ανά τεμάχιο"
    else:
        try:
            res_be_hist = supabase.table("production_log").select("cocktail_name, customer, pieces, free_pieces, discounted_pieces, discount_pct, applied_cost, lot_cocktail, prod_time, prod_date").execute()
            res_cust_be = supabase.table("customers").select("name, discount").execute()
            df_cust_be = pd.DataFrame(res_cust_be.data) if res_cust_be.data else pd.DataFrame(columns=["name", "discount"])
            if res_be_hist.data:
                # 🔧 FIX: πριν το dedup ΔΕΝ περιλάμβανε "customer" — αν το ίδιο κοκτέιλ
                # καταχωρήθηκε στην ίδια αποθήκευση για 2+ διαφορετικούς πελάτες (πολύ συχνό,
                # μιας κι ένα save μπορεί να έχει πολλούς πελάτες), κρατούσε μόνο τον έναν και
                # υποεκτιμούσε τα πραγματικά πληρωμένα τεμάχια.
                df_be_hist = pd.DataFrame(res_be_hist.data).drop_duplicates(subset=["prod_date", "prod_time", "customer", "cocktail_name", "lot_cocktail"])
                df_be_hist["pieces"] = pd.to_numeric(df_be_hist["pieces"], errors="coerce").fillna(0)
                df_be_hist["free_pieces"] = pd.to_numeric(df_be_hist.get("free_pieces", 0), errors="coerce").fillna(0)

                # 🔧 FIX: πριν χρησιμοποιούσε την ΠΛΗΡΗ τιμή καταλόγου (λιανική) για όλες τις
                # πωλήσεις, αγνοώντας τελείως την έκπτωση ανά πελάτη ΚΑΙ την ειδική έκπτωση ανά
                # παρτίδα — ακριβώς το ίδιο πρόβλημα που είχαμε βρει και διορθώσει στο Έσοδα-Έξοδα.
                # Τώρα αναπαράγει ΑΚΡΙΒΩΣ την ίδια μεθοδολογία με Dashboard/Πελατολόγιο/Έσοδα-Έξοδα.
                price_map = dict(zip(df_rec["Ονομα"], pd.to_numeric(df_rec["Τιμή Καταλόγου"], errors="coerce").fillna(0)))
                cust_discount_dict_be = dict(zip(df_cust_be["name"], pd.to_numeric(df_cust_be.get("discount", 0), errors="coerce").fillna(0))) if not df_cust_be.empty else {}

                df_be_hist["catalog_price"] = pd.to_numeric(df_be_hist["cocktail_name"].map(price_map), errors="coerce").fillna(0)
                df_be_hist["global_discount"] = pd.to_numeric(df_be_hist["customer"].map(cust_discount_dict_be), errors="coerce").fillna(0)
                df_be_hist["t_pcs"] = df_be_hist["pieces"]
                df_be_hist["s_pcs"] = pd.to_numeric(df_be_hist.get("discounted_pieces", 0), errors="coerce").fillna(0)
                df_be_hist["s_pct"] = pd.to_numeric(df_be_hist.get("discount_pct", 0), errors="coerce").fillna(0)
                df_be_hist["s_pcs"] = df_be_hist.apply(lambda r: min(r["s_pcs"], max(0, r["t_pcs"] - r["free_pieces"])), axis=1)
                df_be_hist["normal_pcs"] = df_be_hist["t_pcs"] - df_be_hist["free_pieces"] - df_be_hist["s_pcs"]

                df_be_hist["price_after_global"] = df_be_hist["catalog_price"] * (1 - (df_be_hist["global_discount"] / 100))
                df_be_hist["rev_normal"] = df_be_hist["normal_pcs"] * df_be_hist["price_after_global"]
                df_be_hist["rev_special"] = df_be_hist["s_pcs"] * df_be_hist["price_after_global"] * (1 - (df_be_hist["s_pct"] / 100))
                df_be_hist["revenue"] = (df_be_hist["rev_normal"] + df_be_hist["rev_special"]).clip(lower=0)

                df_be_hist["paid_pieces"] = df_be_hist["normal_pcs"] + df_be_hist["s_pcs"]

                # 🔧 FIX: πριν, όποτε έλειπε το applied_cost, γινόταν 0€ αντί να πέσει σε
                # εναλλακτικό υπολογισμό — υποεκτιμούσε το συνολικό κόστος, κάνοντας το
                # περιθώριο τεχνητά μεγαλύτερο και τα τεμάχια νεκρού σημείου τεχνητά λιγότερα.
                # Τώρα υπολογίζει το πραγματικό κόστος υλικών ανά συνταγή όταν λείπει —
                # ίδια λογική με το ήδη διορθωμένο Dashboard/Έσοδα-Έξοδα.
                def _be_raw_material_cost(recipe_row):
                    total = 0.0
                    for i in range(1, 14):
                        ing_n = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                        ml = float(recipe_row.get(f"ML{i}", 0) or 0)
                        if ing_n in ["ΚΕΝΟ", "nan", "", "Νερό"] or ml <= 0:
                            continue
                        match_ing_be = df_ing[df_ing["Name"] == ing_n]
                        if not match_ing_be.empty:
                            total += ml * float(match_ing_be.iloc[0].get("Τιμή/ml", 0) or 0)
                    return total

                name_to_cost_be = {}
                for _, r_be in df_rec.iterrows():
                    r_name_be = r_be["Ονομα"]
                    name_to_cost_be[r_name_be] = get_unit_cost_for_cocktail(r_name_be, _be_raw_material_cost(r_be))

                def _be_effective_cost(row):
                    ac = row.get("applied_cost")
                    if pd.notna(ac):
                        try:
                            return float(ac)
                        except (TypeError, ValueError):
                            pass
                    return name_to_cost_be.get(row["cocktail_name"], get_unit_cost_for_cocktail(row["cocktail_name"], 0.0))

                df_be_hist["effective_unit_cost"] = df_be_hist.apply(_be_effective_cost, axis=1)
                df_be_hist["cost_total"] = df_be_hist["pieces"] * df_be_hist["effective_unit_cost"]

                total_paid_pieces = df_be_hist["paid_pieces"].sum()
                total_revenue = df_be_hist["revenue"].sum()
                total_cost = df_be_hist["cost_total"].sum()
                if total_paid_pieces > 0:
                    contribution_margin = (total_revenue - total_cost) / total_paid_pieces
                    ref_price = total_revenue / total_paid_pieces
                    calc_note = f"Βάσει {int(total_paid_pieces)} πληρωμένων τεμαχίων ιστορικά (όλες οι ημερομηνίες): μέση τιμή {ref_price:.2f}€, μέσο κόστος {(total_cost/total_paid_pieces):.2f}€"

                    # 🆕 ΠΡΟΕΙΔΟΠΟΙΗΣΗ ΕΠΟΧΙΚΟΤΗΤΑΣ: το περιθώριο/τεμάχιο υπολογίζεται μόνο από
                    # τους μήνες που ήδη έχεις δεδομένα. Αν καλύπτουν λιγότερο από 12 μήνες,
                    # το πραγματικό μείγμα πωλήσεων/τιμών του χειμώνα μπορεί να διαφέρει.
                    try:
                        _be_dates = pd.to_datetime(df_be_hist["prod_date"], format="%d/%m/%Y", errors="coerce").dropna()
                        _be_months_covered = _be_dates.dt.strftime("%m/%Y").nunique()
                    except Exception:
                        _be_months_covered = None
                    if _be_months_covered and _be_months_covered < 12:
                        st.warning(
                            f"⚠️ Το περιθώριο υπολογίστηκε από δεδομένα που καλύπτουν **{_be_months_covered} μήνες** "
                            f"(όχι ολόκληρο έτος). Αν οι υπόλοιποι μήνες έχουν διαφορετικό μείγμα πωλήσεων "
                            f"(π.χ. αλλαγή σε τιμές/εκπτώσεις/πελατολόγιο τον χειμώνα), το πραγματικό ετήσιο "
                            f"περιθώριο μπορεί να διαφέρει από αυτή την εκτίμηση. Αν οι τιμές/κόστη παραμένουν "
                            f"σταθερά όλο τον χρόνο και απλά αλλάζει ο όγκος πωλήσεων, η εκτίμηση παραμένει έγκυρη."
                        )
                else:
                    st.warning("Δεν βρέθηκε αρκετό ιστορικό πωλήσεων για υπολογισμό μέσου μείγματος.")
            else:
                st.warning("Δεν βρέθηκε ιστορικό παραγωγής.")
        except Exception as e:
            st.error(f"Σφάλμα φόρτωσης ιστορικού: {e}")

    if calc_note:
        st.caption(f"🔧 {calc_note}")

    st.divider()

    # --- 3. ΑΠΟΤΕΛΕΣΜΑΤΑ ---
    st.subheader("3️⃣ Αποτέλεσμα Νεκρού Σημείου")
    if contribution_margin <= 0:
        st.error("⚠️ Το περιθώριο συνεισφοράς είναι μηδενικό ή αρνητικό — δεν υπάρχει σημείο νεκρού σημείου με τα τρέχοντα δεδομένα (χάνεις χρήματα σε κάθε τεμάχιο).")
    else:
        be_units_month = monthly_fixed / contribution_margin
        be_units_year = yearly_fixed / contribution_margin
        be_revenue_month = be_units_month * ref_price
        be_revenue_year = be_units_year * ref_price

        rc1, rc2 = st.columns(2)
        with rc1:
            st.metric("📅 Νεκρό Σημείο / Μήνα", f"{be_units_month:,.0f} τεμάχια", help=f"≈ {be_revenue_month:,.0f} € τζίρος")
            st.caption(f"≈ {be_revenue_month:,.0f} € τζίρος/μήνα")
        with rc2:
            st.metric("📆 Νεκρό Σημείο / Έτος", f"{be_units_year:,.0f} τεμάχια", help=f"≈ {be_revenue_year:,.0f} € τζίρος")
            st.caption(f"≈ {be_revenue_year:,.0f} € τζίρος/έτος")

        # --- Γράφημα Νεκρού Σημείου (μηνιαία βάση) ---
        st.divider()
        st.subheader("📉 Γράφημα Νεκρού Σημείου (μηνιαία βάση)")
        max_units = max(int(be_units_month * 2), 10)
        step = max(1, max_units // 40)
        units_range = list(range(0, max_units + step, step))
        chart_rows = []
        for u in units_range:
            chart_rows.append({"Τεμάχια": u, "Σειρά": "Συνολικό Κόστος", "Ποσό (€)": monthly_fixed + u * (ref_price - contribution_margin)})
            chart_rows.append({"Τεμάχια": u, "Σειρά": "Έσοδα", "Ποσό (€)": u * ref_price})
        df_be_chart = pd.DataFrame(chart_rows)
        fig_be = px.line(
            df_be_chart, x="Τεμάχια", y="Ποσό (€)", color="Σειρά",
            template="plotly_dark",
            color_discrete_map={"Συνολικό Κόστος": "#ff4b4b", "Έσοδα": "#00ffcc"}
        )
        fig_be.add_vline(x=be_units_month, line_dash="dash", line_color="white", annotation_text="Νεκρό Σημείο")
        st.plotly_chart(fig_be, use_container_width=True)

# --- 📑 ΑΝΑΦΟΡΑ ΕΣΟΔΩΝ - ΕΞΟΔΩΝ (P&L) ---
elif page == "📑 Έσοδα - Έξοδα":
    st.header("📑 Αναφορά Εσόδων - Εξόδων")
    st.caption("Σύνοψη πορείας της επιχείρησης: τζίρος, μεταβλητό κόστος, σταθερά έξοδα, καθαρό κέρδος — ανά μήνα ή έτος.")

    pl_period_type = st.radio("Περίοδος αναφοράς:", ["Μηνιαία", "Ετήσια"], horizontal=True, key="pl_period_type")

    try:
        res_pl = supabase.table("production_log").select("cocktail_name, customer, pieces, free_pieces, discounted_pieces, discount_pct, applied_cost, lot_cocktail, prod_time, prod_date").execute()
        df_pl_all = pd.DataFrame(res_pl.data) if res_pl.data else pd.DataFrame()
        res_cust_pl = supabase.table("customers").select("name, discount").execute()
        df_cust_pl = pd.DataFrame(res_cust_pl.data) if res_cust_pl.data else pd.DataFrame(columns=["name", "discount"])
    except Exception as e:
        st.error(f"Σφάλμα φόρτωσης ιστορικού: {e}")
        df_pl_all = pd.DataFrame()
        df_cust_pl = pd.DataFrame(columns=["name", "discount"])

    if df_pl_all.empty:
        st.warning("Δεν βρέθηκαν δεδομένα παραγωγής.")
    else:
        df_pl_all = df_pl_all.drop_duplicates(subset=["prod_date", "prod_time", "customer", "cocktail_name", "lot_cocktail"])
        df_pl_all["parsed_date"] = pd.to_datetime(df_pl_all["prod_date"], format="%d/%m/%Y", errors="coerce")
        df_pl_all = df_pl_all.dropna(subset=["parsed_date"])

        if df_pl_all.empty:
            st.warning("Δεν βρέθηκαν έγκυρες ημερομηνίες παραγωγής.")
        else:
            df_pl_all["Month_Year"] = df_pl_all["parsed_date"].dt.strftime("%m/%Y")
            df_pl_all["Year"] = df_pl_all["parsed_date"].dt.strftime("%Y")

            if pl_period_type == "Μηνιαία":
                available_periods = sorted(df_pl_all["Month_Year"].unique(), key=lambda x: pd.to_datetime(x, format="%m/%Y"), reverse=True)
                sel_period = st.selectbox("Επίλεξε μήνα:", available_periods, key="pl_month_sel")
                df_period = df_pl_all[df_pl_all["Month_Year"] == sel_period].copy()
                months_count = 1
                period_label = sel_period
            else:
                available_years = sorted(df_pl_all["Year"].unique(), reverse=True)
                sel_period = st.selectbox("Επίλεξε έτος:", available_years, key="pl_year_sel")
                df_period = df_pl_all[df_pl_all["Year"] == sel_period].copy()
                # 🔧 FIX: πριν υπέθετε ΠΑΝΤΑ 12 μήνες λειτουργίας, ακόμα κι αν η επιχείρηση
                # λειτουργούσε μόνο μέρος του έτους (π.χ. ξεκίνησε τον Μάιο) — αυτό
                # πολλαπλασίαζε τα σταθερά έξοδα σε μήνες που δεν υπήρχε καν η επιχείρηση,
                # δείχνοντας ψευδώς αρνητικό ετήσιο αποτέλεσμα. Τώρα μετράει τους
                # πραγματικούς μήνες με δεδομένα παραγωγής μέσα σε αυτό το έτος.
                months_count = df_period["Month_Year"].nunique() if not df_period.empty else 0
                period_label = sel_period
                if months_count and months_count < 12:
                    st.caption(f"ℹ️ Η επιχείρηση είχε δεδομένα παραγωγής για **{months_count} μήνες** μέσα στο {sel_period} — τα σταθερά έξοδα υπολογίζονται ×{months_count}, όχι ×12.")

            # --- ΥΠΟΛΟΓΙΣΜΟΙ ---
            # 🔧 FIX: πριν ο τζίρος υπολογιζόταν σαν πληρωμένα_τεμάχια × πλήρης τιμή καταλόγου,
            # αγνοώντας τελείως τις πραγματικές εκπτώσεις (ανά πελάτη + ειδική ανά παρτίδα).
            # Τώρα αναπαράγει ΑΚΡΙΒΩΣ τη μεθοδολογία του Dashboard/Πελατολογίου.
            recipe_price_dict_pl = dict(zip(df_rec["Ονομα"], pd.to_numeric(df_rec["Τιμή Καταλόγου"], errors="coerce").fillna(0)))
            cust_discount_dict_pl = dict(zip(df_cust_pl["name"], pd.to_numeric(df_cust_pl.get("discount", 0), errors="coerce").fillna(0))) if not df_cust_pl.empty else {}

            df_period["catalog_price"] = pd.to_numeric(df_period["cocktail_name"].map(recipe_price_dict_pl), errors="coerce").fillna(0)
            df_period["global_discount"] = pd.to_numeric(df_period["customer"].map(cust_discount_dict_pl), errors="coerce").fillna(0)

            df_period["t_pcs"] = pd.to_numeric(df_period.get("pieces", 0), errors="coerce").fillna(0)
            df_period["f_pcs"] = pd.to_numeric(df_period.get("free_pieces", 0), errors="coerce").fillna(0)
            df_period["s_pcs"] = pd.to_numeric(df_period.get("discounted_pieces", 0), errors="coerce").fillna(0)
            df_period["s_pct"] = pd.to_numeric(df_period.get("discount_pct", 0), errors="coerce").fillna(0)
            df_period["s_pcs"] = df_period.apply(lambda r: min(r["s_pcs"], max(0, r["t_pcs"] - r["f_pcs"])), axis=1)
            df_period["normal_pcs"] = df_period["t_pcs"] - df_period["f_pcs"] - df_period["s_pcs"]

            df_period["price_after_global"] = df_period["catalog_price"] * (1 - (df_period["global_discount"] / 100))
            df_period["rev_normal"] = df_period["normal_pcs"] * df_period["price_after_global"]
            df_period["rev_special"] = df_period["s_pcs"] * df_period["price_after_global"] * (1 - (df_period["s_pct"] / 100))
            df_period["revenue"] = (df_period["rev_normal"] + df_period["rev_special"]).clip(lower=0)

            # 🔧 FIX #2: πριν, το fallback κόστος (όταν λείπει το applied_cost) περνούσε
            # raw_cost=0.0 αντί για το ΠΡΑΓΜΑΤΙΚΟ κόστος υλικών της συνταγής — υποεκτιμούσε
            # δραστικά το κόστος (π.χ. έδειχνε μόνο 0,22€ αντί για πραγματικό υλικό+0,22€).
            # Τώρα υπολογίζει το πραγματικό κόστος υλικών ανά συνταγή, ΑΚΡΙΒΩΣ όπως κάνει
            # ήδη το Dashboard (name_to_cost / mat_cost_by_id).
            def _pl_raw_material_cost(recipe_row):
                total = 0.0
                for i in range(1, 14):
                    ing_n = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                    ml = float(recipe_row.get(f"ML{i}", 0) or 0)
                    if ing_n in ["ΚΕΝΟ", "nan", "", "Νερό"] or ml <= 0:
                        continue
                    match_ing_pl = df_ing[df_ing["Name"] == ing_n]
                    if not match_ing_pl.empty:
                        total += ml * float(match_ing_pl.iloc[0].get("Τιμή/ml", 0) or 0)
                return total

            name_to_cost_pl = {}
            for _, r_pl in df_rec.iterrows():
                r_name_pl = r_pl["Ονομα"]
                name_to_cost_pl[r_name_pl] = get_unit_cost_for_cocktail(r_name_pl, _pl_raw_material_cost(r_pl))

            def _pl_effective_cost(row):
                ac = row.get("applied_cost")
                if pd.notna(ac):
                    try:
                        return float(ac)
                    except (TypeError, ValueError):
                        pass
                return name_to_cost_pl.get(row["cocktail_name"], get_unit_cost_for_cocktail(row["cocktail_name"], 0.0))

            df_period["effective_unit_cost"] = df_period.apply(_pl_effective_cost, axis=1)
            df_period["paid_pieces"] = df_period["normal_pcs"] + df_period["s_pcs"]
            df_period["cost_total"] = df_period["t_pcs"] * df_period["effective_unit_cost"]

            total_revenue = float(df_period["revenue"].sum())
            total_paid_pieces = int(df_period["paid_pieces"].sum())
            total_gift_pieces = int(df_period["f_pcs"].sum())
            total_cogs = float(df_period["cost_total"].sum())
            gross_profit = total_revenue - total_cogs
            gross_margin_pct = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0

            _pl_settings = load_cost_settings() or {}
            be_rent = float(_pl_settings.get("be_rent", 0.0))
            be_labor = float(_pl_settings.get("be_labor", 0.0))
            be_insurance = float(_pl_settings.get("be_insurance", 0.0))
            be_admin = float(_pl_settings.get("be_admin", 0.0))
            be_utilities = float(_pl_settings.get("be_utilities", 0.0))
            be_other = float(_pl_settings.get("be_other", 0.0))
            monthly_fixed_pl = be_rent + be_labor + be_insurance + be_admin + be_utilities + be_other
            period_fixed = monthly_fixed_pl * months_count

            net_profit = gross_profit - period_fixed
            net_margin_pct = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

            if monthly_fixed_pl == 0:
                st.info("ℹ️ Δεν έχουν καταχωρηθεί σταθερά έξοδα στο «🎯 Νεκρό Σημείο» — το καθαρό κέρδος παρακάτω δεν τα αφαιρεί ακόμα.")

            st.divider()
            st.subheader(f"📅 Περίοδος: {period_label}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Τζίρος", f"{total_revenue:,.2f} €")
            c2.metric("🍹 Τεμάχια Πωληθέντα", f"{total_paid_pieces:,} τμχ")
            c3.metric("🎁 Δωρεάν Τεμάχια", f"{total_gift_pieces:,} τμχ")
            c4.metric("📈 Καθαρό Κέρδος (προ φόρων)", f"{net_profit:,.2f} €", delta=f"{net_margin_pct:.1f}% margin", help="Η φορολογία υπολογίζεται στο αναλυτικό breakdown παρακάτω.")

            st.divider()
            st.subheader("🧾 Αναλυτικό Έσοδα - Έξοδα")

            def pl_row(label, value, kind="expense"):
                colA, colB = st.columns([3, 1])
                if kind == "income":
                    colA.markdown(f"**{label}**")
                    colB.markdown(f":green[**+{value:,.2f} €**]")
                elif kind == "expense":
                    colA.write(label)
                    colB.markdown(f":red[{value:,.2f} €]")
                elif kind == "subtotal":
                    colA.markdown(f"*{label}*")
                    color = "green" if value >= 0 else "red"
                    colB.markdown(f":{color}[*{value:,.2f} €*]")
                elif kind == "total":
                    colA.markdown(f"### {label}")
                    color = "green" if value >= 0 else "red"
                    colB.markdown(f":{color}[**{value:,.2f} €**]")

            st.markdown("**ΕΣΟΔΑ**")
            pl_row("Τζίρος (Θεωρητικά Έσοδα)", total_revenue, "income")
            st.divider()
            st.markdown("**ΜΕΤΑΒΛΗΤΟ ΚΟΣΤΟΣ (COGS)**")
            pl_row("Κόστος Πωληθέντων", -total_cogs, "expense")
            pl_row("Μικτό Κέρδος", gross_profit, "subtotal")
            st.divider()
            st.markdown("**ΣΤΑΘΕΡΑ ΕΞΟΔΑ ΕΠΙΧΕΙΡΗΣΗΣ**")
            pl_row("Ενοίκιο", -be_rent * months_count, "expense")
            pl_row("Μισθοδοσία", -be_labor * months_count, "expense")
            pl_row("Ασφάλιστρα", -be_insurance * months_count, "expense")
            pl_row("Λογιστικά / Διοικητικά", -be_admin * months_count, "expense")
            pl_row("ΔΕΗ / Ρεύμα / Νερό", -be_utilities * months_count, "expense")
            pl_row("Λοιπά Σταθερά", -be_other * months_count, "expense")
            pl_row("Σύνολο Σταθερών Εξόδων", -period_fixed, "subtotal")
            st.divider()
            pl_row("Καθαρό Αποτέλεσμα (προ φόρων)", net_profit, "subtotal")

            # 🆕 ΦΟΡΟΛΟΓΙΑ ΕΙΣΟΔΗΜΑΤΟΣ
            tax_rate_pl = st.number_input("Συντελεστής Φόρου Εισοδήματος (%)", min_value=0.0, max_value=100.0, value=22.0, step=1.0, key="pl_tax_rate", help="Προεπιλογή 22% (τρέχων συντελεστής φορολογίας νομικών προσώπων στην Ελλάδα) — άλλαξέ το αν χρειάζεται.")
            tax_pl = max(0.0, net_profit) * (tax_rate_pl / 100)
            net_after_tax_pl = net_profit - tax_pl
            pl_row(f"Φόρος Εισοδήματος ({tax_rate_pl:.0f}%)", -tax_pl, "expense")
            pl_row("🎯 ΚΑΘΑΡΟ ΑΠΟΤΕΛΕΣΜΑ (μετά φόρων)", net_after_tax_pl, "total")
            st.caption(f"Περιθώριο Μικτού Κέρδους: {gross_margin_pct:.1f}%  |  Περιθώριο Καθαρού Κέρδους (προ φόρων): {net_margin_pct:.1f}%")

            # --- Ανάλυση ανά κοκτέιλ (προαιρετικό, extra λεπτομέρεια) ---
            with st.expander("📊 Ανάλυση ανά Κοκτέιλ (μέσα στην περίοδο)"):
                df_by_cocktail = df_period.groupby("cocktail_name", as_index=False).agg(
                    Τεμάχια=("paid_pieces", "sum"),
                    Δωρεάν=("f_pcs", "sum"),
                    Τζίρος=("revenue", "sum"),
                    Κόστος=("cost_total", "sum"),
                )
                df_by_cocktail["Κέρδος"] = df_by_cocktail["Τζίρος"] - df_by_cocktail["Κόστος"]
                st.dataframe(df_by_cocktail.sort_values("Τζίρος", ascending=False), use_container_width=True, hide_index=True)

            # --- 📄 PDF ---
            st.divider()
            try:
                now_str_pl = datetime.now(greece_tz).strftime("%d/%m/%Y %H:%M")
            except Exception:
                now_str_pl = datetime.now().strftime("%d/%m/%Y %H:%M")

            pl_pdf_data = {
                "now_str": now_str_pl,
                "total_revenue": total_revenue, "total_paid_pieces": total_paid_pieces,
                "total_gift_pieces": total_gift_pieces, "total_cogs": total_cogs,
                "gross_profit": gross_profit, "gross_margin_pct": gross_margin_pct,
                "be_rent": be_rent * months_count, "be_labor": be_labor * months_count,
                "be_insurance": be_insurance * months_count, "be_admin": be_admin * months_count,
                "be_utilities": be_utilities * months_count, "be_other": be_other * months_count,
                "period_fixed": period_fixed, "net_profit": net_profit, "net_margin_pct": net_margin_pct,
                "tax_rate": tax_rate_pl, "tax_amount": tax_pl, "net_after_tax": net_after_tax_pl,
            }
            try:
                pl_pdf_bytes = generate_pl_report_pdf(period_label, pl_pdf_data)
                st.download_button(
                    "📄 Λήψη Αναφοράς PDF",
                    data=bytes(pl_pdf_bytes),
                    file_name=f"Cabclub_Esoda_Exoda_{period_label.replace('/', '-')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Σφάλμα προετοιμασίας PDF: {e}")

elif page == "🎁 Κιβωτιακή Πολιτική":
    st.header("🎁 Κιβωτιακή Πολιτική Δώρων")
    st.caption(
        "Όρισε ανά κοκτέιλ πόσα τεμάχια έχει η κούτα και μετά από πόσες κούτες δίνεται δώρο. "
        "Αυτή η πληροφορία ελέγχεται αυτόματα στο «📦 Lot Παραγωγής» — όταν ένας πελάτης φτάνει "
        "το όριο, το σύστημα θα σε ρωτήσει αν θέλεις να προστεθεί το δώρο."
    )

    try:
        _t = supabase.table("box_gift_offers").select("cocktail_name").limit(1).execute()
        table_exists = True
    except Exception:
        table_exists = False

    if not table_exists:
        st.error("⚠️ Ο πίνακας `box_gift_offers` δεν υπάρχει ακόμα στη Supabase σου. Τρέξε το SQL παρακάτω μία φορά:")
        st.code(
            "create table if not exists box_gift_offers (\n"
            "  cocktail_name text primary key,\n"
            "  box_size int not null default 2,\n"
            "  min_boxes int not null default 10,\n"
            "  gift_boxes int not null default 1,\n"
            "  active boolean not null default true,\n"
            "  updated_at timestamptz not null default now()\n"
            ");",
            language="sql"
        )
    else:
        offers_map = load_box_gift_offers()

        st.subheader("📋 Πολιτική ανά Κοκτέιλ")
        st.caption("Ενεργοποίησε μόνο τους κωδικούς που τρέχουν αυτή τη στιγμή σε προσφορά — οι ανενεργοί δεν ελέγχονται καθόλου στο Lot Παραγωγής.")

        if df_rec.empty:
            st.warning("Δεν βρέθηκαν συνταγές.")
        else:
            table_rows = []
            for cname in sorted(df_rec["Ονομα"].unique()):
                existing = offers_map.get(cname, {})
                table_rows.append({
                    "Κοκτέιλ": cname,
                    "Ενεργή Προσφορά": bool(existing.get("active", False)),
                    "Τεμάχια/Κούτα": int(existing.get("box_size", 2)),
                    "Κούτες για Δώρο": int(existing.get("min_boxes", 10)),
                    "Κούτες Δώρου": int(existing.get("gift_boxes", 1)),
                })
            df_offers_table = pd.DataFrame(table_rows)

            edited_offers = st.data_editor(
                df_offers_table,
                column_config={
                    "Κοκτέιλ": st.column_config.TextColumn(disabled=True),
                    "Ενεργή Προσφορά": st.column_config.CheckboxColumn(),
                    "Τεμάχια/Κούτα": st.column_config.NumberColumn(min_value=1, step=1),
                    "Κούτες για Δώρο": st.column_config.NumberColumn(min_value=1, step=1),
                    "Κούτες Δώρου": st.column_config.NumberColumn(min_value=1, step=1),
                },
                hide_index=True,
                use_container_width=True,
                key="box_gift_offers_editor"
            )

            if st.button("💾 Αποθήκευση Κιβωτιακής Πολιτικής", type="primary"):
                try:
                    updates = []
                    for _, r in edited_offers.iterrows():
                        updates.append({
                            "cocktail_name": r["Κοκτέιλ"],
                            "active": bool(r["Ενεργή Προσφορά"]),
                            "box_size": int(r["Τεμάχια/Κούτα"]),
                            "min_boxes": int(r["Κούτες για Δώρο"]),
                            "gift_boxes": int(r["Κούτες Δώρου"]),
                        })
                    if updates:
                        supabase.table("box_gift_offers").upsert(updates, on_conflict="cocktail_name").execute()
                    st.cache_data.clear()
                    active_count = sum(1 for u in updates if u["active"])
                    st.success(f"✅ Αποθηκεύτηκε! {active_count} κωδικοί έχουν ενεργή προσφορά.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Σφάλμα αποθήκευσης: {e}")

elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής & Ιχνηλασιμότητα")

    # --- 🚀 PERFORMANCE FIX: πριν αυτό το block ξαναφόρτωνε ingredients/recipes/recipe_items
    # από τη βάση ΣΕ ΚΑΘΕ κλικ μέσα στην καρτέλα (κάθε επιλογή πελάτη/κοκτέιλ/τσεκ-μποξ κάνει
    # rerun). Τα df_ing/df_rec είναι ΗΔΗ φορτωμένα (cached, ttl 10-20 λεπτά) στην κορυφή του
    # αρχείου με ακριβώς την ίδια δομή — τα χρησιμοποιούμε απευθείας, χωρίς νέο query.
    # --- ΤΕΛΟΣ ΦΟΡΤΩΣΗΣ SUPABASE ---

    # 1. ΦΟΡΤΩΣΗ ΠΕΛΑΤΩΝ ΓΙΑ ΤΟ DROP-DOWN (cached — 🚀 δεν ξαναφορτώνει σε κάθε κλικ)
    customer_options = load_customer_names()

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

    # --- ΝΕΟ: ΕΚΚΡΕΜΟΤΗΤΕΣ ΠΑΡΑΓΩΓΗΣ (ΕΛΕΓΧΟΣ LOT Ή ΗΜΕΡΟΜΗΝΙΑΣ ΛΗΞΗΣ) ---
    # 🚀 PERFORMANCE FIX: πριν έτρεχε αυτό το (έως 100.000 γραμμών) query σε ΚΑΘΕ
    # κλικ στην καρτέλα. Τώρα είναι cached (90 δευτ.) μέσω load_production_log_snapshot().
    pending_data = load_production_log_snapshot()
    
    if pending_data:
        import pandas as pd
        df_all = pd.DataFrame(pending_data)
        
        cols = df_all.columns.tolist()
        cust_col = next((c for c in ["customer_name", "customer", "Πελάτης", "Customer"] if c in cols), None)
        cocktail_col = next((c for c in ["cocktail_name", "cocktail", "Ονομα", "Cocktail"] if c in cols), None)
        pcs_col = next((c for c in ["pcs", "τεμάχια", "quantity", "Quantity", "pieces"] if c in cols), None)
        
        # ΛΙΣΤΑ ΕΞΑΙΡΕΣΕΩΝ: Προαιρετικά, υλικά που δεν παίρνουν ποτέ ούτε LOT ούτε Λήξη
        exempt_ingredients = ["Κιτρικό Οξύ", "ΡΑΚΙ ΧΥΜΑ1000ML", "SMUSHED CARDAMON", "ΔΕΝΤΡΟΛΙΒΑΝΟ 0,5gr", "ΔΥΟΣΜΟΣ 0,5gr", "ΤΣΑΙ ΤΟΥ ΒΟΥΝΟΥ", "Έτοιμο Προϊόν (Στοκ)"]
        
        # 🚀 ΔΙΟΡΘΩΣΗ: Πιάνουμε το "ΝΑΙ", το "True", το "1" για το Στοκ!
        stock_mask = df_all.get("is_from_stock", "False").astype(str).str.strip().str.upper().isin(["TRUE", "ΝΑΙ", "YES", "1", "T"])
        
        # 1. Κρατάμε τα υλικά που λογικά θέλουν ιχνηλασιμότητα
        df_needs = df_all[
            (~stock_mask) & 
            (~df_all.get("ingredient_name", "").astype(str).str.contains("Έτοιμο Προϊόν", na=False)) &
            (~df_all.get("ingredient_name", "").isin(exempt_ingredients)) &
            (df_all.get("ingredient_name", "").astype(str).str.strip() != "") # Αγνοούμε εντελώς κενές γραμμές
        ]
        
        # 2. Ελέγχουμε ΠΟΤΕ λείπουν τα στοιχεία (Πρέπει να λείπουν ΚΑΙ τα δύο)
        if not df_needs.empty:
            missing_lot = df_needs["lot_number"].isna() | df_needs["lot_number"].astype(str).str.strip().isin(['', '-', 'None', 'nan', 'null'])
            
            exp_col = "expiry_date" if "expiry_date" in cols else "Ημ_Λήξης"
            if exp_col in cols:
                missing_exp = df_needs[exp_col].isna() | df_needs[exp_col].astype(str).str.strip().isin(['', '-', 'None', 'nan', 'null'])
            else:
                missing_exp = True
                
            df_missing = df_needs[missing_lot & missing_exp]
            pending_dates = df_missing["prod_date"].dropna().unique().tolist()
        else:
            pending_dates = []
        
        if pending_dates:
            try:
                from datetime import datetime
                pending_dates = sorted(list(set(pending_dates)), key=lambda x: datetime.strptime(str(x).strip(), "%d/%m/%Y"), reverse=True)
            except Exception:
                pending_dates = sorted(list(set(pending_dates)), reverse=True)
                
            # 3. Εμφάνιση μέσα σε Expander
            with st.expander(f"🚨 Εκκρεμούν LOT ή Ημ. Λήξης για {len(pending_dates)} ημέρα/ες Παραγωγής!", expanded=False):
                for p_date in pending_dates:
                    st.markdown(f"### 🗓️ Παραγωγή: {p_date}")
                    
                    df_day = df_all[df_all["prod_date"] == p_date]
                    
                    if cocktail_col:
                        if cust_col:
                            cols_to_keep = [cust_col, cocktail_col]
                            if pcs_col: cols_to_keep.append(pcs_col)
                                
                            df_orders = df_day[cols_to_keep].drop_duplicates()
                            
                            for cust, cust_group in df_orders.groupby(cust_col):
                                orders_list = []
                                for _, row in cust_group.iterrows():
                                    if pcs_col and pd.notna(row[pcs_col]):
                                        try:
                                            pcs_val = int(float(row[pcs_col]))
                                            orders_list.append(f"{row[cocktail_col]} ({pcs_val} τμχ)")
                                        except:
                                            orders_list.append(str(row[cocktail_col]))
                                    else:
                                        orders_list.append(str(row[cocktail_col]))
                                        
                                st.markdown(f"👤 **{cust}**: {', '.join(orders_list)}")
                        else:
                            cols_to_keep = [cocktail_col]
                            if pcs_col: cols_to_keep.append(pcs_col)
                                
                            df_orders = df_day[cols_to_keep].drop_duplicates()
                            cocktails_list = []
                            for _, row in df_orders.iterrows():
                                if pcs_col and pd.notna(row[pcs_col]):
                                    try:
                                        pcs_val = int(float(row[pcs_col]))
                                        cocktails_list.append(f"{row[cocktail_col]} ({pcs_val} τμχ)")
                                    except:
                                        cocktails_list.append(str(row[cocktail_col]))
                                else:
                                    cocktails_list.append(str(row[cocktail_col]))
                                    
                            st.markdown(f"🍹 **Προϊόντα:** {', '.join(cocktails_list)}")
                    else:
                        st.info("Δεν βρέθηκαν ονόματα κοκτέιλ στη βάση για αυτή την ημέρα.")
                        
                    st.divider()
        else:
            st.success("✅ Όλες οι παραγωγές είναι πλήρως εκτελεσμένες και ιχνηλάσιμες!")
    else:
        st.success("✅ Καμία εκκρεμής παραγωγή στο σύστημα.")

    st.divider()

    st.divider()
    # 1. ΚΕΝΤΡΙΚΟΣ ΟΡΙΣΜΟΣ ΗΜΕΡΟΜΗΝΙΑΣ & LOT
    col_date1, col_date2 = st.columns([2, 1])
    with col_date1:
        selected_date = st.date_input("📅 Ημερομηνία LOT", value=datetime.now(greece_tz), format="DD/MM/YYYY")
    with col_date2:
        # 🚀 Αλλάξαμε το max_chars σε 8 για να δέχεται "15" ή "15/06" ή "15/06/26"
        prod_day = st.text_input("Ημερ. Παραγωγής", value=datetime.now(greece_tz).strftime('%d'), max_chars=8)

    formatted_date = selected_date.strftime('%d/%m/%Y')
    
    # 🚀 Ο ΕΞΥΠΝΟΣ ΜΕΤΑΦΡΑΣΤΗΣ ΗΜΕΡΟΜΗΝΙΑΣ 🚀
    def get_smart_prod_date(val, base_date):
        val = str(val).strip().replace('-', '/').replace('.', '/')
        parts = val.split('/')
        y, m, d = base_date.year, base_date.month, base_date.day
        try:
            if len(parts) == 1 and parts[0]:
                d = int(parts[0])
            elif len(parts) == 2:
                d = int(parts[0])
                m = int(parts[1])
            elif len(parts) >= 3:
                d = int(parts[0])
                m = int(parts[1])
                y = int(parts[2])
                if y < 100: y += 2000
            
            from datetime import date
            return date(y, m, d).strftime('%d/%m/%Y')
        except:
            return base_date.strftime('%d/%m/%Y')

    # ΑΥΤΗ ΕΙΝΑΙ Η ΤΕΛΙΚΗ ΗΜΕΡΟΜΗΝΙΑ ΠΟΥ ΘΑ ΠΑΕΙ ΣΤΗ ΒΑΣΗ ΔΕΔΟΜΕΝΩΝ (π.χ. "02/06/2026")
    final_prod_date = get_smart_prod_date(prod_day, selected_date)

    date_lot_label = f"{formatted_date}-{prod_day}" 
    current_time = datetime.now(greece_tz).strftime('%H:%M')

    st.divider()

    # --- ΑΡΧΙΚΟΠΟΙΗΣΗ ΜΝΗΜΗΣ ---
    if "production_batch_items" not in st.session_state:
        st.session_state.production_batch_items = []
    if "daily_lots_memory" not in st.session_state:
        st.session_state.daily_lots_memory = {}
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
        
        sel_cust = c_col1.selectbox("👤 1. Επιλέξτε Πελάτη:", customer_options, index=None, placeholder="Αναζήτηση Πελάτη...", key=f"batch_cust_{reset_key}")
        
        recipe_options = list(df_rec["Ονομα"].unique())
        
        sel_cocktail = c_col2.selectbox("🍹 2. Επιλέξτε Κοκτέιλ:", recipe_options, index=None, placeholder="Αναζήτηση Κοκτέιλ...", key=f"batch_cocktail_{reset_key}")
        
        sel_pcs = c_col3.number_input("📦 3. Τεμάχια:", min_value=1, step=1, value=1, key=f"batch_pcs_{reset_key}")
        
        # --- 🚀 ΝΕΟΣ ΔΙΑΚΟΠΤΗΣ ΣΤΟΚ ---
        st_col1, st_col2 = st.columns([2, 2])
        is_from_stock = st_col1.checkbox("📦 Άντληση από έτοιμο Στοκ (Δεν αφαιρεί υλικά)", key=f"stock_check_{reset_key}")
        
        charge_stock_cost = False 
        manual_old_lot = ""
        
        if is_from_stock:
            charge_stock_cost = st_col1.checkbox("💰 Να υπολογιστεί κανονικά το κόστος στα σημερινά έξοδα;", value=False, key=f"charge_cost_{reset_key}")
            
            available_lots = []
            if sel_cocktail:
                try:
                    res_lots = supabase.table("production_log").select("lot_cocktail").eq("cocktail_name", sel_cocktail).execute()
                    if res_lots.data:
                        lots_set = set(r["lot_cocktail"] for r in res_lots.data if r.get("lot_cocktail"))
                        available_lots = sorted(list(lots_set), reverse=True)
                except Exception:
                    pass
            
            if available_lots:
                manual_old_lot = st_col2.selectbox("🔢 Επιλέξτε Παλιό LOT:", options=available_lots, key=f"old_lot_{reset_key}")
            else:
                st_col2.error(f"❌ Δεν βρέθηκε παλαιότερη παραγωγή για {sel_cocktail}!")
                manual_old_lot = ""
        
        st.write("") 
        if c_col4.button("➕ Προσθήκη", use_container_width=True, type="secondary"):
            if not sel_cust:
                st.error("⚠️ Πρέπει να επιλέξετε πρώτα Πελάτη! (αν είναι λιανική πώληση, επιλέξτε «Λιανική / Άγνωστος»)")
            elif sel_cocktail:
                if is_from_stock and not manual_old_lot.strip():
                    st.error("⚠️ Πρέπει να συμπληρώσετε το παλιό LOT του έτοιμου κοκτέιλ!")
                else:
                    stock_status = "ΝΑΙ" if is_from_stock else "ΟΧΙ"
                    lot_status = manual_old_lot.strip() if is_from_stock else "-"
                    
                    # 🚀 Βρίσκει το ΣΥΝΟΛΟ όσων υπάρχουν ήδη στο καλάθι (δεν σταματάει στο πρώτο!)
                    cart_qty = 0
                    for item in st.session_state.production_batch_items:
                        if (item["Πελάτης"] == sel_cust and 
                            item["Κοκτέιλ"] == sel_cocktail and 
                            item.get("Στοκ") == stock_status and 
                            item.get("Παλιό_LOT") == lot_status):
                            cart_qty += item["Τεμάχια"] # Προσθέτει όσα κι αν βρει

                    if cart_qty > 0:
                        st.session_state['pending_conflict'] = {
                            "cust": sel_cust, "cocktail": sel_cocktail,
                            "new_pcs": sel_pcs, "old_pcs": cart_qty,
                            "charge_cost": charge_stock_cost,
                            "is_stock": is_from_stock,
                            "old_lot": lot_status
                        }
                        st.rerun() 
                    else:
                        st.session_state.production_batch_items.append({
                            "Πελάτης": sel_cust, "Κοκτέιλ": sel_cocktail, "Τεμάχια": sel_pcs,
                            "Στοκ": stock_status,
                            "Παλιό_LOT": lot_status,
                            "Με Κόστος;": charge_stock_cost
                        })
                        st.toast(f"✅ Προστέθηκαν {sel_pcs} τμχ {sel_cocktail} {'(Από Στοκ)' if is_from_stock else ''}!")
                        st.rerun()

        # ---------------------------------------------------------
        # ΕΜΦΑΝΙΣΗ ΜΗΝΥΜΑΤΟΣ ΣΥΓΚΡΟΥΣΗΣ 
        # ---------------------------------------------------------
        if st.session_state.get('pending_conflict'):
            conf = st.session_state['pending_conflict']
            
            st.error(f"⚠️ **Προσοχή:** Το κοκτέιλ **{conf['cocktail']}** υπάρχει ήδη στο τρέχον Καλάθι για τον πελάτη **{conf['cust']}**!")
            st.write(f"📊 Ποσότητα στο Καλάθι: **{conf['old_pcs']} τμχ** | Νέα προσθήκη: **{conf['new_pcs']} τμχ**")
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            target_stock = "ΝΑΙ" if conf.get("is_stock") else "ΟΧΙ"
            target_lot = str(conf.get("old_lot", "-")).strip()
            if not target_lot or target_lot == "": 
                target_lot = "-"
            
            if col_btn1.button(f"➕ Άθροισμα (Σύνολο: {conf['old_pcs'] + conf['new_pcs']} τμχ)", type="primary"):
                # Καθαρίζει όλες τις παλιές εγγραφές από το καλάθι
                st.session_state.production_batch_items = [
                    i for i in st.session_state.production_batch_items 
                    if not (str(i.get("Πελάτης")).strip() == str(conf['cust']).strip() and 
                            str(i.get("Κοκτέιλ")).strip() == str(conf['cocktail']).strip() and 
                            str(i.get("Στοκ", "ΟΧΙ")).strip() == target_stock and 
                            str(i.get("Παλιό_LOT", "-")).strip() == target_lot)
                ]
                # Βάζει ΜΙΑ γραμμή με το σωστό άθροισμα
                st.session_state.production_batch_items.append({
                    "Πελάτης": conf['cust'], "Κοκτέιλ": conf['cocktail'], "Τεμάχια": conf['old_pcs'] + conf['new_pcs'],
                    "Στοκ": target_stock,
                    "Παλιό_LOT": target_lot,
                    "Με Κόστος;": conf.get('charge_cost', False)
                })
                st.session_state['pending_conflict'] = None
                st.toast("✅ Οι ποσότητες αθροίστηκαν επιτυχώς!")
                st.rerun()
                
            if col_btn2.button(f"📄 Προσθήκη ως 2η ξεχωριστή εγγραφή ({conf['new_pcs']} τμχ)"):
                # 🚀 ΔΕΝ διαγράφει τίποτα! Απλά προσθέτει την νέα παραγγελία ως 2η γραμμή!
                # 🔧 FIX: μοναδικό BatchTag ώστε να ΜΗΝ συγχέεται αργότερα (Split/Ιστορικό/B2B)
                # με την πρώτη γραμμή που έχει ίδιο πελάτη+κοκτέιλ+στοκ+lot.
                st.session_state['dup_batch_counter'] = st.session_state.get('dup_batch_counter', 0) + 1
                st.session_state.production_batch_items.append({
                    "Πελάτης": conf['cust'], "Κοκτέιλ": conf['cocktail'], "Τεμάχια": conf['new_pcs'],
                    "Στοκ": target_stock,
                    "Παλιό_LOT": target_lot,
                    "Με Κόστος;": conf.get('charge_cost', False),
                    "BatchTag": st.session_state['dup_batch_counter']
                })
                st.session_state['pending_conflict'] = None
                st.toast("✅ Η νέα παραγγελία προστέθηκε ξεχωριστά!")
                st.rerun()
                
            if col_btn3.button("❌ Ακύρωση"):
                st.session_state['pending_conflict'] = None
                st.rerun()
            
            st.divider()
            
            st.divider()
        selected_cocktails = []
        all_assignments = {}

        if st.session_state.production_batch_items:
            # 🚀 ΒΗΜΑ 2: Το Καλάθι μπήκε σε expander!
            with st.expander("📦 2. Στοιχεία Τρέχουσας Παρτίδας (Καλάθι Παραγγελιών)", expanded=False):
                hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([2, 2.5, 1, 1.5, 1.5, 0.5])
                hc1.caption("Πελάτης")
                hc2.caption("Κοκτέιλ")
                hc3.caption("Τεμάχια")
                hc4.caption("Στοκ (Παλιό LOT)")
                hc5.caption("Με Κόστος;")
                hc6.caption("")

                for idx, item in enumerate(st.session_state.production_batch_items):
                    c1, c2, c3, c4, c5, c6 = st.columns([2, 2.5, 1, 1.5, 1.5, 0.5])
                    c1.write(item.get("Πελάτης", ""))
                    c2.write(("🎁 " if item.get("Δώρο") else "") + str(item.get("Κοκτέιλ", "")))
                    c3.write(f"**{item.get('Τεμάχια', 0)}**")
                    
                    if item.get("Στοκ") == "ΝΑΙ":
                        c4.markdown(f"✅ Στοκ<br><span style='font-size:10px; color:gray;'>({item.get('Παλιό_LOT', '-')})</span>", unsafe_allow_html=True)
                    else:
                        c4.write("❌ Όχι")
                    
                    c5.write("✅ Ναι" if item.get("Με Κόστος;") else "❌ Όχι")
                    
                    if c6.button("🗑️", key=f"del_cart_item_{idx}_{reset_key}"):
                        st.session_state.production_batch_items.pop(idx)
                        st.toast(f"Το {item.get('Κοκτέιλ')} αφαιρέθηκε από την παρτίδα!")
                        st.rerun()
            
                st.write("")
                if st.button("🗑️ Καθαρισμός Όλης της Παρτίδας", type="secondary"):
                    st.session_state.production_batch_items = []
                    st.session_state['active_b2b_order'] = None
                    st.rerun()

            # ---------------------------------------------------------
            # 🎁 ΕΛΕΓΧΟΣ ΚΙΒΩΤΙΑΚΗΣ ΠΟΛΙΤΙΚΗΣ ΔΩΡΩΝ
            # ---------------------------------------------------------
            _box_offers = load_box_gift_offers()
            if _box_offers and st.session_state.production_batch_items:
                _cart_pairs = set(
                    (i["Πελάτης"], i["Κοκτέιλ"])
                    for i in st.session_state.production_batch_items
                    if not i.get("Δώρο")
                )
                for _cust_g, _cocktail_g in sorted(_cart_pairs):
                    _offer = _box_offers.get(_cocktail_g)
                    if not _offer:
                        continue

                    _box_size = int(_offer.get("box_size", 2))
                    _min_boxes = int(_offer.get("min_boxes", 10))
                    _gift_boxes = int(_offer.get("gift_boxes", 1))
                    if _box_size <= 0 or _min_boxes <= 0:
                        continue

                    _saved_pieces, _saved_free_pieces = 0, 0
                    try:
                        _res_saved = (
                            supabase.table("production_log")
                            .select("pieces, free_pieces, lot_cocktail, prod_time")
                            .eq("prod_date", formatted_date)
                            .eq("customer", _cust_g)
                            .eq("cocktail_name", _cocktail_g)
                            .execute()
                        )
                        if _res_saved.data:
                            _df_saved = pd.DataFrame(_res_saved.data).drop_duplicates(subset=["lot_cocktail", "prod_time"])
                            _saved_pieces = int(pd.to_numeric(_df_saved["pieces"], errors="coerce").fillna(0).sum())
                            _saved_free_pieces = int(pd.to_numeric(_df_saved.get("free_pieces", 0), errors="coerce").fillna(0).sum())
                    except Exception:
                        pass

                    _cart_normal_pieces = sum(
                        i["Τεμάχια"] for i in st.session_state.production_batch_items
                        if i["Πελάτης"] == _cust_g and i["Κοκτέιλ"] == _cocktail_g and not i.get("Δώρο")
                    )
                    _cart_gift_pieces = sum(
                        i["Τεμάχια"] for i in st.session_state.production_batch_items
                        if i["Πελάτης"] == _cust_g and i["Κοκτέιλ"] == _cocktail_g and i.get("Δώρο")
                    )

                    _total_normal_pieces = _saved_pieces - _saved_free_pieces + _cart_normal_pieces
                    _total_boxes = _total_normal_pieces // _box_size
                    _gifts_owed_boxes = (_total_boxes // _min_boxes) * _gift_boxes
                    _gifts_given_boxes = (_saved_free_pieces + _cart_gift_pieces) // _box_size

                    _pending_gift_boxes = _gifts_owed_boxes - _gifts_given_boxes
                    if _pending_gift_boxes > 0:
                        _gift_key = f"gift_offer_{_cust_g}_{_cocktail_g}".replace(" ", "_")
                        if not st.session_state.get(f"{_gift_key}_dismissed", False):
                            _gift_pcs = _pending_gift_boxes * _box_size
                            st.info(
                                f"🎁 Ο πελάτης **{_cust_g}** έφτασε τις **{_total_boxes} κούτες** του **{_cocktail_g}** "
                                f"(όριο: {_min_boxes} κούτες) και δικαιούται **{_pending_gift_boxes} δωρεάν κούτα/ες** "
                                f"({_gift_pcs} τμχ) — ημερομηνία παραγωγής {formatted_date}. Να προστεθεί το δώρο;"
                            )
                            _gcol1, _gcol2 = st.columns(2)
                            if _gcol1.button(f"✅ Ναι, πρόσθεσε {_gift_pcs} τμχ δώρο", key=f"{_gift_key}_yes"):
                                st.session_state['dup_batch_counter'] = st.session_state.get('dup_batch_counter', 0) + 1
                                st.session_state.production_batch_items.append({
                                    "Πελάτης": _cust_g, "Κοκτέιλ": _cocktail_g, "Τεμάχια": _gift_pcs,
                                    "Στοκ": "ΟΧΙ", "Παλιό_LOT": "-", "Με Κόστος;": False,
                                    "Δώρο": True,
                                    "BatchTag": st.session_state['dup_batch_counter']
                                })
                                st.toast(f"🎁 Προστέθηκε δώρο: {_gift_pcs} τμχ {_cocktail_g} για {_cust_g}!")
                                st.rerun()
                            if _gcol2.button("❌ Όχι, όχι τώρα", key=f"{_gift_key}_no"):
                                st.session_state[f"{_gift_key}_dismissed"] = True
                                st.rerun()

                    
            # Υπολογισμός all_assignments (ΑΥΤΟ ΕΙΝΑΙ ΚΡΥΦΟ, ΔΕΝ ΦΑΙΝΕΤΑΙ ΣΤΗΝ ΟΘΟΝΗ)
            for item in st.session_state.production_batch_items:
                cocktail = item["Κοκτέιλ"]
                c_name = item["Πελάτης"]
                pcs = item["Τεμάχια"]
                is_stock = item.get("Στοκ", "ΟΧΙ")
                old_lot = item.get("Παλιό_LOT", "-")
                charge_cost = item.get("Με Κόστος;", False)
                batch_tag = item.get("BatchTag", "")  # 🔧 FIX: μοναδικό αναγνωριστικό για "2η ξεχωριστή εγγραφή"/δώρο
                is_gift = item.get("Δώρο", False)
                
                if cocktail not in all_assignments:
                    all_assignments[cocktail] = pd.DataFrame(columns=["Πελάτης", "Τεμάχια", "Στοκ", "Παλιό_LOT", "Με Κόστος;", "BatchTag", "Δώρο"])
                
                new_row = pd.DataFrame([{
                    "Πελάτης": c_name, "Τεμάχια": int(pcs), 
                    "Στοκ": is_stock, "Παλιό_LOT": old_lot, 
                    "Με Κόστος;": charge_cost, "BatchTag": batch_tag, "Δώρο": is_gift
                }])
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
                # 🚀 ΕΚΡΥΨΑ ΚΑΙ ΤΟ 1β ΜΕΣΑ ΣΕ EXPANDER ΓΙΑ ΝΑ ΑΔΕΙΑΣΕΙ ΕΝΤΕΛΩΣ Η ΟΘΟΝΗ ΣΟΥ!
                with st.expander("📅 1β. Ρύθμιση LOT Έτοιμου Κοκτέιλ ανά Πελάτη", expanded=False):
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
                            "Ημέρα Παραγωγής": st.column_config.TextColumn("ΗΜΕΡΑ ΠΑΡΑΓΩΓΗΣ (Διψήφιος)", max_chars=8)
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
                # 🚀 Υπολογίζουμε Υλικά ΜΟΝΟ για τα τεμάχια που ΠΑΡΑΓΟΝΤΑΙ σήμερα (ΟΧΙ από Στοκ)
                total_qty_for_production = df_assign[df_assign["Στοκ"] == "ΟΧΙ"]["Τεμάχια"].sum() if "Στοκ" in df_assign.columns else 0
                
                if total_qty_for_production > 0:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    for i in range(1, 14):
                        ing = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                        if ing not in ["ΚΕΝΟ", "nan", "", "-", "0"]: 
                            ml_u = get_recipe_ml(recipe_row, i)
                            ing_totals[ing] = ing_totals.get(ing, 0.0) + (ml_u * total_qty_for_production)

            # 🚀 ΟΛΟ ΤΟ ΟΠΤΙΚΟ ΚΟΜΜΑΤΙ ΜΠΗΚΕ ΣΕ ΕΝΑ ΚΛΕΙΣΤΟ EXPANDER
            with st.expander("🔄 2. Συνολικά Υλικά Παραγγελίας & Γρήγορη Εκτύπωση", expanded=False):
                # 🚀 ΑΛΛΑΓΗ: 6 στήλες πλέον, για να χωρέσουν και τα 2 LOT/EXP
                mh = st.columns([2, 1.2, 1.2, 1, 1.2, 1]) 
                mh[0].caption("ΠΡΩΤΗ ΥΛΗ")
                mh[1].caption("ΣΥΝΟΛΟ")
                mh[2].caption("LOT 1")
                mh[3].caption("ΛΗΞΗ 1")
                mh[4].caption("LOT 2")
                mh[5].caption("ΛΗΞΗ 2")
                
                for ing in sorted(ing_totals.keys()):
                    total_ml = ing_totals[ing]
                    weight_g = total_ml
                    
                    if ing != "Νερό" and ing in ing_weights_map:
                        pkg_weight = ing_weights_map[ing]["weight"]
                        pkg_volume = ing_weights_map[ing]["volume"]
                        if pkg_volume > 0 and pkg_weight > 0:
                            weight_g = (pkg_weight / pkg_volume) * total_ml

                    # 🚀 ΑΛΛΑΓΗ: Εμφάνιση 2 πεδίων για LOT (mlot / mlot2) και EXP (mexp / mexp2)
                    mr = st.columns([2, 1.2, 1.2, 1, 1.2, 1])
                    mr[0].write(f"**{ing}**")
                    mr[1].write(f"**{total_ml:.2f} ml | {weight_g:.2f} g**".replace('.', ','))
                    mr[2].text_input("LOT 1", key=f"mlot_{ing}_{reset_key}", label_visibility="collapsed")
                    mr[3].text_input("EXP 1", key=f"mexp_{ing}_{reset_key}", label_visibility="collapsed")
                    mr[4].text_input("LOT 2", key=f"mlot2_{ing}_{reset_key}", label_visibility="collapsed")
                    mr[5].text_input("EXP 2", key=f"mexp2_{ing}_{reset_key}", label_visibility="collapsed")

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
                
            # --- ΒΗΜΑ 3: ΑΝΑΛΥΤΙΚΗ ΦΟΡΜΑ & ΟΡΙΣΤΙΚΟΠΟΙΗΣΗ (ΑΠΛΟΠΟΙΗΜΕΝΟ) ---
            st.markdown("### 🏷️ 3. Σύνοψη & Οριστικοποίηση Παραγγελίας")
            
            lot_entries = []
            
            with st.form(f"detailed_lot_form_{reset_key}"):
                st.info("🛒 Ελέγξτε τις παραγγελίες και πατήστε Οριστικοποίηση. (Η εισαγωγή των LOT πρώτων υλών θα γίνει μαζικά από το ειδικό εργαλείο την ημέρα της παραγωγής!)")
                
                for cocktail_name in selected_cocktails:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    df_assign = all_assignments[cocktail_name]
                    
                    total_qty_this = df_assign["Τεμάχια"].sum() if "Τεμάχια" in df_assign.columns else 0
                    qty_to_produce = df_assign[df_assign["Στοκ"] == "ΟΧΙ"]["Τεμάχια"].sum() if "Στοκ" in df_assign.columns else total_qty_this
                    qty_from_stock = total_qty_this - qty_to_produce

                    if total_qty_this == 0: continue
                    
                    # Υπολογισμός Κόστους για τα Οικονομικά
                    current_unit_cost = 0.0  # 🔧 συσσωρεύουμε ΜΟΝΟ κόστος υλικών εδώ
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
                    # 🔧 FIX: πριν ήταν hardcoded 0.22, ασύνδετο από το Κοστολόγιο· τώρα κόστος ανά κοκτέιλ
                    current_unit_cost = get_unit_cost_for_cocktail(cocktail_name, current_unit_cost)

                    # Καθαρή εμφάνιση
                    st.markdown(f"**🍹 {cocktail_name}** | Συνολικά: **{total_qty_this} τμχ** <span style='color:gray; font-size:14px;'>(Από Στοκ: {qty_from_stock} | Νέα Παραγωγή: {qty_to_produce})</span>", unsafe_allow_html=True)
                    
                    # --- ΔΗΜΙΟΥΡΓΙΑ ΕΓΓΡΑΦΩΝ ΓΙΑ ΒΑΣΗ ΔΕΔΟΜΕΝΩΝ ---
                    for _, row_assign in df_assign.iterrows():
                        c_name = str(row_assign.get("Πελάτης", "Λιανική / Άγνωστος")).strip()
                        if not c_name: c_name = "Λιανική / Άγνωστος"
                        c_qty = int(row_assign.get("Τεμάχια", 0))
                        is_stock = row_assign.get("Στοκ", "ΟΧΙ")
                        old_lot = row_assign.get("Παλιό_LOT", "-")
                        # 🔧 FIX: αν αυτή η γραμμή προήλθε από "2η ξεχωριστή εγγραφή", προσθέτουμε
                        # μοναδικό suffix στο lot_cocktail ώστε ΝΑ ΜΗΝ συγχέεται (σε Split, Ιστορικό,
                        # ή στη σύνοψη B2B) με την πρώτη γραμμή που έχει τα ίδια πελάτης/κοκτέιλ/lot.
                        # Για ΟΛΕΣ τις κανονικές εγγραφές (χωρίς BatchTag) καμία αλλαγή συμπεριφοράς.
                        _btag = row_assign.get("BatchTag", "")
                        _btag_suffix = f"-B{int(_btag)}" if _btag not in ("", None) and pd.notna(_btag) else ""
                        # 🎁 Αν είναι δώρο κιβωτιακής πολιτικής, ΟΛΑ τα τεμάχια της γραμμής μετράνε
                        # ως free_pieces — δεν χρεώνονται στον πελάτη (τζίρος 0), αλλά αφαιρούν
                        # κανονικά απόθεμα (πραγματικό προϊόν φεύγει από την αποθήκη).
                        _is_gift_row = bool(row_assign.get("Δώρο", False))
                        _free_pcs = c_qty if _is_gift_row else 0
                        
                        c_config = cust_lot_config_map.get(c_name, {
                            "prod_date": formatted_date, 
                            "lot_cocktail": date_lot_label
                        })
                        
                        if c_qty > 0:
                            charge_cost = row_assign.get("Με Κόστος;", False) if 'row_assign' in locals() else False
                            
                            if is_stock == "ΝΑΙ":
                                final_cost = round(current_unit_cost, 4) if charge_cost else 0.0
                                lot_entries.append({
                                    "prod_date": c_config["prod_date"], 
                                    "prod_time": current_time, 
                                    "customer": c_name,
                                    "cocktail_name": cocktail_name, 
                                    "lot_cocktail": f"{old_lot}{_btag_suffix}", 
                                    "pieces": c_qty,
                                    "free_pieces": _free_pcs,
                                    "ingredient_name": "📦 Έτοιμο Προϊόν (Στοκ)", 
                                    "total_ml": 0.0, 
                                    "target_g": 0.0,
                                    "lot_number": old_lot, 
                                    "expiry_date": "-",
                                    "unit_cost": round(current_unit_cost, 4),
                                    "applied_cost": final_cost,
                                    "is_from_stock": True
                                })
                            else:
                                for i in range(1, 14):
                                    ing = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                                    if ing in ["ΚΕΝΟ", "nan", "Νερό", ""]: continue
                                    
                                    ml_u = get_recipe_ml(recipe_row, i)
                                    match_ing = df_ing[df_ing["Name"] == ing]
                                    
                                    lot_entries.append({
                                        "prod_date": c_config["prod_date"], 
                                        "prod_time": current_time, 
                                        "customer": c_name,
                                        "cocktail_name": cocktail_name, 
                                        "lot_cocktail": f"{c_config['lot_cocktail']}{_btag_suffix}", 
                                        "pieces": c_qty,
                                        "free_pieces": _free_pcs,
                                        "ingredient_name": ing, 
                                        "total_ml": float(ml_u * c_qty), 
                                        "target_g": round(float((ml_u * c_qty) / match_ing.iloc[0]["Volume"] * match_ing.iloc[0]["Weight_Full"]), 1) if not match_ing.empty else float(ml_u * c_qty),
                                        "lot_number": "-", # ΚΕΝΟ ΓΙΑ ΝΑ ΣΥΜΠΛΗΡΩΘΕΙ ΜΕΤΑ!
                                        "expiry_date": "-",
                                        "unit_cost": round(current_unit_cost, 4),
                                        "applied_cost": round(current_unit_cost, 4),
                                        "is_from_stock": False
                                    })
                
                st.divider()
                if st.form_submit_button("💾 Οριστικοποίηση & Αποθήκευση στο Cloud", type="primary"):
                    if lot_entries:
                        try:
                            # 1. Αποθήκευση όλων των νέων εγγραφών
                            supabase.table("production_log").insert(lot_entries).execute()
                            
                            # 2. ΑΦΑΙΡΕΣΗ ΥΛΙΚΩΝ ΑΠΟ ΑΠΟΘΗΚΗ - ΕΞΑΙΡΟΥΝΤΑΙ ΤΑ ΣΤΟΚ!
                            # 🚀 PERFORMANCE FIX: πριν γινόταν select+update ΑΝΑ ΥΛΙΚΟ ΑΝΑ
                            # ΚΟΚΤΕΪΛ (δεκάδες διαδοχικά network calls). Τώρα υπολογίζουμε όλες
                            # τις αφαιρέσεις ΣΤΗ ΜΝΗΜΗ και τις στέλνουμε με ΕΝΑ batch call.
                            deductions = {}
                            for item in st.session_state.production_batch_items:
                                if item.get("Στοκ", "ΟΧΙ") == "ΟΧΙ":
                                    compute_inventory_deductions(item["Κοκτέιλ"], item["Τεμάχια"], df_rec, deductions)
                            inv_ok, inv_failed = commit_inventory_deductions(deductions)
                            if not inv_ok:
                                st.warning(f"⚠️ Δεν ενημερώθηκε αυτόματα το απόθεμα για: {', '.join(inv_failed)}. Ελέγξτε χειροκίνητα στην Αποθήκη.")
                            
                            # 3. ΣΥΓΧΩΝΕΥΣΗ B2B ΟΙΚΟΝΟΜΙΚΩΝ
                            all_recipes_res = supabase.table("recipes").select("name, catalog_price").execute()
                            all_customers_res = supabase.table("customers").select("name, discount").execute()
                            
                            recipe_prices = {r['name']: float(r.get('catalog_price') or 0.0) for r in all_recipes_res.data} if all_recipes_res.data else {}
                            customer_discounts = {c['name']: float(c.get('discount') or 0.0) for c in all_customers_res.data} if all_customers_res.data else {}

                            b2b_customers = set((e["customer"], e["prod_date"]) for e in lot_entries)
                            
                            from datetime import datetime
                            for cust, pdate in b2b_customers:
                                if cust == "Λιανική / Άγνωστος": continue
                                
                                today_logs = supabase.table("production_log").select("cocktail_name, pieces, free_pieces, discounted_pieces, discount_pct, lot_cocktail, prod_time").eq("prod_date", pdate).eq("customer", cust).execute()
                                
                                try: date_iso = datetime.strptime(pdate, "%d/%m/%Y").strftime("%Y-%m-%d")
                                except ValueError: date_iso = selected_date.isoformat() 
                                    
                                existing_order = find_existing_b2b_order(cust, date_iso)
                                
                                if today_logs.data:
                                    import pandas as pd
                                    df_logs = pd.DataFrame(today_logs.data)
                                    df_logs = df_logs.fillna(0)
                                    df_logs = df_logs.drop_duplicates(subset=["cocktail_name", "lot_cocktail", "prod_time"])
                                    
                                    unique_cocktails = {}
                                    for _, row in df_logs.iterrows():
                                        c_name = row["cocktail_name"]
                                        if c_name not in unique_cocktails:
                                            unique_cocktails[c_name] = {"pcs": 0, "free": 0, "s_pcs": 0, "s_pct": 0.0}
                                        
                                        unique_cocktails[c_name]["pcs"] += int(row.get("pieces") or 0)
                                        # 🔧 FIX: πριν έπαιρνε max() — αν ο πελάτης πάρει 2 ξεχωριστά δώρα την
                                        # ίδια μέρα παραγωγής (2 διαφορετικές παρτίδες), το ένα χανόταν.
                                        # Τώρα αθροίζει, όπως ακριβώς κάνει και το "pcs" παραπάνω.
                                        unique_cocktails[c_name]["free"] += int(row.get("free_pieces") or 0)
                                        unique_cocktails[c_name]["s_pcs"] = max(unique_cocktails[c_name]["s_pcs"], int(row.get("discounted_pieces") or 0))
                                        unique_cocktails[c_name]["s_pct"] = max(unique_cocktails[c_name]["s_pct"], float(row.get("discount_pct") or 0.0))
                                        
                                    total_amount = 0.0
                                    details_lines = []
                                    for cockt, data in unique_cocktails.items():
                                        price = recipe_prices.get(cockt, 0.0)
                                        
                                        t_pcs = data["pcs"]
                                        f_pcs = data["free"]
                                        s_pcs = min(data["s_pcs"], max(0, t_pcs - f_pcs))
                                        normal_pcs = max(0, t_pcs - f_pcs - s_pcs)
                                        
                                        cost_normal = normal_pcs * price
                                        cost_special = s_pcs * price * (1 - (data["s_pct"] / 100.0))
                                        
                                        total_amount += (cost_normal + cost_special)
                                        
                                        line = f"• {t_pcs} τμχ {cockt}"
                                        if f_pcs > 0 or s_pcs > 0:
                                            extras = []
                                            if f_pcs > 0: extras.append(f"{f_pcs} Δώρο")
                                            if s_pcs > 0: extras.append(f"{s_pcs} με -{data['s_pct']}%")
                                            line += f" (Εκ των οποίων: {', '.join(extras)})"
                                            
                                        details_lines.append(line)
                                        
                                    discount = customer_discounts.get(cust, 0.0)
                                    final_total = total_amount * (1 - (discount / 100))
                                    
                                    details_str = "\n".join(details_lines)
                                    if discount > 0:
                                        details_str += f"\n\n[Αρχική Αξία: {total_amount:.2f}€ | Έκπτωση CRM: {discount}%]"
                                        
                                    if existing_order:
                                        supabase.table("b2b_orders").update({
                                            "total_amount": round(final_total, 2),
                                            "order_details": details_str,
                                            "status": "ΟΛΟΚΛΗΡΩΘΗΚΕ"
                                        }).eq("id", existing_order["id"]).execute()
                                    else:
                                        supabase.table("b2b_orders").insert({
                                            "customer_name": cust, "total_amount": round(final_total, 2),
                                            "order_details": details_str, "status": "ΟΛΟΚΛΗΡΩΘΗΚΕ",
                                            "created_at": f"{date_iso}T{current_time}:00"
                                        }).execute()
                                else:
                                    if existing_order:
                                        supabase.table("b2b_orders").delete().eq("id", existing_order["id"]).execute()
                            
                            st.session_state.production_batch_items = []
                            st.session_state['active_b2b_order'] = None 
                            st.session_state['lot_reset_key'] += 1
                            st.session_state.pop('search_data_loaded', None)
                            st.cache_data.clear()  # 🚀 ώστε το cached απόθεμα/εκκρεμότητες να δείξουν αμέσως τα νέα δεδομένα
                            st.success("✅ Η παραγγελία αποθηκεύτηκε πανεύκολα!")
                            st.rerun()
                        except Exception as save_err:
                            st.error(f"Σφάλμα κατά την αποθήκευση: {save_err}")

    # =========================================================================
    # ΕΡΓΑΛΕΙΟ ΕΡΓΑΣΤΗΡΙΟΥ: ΜΑΖΙΚΗ ΚΑΤΑΧΩΡΗΣΗ LOT ΠΡΩΤΩΝ ΥΛΩΝ
    # =========================================================================
    st.divider()
    with st.expander("🧪 Εργαστήριο: Μαζική Καταχώρηση LOT Πρώτων Υλών", expanded=False):
        st.info("Επιλέξτε την ημέρα παραγωγής για να καταχωρήσετε μαζικά τα LOT των υλικών που χρησιμοποιήσατε. (Τα κοκτέιλ από Στοκ προστατεύονται και δεν επηρεάζονται).")

        res_dates = supabase.table("production_log").select("prod_date, is_from_stock, ingredient_name").execute()
        
        if res_dates.data:
            import pandas as pd
            from datetime import datetime
            
            valid_dates = [
                r["prod_date"] for r in res_dates.data 
                if str(r.get("is_from_stock", "False")).lower() != "true" 
                and "Έτοιμο Προϊόν" not in str(r.get("ingredient_name", ""))
            ]
            
            valid_dates = [d for d in valid_dates if d and str(d).strip() not in ["-", ""]]
            
            try:
                all_dates = sorted(
                    list(set(valid_dates)),
                    key=lambda x: datetime.strptime(str(x).strip(), "%d/%m/%Y"),
                    reverse=True
                )
            except Exception:
                all_dates = sorted(list(set(valid_dates)), reverse=True)
                
            sel_prep_date = st.selectbox("📅 Ημερομηνία Παραγωγής:", ["-- Επιλέξτε Ημερομηνία --"] + all_dates)
            
            if sel_prep_date != "-- Επιλέξτε Ημερομηνία --":
                res_mats = supabase.table("production_log").select("id, ingredient_name, total_ml, target_g, lot_number, expiry_date, is_from_stock").eq("prod_date", sel_prep_date).execute()
                
                if res_mats.data:
                    valid_mats = [
                        r for r in res_mats.data 
                        if str(r.get("is_from_stock", "False")).lower() != "true" 
                        and "Έτοιμο Προϊόν" not in str(r.get("ingredient_name", ""))
                    ]
                    
                    if valid_mats:
                        df_mats = pd.DataFrame(valid_mats)
                        df_grouped = df_mats.groupby("ingredient_name").agg({
                            "total_ml": "sum",
                            "target_g": "sum",
                            "lot_number": "first",
                            "expiry_date": "first"
                        }).reset_index()
                        
                        # --- 🚀 ΝΕΟ: ΕΞΥΠΝΗ ΑΝΑΖΗΤΗΣΗ ΤΕΛΕΥΤΑΙΟΥ ΠΡΑΓΜΑΤΙΚΟΥ LOT ΜΕΣΩ PYTHON ---
                        historical_lots = {}
                        try:
                            ing_names = df_grouped["ingredient_name"].tolist()
                            
                            hist_res = supabase.table("production_log") \
                                .select("id, ingredient_name, lot_number, expiry_date") \
                                .in_("ingredient_name", ing_names) \
                                .order("id", desc=True) \
                                .limit(2000) \
                                .execute()
                            
                            if hist_res.data:
                                for r in hist_res.data:
                                    ing_hist = r["ingredient_name"]
                                    lot_hist = str(r.get("lot_number", "")).strip()
                                    exp_hist = str(r.get("expiry_date", "")).strip()
                                    
                                    if ing_hist not in historical_lots:
                                        if lot_hist and lot_hist.lower() not in ("-", "none", "nan", "", "null"):
                                            historical_lots[ing_hist] = {
                                                "lot": lot_hist,
                                                "exp": exp_hist
                                            }
                        except Exception as e:
                            pass
                        # ---------------------------------------------------------

                        # =========================================================
                        # 📱 ΚΑΜΕΡΑ AI ΓΙΑ ΣΚΑΝΑΡΙΣΜΑ ΜΕ GEMINI VISION
                        # =========================================================
                        st.write("### 📷 Σάρωση Ετικέτας με Κάμερα")
                        scannable_ings = ["-- Επιλέξτε Υλικό προς Σάρωση --"] + df_grouped["ingredient_name"].tolist()
                        scan_target = st.selectbox("Επιλέξτε πρώτη ύλη και ανοίξτε την κάμερα:", scannable_ings)
                        
                        if scan_target != "-- Επιλέξτε Υλικό προς Σάρωση --":
                            picture = st.camera_input(f"Φωτογραφίστε το LOT: {scan_target}")
                            
                            if picture:
                                with st.spinner("🤖 Το AI διαβάζει την ετικέτα..."):
                                    import google.generativeai as genai
                                    from PIL import Image
                                    import json
                                    
                                    try:
                                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                                        
                                        img = Image.open(picture)
                                        
                                        # 🚀 Εδώ βάλαμε ακριβώς το μοντέλο που είδαμε στην οθόνη σου!
                                        model = genai.GenerativeModel('gemini-2.0-flash')
                                        
                                        prompt = """
                                        Είσαι βοηθός αποθήκης. Διάβασε αυτή την ετικέτα. 
                                        Βρες τον αριθμό παρτίδας (LOT ή L.) και την ημερομηνία λήξης (EXP ή BBD).
                                        Επίστρεψε ΑΥΣΤΗΡΑ ΚΑΙ ΜΟΝΟ ένα JSON, χωρίς κανένα άλλο κείμενο.
                                        Μορφή: {"lot": "ΤΟ_ΝΟΥΜΕΡΟ", "exp": "Η_ΗΜΕΡΟΜΗΝΙΑ"}
                                        Αν δεν βρεις κάτι, βάλε την παύλα "-".
                                        """
                                        
                                        response = model.generate_content([prompt, img])
                                        
                                        clean_response = response.text.strip()
                                        if clean_response.startswith("```json"):
                                            clean_response = clean_response.replace("```json", "").replace("```", "").strip()
                                        elif clean_response.startswith("```"):
                                            clean_response = clean_response.replace("```", "").strip()
                                            
                                        ai_data = json.loads(clean_response)
                                        
                                        if "scanned_lots" not in st.session_state:
                                            st.session_state.scanned_lots = {}
                                        
                                        st.session_state.scanned_lots[scan_target] = {
                                            "lot": ai_data.get("lot", "-"), 
                                            "exp": ai_data.get("exp", "-")
                                        }
                                        st.success(f"✅ Επιτυχής Ανάγνωση! (LOT: {ai_data.get('lot', '-')} | Λήξη: {ai_data.get('exp', '-')})")
                                        
                                    except Exception as e:
                                        st.error(f"Αποτυχία: {e}")
                        # =========================================================

                        with st.form("bulk_lot_entry_form"):
                            st.write(f"### Συγκεντρωτικά Υλικά για την παραγωγή της {sel_prep_date}")
                            
                            updated_lots = {}
                            
                            h1, h2, h3, h4, h5, h6 = st.columns([2, 1, 1.2, 1, 1.2, 1])
                            h1.caption("Πρώτη Ύλη")
                            h2.caption("Συνολικά ml")
                            h3.caption("LOT 1")
                            h4.caption("Ημ. Λήξης 1")
                            h5.caption("LOT 2")
                            h6.caption("Ημ. Λήξης 2")
                            
                            for _, row in df_grouped.iterrows():
                                ing = row["ingredient_name"]
                                c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1.2, 1, 1.2, 1])
                                
                                c1.write(f"**{ing}**")
                                c2.write(f"{row['total_ml']:.0f} ml")
                                
                                old_lot_full = str(row['lot_number']) if row['lot_number'] and str(row['lot_number']).strip() not in ("-", "None", "nan") else ""
                                old_exp_full = str(row['expiry_date']) if row['expiry_date'] and str(row['expiry_date']).strip() not in ("-", "None", "nan") else ""
                                
                                if not old_lot_full and ing in historical_lots:
                                    old_lot_full = historical_lots[ing]["lot"]
                                    old_exp_full = historical_lots[ing]["exp"]
                                
                                if "scanned_lots" in st.session_state and ing in st.session_state.scanned_lots:
                                    old_lot_full = st.session_state.scanned_lots[ing]["lot"]
                                    old_exp_full = st.session_state.scanned_lots[ing]["exp"]
                                
                                def_lot1, def_lot2 = (old_lot_full.split(" / ", 1) + [""])[:2] if " / " in old_lot_full else (old_lot_full, "")
                                def_exp1, def_exp2 = (old_exp_full.split(" / ", 1) + [""])[:2] if " / " in old_exp_full else (old_exp_full, "")
                                
                                safe_date_key = sel_prep_date.replace("/", "_")
                                
                                n_lot1 = c3.text_input("LOT1", value=def_lot1.strip(), key=f"blot1_{ing}_{safe_date_key}", label_visibility="collapsed")
                                n_exp1 = c4.text_input("EXP1", value=def_exp1.strip(), key=f"bexp1_{ing}_{safe_date_key}", label_visibility="collapsed")
                                n_lot2 = c5.text_input("LOT2", value=def_lot2.strip(), key=f"blot2_{ing}_{safe_date_key}", label_visibility="collapsed")
                                n_exp2 = c6.text_input("EXP2", value=def_exp2.strip(), key=f"bexp2_{ing}_{safe_date_key}", label_visibility="collapsed")
                                
                                final_lot = f"{n_lot1.strip()} / {n_lot2.strip()}" if n_lot2.strip() else n_lot1.strip()
                                final_exp = f"{n_exp1.strip()} / {n_exp2.strip()}" if n_exp2.strip() else n_exp1.strip()
                                
                                updated_lots[ing] = {
                                    "lot": final_lot if final_lot else "-", 
                                    "exp": final_exp if final_exp else "-"
                                }
                            
                            if st.form_submit_button("💾 Αποθήκευση LOT στην Παραγωγή", type="primary"):
                                with st.spinner("Γίνεται αστραπιαία μαζική ενημέρωση..."):
                                    try:
                                        full_rows_res = supabase.table("production_log").select("*").eq("prod_date", sel_prep_date).execute()
                                        
                                        if full_rows_res.data:
                                            bulk_data = []
                                            for r in full_rows_res.data:
                                                ing_name = r.get("ingredient_name")
                                                
                                                if str(r.get("is_from_stock", "False")).lower() != "true" and ing_name in updated_lots:
                                                    updated_row = r.copy()
                                                    updated_row["lot_number"] = updated_lots[ing_name]["lot"]
                                                    updated_row["expiry_date"] = updated_lots[ing_name]["exp"]
                                                    bulk_data.append(updated_row)
                                            
                                            if bulk_data:
                                                supabase.table("production_log").upsert(bulk_data).execute()
                                        
                                        if "scanned_lots" in st.session_state:
                                            del st.session_state["scanned_lots"]
                                            
                                        st.success("✅ Όλα τα LOT καταχωρήθηκαν επιτυχώς σε κλάσματα δευτερολέπτου!")
                                        import time
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Σφάλμα κατά την αποθήκευση: {e}")
                    else:
                        st.info("Όλα τα κοκτέιλ αυτής της ημερομηνίας ήταν από Στοκ, δεν υπάρχουν πρώτες ύλες για συμπλήρωση.")
                else:
                    st.info("Δεν βρέθηκαν υλικά προς παρασκευή για αυτή την ημερομηνία.")
                            
    # --- 4. ΙΣΤΟΡΙΚΟ & ΔΙΑΧΕΙΡΙΣΗ ---
    st.divider()
    st.subheader("📂 Ιστορικό Παραγωγής & Διαχείριση Παραγγελιών")
    
    res_log = supabase.table("production_log").select("*").order("prod_date", desc=True).execute()
    
    if res_log.data:
        raw_data = res_log.data
        
        # 🚀 VIRTUAL JOIN: "Ανοίγουμε" το Στοκ για να φαίνονται τα υλικά του στην οθόνη
        original_productions = {}
        
        # Πέρασμα 1: Αποθηκεύουμε τα αυθεντικά υλικά (Με έξυπνο κόφτη διπλοτυπιών!)
        for row in raw_data:
            if row.get("ingredient_name") and "Έτοιμο Προϊόν" not in str(row.get("ingredient_name")):
                key = (row.get("cocktail_name"), str(row.get("lot_cocktail")).strip())
                if key not in original_productions:
                    original_productions[key] = {} # 🚀 Χρησιμοποιούμε Λεξικό (Dict) για να φιλτράρουμε τα διπλά
                
                ing_name = row.get("ingredient_name")
                # Αν το υλικό δεν υπάρχει ήδη στη λίστα για αυτό το LOT, το προσθέτουμε. Αν υπάρχει, το αγνοούμε!
                if ing_name not in original_productions[key]:
                    original_productions[key][ing_name] = row
                
        # Πέρασμα 2: Αντικαθιστούμε το 1 "Στοκ" με τα πραγματικά του υλικά για την προβολή
        display_data = []
        for row in raw_data:
            if row.get("ingredient_name") == "📦 Έτοιμο Προϊόν (Στοκ)":
                key = (row.get("cocktail_name"), str(row.get("lot_cocktail")).strip())
                if key in original_productions and len(original_productions[key]) > 0:
                    for orig_ing in original_productions[key].values(): # 🚀 Τραβάει μόνο τα μοναδικά υλικά!
                        new_row = row.copy()
                        new_row["ingredient_name"] = orig_ing.get("ingredient_name")
                        new_row["lot_number"] = orig_ing.get("lot_number")
                        new_row["expiry_date"] = orig_ing.get("expiry_date")
                        new_row["total_ml"] = 0.0 
                        new_row["target_g"] = 0.0
                        display_data.append(new_row)
                else:
                    display_data.append(row)
            else:
                display_data.append(row)

        df_all_logs = pd.DataFrame(display_data)
        df_all_logs_renamed = df_all_logs.rename(columns={
            "prod_date": "Ημερομηνία", "prod_time": "Ώρα", "customer": "Πελάτης", "cocktail_name": "Cocktail",
            "lot_cocktail": "LOT_Cocktail", "pieces": "Τεμάχια", "ingredient_name": "Υλικό",
            "total_ml": "Σύνολο_ML", "target_g": "Στόχος_Γραμμάρια", "lot_number": "Lot Number", "expiry_date": "Ημ_Λήξης"
        })

        # --- 1. ΝΕΑ ΚΑΘΑΡΑ ΦΙΛΤΡΑ ---
        st.markdown("### 🔍 1. Φίλτρα Αναζήτησης")
        
        raw_dates = df_all_logs_renamed["Ημερομηνία"].dropna().unique().tolist()
        def safe_date_sort(d):
            try: return pd.to_datetime(str(d).strip(), dayfirst=True)
            except: return pd.to_datetime("1900-01-01")
        all_dates = sorted(raw_dates, key=safe_date_sort, reverse=True)
        
        col_f1, col_f2, col_f3 = st.columns(3)
        sel_hist_date = col_f1.selectbox("📅 Ημερομηνία:", options=["-- Όλες οι Ημερομηνίες --"] + list(all_dates))
        
        cust_options = ["-- Όλοι οι Πελάτες --"] + sorted(list(df_all_logs_renamed["Πελάτης"].dropna().unique()))
        sel_customer = col_f2.selectbox("👤 Πελάτης:", options=cust_options)

        cocktail_options = ["-- Όλα τα Cocktails --"] + sorted(list(df_all_logs_renamed["Cocktail"].dropna().unique()))
        sel_cocktail = col_f3.selectbox("🍹 Cocktail:", options=cocktail_options)

        df_filtered = df_all_logs_renamed.copy()
        if sel_hist_date != "-- Όλες οι Ημερομηνίες --": df_filtered = df_filtered[df_filtered["Ημερομηνία"] == sel_hist_date]
        if sel_customer != "-- Όλοι οι Πελάτες --": df_filtered = df_filtered[df_filtered["Πελάτης"] == sel_customer]
        if sel_cocktail != "-- Όλα τα Cocktails --": df_filtered = df_filtered[df_filtered["Cocktail"] == sel_cocktail]

        df_past = df_filtered.copy() # Κρατάμε το αντίγραφο για τις εκτυπώσεις!

        # --- 1Β. ΜΑΖΙΚΗ ΑΛΛΑΓΗ LOT ΠΑΡΑΓΩΓΗΣ (BULK EDIT) ---
        st.divider()
        with st.expander("⏱️ Μαζική Αλλαγή LOT Παραγωγής", expanded=False):
            st.info("Επιλέξτε ποια ΚΟΚΤΕΙΛ (συνολική παραγωγή ημέρας) θέλετε να ενημερώσετε με νέο LOT. Το σύστημα θα αλλάξει αυτόματα το LOT σε όλες τις επιμέρους παραγγελίες πελατών!")
            
            if not df_filtered.empty:
                # 🚀 Η ΜΑΓΙΚΗ ΑΣΠΙΔΑ: Κρατάμε ΑΥΣΤΗΡΑ μόνο όσα έχουν ml > 0 (δηλαδή τις πραγματικές Νέες Παραγωγές)!
                df_only_new_production = df_filtered[df_filtered["Σύνολο_ML"] > 0]
                
                if not df_only_new_production.empty:
                    # 🚀 ΑΛΛΑΓΗ: Ομαδοποίηση ΜΟΝΟ ανά Ημερομηνία, Κοκτέιλ και Παλιό LOT (αγνοούμε Πελάτη/Ώρα)!
                    bulk_groups = df_only_new_production.groupby(["Ημερομηνία", "Cocktail", "LOT_Cocktail"])
                    bulk_options = []
                    bulk_map = {}
                    
                    for name, group in bulk_groups:
                        o_date, o_cocktail, o_lot = name
                        
                        # Υπολογίζουμε τα συνολικά τεμάχια της ημέρας για αυτό το κοκτέιλ (αγνοώντας τις διπλές γραμμές υλικών)
                        tot_pcs = group.drop_duplicates(subset=["Πελάτης", "Ώρα"])["Τεμάχια"].sum()
                        
                        lbl = f"📅 {o_date} | 🍹 {o_cocktail} | Παλιό LOT: {o_lot} | ({int(tot_pcs)} συνολικά τμχ)"
                        bulk_options.append(lbl)
                        bulk_map[lbl] = {
                            "date": o_date, 
                            "cocktail": o_cocktail, 
                            "old_lot": o_lot
                        }
                    
                    sel_bulk = st.multiselect("Επιλέξτε Κοκτέιλ (Συνολική Παραγωγή) για αλλαγή LOT:", bulk_options)
                    
                    col_b1, col_b2 = st.columns([1.5, 2])
                    new_bulk_lot = col_b1.text_input("Νέο LOT Παραγωγής:", placeholder="π.χ. ZMB-15/06 ή 15/06/2026-31", key="bulk_lot_input")
                    
                    if col_b2.button("💾 Εφαρμογή Νέου LOT", type="primary"):
                        if sel_bulk and new_bulk_lot.strip():
                            with st.spinner("Ενημέρωση LOT στη βάση δεδομένων..."):
                                try:
                                    for lbl in sel_bulk:
                                        b_date = bulk_map[lbl]["date"]
                                        b_cocktail = bulk_map[lbl]["cocktail"]
                                        b_old_lot = bulk_map[lbl]["old_lot"]
                                        
                                        # 🚀 ΑΛΛΑΓΗ: Ενημερώνει ΑΚΑΡΙΑΙΑ όλες τις γραμμές αυτού του κοκτέιλ ανεξαρτήτως πελάτη!
                                        supabase.table("production_log").update({"lot_cocktail": new_bulk_lot.strip()}).eq("prod_date", b_date).eq("cocktail_name", b_cocktail).eq("lot_cocktail", b_old_lot).execute()
                                    
                                    st.session_state.pop('search_data_loaded', None)
                                    st.success("✅ Το LOT Παραγωγής άλλαξε επιτυχώς σε όλες τις παραγγελίες των επιλεγμένων κοκτέιλ!")
                                    import time
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as save_err:
                                    st.error(f"Σφάλμα κατά την αποθήκευση: {save_err}")
                        else:
                            st.warning("Παρακαλώ επιλέξτε τουλάχιστον ένα κοκτέιλ και γράψτε το Νέο LOT.")
                else:
                    st.info("Όλα τα αποτελέσματα της αναζήτησης προέρχονται από έτοιμο Στοκ. Δεν υπάρχει κάποια νέα παραγωγή για αλλαγή LOT.")
            else:
                st.info("Δεν υπάρχουν αποτελέσματα με τα τρέχοντα φίλτρα.")
        # --- 1Γ. ΕΞΥΠΝΟ ΣΠΑΣΙΜΟ ΠΑΡΑΓΓΕΛΙΑΣ (SPLIT) ---
        st.divider()
        with st.expander("✂️ Έξυπνο Σπάσιμο Παραγγελίας (Βρέθηκε Στοκ;)", expanded=False):
            st.info("Βρήκατε έτοιμα κοκτέιλ στο ψυγείο; Επιλέξτε την παραγγελία και το παλιό LOT από τη λίστα. Το σύστημα θα 'σπάσει' την παραγγελία, διατηρώντας το τιμολόγιο άθικτο και συνδέοντας αυτόματα τις παλιές πρώτες ύλες!")
            
            if not df_filtered.empty:
                # Κρατάμε μόνο τις νέες παραγωγές (με ml > 0)
                df_splittable = df_filtered[df_filtered["Σύνολο_ML"] > 0]
                
                if not df_splittable.empty:
                    split_groups = df_splittable.groupby(["Ημερομηνία", "Πελάτης", "Ώρα", "Cocktail", "LOT_Cocktail"])
                    split_options = ["-- Επιλέξτε Παραγγελία --"]
                    split_map = {}
                    
                    for name, group in split_groups:
                        o_date, o_cust, o_time, o_cocktail, o_lot = name
                        tot_pcs = int(group["Τεμάχια"].iloc[0])
                        
                        # Μόνο αν είναι πάνω από 1 τεμάχιο έχει νόημα να σπάσει!
                        if tot_pcs > 1: 
                            lbl = f"📅 {o_date} | 👤 {o_cust} | 🍹 {o_cocktail} ({tot_pcs} τμχ)"
                            split_options.append(lbl)
                            split_map[lbl] = {
                                "date": o_date, "cust": o_cust, "time": o_time, 
                                "cocktail": o_cocktail, "old_lot": o_lot, "total_pcs": tot_pcs
                            }
                    
                    if len(split_options) > 1:
                        import re
                        from datetime import datetime
                        
                        # 🚀 Ο ΑΠΟΛΥΤΟΣ & ΕΥΕΛΙΚΤΟΣ ΑΝΙΧΝΕΥΤΗΣ 
                        def flexible_date_sorter(lbl):
                            if "-- Επιλέξτε" in lbl:
                                return datetime.max # Για να μένει ΠΑΝΤΑ πρώτο
                                
                            try:
                                match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', lbl)
                                
                                if match:
                                    d = int(match.group(1))
                                    m = int(match.group(2))
                                    y = int(match.group(3))
                                    
                                    if y < 100:
                                        y += 2000
                                        
                                    return datetime(y, m, d)
                                
                                match2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', lbl)
                                if match2:
                                    return datetime(int(match2.group(1)), int(match2.group(2)), int(match2.group(3)))
                                    
                                return datetime.min
                            except Exception:
                                return datetime.min

                        # Αφαιρούμε το πρώτο, ταξινομούμε, και τα ξαναενώνουμε
                        temp_splits = split_options[1:]
                        temp_splits.sort(key=flexible_date_sorter, reverse=True)
                        
                        sorted_split_options = [split_options[0]] + temp_splits

                        sel_split = st.selectbox("Επιλέξτε Παραγγελία για Σπάσιμο:", sorted_split_options)
                        
                        if sel_split != "-- Επιλέξτε Παραγγελία --":
                            orig_pcs = split_map[sel_split]["total_pcs"]
                            b_cocktail_selected = split_map[sel_split]["cocktail"]
                            
                            st.info(f"Επιλεγμένη Παραγγελία: **{orig_pcs} τμχ**")
                            
                            hist_lots = []
                            try:
                                lots_query = supabase.table("production_log").select("lot_cocktail").eq("cocktail_name", b_cocktail_selected).execute()
                                if lots_query.data:
                                    import re
                                    from datetime import datetime
                                    
                                    found_lots = set(str(row["lot_cocktail"]) for row in lots_query.data if row.get("lot_cocktail"))
                                    clean_lots = [l for l in found_lots if l.strip() and l.lower() != "nan" and l != "-"]
                                    
                                    def sort_lot_as_date(lot_str):
                                        try:
                                            match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', lot_str)
                                            if match:
                                                d = int(match.group(1))
                                                m = int(match.group(2))
                                                y = int(match.group(3))
                                                if y < 100:
                                                    y += 2000
                                                return datetime(y, m, d)
                                            return datetime.min
                                        except:
                                            return datetime.min
                                            
                                    hist_lots = sorted(clean_lots, key=sort_lot_as_date, reverse=True)
                            except Exception:
                                pass
                            
                            st.markdown("---")
                            num_splits = st.number_input("🔄 Σε πόσα διαφορετικά παλιά LOT θέλετε να σπάσετε την παραγγελία;", min_value=1, max_value=5, value=1, step=1)
                            
                            splits_data = []
                            total_stock_found = 0
                            
                            for i in range(num_splits):
                                st.markdown(f"**📦 Σπάσιμο #{i+1}**")
                                c_s1, c_s2, c_s3 = st.columns([1.5, 2, 1])
                                
                                s_pcs = c_s1.number_input(f"Τεμάχια από LOT #{i+1}:", min_value=1, max_value=orig_pcs, value=1, step=1, key=f"split_pcs_{i}")
                                
                                if hist_lots:
                                    s_lot = c_s2.selectbox(f"Επιλογή LOT #{i+1}:", ["-- Επιλέξτε LOT --"] + hist_lots, key=f"split_lot_sel_{i}")
                                else:
                                    s_lot = c_s2.text_input(f"Πληκτρολόγηση LOT #{i+1}:", placeholder="Δεν βρέθηκε ιστορικό", key=f"split_lot_txt_{i}")
                                    
                                s_cost = c_s3.checkbox("Με Κόστος;", value=False, key=f"split_cost_{i}", help="Υπολογισμός λογιστικού κόστους")
                                
                                splits_data.append({"pcs": s_pcs, "lot": s_lot, "charge": s_cost})
                                total_stock_found += s_pcs
                                
                            st.markdown("---")
                            remain_pcs = orig_pcs - total_stock_found
                            
                            if remain_pcs < 0:
                                st.error(f"🚫 Σφάλμα: Προσπαθείτε να τραβήξετε {total_stock_found} τμχ από το στοκ, αλλά η αρχική παραγγελία είναι μόνο {orig_pcs} τμχ!")
                            # 🚀 ΕΔΩ ΜΠΑΙΝΕΙ Η ΝΕΑ "ΑΣΠΙΔΑ" 🚀
                            elif remain_pcs == 0:
                                st.error(f"🚫 Σφάλμα: Προσπαθείτε να τραβήξετε όλη την ποσότητα ({total_stock_found} τμχ) από το στοκ. Σε αυτήν την περίπτωση δεν κάνετε 'Σπάσιμο'. Πηγαίνετε στο 'Ιστορικό & Επεξεργασία Παραγωγής' και αλλάξτε απλά το LOT της αρχικής παραγγελίας!")
                            else:
                                c_info1, c_info2 = st.columns(2)
                                c_info1.info(f"Συνολικά από Στοκ: **{total_stock_found} τμχ**")
                                c_info2.success(f"Νέα Παραγωγή: **{remain_pcs} τμχ**")

                                if st.button("✂️ Εκτέλεση Πολλαπλού Σπασίματος", type="primary"):
                                    valid_splits = []
                                    for s_data in splits_data:
                                        is_valid_lot = s_data["lot"] and s_data["lot"] != "-- Επιλέξτε LOT --" and s_data["lot"].strip() != ""
                                        if s_data["pcs"] > 0 and is_valid_lot:
                                            valid_splits.append(s_data)
                                            
                                    if len(valid_splits) == 0:
                                        st.warning("⚠️ Δεν έχετε επιλέξει κανένα έγκυρο LOT για το σπάσιμο.")
                                    else:
                                        real_total_stock = sum(item["pcs"] for item in valid_splits)
                                        real_remain = orig_pcs - real_total_stock
                                        
                                        if real_remain < 0:
                                            st.error(f"🚫 Σφάλμα: Προσπαθείτε να τραβήξετε {real_total_stock} τμχ, αλλά η παραγγελία είναι μόνο {orig_pcs} τμχ!")
                                        # 🚀 Η "ΑΣΠΙΔΑ" ΠΡΟΣΤΑΤΕΥΕΙ ΚΑΙ ΤΟ ΚΟΥΜΠΙ 🚀
                                        elif real_remain == 0:
                                            st.error("🚫 Σφάλμα: Η πράξη ακυρώθηκε. Δεν μπορείτε να σπάσετε το 100% της παραγγελίας.")
                                        else:
                                            b_date = split_map[sel_split]["date"]
                                            b_cust = split_map[sel_split]["cust"]
                                            b_cocktail = split_map[sel_split]["cocktail"]
                                            
                                            check_res = supabase.table("production_log").select("is_from_stock, ingredient_name").eq("prod_date", b_date).eq("customer", b_cust).eq("cocktail_name", b_cocktail).execute()
                                            
                                            already_split = False
                                            if check_res.data:
                                                for row in check_res.data:
                                                    if str(row.get("is_from_stock")).lower() == "true" or "Έτοιμο Προϊόν" in str(row.get("ingredient_name", "")):
                                                        already_split = True
                                                        break
                                            
                                            if already_split:
                                                st.error("🚫 Προσοχή! Αυτή η παραγγελία έχει ήδη υποστεί σπάσιμο. Δεν επιτρέπεται δεύτερο σπάσιμο! Διαγράψτε την αρχική εγγραφή και καταχωρήστε την ξανά.")
                                            else:
                                                with st.spinner("Γίνεται έξυπνο πολλαπλό σπάσιμο παραγγελίας..."):
                                                    try:
                                                        b_time = split_map[sel_split]["time"]
                                                        b_lot = split_map[sel_split]["old_lot"]
                                                        
                                                        res_orig = supabase.table("production_log").select("*").eq("prod_date", b_date).eq("customer", b_cust).eq("prod_time", b_time).eq("cocktail_name", b_cocktail).eq("lot_cocktail", b_lot).execute()
                                                        
                                                        if res_orig.data:
                                                            first_row = res_orig.data[0]
                                                            
                                                            for row in res_orig.data:
                                                                new_ml = (float(row["total_ml"]) / orig_pcs) * real_remain
                                                                new_g = (float(row["target_g"]) / orig_pcs) * real_remain
                                                                
                                                                supabase.table("production_log").update({
                                                                    "pieces": real_remain,
                                                                    "total_ml": round(new_ml, 2),
                                                                    "target_g": round(new_g, 2)
                                                                }).eq("id", row["id"]).execute()
                                                            
                                                            stock_entries_to_insert = []
                                                            for s_data in valid_splits:
                                                                final_stock_lot = s_data["lot"].strip()
                                                                if final_stock_lot == b_lot:
                                                                    final_stock_lot = f"{final_stock_lot}-S"
                                                                    
                                                                final_stock_cost = float(first_row["unit_cost"]) if s_data["charge"] else 0.0
                                                                
                                                                stock_entry = {
                                                                    "prod_date": first_row["prod_date"],
                                                                    "prod_time": first_row["prod_time"],
                                                                    "customer": first_row["customer"],
                                                                    "cocktail_name": first_row["cocktail_name"],
                                                                    "lot_cocktail": final_stock_lot, 
                                                                    "pieces": s_data["pcs"],
                                                                    "ingredient_name": "📦 Έτοιμο Προϊόν (Στοκ)",
                                                                    "total_ml": 0.0,
                                                                    "target_g": 0.0,
                                                                    "lot_number": final_stock_lot, 
                                                                    "expiry_date": "-",
                                                                    "unit_cost": first_row["unit_cost"],
                                                                    "applied_cost": final_stock_cost,
                                                                    "is_from_stock": True,
                                                                    "free_pieces": 0, 
                                                                    "discounted_pieces": 0,
                                                                    "discount_pct": 0.0,
                                                                    "cal_uid": first_row.get("cal_uid", "")
                                                                }
                                                                stock_entries_to_insert.append(stock_entry)
                                                                
                                                            supabase.table("production_log").insert(stock_entries_to_insert).execute()
                                                            
                                                            st.session_state.pop('search_data_loaded', None)
                                                            st.success(f"✅ Επιτυχία! Η παραγγελία σπάστηκε σε {len(valid_splits)} παλιά LOT.")
                                                            import time
                                                            time.sleep(1.5)
                                                            st.rerun()
                                                    except Exception as e:
                                                        st.error(f"Σφάλμα κατά το σπάσιμο: {e}")
                    else:
                        st.info("Δεν βρέθηκαν παραγγελίες νέας παραγωγής που να μπορούν να σπαστούν.")
                else:
                    st.info("Δεν υπάρχουν παραγγελίες νέας παραγωγής (με >1 τμχ) για να σπαστούν.")
                
        # --- 2. ΕΠΙΛΟΓΗ ΠΑΡΑΓΓΕΛΙΑΣ (MASTER) ---
        # --- 2. ΕΠΙΛΟΓΗ ΠΑΡΑΓΓΕΛΙΑΣ (MASTER) ---
        st.divider()
        st.markdown("### 📋 2. Διαθέσιμες Παραγγελίες")
        
        if df_filtered.empty:
            st.info("Δεν βρέθηκαν παραγγελίες με τα επιλεγμένα φίλτρα.")
        else:
            # Ομαδοποιούμε ανά Ημερομηνία, Πελάτη και Ώρα για να φτιάξουμε τις ξεκάθαρες "Παραγγελίες"
            order_groups = df_filtered.groupby(["Ημερομηνία", "Πελάτης", "Ώρα"])
            
            temp_options = []
            order_map = {}
            
            for name, group in order_groups:
                o_date, o_cust, o_time = name
                
                # 🚀 ΠΡΟΣΘΗΚΗ: Αναζήτηση Ημερομηνίας Καταχώρησης από τη βάση (Supabase)
                entry_date_str = ""
                for col in ["created_at", "Timestamp", "timestamp", "Ημ_Καταχώρησης"]:
                    if col in group.columns:
                        raw_val = str(group[col].iloc[0]).strip()
                        if raw_val and raw_val.lower() not in ["nan", "none"]:
                            # Κρατάμε μόνο την ημερομηνία
                            date_only = raw_val.split("T")[0].split(" ")[0]
                            
                            # 🚀 ΝΕΟ: Μετατροπή από ΕΕΕΕ-ΜΜ-ΗΗ σε ΗΗ/ΜΜ/ΕΕΕΕ
                            if "-" in date_only:
                                parts = date_only.split("-")
                                if len(parts) == 3 and len(parts[0]) == 4:
                                    date_only = f"{parts[2]}/{parts[1]}/{parts[0]}"
                                    
                            entry_date_str = date_only + " "
                            break
                
                # Τραβάμε τα ονόματα των κοκτέιλ και τα ενώνουμε σε μία γραμμή!
                cocktail_names = group["Cocktail"].unique().tolist()
                cocktails_str = ", ".join(cocktail_names)
                
                total_pcs = group.groupby("Cocktail")["Τεμάχια"].first().sum()
                
                # Το label τώρα βγάζει την entry_date_str (σε ΗΗ/ΜΜ/ΕΕΕΕ) ακριβώς πριν την ώρα!
                label = f"📅 {o_date} | 👤 {o_cust} | 🕒 {entry_date_str}{o_time} | 🍹 {cocktails_str} ({int(total_pcs)} τμχ)"
                temp_options.append(label)
                order_map[label] = {"date": o_date, "cust": o_cust, "time": o_time, "df": group}
                
            # 🚀 ΕΞΥΠΝΗ ΤΑΞΙΝΟΜΗΣΗ (ΧΡΟΝΟΛΟΓΙΚΑ, ΝΕΟΤΕΡΑ ΠΡΩΤΑ)
            from datetime import datetime
            def sort_by_real_date(lbl):
                try:
                    # ΑΛΛΑΓΗ ΑΣΦΑΛΕΙΑΣ: Τραβάμε τα δεδομένα από το order_map αντί να κόβουμε το κείμενο!
                    # Έτσι δεν μπερδεύεται από την έξτρα ημερομηνία καταχώρησης που βάλαμε στο label.
                    d_part = str(order_map[lbl]["date"]).strip()
                    t_part = str(order_map[lbl]["time"]).strip()
                    
                    if t_part.count(":") == 2:
                        return datetime.strptime(f"{d_part} {t_part}", "%d/%m/%Y %H:%M:%S")
                    else:
                        return datetime.strptime(f"{d_part} {t_part}", "%d/%m/%Y %H:%M")
                except Exception:
                    return datetime.min # Αν κάτι πάει στραβά, το πάει στο τέλος

            # Ταξινομούμε την προσωρινή λίστα
            temp_options.sort(key=sort_by_real_date, reverse=True)
            
            # Ενώνουμε την αρχική επιλογή με την ταξινομημένη λίστα
            order_options = ["-- Επιλέξτε Παραγγελία για Επεξεργασία --"] + temp_options
            
            sel_order_label = st.selectbox("Βρέθηκαν οι παρακάτω παραγγελίες:", order_options)
            
            # --- 3. ΚΑΡΤΕΛΑ ΕΠΕΞΕΡΓΑΣΙΑΣ (DETAIL) ---
            if sel_order_label != "-- Επιλέξτε Παραγγελία για Επεξεργασία --":
                sel_order_data = order_map[sel_order_label]
                o_df = sel_order_data["df"]
                o_date = sel_order_data["date"]
                o_cust = sel_order_data["cust"]
                o_time = sel_order_data["time"]
                
                st.divider()
                st.markdown(f"### 🛠️ 3. Καρτέλα Παραγγελίας: **{o_cust}** ({o_date})")
                st.info("💡 Ανοίξτε τα κοκτέιλ παρακάτω. Μπορείτε να αλλάξετε την Ημερομηνία ή τον Πελάτη *ξεχωριστά* για το καθένα (αν θέλετε να τα διαχωρίσετε) ή να τα διαγράψετε βάζοντας **0** στα τεμάχια.")
                
                # 🚀 ΑΛΛΑΓΗ: Έγινε st.container() για να λειτουργεί ΖΩΝΤΑΝΑ η σελίδα!
                with st.container():
                    unique_cocktails_in_order = o_df[["Cocktail", "LOT_Cocktail"]].drop_duplicates()
                    cocktail_updates = {}
                    
                    # 🚀 ΜΑΓΕΙΑ: Η συνάρτηση (callback) που μεταφέρει το LOT στο κουτάκι ΑΚΑΡΙΑΙΑ!
                    def sync_lot(key_to_sync):
                        chosen = st.session_state.get(f"slot_{key_to_sync}")
                        if chosen and chosen != "-- Χειροκίνητη Καταχώρηση --":
                            # Αλλάζει απευθείας την τιμή στο πάνω κουτάκι!
                            st.session_state[f"l_{key_to_sync}"] = chosen
                    
                    for idx, row in unique_cocktails_in_order.iterrows():
                        c_name = row["Cocktail"]
                        c_lot = row["LOT_Cocktail"]
                        c_df = o_df[(o_df["Cocktail"] == c_name) & (o_df["LOT_Cocktail"] == c_lot)]
                        base_pcs = int(c_df["Τεμάχια"].iloc[0])
                        safe_key = f"{c_name}_{c_lot}".replace(" ", "_").replace("-", "_")
                        
                        with st.expander(f"🍹 {c_name} | LOT: {c_lot} | {base_pcs} τμχ", expanded=False):
                            
                            c1, c2, c3, c4 = st.columns(4)
                            new_date = c1.text_input("Ημερομηνία", value=o_date, key=f"d_{safe_key}")
                            
                            try:
                                cust_idx = customer_options.index(o_cust)
                            except ValueError:
                                cust_idx = 0
                            
                            new_cust = c2.selectbox("Πελάτης", options=customer_options, index=cust_idx, key=f"c_{safe_key}")
                            new_pcs = c3.number_input("Τεμάχια", value=base_pcs, min_value=0, key=f"p_{safe_key}")
                            
                            # Επιστρέψαμε στην απλή μορφή, γιατί τώρα το αναλαμβάνει η συνάρτηση sync_lot!
                            new_lot = c4.text_input("LOT Παραγωγής", value=c_lot, key=f"l_{safe_key}")
                            
                            st.markdown("---")
                            
                            is_currently_stock = all(float(x) == 0.0 for x in c_df["Σύνολο_ML"].dropna())
                            current_app_cost = float(c_df["applied_cost"].iloc[0]) if "applied_cost" in c_df.columns and pd.notna(c_df["applied_cost"].iloc[0]) else None
                            
                            col_rad1, col_rad2 = st.columns(2)
                            with col_rad1:
                                prod_type = st.radio(
                                    "🔄 Προέλευση Κοκτέιλ:",
                                    ["Από Παλιό LOT (Αδήλωτο Στοκ)", "Νέα Παραγωγή (Κατανάλωση Υλικών Τώρα)"],
                                    index=0 if is_currently_stock else 1,
                                    key=f"ptype_{safe_key}"
                                )
                                
                            with col_rad2:
                                if prod_type == "Από Παλιό LOT (Αδήλωτο Στοκ)":
                                    default_cost_idx = 1 if (current_app_cost is not None and current_app_cost == 0.0) else 0
                                    cost_mode = st.radio(
                                        "📦 Οικονομική Διαχείριση (Κέρδος):", 
                                        ["Κανονικό Κόστος Συνταγής", "Μηδενικό Κόστος (π.χ. Κέρασμα)"],
                                        index=default_cost_idx,
                                        key=f"smode_{safe_key}"
                                    )
                                else:
                                    cost_mode = "Κανονικό Κόστος Συνταγής"
                            
                            available_lots = df_all_logs_renamed[df_all_logs_renamed["Cocktail"] == c_name]["LOT_Cocktail"].dropna().unique().tolist()
                            available_lots = sorted([str(l) for l in available_lots if str(l).strip() not in ["", "-", "nan"]], reverse=True)
                            
                            if prod_type == "Από Παλιό LOT (Αδήλωτο Στοκ)":
                                stock_lot_selection = st.selectbox(
                                    "🔍 Αυτόματη Ανάκτηση Παλιών Υλικών:",
                                    options=["-- Χειροκίνητη Καταχώρηση --"] + available_lots,
                                    key=f"slot_{safe_key}",
                                    on_change=sync_lot,          # 🚀 ΚΑΛΕΙ ΤΗ ΣΥΝΑΡΤΗΣΗ μόλις αλλάξεις επιλογή!
                                    args=(safe_key,)             # 🚀 Της στέλνει το κλειδί για να βρει ποιο κουτάκι να αλλάξει!
                                )
                            else:
                                stock_lot_selection = "-- Χειροκίνητη Καταχώρηση --"
                                
                            # Από εδώ και κάτω ο κώδικας συνεχίζει κανονικά όπως τον είχες...
                            st.markdown("<p style='font-size:12px; color:#009b3a; font-weight:bold; margin-top:10px; margin-bottom:5px;'>Υλικά (Τα LOT στα κουτάκια σώζονται ακριβώς όπως τα βλέπετε):</p>", unsafe_allow_html=True)
                            
                            ingredients_data = []
                            
                            hist_lot_data = pd.DataFrame()
                            if stock_lot_selection != "-- Χειροκίνητη Καταχώρηση --":
                                hist_lot_data = df_all_logs_renamed[(df_all_logs_renamed["Cocktail"] == c_name) & (df_all_logs_renamed["LOT_Cocktail"] == stock_lot_selection)]
                                
                            # Συνάρτηση που βρίσκει τα ML κατευθείαν από τη Συνταγή!
                            def get_recipe_ml(cocktail, ing):
                                try:
                                    if 'df_rec' in globals() and not df_rec.empty:
                                        r_row = df_rec[df_rec["Ονομα"] == cocktail]
                                        if not r_row.empty:
                                            r_row = r_row.iloc[0]
                                            for i in range(1, 14):
                                                if str(r_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "")).strip() == ing:
                                                    val = r_row.get(f"ML{i}", 0)
                                                    if pd.isna(val): return 0.0
                                                    return float(str(val).replace(',', '.').replace(' ', ''))
                                except: pass
                                return 0.0
                            
                            for index_ing, (_, ing_row) in enumerate(c_df.iterrows()):
                                ing_name = ing_row["Υλικό"]
                                raw_lot = str(ing_row["Lot Number"]) if pd.notna(ing_row["Lot Number"]) else ""
                                raw_exp = str(ing_row["Ημ_Λήξης"]) if pd.notna(ing_row["Ημ_Λήξης"]) else ""
                                
                                if not hist_lot_data.empty:
                                    hist_ing = hist_lot_data[hist_lot_data["Υλικό"] == ing_name]
                                    if not hist_ing.empty:
                                        raw_lot = str(hist_ing["Lot Number"].iloc[0]) if pd.notna(hist_ing["Lot Number"].iloc[0]) else ""
                                        raw_exp = str(hist_ing["Ημ_Λήξης"].iloc[0]) if pd.notna(hist_ing["Ημ_Λήξης"].iloc[0]) else ""
                                
                                old_ml = float(ing_row["Σύνολο_ML"]) if pd.notna(ing_row["Σύνολο_ML"]) else 0.0
                                orig_id = ing_row["id"]
                                u_cost = float(ing_row["unit_cost"]) if "unit_cost" in ing_row.index and pd.notna(ing_row["unit_cost"]) else _TOTAL_FIXED_FALLBACK  # 🔧 fallback μόνο για ελλιπή ιστορικά δεδομένα
                                
                                # 🚀 ΑΝ Ο ΧΡΗΣΤΗΣ ΤΟ ΓΥΡΙΣΕ ΣΕ "ΝΕΑ ΠΑΡΑΓΩΓΗ" ενώ ήταν Στοκ!
                                if prod_type == "Νέα Παραγωγή (Κατανάλωση Υλικών Τώρα)" and old_ml == 0.0:
                                    base_recipe_ml = get_recipe_ml(c_name, ing_name)
                                    old_ml = base_recipe_ml * (base_pcs if base_pcs != 0 else 1)
                                
                                # 🚀 ΑΝ ΤΟ ΓΥΡΙΣΕ ΣΕ "ΣΤΟΚ", τα ML γίνονται 0!
                                if prod_type == "Από Παλιό LOT (Αδήλωτο Στοκ)":
                                    display_ml = 0.0
                                else:
                                    display_ml = old_ml * (new_pcs/base_pcs if base_pcs!=0 else 1)
                                
                                lot_parts = raw_lot.split(" / ") if " / " in raw_lot else [raw_lot, ""]
                                exp_parts = raw_exp.split(" / ") if " / " in raw_exp else [raw_exp, ""]
                                while len(lot_parts) < 2: lot_parts.append("")
                                while len(exp_parts) < 2: exp_parts.append("")
                                
                                r = st.columns([1.5, 0.7, 1, 1, 1, 1])
                                r[0].write(f"**{ing_name}**")
                                r[1].write(f"{display_ml:.0f} ml")
                                
                                refresh_key = stock_lot_selection.replace("/", "_").replace(" ", "").replace("-", "_")
                                
                                l1 = r[2].text_input("L1", value=lot_parts[0], key=f"l1_{safe_key}_{orig_id}_{index_ing}_{refresh_key}", label_visibility="collapsed")
                                e1 = r[3].text_input("E1", value=exp_parts[0], key=f"e1_{safe_key}_{orig_id}_{index_ing}_{refresh_key}", label_visibility="collapsed")
                                l2 = r[4].text_input("L2", value=lot_parts[1], key=f"l2_{safe_key}_{orig_id}_{index_ing}_{refresh_key}", label_visibility="collapsed")
                                e2 = r[5].text_input("E2", value=exp_parts[1], key=f"e2_{safe_key}_{orig_id}_{index_ing}_{refresh_key}", label_visibility="collapsed")
                                
                                ingredients_data.append({
                                    "orig_id": orig_id, "ing_name": ing_name, "final_ml": display_ml, "u_cost": u_cost,
                                    "new_lot": f"{l1} / {l2}".strip(" / "), "new_exp": f"{e1} / {e2}".strip(" / ")
                                })
                                
                            cocktail_updates[safe_key] = {
                                "orig_cocktail": c_name, "orig_lot": c_lot, "base_pcs": base_pcs,
                                "new_date": new_date, "new_cust": new_cust, "new_pcs": new_pcs, "new_lot": new_lot,
                                "prod_type": prod_type, "cost_mode": cost_mode,
                                "ingredients": ingredients_data
                            }
                            
                    st.divider()
                    submit_edits = st.button("💾 Αποθήκευση Όλων των Αλλαγών Παραγγελίας", type="primary")
                    
                    if submit_edits:
                        try:
                            all_orig_ids = []
                            for c_data in cocktail_updates.values():
                                all_orig_ids.extend([i["orig_id"] for i in c_data["ingredients"]])
                            
                            # 🔧 FIX: πριν, ΚΑΘΕ επεξεργασία μέσω αυτού του εργαλείου διέγραφε σιωπηλά
                            # το free_pieces (δώρο)/discounted_pieces/discount_pct της αρχικής παρτίδας —
                            # π.χ. αν διόρθωνες μόνο ένα LOT νούμερο σε παραγγελία με δώρο, το δώρο
                            # "εξαφανιζόταν" και ο πελάτης χρεωνόταν κανονικά. Τώρα διαβάζουμε τις
                            # αρχικές τιμές και τις μεταφέρουμε στις νέες εγγραφές.
                            orig_meta_map = {}
                            if all_orig_ids:
                                res_old = supabase.table("production_log").select("id, applied_cost, free_pieces, discounted_pieces, discount_pct").in_("id", all_orig_ids).execute()
                                if res_old.data:
                                    orig_meta_map = {row["id"]: row for row in res_old.data}
                            
                            if all_orig_ids:
                                supabase.table("production_log").delete().in_("id", all_orig_ids).execute()
                            
                            new_batch = []
                            affected_b2b_pairs = set()
                            affected_b2b_pairs.add((o_cust, o_date)) 
                            
                            for c_data in cocktail_updates.values():
                                if int(c_data["new_pcs"]) == 0:
                                    continue
                                    
                                affected_b2b_pairs.add((c_data["new_cust"], c_data["new_date"]))
                                
                                p_type = c_data["prod_type"]
                                c_mode = c_data["cost_mode"]

                                # Παίρνουμε το free_pieces/discounted_pieces/discount_pct από την ΑΡΧΙΚΗ
                                # παρτίδα (όλες οι γραμμές υλικών της ίδιας παρτίδας μοιράζονται τις ίδιες
                                # τιμές, όπως ακριβώς και το "pieces"), και τα προσαρμόζουμε ώστε να μην
                                # ξεπερνούν τα νέα τεμάχια αν η ποσότητα άλλαξε.
                                first_orig_id = c_data["ingredients"][0]["orig_id"] if c_data["ingredients"] else None
                                orig_meta = orig_meta_map.get(first_orig_id, {}) if first_orig_id is not None else {}
                                new_pcs_int = int(c_data["new_pcs"])
                                carried_free = min(int(orig_meta.get("free_pieces") or 0), new_pcs_int)
                                carried_disc_pcs = min(int(orig_meta.get("discounted_pieces") or 0), max(0, new_pcs_int - carried_free))
                                carried_disc_pct = float(orig_meta.get("discount_pct") or 0.0)
                                
                                for ing in c_data["ingredients"]:
                                    new_ml = ing["final_ml"] # Παίρνει κατευθείαν τα τελικά ML που υπολόγισε η οθόνη!
                                    
                                    g_calc = new_ml
                                    match_i = df_ing[df_ing["Name"] == ing["ing_name"]]
                                    if not match_i.empty and float(match_i.iloc[0].get("Volume", 1)) > 0: 
                                        g_calc = (new_ml / float(match_i.iloc[0]["Volume"])) * float(match_i.iloc[0]["Weight_Full"])
                                        
                                    new_row = {
                                        "prod_date": c_data["new_date"].strip(), "prod_time": o_time, 
                                        "customer": c_data["new_cust"].strip(), "cocktail_name": c_data["orig_cocktail"], 
                                        "lot_cocktail": c_data["new_lot"].strip(), "pieces": new_pcs_int, 
                                        "ingredient_name": ing["ing_name"], "total_ml": new_ml, "target_g": round(g_calc, 1), 
                                        "lot_number": ing["new_lot"], "expiry_date": ing["new_exp"], "unit_cost": round(float(ing["u_cost"]), 4),
                                        "free_pieces": carried_free,
                                        "discounted_pieces": carried_disc_pcs,
                                        "discount_pct": carried_disc_pct,
                                    }
                                    if p_type == "Από Παλιό LOT (Αδήλωτο Στοκ)" and "Μηδενικό" in c_mode:
                                        new_row["applied_cost"] = 0.0
                                    else:
                                        new_row["applied_cost"] = None 
                                        
                                    new_batch.append(new_row)
                            
                            if new_batch:
                                supabase.table("production_log").insert(new_batch).execute()
                                
                            # ΑΠΟΛΥΤΟ REBUILD B2B
                            all_recipes_res = supabase.table("recipes").select("name, catalog_price").execute()
                            all_customers_res = supabase.table("customers").select("name, discount").execute()
                            recipe_prices = {r['name']: float(r.get('catalog_price') or 0.0) for r in all_recipes_res.data} if all_recipes_res.data else {}
                            customer_discounts = {c['name']: float(c.get('discount') or 0.0) for c in all_customers_res.data} if all_customers_res.data else {}
                            
                            from datetime import datetime
                            for b2b_cust, b2b_date in affected_b2b_pairs:
                                today_logs = supabase.table("production_log").select("cocktail_name, pieces, free_pieces, discounted_pieces, discount_pct, lot_cocktail, prod_time").eq("prod_date", b2b_date).eq("customer", b2b_cust).execute()
                                
                                try: date_iso = datetime.strptime(b2b_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                                except ValueError: date_iso = "1900-01-01" 
                                    
                                existing_order = find_existing_b2b_order(b2b_cust, date_iso)
                                
                                if today_logs.data:
                                    import pandas as pd
                                    df_logs = pd.DataFrame(today_logs.data).fillna(0)
                                    df_logs = df_logs.drop_duplicates(subset=["cocktail_name", "lot_cocktail", "prod_time"])
                                    
                                    unique_cocktails = {}
                                    for _, row in df_logs.iterrows():
                                        c_n = row["cocktail_name"]
                                        if c_n not in unique_cocktails: unique_cocktails[c_n] = {"pcs": 0, "free": 0, "s_pcs": 0, "s_pct": 0.0}
                                        unique_cocktails[c_n]["pcs"] += int(row.get("pieces") or 0)
                                        # 🔧 FIX: πριν max() — τώρα αθροίζει, ίδιος λόγος με την πρώτη εμφάνιση παραπάνω.
                                        unique_cocktails[c_n]["free"] += int(row.get("free_pieces") or 0)
                                        unique_cocktails[c_n]["s_pcs"] = max(unique_cocktails[c_n]["s_pcs"], int(row.get("discounted_pieces") or 0))
                                        unique_cocktails[c_n]["s_pct"] = max(unique_cocktails[c_n]["s_pct"], float(row.get("discount_pct") or 0.0))
                                        
                                    total_amount = 0.0
                                    details_lines = []
                                    for cockt, data in unique_cocktails.items():
                                        price = recipe_prices.get(cockt, 0.0)
                                        t_pcs, f_pcs = data["pcs"], data["free"]
                                        s_pcs = min(data["s_pcs"], max(0, t_pcs - f_pcs))
                                        normal_pcs = max(0, t_pcs - f_pcs - s_pcs)
                                        
                                        cost_normal = normal_pcs * price
                                        cost_special = s_pcs * price * (1 - (data["s_pct"] / 100.0))
                                        total_amount += (cost_normal + cost_special)
                                        
                                        line = f"• {t_pcs} τμχ {cockt}"
                                        if f_pcs > 0 or s_pcs > 0:
                                            extras = []
                                            if f_pcs > 0: extras.append(f"{f_pcs} Δώρο")
                                            if s_pcs > 0: extras.append(f"{s_pcs} με -{data['s_pct']}%")
                                            line += f" (Εκ των οποίων: {', '.join(extras)})"
                                        details_lines.append(line)
                                        
                                    discount = customer_discounts.get(b2b_cust, 0.0)
                                    final_total = total_amount * (1 - (discount / 100))
                                    details_str = "\n".join(details_lines)
                                    if discount > 0: details_str += f"\n\n[Αρχική Αξία: {total_amount:.2f}€ | Έκπτωση CRM: {discount}%]"
                                        
                                    if existing_order:
                                        supabase.table("b2b_orders").update({"total_amount": round(final_total, 2), "order_details": details_str}).eq("id", existing_order["id"]).execute()
                                    else:
                                        supabase.table("b2b_orders").insert({"customer_name": b2b_cust, "total_amount": round(final_total, 2), "order_details": details_str, "created_at": f"{date_iso}T12:00:00"}).execute()
                                else:
                                    if existing_order:
                                        supabase.table("b2b_orders").delete().eq("id", existing_order["id"]).execute()
                            
                            st.session_state['lot_reset_key'] += 1
                            st.session_state.pop('search_data_loaded', None)
                            st.success("✅ Όλα αποθηκεύτηκαν τέλεια! Το Σύστημα Πιστότητας, οι ποσότητες και τα LOT ενημερώθηκαν επιτυχώς!")
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as save_err:
                            st.error(f"Σφάλμα κατά την αποθήκευση: {save_err}")

        # --- 4. ΕΚΤΥΠΩΣΕΙΣ (ΑΠΕΥΘΕΙΑΣ ΑΠΟ ΤΗ ΒΑΣΗ - ΛΟΓΙΚΗ ΠΕΛΑΤΟΛΟΓΙΟΥ) ---
        st.divider()
        st.markdown("### 🖨️ 4. Συγκεντρωτικές Εκτυπώσεις (Βάσει Φίλτρων Αναζήτησης)")
        
        cust_label = f" | Πελάτης: <b>{sel_customer}</b>" if sel_customer != "-- Όλοι οι Πελάτες --" else ""
        file_suffix = f"_{sel_customer.replace(' ', '_')}" if sel_customer != "-- Όλοι οι Πελάτες --" else ""

        # 🚀 ΦΕΡΝΟΥΜΕ ΤΑ ΔΕΔΟΜΕΝΑ ΑΠΕΥΘΕΙΑΣ ΑΠΟ ΤΗ ΒΑΣΗ ΟΠΩΣ ΣΤΟ CRM
        query_print = supabase.table("production_log").select("*").eq("prod_date", sel_hist_date)
        if sel_customer != "-- Όλοι οι Πελάτες --":
            query_print = query_print.eq("customer", sel_customer)

        res_print = query_print.execute()

        if res_print.data:
            df_sales_raw = pd.DataFrame(res_print.data)

            # 🚀 Η ΛΟΓΙΚΗ ΣΟΥ: Αθροίζουμε τα ML ΠΡΙΝ κάνουμε drop duplicates για το Στοκ
            df_sales_raw['total_ml'] = pd.to_numeric(df_sales_raw['total_ml'], errors='coerce').fillna(0)
            df_ml_sum = df_sales_raw.groupby(["customer", "prod_time", "cocktail_name", "lot_cocktail"])['total_ml'].sum().reset_index()
            df_ml_sum = df_ml_sum.rename(columns={'total_ml': 'sum_ml'})

            # Κρατάμε μια γραμμή ανά παραγγελία
            df_sales = df_sales_raw.drop_duplicates(subset=["customer", "prod_time", "cocktail_name", "lot_cocktail"]).copy()
            df_sales = pd.merge(df_sales, df_ml_sum, on=["customer", "prod_time", "cocktail_name", "lot_cocktail"], how="left")

            # Μετατροπές σε νούμερα (όπως στο CRM)
            df_sales['t_pcs'] = pd.to_numeric(df_sales.get('pieces', 0), errors='coerce').fillna(0)
            df_sales['f_pcs'] = pd.to_numeric(df_sales.get('free_pieces', 0), errors='coerce').fillna(0)
            df_sales['s_pcs'] = pd.to_numeric(df_sales.get('discounted_pieces', 0), errors='coerce').fillna(0)
            df_sales['s_pct'] = pd.to_numeric(df_sales.get('discount_pct', 0), errors='coerce').fillna(0)

            # Ομαδοποίηση ανά Πελάτη και Κοκτέιλ για τις εκτυπώσεις της ημέρας
            df_daily = df_sales.groupby(["customer", "cocktail_name", "lot_cocktail"], as_index=False).agg({
                "t_pcs": "sum",
                "f_pcs": "sum",
                "s_pcs": "sum",
                "s_pct": "max",
                "sum_ml": "sum",
                "ingredient_name": "first",
                "is_from_stock": "first"
            })
        else:
            df_daily = pd.DataFrame(columns=["customer", "cocktail_name", "lot_cocktail", "t_pcs", "f_pcs", "s_pcs", "s_pct", "sum_ml", "ingredient_name", "is_from_stock"])

        # ─── ΕΚΤΥΠΩΣΗ 1: ΗΜΕΡΗΣΙΑ ΠΑΡΑΓΩΓΗ ΑΝΑ ΠΕΛΑΤΗ ───
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
            .discount-info {{ font-size: 11px; color: #dc3545; display: block; margin-top: 4px; font-weight: bold; }}
            .stock-badge {{ font-size: 11px; color: #007bff; font-weight: bold; background: #e7f1ff; padding: 2px 4px; border-radius: 3px; border: 1px solid #b6d4fe; }}
        </style></head><body>
            <div class='document-header'><h1>CABCLUB COCKTAILS</h1><h2>📋 ΗΜΕΡΗΣΙΑ ΠΑΡΑΓΩΓΗ ΑΝΑ ΠΕΛΑΤΗ</h2><p>Ημερομηνία Φιλτραρίσματος: <b>{sel_hist_date}</b>{cust_label}</p></div>
        """
        for p in df_daily["customer"].unique():
            p_df = df_daily[df_daily["customer"] == p]
            html_pro += f"<div class='customer-section'><strong>👤 ΠΕΛΑΤΗΣ:</strong> {p} | <strong>ΗΜΕΡΟΜΗΝΙΑ ΠΑΡΑΓΩΓΗΣ:</strong> {sel_hist_date}</div><table><thead><tr><th>🍹 Έτοιμο Cocktail</th><th>🔢 LOT Προϊόντος</th><th>📦 Ποσότητα / Στοιχεία</th></tr></thead><tbody>"
            for _, row in p_df.iterrows(): 
                # 🚀 Ο ΑΠΟΛΥΤΟΣ ΕΛΕΓΧΟΣ ΣΤΟΚ ΤΟΥ CRM
                is_stock = float(row.get("sum_ml", 1.0)) == 0.0 or ("Έτοιμο Προϊόν" in str(row.get("ingredient_name", ""))) or str(row.get("is_from_stock", "")).strip().lower() in ['true', '1', 't', 'yes']
                stock_html = " <span class='stock-badge'>📦 ΑΠΟ ΣΤΟΚ</span>" if is_stock else ""
                
                # 🚀 ΑΠΟΛΥΤΟ LOT (Κατευθείαν από τη βάση)
                lot_c = str(row['lot_cocktail']).strip()
                if lot_c.lower() in ['nan', 'none', ''] or not lot_c: lot_c = '-'
                
                t_pcs = int(row['t_pcs'])
                f_pcs = int(row['f_pcs'])
                s_pcs = int(row['s_pcs'])
                s_pct = float(row['s_pct'])
                
                discount_html = ""
                if f_pcs > 0 or s_pcs > 0:
                    discount_html = "<span class='discount-info'>("
                    parts = []
                    if f_pcs > 0: parts.append(f"{f_pcs} Δώρο")
                    if s_pcs > 0: parts.append(f"{s_pcs} με -{int(s_pct)}%")
                    discount_html += " / ".join(parts) + ")</span>"
                    
                html_pro += f"<tr><td><strong>{row['cocktail_name']}</strong>{stock_html}</td><td><span class='badge'>{lot_c}</span></td><td><b>{t_pcs} τμχ</b>{discount_html}</td></tr>"
            html_pro += "</tbody></table>"
        html_pro += "</body></html>"

        grand_total_pcs = int(df_daily["t_pcs"].sum()) if not df_daily.empty else 0
        total_different_cocktails = df_daily["cocktail_name"].nunique() if not df_daily.empty else 0
        total_label_text = f"ΣΥΝΟΛΙΚΗ ΠΑΡΑΓΩΓΗ ({sel_hist_date}):" if sel_customer == "-- Όλοι οι Πελάτες --" else f"ΣΥΝΟΛΙΚΗ ΠΑΡΑΓΩΓΗ ΓΙΑ {sel_customer.upper()} ({sel_hist_date}):"

        # ─── ΕΚΤΥΠΩΣΗ 2: ΗΜΕΡΗΣΙΑ ΠΑΡΑΓΩΓΗ ───
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
            .discount-info {{ font-size: 11px; color: #dc3545; display: block; margin-top: 4px; font-weight: bold; }}
            .stock-badge {{ font-size: 11px; color: #007bff; font-weight: bold; background: #e7f1ff; padding: 2px 4px; border-radius: 3px; border: 1px solid #b6d4fe; }}
        </style></head><body>
            <div class='header'><h1>📋 ΗΜΕΡΗΣΙΟ ΦΥΛΛΟ ΠΑΡΑΓΩΓΗΣ</h1><p>Ημερομηνία: <b>{sel_hist_date}</b>{cust_label}</p></div>
        """
        for cock in df_daily["cocktail_name"].unique():
            c_data = df_daily[df_daily["cocktail_name"] == cock]
            html_daily += f"<h2 class='cocktail-header'>🍹 {cock}</h2><table><thead><tr><th>LOT Number</th><th>Πελάτης</th><th>Ποσότητα (τμχ) / Στοιχεία</th></tr></thead><tbody>"
            for _, row in c_data.iterrows(): 
                is_stock = float(row.get("sum_ml", 1.0)) == 0.0 or ("Έτοιμο Προϊόν" in str(row.get("ingredient_name", ""))) or str(row.get("is_from_stock", "")).strip().lower() in ['true', '1', 't', 'yes']
                stock_html = " <span class='stock-badge'>📦 ΑΠΟ ΣΤΟΚ</span>" if is_stock else ""
                
                lot_c = str(row['lot_cocktail']).strip()
                if lot_c.lower() in ['nan', 'none', ''] or not lot_c: lot_c = '-'
                
                t_pcs = int(row['t_pcs'])
                f_pcs = int(row['f_pcs'])
                s_pcs = int(row['s_pcs'])
                s_pct = float(row['s_pct'])
                
                discount_html = ""
                if f_pcs > 0 or s_pcs > 0:
                    discount_html = "<span class='discount-info'>("
                    parts = []
                    if f_pcs > 0: parts.append(f"{f_pcs} Δώρο")
                    if s_pcs > 0: parts.append(f"{s_pcs} με -{int(s_pct)}%")
                    discount_html += " / ".join(parts) + ")</span>"
                    
                html_daily += f"<tr><td><b>{lot_c}</b>{stock_html}</td><td>{row['customer']}</td><td><b>{t_pcs} τμχ</b>{discount_html}</td></tr>"
            
            sub_total = int(c_data['t_pcs'].sum())
            html_daily += f"<tr style='background:#f9f9f9; font-weight:bold;'><td colspan='2' style='text-align: right;'>ΜΕΡΙΚΟ ΣΥΝΟΛΟ {cock}:</td><td>{sub_total} τμχ</td></tr></tbody></table>"

        html_daily += f"<div class='grand-total'>{total_label_text}<br><b>{grand_total_pcs} Τεμάχια</b><span class='cocktail-count'>🍹 Διαφορετικά Cocktail: {total_different_cocktails}</span></div></body></html>"
        
        # ─── ΕΚΤΥΠΩΣΗ 3: ΛΙΣΤΑ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ΥΛΙΚΩΝ ───
        if not df_past.empty and "Υλικό" in df_past.columns:
            df_prep = df_past.groupby("Υλικό").agg({
                "Σύνολο_ML": "sum", "Στόχος_Γραμμάρια": "sum",
                "Lot Number": lambda x: " / ".join(sorted(set(str(v).strip() for v in x if v and str(v).lower() not in ['none', '', 'nan', '-']))),
                "Ημ_Λήξης": lambda x: " / ".join(sorted(set(str(v).strip() for v in x if v and str(v).lower() not in ['none', '', 'nan', '-'])))
            }).reset_index()
        else:
            df_prep = pd.DataFrame(columns=["Υλικό", "Σύνολο_ML", "Στόχος_Γραμμάρια", "Lot Number", "Ημ_Λήξης"])

        # --- 🚀 ΝΕΟ: ΤΡΑΒΑΜΕ ΤΑ ΠΡΑΓΜΑΤΙΚΑ LOT ΑΠΟ ΤΟ ΙΣΤΟΡΙΚΟ ΠΑΡΑΓΩΓΗΣ ---
        actual_saved_lots = {}
        try:
            log_res = supabase.table("production_log") \
                .select("ingredient_name, lot_number, expiry_date") \
                .eq("prod_date", sel_hist_date) \
                .execute()
            
            if log_res.data:
                for r in log_res.data:
                    i_name = r.get("ingredient_name")
                    i_lot = str(r.get("lot_number", "")).strip()
                    i_exp = str(r.get("expiry_date", "")).strip()
                    if i_lot and i_lot.lower() not in ['none', '', 'nan', '-']:
                        actual_saved_lots[i_name] = {"lot": i_lot, "exp": i_exp}
        except Exception as e:
            pass
        # ---------------------------------------------------------------

        # ΣΥΜΠΙΕΣΜΕΝΟ CSS ΓΙΑ ΕΞΟΙΚΟΝΟΜΗΣΗ ΧΑΡΤΙΟΥ
        html_prep = f"""<html><head><meta charset='UTF-8'><style>
            body {{ font-family: sans-serif; padding: 10px; font-size: 12px; }}
            .header {{ text-align: center; border-bottom: 2px solid #2980b9; margin-bottom: 10px; padding-bottom: 5px; }}
            .header h1 {{ margin: 5px 0; font-size: 16px; }}
            .header p {{ margin: 0; font-size: 13px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background-color: #2980b9; color: white; padding: 4px; text-align: left; font-size: 12px; }}
            td {{ border: 1px solid #bdc3c7; padding: 3px 5px; }}
            .lot-info {{ font-size: 0.9em; color: #333; line-height: 1.1; }}
            @media print {{
                body {{ padding: 0; margin: 0; }}
                @page {{ margin: 0.5cm; }}
                table {{ page-break-inside: auto; }}
                tr {{ page-break-inside: avoid; page-break-after: auto; }}
            }}
        </style></head><body>
            <div class='header'><h1>🧪 ΛΙΣΤΑ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ΥΛΙΚΩΝ</h1><p>Ημερομηνία: <b>{sel_hist_date}</b>{cust_label}</p></div>
            <table><thead><tr>
                <th>Πρώτη Ύλη</th>
                <th>Ποσότητα (ml)</th>
                <th>Βάρος (g)</th>
                <th>LOT 1 & Λήξη 1</th>
                <th>LOT 2 & Λήξη 2</th>
            </tr></thead><tbody>
        """
        
        for _, row in df_prep.iterrows():
            ing_name = row.get('Υλικό', '-')
            ml_val = float(row.get('Σύνολο_ML', 0)) if pd.notna(row.get('Σύνολο_ML')) else 0.0
            g_val = float(row.get('Στόχος_Γραμμάρια', 0)) if pd.notna(row.get('Στόχος_Γραμμάρια')) else 0.0
            
            # Παίρνουμε αρχικά τα "θεωρητικά" από την αποθήκη
            lots_str = str(row.get('Lot Number', ''))
            exps_str = str(row.get('Ημ_Λήξης', ''))
            
            # ΑΝ ΟΜΩΣ έχουμε σώσει πραγματικά LOT για αυτή τη μέρα, τα κάνουμε αντικατάσταση (OVERRIDE)!
            if ing_name in actual_saved_lots:
                lots_str = actual_saved_lots[ing_name]["lot"]
                exps_str = actual_saved_lots[ing_name]["exp"]
            
            # Σπάμε τα string σε λίστες αν υπάρχουν πολλαπλά LOT (διαχωρισμένα με " / ")
            lots = lots_str.split(" / ") if lots_str else []
            exps = exps_str.split(" / ") if exps_str else []
            
            # Αν υπάρχει το βρίσκει, αλλιώς βάζει τελείες για χειρόγραφη συμπλήρωση (μειωμένες τελείες για εξοικονόμηση χώρου)
            l1 = lots[0] if len(lots) > 0 and lots[0] else "............"
            e1 = exps[0] if len(exps) > 0 and exps[0] else "............"
            
            l2 = lots[1] if len(lots) > 1 and lots[1] else "............"
            e2 = exps[1] if len(exps) > 1 and exps[1] else "............"
            
            html_prep += f"""<tr>
                <td><b>{ing_name}</b></td>
                <td>{ml_val:.0f} ml</td>
                <td>{g_val:.1f} g</td>
                <td class='lot-info'><b>L1:</b> {l1}<br><b>E1:</b> {e1}</td>
                <td class='lot-info'><b>L2:</b> {l2}<br><b>E2:</b> {e2}</td>
            </tr>"""
            
        html_prep += "</tbody></table></body></html>"

        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.download_button("📋 Ημερήσια Παραγωγή Ανά Πελάτη", data=html_pro, file_name=f"Prod_By_Customer_{sel_hist_date}{file_suffix}.html", mime="text/html", use_container_width=True)
        col_p2.download_button("📋 Ημερήσια Παραγωγή", data=html_daily, file_name=f"Daily_{sel_hist_date}{file_suffix}.html", mime="text/html", use_container_width=True)
        col_p3.download_button("🧪 Λίστα Προετοιμασίας", data=html_prep, file_name=f"Prep_{sel_hist_date}{file_suffix}.html", mime="text/html", use_container_width=True)
    # =========================================================================
    # 📊 REPORT: ΠΛΗΡΕΣ ΙΣΤΟΡΙΚΟ LOT ΠΡΩΤΩΝ ΥΛΩΝ
    # =========================================================================
    st.divider()
    with st.expander("📊 Report: Συγκεντρωτικό Ιστορικό LOT Πρώτων Υλών", expanded=False):
        st.info("Εξαγωγή όλων των LOT που έχουν χρησιμοποιηθεί στην παραγωγή (Ιχνηλασιμότητα).")

        if st.button("📥 Παραγωγή Report LOT", type="primary"):
            with st.spinner("Άντληση δεδομένων από το ιστορικό..."):
                res_report = supabase.table("production_log").select("prod_date, ingredient_name, lot_number, expiry_date, is_from_stock").order("id", desc=True).limit(100000).execute()
                
                if res_report.data:
                    import pandas as pd
                    df_rep = pd.DataFrame(res_report.data)
                    
                    # 1. Φιλτράρισμα: Αγνοούμε Στοκ και Έτοιμα Προϊόντα
                    stock_mask = df_rep.get("is_from_stock", "False").astype(str).str.strip().str.upper().isin(["TRUE", "ΝΑΙ", "YES", "1", "T"])
                    df_rep = df_rep[
                        (~stock_mask) & 
                        (~df_rep.get("ingredient_name", "").astype(str).str.contains("Έτοιμο Προϊόν", na=False))
                    ]
                    
                    # 2. Φιλτράρισμα: Κρατάμε ΜΟΝΟ όσα έχουν πραγματικό LOT
                    df_rep = df_rep[
                        df_rep["lot_number"].notna() & 
                        ~df_rep["lot_number"].astype(str).str.strip().isin(['', '-', 'None', 'nan', 'null'])
                    ]
                    
                    if not df_rep.empty:
                        # 3. Καθαρισμός και μετονομασία στηλών
                        df_rep = df_rep[["ingredient_name", "lot_number", "expiry_date", "prod_date"]]
                        df_rep.columns = ["Πρώτη Ύλη", "LOT Number", "Ημ. Λήξης", "Ημ. Παραγωγής"]
                        
                        # 4. Αφαίρεση διπλότυπων
                        df_unique = df_rep.drop_duplicates().sort_values(by=["Πρώτη Ύλη", "Ημ. Παραγωγής"], ascending=[True, False])
                        
                        st.success(f"✅ Βρέθηκαν {len(df_unique)} μοναδικές καταγραφές LOT!")
                        st.dataframe(df_unique, use_container_width=True, hide_index=True)
                        
                        # --- ΝΕΟ: ΔΗΜΙΟΥΡΓΙΑ HTML ΓΙΑ PDF / ΕΚΤΥΠΩΣΗ ---
                        import datetime
                        current_time = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
                        
                        html_report = f"""<html><head><meta charset='UTF-8'><style>
                            body {{ font-family: sans-serif; padding: 20px; font-size: 12px; }}
                            .header {{ text-align: center; border-bottom: 2px solid #2980b9; margin-bottom: 20px; padding-bottom: 10px; }}
                            .header h1 {{ margin: 0; font-size: 18px; color: #2c3e50; }}
                            .header p {{ margin: 5px 0 0 0; color: #7f8c8d; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                            th {{ background-color: #2980b9; color: white; padding: 8px; text-align: left; font-size: 12px; border: 1px solid #bdc3c7; }}
                            td {{ border: 1px solid #bdc3c7; padding: 6px; color: #333; }}
                            tr:nth-child(even) {{ background-color: #f9f9f9; }}
                            @media print {{
                                body {{ padding: 0; margin: 0; }}
                                @page {{ margin: 1cm; }}
                                table {{ page-break-inside: auto; }}
                                tr {{ page-break-inside: avoid; page-break-after: auto; }}
                            }}
                        </style></head><body>
                            <div class='header'>
                                <h1>📊 ΣΥΓΚΕΝΤΡΩΤΙΚΟ ΙΣΤΟΡΙΚΟ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑΣ (LOT)</h1>
                                <p>Ημερομηνία Εξαγωγής: <b>{current_time}</b></p>
                            </div>
                            <table><thead><tr>
                                <th>Πρώτη Ύλη</th>
                                <th>LOT Number</th>
                                <th>Ημ. Λήξης</th>
                                <th>Ημ. Παραγωγής</th>
                            </tr></thead><tbody>
                        """
                        
                        for _, row in df_unique.iterrows():
                            # Αντικαθιστούμε τα 'nan' με κενό για να φαίνεται πιο όμορφο
                            lot_val = row['LOT Number'] if pd.notna(row['LOT Number']) else '-'
                            exp_val = row['Ημ. Λήξης'] if pd.notna(row['Ημ. Λήξης']) else '-'
                            html_report += f"<tr><td><b>{row['Πρώτη Ύλη']}</b></td><td>{lot_val}</td><td>{exp_val}</td><td>{row['Ημ. Παραγωγής']}</td></tr>"
                            
                        html_report += "</tbody></table></body></html>"
                        # -----------------------------------------------
                        
                        st.markdown("### 📥 Επιλογές Εξαγωγής")
                        col_dl1, col_dl2 = st.columns(2)
                        
                        with col_dl1:
                            csv = df_unique.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="💾 Λήψη σε Excel (CSV)",
                                data=csv,
                                file_name="Traceability_LOT_Report.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                            
                        with col_dl2:
                            st.download_button(
                                label="🖨️ Λήψη για Εκτύπωση / PDF",
                                data=html_report,
                                file_name="Traceability_LOT_Report.html",
                                mime="text/html",
                                use_container_width=True
                            )
                    else:
                        st.warning("Δεν βρέθηκαν καταχωρημένα LOT στις πρώτες ύλες.")
                else:
                    st.error("Δεν υπάρχουν δεδομένα στη βάση.")
    # --- 5. ΣΥΝΘΕΤΗ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ & RECALL TOOL ---
    st.divider()
    st.subheader("🔍 Έλεγχος & Ιχνηλασιμότητα")
    tab_filter, tab_recall_tool, tab_forward = st.tabs(["📋 Αναζήτηση & Φίλτρα", "🚨 Recall Tool (Ανάκληση Υλικών)", "🔬 Έλεγχος Παρτίδας (Cocktail LOT)"])

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

    # ==========================================
        # TAB 3: ΑΛΥΣΙΔΩΤΗ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ & ΔΙΑΣΤΑΥΡΩΣΗ (INTERSECTION ENGINE)
        # ==========================================
        with tab_forward:
            st.markdown("#### 🔬 Έλεγχος Αναφοράς Πελάτη & Αλυσιδωτή Ιχνηλασιμότητα")
            st.write("Καταχωρήστε το κοκτέιλ που ανέφερε ο πελάτης. Αν έχετε και δεύτερη αναφορά, προσθέστε τη για να βρείτε το **κοινό υλικό** και να μικρύνετε τη λίστα ανάκλησης!")
            
            # Αρχικοποίηση μνήμης για τις διασταυρώσεις
            if 'recall_stack' not in st.session_state:
                st.session_state.recall_stack = []

            # Φόρτωση Δεδομένων
            with st.spinner("Φόρτωση δεδομένων ιχνηλασιμότητας..."):
                res_trace = supabase.table("production_log").select("*").execute()
                df_trace = pd.DataFrame(res_trace.data) if res_trace.data else pd.DataFrame()
            
            if not df_trace.empty:
                # ΔΙΟΡΘΩΣΗ ΣΦΑΛΜΑΤΟΣ: Ομαλοποίηση ονομάτων στηλών για το Lot Number
                if 'lot_number' in df_trace.columns and 'Lot Number' not in df_trace.columns:
                    df_trace = df_trace.rename(columns={'lot_number': 'Lot Number'})
                
                # Καθαρισμός των LOT για να μην "σκάει" στα κενά
                df_trace['Lot Number'] = df_trace.get('Lot Number', '').fillna('-').astype(str).str.strip()
                df_trace['lot_cocktail'] = df_trace.get('lot_cocktail', '').fillna('-').astype(str).str.strip()
                
                cocktails_in_log = sorted([c for c in df_trace['cocktail_name'].unique() if str(c).strip() not in ['nan', 'None', '']])
                
                col_fw1, col_fw2, col_fw3 = st.columns(3)
                sel_fw_cocktail = col_fw1.selectbox("1. Ελαττωματικό Cocktail:", ["-- Επιλογή --"] + cocktails_in_log)
                search_fw_date = col_fw2.text_input("2. Ημερομηνία (π.χ. 15/06/2026):", placeholder="DD/MM/YYYY")
                search_fw_lot = col_fw3.text_input("3. Ή LOT (προαιρετικά):", placeholder="π.χ. ZMB-1506")
                
                if st.button("➕ Προσθήκη στην Ανάλυση", type="primary"):
                    if sel_fw_cocktail != "-- Επιλογή --" and (search_fw_date or search_fw_lot):
                        # Βρίσκουμε την προβληματική παρτίδα
                        match = df_trace[df_trace['cocktail_name'] == sel_fw_cocktail]
                        if search_fw_date:
                            match = match[match['prod_date'] == search_fw_date.strip()]
                        if search_fw_lot:
                            match = match[match['lot_cocktail'] == search_fw_lot.strip()]
                            
                        if not match.empty:
                            # Απομονώνουμε τα LOT των Πρώτων Υλών
                            lots = set(match['Lot Number'].unique()) - {'-', '', 'nan', 'None'}
                            st.session_state.recall_stack.append({
                                'cocktail': sel_fw_cocktail, 
                                'date': search_fw_date, 
                                'lot': search_fw_lot,
                                'lots': lots
                            })
                            st.rerun()
                        else:
                            st.error("⚠️ Δεν βρέθηκε παρτίδα με αυτά τα στοιχεία. Ελέγξτε την ημερομηνία (DD/MM/YYYY).")
                    else:
                        st.warning("Παρακαλώ επιλέξτε κοκτέιλ και δώστε ημερομηνία ή LOT.")

                # ========================================================
                # ΕΜΦΑΝΙΣΗ & ΑΛΓΟΡΙΘΜΟΣ ΑΝΑΛΥΣΗΣ
                # ========================================================
                if st.session_state.recall_stack:
                    st.write("---")
                    
                    col_clear1, col_clear2 = st.columns([3, 1])
                    col_clear1.markdown("### 🔍 Ενεργή Ανάλυση (Λίστα Ελαττωματικών)")
                    if col_clear2.button("🧹 Καθαρισμός Ανάλυσης"):
                        st.session_state.recall_stack = []
                        st.rerun()

                    for i, item in enumerate(st.session_state.recall_stack):
                        st.info(f"{i+1}. 🍹 **{item['cocktail']}** | Ημ: {item['date']} | LOT: {item['lot']} \n\n Ύποπτα LOT Υλικών: {list(item['lots'])}")
                    
                    st.write("---")
                    
                    # Ο ΑΛΓΟΡΙΘΜΟΣ ΤΗΣ ΔΙΑΣΤΑΥΡΩΣΗΣ
                    target_lots = set()
                    
                    if len(st.session_state.recall_stack) == 1:
                        target_lots = st.session_state.recall_stack[0]['lots']
                        st.markdown("### 🚨 Ακτίνα Ζημιάς (Βάσει 1 Κοκτέιλ)")
                        st.write("Ελέγχουμε **ΟΛΑ** τα υλικά αυτού του κοκτέιλ, καθώς δεν έχουμε δεύτερο δείγμα για διασταύρωση.")
                    else:
                        st.markdown("### 🎯 Ακτίνα Ζημιάς (Με Διασταύρωση)")
                        target_lots = st.session_state.recall_stack[0]['lots']
                        for item in st.session_state.recall_stack[1:]:
                            target_lots = target_lots.intersection(item['lots'])
                        
                        if target_lots:
                            # 🚀 -------------------------------------------------------------
                            # 🚀 ΝΕΟ: ΑΝΙΧΝΕΥΣΗ ΟΝΟΜΑΤΟΣ ΠΡΩΤΗΣ ΥΛΗΣ ΑΠΟ ΤΟ ΚΟΙΝΟ LOT
                            # 🚀 -------------------------------------------------------------
                            df_matched_ingredients = df_trace[df_trace['Lot Number'].isin(target_lots)]
                            ing_lot_pairs = []
                            for lot in target_lots:
                                # Βρίσκουμε ποια ονόματα υλικών έχουν αυτό το LOT
                                ing_names = df_matched_ingredients[df_matched_ingredients['Lot Number'] == lot]['ingredient_name'].unique().tolist()
                                ing_names_str = ", ".join(ing_names)
                                ing_lot_pairs.append(f"💥 **{ing_names_str}** (LOT: `{lot}`)")
                            
                            common_ing_text = " και ".join(ing_lot_pairs)
                            st.success(f"🎯 **Ο ΕΝΟΧΟΣ ΒΡΕΘΗΚΕ!** Τα κοκτέιλ μοιράζονται το εξής προβληματικό ποτό: {common_ing_text}")
                            # -------------------------------------------------------------
                        else:
                            st.error("⚠️ Κανένα κοινό υλικό στα LOT! Τα κοκτέιλ αυτά δεν συνδέονται μέσω των πρώτων υλών. Το πρόβλημα ίσως βρίσκεται αλλού.")

                    # ΕΜΦΑΝΙΣΗ ΑΠΟΤΕΛΕΣΜΑΤΩΝ & ΛΙΣΤΑΣ ΠΕΛΑΤΩΝ
                    if target_lots:
                        df_blast_radius = df_trace[df_trace['Lot Number'].isin(target_lots)]
                        
                        df_blast_summary = df_blast_radius.groupby(["prod_date", "customer", "cocktail_name", "lot_cocktail"]).agg({
                            "pieces": "first",
                            "ingredient_name": lambda x: ", ".join(set(x)) 
                        }).reset_index().rename(columns={
                            "prod_date": "📅 Ημερομηνία", 
                            "customer": "👤 Πελάτης", 
                            "cocktail_name": "🍹 Cocktail", 
                            "lot_cocktail": "🔢 LOT", 
                            "pieces": "📦 Τμχ",
                            "ingredient_name": "⚠️ Ύποπτο Υλικό που περιέχει"
                        })
                        
                        st.warning("⚠️ **ΠΡΟΣΟΧΗ:** Τα παρακάτω προϊόντα πρέπει να ελεγχθούν / ανακληθούν!")
                        st.dataframe(df_blast_summary, use_container_width=True, hide_index=True)
                        
                        affected_customers = df_blast_summary["👤 Πελάτης"].unique().tolist()
                        st.error(f"📞 Πελάτες προς ενημέρωση: **{', '.join(affected_customers)}**")
                        
                        # --- ΔΗΜΙΟΥΡΓΙΑ ΕΚΤΥΠΩΣΗΣ ΕΠΙΚΟΙΝΩΝΙΑΣ ---
                        st.divider()
                        st.markdown("### 📞 Λίστα Επικοινωνίας & Ανάκλησης")
                        
                        res_phones = supabase.table("customers").select("name, phone").execute()
                        phone_dict = {c['name']: c.get('phone', 'Μη διαθέσιμο') for c in res_phones.data} if res_phones.data else {}
                        
                        from datetime import datetime
                        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                            
                        html_recall = f"""
                        <!DOCTYPE html>
                        <html lang="el">
                        <head>
                            <meta charset='UTF-8'>
                            <title>Λίστα Ανάκλησης</title>
                            <style>
                                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #333; background-color: #f9f9f9; }}
                                .header {{ text-align: center; border-bottom: 4px solid #d32f2f; padding-bottom: 15px; margin-bottom: 30px; }}
                                h1 {{ color: #d32f2f; margin: 0; text-transform: uppercase; font-size: 26px; }}
                                .meta-info {{ color: #555; font-size: 15px; margin-top: 10px; }}
                                .customer-card {{ background: white; border: 1px solid #ddd; padding: 20px; margin-bottom: 25px; border-radius: 8px; border-left: 6px solid #d32f2f; box-shadow: 0 2px 5px rgba(0,0,0,0.05); page-break-inside: avoid; }}
                                .cust-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 15px; }}
                                .cust-name {{ font-size: 20px; font-weight: bold; color: #1a1a1a; margin: 0; }}
                                .phone {{ font-size: 18px; color: #1976d2; font-weight: bold; background: #e3f2fd; padding: 5px 12px; border-radius: 20px; }}
                                table {{ width: 100%; border-collapse: collapse; }}
                                th, td {{ border: 1px solid #eee; padding: 10px; text-align: left; font-size: 14px; }}
                                th {{ background-color: #f8f9fa; color: #444; }}
                                .lot-badge {{ background: #d32f2f; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-family: monospace; letter-spacing: 1px; }}
                                .footer {{ text-align: center; color: #999; font-size: 12px; border-top: 1px solid #ccc; padding-top: 10px; margin-top: 40px; }}
                            </style>
                        </head>
                        <body>
                            <div class="header">
                                <h1>🚨 ΛΙΣΤΑ ΕΠΙΚΟΙΝΩΝΙΑΣ ΓΙΑ ΕΠΕΙΓΟΥΣΑ ΑΝΑΚΛΗΣΗ</h1>
                                <div class="meta-info">
                                    <b>Ημερομηνία Εξαγωγής Αναφοράς:</b> {now_str}
                                </div>
                            </div>
                        """
                        
                        grouped_blast = df_blast_summary.groupby("👤 Πελάτης")
                        for cust_name, group in grouped_blast:
                            phone = phone_dict.get(cust_name, "Μη διαθέσιμο")
                            html_recall += f"""
                            <div class="customer-card">
                                <div class="cust-header">
                                    <div class="cust-name">👤 {cust_name}</div>
                                    <div class="phone">📞 {phone}</div>
                                </div>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Ημερομηνία Παραλαβής</th>
                                            <th>Cocktail προς Έλεγχο</th>
                                            <th>Ακριβές LOT</th>
                                            <th>Ποσότητα</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                            """
                            for _, row in group.iterrows():
                                html_recall += f"""
                                        <tr>
                                            <td>{row['📅 Ημερομηνία']}</td>
                                            <td><b>{row['🍹 Cocktail']}</b></td>
                                            <td><span class="lot-badge">{row['🔢 LOT']}</span></td>
                                            <td><b>{row['📦 Τμχ']} τμχ</b></td>
                                        </tr>
                                """
                            html_recall += """
                                    </tbody>
                                </table>
                            </div>
                            """
                            
                        html_recall += """
                            <div class="footer">
                                Η παρούσα αναφορά εξάγεται από το σύστημα ιχνηλασιμότητας CABCLUB.<br>
                                Παρακαλούμε καλέστε άμεσα τους παραπάνω πελάτες για απόσυρση των αναγραφόμενων παρτίδων.
                            </div>
                        </body>
                        </html>
                        """
                        
                        st.download_button(
                            label="🖨️ Λήψη Λίστας Επικοινωνίας Πελατών (HTML)",
                            data=html_recall,
                            file_name=f"Recall_Action_Plan_{datetime.now().strftime('%d%m%Y')}.html",
                            mime="text/html",
                            type="primary",
                            use_container_width=True
                        )
            else:
                st.info("Δεν υπάρχουν δεδομένα παραγωγής στο σύστημα για έλεγχο.")
    
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
            # 🔧 FIX: πριν ελεγχόταν ΜΟΝΟ το άνω όριο (π.χ. ψυγείο στους -50°C περνούσε ως
            # "ΕΝΤΟΣ ΟΡΙΩΝ"). Τώρα ελέγχεται και κάτω όριο. Ενδεικτικά εύρη: Ψυγείο 0–7°C,
            # Κατάψυξη -25–15°C — προσάρμοσέ τα αν η δική σας πολιτική ορίζει διαφορετικά.
            if is_freezer:
                is_ok = -25.0 <= temp <= -15.0
            else:
                is_ok = 0.0 <= temp <= 7.0
            
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
                st.subheader(f"📊 Οικονομικό Προφίλ & Ιστορικό: {sel_name}")
                
                res_prod = supabase.table("production_log").select("prod_date, prod_time, cocktail_name, lot_cocktail, pieces, is_from_stock, free_pieces, discounted_pieces, discount_pct").eq("customer", sel_name).order("prod_date", desc=True).execute()
                
                if res_prod.data:
                    df_p = pd.DataFrame(res_prod.data)
                    df_p_clean = df_p.drop_duplicates(subset=["prod_date", "prod_time", "lot_cocktail", "cocktail_name"]).copy()
                    
                    def safe_int(val):
                        try: return int(float(val)) if pd.notna(val) and str(val).strip() != "" else 0
                        except: return 0

                    def safe_float(val):
                        try: return float(val) if pd.notna(val) and str(val).strip() != "" else 0.0
                        except: return 0.0

                    # 🚀 ΤΟ ΚΛΕΙΔΙ: Τραβάμε τη Γενική Έκπτωση του πελάτη από τα στοιχεία του!
                    global_discount = safe_float(customer_data.get('discount', 0))

                    total_turnover = 0.0
                    total_savings = 0.0
                    
                    total_pieces = safe_int(df_p_clean["pieces"].sum())
                    total_free = safe_int(df_p_clean["free_pieces"].fillna(0).apply(safe_int).sum())
                    total_discounted = safe_int(df_p_clean["discounted_pieces"].fillna(0).apply(safe_int).sum())
                    
                    for _, row in df_p_clean.iterrows():
                        cocktail_name = row["cocktail_name"]
                        cat_price = float(recipe_prices.get(cocktail_name, 0.0))
                        
                        t_pcs = safe_int(row["pieces"])
                        f_pcs = safe_int(row.get("free_pieces", 0))
                        s_pcs = safe_int(row.get("discounted_pieces", 0))
                        s_pct = safe_float(row.get("discount_pct", 0.0))
                        
                        # Μαθηματικά ολόιδια με το παλιό σου σύστημα
                        s_pcs = min(s_pcs, max(0, t_pcs - f_pcs))
                        normal_pcs = t_pcs - f_pcs - s_pcs
                        
                        # 1. Βρίσκουμε την τιμή ΑΦΟΥ εφαρμοστεί η Γενική Έκπτωση του πελάτη
                        price_after_global = cat_price * (1 - (global_discount / 100.0))
                        
                        # 2. Υπολογισμός Εσόδων
                        rev_normal = normal_pcs * price_after_global
                        rev_special = s_pcs * price_after_global * (1 - (s_pct / 100.0))
                        
                        row_turnover = max(0.0, rev_normal + rev_special)
                        total_turnover += row_turnover
                        
                        # 3. Υπολογισμός Οφέλους Πελάτη (Όσα θα πλήρωνε χωρίς ΚΑΜΙΑ έκπτωση - Όσα πλήρωσε τελικά)
                        row_full_value = t_pcs * cat_price
                        row_savings = max(0.0, row_full_value - row_turnover)
                        total_savings += row_savings

                    # Εμφάνιση του Ταμπλό
                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("💰 Συνολικός Τζίρος", f"{total_turnover:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    k2.metric("📦 Συνολικά Τμχ", f"{total_pieces}")
                    k3.metric("🎁 Δώρα (100%)", f"{total_free}")
                    k4.metric("🏷️ Εκπτωμένα Τμχ", f"{total_discounted}")
                    k5.metric("💸 Όφελος Πελάτη", f"{total_savings:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'), "+ Κέρδος", delta_color="normal")
                    
                    st.divider()
                    
                    with st.expander("📜 Αναλυτικό Ιστορικό Παραγγελιών", expanded=False):
                        st.dataframe(
                            df_p_clean.rename(columns={"prod_date": "Ημερομηνία", "cocktail_name": "Cocktail", "pieces": "Τεμάχια"})[["Ημερομηνία", "Cocktail", "Τεμάχια"]],
                            use_container_width=True, hide_index=True
                        )
                else:
                    st.info("Δεν βρέθηκε ιστορικό παραγωγής για αυτόν τον πελάτη.")

                st.divider()

                st.subheader("💰 Οικονομικό Ιστορικό & Αναλυτική Κερδοφορία")
                res_orders = supabase.table("b2b_orders").select("*").eq("customer_name", sel_name).order("created_at", desc=True).execute()
                
                if res_orders.data:
                    with st.expander("🖨️ Εξαγωγή & Εκτύπωση Ιστορικού (PDF/HTML)", expanded=False):
                        st.write("Δημιουργήστε μια απόλυτα αναλυτική αναφορά με Κόστος και Κέρδος για τον πελάτη.")
                        
                        export_mode = st.radio("Τι θέλετε να περιλαμβάνει η αναφορά;", ["Όλο το Ιστορικό Αγορών", "Συγκεκριμένη Παραγγελία"], horizontal=True)
                        
                        orders_to_export = []
                        if export_mode == "Συγκεκριμένη Παραγγελία":
                            order_dict = {o['id']: f"{str(o['created_at'])[:10]} | Αξία: {float(o['total_amount']):.2f}€" for o in res_orders.data}
                            sel_export_id = st.selectbox("Επιλέξτε Παραγγελία για εξαγωγή:", options=list(order_dict.keys()), format_func=lambda x: order_dict[x])
                            orders_to_export = [o for o in res_orders.data if o['id'] == sel_export_id]
                        else:
                            orders_to_export = res_orders.data
                            
                        if st.button("📄 Δημιουργία Απόλυτης Αναφοράς"):
                            with st.spinner("Υπολογισμός Κόστους & Κέρδους..."):
                                # --- 1. ΦΟΡΤΩΣΗ "ΕΞΥΠΝΩΝ" ΔΕΔΟΜΕΝΩΝ ΟΠΩΣ ΣΤΟ DASHBOARD ---
                                df_ing = pd.DataFrame(supabase.table("ingredients").select("name, price, volume").execute().data)
                                df_items = pd.DataFrame(supabase.table("recipe_items").select("recipe_id, ingredient_name, ml_per_unit").execute().data)
                                df_recipes = pd.DataFrame(supabase.table("recipes").select("id, name, catalog_price").execute().data)
                                res_log_full = supabase.table("production_log").select("*").eq("customer", sel_name).execute()
                                df_sales_raw = pd.DataFrame(res_log_full.data)
                                
                                # --- 2. ΜΑΘΗΜΑΤΙΚΑ ΚΟΣΤΟΥΣ & ΕΣΟΔΩΝ ---
                                df_ing['cost_per_ml'] = pd.to_numeric(df_ing.get('price', 0), errors='coerce') / pd.to_numeric(df_ing.get('volume', 1), errors='coerce')
                                ing_cost_dict = dict(zip(df_ing['name'], df_ing['cost_per_ml']))
                                
                                mat_cost_by_id = {}
                                for rid in df_items['recipe_id'].unique():
                                    sub = df_items[df_items['recipe_id'] == rid]
                                    mat_cost_by_id[rid] = sum(pd.to_numeric(item.get('ml_per_unit', 0), errors='coerce') * ing_cost_dict.get(item.get('ingredient_name'), 0) for _, item in sub.iterrows() if str(item.get('ingredient_name')).strip() != "Νερό")
                                    
                                # 🔧 FIX: πριν ήταν hardcoded 0.22 ασύνδετο από το Κοστολόγιο· τώρα κόστος ανά κοκτέιλ
                                name_to_cost = {r['name']: get_unit_cost_for_cocktail(r['name'], mat_cost_by_id.get(r['id'], 0.0)) for _, r in df_recipes.iterrows()}
                                recipe_price_dict = dict(zip(df_recipes['name'], pd.to_numeric(df_recipes.get('catalog_price', 0), errors='coerce')))
                                
                                global_discount = float(customer_data.get('discount', 0))
                                
                                if not df_sales_raw.empty:
                                    # 🚀 ΝΕΑ ΛΟΓΙΚΗ ΑΝΙΧΝΕΥΣΗΣ ΣΤΟΚ: ΠΡΙΝ κάνουμε drop duplicates, αθροίζουμε τα ml κάθε κοκτέιλ!
                                    # Αν τα συνολικά ML ενός κοκτέιλ είναι 0, τότε είναι Στοκ.
                                    df_sales_raw['total_ml'] = pd.to_numeric(df_sales_raw['total_ml'], errors='coerce').fillna(0)
                                    df_ml_sum = df_sales_raw.groupby(["prod_date", "prod_time", "cocktail_name", "lot_cocktail"])['total_ml'].sum().reset_index()
                                    df_ml_sum = df_ml_sum.rename(columns={'total_ml': 'sum_ml'})
                                    
                                    df_sales = df_sales_raw.drop_duplicates(subset=["prod_date", "prod_time", "cocktail_name", "lot_cocktail"]).copy()
                                    df_sales = pd.merge(df_sales, df_ml_sum, on=["prod_date", "prod_time", "cocktail_name", "lot_cocktail"], how="left")
                                    
                                    df_sales['match_date'] = pd.to_datetime(df_sales['prod_date'], format='%d/%m/%Y', errors='coerce').dt.strftime('%Y-%m-%d')
                                    
                                    df_sales['t_pcs'] = pd.to_numeric(df_sales.get('pieces', 0), errors='coerce').fillna(0)
                                    df_sales['f_pcs'] = pd.to_numeric(df_sales.get('free_pieces', 0), errors='coerce').fillna(0)
                                    df_sales['s_pcs'] = pd.to_numeric(df_sales.get('discounted_pieces', 0), errors='coerce').fillna(0)
                                    df_sales['s_pct'] = pd.to_numeric(df_sales.get('discount_pct', 0), errors='coerce').fillna(0)
                                    df_sales['s_pcs'] = df_sales.apply(lambda r: min(r['s_pcs'], max(0, r['t_pcs'] - r['f_pcs'])), axis=1)
                                    df_sales['normal_pcs'] = df_sales['t_pcs'] - df_sales['f_pcs'] - df_sales['s_pcs']
                                    
                                    df_sales['catalog_price'] = df_sales['cocktail_name'].map(recipe_price_dict).fillna(0)
                                    df_sales['price_after_global'] = df_sales['catalog_price'] * (1 - (global_discount / 100))
                                    df_sales['rev_normal'] = df_sales['normal_pcs'] * df_sales['price_after_global']
                                    df_sales['rev_special'] = df_sales['s_pcs'] * df_sales['price_after_global'] * (1 - (df_sales['s_pct'] / 100))
                                    df_sales['Theoretical_Revenue'] = (df_sales['rev_normal'] + df_sales['rev_special']).clip(lower=0)
                                    
                                    def get_actual_cost(row):
                                        catalog_c = name_to_cost.get(row['cocktail_name'], get_unit_cost_for_cocktail(row['cocktail_name'], 0.0))
                                        if 'applied_cost' in row and pd.notna(row['applied_cost']): return float(row['applied_cost'])
                                        return catalog_c

                                    df_sales['Final_Unit_Cost'] = df_sales.apply(get_actual_cost, axis=1)
                                    df_sales['Total_Cost'] = df_sales['t_pcs'] * df_sales['Final_Unit_Cost']
                                    df_sales['Profit'] = df_sales['Theoretical_Revenue'] - df_sales['Total_Cost']
                                
                                # --- 3. ΔΗΜΙΟΥΡΓΙΑ HTML ---
                                now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                                
                                html_content = f"""
                                <!DOCTYPE html>
                                <html lang="el">
                                <head>
                                    <meta charset="UTF-8">
                                    <title>Οικονομική Καρτέλα - {sel_name}</title>
                                    <style>
                                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; padding: 20px; }}
                                        .container {{ max-width: 1100px; margin: auto; border: 1px solid #ddd; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }}
                                        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1a3a5f; padding-bottom: 10px; margin-bottom: 20px; }}
                                        .header h1 {{ color: #1a3a5f; margin: 0; font-size: 24px; }}
                                        .cust-info {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid #1a3a5f; margin-bottom: 20px; }}
                                        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 12px; }}
                                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle; }}
                                        th {{ background-color: #1a3a5f; color: white; font-weight: bold; }}
                                        .text-left {{ text-align: left; }}
                                        .order-date-row {{ background-color: #e8f4f8; font-weight: bold; font-size: 14px; color: #1a3a5f; text-align: left; }}
                                        .free-badge {{ color: #d32f2f; font-weight: bold; }}
                                        .profit-pos {{ color: #2e7d32; font-weight: bold; }}
                                        .profit-neg {{ color: #d32f2f; font-weight: bold; }}
                                        .total-row {{ background-color: #1a3a5f; color: white; font-weight: bold; font-size: 14px; }}
                                        .stock-row {{ background-color: #fff4e5 !important; }}
                                        .stock-badge {{ font-size: 10px; font-weight: bold; background-color: #ff9800; color: white; padding: 2px 5px; border-radius: 4px; margin-left: 5px; vertical-align: middle; }}
                                    </style>
                                </head>
                                <body>
                                    <div class="container">
                                        <div class="header">
                                            <h1>Αναλυτική Καρτέλα (Έσοδα, Κόστος, Κέρδος)</h1>
                                            <p>Εκτύπωση: {now_str}</p>
                                        </div>
                                        <div class="cust-info">
                                            <p><b>Επωνυμία:</b> {sel_name} | <b>ΑΦΜ:</b> {customer_data.get('afm', '-')} | <b>Γενική Έκπτωση:</b> {global_discount}%</p>
                                        </div>
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th width="25%" class="text-left">Προϊόν (Cocktail)</th>
                                                    <th width="10%">Τιμή<br>(μετά εκπτ.)</th>
                                                    <th width="12%">Τεμάχια<br>(Χρεώσιμα / Δώρα)</th>
                                                    <th width="12%">Έσοδα<br>Πώλησης</th>
                                                    <th width="12%">Κόστος<br>Υλικών</th>
                                                    <th width="12%">Καθαρό<br>Κέρδος</th>
                                                    <th width="10%">Margin %</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                """
                                
                                grand_rev, grand_cost, grand_prof = 0, 0, 0
                                
                                for o in orders_to_export:
                                    o_date_raw = str(o['created_at'])[:10]
                                    date_formatted = datetime.strptime(o_date_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
                                    
                                    html_content += f"""<tr class="order-date-row"><td colspan="7">📅 Παραγγελία: {date_formatted}</td></tr>"""
                                    
                                    if not df_sales.empty:
                                        day_sales = df_sales[df_sales['match_date'] == o_date_raw]
                                        
                                        if not day_sales.empty:
                                            # 🚀 ΝΕΑ ΛΟΓΙΚΗ ΟΜΑΔΟΠΟΙΗΣΗΣ: Αθροίζει ίδιο Cocktail + ίδιο LOT!
                                            grouped_day_sales = day_sales.groupby(["cocktail_name", "lot_cocktail"]).agg({
                                                "t_pcs": "sum",
                                                "f_pcs": "sum",
                                                "s_pcs": "sum",
                                                "s_pct": "max",
                                                "Theoretical_Revenue": "sum",
                                                "Total_Cost": "sum",
                                                "Profit": "sum",
                                                "sum_ml": "sum",
                                                "price_after_global": "first",
                                                "ingredient_name": "first"
                                            }).reset_index()

                                            for _, row in grouped_day_sales.iterrows():
                                                c_name = row['cocktail_name']
                                                
                                                # 🚀 Ο ΝΕΟΣ ΑΠΟΛΥΤΟΣ ΑΙΣΘΗΤΗΡΑΣ ΣΤΟΚ
                                                is_stock = float(row.get("sum_ml", 1.0)) == 0.0 or ("Έτοιμο Προϊόν" in str(row.get("ingredient_name", "")))
                                                
                                                lot_c = str(row['lot_cocktail'])
                                                if lot_c == 'nan' or not lot_c: lot_c = '-'
                                                
                                                stock_label = "<span class='stock-badge'>ΑΠΟ ΣΤΟΚ</span>" if is_stock else ""
                                                row_class = "stock-row" if is_stock else ""
                                                
                                                display_name = f"{c_name} {stock_label}<br><span style='font-size:11px; color:#777;'>↳ LOT: {lot_c}</span>"
                                                
                                                p_price = row['price_after_global']
                                                
                                                t_pcs = int(row['t_pcs'])
                                                f_pcs = int(row['f_pcs'])
                                                s_pcs = int(row['s_pcs'])
                                                s_pct = float(row['s_pct'])
                                                normal_pcs = max(0, t_pcs - f_pcs - s_pcs)
                                                
                                                rev = row['Theoretical_Revenue']
                                                cost = row['Total_Cost']
                                                prof = row['Profit']
                                                margin = (prof / rev * 100) if rev > 0 else 0
                                                
                                                grand_rev += rev
                                                grand_cost += cost
                                                grand_prof += prof
                                                
                                                # Δημιουργία της ετικέτας των δώρων/εκπτώσεων
                                                details_arr = []
                                                if normal_pcs > 0:
                                                    details_arr.append(f"{normal_pcs} κανονικά")
                                                if s_pcs > 0:
                                                    details_arr.append(f"<span style='color:#1976d2; font-weight:bold;'>{s_pcs} με έκπτ. -{s_pct:g}%</span>")
                                                if f_pcs > 0:
                                                    details_arr.append(f"<span class='free-badge'>{f_pcs} δώρα</span>")
                                                    
                                                if details_arr:
                                                    details_html = " / ".join(details_arr)
                                                    pcs_str = f"<b>{t_pcs} τμχ</b><br><span style='font-size:11px; color:#555;'>({details_html})</span>"
                                                else:
                                                    pcs_str = f"<b>{t_pcs} τμχ</b>"
                                                    
                                                prof_class = "profit-pos" if prof >= 0 else "profit-neg"
                                                
                                                html_content += f"""
                                                <tr class="{row_class}">
                                                    <td class="text-left">{display_name}</td>
                                                    <td>{p_price:.2f} €</td>
                                                    <td>{pcs_str}</td>
                                                    <td><b>{rev:.2f} €</b></td>
                                                    <td>{cost:.2f} €</td>
                                                    <td class="{prof_class}">{prof:.2f} €</td>
                                                    <td class="{prof_class}">{margin:.1f}%</td>
                                                </tr>
                                                """
                                        else:
                                            html_content += f"""<tr><td colspan="7" class="text-left" style="color:#666;">{o['order_details']}</td></tr>"""
                                    else:
                                        html_content += f"""<tr><td colspan="7" class="text-left" style="color:#666;">{o['order_details']}</td></tr>"""
                                        
                                # --- ΠΡΟΣΘΗΚΗ ΦΠΑ ΚΑΙ ΓΕΝΙΚΟΥ ΤΖΙΡΟΥ ΣΤΟ HTML ---
                                html_content += f"""
                                            </tbody>
                                            <tfoot>
                                                <tr class="total-row">
                                                    <td colspan="3" style="text-align: right;">ΚΑΘΑΡΑ ΣΥΝΟΛΑ ΙΣΤΟΡΙΚΟΥ:</td>
                                                    <td>{grand_rev:.2f} €</td>
                                                    <td>{grand_cost:.2f} €</td>
                                                    <td>{grand_prof:.2f} €</td>
                                                    <td>{((grand_prof / grand_rev * 100) if grand_rev > 0 else 0):.1f}%</td>
                                                </tr>
                                                <tr style="background-color: #e8f4f8; color: #1a3a5f; font-weight: bold;">
                                                    <td colspan="3" style="text-align: right;">ΣΥΝΟΛΙΚΟΣ ΦΠΑ (24%):</td>
                                                    <td colspan="4">{(grand_rev * 0.24):.2f} €</td>
                                                </tr>
                                                <tr style="background-color: #1a3a5f; color: white; font-weight: bold; font-size: 15px;">
                                                    <td colspan="3" style="text-align: right;">ΓΕΝΙΚΟΣ ΤΖΙΡΟΣ (ΜΕ ΦΠΑ):</td>
                                                    <td colspan="4">{(grand_rev * 1.24):.2f} €</td>
                                                </tr>
                                            </tfoot>
                                        </table>
                                        <p style="text-align:center; font-size:11px; color:#999;">Αυτόματοι υπολογισμοί βάσει τρέχοντος κοστολογίου συνταγών.</p>
                                    </div>
                                </body>
                                </html>
                                """
                                
                            st.download_button(
                                label="📥 Λήψη Αναλυτικής Αναφοράς Κερδοφορίας (HTML / PDF)",
                                data=html_content,
                                file_name=f"Profit_Report_{sel_name.replace(' ', '_')}.html",
                                mime="text/html",
                                type="primary"
                            )
                            st.info("💡 **Οδηγία:** Ανοίξτε το αρχείο στον browser σας και πατήστε **Ctrl+P** (Print) για να το αποθηκεύσετε ως ένα τέλειο PDF!")
                    
                    st.divider()

                    # --- ΛΙΣΤΑ ΠΑΡΑΓΓΕΛΙΩΝ (EXPANDERS) ΜΕ ΦΠΑ ---
                    for order in res_orders.data:
                        order_id = order['id']
                        current_amt = float(order['total_amount'])
                        fpa_amt = current_amt * 0.24
                        final_with_fpa = current_amt + fpa_amt
                        details = str(order['order_details'])
                        
                        import re
                        base_amt = current_amt
                        match_base = re.search(r"Αρχική Αξία:\s*([\d\.]+)", details)
                        if match_base:
                            base_amt = float(match_base.group(1))

                        with st.expander(f"🛒 Παραγγελία {str(order['created_at'])[:10]} | Καθαρή: {current_amt:.2f}€ | Με ΦΠΑ: {final_with_fpa:.2f}€"):
                            st.info(f"**Αρχική Αξία (προ εκπτώσεων):** {base_amt:.2f} €\n\n**Καθαρή Χρέωση:** {current_amt:.2f} €\n\n**ΦΠΑ (24%):** {fpa_amt:.2f} €\n\n**Τελικό Πληρωτέο:** {final_with_fpa:.2f} €")
                            st.caption(f"Λεπτομέρειες:\n{details}")
                            
                            if st.button("🗑️ Διαγραφή Ολόκληρης Παραγγελίας", key=f"del_o_{order_id}"):
                                with st.spinner("Έλεγχος ασφάλειας..."):
                                    try:
                                        order_date_iso = str(order['created_at'])[:10]
                                        
                                        # 🔧 ΕΞΥΠΝΟΣ ΕΛΕΓΧΟΣ: πριν διαγράψουμε τίποτα, ελέγχουμε αν υπάρχει
                                        # ΑΛΛΗ παραγγελία (b2b_orders) του ίδιου πελάτη ΣΤΗΝ ΙΔΙΑ ημέρα.
                                        # Αν ΔΕΝ υπάρχει (ο κανονικός, ασφαλής κανόνας), σβήνουμε τα πάντα
                                        # μαζί, γρήγορα, με 1 κλικ. Αν ΥΠΑΡΧΕΙ (π.χ. διπλότυπο), το
                                        # production_log είναι κοινό/ασαφές ανάμεσά τους — σβήνουμε ΜΟΝΟ
                                        # την οικονομική εγγραφή, για ασφάλεια, ακριβώς όπως έμαθε η εφαρμογή
                                        # μας πριν λίγο, με τον δύσκολο τρόπο.
                                        res_check = supabase.table("b2b_orders").select("id, created_at").eq("customer_name", sel_name).execute()
                                        same_day_count = 0
                                        if res_check.data:
                                            for r in res_check.data:
                                                try:
                                                    r_iso = pd.to_datetime(r["created_at"]).strftime("%Y-%m-%d")
                                                    if r_iso == order_date_iso:
                                                        same_day_count += 1
                                                except Exception:
                                                    pass

                                        if same_day_count > 1:
                                            supabase.table("b2b_orders").delete().eq("id", order_id).execute()
                                            st.warning(f"⚠️ Βρέθηκαν {same_day_count} παραγγελίες αυτού του πελάτη την ίδια μέρα — για ασφάλεια διαγράφηκε ΜΟΝΟ η οικονομική εγγραφή. Τα δεδομένα παραγωγής είναι κοινά/ασαφή ανάμεσα στις παραγγελίες — αν χρειάζεται πλήρης διαγραφή, χρησιμοποίησε το «📦 Lot Παραγωγής → Ιστορικό» για χειροκίνητη, στοχευμένη διαγραφή.")
                                        else:
                                            prod_res = supabase.table("production_log").select("id, prod_date").eq("customer", sel_name).execute()
                                            ids_to_delete = []
                                            if prod_res.data:
                                                for p in prod_res.data:
                                                    try:
                                                        p_iso = datetime.strptime(str(p['prod_date']).strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
                                                        if p_iso == order_date_iso:
                                                            ids_to_delete.append(p['id'])
                                                    except Exception:
                                                        pass
                                            if ids_to_delete:
                                                supabase.table("production_log").delete().in_("id", ids_to_delete).execute()
                                            supabase.table("b2b_orders").delete().eq("id", order_id).execute()
                                            st.success("✅ Διαγράφηκε ολόκληρη η παραγγελία (οικονομικά + όλα τα υλικά παραγωγής) — ήταν η μοναδική παραγγελία αυτού του πελάτη/ημέρας, οπότε ήταν ασφαλές.")
                                        
                                        import time
                                        time.sleep(1.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Σφάλμα κατά τη διαγραφή: {e}")
                else:
                    st.info("Δεν έχουν δημιουργηθεί ακόμα οικονομικές εγγραφές.")
    # =========================================================================
    # TAB 2: ΠΡΟΣΘΗΚΗ ΝΕΟΥ ΠΕΛΑΤΗ
    # =========================================================================
    with tab_crm2:
        st.subheader("➕ Καταχώρηση Νέου Πελάτη")
        with st.form("new_customer_form_final", clear_on_submit=True):
            n_name = st.text_input("Όνομα / Επωνυμία *")
            n_afm = st.text_input("ΑΦΜ")
            # 🔧 FIX: πριν ήταν text_input (ελεύθερο κείμενο) και αποθηκευόταν ως STRING στη
            # βάση χωρίς κανέναν έλεγχο — πιθανή αιτία των "βρώμικων" τιμών έκπτωσης που
            # χρειάστηκε να διορθώσουμε αμυντικά αλλού (Νεκρό Σημείο, Έσοδα-Έξοδα).
            n_discount = st.number_input("Αρχική Γενική Έκπτωση (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            n_phone = st.text_input("Τηλέφωνο")
            n_email = st.text_input("Email")
            n_addr = st.text_area("Διεύθυνση")
            n_notes = st.text_area("Σημειώσεις")
            
            if st.form_submit_button("💾 Αποθήκευση"):
                if n_name:
                    supabase.table("customers").insert({
                        "name": n_name, "afm": n_afm, "discount": float(n_discount),
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
            st.write("Επιλέξτε μια παραγγελία. Για κάθε κοκτέιλ της, μπορείτε να ορίσετε δωρεάν τεμάχια ή/και ειδική έκπτωση.")

            res_orders = supabase.table("b2b_orders").select("*").eq("customer_name", sel_cust_offers).order("created_at", desc=True).limit(50).execute()
            if res_orders.data:
                df_orders = pd.DataFrame(res_orders.data)
                order_dict = {}
                for _, r in df_orders.iterrows():
                    dt = pd.to_datetime(r['created_at']).tz_localize(None)
                    dt_str = dt.strftime('%d/%m %H:%M')
                    order_dict[r['id']] = f"📅 {dt_str} | Αξία: {float(r['total_amount']):.2f}€"
                
                sel_order_id = st.selectbox("🛒 Επιλογή Παραγγελίας:", options=list(order_dict.keys()), format_func=lambda x: order_dict[x], key="gift_o")
                
                if sel_order_id:
                    selected_order = df_orders[df_orders['id'] == sel_order_id].iloc[0]
                    current_details = selected_order['order_details']
                    
                    clean_display_details = str(current_details).split("\n\n--- ΔΩΡΑ")[0].split("\n\n--- ΕΙΔΙΚΕΣ")[0]
                    st.info(f"**Περιεχόμενο Παραγγελίας:**\n{clean_display_details}")
                    
                    order_dt = pd.to_datetime(selected_order['created_at']).tz_localize(None)
                    prod_date_str = order_dt.strftime('%d/%m/%Y')
                    
                    valid_cocktails = []
                    for line in clean_display_details.split('\n'):
                        if line.strip().startswith('•') or 'τμχ' in line:
                            try:
                                c_name_ext = line.replace('•', '').split(' τμχ ')[1].split(' (Εκ των')[0].split(' (LOT:')[0].strip()
                                valid_cocktails.append(c_name_ext)
                            except:
                                pass

                    res_prod = supabase.table("production_log").select("cocktail_name, pieces, free_pieces, discounted_pieces, discount_pct, prod_time, lot_cocktail").eq("customer", sel_cust_offers).eq("prod_date", prod_date_str).execute()
                    
                    if res_prod.data:
                        import pandas as pd
                        df_prod = pd.DataFrame(res_prod.data).fillna(0)
                        
                        if valid_cocktails:
                            df_prod = df_prod[df_prod['cocktail_name'].isin(valid_cocktails)]
                            
                        # 🚀 Η ΛΥΣΗ ΤΟΥ ΜΥΣΤΗΡΙΟΥ 1: 
                        # Ομαδοποιούμε βάζοντας μέσα ΚΑΙ την ώρα (prod_time) για να ξεχωρίζουν οι παραγγελίες!
                        # Χρησιμοποιούμε 'first' αντί για 'sum' για να μην αθροίζονται τα πολλαπλά υλικά του ίδιου κοκτέιλ.
                        df_grouped = df_prod.groupby(["cocktail_name", "lot_cocktail", "prod_time"], as_index=False).agg({
                            "pieces": "first", 
                            "free_pieces": "first",
                            "discounted_pieces": "first",
                            "discount_pct": "first"
                        })
                        
                        with st.form("apply_gifts_and_discounts_form"):
                            inputs = {}
                            st.markdown("##### ⚙️ Ρυθμίσεις ανά Κωδικό Παραγγελίας & LOT")
                            
                            h1, h2, h3, h4 = st.columns([2.5, 1, 1.2, 1])
                            h1.caption("Κοκτέιλ (Σύνολο Τμχ)")
                            h2.caption("Δωρεάν Τμχ")
                            h3.caption("Τμχ με Έκπτωση")
                            h4.caption("Έκπτωση (%)")
                            
                            for _, prow in df_grouped.iterrows():
                                c_name = prow['cocktail_name']
                                lot_c = prow['lot_cocktail']
                                p_time = prow['prod_time'] # Διαβάζουμε και την Ώρα!
                                t_pcs = int(prow['pieces'])
                                curr_free = int(prow['free_pieces'])
                                curr_s_pcs = int(prow['discounted_pieces'])
                                curr_s_pct = float(prow['discount_pct'])
                                
                                # Ασφαλές κλειδί που περιέχει την ώρα, ώστε το Streamlit να μην μπερδεύει τα πεδία
                                safe_key_suffix = f"{c_name}_{lot_c}_{p_time}".replace("/", "_").replace("-", "_").replace(":", "_").replace(" ", "")
                                
                                c1, c2, c3, c4 = st.columns([2.5, 1, 1.2, 1])
                                # Δείχνουμε την ώρα στην οθόνη για να βλέπεις ξεκάθαρα σε ποια από τις 2 παραγγελίες βάζεις την έκπτωση!
                                c1.write(f"🍹 **{c_name}** ({t_pcs} τμχ) <br><span style='font-size:11px; color:gray;'>LOT: {lot_c} | Ώρα: {p_time}</span>", unsafe_allow_html=True)
                                
                                f_pcs = c2.number_input("Δώρο", min_value=0, max_value=t_pcs, value=curr_free, step=1, key=f"f_{safe_key_suffix}", label_visibility="collapsed")
                                s_pcs = c3.number_input("Τμχ Έκπτωσης", min_value=0, max_value=t_pcs, value=curr_s_pcs, step=1, key=f"s_{safe_key_suffix}", label_visibility="collapsed")
                                s_pct = c4.number_input("% Έκπτωσης", min_value=0.0, max_value=100.0, value=curr_s_pct, step=1.0, key=f"p_{safe_key_suffix}", label_visibility="collapsed")
                                
                                # Σώζουμε και την ώρα στο λεξικό (inputs) για να ξέρει το κουμπί Save πού να "χτυπήσει"
                                inputs[(c_name, lot_c, p_time)] = {"t_pcs": t_pcs, "f_pcs": f_pcs, "s_pcs": s_pcs, "s_pct": s_pct}
                                
                            if st.form_submit_button("💾 Εφαρμογή & Επανυπολογισμός Παραγγελίας", type="primary"):
                                new_total = 0.0
                                gift_text = ""
                                disc_text = ""
                                
                                cust_discount = float(current_discount)
                                
                                with st.spinner("Επανυπολογισμός αξιών..."):
                                    for key, vals in inputs.items():
                                        c_name, lot_c, p_time = key # Διαβάζουμε την ώρα
                                        t_pcs = vals["t_pcs"]
                                        f_pcs = vals["f_pcs"]
                                        s_pcs = vals["s_pcs"]
                                        s_pct = vals["s_pct"]
                                        
                                        if f_pcs + s_pcs > t_pcs:
                                            s_pcs = t_pcs - f_pcs 
                                            
                                        normal_pcs = t_pcs - f_pcs - s_pcs
                                        
                                        # 🚀 Η ΛΥΣΗ ΤΟΥ ΜΥΣΤΗΡΙΟΥ 2: Προσθέτουμε το `.eq("prod_time", p_time)`
                                        # Έτσι η Supabase θα βάλει τα δώρα ΜΟΝΟ στην παραγγελία αυτής της ώρας και θα αφήσει την άλλη ανέγγιχτη!
                                        supabase.table("production_log").update({
                                            "free_pieces": f_pcs,
                                            "discounted_pieces": s_pcs,
                                            "discount_pct": s_pct
                                        }).eq("customer", sel_cust_offers).eq("prod_date", prod_date_str).eq("prod_time", p_time).eq("cocktail_name", c_name).eq("lot_cocktail", lot_c).execute()
                                        
                                        catalog_p = float(recipe_prices.get(c_name, 0.0))
                                        
                                        price_after_global = catalog_p * (1 - (cust_discount / 100))
                                        cost_normal = normal_pcs * price_after_global
                                        cost_spec = s_pcs * price_after_global * (1 - (s_pct / 100))
                                        
                                        new_total += (cost_normal + cost_spec)
                                        
                                        if f_pcs > 0:
                                            gift_text += f"🎁 {f_pcs}x {c_name} (ΔΩΡΟ - LOT: {lot_c} - {p_time})\n"
                                        if s_pcs > 0:
                                            disc_text += f"📉 {s_pcs}x {c_name} (Έκπτωση {s_pct}% - LOT: {lot_c} - {p_time})\n"
                                            
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
# --- 1.5 ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΠΡΩΤΗΣ ΥΛΗΣ (FINAL PRO VERSION - FULL PROFIT TRACKING & CLEAN HTML) ---
elif page == "🔄 Αντικατάσταση":
    st.header("🔄 Μαζική Αντικατάσταση Υλικών & Πρόγνωση Κέρδους")
    st.info("Σύγκριση Τιμών: Οι τιμές πώλησης (Λιανική & Αντιπρόσωπος στο -26%) παραμένουν σταθερές για να φανεί το πραγματικό επιπλέον κέρδος.")

    # --- ΜΑΓΕΙΑ SUPABASE: Φόρτωση φρέσκων δεδομένων (αν δεν υπάρχουν) ---
    res_ing = supabase.table("ingredients").select("*").execute()
    ing_data = res_ing.data if res_ing.data else []
    df_ing_list = []
    for item in ing_data:
        df_ing_list.append({
            "Name": str(item["name"]).strip(), 
            "Price": item["price"],
            "Volume": item["volume"],
            "weight_full": item.get("weight_full", 0.0),
            "Weight_Full": item.get("weight_full", 0.0), 
            "Weight": item.get("weight_full", 0.0),
            "Αλκοόλ %": item["abv"],
            "ABV": item["abv"], 
            "Τιμή/ml": item["price"] / item["volume"] if item["volume"] > 0 else 0
        })
    df_ing = pd.DataFrame(df_ing_list)

    res_all_items = supabase.table("recipe_items").select("*").execute()
    df_all_items = pd.DataFrame(res_all_items.data) if res_all_items.data else pd.DataFrame()
    
    if not df_all_items.empty and not df_ing.empty:
        used_ings = sorted(df_all_items["ingredient_name"].unique().tolist())
        all_ings = sorted(df_ing["Name"].unique().tolist())
        
        # --- ΔΥΝΑΜΙΚΟ UI ΓΙΑ ΠΟΛΛΑΠΛΕΣ ΑΝΤΙΚΑΤΑΣΤΑΣΕΙΣ ---
        if 'swap_rows' not in st.session_state:
            st.session_state.swap_rows = 1

        st.subheader("🛠️ Επιλογή Υλικών προς Αντικατάσταση")
        
        swaps = []
        for i in range(st.session_state.swap_rows):
            col_r1, col_r2 = st.columns(2)
            old_val = col_r1.selectbox(f"❌ Παλιό Υλικό ({i+1}):", options=used_ings, index=None, key=f"old_ing_{i}")
            new_val = col_r2.selectbox(f"✅ Νέο Υλικό ({i+1}):", options=all_ings, index=None, key=f"new_ing_{i}")
            if old_val and new_val and old_val != new_val:
                swaps.append({"old": old_val, "new": new_val})

        col_btn1, col_btn2 = st.columns([1, 4])
        if col_btn1.button("➕ Προσθήκη Γραμμής"):
            st.session_state.swap_rows += 1
            st.rerun()
        if col_btn2.button("🗑️ Καθαρισμός"):
            st.session_state.swap_rows = 1
            for key in list(st.session_state.keys()):
                if key.startswith("old_ing_") or key.startswith("new_ing_"):
                    del st.session_state[key]
            st.rerun()

        st.divider()

        # --- ΥΠΟΛΟΓΙΣΜΟΙ ΑΝ ΥΠΑΡΧΟΥΝ ΕΓΚΥΡΕΣ ΑΛΛΑΓΕΣ ---
        if swaps:
            affected_recipes_ids = set()
            for swap in swaps:
                ids = df_all_items[df_all_items["ingredient_name"] == swap["old"]]["recipe_id"].unique().tolist()
                affected_recipes_ids.update(ids)
            
            if affected_recipes_ids:
                affected_recipes_ids = list(affected_recipes_ids)
                res_rec_info = supabase.table("recipes").select("id, name, catalog_price").in_("id", affected_recipes_ids).execute()
                rec_lookup = {r['id']: r for r in res_rec_info.data}

                analysis_data = []
                for rid in affected_recipes_ids:
                    r_items = df_all_items[df_all_items["recipe_id"] == rid]
                    r_name = rec_lookup[rid]['name']
                    
                    # Κρατάμε σταθερές τις τιμές πώλησης
                    retail_price = rec_lookup[rid]['catalog_price'] or 0.0
                    agent_price = retail_price * 0.74 
                    
                    current_cost = 0.0  # 🔧 συσσωρεύουμε ΜΟΝΟ κόστος υλικών εδώ
                    cost_diff_total = 0.0
                    swap_desc_list = []

                    # Υπολογισμός συνολικού παλιού κόστους & διαφορών από τα swaps
                    for _, item in r_items.iterrows():
                        ing_n = item['ingredient_name']
                        ml = item['ml_per_unit']
                        
                        ing_info = df_ing[df_ing["Name"] == ing_n]
                        if not ing_info.empty:
                            price_ml = ing_info["Τιμή/ml"].values[0]
                            current_cost += ml * price_ml
                            
                        for swap in swaps:
                            if ing_n == swap["old"]:
                                new_ing_info = df_ing[df_ing["Name"] == swap["new"]]
                                if not new_ing_info.empty:
                                    new_price_ml = new_ing_info["Τιμή/ml"].values[0]
                                    diff_ml = new_price_ml - price_ml
                                    cost_diff_total += (ml * diff_ml)
                                    swap_desc_list.append(f"{swap['old']} ➡️ {swap['new']}")

                    if cost_diff_total != 0:
                        # 🔧 FIX: εφαρμόζουμε το ενεργό μοντέλο κόστους (χειροκίνητο ή αυτόματο) και στα δύο
                        full_current_cost = get_unit_cost_for_cocktail(r_name, current_cost)
                        full_new_cost = get_unit_cost_for_cocktail(r_name, current_cost + cost_diff_total)
                        
                        # Υπολογισμός Κέρδους Λιανικής
                        old_retail_profit = retail_price - full_current_cost
                        new_retail_profit = retail_price - full_new_cost
                        diff_retail = new_retail_profit - old_retail_profit
                        
                        # Υπολογισμός Κέρδους Αντιπροσώπου
                        old_agent_profit = agent_price - full_current_cost
                        new_agent_profit = agent_price - full_new_cost
                        diff_agent = new_agent_profit - old_agent_profit

                        analysis_data.append({
                            "Cocktail": r_name,
                            "Αλλαγές": " | ".join(swap_desc_list),
                            "Παλιό Κόστος (€)": full_current_cost,
                            "Νέο Κόστος (€)": full_new_cost,
                            "Λιανική (€)": retail_price,
                            "Παλιό Κέρδος Λιαν. (€)": old_retail_profit,
                            "Νέο Κέρδος Λιαν. (€)": new_retail_profit,
                            "Διαφορά Λιαν. (€)": diff_retail,
                            "Αντιπρόσωπος (€)": agent_price,
                            "Παλιό Κέρδος Αντιπρ. (€)": old_agent_profit,
                            "Νέο Κέρδος Αντιπρ. (€)": new_agent_profit,
                            "Διαφορά Αντιπρ. (€)": diff_agent
                        })

                if analysis_data:
                    df_res = pd.DataFrame(analysis_data)
                    
                    st.subheader(f"📊 Ανάλυση Οικονομικού Αντικτύπου ({len(df_res)} Συνταγές)")
                    
                    # Χρωματισμός Διαφοράς Κέρδους (Πράσινο για θετικό, Κόκκινο για αρνητικό)
                    def style_profit(val):
                        color = '#ff4b4b' if val < 0 else '#00ffcc' if val > 0 else '#ffffff'
                        return f'color: {color}; font-weight: bold'

                    # Μορφοποίηση για καθαρά 2 δεκαδικά (εξαφάνιση περιττών μηδενικών)
                    format_dict = {
                        "Παλιό Κόστος (€)": "{:.2f}",
                        "Νέο Κόστος (€)": "{:.2f}",
                        "Λιανική (€)": "{:.2f}",
                        "Παλιό Κέρδος Λιαν. (€)": "{:.2f}",
                        "Νέο Κέρδος Λιαν. (€)": "{:.2f}",
                        "Διαφορά Λιαν. (€)": "{:.2f}",
                        "Αντιπρόσωπος (€)": "{:.2f}",
                        "Παλιό Κέρδος Αντιπρ. (€)": "{:.2f}",
                        "Νέο Κέρδος Αντιπρ. (€)": "{:.2f}",
                        "Διαφορά Αντιπρ. (€)": "{:.2f}"
                    }

                    # Εμφάνιση του DataFrame
                    st.dataframe(
                        df_res.style.format(format_dict).map(style_profit, subset=['Διαφορά Λιαν. (€)', 'Διαφορά Αντιπρ. (€)']),
                        use_container_width=True,
                        hide_index=True
                    )

                    # --- ΔΗΜΙΟΥΡΓΙΑ ΑΠΛΟΥ HTML REPORT ΓΙΑ SAFARI ---
                    html_rows = ""
                    for _, row in df_res.iterrows():
                        # Χρώματα Λιανικής
                        profit_color_retail = "red" if row['Διαφορά Λιαν. (€)'] < 0 else "green"
                        diff_sign_retail = "+" if row['Διαφορά Λιαν. (€)'] > 0 else ""
                        
                        # Χρώματα Αντιπροσώπου
                        profit_color_agent = "red" if row['Διαφορά Αντιπρ. (€)'] < 0 else "green"
                        diff_sign_agent = "+" if row['Διαφορά Αντιπρ. (€)'] > 0 else ""

                        html_rows += f"""
                        <tr>
                            <td><strong>{row['Cocktail']}</strong><br><small style="color:#666;">{row['Αλλαγές']}</small></td>
                            <td>{row['Παλιό Κόστος (€)']:.2f} ➡️ <b>{row['Νέο Κόστος (€)']:.2f}</b></td>
                            <td style="background-color: #f9f9f9;">
                                <u>Τιμή: {row['Λιανική (€)']:.2f} €</u><br>
                                Παλιό Κέρδος: {row['Παλιό Κέρδος Λιαν. (€)']:.2f} €<br>
                                Νέο Κέρδος: <b>{row['Νέο Κέρδος Λιαν. (€)']:.2f} €</b><br>
                                <span style="color:{profit_color_retail}; font-weight:bold; font-size: 1.1em;">Διαφορά: {diff_sign_retail}{row['Διαφορά Λιαν. (€)']:.2f} €</span>
                            </td>
                            <td>
                                <u>Τιμή: {row['Αντιπρόσωπος (€)']:.2f} €</u><br>
                                Παλιό Κέρδος: {row['Παλιό Κέρδος Αντιπρ. (€)']:.2f} €<br>
                                Νέο Κέρδος: <b>{row['Νέο Κέρδος Αντιπρ. (€)']:.2f} €</b><br>
                                <span style="color:{profit_color_agent}; font-weight:bold; font-size: 1.1em;">Διαφορά: {diff_sign_agent}{row['Διαφορά Αντιπρ. (€)']:.2f} €</span>
                            </td>
                        </tr>
                        """
                        
                    report_html = f"""
                    <!DOCTYPE html>
                    <html lang="el">
                    <head>
                        <meta charset="UTF-8">
                        <title>Αναφορά Αντικατάστασης - CabClub</title>
                        <style>
                            @media print {{
                                @page {{ margin: 1cm; }}
                                body {{ -webkit-print-color-adjust: exact; }}
                                .no-print {{ display: none !important; }}
                            }}
                            body {{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 20px; color: #333; }}
                            .container {{ max-width: 1000px; margin: auto; }}
                            h2 {{ color: #1a3a5f; border-bottom: 2px solid #1a3a5f; padding-bottom: 10px; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; vertical-align: top; }}
                            th {{ background-color: #f4f6f8; color: #333; }}
                            td:first-child {{ text-align: left; vertical-align: middle; }}
                            .print-btn {{ background: #1a3a5f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-bottom: 20px; font-weight: bold; cursor: pointer; border: none; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <button class="no-print print-btn" onclick="window.print()">🖨️ Εκτύπωση Αναφοράς</button>
                            <h2>📊 CabClub: Αναφορά Αντικατάστασης Υλικών & Κερδοφορίας</h2>
                            <p><b>Ημερομηνία:</b> {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}</p>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Cocktail / Αλλαγή</th>
                                        <th>Κόστος Υλικών (€)</th>
                                        <th>Πωλήσεις Λιανικής</th>
                                        <th>Πωλήσεις Αντιπροσώπου</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {html_rows}
                                </tbody>
                            </table>
                        </div>
                    </body>
                    </html>
                    """

                    col_dl1, col_dl2 = st.columns([1, 2])
                    with col_dl1:
                        st.download_button(
                            label="📄 Λήψη Αναφοράς (HTML)",
                            data=report_html,
                            file_name="Replacement_Profit_Report.html",
                            mime="text/html"
                        )
                    st.caption("*(Ανοίξτε το αρχείο στον browser σας (π.χ. Safari) για να δείτε τα αποτελέσματα και να τα εκτυπώσετε)*")

                    st.divider()

                    # --- ΕΚΤΕΛΕΣΗ ΜΑΖΙΚΗΣ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ---
                    st.warning("⚠️ ΠΡΟΣΟΧΗ: Η παρακάτω ενέργεια θα αλλάξει οριστικά τα υλικά στη βάση δεδομένων σας.")
                    confirm = st.checkbox(f"Επιβεβαιώνω την εκτέλεση {len(swaps)} αλλαγών σε {len(df_res)} συνταγές.")
                    if st.button("🚀 ΕΚΤΕΛΕΣΗ ΜΑΖΙΚΗΣ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΤΩΡΑ", type="primary", disabled=not confirm):
                        with st.spinner("Ενημέρωση συστατικών στη βάση δεδομένων..."):
                            for swap in swaps:
                                supabase.table("recipe_items").update({"ingredient_name": swap["new"]}).eq("ingredient_name", swap["old"]).execute()
                            st.success("✅ Όλες οι αντικαταστάσεις ολοκληρώθηκαν με επιτυχία!")
                            st.session_state.swap_rows = 1
                            st.cache_data.clear()
                            time.sleep(2)
                            st.rerun()
                else:
                    st.info("Οι συγκεκριμένες αλλαγές δεν επηρεάζουν καμία συνταγή.")
        else:
            st.info("Επιλέξτε τουλάχιστον ένα ζευγάρι (Παλιό -> Νέο) για να δείτε την πρόγνωση κέρδους.")
    else:
        st.warning("⚠️ Δεν υπάρχουν δεδομένα στην αποθήκη ή στις συνταγές.")
# --- ΕΝΟΤΗΤΑ: ΔΙΑΧΕΙΡΙΣΗ ΠΑΡΑΓΓΕΛΙΩΝ B2B & E-SHOP ---
elif page == "📦 Παραγγελίες B2B":
    st.header("📦 Διαχείριση Παραγγελιών B2B")

    # --- 🔍 ΔΙΑΓΝΩΣΤΙΚΟ: ΣΥΝΕΠΕΙΑ ΜΕ ΤΟ PRODUCTION_LOG ---
    with st.expander("🔍 Έλεγχος Συνέπειας — γιατί ο αριθμός παραγγελιών διαφέρει από το Dashboard"):
        st.caption("Συγκρίνει τις εγγραφές του b2b_orders με τα πραγματικά δεδομένα παραγωγής, για να βρει διπλότυπες ή \"ξεχασμένες\" εγγραφές.")
        if st.button("▶️ Τρέξε τον έλεγχο τώρα"):
            with st.spinner("Ελέγχω..."):
                try:
                    res_all_orders = supabase.table("b2b_orders").select("id, customer_name, created_at, total_amount").execute()
                    res_all_prod = supabase.table("production_log").select("customer, prod_date").execute()

                    df_orders_chk = pd.DataFrame(res_all_orders.data) if res_all_orders.data else pd.DataFrame(columns=["id", "customer_name", "created_at", "total_amount"])
                    df_prod_chk = pd.DataFrame(res_all_prod.data) if res_all_prod.data else pd.DataFrame(columns=["customer", "prod_date"])

                    if not df_orders_chk.empty:
                        df_orders_chk["order_date_iso"] = pd.to_datetime(df_orders_chk["created_at"]).dt.strftime("%Y-%m-%d")
                    if not df_prod_chk.empty:
                        df_prod_chk["prod_date_iso"] = pd.to_datetime(df_prod_chk["prod_date"], format="%d/%m/%Y", errors="coerce").dt.strftime("%Y-%m-%d")

                    valid_prod_keys = set(zip(df_prod_chk["customer"], df_prod_chk["prod_date_iso"])) if not df_prod_chk.empty else set()

                    # 1. Διπλότυπες εγγραφές b2b_orders για ίδιο πελάτη+ημέρα
                    dup_mask = df_orders_chk.duplicated(subset=["customer_name", "order_date_iso"], keep=False) if not df_orders_chk.empty else pd.Series(dtype=bool)
                    df_duplicates = df_orders_chk[dup_mask].sort_values(["customer_name", "order_date_iso"]) if not df_orders_chk.empty else pd.DataFrame()

                    # 2. "Ξεχασμένες" εγγραφές b2b_orders χωρίς καμία αντίστοιχη παραγωγή
                    if not df_orders_chk.empty:
                        df_orders_chk["has_production"] = df_orders_chk.apply(lambda r: (r["customer_name"], r["order_date_iso"]) in valid_prod_keys, axis=1)
                        df_orphaned = df_orders_chk[~df_orders_chk["has_production"]]
                    else:
                        df_orphaned = pd.DataFrame()

                    st.markdown(f"**Σύνολο εγγραφών b2b_orders:** {len(df_orders_chk)}")

                    if not df_duplicates.empty:
                        st.error(f"⚠️ Βρέθηκαν {len(df_duplicates)} εγγραφές σε {df_duplicates.groupby(['customer_name','order_date_iso']).ngroups} διπλότυπα ζευγάρια (ίδιος πελάτης + ίδια ημέρα, 2+ φορές):")
                        st.dataframe(df_duplicates[["id", "customer_name", "order_date_iso", "total_amount"]], use_container_width=True, hide_index=True)
                    else:
                        st.success("✅ Δεν βρέθηκαν διπλότυπες εγγραφές (ίδιος πελάτης + ίδια ημέρα).")

                    if not df_orphaned.empty:
                        st.warning(f"⚠️ Βρέθηκαν {len(df_orphaned)} εγγραφές b2b_orders ΧΩΡΙΣ καμία αντίστοιχη γραμμή παραγωγής (πιθανές \"ξεχασμένες\"):")
                        st.dataframe(df_orphaned[["id", "customer_name", "order_date_iso", "total_amount"]], use_container_width=True, hide_index=True)
                        st.caption("Αυτές οι εγγραφές πιθανόν να προήλθαν από παλιά παραγωγή που διαγράφηκε/επεξεργάστηκε χωρίς να ενημερωθεί το b2b_orders. Μπορείς να τις διαγράψεις χειροκίνητα από το tab «Ιστορικό & Αναζήτηση» παρακάτω αν επιβεβαιώσεις ότι είναι όντως ξεπερασμένες.")
                    else:
                        st.success("✅ Δεν βρέθηκαν 'ξεχασμένες' εγγραφές χωρίς αντίστοιχη παραγωγή.")
                except Exception as e:
                    st.error(f"Σφάλμα ελέγχου: {e}")

        
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
                        # 🚀 ΚΑΘΑΡΙΣΜΟΣ ΚΕΙΜΕΝΟΥ (Αφαίρεση παρενθέσεων)
                        raw_details = str(row['order_details'])
                        clean_lines = []
                        for line in raw_details.split('\n'):
                            if ' (Εκ των' in line:
                                clean_lines.append(line.split(' (Εκ των')[0].strip())
                            else:
                                clean_lines.append(line)
                        clean_details = '\n'.join(clean_lines)

                        st.code(clean_details)
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
                            
                            # Προβολή των κοκτέιλ (ΧΩΡΙΣ ΤΙΣ ΠΑΡΕΝΘΕΣΕΙΣ)
                            items = str(row['order_details']).split('\n')
                            
                            for i, item in enumerate(items):
                                if item.strip(): # Μόνο αν δεν είναι κενή γραμμή
                                    # 🚀 Αν έχει παρένθεση "Εκ των", την κόβουμε!
                                    if ' (Εκ των' in item:
                                        item = item.split(' (Εκ των')[0].strip()
                                    
                                    # Εμφανίζουμε το καθαρό πλέον κείμενο
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
        return rec, ing, items

    with st.spinner("Φόρτωση δεδομένων κόστους..."):
        rec_data, ing_data, items_data = load_simulation_data()

    if rec_data:
        df_recipes = pd.DataFrame(rec_data)
        recipe_prices = dict(zip(df_recipes['name'], pd.to_numeric(df_recipes['catalog_price'], errors='coerce').fillna(0)))
        
        # Υπολογισμός Κόστους
        df_ing = pd.DataFrame(ing_data)
        df_ing['cost_per_ml'] = pd.to_numeric(df_ing.get('price', 0), errors='coerce') / pd.to_numeric(df_ing.get('volume', 1), errors='coerce')
        ing_cost_dict = dict(zip(df_ing['name'], df_ing['cost_per_ml']))
        
        df_items = pd.DataFrame(items_data)
        mat_cost_by_id = {}
        for rid in df_items['recipe_id'].unique():
            sub = df_items[df_items['recipe_id'] == rid]
            mat_cost_by_id[rid] = sum(pd.to_numeric(item.get('ml_per_unit', 0), errors='coerce') * ing_cost_dict.get(item.get('ingredient_name'), 0) for _, item in sub.iterrows() if str(item.get('ingredient_name')).strip() != "Νερό")
            
        # 🔧 FIX: πριν ήταν hardcoded 0.22 ασύνδετο από το Κοστολόγιο· τώρα κόστος ανά κοκτέιλ
        name_to_cost = {r['name']: get_unit_cost_for_cocktail(r['name'], mat_cost_by_id.get(r['id'], 0.0)) for _, r in df_recipes.iterrows()}

        # --- 2. INITIALIZE SESSION STATE ---
        if 'sim_cart' not in st.session_state:
            st.session_state.sim_cart = []
        if 'sim_global_disc' not in st.session_state:
            st.session_state.sim_global_disc = 0.0
        # 🚀 ΝΕΑ ΠΕΔΙΑ ΓΙΑ ΧΕΙΡΟΚΙΝΗΤΗ ΕΙΣΑΓΩΓΗ ΠΕΛΑΤΗ & ΑΦΜ
        if 'sim_customer_name' not in st.session_state:
            st.session_state.sim_customer_name = ""
        if 'sim_customer_afm' not in st.session_state:
            st.session_state.sim_customer_afm = ""

        # --- 3. ΡΥΘΜΙΣΕΙΣ & ΠΡΟΣΘΗΚΗ ΠΡΟΪΟΝΤΩΝ ---
        st.divider()
        col_c1, col_c2 = st.columns([1, 1.5])
        
        with col_c1:
            st.markdown("### 👤 Στοιχεία Πρότασης")
            
            # 🚀 Ελεύθερη πληκτρολόγηση Πελάτη και ΑΦΜ
            new_name = st.text_input("Επωνυμία / Όνομα Πελάτη:", value=st.session_state.sim_customer_name, placeholder="π.χ. CABCLUB BAR")
            if new_name != st.session_state.sim_customer_name:
                st.session_state.sim_customer_name = new_name
                
            new_afm = st.text_input("ΑΦΜ Πελάτη (Προαιρετικό):", value=st.session_state.sim_customer_afm, placeholder="π.χ. 999999999")
            if new_afm != st.session_state.sim_customer_afm:
                st.session_state.sim_customer_afm = new_afm

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
                            "id": str(datetime.now().timestamp()),
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
                        st.write("") 
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
            total_list_value = 0.0 
            
            sim_export_data = [] 
            
            for item in st.session_state.sim_cart:
                c_name = item["cocktail"]
                t_pcs = item["t_pcs"]
                f_pcs = item["f_pcs"]
                s_pcs = item["s_pcs"]
                s_pct = item["s_pct"]
                normal_pcs = t_pcs - f_pcs - s_pcs
                
                cat_price = recipe_prices.get(c_name, 0.0)
                unit_cost = name_to_cost.get(c_name, get_unit_cost_for_cocktail(c_name, 0.0))
                
                price_after_global = cat_price * (1 - (st.session_state.sim_global_disc / 100))
                rev_norm = normal_pcs * price_after_global
                rev_spec = s_pcs * price_after_global * (1 - (s_pct / 100))
                
                item_rev = rev_norm + rev_spec
                item_cost = t_pcs * unit_cost
                
                total_sim_rev += item_rev
                total_sim_cost += item_cost
                total_list_value += (t_pcs * cat_price) 
                
                # 🚀 Δημιουργία κειμένου ΜΟΝΟ αν υπάρχουν εκπτώσεις
                promo_text_parts = []
                if f_pcs > 0:
                    promo_text_parts.append(f"{f_pcs} τμχ Δώρο")
                if s_pcs > 0:
                    promo_text_parts.append(f"{s_pcs} τμχ με -{s_pct}%")
                promo_text = " | ".join(promo_text_parts) if promo_text_parts else ""
                
                sim_export_data.append({
                    "Cocktail": c_name,
                    "Τεμάχια": t_pcs,
                    "Δώρα/Εκπτώσεις": promo_text,
                    "Αρχική Αξία": t_pcs * cat_price,
                    "Τελική Χρέωση": item_rev
                })

            total_sim_profit = total_sim_rev - total_sim_cost
            sim_margin = (total_sim_profit / total_sim_rev * 100) if total_sim_rev > 0 else 0
            customer_savings = total_list_value - total_sim_rev 
            
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Εκτιμώμενος Τζίρος", f"{total_sim_rev:,.2f} €", delta=f"-{customer_savings:,.2f}€ όφελος πελάτη" if customer_savings > 0 else None, delta_color="normal")
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
            st.write("Δημιουργήστε ένα επαγγελματικό έγγραφο για να το παρουσιάσετε στον πελάτη. Τα δώρα και οι εκπτώσεις (αν υπάρχουν) αναδεικνύονται στρατηγικά.")
            
            now_str = datetime.now().strftime("%d/%m/%Y")
            
            # 🚀 ΝΕΟ: Ενσωμάτωση Λογότυπου ως Υδατογράφημα (Απευθείας από το link)
            watermark_url = "https://cabclub.gr/wp-content/uploads/2021/12/logo.png"
            
            watermark_css = f"""
            .container::before {{
                content: "";
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 70%;
                height: 70%;
                background-image: url('{watermark_url}');
                background-repeat: no-repeat;
                background-position: center;
                background-size: contain;
                opacity: 0.08; /* 👈 Εδώ ρυθμίζεις τη διαφάνεια (0.08 = 8%) */
                z-index: -1;
            }}
            """
            
            # 🚀 Ελέγχουμε αν υπάρχει ΕΣΤΩ ΚΑΙ ΕΝΑ δώρο/έκπτωση σε όλη την παραγγελία
            has_item_promos = any(row['Δώρα/Εκπτώσεις'] != "" for row in sim_export_data)
            
            html_proposal = f"""
            <!DOCTYPE html>
            <html lang="el">
            <head>
                <meta charset="UTF-8">
                <title>Εμπορική Πρόταση - {st.session_state.sim_customer_name}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }}
                    /* Προσθέσαμε position: relative και z-index στο container για να μπει το υδατογράφημα από πίσω */
                    .container {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #ddd; box-shadow: 0 0 10px rgba(0,0,0,0.1); position: relative; z-index: 1; }}
                    
                    /* Εδώ μπαίνει αυτόματα ο κώδικας της εικόνας */
                    {watermark_css}
                    
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
                        <p>CABCLUB COCKTAIL</p>
                    </div>
                    
                    <div class="info-box">
                        <p><strong>Προς:</strong> {st.session_state.sim_customer_name}</p>
                        {f"<p><strong>ΑΦΜ:</strong> {st.session_state.sim_customer_afm}</p>" if st.session_state.sim_customer_afm else ""}
                        <p><strong>Ημερομηνία:</strong> {now_str}</p>
                        {f"<p><strong>Βασική Έκπτωση Συνεργασίας:</strong> {st.session_state.sim_global_disc}%</p>" if st.session_state.sim_global_disc > 0 else ""}
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Προϊόν</th>
                                <th>Συνολικά Τεμάχια</th>
                                {"<th>Ειδικές Προσφορές</th>" if has_item_promos else ""}
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
                                {f'<td style="color: #d32f2f; font-size: 0.9em;">{row["Δώρα/Εκπτώσεις"]}</td>' if has_item_promos else ''}
                                <td style="text-align: right; font-weight: bold;">{row['Τελική Χρέωση']:.2f} €</td>
                            </tr>
                """
                
            html_proposal += f"""
                        </tbody>
                    </table>
                    
                    <div class="totals">
                        <table>
            """
            
            # 🚀 Εμφανίζουμε το "Όφελος Πελάτη" ΜΟΝΟ αν κερδίζει κάτι!
            if customer_savings > 0:
                html_proposal += f"""
                            <tr>
                                <th>Αρχική Αξία Καταλόγου:</th>
                                <td style="text-align: right; text-decoration: line-through; color: #777; white-space: nowrap;">{total_list_value:.2f} &nbsp;€</td>
                            </tr>
                            <tr class="savings-row">
                                <th>Συνολικό Όφελος / Έκπτωση:</th>
                                <td style="text-align: right; white-space: nowrap;">- {customer_savings:.2f} &nbsp;€</td>
                            </tr>
                """
                
            # 🚀 Υπολογισμός ΦΠΑ (24%)
            vat_rate = 0.24
            vat_amount = total_sim_rev * vat_rate
            total_with_vat = total_sim_rev + vat_amount
                
            html_proposal += f"""
                            <tr>
                                <th>Καθαρή Αξία (Χωρίς Φ.Π.Α.):</th>
                                <td style="text-align: right; white-space: nowrap;">{total_sim_rev:.2f} &nbsp;€</td>
                            </tr>
                            <tr>
                                <th>Φ.Π.Α. (24%):</th>
                                <td style="text-align: right; white-space: nowrap;">{vat_amount:.2f} &nbsp;€</td>
                            </tr>
                            <tr class="final-row">
                                <th style="color: white;">ΤΕΛΙΚΟ ΠΛΗΡΩΤΕΟ (Με Φ.Π.Α.):</th>
                                <td style="text-align: right; color: white; white-space: nowrap;">{total_with_vat:.2f} &nbsp;€</td>
                            </tr>
                        </table>
                    </div>
                    <div class="clear"></div>
                    
                    <div class="footer">
                        <p>Σας ευχαριστούμε για την προτίμηση. Η προσφορά ισχύει για 30 ημέρες.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            safe_filename = st.session_state.sim_customer_name.replace(" ", "_") if st.session_state.sim_customer_name else "New_Customer"
            
            st.download_button(
                label="📥 Κατέβασμα Εμπορικής Πρότασης (Ανοίξτε το & τυπώστε σε PDF)",
                data=html_proposal,
                file_name=f"Quotation_{safe_filename}_{now_str.replace('/','-')}.html",
                mime="text/html",
                type="primary"
            )

# --- 13. ΔΙΑΧΕΙΡΙΣΗ ΑΠΟΘΗΚΗΣ & ΛΙΣΤΑ ΑΓΟΡΩΝ ---
elif page == "🛒 Λίστα Αγορών":
    st.header("🛒 Διαχείριση Αποθέματος & Λίστα Αγορών")
    st.write("Δημιουργήστε λίστες αγορών βάσει των πραγματικών σας παραγγελιών ή διορθώστε τα αποθέματά σας.")

    @st.cache_data(ttl=10)
    def load_live_data():
        ing = supabase.table("ingredients").select("*").execute().data
        # 🚀 ΣΠΑΜΕ ΤΟ ΟΡΙΟ: Αντί για 1000, ζητάμε 10.000 γραμμές και τις πιο πρόσφατες πρώτα!
        plog = supabase.table("production_log").select("prod_date, prod_time, customer, cocktail_name, pieces").order("id", desc=True).limit(100000).execute().data
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
        global_recipes = df_rec.copy() if not df_rec.empty else pd.DataFrame()

        tab_inv1, tab_inv2, tab_inv3 = st.tabs(["📋 Λίστα Αγορών & Παραγγελία", "📝 Απογραφή (Διόρθωση)", "🧮 What-If"])

        # ==========================================
        # TAB 1: ΑΥΤΟΜΑΤΗ ΛΙΣΤΑ & ΠΑΡΑΓΓΕΛΙΑ (ΝΕΟ)
        # ==========================================
        with tab_inv1:
            st.markdown("### 🛒 Δημιουργία Λίστας & Καταχώρηση Παραγγελίας")
            
            if not df_plog.empty and not global_recipes.empty:
                
                # 1. Καθαρίζουμε κενά γύρω από τις ημερομηνίες (π.χ. " 01/05/26 ")
                df_plog['prod_date'] = df_plog['prod_date'].astype(str).str.strip()
                
                # 2. Φτιάχνουμε μια αόρατη στήλη. Το dayfirst=True καταλαβαίνει άψογα το 01/05/26 και το 01/05/2026!
                df_plog['Αληθινός_Χρόνος'] = pd.to_datetime(df_plog['prod_date'], dayfirst=True, errors='coerce')
                
                # 3. Ταξινομούμε ΟΛΟ το αρχείο με βάση τον Αληθινό Χρόνο (Φθίνουσα). 
                # Ό,τι άκυρο (π.χ. γράμματα) πάει αυτόματα τέρμα κάτω.
                df_plog = df_plog.sort_values(by='Αληθινός_Χρόνος', ascending=False)
                
                # 4. Εφόσον πλέον ο πίνακας είναι ταξινομημένος τέλεια, τραβάμε τις ημερομηνίες μία-μία.
                # Η drop_duplicates() κρατάει ΜΟΝΟ την πρώτη εμφάνιση και ΔΙΑΤΗΡΕΙ ΑΥΣΤΗΡΑ τη χρονολογική σειρά!
                available_dates = df_plog['prod_date'].drop_duplicates().tolist()
                
                sel_dates = st.multiselect(
                    "📅 Επιλέξτε Ημερομηνίες Παραγγελιών:", 
                    options=available_dates, 
                    default=[available_dates[0]] if available_dates else None
                )
                
                if sel_dates:
                    batch_orders = df_plog[df_plog['prod_date'].isin(sel_dates)].copy()
                    batch_orders['pieces'] = pd.to_numeric(batch_orders['pieces'], errors='coerce').fillna(0)
                    
                    if 'prod_time' in batch_orders.columns and 'customer' in batch_orders.columns:
                        batch_orders = batch_orders.drop_duplicates(subset=['prod_date', 'prod_time', 'customer', 'cocktail_name'])
                    
                    cocktail_sums = batch_orders.groupby('cocktail_name')['pieces'].sum().reset_index()
                    
                    c1, c2 = st.columns([1, 2.5])
                    with c1:
                        st.markdown("**Σύνοψη προς Παραγωγή:**")
                        st.dataframe(cocktail_sums.rename(columns={"cocktail_name": "Κοκτέιλ", "pieces": "Τεμάχια"}), hide_index=True)
                    
                    with c2:
                        st.markdown("**🛍️ Πίνακας Προμηθειών (Διορθώστε την Παραγγελία και Καταχωρήστε)**")
                        materials_needed = {}
                        import math
                        
                        for _, row in cocktail_sums.iterrows():
                            c_name = row['cocktail_name']
                            c_qty = row['pieces']
                            
                            rec_row = global_recipes[global_recipes['Ονομα'] == c_name]
                                
                            if not rec_row.empty:
                                r_data = rec_row.iloc[0]
                                for i in range(1, 14):
                                    ing_name = str(r_data.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                                    if ing_name in ["ΚΕΝΟ", "nan", "", "-", "0", "Νερό"]: continue
                                    
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
                            
                            real_stock = max(0, stock_ml)
                            missing_ml = required_ml - real_stock
                            
                            bottles_to_buy = math.ceil(missing_ml / bottle_vol) if missing_ml > 0 else 0
                                
                            shopping_list.append({
                                "Υλικό": ing,
                                "Απαιτούμενα": f"{required_ml:.1f} ml",
                                "Απόθεμα": f"{stock_ml:.1f} ml",
                                "Πρόταση Συστήματος": bottles_to_buy,
                                "Παραγγελία (Φιάλες)": bottles_to_buy # Εδώ θα γράφει ο χρήστης
                            })
                        
                        if shopping_list:
                            df_shop = pd.DataFrame(shopping_list)
                            
                            # Το data_editor επιτρέπει επεξεργασία ΜΟΝΟ στη στήλη της παραγγελίας
                            edited_df = st.data_editor(
                                df_shop,
                                column_config={
                                    "Παραγγελία (Φιάλες)": st.column_config.NumberColumn(
                                        "Παραγγελία (Φιάλες) ✏️",
                                        min_value=0,
                                        step=1,
                                        help="Διορθώστε εδώ τον αριθμό φιαλών που θέλετε πραγματικά να παραγγείλετε."
                                    ),
                                    "Υλικό": st.column_config.TextColumn(disabled=True),
                                    "Απαιτούμενα": st.column_config.TextColumn(disabled=True),
                                    "Απόθεμα": st.column_config.TextColumn(disabled=True),
                                    "Πρόταση Συστήματος": st.column_config.NumberColumn(disabled=True)
                                },
                                hide_index=True,
                                use_container_width=True
                            )
                            
                            if st.button("🚀 Καταχώρηση Παραγγελίας σε Εκκρεμότητα", type="primary"):
                                orders_to_insert = []
                                for _, row in edited_df.iterrows():
                                    order_qty = int(row["Παραγγελία (Φιάλες)"])
                                    if order_qty > 0:
                                        orders_to_insert.append({
                                            "ingredient_name": row["Υλικό"],
                                            "bottles_ordered": order_qty,
                                            "status": "PENDING"
                                        })
                                
                                if orders_to_insert:
                                    try:
                                        supabase.table("orders_to_receive").insert(orders_to_insert).execute()
                                        st.success("✅ Η παραγγελία καταχωρήθηκε επιτυχώς! Εκκρεμεί η παραλαβή της.")
                                    except Exception as e:
                                        st.error(f"Σφάλμα κατά την αποθήκευση: {e}")
                                else:
                                    st.warning("Δεν έχετε συμπληρώσει φιάλες για παραγγελία.")
                        else:
                            st.success("Δεν απαιτούνται υλικά.")
            else:
                st.info("Δεν βρέθηκαν καταχωρημένες παραγγελίες.")

        # ==========================================
        # TAB 2: ΕΝΗΜΕΡΩΣΗ ΑΠΟΘΕΜΑΤΟΣ (Χειροκίνητα)
        # ==========================================
        with tab_inv2:
            st.markdown("### 📝 Χειροκίνητη Διόρθωση Αποθέματος")
            st.write("Αν παρατηρήσετε διαφορά ανάμεσα στο σύστημα και το ράφι, διορθώστε το απόθεμα εδώ.")
            
            sel_ingredient = st.selectbox("Επιλέξτε Υλικό για διόρθωση:", options=df_ing_live['name'].tolist())
            
            if sel_ingredient:
                ing_row = df_ing_live[df_ing_live['name'] == sel_ingredient].iloc[0]
                current_ml = float(ing_row.get('current_stock_ml', 0.0))
                
                st.metric("Τρέχον Απόθεμα (Συστήματος)", f"{current_ml:.1f} ml")
                
                with st.form("manual_correction_form"):
                    new_val = st.number_input("Ορίστε τη ΣΩΣΤΗ ποσότητα σε ml:", value=current_ml, step=10.0)
                    reason = st.text_input("Αιτιολογία (προαιρετικά, π.χ. 'Σπάσιμο μπουκαλιού')")
                    
                    if st.form_submit_button("💾 Οριστικοποίηση Διόρθωσης"):
                        supabase.table("ingredients").update({"current_stock_ml": new_val}).eq("id", ing_row['id']).execute()
                        if reason: st.toast(f"Αιτιολογία: {reason}")
                        st.success(f"Το απόθεμα για το {sel_ingredient} διορθώθηκε σε {new_val} ml!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()

        # --- ⚠️ ΚΟΥΜΠΙ DEVELOPER / TESTING ---
        with st.expander("⚠️ Εργαλεία Developer (Για Δοκιμές)"):
            st.warning("ΠΡΟΣΟΧΗ: Το παρακάτω κουμπί θα κάνει το απόθεμα (current_stock_ml) ΜΗΔΕΝ σε όλα τα υλικά της βάσης!")
            
            if st.button("🚨 ΜΗΔΕΝΙΣΜΟΣ ΟΛΩΝ ΤΩΝ ΑΠΟΘΕΜΑΤΩΝ 🚨", type="primary"):
                with st.spinner("Μηδενισμός αποθηκών..."):
                    try:
                        # Τραβάμε όλα τα ID των υλικών
                        res_ids = supabase.table("ingredients").select("id").execute()
                        
                        if res_ids.data:
                            # Κάνουμε update το καθένα ξεχωριστά (είναι ο πιο ασφαλής τρόπος 
                            # για να μην μας κόψει το Supabase λόγω ασφαλείας στα μαζικά updates)
                            for item in res_ids.data:
                                supabase.table("ingredients").update({"current_stock_ml": 0.0}).eq("id", item["id"]).execute()
                            
                            st.success("✅ Όλα τα αποθέματα μηδενίστηκαν επιτυχώς! Μπορείτε να ξεκινήσετε τις δοκιμές.")
                            st.cache_data.clear() # Καθαρίζουμε τη μνήμη
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.info("Δεν βρέθηκαν υλικά για μηδενισμό.")
                    except Exception as e:
                        st.error(f"Προέκυψε σφάλμα κατά τον μηδενισμό: {e}")

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
                    
                    if shopping_list: st.dataframe(pd.DataFrame(shopping_list), use_container_width=True, hide_index=True)
            else:
                st.warning("Δεν βρέθηκαν συνταγές.")
    else:
        st.error("Δεν βρέθηκαν δεδομένα υλικών στη βάση.")

# --- 14. ΠΑΡΑΛΑΒΕΣ (RECEIVING) ---
elif page == "🚚 Παραλαβές":
    st.header("🚚 Διαχείριση Παραγγελιών & Παραλαβές")
    st.write("Δείτε τις εκκρεμείς παραγγελίες, διορθώστε τις ποσότητες αν χρειάζεται, και παραλάβετε τα υλικά για να μπουν αυτόματα στην αποθήκη.")

    # Τραβάμε τις εκκρεμείς παραγγελίες
    res_orders = supabase.table("orders_to_receive").select("*").eq("status", "PENDING").execute()
    
    tab1, tab2 = st.tabs(["📦 Εκκρεμείς Παραλαβές", "📜 Ιστορικό Παραλαβών"])
    
    # === TAB 1: ΕΚΚΡΕΜΕΙΣ ΠΑΡΑΛΑΒΕΣ ===
    with tab1:
        if res_orders.data:
            df_orders = pd.DataFrame(res_orders.data)
            
            st.markdown("### 📋 Λίστα Αναμονής")
            st.info("Επιλέξτε ✔️ ποια υλικά παραλάβατε. Αν ο προμηθευτής έφερε άλλη ποσότητα, διορθώστε το νούμερο στη στήλη 'Ήρθαν (Φιάλες)'.")
            
            # Προετοιμασία πίνακα: Αντιγράφουμε τα παραγγελθέντα στη στήλη "Προς Παραλαβή"
            df_orders["Ήρθαν (Φιάλες)"] = df_orders["bottles_ordered"]
            df_orders["Επιλογή"] = True # Προεπιλογή: όλα τσεκαρισμένα
            
            # Φτιάχνουμε μια ωραία ημερομηνία αν υπάρχει
            if 'created_at' in df_orders.columns:
                df_orders['Ημ/νια'] = pd.to_datetime(df_orders['created_at']).dt.strftime('%d/%m/%Y')
            else:
                df_orders['Ημ/νια'] = "-"

            display_cols = ["Επιλογή", "ingredient_name", "bottles_ordered", "Ήρθαν (Φιάλες)", "Ημ/νια", "id"]
            df_display = df_orders[display_cols].copy()
            
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "Επιλογή": st.column_config.CheckboxColumn("Παραλαβή;", default=True),
                    "ingredient_name": st.column_config.TextColumn("Υλικό", disabled=True),
                    "bottles_ordered": st.column_config.NumberColumn("Παραγγέλθηκαν", disabled=True),
                    "Ήρθαν (Φιάλες)": st.column_config.NumberColumn(
                        "Ήρθαν (Φιάλες) ✏️", 
                        min_value=0, 
                        step=1,
                        help="Αλλάξτε αυτό το νούμερο αν η πραγματική παραλαβή διαφέρει από την παραγγελία."
                    ),
                    "Ημ/νια": st.column_config.TextColumn("Ημ/νια", disabled=True),
                    "id": None # Κρύβουμε το ID από τον χρήστη
                },
                hide_index=True,
                use_container_width=True,
                key="receive_editor"
            )
            
            st.divider()
            if st.button("📥 Οριστική Παραλαβή Επιλεγμένων", type="primary"):
                with st.spinner("Ενημέρωση αποθήκης..."):
                    # Κατεβάζουμε τα υλικά για να ξέρουμε πόσα ml έχει το κάθε μπουκάλι
                    res_ing = supabase.table("ingredients").select("id, name, volume, current_stock_ml").execute()
                    ing_dict = {item['name']: item for item in res_ing.data} if res_ing.data else {}
                    
                    processed_count = 0
                    
                    for _, row in edited_df.iterrows():
                        if row["Επιλογή"]:
                            ing_name = row["ingredient_name"]
                            received_bottles = int(row["Ήρθαν (Φιάλες)"])
                            order_id = int(row["id"])
                            
                            if received_bottles > 0:
                                # Ενημέρωση Αποθήκης
                                if ing_name in ing_dict:
                                    ing_info = ing_dict[ing_name]
                                    bottle_vol = float(ing_info.get("volume", 1000) or 1000)
                                    current_stock = float(ing_info.get("current_stock_ml", 0) or 0)
                                    
                                    # Προσθέτουμε τα νέα ml στο υπάρχον απόθεμα
                                    added_ml = received_bottles * bottle_vol
                                    new_stock = current_stock + added_ml
                                    
                                    # 1. Ενημέρωση του πίνακα ingredients (το απόθεμα ανεβαίνει)
                                    supabase.table("ingredients").update({"current_stock_ml": new_stock}).eq("id", ing_info["id"]).execute()
                                    
                                    # 2. Ενημέρωση της παραγγελίας (κλείνει)
                                    supabase.table("orders_to_receive").update({
                                        "status": "RECEIVED",
                                        "bottles_received": received_bottles
                                    }).eq("id", order_id).execute()
                                    
                                    processed_count += 1
                                    
                    if processed_count > 0:
                        st.success(f"✅ Ολοκληρώθηκε η παραλαβή! Ενημερώθηκαν {processed_count} κωδικοί στην αποθήκη.")
                        
                        # 🚀 ΝΕΑ ΓΡΑΜΜΗ: Καθαρίζουμε τη μνήμη για να εμφανιστούν αμέσως τα νέα ml στην Αποθήκη!
                        st.cache_data.clear() 
                        
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.warning("Δεν επιλέξατε παραλαβή ή βγάλατε ποσότητα 0.")
        else:
            st.success("🎉 Δεν υπάρχουν εκκρεμείς παραγγελίες!")
            
    # === TAB 2: ΙΣΤΟΡΙΚΟ ===
    with tab2:
        st.markdown("### 📜 Ιστορικό Ολοκληρωμένων Παραλαβών")
        res_hist = supabase.table("orders_to_receive").select("*").eq("status", "RECEIVED").order("created_at", desc=True).limit(50).execute()
        if res_hist.data:
            df_hist = pd.DataFrame(res_hist.data)
            
            if 'created_at' in df_hist.columns:
                df_hist['Ημερομηνία'] = pd.to_datetime(df_hist['created_at']).dt.strftime('%d/%m/%Y %H:%M')
            else:
                df_hist['Ημερομηνία'] = "-"
                
            df_hist = df_hist.rename(columns={
                "ingredient_name": "Υλικό",
                "bottles_ordered": "Παραγγέλθηκαν (Φιάλες)",
                "bottles_received": "Παρελήφθησαν (Φιάλες)"
            })
            
            st.dataframe(df_hist[["Ημερομηνία", "Υλικό", "Παραγγέλθηκαν (Φιάλες)", "Παρελήφθησαν (Φιάλες)"]], use_container_width=True, hide_index=True)
        else:
            st.info("Δεν υπάρχει ιστορικό παραλαβών.")


# --- ΝΕΑ ΚΑΡΤΕΛΑ: ΔΟΚΙΜΑΣΤΙΚΕΣ ΠΑΡΑΓΩΓΕΣ ---
elif page == "🧪 Δοκιμαστικές Παραγωγές":
    st.header("🧪 Αριθμομηχανή Δοκιμαστικών Παραγωγών")
    st.write("Υπολογίστε άμεσα τα ακριβή υλικά για παραγωγή. Οι δοκιμές εδώ **δεν αποθηκεύονται** στο ιστορικό.")

    # --- ΜΑΓΕΙΑ SUPABASE: Φόρτωση φρέσκων δεδομένων (Συνταγές & Υλικά) ---
    res_ing = supabase.table("ingredients").select("*").execute()
    ing_data = res_ing.data if res_ing.data else []
    df_ing_list = []
    for item in ing_data:
        df_ing_list.append({
            "Name": str(item["name"]).strip(), 
            "Price": item["price"],
            "Volume": item["volume"],
            "weight_full": item.get("weight_full", 0.0),
            "Weight_Full": item.get("weight_full", 0.0), # 👈 Το διορθώσαμε και εδώ για ασφάλεια!
            "Weight": item.get("weight_full", 0.0),
            "Αλκοόλ %": item["abv"],
            "ABV": item["abv"], 
            "Τιμή/ml": item["price"] / item["volume"] if item["volume"] > 0 else 0
        })
    df_ing = pd.DataFrame(df_ing_list)

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

    if not df_rec.empty and not df_ing.empty:
        recipe_options = sorted(list(df_rec["Ονομα"].unique()))
        
        col1, col2 = st.columns(2)
        sel_cocktail = col1.selectbox("🍹 Επιλέξτε Κοκτέιλ για Δοκιμή:", ["-- Επιλέξτε --"] + recipe_options)
        sel_pcs = col2.number_input("📦 Αριθμός Τεμαχίων (τμχ):", min_value=1, step=1, value=1)
        
        if sel_cocktail != "-- Επιλέξτε --":
            st.divider()
            st.subheader(f"📊 Απαιτούμενα Υλικά για {sel_pcs} τμχ {sel_cocktail}")
            
            recipe_row = df_rec[df_rec["Ονομα"] == sel_cocktail].iloc[0]
            
            # Βοηθητική συνάρτηση για ασφαλή ανάγνωση των ML
            def get_test_ml(row, idx):
                exact_key = f"ML{idx}"
                if exact_key in row: val = row[exact_key]
                else:
                    target = exact_key.lower()
                    val = next((row[c] for c in row.index if str(c).lower().replace(" ", "") == target), 0.0)
                try: return float(str(val).replace(',', '.').replace(' ', '')) if pd.notna(val) else 0.0
                except: return 0.0

            test_results = []
            grand_total_g = 0.0  # 🚀 ΝΕΟ: Μεταβλητή για το συνολικό βάρος
            
            for i in range(1, 14):
                ing_name = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                if ing_name not in ["ΚΕΝΟ", "nan", "", "-", "0"]:
                    ml_per_unit = get_test_ml(recipe_row, i)
                    total_ml = ml_per_unit * sel_pcs
                    
                    # Αναζήτηση της πρώτης ύλης στον πίνακα συστατικών (df_ing)
                    match_ing = df_ing[(df_ing["Name"] == ing_name) | (df_ing.get("name", "") == ing_name)]
                    
                    total_g = total_ml
                    total_bottles = 0.0
                    
                    if not match_ing.empty:
                        # Ασφαλής ανάγνωση στηλών
                        vol = float(match_ing.iloc[0].get("Volume", match_ing.iloc[0].get("volume", 1)))
                        weight = float(match_ing.iloc[0].get("Weight_Full", match_ing.iloc[0].get("weight_full", vol)))
                        
                        if vol > 0:
                            total_g = (total_ml / vol) * weight
                            total_bottles = total_ml / vol
                            
                    test_results.append({
                        "Πρώτη Ύλη": ing_name,
                        "Απαιτούμενα (ml)": total_ml,
                        "Βάρος (g)": total_g,
                        "Φιάλες": total_bottles
                    })
                    
                    grand_total_g += total_g  # 🚀 ΝΕΟ: Προσθήκη στο γενικό σύνολο
            
            if test_results:
                df_results = pd.DataFrame(test_results)
                
                # 1. ΕΜΦΑΝΙΣΗ ΣΤΗΝ ΟΘΟΝΗ
                st.dataframe(
                    df_results.style.format({
                        "Απαιτούμενα (ml)": "{:.1f} ml",
                        "Βάρος (g)": "{:.1f} g",
                        "Φιάλες": "{:.2f} μπουκ."
                    }),
                    hide_index=True,
                    use_container_width=True
                )
                
                # 🚀 ΝΕΟ: Εμφάνιση του τελικού συνόλου κάτω από τον πίνακα στην οθόνη
                st.success(f"⚖️ **ΓΕΝΙΚΟ ΣΥΝΟΛΟ ΖΥΓΙΣΗΣ:** {grand_total_g:.1f} γραμμάρια")
                
                # 2. ΔΗΜΙΟΥΡΓΙΑ HTML ΕΚΤΥΠΩΣΗΣ
                html_content = f"""
                <!DOCTYPE html>
                <html lang="el">
                <head>
                    <meta charset="UTF-8">
                    <title>Δοκιμαστική Παραγωγή - {sel_cocktail}</title>
                    <style>
                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #333; }}
                        .container {{ max-width: 800px; margin: auto; border: 1px solid #ddd; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }}
                        .header {{ text-align: center; border-bottom: 3px solid #009b3a; padding-bottom: 15px; margin-bottom: 30px; }}
                        h1 {{ color: #009b3a; margin: 0; font-size: 26px; }}
                        p {{ font-size: 16px; color: #555; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
                        th {{ background-color: #f8f9fa; color: #333; font-weight: bold; }}
                        .ing-name {{ text-align: left; font-weight: bold; font-size: 15px; }}
                        .total-row {{ background-color: #e8f5e9; font-weight: bold; font-size: 16px; color: #2e7d32; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🧪 Φύλλο Δοκιμαστικής Παραγωγής</h1>
                            <p><b>Κοκτέιλ:</b> {sel_cocktail} &nbsp;|&nbsp; <b>Τεμάχια (Στόχος):</b> {sel_pcs} τμχ</p>
                        </div>
                        <table>
                            <thead>
                                <tr>
                                    <th class="ing-name">Πρώτη Ύλη</th>
                                    <th>Απαιτούμενα (ml)</th>
                                    <th>Βάρος Ζύγισης (g)</th>
                                    <th>Εκτιμώμενες Φιάλες</th>
                                </tr>
                            </thead>
                            <tbody>
                """
                
                for row in test_results:
                    html_content += f"""
                                <tr>
                                    <td class="ing-name">{row['Πρώτη Ύλη']}</td>
                                    <td>{row['Απαιτούμενα (ml)']:.1f}</td>
                                    <td>{row['Βάρος (g)']:.1f}</td>
                                    <td>{row['Φιάλες']:.2f}</td>
                                </tr>
                    """
                    
                # 🚀 ΝΕΟ: Ενσωμάτωση της γραμμής του συνόλου στο τέλος του πίνακα στο HTML
                html_content += f"""
                                <tr class="total-row">
                                    <td colspan="2" style="text-align: right;">ΓΕΝΙΚΟ ΣΥΝΟΛΟ ΖΥΓΙΣΗΣ:</td>
                                    <td>{grand_total_g:.1f} g</td>
                                    <td></td>
                                </tr>
                            </tbody>
                        </table>
                        <p style="text-align:center; font-size:11px; color:#999; margin-top: 30px;">Εκτύπωση από το B2B Σύστημα Παραγωγής - Μη Δεσμευτικό Έγγραφο</p>
                    </div>
                </body>
                </html>
                """
                
                st.write("")
                st.download_button(
                    label="🖨️ Λήψη Φύλλου Δοκιμής (HTML)",
                    data=html_content,
                    file_name=f"Test_Production_{sel_cocktail.replace(' ', '_')}.html",
                    mime="text/html",
                    type="primary"
                )
            else:
                st.warning("Το κοκτέιλ δεν περιέχει καταχωρημένα συστατικά.")
    else:
        st.info("Παρακαλώ περιμένετε να φορτώσουν τα δεδομένα ή ελέγξτε αν υπάρχουν καταχωρημένες συνταγές.")
