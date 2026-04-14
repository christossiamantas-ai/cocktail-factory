import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Cocktail Factory Pro v12.2", layout="wide")

def init_db():
   conn = sqlite3.connect('cocktail_factory.db')
   c = conn.cursor()
   c.execute('CREATE TABLE IF NOT EXISTS ingredients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, purchase_price REAL, volume_ml REAL, cost_per_ml REAL)')
   c.execute('CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, ingredients_json TEXT, fixed_costs REAL, tax_percent REAL, box_cost REAL, shipping_cost REAL)')
   c.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_date TEXT, items_json TEXT, status TEXT DEFAULT "Ολοκληρώθηκε")')
   conn.commit()
   conn.close()

init_db()

# --- STATE MANAGEMENT ---
if 'builder_recipe' not in st.session_state: st.session_state.builder_recipe = []
if 'edit_name' not in st.session_state: st.session_state.edit_name = ""

# --- NAVIGATION ---
st.sidebar.title("🍸 Factory Flow v12.2")
page = st.sidebar.selectbox("Μενού", [
   "📊 Dashboard",
   "📦 Αποθήκη",
   "🛠️ Recipe Builder",
   "📂 Αρχείο Συνταγών",
   "📝 Νέα Παραγγελία",
   "📋 Τιμοκατάλογος"
])

# --- 0. DASHBOARD ---
if page == "📊 Dashboard":
   st.title("📊 Επισκόπηση Παραγωγής")
   conn = sqlite3.connect('cocktail_factory.db')
   recs = pd.read_sql_query("SELECT * FROM recipes", conn)
   ords = pd.read_sql_query("SELECT * FROM orders", conn)
   ings = pd.read_sql_query("SELECT * FROM ingredients", conn)

   c1, c2, c3 = st.columns(3)
   c1.metric("Συνολικές Συνταγές", len(recs))
   c2.metric("Πρώτες Ύλες (Αποθήκη)", len(ings))
   c3.metric("Σύνολο Παραγγελιών", len(ords))

   st.divider()
   st.subheader("📅 Τελευταίες Καταχωρήσεις Παραγγελιών")
   if not ords.empty:
       st.dataframe(ords.sort_values('id', ascending=False).head(10), use_container_width=True)
   conn.close()

# --- 1. INVENTORY (ENHANCED EDIT) ---
elif page == "📦 Αποθήκη":
   st.title("📦 Διαχείριση Υλικών")
   conn = sqlite3.connect('cocktail_factory.db')
   c1, c2 = st.columns(2)
   with c1:
       with st.expander("➕ Προσθήκη / Import", expanded=True):
           t1, t2 = st.tabs(["Χειροκίνητα", "Excel"])
           with t1:
               n = st.text_input("Όνομα Υλικού")
               p = st.number_input("Τιμή Αγοράς (€)", 0.0, format="%.2f")
               v = st.number_input("Όγκος (ml)", 1.0, 5000.0, 700.0)
               if st.button("Αποθήκευση"):
                   conn.execute("INSERT INTO ingredients (name, purchase_price, volume_ml, cost_per_ml) VALUES (?,?,?,?)", (n, p, v, p/v if v > 0 else 0))
                   conn.commit(); st.rerun()
           with t2:
               up = st.file_uploader("Αρχείο Excel", type=["xlsx"])
               if up and st.button("Import Υλικών"):
                   df = pd.read_excel(up)
                   for _, r in df.iterrows():
                       pr, vl = float(r['Price']), float(r['Volume'])
                       conn.execute("INSERT OR REPLACE INTO ingredients (name, purchase_price, volume_ml, cost_per_ml) VALUES (?,?,?,?)", (str(r['Name']).strip(), pr, vl, pr/vl if vl > 0 else 0))
                   conn.commit(); st.rerun()
   with c2:
       df_i = pd.read_sql_query("SELECT * FROM ingredients ORDER BY name ASC", conn)
       if not df_i.empty:
           with st.expander("📝 Επεξεργασία / Διαγραφή", expanded=True):
               sel = st.selectbox("Επιλέξτε Υλικό για αλλαγή", df_i['name'])
               row = df_i[df_i['name'] == sel].iloc[0]

               # Φόρμα Επεξεργασίας
               new_name = st.text_input("Όνομα", value=row['name'])
               new_price = st.number_input("Τιμή (€)", value=float(row['purchase_price']), format="%.2f")
               new_vol = st.number_input("ml", value=float(row['volume_ml']))

               col_btn1, col_btn2 = st.columns(2)
               if col_btn1.button("✅ Ενημέρωση"):
                   new_cost_ml = new_price / new_vol if new_vol > 0 else 0
                   conn.execute("UPDATE ingredients SET name=?, purchase_price=?, volume_ml=?, cost_per_ml=? WHERE id=?",
                                (new_name, new_price, new_vol, new_cost_ml, int(row['id'])))
                   conn.commit()
                   st.success("Το υλικό ενημερώθηκε!")
                   st.rerun()

               if col_btn2.button("🗑️ Διαγραφή"):
                   conn.execute("DELETE FROM ingredients WHERE id=?", (int(row['id']),))
                   conn.commit(); st.rerun()

   st.divider()
   st.dataframe(df_i.drop(columns=['id']), use_container_width=True)
   conn.close()

# --- 2. RECIPE BUILDER ---
elif page == "🛠️ Recipe Builder":
   st.title("🛠️ Σχεδιασμός Συνταγής")
   conn = sqlite3.connect('cocktail_factory.db')
   ing_df = pd.read_sql_query("SELECT name, cost_per_ml FROM ingredients ORDER BY name ASC", conn)

   col_opt, col_main = st.columns([1, 2])
   with col_opt:
       f_bot = st.number_input("Μπουκάλι/Καπάκι (€)", 0.19)
       f_box = st.number_input("Κούτα (€)", 0.02)
       f_ship = st.number_input("Μεταφορικά (€)", 0.01)
       f_tax = st.number_input("Φόρος %", 24.5)

   with col_main:
       rec_name = st.text_input("Όνομα Cocktail", value=st.session_state.edit_name)
       c1, c2, c3 = st.columns([2, 1, 1])
       sel_ing = c1.selectbox("Υλικό", ing_df['name']) if not ing_df.empty else ""
       sel_ml = c2.number_input("ml", 0.0)
       if c3.button("Προσθήκη"):
           st.session_state.builder_recipe.append({"Υλικό": sel_ing, "ml": sel_ml})
           st.rerun()

       liq_cost = 0
       for idx, item in enumerate(st.session_state.builder_recipe):
           p = ing_df[ing_df['name'] == item['Υλικό']]['cost_per_ml'].values[0] if item['Υλικό'] in ing_df['name'].values else 0
           cost_item = item['ml'] * p
           liq_cost += cost_item
           cols = st.columns([3, 1])
           cols[0].write(f"• {item['Υλικό']} ({item['ml']}ml)")
           if cols[1].button("🗑️", key=f"del_b_{idx}"):
               st.session_state.builder_recipe.pop(idx); st.rerun()

       total = liq_cost + (liq_cost * f_tax/100) + f_bot + f_box + f_ship
       st.metric("Κόστος Μονάδας", f"{total:.3f} €")
       if st.button("💾 Αποθήκευση Συνταγής"):
           conn.execute("INSERT OR REPLACE INTO recipes (name, ingredients_json, fixed_costs, tax_percent, box_cost, shipping_cost) VALUES (?,?,?,?,?,?)", (rec_name, json.dumps(st.session_state.builder_recipe), f_bot, f_tax, f_box, f_ship))
           conn.commit(); st.session_state.builder_recipe = []; st.session_state.edit_name = ""; st.rerun()
   conn.close()

# --- 3. ARCHIVE ---
elif page == "📂 Αρχείο Συνταγών":
   st.title("📂 Αρχείο Συνταγών")
   conn = sqlite3.connect('cocktail_factory.db')
   recs = pd.read_sql_query("SELECT * ORDER BY name ASC", "recipes", conn) if False else pd.read_sql_query("SELECT * FROM recipes ORDER BY name ASC", conn)
   if not recs.empty:
       sel_rec = st.selectbox("Επιλέξτε Συνταγή", recs['name'])
       r = recs[recs['name'] == sel_rec].iloc[0]
       ings = json.loads(r['ingredients_json'])

       st.subheader(f"Ανάλυση: {sel_rec}")
       ing_ps = pd.read_sql_query("SELECT name, cost_per_ml FROM ingredients", conn)

       table_data = []
       total_ml = 0
       liq_sum = 0
       for i in ings:
           p_row = ing_ps[ing_ps['name'] == i['Υλικό']]
           p_ml = p_row['cost_per_ml'].values[0] if not p_row.empty else 0
           item_c = i['ml'] * p_ml
           table_data.append({"Υλικό": i['Υλικό'], "Ποσότητα (ml)": i['ml'], "Κόστος/ml (€)": round(p_ml, 4), "Σύνολο Υλικού (€)": round(item_c, 3)})
           total_ml += i['ml']; liq_sum += item_c

       st.table(pd.DataFrame(table_data))
       st.divider()
       c1, c2, c3 = st.columns(3)
       c1.metric("Συνολικά ml", f"{total_ml} ml")
       c2.metric("Κόστος Υγρών (Net)", f"{liq_sum:.3f} €")
       tax_v = liq_sum * (r['tax_percent']/100)
       final = liq_sum + tax_v + r['fixed_costs'] + r['box_cost'] + r['shipping_cost']
       c3.metric("Τελικό Κόστος Μονάδας", f"{final:.3f} €")

       with st.expander("Ανάλυση Λοιπών Εξόδων"):
           st.write(f"• Φόρος ({r['tax_percent']}%): {tax_v:.3f}€")
           st.write(f"• Μπουκάλι/Καπάκι: {r['fixed_costs']}€")
           st.write(f"• Κούτα: {r['box_cost']}€")
           st.write(f"• Μεταφορικά: {r['shipping_cost']}€")

       btn_col1, btn_col2 = st.columns(2)
       if btn_col1.button("📝 Επεξεργασία"):
           st.session_state.builder_recipe = ings; st.session_state.edit_name = sel_rec; st.rerun()
       if btn_col2.button("🗑️ Διαγραφή"):
           conn.execute("DELETE FROM recipes WHERE name=?", (sel_rec,)); conn.commit(); st.rerun()
   conn.close()

# --- 4. NEW ORDER ---
elif page == "📝 Νέα Παραγγελία":
   st.title("📝 Καταχώρηση & Υπολογισμός Παραγωγής")
   conn = sqlite3.connect('cocktail_factory.db')
   recs = pd.read_sql_query("SELECT * FROM recipes ORDER BY name ASC", conn)

   col1, col2 = st.columns([1, 2])
   with col1:
       st.subheader("🛒 Επιλογή")
       selected = st.multiselect("Προϊόντα για παραγγελία:", recs['name'])
       order_items = []
       for s in selected:
           qty = st.number_input(f"Φιάλες {s}", min_value=1, value=10, key=f"q_{s}")
           order_items.append({"item": s, "qty": qty})

       if st.button("🚀 Αποθήκευση Παραγγελίας"):
           if order_items:
               conn.execute("INSERT INTO orders (order_date, items_json) VALUES (?,?)", (datetime.now().strftime("%d/%m/%Y %H:%M"), json.dumps(order_items)))
               conn.commit(); st.success("Αποθηκεύτηκε!")
           else: st.warning("Κενή παραγγελία.")

   with col2:
       st.subheader("🧪 Ανάγκες σε Πρώτες Ύλες")
       if order_items:
           raw = {}
           for entry in order_items:
               r_row = recs[recs['name'] == entry['item']].iloc[0]
               r_ings = json.loads(r_row['ingredients_json'])
               for ing in r_ings:
                   raw[ing['Υλικό']] = raw.get(ing['Υλικό'], 0) + (ing['ml'] * entry['qty'])

           df_needs = pd.DataFrame([{"Υλικό": k, "Συνολικά ml": v, "Λίτρα": round(v/1000, 2)} for k, v in raw.items()])
           st.table(df_needs)
           waste = st.slider("Φύρα %", 0, 10, 2)
           if waste > 0:
               df_needs["Με Φύρα (L)"] = round(df_needs["Λίτρα"] * (1 + waste/100), 2)
               st.dataframe(df_needs[["Υλικό", "Με Φύρα (L)"]], use_container_width=True)

   st.divider()
   st.subheader("📂 Ιστορικό")
   all_ords = pd.read_sql_query("SELECT id as 'ID', order_date as 'Ημερομηνία', items_json as 'Περιεχόμενο' FROM orders ORDER BY id DESC", conn)
   if not all_ords.empty:
       st.dataframe(all_ords, use_container_width=True)
       sel_id = st.selectbox("Επιλογή ID για διαγραφή", all_ords['ID'])
       if st.button("🗑️ Διαγραφή Παραγγελίας"):
           conn.execute("DELETE FROM orders WHERE id=?", (int(sel_id),)); conn.commit(); st.rerun()
   conn.close()

# --- 5. PRICE LIST ---
elif page == "📋 Τιμοκατάλογος":
   st.title("📋 Τιμοκατάλογος & Κερδοφορία")
   conn = sqlite3.connect('cocktail_factory.db')
   recs = pd.read_sql_query("SELECT * FROM recipes", conn)
   ing_p = pd.read_sql_query("SELECT name, cost_per_ml FROM ingredients", conn)

   markup = st.slider("Περιθώριο Κέρδους (επί του κόστους) %", 10, 300, 100)

   res = []
   for _, r in recs.iterrows():
       ings = json.loads(r['ingredients_json'])
       liq_c = sum([i['ml'] * (ing_p[ing_p['name']==i['Υλικό']]['cost_per_ml'].values[0] if i['Υλικό'] in ing_p['name'].values else 0) for i in ings])
       unit_cost = liq_c + (liq_c*r['tax_percent']/100) + r['fixed_costs'] + r['box_cost'] + r['shipping_cost']

       selling_price = unit_cost * (1 + markup/100)
       profit_eur = selling_price - unit_cost
       margin_pct = (profit_eur / selling_price) * 100 if selling_price > 0 else 0

       res.append({
           "Cocktail": r['name'],
           "Κόστος (€)": round(unit_cost, 3),
           "Τιμή Πώλησης (€)": round(selling_price, 2),
           "Κέρδος (€)": round(profit_eur, 2),
           "Margin %": f"{round(margin_pct, 1)}%"
       })

   st.table(pd.DataFrame(res))
   conn.close()