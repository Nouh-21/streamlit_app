import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import boto3
from datetime import datetime, timedelta
from io import BytesIO
import os

# Configuration AWS
AWS_BUCKET = "votre-bucket-s3"
AWS_KEY = "contributions.db"

# Initialisation de la base de données avec backup S3
@st.cache_resource
def init_db():
    """Initialise la base de données avec restauration depuis S3"""
    s3 = boto3.client(
        's3',
        aws_access_key_id=st.secrets['AWS_ACCESS_KEY'],
        aws_secret_access_key=st.secrets['AWS_SECRET_KEY']
    )
    
    try:
        s3.download_file(AWS_BUCKET, AWS_KEY, 'contributions.db')
        st.success("Base de données restaurée depuis S3")
    except Exception as e:
        st.info("Création d'une nouvelle base de données")
    
    return sqlite3.connect('contributions.db')

def backup_to_s3():
    """Sauvegarde de la base vers S3"""
    s3 = boto3.client(
        's3',
        aws_access_key_id=st.secrets['AWS_ACCESS_KEY'],
        aws_secret_access_key=st.secrets['AWS_SECRET_KEY']
    )
    
    with open('contributions.db', 'rb') as f:
        s3.upload_fileobj(
            Fileobj=f,
            Bucket=AWS_BUCKET,
            Key=AWS_KEY
        )

# Configuration de l'application
st.set_page_config(
    page_title="📊 Dashboard Budget Persistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Connexion à la base
conn = init_db()

# Création de la table si nécessaire
conn.execute('''
    CREATE TABLE IF NOT EXISTS contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telephone TEXT,
        montant REAL,
        date_virement DATE
    )
''')
conn.commit()

# Interface utilisateur
st.title("💶 Dashboard de Gestion des Contributions")

# Sidebar avec gestion des données
with st.sidebar:
    st.header("Gestion des Données")
    
    # Import de fichier
    uploaded_file = st.file_uploader("📤 Importer CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df['date_virement'] = pd.to_datetime(df['date_virement']).dt.date
            
            # Insertion en base
            df.to_sql('contributions', conn, if_exists='append', index=False)
            st.success(f"{len(df)} transactions importées!")
            backup_to_s3()
            
        except Exception as e:
            st.error(f"Erreur d'import : {str(e)}")
    
    # Gestion S3
    with st.expander("🔒 Sauvegarde/Restauration"):
        if st.button("🔄 Sauvegarder vers S3"):
            try:
                backup_to_s3()
                st.success("Backup réussi!")
            except Exception as e:
                st.error(f"Erreur : {str(e)}")
        
        if st.button("⏬ Restaurer depuis S3"):
            conn.close()
            os.remove('contributions.db')
            init_db()
            st.experimental_rerun()

# Récupération des données
df = pd.read_sql('SELECT * FROM contributions', conn)
df['date_virement'] = pd.to_datetime(df['date_virement'])

# Filtres
with st.expander("🔎 Filtres", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.date_input(
            "Période",
            value=[df['date_virement'].min().date(), df['date_virement'].max().date()],
            min_value=df['date_virement'].min().date(),
            max_value=df['date_virement'].max().date()
        )
    
    with col2:
        min_amount, max_amount = st.slider(
            "Fourchette de montants (€)",
            min_value=float(df['montant'].min()),
            max_value=float(df['montant'].max()),
            value=(float(df['montant'].min()), float(df['montant'].max()))
        )

# Application des filtres
filtered_df = df[
    (df['date_virement'].dt.date >= date_range[0]) & 
    (df['date_virement'].dt.date <= date_range[1]) &
    (df['montant'] >= min_amount) & 
    (df['montant'] <= max_amount)
]

# KPI
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Budget Total", f"{filtered_df['montant'].sum():,.2f} €")
with col2:
    st.metric("Moyenne Journalière", f"{filtered_df['montant'].mean():,.2f} €")
with col3:
    st.metric("Transactions", len(filtered_df))

# Visualisations
st.subheader("Évolution des Contributions")
fig = px.line(
    filtered_df.set_index('date_virement').resample('D').sum().reset_index(),
    x='date_virement',
    y='montant',
    labels={'montant': 'Montant (€)', 'date_virement': 'Date'},
    height=400
)
st.plotly_chart(fig, use_container_width=True)

# Détail des transactions
st.subheader("Dernières Transactions")
st.dataframe(
    filtered_df[['telephone', 'montant', 'date_virement']]
    .rename(columns={
        'telephone': '📱 Téléphone',
        'montant': '💶 Montant',
        'date_virement': '📅 Date'
    }),
    use_container_width=True,
    hide_index=True
)

# Backup automatique toutes les 30 minutes
if datetime.now().minute % 30 == 0:
    backup_to_s3()

# Fermeture connexion
conn.close()
