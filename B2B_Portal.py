import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

# --- ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ ---
st.set_page_config(page_title="CabClub B2B Portal", page_icon="🍹", layout="centered")

# --- ΣΥΝΔΕΣΗ ΜΕ SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- ΜΗΧΑΝΙΣΜΟΣ RESET (Κλειδί για το κατάστημα) ---
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0

# --- ΚΕΝΤΡΙΚΗ ΕΜΦΑΝΙΣΗ ---
st.markdown("<h1 style='text-align: center; color: #d32f2f;'>CABCLUB COCKTAILS</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>🤝 B2B Portal Παραγγελιών</h3>", unsafe_allow_html=True)
st.divider()

# --- 1. ΤΑΥΤΟΠΟΙΗΣΗ ΠΕΛΑΤΗ ---
res_c = supabase.table("customers").select("name").order("name").execute()
customers = [c["name"] for c in res_c.data] if res_c.data else []

st.write("Καλώς ήρθατε! Επιλέξτε το κατάστημά σας:")

# Χρησιμοποιούμε το reset_key στο key του selectbox
client_name = st.selectbox(
    "👤 Κατάστημα:", 
    ["-- Επιλέξτε το Κατάστημά σας --"] + customers, 
    key=f"client_box_{st.session_state.reset_key}"
)

if client_name != "-- Επιλέξτε το Κατάστημά σας --":
    st.success(f"Συνδεθήκατε ως: **{client_name}**")
    st.divider()
    
    st.subheader("🍹 Κατάλογος Προϊόντων")
    
    res_r = supabase.table("recipes").select("*").execute()
    df_rec = pd.DataFrame(res_r.data) if res_r.data else pd.DataFrame()
    
    if not df_rec.empty:
        order_items = {}
        total_cost = 0.0
        
        # --- ΑΦΑΙΡΕΣΗ ΦΟΡΜΑΣ (Για να μην δουλεύει το Enter) ---
        c_head1, c_head2, c_head3 = st.columns([3, 1, 1.5])
        c_head1.caption("ΠΡΟΪΟΝ")
        c_head2.caption("ΤΜΧ")
        c_head3.caption("ΣΥΝΟΛΟ")
        st.markdown("<hr style='margin: 0px; padding-bottom: 10px;'>", unsafe_allow_html=True)

        for _, row in df_rec.iterrows():
            c_name = row.get("name", "Άγνωστο")
            try:
                price_cat = float(str(row.get("catalog_price", 0)).replace(',', '.'))
            except:
                price_cat = 0.0
            
            price_b2b = price_cat * 0.74 
            
            if price_b2b > 0:
                c1, c2, c3 = st.columns([3, 1, 1.5])
                with c1:
                    st.markdown(f"**{c_name}**<br><span style='font-size:12px; color:gray;'>{price_b2b:.2f} € / τμχ</span>", unsafe_allow_html=True)
                with c2:
                    # Προσθέτουμε μοναδικό key για να καθαρίζουν οι ποσότητες στο reset
                    qty = st.number_input("Τεμάχια", min_value=0, step=1, key=f"qty_{c_name}_{st.session_state.reset_key}", label_visibility="collapsed")
                with c3:
                    subtotal = qty * price_b2b
                    st.markdown(f"<div style='padding-top:8px;'><b>{subtotal:.2f} €</b></div>", unsafe_allow_html=True)
                    
                if qty > 0:
                    order_items[c_name] = {"qty": qty, "price": price_b2b, "subtotal": subtotal}
                    total_cost += subtotal
                        
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: right; color: #d32f2f;'>Σύνολο: {total_cost:.2f} €</h3>", unsafe_allow_html=True)
        
        notes = st.text_area("📝 Σημειώσεις / Ημέρα Παράδοσης:", placeholder="Γράψτε τυχόν οδηγίες...", key=f"notes_{st.session_state.reset_key}")
        
        # Χρησιμοποιούμε απλό κουμπί (st.button) αντί για submit_button
        if st.button("🚀 Αποστολή Παραγγελίας", type="primary", use_container_width=True):
            if not order_items:
                st.error("Το καλάθι σας είναι άδειο!")
            else:
                order_text = "\n".join([f"• {v['qty']}x {k} ({v['subtotal']:.2f}€)" for k, v in order_items.items()])
                insert_data = {
                    "customer_name": client_name,
                    "order_details": order_text,
                    "total_amount": total_cost,
                    "status": "ΝΕΑ",
                    "notes": notes
                }
                
                try:
                    supabase.table("b2b_orders").insert([insert_data]).execute()
                    st.success("✅ Η παραγγελία καταχωρήθηκε!")
                    st.balloons()
                    
                    # --- ΤΟ ΜΑΓΙΚΟ RESET ---
                    time.sleep(3)
                    # Αλλάζουμε το reset_key για να "αναγκάσουμε" όλα τα πεδία να ξαναδημιουργηθούν άδεια
                    st.session_state.reset_key += 1
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Σφάλμα: {e}")
    else:
        st.warning("Ο κατάλογος είναι άδειος.")
else:
    st.info("Παρακαλούμε επιλέξτε το κατάστημά σας.")
