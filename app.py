 import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Cocktail Factory Cloud v13.1", layout="wide")

# Σύνδεση με το Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ΣΥΝΑΡΤΗΣΕΙΣ ΓΙΑ ΔΕΔΟΜΕΝΑ ---
def get_data(worksheet):
   try:
       # ttl=0 για να διαβάζει πάντα τα τελευταία δεδομένα από το Sheet
       return conn.read(worksheet=worksheet, ttl=0)
   except:
       return pd.DataFrame()

def save_data(df, worksheet):
   conn.update(worksheet=worksheet, data=df)
   st.cache_data.clear()

# --- STATE MANAGEMENT ---
if 'builder_recipe' not in st.session_state: st.session_state.builder_recipe = []
if 'edit_name' not in st.session_state: st.session_state.edit_name = ""

# --- NAVIGATION ---
st.sidebar.title("🍸 Factory Cloud v13.1")
page = st.sidebar.selectbox("Μενού", [
   "📊 Dashboard", "📦 Αποθήκη", "🛠️ Recipe Builder",
   "📂 Αρχείο Συνταγών", "📝 Νέα Παραγγελία", "📋 Τιμοκατάλογος"
])

# --- 0. DASHBOARD ---
if page == "📊 Dashboard":
   st.title("📊 Επισκόπηση (Live)")
   ings = get_data("ingredients")
   recs = get_data("recipes")
   ords = get_data("orders")

   c1, c2, c3 = st.columns(3)
   c1.metric("Υλικά στην Αποθήκη", len(ings) if not ings.empty else 0)
   c2.metric("Συνταγές στο Αρχείο", len(recs) if not recs.empty else 0)
   c3.metric("Σύνολο Παραγγελιών", len(ords) if not ords.empty else 0)

   st.divider()
   if not ords.empty:
       st.subheader("📅 Τελευταίες Παραγγελίες")
       st.dataframe(ords.tail(10), use_container_width=True)

# --- 1. INVENTORY (ΜΕ IMPORT) ---
elif page == "📦 Αποθήκη":
   st.title("📦 Διαχείριση Υλικών")
   ings = get_data("ingredients")

   c1, c2 = st.columns(2)
   with c1:
       with st.expander("➕ Προσθήκη / Import", expanded=True):
           t1, t2 = st.tabs(["Χειροκίνητα", "Excel Import"])
           with t1:
               n = st.text_input("Όνομα Υλικού")
               p = st.number_input("Τιμή Αγοράς (€)", 0.0)
               v = st.number_input("Όγκος (ml)", 1.0, 5000.0, 700.0)
               if st.button("Αποθήκευση"):
                   new_row = pd.DataFrame([{"name": n, "purchase_price": p, "volume_ml": v, "cost_per_ml": p/v}])
                   updated_df = pd.concat([ings, new_row], ignore_index=True)
                   save_data(updated_df, "ingredients")
                   st.success("Αποθηκεύτηκε!")
                   st.rerun()

           with t2:
               st.write("Το Excel πρέπει να έχει στήλες: **Name, Price, Volume**")
               up = st.file_uploader("Ανεβάστε αρχείο .xlsx", type=["xlsx"])
               if up and st.button("🚀 Εκτέλεση Import"):
                   df_upload = pd.read_excel(up)
                   new_ings = pd.DataFrame({
                       "name": df_upload["Name"],
                       "purchase_price": df_upload["Price"],
                       "volume_ml": df_upload["Volume"],
                       "cost_per_ml": df_upload["Price"] / df_upload["Volume"]
                   })
                   updated_df = pd.concat([ings, new_ings], ignore_index=True).drop_duplicates(subset=['name'], keep='last')
                   save_data(updated_df, "ingredients")
                   st.success(f"Εισήχθησαν {len(new_ings)} υλικά!")
                   st.rerun()

   with c2:
       if not ings.empty:
           with st.expander("📝 Επεξεργασία / Διαγραφή"):
               sel = st.selectbox("Επιλογή Υλικού", ings['name'])
               idx = ings[ings['name'] == sel].index[0]

               col_up, col_del = st.columns(2)
               if col_del.button("🗑️ Διαγραφή"):
                   ings = ings.drop(idx)
                   save_data(ings, "ingredients")
                   st.rerun()

   st.dataframe(ings, use_container_width=True)

# --- 2. RECIPE BUILDER ---
elif page == "🛠️ Recipe Builder":
   st.title("🛠️ Σχεδιασμός Συνταγής")
   ings = get_data("ingredients")
   recs = get_data("recipes")

   col_opt, col_main = st.columns([1, 2])
   with col_opt:
       f_bot = st.number_input("Μπουκάλι/Καπάκι (€)", 0.19)
       f_tax = st.number_input("Φόρος %", 24.5)
       f_box = 0.02
       f_ship = 0.01

   with col_main:
       name = st.text_input("Όνομα Cocktail", value=st.session_state.edit_name)
       c1, c2, c3 = st.columns([2,1,1])
       sel_ing = c1.selectbox("Υλικό", ings['name']) if not ings.empty else ""
       ml = c2.number_input("ml", 0.0)
       if c3.button("Προσθήκη"):
           st.session_state.builder_recipe.append({"Υλικό": sel_ing, "ml": ml})
           st.rerun()

       liq_cost = 0
       for idx, item in enumerate(st.session_state.builder_recipe):
           p_ml = ings[ings['name'] == item['Υλικό']]['cost_per_ml'].values[0]
           liq_cost += item['ml'] * p_ml
           st.write(f"• {item['Υλικό']} ({item['ml']}ml)")
           if st.button("🗑️", key=f"del_{idx}"):
               st.session_state.builder_recipe.pop(idx); st.rerun()

       total = liq_cost + (liq_cost * f_tax/100) + f_bot + f_box + f_ship
       st.metric("Κόστος Μονάδας", f"{total:.3f}€")

       if st.button("💾 Αποθήκευση Συνταγής"):
           new_rec = pd.DataFrame([{
               "name": name, "ingredients_json": json.dumps(st.session_state.builder_recipe),
               "fixed_costs": f_bot, "tax_percent": f_tax, "box_cost": f_box, "shipping_cost": f_ship
           }])
           if not recs.empty and name in recs['name'].values:
               recs = recs[recs['name'] != name]
           updated_recs = pd.concat([recs, new_rec], ignore_index=True)
           save_data(updated_recs, "recipes")
           st.session_state.builder_recipe = []; st.session_state.edit_name = ""; st.rerun()

# --- 3. ARCHIVE ---
elif page == "📂 Αρχείο Συνταγών":
   st.title("📂 Αρχείο Συνταγών")
   recs = get_data("recipes")
   ings_db = get_data("ingredients")

   if not recs.empty:
       sel = st.selectbox("Επιλέξτε Συνταγή", recs['name'])
       r = recs[recs['name'] == sel].iloc[0]
       items = json.loads(r['ingredients_json'])

       table = []
       liq_sum = 0
       for i in items:
           p_ml = ings_db[ings_db['name'] == i['Υλικό']]['cost_per_ml'].values[0] if not ings_db.empty else 0
           cost = i['ml'] * p_ml
           table.append({"Υλικό": i['Υλικό'], "ml": i['ml'], "Κόστος (€)": round(cost, 3)})
           liq_sum += cost

       st.table(pd.DataFrame(table))
       tax_v = liq_sum * (r['tax_percent']/100)
       final = liq_sum + tax_v + r['fixed_costs'] + r['box_cost'] + r['shipping_cost']
       st.metric("Τελικό Κόστος", f"{final:.3f}€")

       if st.button("🗑️ Διαγραφή Συνταγής"):
           recs = recs[recs['name'] != sel]
           save_data(recs, "recipes"); st.rerun()

# --- 4. NEW ORDER ---
elif page == "📝 Νέα Παραγγελία":
   st.title("📝 Παραγγελίες & Ανάγκες")
   recs = get_data("recipes")
   ords = get_data("orders")

   col1, col2 = st.columns([1,2])
   with col1:
       sel_list = st.multiselect("Προϊόντα", recs['name'])
       order_items = []
       for s in sel_list:
           q = st.number_input(f"Τεμάχια {s}", 1, 1000, 10)
           order_items.append({"item": s, "qty": q})

       if st.button("🚀 Καταχώρηση Παραγγελίας"):
           new_ord = pd.DataFrame([{"order_date": datetime.now().strftime("%d/%m/%Y %H:%M"), "items_json": json.dumps(order_items)}])
           updated_ords = pd.concat([ords, new_ord], ignore_index=True)
           save_data(updated_ords, "orders")
           st.success("Η παραγγελία καταγράφηκε!")

   with col2:
       if order_items:
           raw = {}
           for entry in order_items:
               recipe = recs[recs['name'] == entry['item']].iloc[0]
               ing_list = json.loads(recipe['ingredients_json'])
               for ing in ing_list:
                   raw[ing['Υλικό']] = raw.get(ing['Υλικό'], 0) + (ing['ml'] * entry['qty'])
           st.subheader("Συνολικές Ανάγκες")
           st.table(pd.DataFrame([{"Υλικό": k, "Λίτρα": round(v/1000, 2)} for k, v in raw.items()]))

# --- 5. PRICE LIST ---
elif page == "📋 Τιμοκατάλογος":
   st.title("📋 Τιμοκατάλογος")
   recs = get_data("recipes")
   ings = get_data("ingredients")
   markup = st.slider("Markup %", 10, 300, 100)

   res = []
   if not recs.empty:
       for _, r in recs.iterrows():
           items = json.loads(r['ingredients_json'])
           l_cost = 0
           for i in items:
               p_ml = ings[ings['name'] == i['Υλικό']]['cost_per_ml'].values[0] if not ings.empty else 0
               l_cost += i['ml'] * p_ml
           unit_c = l_cost + (l_cost * r['tax_percent']/100) + r['fixed_costs'] + r['box_cost'] + r['shipping_cost']
           price = unit_c * (1 + markup/100)
           res.append({"Cocktail": r['name'], "Κόστος": round(unit_c, 2), "Τιμή": round(price, 2), "Κέρδος €": round(price-unit_c, 2)})
       st.table(pd.DataFrame(res))
