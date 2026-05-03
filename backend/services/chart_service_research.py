import matplotlib
matplotlib.use('Agg')  # Must be set before any other matplotlib/mplfinance imports for headless server rendering
import os
import pandas as pd
import numpy as np
import mplfinance as mpf

def _calc_adx(df, period=14):
    """Calculate ADX, +DI, and -DI."""
    high = df['high']
    low = df['low']
    close = df['close']

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    pos_dm = pd.Series(pos_dm, index=df.index)
    neg_dm = pd.Series(neg_dm, index=df.index)

    # Wilder's Smoothing (using ewm with alpha=1/n is close enough for wilders)
    # Exact Wilder's smoothing is slightly different, but this is standard approximation
    tr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()
    pos_dm_smooth = pos_dm.ewm(alpha=1/period, adjust=False).mean()
    neg_dm_smooth = neg_dm.ewm(alpha=1/period, adjust=False).mean()

    plus_di = 100 * (pos_dm_smooth / tr_smooth)
    minus_di = 100 * (neg_dm_smooth / tr_smooth)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).abs()
    adx = dx.ewm(alpha=1/period, adjust=False).mean()

    return adx, plus_di, minus_di

def _calc_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def build_session_chart(ticker: str, date: str, df: pd.DataFrame, job_id: str, storage_dir: str) -> str:
    """
    Builds a 4-panel intraday chart using mplfinance and saves it.
    Expects df with lower case columns: 'open', 'high', 'low', 'close', 'volume'
    """
    if df.empty or len(df) < 55:
        raise ValueError("Not enough data to compute technical indicators (need at least 55 rows).")

    # Rename columns to title case for mplfinance
    df_mpf = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})

    # 1. Calculate EMAs
    ema_spans = [8, 13, 21, 34, 55]
    colors = ['#00FFFF', '#00BFFF', '#1E90FF', '#4169E1', '#0000CD'] # Cyan to dark blue
    emas = []
    for span in ema_spans:
        df_mpf[f'EMA_{span}'] = df_mpf['Close'].ewm(span=span, adjust=False).mean()
        emas.append(df_mpf[f'EMA_{span}'])

    # 2. RVOL (Rolling 20-period volume average)
    df_mpf['Vol_Avg'] = df_mpf['Volume'].rolling(20).mean()
    df_mpf['RVOL'] = df_mpf['Volume'] / df_mpf['Vol_Avg']
    df_mpf['RVOL'] = df_mpf['RVOL'].fillna(1.0) # Handle initial NaNs

    # 3. ADX & DI
    adx, plus_di, minus_di = _calc_adx(df)
    df_mpf['ADX'] = adx
    df_mpf['+DI'] = plus_di
    df_mpf['-DI'] = minus_di

    # 4. ATR
    df_mpf['ATR'] = _calc_atr(df)

    # Clean NaNs to avoid plot errors
    df_mpf = df_mpf.bfill().fillna(0)

    # Build addplots
    apds = []
    
    # EMA Ribbon (Panel 0)
    for i, span in enumerate(ema_spans):
        apds.append(mpf.make_addplot(df_mpf[f'EMA_{span}'], color=colors[i], panel=0, width=1))

    # RVOL overlay on Volume (Panel 1) - scale it to fit alongside volume visually, or just use secondary axis
    apds.append(mpf.make_addplot(df_mpf['RVOL'], type='line', color='magenta', panel=1, secondary_y=True, ylabel='RVOL (x)'))

    # ADX and DI (Panel 2)
    apds.append(mpf.make_addplot(df_mpf['ADX'], color='white', panel=2, ylabel='ADX'))
    apds.append(mpf.make_addplot(df_mpf['+DI'], color='lime', panel=2, type='line', linestyle='dotted'))
    apds.append(mpf.make_addplot(df_mpf['-DI'], color='red', panel=2, type='line', linestyle='dotted'))

    # ATR (Panel 3)
    apds.append(mpf.make_addplot(df_mpf['ATR'], color='yellow', panel=3, ylabel='ATR'))

    # Styling
    custom_style = mpf.make_mpf_style(
        base_mpf_style='nightclouds',
        facecolor='#111111',
        edgecolor='#222222',
        figcolor='#0a0a0a',
        gridcolor='#333333',
        gridstyle='--',
        rc={'axes.labelcolor': 'white', 'xtick.color': 'white', 'ytick.color': 'white'}
    )

    filename = f"{ticker}_Session_{date}_{job_id[:8]}.png"
    filepath = os.path.join(storage_dir, filename)

    # We use volume=True which automatically goes to panel=1. 
    # That means our ADX is panel=2 and ATR is panel=3.
    mpf.plot(
        df_mpf, 
        type='candle', 
        volume=True, 
        addplot=apds, 
        style=custom_style,
        title=f"{ticker} Intraday Technicals - {date}",
        panel_ratios=(5, 2, 2, 2),
        figratio=(16, 10),
        figscale=1.5,
        savefig=filepath,
        tight_layout=True,
        warn_too_much_data=10000
    )

    return filepath
