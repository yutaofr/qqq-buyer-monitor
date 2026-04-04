import pandas as pd


def align_target_inputs(price_series: pd.Series, stress_series: pd.Series) -> pd.DataFrame:
    frame = pd.concat(
        [
            pd.to_numeric(price_series, errors="coerce").rename("price"),
            pd.to_numeric(stress_series, errors="coerce").rename("stress"),
        ],
        axis=1,
        join="inner",
    )
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[~frame.index.isna()].sort_index()
    return frame.groupby(level=0).last()
