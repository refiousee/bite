import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import date, timedelta

import database.db as db
from utils.forecasting import forecast_demand
from utils.recommendation import generate_recommendations


# =========================================================
# KONFIGURASI DAN INISIALISASI
# =========================================================
st.set_page_config(
    page_title="BITE | Bakery Business Companion",
    page_icon="🥐",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

BUSINESS = db.get_business()
if BUSINESS is None:
    st.error("Profil bisnis belum tersedia. Silakan buat profil bisnis di menu Pengaturan.")
    st.stop()

BUSINESS_ID = BUSINESS["business_id"]


# =========================================================
# TEMA VISUAL BITE
# =========================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700;800&display=swap');

    :root {
        --cream: #FBF5EC;
        --cream-dark: #F2E6D8;
        --peach: #F4DFD0;
        --terracotta: #A85F45;
        --terracotta-dark: #824B37;
        --brown: #624638;
        --muted: #927969;
        --sage: #879477;
        --gold: #D7A85B;
        --white: #FFFCF8;
    }

    .stApp {
        background: var(--cream);
        color: var(--brown);
        font-family: 'DM Sans', sans-serif;
    }

    [data-testid="stSidebar"] {
        background: #F1E5D8;
        border-right: 1px solid #E8D6C5;
    }

    [data-testid="stSidebar"] * {
        color: var(--brown);
    }

    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: var(--terracotta-dark) !important;
        letter-spacing: -0.4px;
    }

    h1 { font-size: 2.35rem !important; }
    h2 { font-size: 1.65rem !important; }
    h3 { font-size: 1.2rem !important; }

    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .brand {
        font-family: 'Playfair Display', serif;
        font-size: 2rem;
        font-weight: 800;
        color: var(--terracotta-dark);
        margin-bottom: 0;
    }

    .brand-sub {
        color: var(--muted);
        font-size: 0.86rem;
        margin-top: -5px;
    }

    .hero {
        background: linear-gradient(115deg, #F5E2D2 0%, #F9EDE1 68%, #F2DDCC 100%);
        border: 1px solid #EED9C7;
        border-radius: 24px;
        padding: 34px 38px;
        margin-bottom: 22px;
    }

    .hero-kicker {
        color: var(--terracotta);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 1.7px;
        text-transform: uppercase;
    }

    .hero-title {
        font-family: 'Playfair Display', serif;
        color: var(--terracotta-dark);
        font-size: 2.45rem;
        line-height: 1.2;
        font-weight: 800;
        margin: 8px 0;
    }

    .hero-copy {
        color: #765A49;
        font-size: 1rem;
        max-width: 720px;
        line-height: 1.7;
    }

    .metric-card {
        background: var(--white);
        border: 1px solid #EEDFD1;
        border-radius: 18px;
        padding: 18px 20px;
        min-height: 112px;
        box-shadow: 0 3px 12px rgba(100, 65, 45, 0.035);
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.82rem;
        font-weight: 600;
    }

    .metric-value {
        color: var(--terracotta-dark);
        font-family: 'Playfair Display', serif;
        font-size: 1.75rem;
        font-weight: 700;
        margin-top: 7px;
    }

    .metric-note {
        color: #A18A79;
        font-size: 0.74rem;
        margin-top: 2px;
    }

    .soft-card {
        background: var(--white);
        border: 1px solid #EEDFD1;
        border-radius: 18px;
        padding: 20px 22px;
    }

    .section-note {
        color: var(--muted);
        font-size: 0.9rem;
    }

    div.stButton > button, div.stFormSubmitButton > button {
        background: var(--terracotta);
        color: white;
        border: 0;
        border-radius: 11px;
        padding: 0.55rem 1.1rem;
        font-weight: 600;
    }

    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        background: var(--terracotta-dark);
        color: white;
        border: 0;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background: #F4E8DC;
        border-radius: 10px 10px 0 0;
        color: var(--brown);
        padding: 9px 16px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #EEDFD1;
        border-radius: 12px;
        overflow: hidden;
    }

    .footer {
        color: #A58D7B;
        font-size: 0.78rem;
        border-top: 1px solid #E7D8CA;
        padding-top: 18px;
        margin-top: 42px;
    }

    @media (max-width: 700px) {
        .hero { padding: 24px; }
        .hero-title { font-size: 1.8rem; }
        .block-container { padding-left: 1rem; padding-right: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# FUNGSI BANTU
# =========================================================
def rupiah(value):
    try:
        return "Rp{:,.0f}".format(float(value)).replace(",", ".")
    except (TypeError, ValueError):
        return "Rp0"


def load_products():
    return pd.DataFrame(db.get_products(BUSINESS_ID))


def load_sales():
    sales = pd.DataFrame(db.get_sales(BUSINESS_ID))
    products = load_products()

    if sales.empty:
        return sales

    if not products.empty:
        sales = sales.merge(
            products[["product_id", "product_name", "product_category"]],
            on="product_id",
            how="left",
        )
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales["sold_quantity"] = pd.to_numeric(sales["sold_quantity"], errors="coerce").fillna(0)
    sales["lost_demand_estimate"] = pd.to_numeric(
        sales["lost_demand_estimate"], errors="coerce"
    ).fillna(0)
    sales["demand"] = sales["sold_quantity"] + sales["lost_demand_estimate"]
    sales["revenue"] = sales["sold_quantity"] * pd.to_numeric(
        sales["selling_price"], errors="coerce"
    ).fillna(0)
    return sales


def load_production():
    production = pd.DataFrame(db.get_production(BUSINESS_ID))
    if not production.empty:
        production["date"] = pd.to_datetime(production["date"], errors="coerce")
    return production


def latest_inventory(products):
    """Mengambil sisa persediaan terakhir dari riwayat produksi."""
    production = load_production()
    if products.empty:
        return pd.DataFrame(columns=["product_id", "available_inventory"])

    if production.empty:
        return pd.DataFrame({
            "product_id": products["product_id"],
            "available_inventory": 0,
        })

    latest = (
        production.sort_values("date")
        .groupby("product_id", as_index=False)
        .tail(1)[["product_id", "leftover_quantity"]]
        .rename(columns={"leftover_quantity": "available_inventory"})
    )
    return products[["product_id"]].merge(latest, on="product_id", how="left").fillna(
        {"available_inventory": 0}
    )


def get_forecast(sales):
    if sales.empty:
        return pd.DataFrame(), pd.DataFrame()

    # forecasting.py membutuhkan kolom product_name dan minimal 14 tanggal
    required = {"date", "product_id", "product_name", "sold_quantity", "lost_demand_estimate"}
    if not required.issubset(sales.columns):
        return pd.DataFrame(), pd.DataFrame()

    forecast, evaluation = forecast_demand(
        sales[list(required)].copy(),
        horizon=7,
    )
    return forecast, evaluation


def record_sales(product_id, sales_date, quantity, price, stockout, lost_demand):
    db.add_sales(
        business_id=BUSINESS_ID,
        product_id=int(product_id),
        date=sales_date.strftime("%Y-%m-%d"),
        sold_quantity=int(quantity),
        selling_price=float(price),
        stockout_status=int(stockout),
        lost_demand_estimate=int(lost_demand),
    )


def save_uploaded_sales(data, products):
    required = {"date", "product_name", "sold_quantity"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(
            "Kolom wajib belum lengkap: " + ", ".join(sorted(missing))
        )

    product_lookup = {
        str(row["product_name"]).strip().lower(): row
        for _, row in products.iterrows()
    }

    saved = 0
    skipped = []
    for index, row in data.iterrows():
        name = str(row["product_name"]).strip().lower()
        if name not in product_lookup:
            skipped.append(f"Baris {index + 2}: produk '{row['product_name']}' tidak ditemukan")
            continue

        parsed_date = pd.to_datetime(row["date"], errors="coerce")
        if pd.isna(parsed_date):
            skipped.append(f"Baris {index + 2}: tanggal tidak valid")
            continue

        try:
            quantity = int(row["sold_quantity"])
            price = float(row.get("selling_price", product_lookup[name]["selling_price"]))
            stockout = int(row.get("stockout_status", 0) or 0)
            lost = int(row.get("lost_demand_estimate", 0) or 0)
            if quantity < 0 or price < 0 or lost < 0 or stockout not in (0, 1):
                raise ValueError("nilai tidak sesuai")
            record_sales(
                product_lookup[name]["product_id"],
                parsed_date.date(),
                quantity,
                price,
                stockout,
                lost,
            )
            saved += 1
        except sqlite3.IntegrityError:
            skipped.append(
                f"Baris {index + 2}: data produk dan tanggal sudah ada"
            )
        except (TypeError, ValueError):
            skipped.append(f"Baris {index + 2}: format angka tidak valid")

    return saved, skipped


def metric_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, description, emoji="🥐"):
    st.markdown(f"## {emoji} {title}")
    st.markdown(f'<p class="section-note">{description}</p>', unsafe_allow_html=True)


# =========================================================
# DATA AWAL
# =========================================================
products = load_products()
sales = load_sales()
production = load_production()

with st.sidebar:
    st.markdown('<div class="brand">🥐 BITE.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-sub">Bakery Business Companion</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("MENU UTAMA")

    menu = st.radio(
        "Navigasi",
        [
            "Beranda",
            "Data Penjualan",
            "Produk",
            "Prediksi Permintaan",
            "Rekomendasi Produksi",
            "Pemantauan Persediaan",
            "Analisis Usaha",
            "Laporan",
            "Pengaturan",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"Bisnis aktif: {BUSINESS['business_name']}")
    st.caption("Kenali Permintaan, Siapkan Produksi.")


# =========================================================
# BERANDA
# =========================================================
if menu == "Beranda":
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Your daily bakery companion</div>
            <div class="hero-title">Selamat datang di BITE! 🥐</div>
            <div class="hero-copy">
                Kenali permintaan, siapkan produksi, dan kurangi produk tersisa.
                BITE membantu usaha bakery mengambil keputusan produksi
                berdasarkan riwayat penjualan.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_revenue = sales["revenue"].sum() if not sales.empty else 0
    total_sold = sales["sold_quantity"].sum() if not sales.empty else 0
    total_stockout = sales["stockout_status"].sum() if not sales.empty else 0
    total_products = len(products)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Penjualan", rupiah(total_revenue), "Akumulasi dari data tersimpan")
    with c2:
        metric_card("Produk Terjual", f"{total_sold:,.0f}".replace(",", "."), "Dalam satuan produk")
    with c3:
        metric_card("Kejadian Produk Habis", f"{total_stockout:,.0f}".replace(",", "."), "Berdasarkan catatan penjualan")
    with c4:
        metric_card("Produk Terdaftar", str(total_products), "Produk aktif dalam bisnis")

    st.write("")
    left, right = st.columns([1.5, 1])

    with left:
        st.markdown("### 📈 Ringkasan Penjualan")
        if not sales.empty:
            daily = sales.groupby("date", as_index=False)["sold_quantity"].sum()
            daily = daily.set_index("date")
            st.area_chart(daily, y="sold_quantity", color="#B66A4B")
        else:
            st.info("Belum ada data penjualan. Tambahkan data melalui menu Data Penjualan.")

    with right:
        st.markdown("### 🍞 Produk Terlaris")
        if not sales.empty:
            best = (
                sales.groupby("product_name")["sold_quantity"]
                .sum().sort_values(ascending=False)
            )
            st.bar_chart(best, color="#C28B62")
        else:
            st.info("Grafik produk akan muncul setelah data penjualan tersedia.")

    st.markdown("### ✨ Mulai dari sini")
    a, b, c = st.columns(3)
    with a:
        st.markdown('<div class="soft-card"><h3>🧾 Catat Penjualan</h3><p>Masukkan transaksi harian atau unggah file penjualan.</p></div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="soft-card"><h3>🔮 Lihat Prediksi</h3><p>Bandingkan model dan lihat perkiraan permintaan tujuh hari.</p></div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="soft-card"><h3>🥐 Siapkan Produksi</h3><p>Gunakan rekomendasi jumlah produksi berdasarkan stok.</p></div>', unsafe_allow_html=True)


# =========================================================
# DATA PENJUALAN
# =========================================================
elif menu == "Data Penjualan":
    page_header(
        "Data Penjualan",
        "Catat transaksi harian atau unggah file Excel/CSV. Data yang disimpan akan digunakan untuk prediksi.",
        "🧾",
    )

    if products.empty:
        st.warning("Belum ada produk. Tambahkan produk terlebih dahulu melalui menu Produk.")
        st.stop()

    tab_manual, tab_upload, tab_history = st.tabs(
        ["Input Manual", "Upload Excel / CSV", "Riwayat Penjualan"]
    )

    with tab_manual:
        st.markdown("### Tambahkan transaksi")
        with st.form("manual_sales_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            product_options = {
                f"{row['product_name']} (ID {row['product_id']})": row
                for _, row in products.iterrows()
            }
            with col1:
                selected_product = st.selectbox("Pilih produk", list(product_options.keys()))
                sales_date = st.date_input("Tanggal penjualan", value=date.today())
                quantity = st.number_input("Jumlah terjual", min_value=0, step=1, value=0)
            with col2:
                default_price = float(product_options[selected_product]["selling_price"])
                price = st.number_input("Harga jual per unit (Rp)", min_value=0.0, value=default_price, step=1000.0)
                stockout = st.checkbox("Produk sempat habis?")
                lost = st.number_input(
                    "Estimasi permintaan tidak terpenuhi (unit)",
                    min_value=0,
                    step=1,
                    value=0,
                    help="Isi 0 jika tidak ada estimasi permintaan yang tidak terpenuhi.",
                )

            submitted = st.form_submit_button("💾 Simpan Penjualan", use_container_width=True)
            if submitted:
                try:
                    record_sales(
                        product_options[selected_product]["product_id"],
                        sales_date,
                        quantity,
                        price,
                        stockout,
                        lost,
                    )
                    st.success("Data penjualan berhasil disimpan ke database.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Penjualan untuk produk dan tanggal tersebut sudah tercatat. Gunakan tanggal berbeda atau periksa riwayat.")

    with tab_upload:
        st.markdown("### Unggah data penjualan")
        st.caption("Kolom wajib: date, product_name, sold_quantity. Kolom opsional: selling_price, stockout_status, lost_demand_estimate.")
        uploaded = st.file_uploader(
            "Pilih file Excel atau CSV",
            type=["xlsx", "xls", "csv"],
            key="sales_uploader",
        )

        if uploaded is not None:
            try:
                if uploaded.name.lower().endswith(".csv"):
                    upload_df = pd.read_csv(uploaded)
                else:
                    upload_df = pd.read_excel(uploaded)

                st.markdown("**Pratinjau data**")
                st.dataframe(upload_df.head(10), use_container_width=True)

                if st.button("Simpan data ke database", type="primary"):
                    saved, skipped = save_uploaded_sales(upload_df, products)
                    st.success(f"{saved} baris berhasil disimpan.")
                    if skipped:
                        st.warning(f"{len(skipped)} baris dilewati.")
                        st.write(skipped[:20])
                    st.rerun()
            except Exception as error:
                st.error(f"File tidak dapat dibaca: {error}")

        template = pd.DataFrame(
            columns=[
                "date", "product_name", "sold_quantity",
                "selling_price", "stockout_status", "lost_demand_estimate",
            ]
        )
        st.download_button(
            "⬇️ Unduh template CSV",
            data=template.to_csv(index=False).encode("utf-8"),
            file_name="Template_Penjualan_BITE.csv",
            mime="text/csv",
        )

    with tab_history:
        current_sales = load_sales()
        if current_sales.empty:
            st.info("Belum ada riwayat penjualan.")
        else:
            display = current_sales[
                [
                    "date", "product_name", "sold_quantity",
                    "lost_demand_estimate", "stockout_status",
                    "selling_price", "revenue",
                ]
            ].copy()
            display["date"] = display["date"].dt.strftime("%Y-%m-%d")
            display = display.rename(
                columns={
                    "date": "Tanggal",
                    "product_name": "Produk",
                    "sold_quantity": "Jumlah Terjual",
                    "lost_demand_estimate": "Estimasi Permintaan Tidak Terpenuhi",
                    "stockout_status": "Produk Habis (1=Ya)",
                    "selling_price": "Harga Jual",
                    "revenue": "Pendapatan",
                }
            )
            st.dataframe(display, use_container_width=True, hide_index=True)
            st.caption(f"Total {len(display)} catatan penjualan.")


# =========================================================
# PRODUK
# =========================================================
elif menu == "Produk":
    page_header(
        "Kelola Produk",
        "Tambahkan produk yang dijual oleh bisnis. Produk akan tersedia pada input penjualan dan perhitungan rekomendasi.",
        "🍰",
    )

    tab_add, tab_list = st.tabs(["Tambah Produk", "Daftar Produk"])

    with tab_add:
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                product_name = st.text_input("Nama produk", placeholder="Contoh: Croissant")
                category = st.selectbox(
                    "Kategori",
                    ["Bakery", "Pastry", "Dessert", "Roti", "Cake", "Lainnya"],
                )
                selling_price = st.number_input(
                    "Harga jual (Rp)", min_value=0.0, step=1000.0, value=15000.0
                )
            with col2:
                shelf_life = st.number_input(
                    "Masa simpan (hari)", min_value=1, max_value=365, value=2, step=1
                )
                minimum_stock = st.number_input(
                    "Batas minimum stok", min_value=0, value=5, step=1
                )
                safety_stock = st.number_input(
                    "Safety stock", min_value=0, value=3, step=1
                )

            save_product = st.form_submit_button("＋ Tambahkan Produk", use_container_width=True)
            if save_product:
                if not product_name.strip():
                    st.error("Nama produk wajib diisi.")
                elif selling_price <= 0:
                    st.error("Harga jual harus lebih dari 0.")
                else:
                    try:
                        db.add_product(
                            BUSINESS_ID,
                            product_name.strip(),
                            category,
                            selling_price,
                            int(shelf_life),
                            int(minimum_stock),
                            int(safety_stock),
                        )
                        st.success(f"Produk {product_name} berhasil ditambahkan.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Nama produk tersebut sudah terdaftar.")

    with tab_list:
        current_products = load_products()
        if current_products.empty:
            st.info("Belum ada produk terdaftar.")
        else:
            show_products = current_products[
                [
                    "product_id", "product_name", "product_category",
                    "selling_price", "shelf_life_days",
                    "minimum_stock", "safety_stock",
                ]
            ].rename(
                columns={
                    "product_id": "ID",
                    "product_name": "Nama Produk",
                    "product_category": "Kategori",
                    "selling_price": "Harga Jual",
                    "shelf_life_days": "Masa Simpan (hari)",
                    "minimum_stock": "Minimum Stok",
                    "safety_stock": "Safety Stock",
                }
            )
            st.dataframe(show_products, use_container_width=True, hide_index=True)


# =========================================================
# PREDIKSI PERMINTAAN
# =========================================================
elif menu == "Prediksi Permintaan":
    page_header(
        "Prediksi Permintaan",
        "Perkiraan permintaan tujuh hari ke depan berdasarkan riwayat penjualan dan estimasi permintaan yang tidak terpenuhi.",
        "🔮",
    )

    if sales.empty:
        st.warning("Belum ada data penjualan untuk membuat prediksi.")
        st.stop()

    with st.spinner("Menghitung dan membandingkan model prediksi..."):
        forecast, evaluation = get_forecast(sales)

    if forecast.empty:
        st.warning(
            "Prediksi belum dapat dibuat. Setiap produk memerlukan minimal "
            "14 tanggal pengamatan penjualan. Tambahkan data penjualan terlebih dahulu."
        )
        st.stop()

    product_names = sorted(forecast["product_name"].dropna().unique().tolist())
    selected_name = st.selectbox("Pilih produk", product_names)
    selected_forecast = forecast[forecast["product_name"] == selected_name].copy()
    selected_evaluation = evaluation[
        evaluation["product_name"] == selected_name
    ].sort_values("WAPE")

    best_model = selected_forecast["model_terpilih"].iloc[0]
    average_forecast = selected_forecast["prediksi_permintaan"].mean()

    c1, c2 = st.columns(2)
    with c1:
        metric_card("Model Terpilih", best_model, "Model dengan WAPE terendah")
    with c2:
        metric_card(
            "Rata-rata Prediksi Harian",
            f"{average_forecast:.1f} unit",
            "Rata-rata selama 7 hari",
        )

    st.markdown("### Grafik prediksi")
    chart_df = selected_forecast.set_index("date")[["prediksi_permintaan"]]
    st.line_chart(chart_df, color="#B66A4B")

    st.markdown("### Rincian prediksi 7 hari")
    forecast_display = selected_forecast[
        ["date", "prediksi_permintaan", "model_terpilih"]
    ].copy()
    forecast_display["date"] = forecast_display["date"].dt.strftime("%d %b %Y")
    forecast_display = forecast_display.rename(
        columns={
            "date": "Tanggal",
            "prediksi_permintaan": "Perkiraan Permintaan (unit)",
            "model_terpilih": "Model",
        }
    )
    st.dataframe(forecast_display, use_container_width=True, hide_index=True)

    st.markdown("### Evaluasi model")
    evaluation_display = selected_evaluation.rename(
        columns={"model": "Model", "MAE": "MAE", "WAPE": "WAPE (%)"}
    )
    st.dataframe(
        evaluation_display[["Model", "MAE", "WAPE (%)"]].round(3),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Model dipilih berdasarkan nilai WAPE terendah pada data pengujian.")


# =========================================================
# REKOMENDASI PRODUKSI
# =========================================================
elif menu == "Rekomendasi Produksi":
    page_header(
        "Rekomendasi Produksi",
        "Hitung jumlah produksi untuk hari berikutnya dengan mempertimbangkan prediksi permintaan, persediaan, dan safety stock.",
        "🥐",
    )

    if products.empty or sales.empty:
        st.warning("Tambahkan produk dan riwayat penjualan terlebih dahulu.")
        st.stop()

    forecast, evaluation = get_forecast(sales)
    if forecast.empty:
        st.warning("Prediksi belum tersedia. Pastikan setiap produk memiliki minimal 14 tanggal data penjualan.")
        st.stop()

    first_date = forecast["date"].min()
    first_day_forecast = forecast[forecast["date"] == first_date].copy()
    inventory_latest = latest_inventory(products)

    st.markdown(f"### Persediaan untuk tanggal {first_date.strftime('%d %B %Y')}")
    st.caption(
        "Nilai awal diambil dari sisa persediaan terakhir pada menu Pemantauan Persediaan. "
        "Kamu dapat menyesuaikannya sebelum menghitung rekomendasi."
    )

    inventory_values = []
    with st.form("recommendation_form"):
        for _, product in products.iterrows():
            found = inventory_latest[
                inventory_latest["product_id"] == product["product_id"]
            ]
            default_stock = int(found["available_inventory"].iloc[0]) if not found.empty else 0
            stock = st.number_input(
                f"Persediaan {product['product_name']} (unit)",
                min_value=0,
                value=max(0, default_stock),
                step=1,
                key=f"rec_stock_{product['product_id']}",
            )
            inventory_values.append(
                {
                    "product_id": int(product["product_id"]),
                    "available_inventory": int(stock),
                }
            )

        calculate = st.form_submit_button("✨ Hitung Rekomendasi Produksi", use_container_width=True)

    if calculate:
        inventory_df = pd.DataFrame(inventory_values)
        recommendations = generate_recommendations(
            first_day_forecast,
            products,
            inventory_df,
        )

        st.markdown("### Hasil rekomendasi")
        for _, row in recommendations.iterrows():
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns(4)
                col1.markdown(f"**{row['product_name']}**")
                col2.metric("Prediksi permintaan", f"{row['prediksi_permintaan']:.1f} unit")
                col3.metric("Persediaan", f"{int(row['available_inventory'])} unit")
                col4.metric("Produksi disarankan", f"{int(row['recommended_production'])} unit")

        export_recommendations = recommendations[
            [
                "date", "product_name", "prediksi_permintaan",
                "available_inventory", "safety_stock",
                "recommended_production",
            ]
        ].copy()
        st.download_button(
            "⬇️ Unduh rekomendasi (CSV)",
            data=export_recommendations.to_csv(index=False).encode("utf-8"),
            file_name="Rekomendasi_Produksi_BITE.csv",
            mime="text/csv",
        )


# =========================================================
# PEMANTAUAN PERSEDIAAN
# =========================================================
elif menu == "Pemantauan Persediaan":
    page_header(
        "Pemantauan Persediaan",
        "Catat persediaan awal, jumlah produksi, dan produk tersisa. Sisa terakhir akan digunakan sebagai acuan persediaan rekomendasi.",
        "📦",
    )

    if products.empty:
        st.warning("Tambahkan produk terlebih dahulu melalui menu Produk.")
        st.stop()

    with st.form("production_form", clear_on_submit=True):
        st.markdown("### Catat aktivitas produksi")
        col1, col2 = st.columns(2)
        with col1:
            production_product = st.selectbox(
                "Pilih produk",
                products["product_name"].tolist(),
            )
            production_date = st.date_input("Tanggal pencatatan", value=date.today())
        with col2:
            opening = st.number_input("Persediaan awal (unit)", min_value=0, value=0, step=1)
            produced = st.number_input("Jumlah diproduksi (unit)", min_value=0, value=0, step=1)
            leftover = st.number_input("Produk tersisa di akhir hari (unit)", min_value=0, value=0, step=1)

        save_production = st.form_submit_button("💾 Simpan Catatan Produksi", use_container_width=True)
        if save_production:
            selected_product_row = products[
                products["product_name"] == production_product
            ].iloc[0]
            if leftover > opening + produced:
                st.error("Produk tersisa tidak boleh melebihi persediaan awal ditambah jumlah produksi.")
            else:
                try:
                    db.add_production(
                        BUSINESS_ID,
                        int(selected_product_row["product_id"]),
                        production_date.strftime("%Y-%m-%d"),
                        int(opening),
                        int(produced),
                        int(leftover),
                    )
                    st.success("Catatan produksi berhasil disimpan.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Catatan untuk produk dan tanggal tersebut sudah ada.")

    st.markdown("### Posisi persediaan terakhir")
    inventory = latest_inventory(products).merge(
        products[["product_id", "product_name", "minimum_stock"]],
        on="product_id",
        how="left",
    )
    if not production.empty:
        latest_dates = (
            production.sort_values("date")
            .groupby("product_id")["date"].max()
            .reset_index()
        )
        inventory = inventory.merge(latest_dates, on="product_id", how="left")
    else:
        inventory["date"] = pd.NaT

    inventory["Status"] = np.where(
        inventory["available_inventory"] <= 0,
        "Habis",
        np.where(
            inventory["available_inventory"] <= inventory["minimum_stock"],
            "Stok menipis",
            "Tersedia",
        ),
    )
    inventory_display = inventory[
        ["product_name", "available_inventory", "minimum_stock", "date", "Status"]
    ].rename(
        columns={
            "product_name": "Produk",
            "available_inventory": "Persediaan Tersisa",
            "minimum_stock": "Batas Minimum",
            "date": "Tanggal Catatan",
        }
    )
    st.dataframe(inventory_display, use_container_width=True, hide_index=True)

    st.markdown("### Riwayat produksi")
    current_production = load_production()
    if current_production.empty:
        st.info("Belum ada riwayat produksi.")
    else:
        production_display = current_production.merge(
            products[["product_id", "product_name"]],
            on="product_id",
            how="left",
        )
        production_display = production_display[
            [
                "date", "product_name", "opening_inventory",
                "production_quantity", "leftover_quantity",
            ]
        ].rename(
            columns={
                "date": "Tanggal",
                "product_name": "Produk",
                "opening_inventory": "Persediaan Awal",
                "production_quantity": "Jumlah Produksi",
                "leftover_quantity": "Produk Tersisa",
            }
        )
        st.dataframe(production_display, use_container_width=True, hide_index=True)


# =========================================================
# ANALISIS USAHA
# =========================================================
elif menu == "Analisis Usaha":
    page_header(
        "Analisis Usaha",
        "Pantau produk terlaris, permintaan yang belum terpenuhi, dan produk tersisa berdasarkan data yang tercatat.",
        "📊",
    )

    if sales.empty:
        st.info("Analisis akan tersedia setelah data penjualan dimasukkan.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Penjualan per produk")
        by_product = sales.groupby("product_name")["sold_quantity"].sum().sort_values(ascending=False)
        st.bar_chart(by_product, color="#B66A4B")

    with col2:
        st.markdown("### Estimasi permintaan tidak terpenuhi")
        lost = sales.groupby("product_name")["lost_demand_estimate"].sum().sort_values(ascending=False)
        st.bar_chart(lost, color="#D7A85B")

    st.markdown("### Ringkasan kejadian produk habis")
    stockout = sales[sales["stockout_status"] == 1]
    if stockout.empty:
        st.success("Belum ada kejadian produk habis yang tercatat.")
    else:
        st.dataframe(
            stockout[
                ["date", "product_name", "sold_quantity", "lost_demand_estimate"]
            ].rename(
                columns={
                    "date": "Tanggal",
                    "product_name": "Produk",
                    "sold_quantity": "Jumlah Terjual",
                    "lost_demand_estimate": "Estimasi Permintaan Tidak Terpenuhi",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Produk tersisa")
    if production.empty:
        st.info("Belum ada catatan produksi. Isi menu Pemantauan Persediaan untuk mulai mencatat produk tersisa.")
    else:
        leftover_summary = production.merge(
            products[["product_id", "product_name"]],
            on="product_id",
            how="left",
        )
        st.bar_chart(
            leftover_summary.groupby("product_name")["leftover_quantity"].sum(),
            color="#879477",
        )
        st.caption("Jumlah produk tersisa merupakan akumulasi catatan produksi yang tersimpan.")


# =========================================================
# LAPORAN
# =========================================================
elif menu == "Laporan":
    page_header(
        "Laporan Usaha",
        "Unduh data penjualan, produksi, dan hasil prediksi untuk dokumentasi usaha.",
        "📄",
    )

    current_sales = load_sales()
    current_production = load_production()

    st.markdown("### Unduh data")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Riwayat penjualan**")
        if current_sales.empty:
            st.info("Belum ada data penjualan.")
        else:
            sales_export = current_sales.copy()
            sales_export["date"] = sales_export["date"].dt.strftime("%Y-%m-%d")
            st.download_button(
                "⬇️ Unduh penjualan CSV",
                data=sales_export.to_csv(index=False).encode("utf-8"),
                file_name="Data_Penjualan_BITE.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with c2:
        st.markdown("**Riwayat produksi**")
        if current_production.empty:
            st.info("Belum ada data produksi.")
        else:
            st.download_button(
                "⬇️ Unduh produksi CSV",
                data=current_production.to_csv(index=False).encode("utf-8"),
                file_name="Data_Produksi_BITE.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.markdown("**Hasil prediksi**")
    if not current_sales.empty:
        forecast, evaluation = get_forecast(current_sales)
        if not forecast.empty:
            forecast_export = forecast.copy()
            forecast_export["date"] = forecast_export["date"].dt.strftime("%Y-%m-%d")
            st.download_button(
                "⬇️ Unduh prediksi 7 hari CSV",
                data=forecast_export.to_csv(index=False).encode("utf-8"),
                file_name="Prediksi_Permintaan_BITE.csv",
                mime="text/csv",
            )
        else:
            st.info("Prediksi belum tersedia. Setiap produk membutuhkan minimal 14 tanggal pengamatan.")
    else:
        st.info("Masukkan data penjualan terlebih dahulu untuk menghasilkan prediksi.")


# =========================================================
# PENGATURAN
# =========================================================
elif menu == "Pengaturan":
    page_header(
        "Pengaturan Bisnis",
        "Kelola informasi dasar bisnis yang digunakan dalam aplikasi BITE.",
        "⚙️",
    )

    with st.form("business_settings_form"):
        business_name = st.text_input(
            "Nama bisnis",
            value=BUSINESS.get("business_name", ""),
        )
        categories = [
            "Bakery & Pastry", "Bakery", "Pastry", "Dessert",
            "Coffee Shop", "F&B Lainnya",
        ]
        current_category = BUSINESS.get("business_category") or "Bakery & Pastry"
        category_index = categories.index(current_category) if current_category in categories else 0
        business_category = st.selectbox(
            "Kategori bisnis",
            categories,
            index=category_index,
        )

        c1, c2 = st.columns(2)
        with c1:
            opening_time = st.text_input(
                "Jam buka (HH:MM)",
                value=BUSINESS.get("opening_time") or "07:00",
            )
            minimum_stock = st.number_input(
                "Default minimum stok",
                min_value=0,
                value=int(BUSINESS.get("default_minimum_stock") or 5),
            )
        with c2:
            closing_time = st.text_input(
                "Jam tutup (HH:MM)",
                value=BUSINESS.get("closing_time") or "17:00",
            )
            safety_stock = st.number_input(
                "Default safety stock",
                min_value=0,
                value=int(BUSINESS.get("default_safety_stock") or 3),
            )

        save_settings = st.form_submit_button("Simpan Pengaturan", use_container_width=True)
        if save_settings:
            if not business_name.strip():
                st.error("Nama bisnis tidak boleh kosong.")
            else:
                db.update_business(
                    BUSINESS_ID,
                    business_name=business_name.strip(),
                    business_category=business_category,
                    opening_time=opening_time,
                    closing_time=closing_time,
                    default_minimum_stock=int(minimum_stock),
                    default_safety_stock=int(safety_stock),
                )
                st.success("Pengaturan bisnis berhasil diperbarui.")
                st.rerun()

    st.markdown("### Informasi aplikasi")
    st.markdown(
        """
        <div class="soft-card">
            <h3>🥐 BITE — Business Intelligence for Tomorrow's Estimation</h3>
            <p>
                BITE membantu usaha makanan dan minuman memperkirakan permintaan,
                menyusun rekomendasi produksi, serta memantau persediaan
                berdasarkan riwayat data usaha.
            </p>
            <p><b>Catatan:</b> kualitas prediksi bergantung pada kelengkapan dan
            konsistensi data penjualan yang dimasukkan.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    '<div class="footer">BITE © 2026 · Business Intelligence for Tomorrow’s Estimation · Made for better bakery decisions 🥐</div>',
    unsafe_allow_html=True,
)
