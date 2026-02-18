import pandas as pd
import pandas_ta as ta


class TechnicalAnalysis:

    @staticmethod
    def add_rsi(df: pd.DataFrame, length: int = 14, column_name: str = 'rsi'):
        rsi = df.ta.rsi(length=length)
        if rsi is not None:
            df[column_name] = rsi
        return df

    @staticmethod
    def add_ema(df: pd.DataFrame, length: int = 200, source: str = 'close', column_name: str = 'ema'):
        ema = df.ta.ema(length=length, close=df[source])
        if ema is not None:
            df[column_name] = ema
        return df

    @staticmethod
    def add_atr(df: pd.DataFrame, length: int = 14, column_name: str = 'atr'):
        atr = df.ta.atr(length=length)
        if atr is not None:
            df[column_name] = atr
        return df

    @staticmethod
    def add_cci(df: pd.DataFrame, length: int = 20, column_name: str = 'cci'):
        cci = df.ta.cci(length=length)
        if cci is not None:
            df[column_name] = cci
        return df

    @staticmethod
    def add_adx_value(df: pd.DataFrame, length: int = 14, column_name: str = 'adx'):
        adx_df = df.ta.adx(length=length)
        if adx_df is not None:
            adx_col = f"ADX_{length}"
            if adx_col in adx_df.columns:
                df[column_name] = adx_df[adx_col]
        return df

    @staticmethod
    def add_wavetrend(df: pd.DataFrame, chlen: int = 10, avg: int = 21, column_name: str = 'wt'):
        ap = (df['high'] + df['low'] + df['close']) / 3
        esa = df.ta.ema(close=ap, length=chlen)
        d = df.ta.ema(close=(ap - esa).abs(), length=chlen)

        ci = (ap - esa) / (0.015 * d)
        wt1 = df.ta.ema(close=ci, length=avg)

        if wt1 is not None:
            df[column_name] = wt1
        return df