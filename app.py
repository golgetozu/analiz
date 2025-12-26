import streamlit as st
st.set_page_config(page_title="Oto Sigorta Analiz", page_icon="🚗", layout="wide")

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==================== ŞİFRE KORUMASI ====================
def check_password():
    def password_entered():
        if st.session_state["password"] == "Emaa2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Giriş Yapın")
        st.text_input("Şifre", type="password", on_change=password_entered, key="password")
        st.info("Yetkisiz erişim yasaktır.")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Giriş Yapın")
        st.text_input("Şifre", type="password", on_change=password_entered, key="password")
        st.error("❌ Yanlış şifre!")
        return False
    else:
        return True

if not check_password():
    st.stop()
# ==================== ŞİFRE KORUMASI BİTTİ ====================

st.title("🚗 Oto Branşı Hasar/Prim Analiz Sistemi")

# Dosya Yükleme
st.sidebar.header("📂 Veri Yükle")
hasar_file = st.sidebar.file_uploader("Hasar/Prim Verisi", type=['xlsx', 'xls', 'xlsb'])

@st.cache_data(ttl=7200, show_spinner="Veri yükleniyor...")
def load_excel(file):
    if file:
        try:
            df = pd.read_excel(file)
            # Tarih sütunlarını düzelt
            date_cols = ['POLICE_BASLANGIC_TARIHI', 'POLICE_BITIS_TARIHI', 'ZEYIL_ONAY_TARIHI', 
                        'IPTAL_TARIHI', 'TAZMINAT_ODEME_TARIH', 'TAZMINAT_MAX_ODEME_TARIH', 'HASAR_TARIHI']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Dosya okuma hatası: {e}")
            return None
    return None

df_raw = load_excel(hasar_file)

# Ana hesaplama fonksiyonu
@st.cache_data(ttl=7200)
def hesapla_metrikler(df):
    """Tüm temel metrikleri hesapla ve cache'le"""
    
    # Net Hasar = Tazminat + Masraf - Rücu - Sovtaj
    df['NET_HASAR'] = (
        df['TAZMINAT_TOPLAM_ODEME_TUTAR'].fillna(0) + 
        df['MASRAF_TOPLAM_ODEME_TUTAR'].fillna(0) - 
        df['RUCU_TOPLAM_ODEME_TUTAR'].fillna(0) - 
        df['SOVTAJ_TOPLAM_ODEME_TUTAR'].fillna(0)
    )
    
    # Muallak dahil hasar
    df['TOPLAM_HASAR_MUALLAK'] = (
        df['NET_HASAR'] + 
        df['TAZMINAT_TOPLAM_MUALLAK_TUTAR'].fillna(0) + 
        df['MASRAF_TOPLAM_MUALLAK_TUTAR'].fillna(0) - 
        df['RUCU_TOPLAM_MUALLAK_TUTAR'].fillna(0) - 
        df['SOVTAJ_TOPLAM_MUALLAK_TUTAR'].fillna(0)
    )
    
    # Hasar/Prim oranı
    df['HP_ORANI'] = np.where(
        df['TOPLAM_KAZANILMIS_PRIM'] > 0,
        df['NET_HASAR'] / df['TOPLAM_KAZANILMIS_PRIM'] * 100,
        0
    )
    
    # Sürücü yaş grubu
    df['YAS_GRUBU'] = pd.cut(
        df['SURUCU_YASI'].fillna(35),
        bins=[0, 25, 35, 45, 55, 65, 100],
        labels=['18-25', '26-35', '36-45', '46-55', '56-65', '65+']
    )
    
    # Model yaş grubu
    current_year = pd.Timestamp.now().year
    df['ARAC_YASI'] = current_year - df['MODEL_YILI'].fillna(current_year - 5)
    df['ARAC_YAS_GRUBU'] = pd.cut(
        df['ARAC_YASI'],
        bins=[-1, 2, 5, 10, 15, 50],
        labels=['0-2 yaş', '3-5 yaş', '6-10 yaş', '11-15 yaş', '15+ yaş']
    )
    
    return df

# Segment analizi fonksiyonu
@st.cache_data(ttl=7200)
def segment_analizi(df, grup_kolonu):
    """Herhangi bir kolona göre segment analizi yap"""
    
    analiz = df.groupby(grup_kolonu).agg({
        'TOPLAM_KAZANILMIS_PRIM': 'sum',
        'NET_HASAR': 'sum',
        'TOPLAM_HASAR_MUALLAK': 'sum',
        'TOPLAM_IHBAR_ADET': 'sum',
        'KAZANILMIS_ADET': 'sum',
        'POLICE_NO': 'count'
    }).reset_index()
    
    analiz.columns = [grup_kolonu, 'Kazanılmış Prim', 'Net Hasar', 'Hasar+Muallak', 
                      'İhbar Adet', 'Kazanılmış Adet', 'Poliçe Sayısı']
    
    # H/P Oranı
    analiz['H/P Oranı (%)'] = np.where(
        analiz['Kazanılmış Prim'] > 0,
        (analiz['Net Hasar'] / analiz['Kazanılmış Prim'] * 100).round(1),
        0
    )
    
    # Hasar Frekansı
    analiz['Hasar Frekansı (%)'] = np.where(
        analiz['Kazanılmış Adet'] > 0,
        (analiz['İhbar Adet'] / analiz['Kazanılmış Adet'] * 100).round(2),
        0
    )
    
    # Ortalama Hasar
    analiz['Ort. Hasar'] = np.where(
        analiz['İhbar Adet'] > 0,
        (analiz['Net Hasar'] / analiz['İhbar Adet']).round(0),
        0
    )
    
    # Kar/Zarar
    analiz['Kar/Zarar'] = analiz['Kazanılmış Prim'] - analiz['Net Hasar']
    
    # Durum belirleme
    def durum_belirle(hp):
        if hp < 50:
            return '🟢 Karlı'
        elif hp < 70:
            return '🟡 Dikkat'
        elif hp < 100:
            return '🟠 Riskli'
        else:
            return '🔴 Zararlı'
    
    analiz['Durum'] = analiz['H/P Oranı (%)'].apply(durum_belirle)
    
    return analiz.sort_values('H/P Oranı (%)', ascending=False)

# Sekmeler
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Özet Dashboard", 
    "🔍 Segment Analizi", 
    "🗺️ Bölgesel Analiz",
    "👤 Sürücü Profili",
    "🚗 Araç Analizi",
    "📈 Trend & Tahmin"
])

# ==================== TAB 1: ÖZET DASHBOARD ====================
with tab1:
    if df_raw is not None:
        df = hesapla_metrikler(df_raw.copy())
        
        st.subheader("📊 Genel Performans Özeti")
        
        # Ana metrikler
        col1, col2, col3, col4, col5 = st.columns(5)
        
        toplam_prim = df['TOPLAM_KAZANILMIS_PRIM'].sum()
        toplam_hasar = df['NET_HASAR'].sum()
        toplam_muallak = df['TOPLAM_HASAR_MUALLAK'].sum()
        genel_hp = (toplam_hasar / toplam_prim * 100) if toplam_prim > 0 else 0
        
        with col1:
            st.metric("Kazanılmış Prim", f"₺{toplam_prim:,.0f}")
        with col2:
            st.metric("Net Hasar", f"₺{toplam_hasar:,.0f}")
        with col3:
            st.metric("Hasar + Muallak", f"₺{toplam_muallak:,.0f}")
        with col4:
            delta_color = "inverse" if genel_hp > 70 else "normal"
            st.metric("H/P Oranı", f"%{genel_hp:.1f}", delta=f"{'Riskli' if genel_hp > 70 else 'Normal'}", delta_color=delta_color)
        with col5:
            kar_zarar = toplam_prim - toplam_hasar
            st.metric("Kar/Zarar", f"₺{kar_zarar:,.0f}")
        
        # İkinci satır metrikler
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Toplam Poliçe", f"{len(df):,}")
        with col2:
            st.metric("Toplam İhbar", f"{df['TOPLAM_IHBAR_ADET'].sum():,.0f}")
        with col3:
            frekans = (df['TOPLAM_IHBAR_ADET'].sum() / df['KAZANILMIS_ADET'].sum() * 100) if df['KAZANILMIS_ADET'].sum() > 0 else 0
            st.metric("Hasar Frekansı", f"%{frekans:.2f}")
        with col4:
            ort_hasar = toplam_hasar / df['TOPLAM_IHBAR_ADET'].sum() if df['TOPLAM_IHBAR_ADET'].sum() > 0 else 0
            st.metric("Ort. Hasar Tutarı", f"₺{ort_hasar:,.0f}")
        
        st.markdown("---")
        
        # Hızlı Görselleştirmeler
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔴 En Zararlı 10 Segment")
            # Bölge bazlı hızlı analiz
            bolge_analiz = segment_analizi(df, 'BOLGE_AD')
            zararli = bolge_analiz[bolge_analiz['H/P Oranı (%)'] > 70].head(10)
            
            if len(zararli) > 0:
                fig = px.bar(zararli, x='BOLGE_AD', y='H/P Oranı (%)', 
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Bölge Bazlı H/P Oranı (Zararlı Olanlar)")
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Tüm bölgeler karlı!")
        
        with col2:
            st.subheader("🟢 En Karlı 10 Segment")
            karli = bolge_analiz[bolge_analiz['H/P Oranı (%)'] < 50].head(10)
            
            if len(karli) > 0:
                fig = px.bar(karli.sort_values('H/P Oranı (%)'), x='BOLGE_AD', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Bölge Bazlı H/P Oranı (Karlı Olanlar)")
                fig.add_hline(y=50, line_dash="dash", line_color="green")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("50% altında bölge yok")
        
        # Hasar dağılımı
        st.subheader("📊 Hasar Tipi Dağılımı")
        col1, col2 = st.columns(2)
        
        with col1:
            hasar_tipleri = pd.DataFrame({
                'Hasar Tipi': ['Maddi', 'Bedeni', 'Değer Kaybı', 'Diğer'],
                'Tutar': [
                    df['TAZMINAT_MADDI_ODEME_TUTAR'].sum(),
                    df['TAZMINAT_BEDENI_ODEME_TUTAR'].sum(),
                    df['TAZMINAT_DEGER_KAYBI_ODEME_TUTAR'].sum(),
                    df['TAZMINAT_DIGER_ODEME_TUTAR'].sum()
                ]
            })
            fig = px.pie(hasar_tipleri, values='Tutar', names='Hasar Tipi', 
                        title="Hasar Tipi Dağılımı", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            ihbar_tipleri = pd.DataFrame({
                'İhbar Tipi': ['Maddi', 'Bedeni', 'Değer Kaybı', 'Diğer'],
                'Adet': [
                    df['MADDI_IHBAR_ADET'].sum(),
                    df['BEDENI_IHBAR_ADET'].sum(),
                    df['DEGER_KAYBI_IHBAR_ADET'].sum(),
                    df['DIGER_IHBAR_ADET'].sum()
                ]
            })
            fig = px.pie(ihbar_tipleri, values='Adet', names='İhbar Tipi',
                        title="İhbar Tipi Dağılımı", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.info("👈 Sol panelden hasar/prim Excel dosyanızı yükleyin")

# ==================== TAB 2: SEGMENT ANALİZİ ====================
with tab2:
    if df_raw is not None:
        df = hesapla_metrikler(df_raw.copy())
        
        st.subheader("🔍 Detaylı Segment Analizi")
        
        # Analiz boyutu seçimi
        analiz_secenekleri = {
            'Bölge': 'BOLGE_AD',
            'Acente': 'ACENTE_AD',
            'İl (Sigortalı)': 'SIG_IL_KODU',
            'İl (Plaka)': 'PLAKA_IL',
            'Kullanım Tarzı': 'KULLANIM_TARZI',
            'Marka': 'MARKA',
            'Basamak': 'BASAMAK_KODU',
            'Ürün': 'URUN_ADI',
            'Sürücü Yaş Grubu': 'YAS_GRUBU',
            'Araç Yaş Grubu': 'ARAC_YAS_GRUBU',
            'Medeni Durum': 'MEDENI_DURUM',
            'Cinsiyet': 'CINSIYET',
            'Özel/Tüzel': 'OZEL_TUZEL',
            'Yakıt Tipi': 'YAKIT_TIPI',
            'Havuz Durumu': 'HAVUZ_DURUM',
            'Model Yılı': 'MODEL_YILI'
        }
        
        col1, col2 = st.columns(2)
        with col1:
            secilen_boyut = st.selectbox("Analiz Boyutu Seçin", list(analiz_secenekleri.keys()))
        with col2:
            min_police = st.number_input("Minimum Poliçe Sayısı", min_value=1, value=10)
        
        kolon = analiz_secenekleri[secilen_boyut]
        
        if kolon in df.columns:
            analiz = segment_analizi(df, kolon)
            analiz = analiz[analiz['Poliçe Sayısı'] >= min_police]
            
            # Özet metrikler
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                zararli_sayisi = len(analiz[analiz['H/P Oranı (%)'] > 100])
                st.metric("🔴 Zararlı Segment", zararli_sayisi)
            with col2:
                riskli_sayisi = len(analiz[(analiz['H/P Oranı (%)'] > 70) & (analiz['H/P Oranı (%)'] <= 100)])
                st.metric("🟠 Riskli Segment", riskli_sayisi)
            with col3:
                dikkat_sayisi = len(analiz[(analiz['H/P Oranı (%)'] > 50) & (analiz['H/P Oranı (%)'] <= 70)])
                st.metric("🟡 Dikkat Segment", dikkat_sayisi)
            with col4:
                karli_sayisi = len(analiz[analiz['H/P Oranı (%)'] <= 50])
                st.metric("🟢 Karlı Segment", karli_sayisi)
            
            # Görselleştirme
            st.subheader(f"📊 {secilen_boyut} Bazlı H/P Analizi")
            
            # Top 20 göster
            analiz_top = analiz.head(20)
            
            fig = px.bar(analiz_top, x=kolon, y='H/P Oranı (%)',
                        color='H/P Oranı (%)',
                        color_continuous_scale=['green', 'yellow', 'orange', 'red'],
                        hover_data=['Kazanılmış Prim', 'Net Hasar', 'Kar/Zarar', 'Poliçe Sayısı'],
                        title=f"{secilen_boyut} Bazlı H/P Oranı (En Yüksek 20)")
            fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Risk Eşiği %70")
            fig.add_hline(y=100, line_dash="dash", line_color="darkred", annotation_text="Zarar Eşiği %100")
            st.plotly_chart(fig, use_container_width=True)
            
            # Detaylı tablo
            st.subheader("📋 Detaylı Tablo")
            
            # Filtreleme
            col1, col2 = st.columns(2)
            with col1:
                durum_filtre = st.multiselect("Durum Filtresi", 
                    ['🔴 Zararlı', '🟠 Riskli', '🟡 Dikkat', '🟢 Karlı'],
                    default=['🔴 Zararlı', '🟠 Riskli'])
            
            if durum_filtre:
                analiz_filtered = analiz[analiz['Durum'].isin(durum_filtre)]
            else:
                analiz_filtered = analiz
            
            # Format
            format_dict = {
                'Kazanılmış Prim': '₺{:,.0f}',
                'Net Hasar': '₺{:,.0f}',
                'Hasar+Muallak': '₺{:,.0f}',
                'Kar/Zarar': '₺{:,.0f}',
                'Ort. Hasar': '₺{:,.0f}',
                'H/P Oranı (%)': '{:.1f}%',
                'Hasar Frekansı (%)': '{:.2f}%'
            }
            
            st.dataframe(analiz_filtered.style.format(format_dict), use_container_width=True)
            
            # Öneri kutusu
            st.subheader("💡 Stratejik Öneriler")
            
            zararli_segmentler = analiz[analiz['H/P Oranı (%)'] > 100]
            karli_segmentler = analiz[analiz['H/P Oranı (%)'] < 50]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.error("🔴 **PRİM ARTIŞI ÖNERİLEN SEGMENTLER**")
                if len(zararli_segmentler) > 0:
                    for _, row in zararli_segmentler.head(5).iterrows():
                        st.write(f"• **{row[kolon]}**: H/P %{row['H/P Oranı (%)']:.0f} - Zarar: ₺{abs(row['Kar/Zarar']):,.0f}")
                else:
                    st.write("Zararlı segment yok")
            
            with col2:
                st.success("🟢 **İNDİRİM UYGULANABİLECEK SEGMENTLER**")
                if len(karli_segmentler) > 0:
                    for _, row in karli_segmentler.head(5).iterrows():
                        st.write(f"• **{row[kolon]}**: H/P %{row['H/P Oranı (%)']:.0f} - Kar: ₺{row['Kar/Zarar']:,.0f}")
                else:
                    st.write("Çok karlı segment yok")
        else:
            st.warning(f"'{kolon}' sütunu verilerinizde bulunamadı")
    else:
        st.info("👈 Sol panelden veri yükleyin")

# ==================== TAB 3: BÖLGESEL ANALİZ ====================
with tab3:
    if df_raw is not None:
        df = hesapla_metrikler(df_raw.copy())
        
        st.subheader("🗺️ Bölgesel Performans Analizi")
        
        col1, col2 = st.columns(2)
        
        with col1:
            il_tipi = st.radio("İl Bazı", ["Sigortalı İli (SIG_IL_KODU)", "Plaka İli (PLAKA_IL)"])
        
        il_kolon = 'SIG_IL_KODU' if 'Sigortalı' in il_tipi else 'PLAKA_IL'
        
        if il_kolon in df.columns:
            il_analiz = segment_analizi(df, il_kolon)
            
            # Harita yerine bar chart (Türkiye haritası için ek kütüphane gerekir)
            st.subheader("📊 İl Bazlı H/P Oranı")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🔴 En Zararlı 15 İl**")
                zararli_iller = il_analiz.head(15)
                fig = px.bar(zararli_iller, x=il_kolon, y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['yellow', 'orange', 'red'],
                           hover_data=['Kazanılmış Prim', 'Net Hasar'])
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.write("**🟢 En Karlı 15 İl**")
                karli_iller = il_analiz.sort_values('H/P Oranı (%)').head(15)
                fig = px.bar(karli_iller, x=il_kolon, y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow'],
                           hover_data=['Kazanılmış Prim', 'Net Hasar'])
                fig.add_hline(y=50, line_dash="dash", line_color="green")
                st.plotly_chart(fig, use_container_width=True)
            
            # Bölge analizi
            if 'BOLGE_AD' in df.columns:
                st.subheader("📊 Bölge Bazlı Analiz")
                bolge_analiz = segment_analizi(df, 'BOLGE_AD')
                
                fig = px.treemap(bolge_analiz, path=['BOLGE_AD'], values='Kazanılmış Prim',
                               color='H/P Oranı (%)',
                               color_continuous_scale=['green', 'yellow', 'red'],
                               title="Bölge Bazlı Prim ve H/P Oranı")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(bolge_analiz, use_container_width=True)
    else:
        st.info("👈 Sol panelden veri yükleyin")

# ==================== TAB 4: SÜRÜCÜ PROFİLİ ====================
with tab4:
    if df_raw is not None:
        df = hesapla_metrikler(df_raw.copy())
        
        st.subheader("👤 Sürücü Profili Analizi")
        
        col1, col2 = st.columns(2)
        
        # Yaş grubu analizi
        with col1:
            st.write("**📊 Yaş Grubu Analizi**")
            if 'YAS_GRUBU' in df.columns:
                yas_analiz = segment_analizi(df, 'YAS_GRUBU')
                
                fig = px.bar(yas_analiz, x='YAS_GRUBU', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Yaş Grubu Bazlı H/P Oranı")
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(yas_analiz, use_container_width=True)
        
        # Cinsiyet analizi
        with col2:
            st.write("**📊 Cinsiyet Analizi**")
            if 'CINSIYET' in df.columns:
                cinsiyet_analiz = segment_analizi(df, 'CINSIYET')
                
                fig = px.bar(cinsiyet_analiz, x='CINSIYET', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Cinsiyet Bazlı H/P Oranı")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(cinsiyet_analiz, use_container_width=True)
        
        # Medeni durum ve Özel/Tüzel
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 Medeni Durum Analizi**")
            if 'MEDENI_DURUM' in df.columns:
                medeni_analiz = segment_analizi(df, 'MEDENI_DURUM')
                
                fig = px.bar(medeni_analiz, x='MEDENI_DURUM', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Medeni Durum Bazlı H/P Oranı")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(medeni_analiz, use_container_width=True)
        
        with col2:
            st.write("**📊 Özel/Tüzel Analizi**")
            if 'OZEL_TUZEL' in df.columns:
                ozel_tuzel_analiz = segment_analizi(df, 'OZEL_TUZEL')
                
                fig = px.bar(ozel_tuzel_analiz, x='OZEL_TUZEL', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Özel/Tüzel Bazlı H/P Oranı")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(ozel_tuzel_analiz, use_container_width=True)
        
        # Çapraz analiz
        st.subheader("🔀 Çapraz Analiz")
        
        col1, col2 = st.columns(2)
        with col1:
            capraz1 = st.selectbox("Birinci Boyut", ['CINSIYET', 'MEDENI_DURUM', 'OZEL_TUZEL', 'YAS_GRUBU'])
        with col2:
            capraz2 = st.selectbox("İkinci Boyut", ['YAS_GRUBU', 'CINSIYET', 'MEDENI_DURUM', 'OZEL_TUZEL'])
        
        if capraz1 in df.columns and capraz2 in df.columns:
            capraz_analiz = df.groupby([capraz1, capraz2]).agg({
                'TOPLAM_KAZANILMIS_PRIM': 'sum',
                'NET_HASAR': 'sum'
            }).reset_index()
            
            capraz_analiz['H/P Oranı'] = np.where(
                capraz_analiz['TOPLAM_KAZANILMIS_PRIM'] > 0,
                capraz_analiz['NET_HASAR'] / capraz_analiz['TOPLAM_KAZANILMIS_PRIM'] * 100,
                0
            )
            
            fig = px.density_heatmap(capraz_analiz, x=capraz1, y=capraz2, z='H/P Oranı',
                                    color_continuous_scale=['green', 'yellow', 'red'],
                                    title=f"{capraz1} vs {capraz2} - H/P Oranı Heatmap")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👈 Sol panelden veri yükleyin")

# ==================== TAB 5: ARAÇ ANALİZİ ====================
with tab5:
    if df_raw is not None:
        df = hesapla_metrikler(df_raw.copy())
        
        st.subheader("🚗 Araç Bazlı Analiz")
        
        col1, col2 = st.columns(2)
        
        # Marka analizi
        with col1:
            st.write("**📊 Marka Analizi**")
            if 'MARKA' in df.columns:
                marka_analiz = segment_analizi(df, 'MARKA')
                marka_analiz = marka_analiz[marka_analiz['Poliçe Sayısı'] >= 50]
                
                fig = px.bar(marka_analiz.head(20), x='MARKA', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Marka Bazlı H/P Oranı (Top 20)")
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
        
        # Araç yaşı analizi
        with col2:
            st.write("**📊 Araç Yaşı Analizi**")
            if 'ARAC_YAS_GRUBU' in df.columns:
                arac_yas_analiz = segment_analizi(df, 'ARAC_YAS_GRUBU')
                
                fig = px.bar(arac_yas_analiz, x='ARAC_YAS_GRUBU', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Araç Yaşı Bazlı H/P Oranı")
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
        
        # Kullanım tarzı ve Yakıt tipi
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 Kullanım Tarzı Analizi**")
            if 'KULLANIM_TARZI' in df.columns:
                kullanim_analiz = segment_analizi(df, 'KULLANIM_TARZI')
                
                fig = px.bar(kullanim_analiz, x='KULLANIM_TARZI', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Kullanım Tarzı Bazlı H/P Oranı")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(kullanim_analiz, use_container_width=True)
        
        with col2:
            st.write("**📊 Yakıt Tipi Analizi**")
            if 'YAKIT_TIPI' in df.columns:
                yakit_analiz = segment_analizi(df, 'YAKIT_TIPI')
                
                fig = px.bar(yakit_analiz, x='YAKIT_TIPI', y='H/P Oranı (%)',
                           color='H/P Oranı (%)',
                           color_continuous_scale=['green', 'yellow', 'red'],
                           title="Yakıt Tipi Bazlı H/P Oranı")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(yakit_analiz, use_container_width=True)
        
        # Basamak analizi
        st.subheader("📊 Basamak Analizi")
        if 'BASAMAK_KODU' in df.columns:
            basamak_analiz = segment_analizi(df, 'BASAMAK_KODU')
            
            fig = px.line(basamak_analiz.sort_values('BASAMAK_KODU'), 
                         x='BASAMAK_KODU', y='H/P Oranı (%)',
                         markers=True,
                         title="Basamak Bazlı H/P Oranı Trendi")
            fig.add_hline(y=70, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(basamak_analiz, use_container_width=True)
    else:
        st.info("👈 Sol panelden veri yükleyin")

# ==================== TAB 6: TREND & TAHMİN ====================
with tab6:
    if df_raw is not None:
        df = hesapla_metrikler(df_raw.copy())
        
        st.subheader("📈 Trend Analizi")
        
        if 'POLICE_BASLANGIC_TARIHI' in df.columns:
            df['AY'] = df['POLICE_BASLANGIC_TARIHI'].dt.to_period('M')
            
            aylik = df.groupby('AY').agg({
                'TOPLAM_KAZANILMIS_PRIM': 'sum',
                'NET_HASAR': 'sum',
                'TOPLAM_IHBAR_ADET': 'sum',
                'KAZANILMIS_ADET': 'sum'
            }).reset_index()
            
            aylik['AY'] = aylik['AY'].astype(str)
            aylik['H/P Oranı'] = np.where(
                aylik['TOPLAM_KAZANILMIS_PRIM'] > 0,
                aylik['NET_HASAR'] / aylik['TOPLAM_KAZANILMIS_PRIM'] * 100,
                0
            )
            
            # Trend grafiği
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(x=aylik['AY'], y=aylik['TOPLAM_KAZANILMIS_PRIM'],
                                    mode='lines+markers', name='Kazanılmış Prim',
                                    line=dict(color='blue', width=2)))
            
            fig.add_trace(go.Scatter(x=aylik['AY'], y=aylik['NET_HASAR'],
                                    mode='lines+markers', name='Net Hasar',
                                    line=dict(color='red', width=2)))
            
            fig.update_layout(title="Aylık Prim ve Hasar Trendi",
                            xaxis_title="Ay", yaxis_title="Tutar (₺)")
            st.plotly_chart(fig, use_container_width=True)
            
            # H/P oranı trendi
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=aylik['AY'], y=aylik['H/P Oranı'],
                                     mode='lines+markers', name='H/P Oranı',
                                     line=dict(color='purple', width=3)))
            fig2.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Risk Eşiği")
            fig2.update_layout(title="Aylık H/P Oranı Trendi",
                             xaxis_title="Ay", yaxis_title="H/P Oranı (%)")
            st.plotly_chart(fig2, use_container_width=True)
            
            st.dataframe(aylik, use_container_width=True)
        
        # UW Yılı analizi
        st.subheader("📅 UW Yılı Bazlı Analiz")
        if 'UW_YIL' in df.columns:
            uw_analiz = segment_analizi(df, 'UW_YIL')
            
            fig = px.bar(uw_analiz, x='UW_YIL', y=['Kazanılmış Prim', 'Net Hasar'],
                        barmode='group', title="UW Yılı Bazlı Prim vs Hasar")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(uw_analiz, use_container_width=True)
    else:
        st.info("👈 Sol panelden veri yükleyin")

# Alt bilgi
st.markdown("---")
st.caption("Oto Branşı Hasar/Prim Analiz Sistemi v3.0")
