import pandas as pd
import numpy as np


def generate_recommendations(
    df_forecast,
    df_products,
    available_inventory=None
):
    """
    Membuat rekomendasi produksi berdasarkan forecast,
    safety stock, dan persediaan.
    """

    products = df_products.copy()
    forecast = df_forecast.copy()

    if available_inventory is None:
        inventory = pd.DataFrame({
            "product_id": products["product_id"],
            "available_inventory": 0
        })
        inventory_status = "Simulasi - stok belum tersedia"
    else:
        inventory = available_inventory.copy()
        inventory_status = "Berdasarkan data persediaan"

    result = forecast.merge(
        products[
            ["product_id", "product_name", "safety_stock"]
        ],
        on=["product_id", "product_name"],
        how="left"
    )

    result = result.merge(
        inventory[["product_id", "available_inventory"]],
        on="product_id",
        how="left"
    )

    result["safety_stock"] = (
        result["safety_stock"].fillna(0)
    )

    result["available_inventory"] = (
        result["available_inventory"].fillna(0)
    )

    result["recommended_production"] = np.ceil(
        (
            result["prediksi_permintaan"]
            + result["safety_stock"]
            - result["available_inventory"]
        ).clip(lower=0)
    ).astype(int)

    result["inventory_status"] = inventory_status

    return result
