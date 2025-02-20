import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, Column, Integer, Float, String, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

st.set_page_config(
    page_title="Dashboard Contributions Financières",
    page_icon="💶",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Configuration de la base de données SQLite
Base = declarative_base()
engine = create_engine('sqlite:///contributions.db', echo=False)

class Contribution(Base):
    __tablename__ = 'contributions'
    id = Column(Integer, primary_key=True)
    telephone = Column(String(15))
    montant = Column(Float)
    date_virement = Column(Date)

# Création des tables si elles n'existent pas
Base.metadata.create_all(engine)

# Interface utilisateur
st.set_page_config(
    page_title="📊 Dashboard Budget Persistant",
    layout="wide"
)

# Fonction de gestion de la base de données
def get_session():
    Session = sessionmaker(bind=engine)
    return Session()

# Formulaire d'ajout manuel
with st.sidebar.expander("➕ Ajouter une transaction"):
    with st.form("transaction_form"):
        tel = st.text_input("Numéro de téléphone")
        amount = st.number_input("Montant (€)", min_value=0.0)
        date = st.date_input("Date du virement")
        
        if st.form_submit_button("Enregistrer"):
            with get_session() as session:
                new_contribution = Contribution(
                    telephone=tel,
                    montant=amount,
                    date_virement=date
                )
                session.add(new_contribution)
                session.commit()
            st.success("Transaction enregistrée!")

# Upload de fichier batch
uploaded_file = st.sidebar.file_uploader("📤 Importer CSV/Excel", type=["csv", "xlsx"])
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df['date_virement'] = pd.to_datetime(df['date_virement']).dt.date
        
        with get_session() as session:
            df.to_sql(
                name='contributions',
                con=engine,
                if_exists='append',
                index=False,
                dtype={
                    'telephone': String(15),
                    'montant': Float,
                    'date_virement': Date
                }
            )
        st.success(f"{len(df)} transactions importées!")
        
    except Exception as e:
        st.error(f"Erreur d'import : {str(e)}")

# Récupération des données
with get_session() as session:
    df = pd.read_sql_table('contributions', con=engine)

# Filtres et visualisation (identique à la version précédente mais avec données SQL)
if not df.empty:
    df['date_virement'] = pd.to_datetime(df['date_virement'])
    
    # Widgets de filtrage
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.date_input(
            "Période",
            value=[df['date_virement'].min().date(), df['date_virement'].max().date()]
        )
    
    with col2:
        min_amount, max_amount = st.slider(
            "Fourchette de montants (€)",
            min_value=float(df['montant'].min()),
            max_value=float(df['montant'].max()),
            value=(float(df['montant'].min()), float(df['montant'].max()))
        )

    # Filtrage
    filtered_df = df[
        (df['date_virement'].dt.date >= date_range[0]) &
        (df['date_virement'].dt.date <= date_range[1]) &
        (df['montant'] >= min_amount) &
        (df['montant'] <= max_amount)
    ]

    # Visualisations (garder le code précédent des graphiques)
    # ... [identique à la version précédente] ...

else:
    st.warning("Aucune donnée dans la base de données")

# Optimisation pour Streamlit Cloud
#st.sidebar.markdown("""
#**Configuration requise pour le déploiement :**
#1. Ajouter `contributions.db` au .gitignore
#2. Dans Streamlit Secrets :
#```toml
# Aucun secret nécessaire pour SQLite local
#""")
