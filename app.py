import streamlit as st
st.set_page_config(page_title="Oto Sigorta Analiz", page_icon="🚗", layout="wide")

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import statsmodels.api as sm
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

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

st.title("🚗 Oto Branşı Analiz Sistemi - Aktüeryal Modül")

# Dosya Yükleme
st.sidebar.header("📂 Veri Yükle")
uretim_file = st.sidebar.file_uploader("Üretim Verisi", type=['xlsx', 'xls', 'xlsb'])
hasar_file = st.sidebar.file_uploader("Hasar Verisi", type=['xlsx', 'xls', 'xlsb'])

@st.cache_data(ttl=3600)
def load_excel(file):
    if file:
        try:
            df = pd.read_excel(file)
            date_cols = ['P Tanzim Tarihi', 'P Baş.Tarih', 'P Bit. Tarihi']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Dosya okuma hatası: {e}")
            return None
    return None

df_uretim_raw = load_excel(uretim_file)
df_hasar_raw = load_excel(hasar_file)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Özet", "🏭 Üretim", "💥 Hasar", "📈 H/P Oranı", 
    "🔬 GLM Analizi", "📉 Aktüeryal", "🎯 Risk Skorlama"
])

# TAB 1: ÖZET
with tab1:
    if df_uretim_raw is not None:
        df_uretim = df_uretim_raw.copy()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Toplam Poliçe", f"{len(df_uretim):,}")
        with col2:
            st.metric("Toplam Brüt Prim", f"₺{df_uretim['P Brüt Prim'].sum():,.0f}")
        with col3:
            st.metric("Toplam Net Prim", f"₺{df_uretim['P Net Prim'].sum():,.0f}")
        with col4:
            st.metric("Ortalama Prim", f"₺{df_uretim['P Brüt Prim'].mean():,.0f}")
        
        st.subheader("📊 Özet İstatistikler")
        col1, col2 = st.columns(2)
        
        with col1:
            kullanim = df_uretim.groupby('KULLANIM ŞEKLİ')['P Brüt Prim'].sum()
            fig = px.pie(values=kullanim.values, names=kullanim.index, 
                        title="Kullanım Şekli Dağılımı", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            il_uretim = df_uretim.groupby('U Sig. İl')['P Brüt Prim'].sum().nlargest(10)
            fig2 = px.bar(x=il_uretim.index, y=il_uretim.values, 
                         title="Top 10 İl - Prim Üretimi")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("👈 Sol panelden üretim Excel dosyanızı yükleyin")

# TAB 2: ÜRETİM
with tab2:
    if df_uretim_raw is not None:
        df_uretim = df_uretim_raw.copy()
        
        st.subheader("🏭 Üretim Analizi")
        
        analiz_tip = st.selectbox("Analiz Tipi", [
            "Kaynak Performansı", "İl Bazlı", "Aylık Trend", 
            "Marka Dağılımı", "Dijital vs Geleneksel"
        ])
        
        if analiz_tip == "Kaynak Performansı":
            kaynak = df_uretim.groupby('P Kaynak Adı').agg({
                'P Brüt Prim': 'sum',
                'Poliçe No': 'count'
            }).sort_values('P Brüt Prim', ascending=False).head(15)
            
            fig = px.bar(kaynak, y='P Brüt Prim', title="Top 15 Kaynak")
            st.plotly_chart(fig, use_container_width=True)
        
        elif analiz_tip == "İl Bazlı":
            il_analiz = df_uretim.groupby('U Sig. İl').agg({
                'P Brüt Prim': ['sum', 'mean'],
                'Poliçe No': 'count'
            }).round(0)
            il_analiz.columns = ['Toplam Prim', 'Ortalama Prim', 'Poliçe Sayısı']
            il_analiz = il_analiz.sort_values('Toplam Prim', ascending=False)
            
            fig = px.bar(il_analiz.head(20).reset_index(), x='U Sig. İl', y='Toplam Prim',
                        title="İl Bazlı Prim Dağılımı (Top 20)")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(il_analiz.head(20))
        
        elif analiz_tip == "Aylık Trend":
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
                fig2 = px.pie(values=marka['Poliçe No'][:10].values, 
                             names=marka.index[:10],
                             title="Top 10 Marka - Poliçe Sayısı")
                st.plotly_chart(fig2, use_container_width=True)
        
        elif analiz_tip == "Dijital vs Geleneksel":
            col1, col2, col3 = st.columns(3)
            
            dijital_prim = df_uretim[df_uretim['DİJİTAL Mİ ? ( E / H )'] == 'E']['P Brüt Prim'].sum()
            geleneksel_prim = df_uretim[df_uretim['DİJİTAL Mİ ? ( E / H )'] == 'H']['P Brüt Prim'].sum()
            
            with col1:
                st.metric("Dijital Kanallar", f"₺{dijital_prim:,.0f}")
            with col2:
                st.metric("Geleneksel Kanallar", f"₺{geleneksel_prim:,.0f}")
            with col3:
                toplam = dijital_prim + geleneksel_prim
                if toplam > 0:
                    dijital_oran = (dijital_prim / toplam * 100)
                    st.metric("Dijital Oran", f"%{dijital_oran:.1f}")
    else:
        st.info("👈 Sol panelden üretim Excel dosyanızı yükleyin")

# TAB 3: HASAR
with tab3:
    if df_hasar_raw is not None:
        st.subheader("💥 Hasar Analizi")
        st.dataframe(df_hasar_raw.head())
    else:
        st.warning("Hasar verisi yüklenmedi")

# TAB 4: H/P ORANI
with tab4:
    if df_uretim_raw is not None:
        st.subheader("📈 Hasar/Prim Oranı")
        st.info("Hasar verisi yüklendiğinde H/P oranı hesaplanacak")
    else:
        st.info("👈 Sol panelden veri yükleyin")

# TAB 5: GLM ANALİZİ
with tab5:
    if df_uretim_raw is not None:
        st.header("🔬 GLM (Generalized Linear Model) Analizi")
        
        st.markdown("""
        ### GLM ile Prim Tahmini
        Aktüeryal fiyatlamada kullanılan GLM modelini verilerinize uyguluyoruz.
        """)
        
        model_data = df_uretim_raw.copy()
        
        le_il = LabelEncoder()
        le_marka = LabelEncoder()
        le_kullanim = LabelEncoder()
        
        model_data['il_encoded'] = le_il.fit_transform(model_data['U Sig. İl'].fillna('Bilinmeyen').astype(str))
        model_data['marka_encoded'] = le_marka.fit_transform(model_data['MARKA'].fillna('Diğer').astype(str))
        model_data['kullanim_encoded'] = le_kullanim.fit_transform(model_data['KULLANIM ŞEKLİ'].fillna('Diğer').astype(str))
        
        col1, col2 = st.columns(2)
        
        with col1:
            model_type = st.selectbox("Model Tipi", [
                "Gamma GLM (Pure Premium)",
                "Poisson GLM (Frequency)",
                "Tweedie GLM (Aggregate Loss)"
            ])
        
        with col2:
            target_col = st.selectbox("Hedef Değişken", ['P Net Prim', 'P Brüt Prim'])
        
        st.subheader("Model Değişkenleri")
        
        degiskenler = st.multiselect(
            "Modele eklenecek değişkenler",
            ['il_encoded', 'marka_encoded', 'kullanim_encoded', 'MODEL YILI', 'BASAMAK'],
            default=['il_encoded', 'marka_encoded', 'MODEL YILI']
        )
        
        if st.button("🚀 GLM Modelini Çalıştır", type="primary"):
            try:
                model_df = model_data[degiskenler + [target_col]].dropna()
                
                # Sıfır ve negatif değerleri filtrele (Gamma için gerekli)
                model_df = model_df[model_df[target_col] > 0]
                
                if len(model_df) < 100:
                    st.error("Yeterli veri yok. En az 100 satır gerekli.")
                else:
                    X = model_df[degiskenler]
                    y = model_df[target_col]
                    
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.2, random_state=42
                    )
                    
                    if model_type == "Gamma GLM (Pure Premium)":
                        glm_model = sm.GLM(y_train, sm.add_constant(X_train), 
                                          family=sm.families.Gamma(link=sm.families.links.Log()))
                    elif model_type == "Poisson GLM (Frequency)":
                        glm_model = sm.GLM(y_train, sm.add_constant(X_train), 
                                          family=sm.families.Poisson())
                    else:
                        glm_model = sm.GLM(y_train, sm.add_constant(X_train), 
                                          family=sm.families.Tweedie(var_power=1.5))
                    
                    glm_results = glm_model.fit()
                    
                    st.success("✅ Model başarıyla oluşturuldu!")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("AIC", f"{glm_results.aic:.0f}")
                    with col2:
                        st.metric("BIC", f"{glm_results.bic:.0f}")
                    with col3:
                        st.metric("Log-Likelihood", f"{glm_results.llf:.0f}")
                    
                    st.subheader("📊 Model Katsayıları")
                    
                    coef_df = pd.DataFrame({
                        'Değişken': glm_results.params.index,
                        'Katsayı': glm_results.params.values,
                        'Std Hata': glm_results.bse.values,
                        'P-değeri': glm_results.pvalues.values
                    })
                    
                    st.dataframe(coef_df)
                    
                    st.subheader("🎯 Model Performansı")
                    
                    y_pred = glm_results.predict(sm.add_constant(X_test))
                    
                    mse = np.mean((y_test - y_pred) ** 2)
                    rmse = np.sqrt(mse)
                    mae = np.mean(np.abs(y_test - y_pred))
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("RMSE", f"{rmse:,.0f}")
                    with col2:
                        st.metric("MAE", f"{mae:,.0f}")
                    with col3:
                        ss_res = np.sum((y_test - y_pred) ** 2)
                        ss_tot = np.sum((y_test - y_test.mean()) ** 2)
                        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                        st.metric("R²", f"{r2:.3f}")
                    
                    fig = px.scatter(x=y_test, y=y_pred, 
                                   title="Gerçek vs Tahmin Değerleri",
                                   labels={'x': 'Gerçek Prim', 'y': 'Tahmin Prim'})
                    fig.add_trace(go.Scatter(x=[y_test.min(), y_test.max()], 
                                            y=[y_test.min(), y_test.max()],
                                            mode='lines', name='İdeal Çizgi',
                                            line=dict(color='red', dash='dash')))
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.subheader("📈 Değişken Önem Sıralaması")
                    
                    importance_df = pd.DataFrame({
                        'Değişken': coef_df['Değişken'][1:],
                        'Önem': np.abs(coef_df['Katsayı'][1:].values)
                    }).sort_values('Önem', ascending=False)
                    
                    fig2 = px.bar(importance_df, x='Önem', y='Değişken', 
                                 orientation='h', title="Değişken Önem Skorları")
                    st.plotly_chart(fig2, use_container_width=True)
                    
            except Exception as e:
                st.error(f"Model hatası: {e}")
    else:
        st.info("👈 Sol panelden üretim Excel dosyanızı yükleyin")

# TAB 6: AKTÜERYAL ANALİZ
with tab6:
    if df_uretim_raw is not None:
        df_uretim = df_uretim_raw.copy()
        
        st.header("📉 Aktüeryal Analizler")
        
        aktueryal_tip = st.selectbox("Analiz Tipi", [
            "Loss Development (Hasar Gelişimi)",
            "Frequency-Severity Analizi",
            "Pure Premium Hesaplama",
            "Credibility Analizi",
            "Risk Gruplaması"
        ])
        
        if aktueryal_tip == "Pure Premium Hesaplama":
            st.subheader("💰 Pure Premium (Saf Prim) Hesaplama")
            
            grup_degisken = st.selectbox("Gruplama Değişkeni", 
                                        ['U Sig. İl', 'MARKA', 'KULLANIM ŞEKLİ', 'MODEL YILI'])
            
            pure_premium = df_uretim.groupby(grup_degisken).agg({
                'P Net Prim': ['sum', 'mean', 'count']
            })
            pure_premium.columns = ['Toplam Prim', 'Ortalama Prim', 'Poliçe Sayısı']
            
            pure_premium['Risk Skoru'] = (pure_premium['Ortalama Prim'] / 
                                         pure_premium['Ortalama Prim'].mean() * 100).round(0)
            
            st.dataframe(pure_premium)
            
            fig = px.treemap(pure_premium.reset_index(), 
                           path=[grup_degisken], 
                           values='Toplam Prim',
                           color='Risk Skoru',
                           color_continuous_scale='RdYlGn_r',
                           title=f"{grup_degisken} Bazında Risk Haritası")
            st.plotly_chart(fig, use_container_width=True)
        
        elif aktueryal_tip == "Frequency-Severity Analizi":
            st.subheader("📊 Frequency-Severity Analizi")
            
            freq_data = df_uretim.groupby('U Sig. İl').agg({
                'Poliçe No': 'count',
                'P Net Prim': 'mean'
            }).rename(columns={'Poliçe No': 'Frequency', 'P Net Prim': 'Severity'})
            
            fig = px.scatter(freq_data, x='Frequency', y='Severity',
                           size='Frequency', hover_name=freq_data.index,
                           title="Frequency vs Severity Matrisi",
                           labels={'Frequency': 'Poliçe Sayısı (Frequency)',
                                  'Severity': 'Ortalama Prim (Severity)'})
            
            fig.add_hline(y=freq_data['Severity'].median(), 
                         line_dash="dash", line_color="gray")
            fig.add_vline(x=freq_data['Frequency'].median(), 
                         line_dash="dash", line_color="gray")
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("""
            ### 📍 Quadrant Analizi
            - **Sağ Üst:** Yüksek Frequency, Yüksek Severity → Kritik segment
            - **Sol Üst:** Düşük Frequency, Yüksek Severity → Büyük riskler
            - **Sağ Alt:** Yüksek Frequency, Düşük Severity → Küçük riskler
            - **Sol Alt:** Düşük Frequency, Düşük Severity → İdeal segment
            """)
        
        elif aktueryal_tip == "Risk Gruplaması":
            st.subheader("🎯 Risk Gruplaması ve Segmentasyon")
            
            df_uretim['Model_Risk'] = np.where(
                df_uretim['MODEL YILI'] < 2015, 1.5,
                np.where(df_uretim['MODEL YILI'] < 2020, 1.0, 0.8)
            )
            
            df_uretim['Cinsiyet_Risk'] = np.where(
                df_uretim['U Sig. Cinsiyet'] == 'E', 1.1, 1.0
            )
            
            mean_prim = df_uretim['P Net Prim'].mean()
            if mean_prim > 0:
                df_uretim['Toplam_Risk'] = (
                    df_uretim['Model_Risk'] * 
                    df_uretim['Cinsiyet_Risk'] * 
                    (df_uretim['P Net Prim'] / mean_prim)
                )
                
                df_uretim['Risk_Kategori'] = pd.cut(
                    df_uretim['Toplam_Risk'],
                    bins=[0, 0.8, 1.2, float('inf')],
                    labels=['Düşük Risk', 'Orta Risk', 'Yüksek Risk']
                )
                
                risk_dagilim = df_uretim['Risk_Kategori'].value_counts()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.pie(values=risk_dagilim.values, 
                               names=risk_dagilim.index,
                               title="Risk Kategorisi Dağılımı")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    risk_prim = df_uretim.groupby('Risk_Kategori')['P Net Prim'].mean()
                    fig2 = px.bar(x=risk_prim.index, y=risk_prim.values,
                                title="Risk Kategorisine Göre Ortalama Prim")
                    st.plotly_chart(fig2, use_container_width=True)
        
        elif aktueryal_tip == "Loss Development (Hasar Gelişimi)":
            st.info("Bu analiz için hasar verisi gereklidir.")
        
        elif aktueryal_tip == "Credibility Analizi":
            st.info("Credibility analizi yakında eklenecek.")
    else:
        st.info("👈 Sol panelden üretim Excel dosyanızı yükleyin")

# TAB 7: RİSK SKORLAMA
with tab7:
    if df_uretim_raw is not None:
        df_uretim = df_uretim_raw.copy()
        
        st.header("🎯 Otomatik Risk Skorlama Sistemi")
        
        st.markdown("""
        ### Çok Değişkenli Risk Skorlama
        Tüm faktörleri birlikte değerlendirerek her poliçe için risk skoru hesaplıyoruz.
        """)
        
        st.subheader("⚙️ Skorlama Parametreleri")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            model_yili_agirlik = st.slider("Model Yılı Ağırlığı", 0.0, 2.0, 1.0)
        
        with col2:
            il_agirlik = st.slider("İl Risk Ağırlığı", 0.0, 2.0, 1.0)
        
        with col3:
            marka_agirlik = st.slider("Marka Ağırlığı", 0.0, 2.0, 1.0)
        
        if st.button("📊 Risk Skorlarını Hesapla", type="primary"):
            try:
                il_risk = df_uretim.groupby('U Sig. İl')['P Net Prim'].mean()
                il_risk_norm = il_risk / il_risk.mean()
                
                marka_risk = df_uretim.groupby('MARKA')['P Net Prim'].mean()
                marka_risk_norm = marka_risk / marka_risk.mean()
                
                df_uretim['model_yili_skor'] = (2024 - df_uretim['MODEL YILI'].fillna(2020)) / 10 * model_yili_agirlik
                
                df_uretim['il_skor'] = df_uretim['U Sig. İl'].map(il_risk_norm).fillna(1) * il_agirlik
                
                df_uretim['marka_skor'] = df_uretim['MARKA'].map(marka_risk_norm).fillna(1) * marka_agirlik
                
                df_uretim['risk_skoru'] = (
                    df_uretim['model_yili_skor'].fillna(1) + 
                    df_uretim['il_skor'].fillna(1) + 
                    df_uretim['marka_skor'].fillna(1)
                ) / 3 * 100
                
                st.success("✅ Risk skorları başarıyla hesaplandı!")
                
                fig = px.histogram(df_uretim, x='risk_skoru', nbins=50,
                                title="Risk Skoru Dağılımı",
                                labels={'risk_skoru': 'Risk Skoru', 'count': 'Poliçe Sayısı'})
                fig.add_vline(x=100, line_dash="dash", line_color="red", 
                             annotation_text="Ortalama Risk")
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("🔴 En Riskli Segmentler")
                
                gosterilecek_kolonlar = ['Poliçe No', 'U Sig. İl', 'MARKA', 'MODEL YILI', 'P Net Prim', 'risk_skoru']
                mevcut_kolonlar = [k for k in gosterilecek_kolonlar if k in df_uretim.columns]
                
                riskli_segmentler = df_uretim.nlargest(10, 'risk_skoru')[mevcut_kolonlar]
                st.dataframe(riskli_segmentler)
                
                st.subheader("💡 Risk Bazlı Fiyat Önerileri")
                
                df_uretim['onerilen_prim'] = df_uretim['P Net Prim'] * (df_uretim['risk_skoru'] / 100)
                df_uretim['prim_farki'] = df_uretim['onerilen_prim'] - df_uretim['P Net Prim']
                
                ozet = pd.DataFrame({
                    'Metrik': ['Mevcut Toplam Prim', 'Önerilen Toplam Prim', 'Potansiyel Gelir Artışı'],
                    'Değer': [
                        f"₺{df_uretim['P Net Prim'].sum():,.0f}",
                        f"₺{df_uretim['onerilen_prim'].sum():,.0f}",
                        f"₺{df_uretim['prim_farki'].sum():,.0f}"
                    ]
                })
                
                st.table(ozet)
                
            except Exception as e:
                st.error(f"Hesaplama hatası: {e}")
    else:
        st.info("👈 Sol panelden üretim Excel dosyanızı yükleyin")

# Alt bilgi
st.markdown("---")
st.caption("Oto Branşı Analiz Sistemi - Aktüeryal Modül v2.0")
