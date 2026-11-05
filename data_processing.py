import pandas as pd

KOLOM_PRODUKSI = [
    "date",
    "product_name",
    "opening_inventory",
    "production_quantity",
    "leftover_quantity"
]


def validate_production_excel(df, products):
    """
    Memvalidasi struktur dan isi Excel riwayat produksi.
    Tidak menyimpan data ke database.
    """

    errors = []

    # 1. Periksa kolom
    kolom_hilang = [
        kolom for kolom in KOLOM_PRODUKSI
        if kolom not in df.columns
    ]

    if kolom_hilang:
        errors.append(
            f"Kolom belum tersedia: {kolom_hilang}"
        )
        return False, errors, None

    # 2. Ambil kolom yang dibutuhkan
    df = df[KOLOM_PRODUKSI].copy()

    # 3. Periksa data kosong
    if df.isnull().any().any():
        errors.append(
            "Terdapat sel kosong pada data produksi."
        )

    # 4. Validasi tanggal
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    if df["date"].isnull().any():
        errors.append(
            "Terdapat format tanggal yang tidak valid."
        )

    # 5. Validasi nama produk
    nama_produk_tersedia = {
        str(p["product_name"]).strip().lower()
        for p in products
    }

    nama_produk_file = (
        df["product_name"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    produk_tidak_dikenal = sorted(
        set(nama_produk_file) - nama_produk_tersedia
    )

    if produk_tidak_dikenal:
        errors.append(
            f"Produk tidak terdaftar: {produk_tidak_dikenal}"
        )

    # 6. Validasi angka
    kolom_angka = [
        "opening_inventory",
        "production_quantity",
        "leftover_quantity"
    ]

    for kolom in kolom_angka:
        nilai = pd.to_numeric(
            df[kolom],
            errors="coerce"
        )

        if nilai.isnull().any():
            errors.append(
                f"Kolom {kolom} harus berisi angka."
            )
            continue

        if (nilai < 0).any():
            errors.append(
                f"Kolom {kolom} tidak boleh negatif."
            )

        if (nilai % 1 != 0).any():
            errors.append(
                f"Kolom {kolom} harus berupa bilangan bulat."
            )

        df[kolom] = nilai

    # 7. Periksa duplikasi tanggal dan produk
    df["product_name"] = (
        df["product_name"].astype(str).str.strip()
    )

    duplikat = df.duplicated(
        subset=["date", "product_name"],
        keep=False
    )

    if duplikat.any():
        errors.append(
            "Terdapat catatan ganda untuk produk "
            "pada tanggal yang sama."
        )

    return len(errors) == 0, errors, df
