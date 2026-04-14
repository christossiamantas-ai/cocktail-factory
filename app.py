import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Cocktail Factory Cloud v13.1", layout="wide")

# Σύνδεση με το Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet):
   try:
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
page = st.sidebar.selectbox("Μενού", ["📊 Dashboard", "📦 Αποθήκη", "🛠️ Recipe Builder", "📂 Αρχείο Συνταγών", "📝 Νέα Παραγγελία", "📋 Τιμοκατάλογος"])

# --- 1. INVENTORY (ΜΕ ΔΙΟΡΘΩΜΕΝΟ IMPORT ΓΙΑ GOOGLE SHEETS) ---
if page == "📦 Αποθήκη":
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
               up = st.file_uploader("Ανεβάστε αρχείο Excel", type=["xlsx"])
               if up and st.button("🚀 Εκτέλεση Import"):
                   df_upload = pd.read_excel(up)
                   # Μετατροπή των στηλών του Excel στις στήλες της βάσης μας
                   new_ings = pd.DataFrame({
                       "name": df_upload["Name"],
                       "purchase_price": df_upload["Price"],
                       "volume_ml": df_upload["Volume"],
                       "cost_per_ml": df_upload["Price"] / df_upload["Volume"]
                   })
                   # Συνένωση με τα υπάρχοντα και αποθήκευση στο Google Sheet
                   updated_df = pd.concat([ings, new_ings], ignore_index=True).drop_duplicates(subset=['name'], keep='last')
                   save_data(updated_df, "ingredients")
                   st.success(f"Εισήχθησαν {len(new_ings)} υλικά!")
                   st.rerun()

   with c2:
       if not ings.empty:
           with st.expander("📝 Επεξεργασία / Διαγραφή"):
               sel = st.selectbox("Επιλέξτε Υλικό", ings['name'])
               idx = ings[ings['name'] == sel].index[0]
               if st.button("🗑️ Διαγραφή Υλικού"):
                   ings = ings.drop(idx)
                   save_data(ings, "ingredients")
                   st.rerun()

   st.divider()
   st.subheader("Λίστα Υλικών στο Google Sheet")
   st.dataframe(ings, use_container_width=True)
