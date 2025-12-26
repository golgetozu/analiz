import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Oto Sigorta Analiz", page_icon="🚗", layout="wide")

st.title("🚗 Oto Branşı Analiz Sistemi")

# Dosya Yükleme
st.sidebar.header("📂 Veri Yükle")
uretim_file = st.sidebar.file_uploader("Üretim Verisi", type=['xlsx', 'xls'])
hasar_file = st.sidebar.file_uploader("Hasar Verisi", type=['xlsx', 'xls'])

@st.cache_data
def load_excel(file):
    if file:
        return pd.read_excel(file)
    return None

df_uretim = load_excel(uretim_file)
df_hasar = load_excel(hasar_file)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Özet", "🏭 Üretim", "💥 Hasar", "📈 H/P Oranı"])

with tab1:
    if df_uretim is not None:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Poliçe Sayısı", f"{len(df_uretim):,}")
        
        prim_cols = [c for c in df_uretim.columns if 'prim' in c.lower()]
        if prim_cols:
            col2.metric("Toplam Prim", f"₺{df_uretim[prim_cols[0]].sum():,.0f}")
        
        if df_hasar is not None:
            col3.metric("Hasar Adedi", f"{len(df_hasar):,}")
            hasar_cols = [c for c in df_hasar.columns if 'öde' in c.lower() or 'tutar' in c.lower()]
            if hasar_cols:
                col4.metric("Toplam Hasar", f"₺{df_hasar[hasar_cols[0]].sum():,.0f}")
        
        st.dataframe(df_uretim.head(100))
    else:
        st.info("👈 Sol panelden Excel dosyalarınızı yükleyin")

with tab2:
    if df_uretim is not None:
        grup = st.selectbox("Gruplama", df_uretim.columns, key="g1")
        deger = st.selectbox("Değer", df_uretim.columns, key="d1")
        
        grouped = df_uretim.groupby(grup)[deger].sum().sort_values(ascending=False).head(15)
        fig = px.bar(x=grouped.index, y=grouped.values, title=f"{grup} Bazında {deger}")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    if df_hasar is not None:
        tutar = st.selectbox("Hasar Tutarı Sütunu", df_hasar.columns)
        col1, col2, col3 = st.columns(3)
        col1.metric("Ortalama", f"₺{df_hasar[tutar].mean():,.0f}")
        col2.metric("Medyan", f"₺{df_hasar[tutar].median():,.0f}")
        col3.metric("Maksimum", f"₺{df_hasar[tutar].max():,.0f}")
        
        fig = px.histogram(df_hasar, x=tutar, nbins=50)
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    if df_uretim is not None and df_hasar is not None:
        col1, col2 = st.columns(2)
        with col1:
            prim_col = st.selectbox("Prim Sütunu", df_uretim.columns)
            grup_u = st.selectbox("Grup (Üretim)", df_uretim.columns, key="gu")
        with col2:
            hasar_col = st.selectbox("Hasar Sütunu", df_hasar.columns)
            grup_h = st.selectbox("Grup (Hasar)", df_hasar.columns, key="gh")
        
        if st.button("Hesapla", type="primary"):
            prim_g = df_uretim.groupby(grup_u)[prim_col].sum()
            hasar_g = df_hasar.groupby(grup_h)[hasar_col].sum()
            
            sonuc = pd.DataFrame({'Prim': prim_g, 'Hasar': hasar_g}).dropna()
            sonuc['H/P %'] = (sonuc['Hasar'] / sonuc['Prim'] * 100).round(1)
            
            fig = px.bar(sonuc.reset_index(), x=grup_u, y='H/P %', 
                        color='H/P %', color_continuous_scale=['green','yellow','red'])
            fig.add_hline(y=70, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(sonuc)
