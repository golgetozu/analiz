import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Oto Sigorta Analiz", page_icon="🚗", layout="wide")

st.title("🚗 Oto Branşı Analiz Sistemi")

# Dosya Yükleme
st.sidebar.header("📂 Veri Yükle")
uretim_file = st.sidebar.file_uploader("Üretim Verisi", type=['xlsx', 'xls'])
hasar_file = st.sidebar.file_uploader("Hasar Verisi", type=['xlsx', 'xls'])

@st.cache_data
def load_excel(file):
    if file:
        df = pd.read_excel(file)
        # Tarih sütunlarını düzelt
        date_cols = ['P Tanzim Tarihi', 'P Baş.Tarih', 'P Bit. Tarihi', 'SYS Sistem Tarihi', 'P Onay Tarihi']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    return None

df_uretim = load_excel(uretim_file)
df_hasar = load_excel(hasar_file)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Özet", "🏭 Üretim", "💥 Hasar", "📈 H/P Oranı", "🚗 Araç Analizi", "🎯 Detaylı"
])

# TAB 1: ÖZET
with tab1:
    if df_uretim is not None:
        # Temel metrikler
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Toplam Poliçe", f"{len(df_uretim):,}")
        
        with col2:
            st.metric("Toplam Brüt Prim", f"₺{df_uretim['P Brüt Prim'].sum():,.0f}")
        
        with col3:
            st.metric("Toplam Net Prim", f"₺{df_uretim['P Net Prim'].sum():,.0f}")
        
        with col4:
            st.metric("Ortalama Prim", f"₺{df_uretim['P Brüt Prim'].mean():,.0f}")
        
        # İkinci satır metrikler
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            digital_count = df_uretim[df_uretim['DİJİTAL Mİ ? ( E / H )'] == 'E'].shape[0]
            digital_rate = (digital_count / len(df_uretim) * 100) if len(df_uretim) > 0 else 0
            st.metric("Dijital Poliçe", f"%{digital_rate:.1f}")
        
        with col6:
            unique_sources = df_uretim['P Kaynak Adı'].nunique()
            st.metric("Aktif Kaynak", f"{unique_sources}")
        
        with col7:
            if 'P Komisyon' in df_uretim.columns:
                st.metric("Toplam Komisyon", f"₺{df_uretim['P Komisyon'].sum():,.0f}")
        
        with col8:
            if df_hasar is not None:
                st.metric("Toplam Hasar", f"{len(df_hasar):,}")
        
        # Branş Dağılımı
        st.subheader("📊 Branş Dağılımı")
        col1, col2 = st.columns(2)
        
        with col1:
            # Kullanım Şekli pasta grafiği
            kullanim = df_uretim.groupby('KULLANIM ŞEKLİ')['P Brüt Prim'].sum()
            fig = px.pie(values=kullanim.values, names=kullanim.index, 
                        title="Kullanım Şekli Dağılımı", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # En çok üretim yapan iller
            il_uretim = df_uretim.groupby('U Sig. İl')['P Brüt Prim'].sum().nlargest(10)
            fig2 = px.bar(x=il_uretim.index, y=il_uretim.values, 
                         title="Top 10 İl - Prim Üretimi",
                         labels={'x': 'İl', 'y': 'Brüt Prim'})
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("👈 Sol panelden üretim Excel dosyanızı yükleyin")

# TAB 2: ÜRETİM ANALİZİ
with tab2:
    if df_uretim is not None:
        st.subheader("🏭 Üretim Analizi")
        
        # Analiz tipi seçimi
        analiz_tip = st.selectbox("Analiz Tipi", [
            "Kaynak (Acente) Performansı",
            "İl Bazlı Analiz",
            "Aylık Üretim Trendi",
            "Marka Dağılımı",
            "Dijital vs Geleneksel",
            "Cinsiyet Analizi",
            "Basamak Analizi"
        ])
        
        if analiz_tip == "Kaynak (Acente) Performansı":
            kaynak_analiz = df_uretim.groupby('P Kaynak Adı').agg({
                'P Brüt Prim': 'sum',
                'Poliçe No': 'count',
                'P Komisyon': 'sum'
            }).round(0).sort_values('P Brüt Prim', ascending=False).head(20)
            
            kaynak_analiz.columns = ['Toplam Prim', 'Poliçe Sayısı', 'Komisyon']
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(kaynak_analiz.head(10), y='Toplam Prim', 
                           title="Top 10 Kaynak - Prim Üretimi")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig2 = px.scatter(kaynak_analiz, x='Poliçe Sayısı', y='Toplam Prim',
                                size='Komisyon', hover_name=kaynak_analiz.index,
                                title="Kaynak Performans Matrisi")
                st.plotly_chart(fig2, use_container_width=True)
            
            st.dataframe(kaynak_analiz)
        
        elif analiz_tip == "İl Bazlı Analiz":
            il_analiz = df_uretim.groupby('U Sig. İl').agg({
                'P Brüt Prim': ['sum', 'mean'],
                'Poliçe No': 'count'
            }).round(0)
            il_analiz.columns = ['Toplam Prim', 'Ortalama Prim', 'Poliçe Sayısı']
            il_analiz = il_analiz.sort_values('Toplam Prim', ascending=False)
            
            fig = px.choropleth(
                geojson="https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json",
                locations=il_analiz.index,
                color=il_analiz['Toplam Prim'],
                title="İl Bazlı Prim Dağılımı"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(il_analiz.head(20))
        
        elif analiz_tip == "Aylık Üretim Trendi":
            df_uretim['Ay'] = pd.to_datetime(df_uretim['P Tanzim Tarihi']).dt.to_period('M')
            aylik = df_uretim.groupby('Ay').agg({
                'P Brüt Prim': 'sum',
                'Poliçe No': 'count'
            })
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=aylik.index.astype(str), y=aylik['P Brüt Prim'],
                                    mode='lines+markers', name='Prim',
                                    line=dict(color='blue', width=3)))
            fig.update_layout(title="Aylık Üretim Trendi", 
                            xaxis_title="Ay", yaxis_title="Brüt Prim")
            st.plotly_chart(fig, use_container_width=True)
        
        elif analiz_tip == "Marka Dağılımı":
            marka = df_uretim.groupby('MARKA').agg({
                'P Brüt Prim': 'sum',
                'Poliçe No': 'count'
            }).sort_values('P Brüt Prim', ascending=False).head(15)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(marka, y='P Brüt Prim', title="Top 15 Marka - Prim")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig2 = px.pie(values=marka['Poliçe No'][:10], names=marka.index[:10],
                            title="Top 10 Marka - Poliçe Sayısı")
                st.plotly_chart(fig2, use_container_width=True)
        
        elif analiz_tip == "Dijital vs Geleneksel":
            dijital_analiz = df_uretim.groupby('DİJİTAL Mİ ? ( E / H )').agg({
                'P Brüt Prim': ['sum', 'mean'],
                'Poliçe No': 'count'
            }).round(0)
            
            col1, col2, col3 = st.columns(3)
            
            dijital_prim = df_uretim[df_uretim['DİJİTAL Mİ ? ( E / H )'] == 'E']['P Brüt Prim'].sum()
            geleneksel_prim = df_uretim[df_uretim['DİJİTAL Mİ ? ( E / H )'] == 'H']['P Brüt Prim'].sum()
            
            with col1:
                st.metric("Dijital Kanallar", f"₺{dijital_prim:,.0f}")
            with col2:
                st.metric("Geleneksel Kanallar", f"₺{geleneksel_prim:,.0f}")
            with col3:
                dijital_oran = (dijital_prim / (dijital_prim + geleneksel_prim) * 100)
                st.metric("Dijital Oran", f"%{dijital_oran:.1f}")
            
            st.dataframe(dijital_analiz)
        
        elif analiz_tip == "Cinsiyet Analizi":
            cinsiyet = df_uretim.groupby('U Sig. Cinsiyet').agg({
                'P Brüt Prim': ['sum', 'mean'],
                'Poliçe No': 'count'
            }).round(0)
            st.dataframe(cinsiyet)
        
        elif analiz_tip == "Basamak Analizi":
            basamak = df_uretim.groupby('BASAMAK').agg({
                'P Brüt Prim': ['sum', 'mean'],
                'Poliçe No': 'count'
            }).round(0).sort_index()
            
            fig = px.line(x=basamak.index, y=basamak['P Brüt Prim']['sum'],
                        title="Basamak Bazında Prim Dağılımı",
                        markers=True)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(basamak)

# TAB 3: HASAR
with tab3:
    if df_hasar is not None:
        st.subheader("💥 Hasar Analizi")
        st.info("Hasar verisi yüklendi. Sütun yapısına göre analiz ekleyin.")
        st.dataframe(df_hasar.head())
    else:
        st.warning("Hasar verisi yüklenmedi")

# TAB 4: H/P ORANI
with tab4:
    if df_uretim is not None and df_hasar is not None:
        st.subheader("📈 Hasar/Prim Oranı")
        st.info("Her iki veri yüklendi. Eşleştirme için sütun seçin.")
    else:
        st.warning("H/P analizi için hem üretim hem hasar verisi gereklidir")

# TAB 5: ARAÇ ANALİZİ
with tab5:
    if df_uretim is not None:
        st.subheader("🚗 Araç Bazlı Analiz")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Model yılı analizi
            model_yili = df_uretim.groupby('MODEL YILI')['P Brüt Prim'].sum().sort_index()
            fig = px.bar(x=model_yili.index[-10:], y=model_yili.values[-10:],
                        title="Son 10 Model Yılı Prim Dağılımı")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Yakıt türü
            yakit = df_uretim.groupby('YAKIT TÜRÜ')['P Brüt Prim'].sum()
            fig2 = px.pie(values=yakit.values, names=yakit.index,
                         title="Yakıt Türü Dağılımı")
            st.plotly_chart(fig2, use_container_width=True)

# TAB 6: DETAYLI
with tab6:
    if df_uretim is not None:
        st.subheader("🎯 Detaylı Analizler")
        
        # Teminat analizi
        st.write("**Ek Teminat Kullanım Oranları**")
        
        teminatlar = {
            'Trafik': 'TRAFİK-Net Prim',
            'İMM': 'İMM-MADDİ BEDENİ AYRIMSIZ-Net Prim',
            'Yol Yardım': 'EMAA YOL YARDIM-Net Prim',
            'Ferdi Kaza': 'FERDİ KAZA - ÖLÜM / SÜREKLİ SAKAT.-Net Prim',
            'Hukuksal Koruma': 'HUKUKSAL KORUMA-Net Prim',
            'Mini Onarım': 'EMAA MİNİ ONARIM-Net Prim'
        }
        
        teminat_data = []
        for name, col in teminatlar.items():
            if col in df_uretim.columns:
                kullanan = (df_uretim[col] > 0).sum()
                oran = (kullanan / len(df_uretim) * 100)
                toplam = df_uretim[col].sum()
                teminat_data.append({
                    'Teminat': name,
                    'Kullanan Poliçe': kullanan,
                    'Kullanım Oranı (%)': oran,
                    'Toplam Prim': toplam
                })
        
        if teminat_data:
            teminat_df = pd.DataFrame(teminat_data)
            
            fig = px.bar(teminat_df, x='Teminat', y='Kullanım Oranı (%)',
                        title="Ek Teminat Kullanım Oranları")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(teminat_df)

# Footer
st.markdown("---")
st.caption("Oto Branşı Analiz Sistemi")
