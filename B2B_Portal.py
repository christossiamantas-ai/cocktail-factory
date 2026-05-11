import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import requests
from streamlit_lottie import st_lottie

# --- 1. ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ ---
st.set_page_config(page_title="CabClub B2B Portal", page_icon="🍹", layout="centered")

# --- 2. ΣΥΝΔΕΣΗ ΜΕ SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- 3. ΦΟΡΤΩΣΗ ANIMATION (SHAKER) ΜΕ ΠΡΟΣΤΑΣΙΑ ---
def load_lottieurl(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Το animation shaker (δοκιμασμένο link)
lottie_shaker = load_lottieurl("https://lottie.host/82540134-8b65-4f74-9721-a1286c078832/t9HAtvP0P0.json")

# --- 4. ΜΝΗΜΗ ΕΦΑΡΜΟΓΗΣ ---
if "authenticated_shop" not in st.session_state:
    st.session_state.authenticated_shop = None
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0

# --- 5. ΟΘΟΝΗ ΕΙΣΟΔΟΥ (LOGIN) ---
if st.session_state.authenticated_shop is None:
    st.markdown("<h1 style='text-align: center; color: #d32f2f;'>CABCLUB B2B</h1>", unsafe_allow_html=True)
    st.subheader("🔑 Είσοδος Καταστήματος")
    st.write("Παρακαλούμε εισάγετε το κινητό τηλέφωνο που έχετε δηλώσει.")
    
    user_pin = st.text_input("Κινητό Τηλέφωνο (PIN):", type="password", placeholder="π.χ. 6970000000")
    
    if st.button("Είσοδος", use_container_width=True):
        if user_pin:
            res = supabase.table("customers").select("name").eq("phone", user_pin).execute()
            if res.data and len(res.data) > 0:
                st.session_state.authenticated_shop = res.data[0]["name"]
                st.success(f"✅ Καλώς ήρθες!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Το κινητό δεν βρέθηκε.")
    st.stop()

# --- 6. ΚΥΡΙΑ ΣΕΛΙΔΑ ΠΑΡΑΓΓΕΛΙΑΣ ---
client_name = st.session_state.authenticated_shop

c_top1, c_top2 = st.columns([3, 1])
with c_top1:
    st.markdown(f"### 🍹 {client_name}")
with c_top2:
    if st.button("🚪 Έξοδος"):
        st.session_state.authenticated_shop = None
        st.rerun()

# Ενημέρωση Κατάστασης
res_last = supabase.table("b2b_orders").select("status").eq("customer_name", client_name).order("created_at", desc=True).limit(1).execute()
if res_last.data:
    status = res_last.data[0]["status"]
    icon = "🔵" if status == "ΝΕΑ" else "🟡" if status == "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ" else "✅"
    st.info(f"{icon} Η τελευταία σας παραγγελία είναι: **{status}**")

st.divider()

# --- 7. ΚΑΤΑΛΟΓΟΣ ΠΡΟΪΟΝΤΩΝ (ΑΛΦΑΒΗΤΙΚΑ) ---
res_r = supabase.table("recipes").select("*").execute()
df_rec = pd.DataFrame(res_r.data) if res_r.data else pd.DataFrame()

if not df_rec.empty:
    df_rec = df_rec.sort_values(by="name") # Αλφαβητική σειρά

    order_items = {}
    total_cost = 0.0
    
    h1, h2, h3 = st.columns([3, 1, 1.5])
    h1.caption("ΠΡΟΪΟΝ")
    h2.caption("ΤΜΧ")
    h3.caption("ΣΥΝΟΛΟ")
    st.markdown("<hr style='margin: 0px; padding-bottom: 10px;'>", unsafe_allow_html=True)

    for _, row in df_rec.iterrows():
        c_name = row.get("name", "Άγνωστο")
        try:
            raw_price = str(row.get("catalog_price", 0)).replace(',', '.')
            price_cat = float(raw_price)
        except: price_cat = 0.0
        
        # Υπολογισμός 26% έκπτωσης
        price_b2b = round(price_cat * 0.74, 2)
        
        if price_b2b > 0:
            c1, c2, c3 = st.columns([3, 1, 1.5])
            with c1:
                st.markdown(f"**{c_name}**<br><small>{price_b2b:.2f} € / τμχ</small>", unsafe_allow_html=True)
            with c2:
                qty = st.number_input("Τμχ", min_value=0, max_value=500, step=1, key=f"qty_{c_name}_{st.session_state.reset_key}", label_visibility="collapsed")
            with c3:
                subtotal = round(qty * price_b2b, 2)
                st.markdown(f"**{subtotal:.2f} €**")
                
            if qty > 0:
                order_items[c_name] = {"qty": qty, "subtotal": subtotal}
                total_cost += subtotal

    st.divider()
    total_cost = round(total_cost, 2)
    st.markdown(f"<h3 style='text-align: right; color: #d32f2f;'>Σύνολο: {total_cost:.2f} €</h3>", unsafe_allow_html=True)
    
    notes = st.text_area("📝 Σημειώσεις / Ημέρα Παράδοσης:", key=f"notes_{st.session_state.reset_key}")

    # --- 8. ΥΠΟΒΟΛΗ ΠΑΡΑΓΓΕΛΙΑΣ ΜΕ SHAKER ---
    if st.button("🚀 Αποστολή Παραγγελίας", type="primary", use_container_width=True):
        if not order_items:
            st.error("Το καλάθι σας είναι άδειο!")
        else:
            order_details = "\n".join([f"• {v['qty']}x {k} ({v['subtotal']:.2f}€)" for k, v in order_items.items()])
            insert_data = {
                "customer_name": client_name,
                "order_details": order_details,
                "total_amount": total_cost,
                "status": "ΝΕΑ",
                "notes": notes
            }
            try:
                # Αποθήκευση στη Supabase
                supabase.table("b2b_orders").insert([insert_data]).execute()
                
                # Δημιουργούμε ένα κενό "δοχείο" για να βάλουμε το animation
                placeholder = st.empty()
                with placeholder.container():
                    if lottie_shaker:
                        st_lottie(lottie_shaker, height=300, key="shaker_anim")
                    else:
                        st.markdown("### 🍸 Cheers!")
                    st.success("✅ Η παραγγελία στάλθηκε στην CabClub!")
                
                # Περιμένουμε 5 δευτερόλεπτα για να φανεί το εφέ
                time.sleep(5)
                
                # Καθαρίζουμε το animation και κάνουμε reset
                placeholder.empty()
                st.session_state.reset_key += 1
                st.rerun()
                
            except Exception as e:
                st.error(f"Σφάλμα κατά την αποστολή: {e}")
else:
    st.warning("Δεν υπάρχουν προϊόντα διαθέσιμα.")
