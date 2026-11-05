import numpy as np
import pandas as pd


def calculate_wape(actual, predicted):
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)

    total = np.sum(np.abs(actual))

    if total == 0:
        return np.nan

    return np.sum(np.abs(actual - predicted)) / total * 100


def forecast_demand(df_sales, horizon=7):
    """
    Membandingkan Naive, Moving Average 7 Hari,
    dan Simple Exponential Smoothing.
    Memilih model dengan WAPE terendah per produk.
    """

    df = df_sales.copy()

    df["date"] = pd.to_datetime(df["date"])

    df["lost_demand_estimate"] = (
        pd.to_numeric(
            df["lost_demand_estimate"],
            errors="coerce"
        ).fillna(0)
    )

    df["demand"] = (
        pd.to_numeric(
            df["sold_quantity"],
            errors="coerce"
        ).fillna(0)
        + df["lost_demand_estimate"]
    )

    df = df.sort_values("date")

    forecast_results = []
    evaluation_results = []

    for product_id, group in df.groupby("product_id"):

        group = (
            group.groupby("date")["demand"]
            .sum()
            .sort_index()
        )

        if len(group) < 14:
            continue

        product_name = df.loc[
            df["product_id"] == product_id,
            "product_name"
        ].iloc[0]

        train = group.iloc[:-7]
        test = group.iloc[-7:]

        # Model Naive
        naive_value = train.iloc[-1]
        pred_naive = np.repeat(naive_value, len(test))

        # Moving Average 7 Hari
        ma_value = train.tail(7).mean()
        pred_ma = np.repeat(ma_value, len(test))

        # Simple Exponential Smoothing
        alpha = 0.3
        level = train.iloc[0]

        for value in train.iloc[1:]:
            level = alpha * value + (1 - alpha) * level

        pred_ses = np.repeat(level, len(test))

        models = {
            "Naive Forecast": pred_naive,
            "Moving Average 7 Hari": pred_ma,
            "Simple Exponential Smoothing": pred_ses
        }

        # Evaluasi model
        for model_name, prediction in models.items():
            evaluation_results.append({
                "product_id": product_id,
                "product_name": product_name,
                "model": model_name,
                "MAE": np.mean(
                    np.abs(test.values - prediction)
                ),
                "WAPE": calculate_wape(
                    test.values,
                    prediction
                )
            })

        # Pilih model dengan WAPE terendah
        evaluation = [
            item for item in evaluation_results
            if item["product_id"] == product_id
        ]

        best_model = min(
            evaluation,
            key=lambda x: (
                x["WAPE"] if not np.isnan(x["WAPE"])
                else float("inf")
            )
        )["model"]

        # Hitung ulang model menggunakan seluruh data
        if best_model == "Naive Forecast":
            final_value = group.iloc[-1]

        elif best_model == "Moving Average 7 Hari":
            final_value = group.tail(7).mean()

        else:
            final_value = group.iloc[0]

            for value in group.iloc[1:]:
                final_value = (
                    alpha * value
                    + (1 - alpha) * final_value
                )

        future_dates = pd.date_range(
            start=group.index.max() + pd.Timedelta(days=1),
            periods=horizon,
            freq="D"
        )

        for date in future_dates:
            forecast_results.append({
                "date": date,
                "product_id": product_id,
                "product_name": product_name,
                "model_terpilih": best_model,
                "prediksi_permintaan": max(
                    0, float(final_value)
                )
            })

    return (
        pd.DataFrame(forecast_results),
        pd.DataFrame(evaluation_results)
    )
