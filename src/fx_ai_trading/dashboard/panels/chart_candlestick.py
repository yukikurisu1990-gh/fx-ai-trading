"""Panel: Candlestick Chart — OHLCV with trade entry/exit and signal overlays."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service

_COLS_PER_ROW = 10

_GRANULARITY_OPTIONS = ["M1", "M5", "M15", "H1"]
_RESAMPLE_RULE = {"M1": None, "M5": "5min", "M15": "15min", "H1": "1h"}
# Fetch more M1 bars when resampling to higher timeframes
_FETCH_MULTIPLIER = {"M1": 1, "M5": 5, "M15": 15, "H1": 60}

_THRESHOLD = 0.40
_JST = pd.Timedelta(hours=9)

_PIP_SIZE: dict[str, float] = {
    "AUD_JPY": 0.01, "CHF_JPY": 0.01, "EUR_JPY": 0.01,
    "GBP_JPY": 0.01, "NZD_JPY": 0.01, "USD_JPY": 0.01,
}

# Default number of bars visible in the initial chart view (before scrolling)
_DEFAULT_VISIBLE: dict[str, int] = {"M1": 120, "M5": 96, "M15": 96, "H1": 72}


@st.cache_data(ttl=30)
def _fetch_candles(_engine: object, instrument: str, limit: int) -> list[dict]:
    return dashboard_query_service.get_market_candles(
        _engine,
        instrument=instrument,
        tier="M1",
        limit=limit,  # type: ignore[arg-type]
    )


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate M1 OHLCV bars into a higher timeframe."""
    df = df.set_index("event_time_utc").sort_index()
    resampled = df.resample(rule, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).dropna(subset=["open"])
    resampled = resampled.reset_index()
    return resampled


@st.cache_data(ttl=30)
def _fetch_trades(_engine: object, instrument: str, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_trade_markers(
        _engine,
        instrument=instrument,
        account_id=account_id,  # type: ignore[arg-type]
    )


@st.cache_data(ttl=30)
def _fetch_signals(_engine: object, instrument: str, since_utc: object = None) -> list[dict]:
    return dashboard_query_service.get_decision_markers(
        _engine,
        instrument=instrument,  # type: ignore[arg-type]
        since=since_utc,  # type: ignore[arg-type]
    )


@st.cache_data(ttl=300)
def _list_instruments(_engine: object) -> list[str]:
    instruments = dashboard_query_service.list_instruments(_engine)  # type: ignore[arg-type]
    if not instruments:
        # fallback: instruments that at least have candle data
        instruments = dashboard_query_service.list_candle_instruments(_engine)  # type: ignore[arg-type]
    return instruments


def _utc_to_jst(col: pd.Series) -> pd.Series:
    """Convert a tz-aware or UTC-naive datetime Series to JST-naive."""
    s = pd.to_datetime(col)
    if s.dt.tz is not None:
        return s.dt.tz_convert("Asia/Tokyo").dt.tz_localize(None)
    return s + _JST


def render(engine: Engine | None, account_id: str | None = None) -> None:
    try:
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed — candlestick chart unavailable.")
        return

    st.subheader("ロウソク足チャート（JST）")

    instruments = _list_instruments(engine)
    if not instruments:
        st.info("通貨ペアデータなし。`python scripts/seed_demo_data.py` を実行してください。")
        return

    # --- Granularity + Bar count (先に描画して st.rerun() 後も状態保持) ---
    ctrl_gran, ctrl_bars = st.columns([1, 2])
    with ctrl_gran:
        granularity = st.radio(
            "時間軸",
            options=_GRANULARITY_OPTIONS,
            index=0,
            horizontal=True,
            key="chart_candlestick.granularity",
        )
    with ctrl_bars:
        n_bars = st.select_slider(
            "本数",
            options=[50, 100, 200, 500, 1440, 4320, 10080],
            value=200,
            key="chart_candlestick.n_bars",
            format_func=lambda v: {
                50: "50",
                100: "100",
                200: "200",
                500: "500",
                1440: "1D",
                4320: "3D",
                10080: "7D",
            }[v],
        )

    col_signals, col_trades, col_proba, col_tpsl = st.columns(4)
    with col_signals:
        show_signals = st.checkbox("シグナル表示", value=True, key="chart_candlestick.signals")
    with col_trades:
        show_trades = st.checkbox(
            "取引エントリー/決済表示", value=True, key="chart_candlestick.trades"
        )
    with col_proba:
        show_proba = st.checkbox(
            "確信度パネル(p_long/p_short)", value=True, key="chart_candlestick.proba"
        )
    with col_tpsl:
        show_tpsl = st.checkbox("TP/SL表示", value=True, key="chart_candlestick.tpsl")

    # --- Instrument selector (button grid) ---
    _key = "chart_candlestick.instrument"
    if _key not in st.session_state or st.session_state[_key] not in instruments:
        st.session_state[_key] = instruments[0]

    selected = st.session_state[_key]

    for row_start in range(0, len(instruments), _COLS_PER_ROW):
        row_pairs = instruments[row_start : row_start + _COLS_PER_ROW]
        cols = st.columns(_COLS_PER_ROW)
        for col, pair in zip(cols, row_pairs, strict=False):
            with col:
                btn_type = "primary" if pair == selected else "secondary"
                if st.button(
                    pair,
                    key=f"chart_inst_btn_{pair}",
                    type=btn_type,
                    use_container_width=True,
                ):
                    st.session_state[_key] = pair
                    st.rerun()

    instrument = st.session_state[_key]

    # Fetch enough M1 bars to cover the requested n_bars at the selected granularity
    fetch_limit = n_bars * _FETCH_MULTIPLIER.get(granularity, 1)
    candles = _fetch_candles(engine, instrument, fetch_limit)
    if not candles:
        st.info(
            f"{instrument} のロウソク足データなし。デモループが稼働中であれば数分後に表示されます。"
        )
        return

    df = pd.DataFrame(candles)
    # Convert to UTC-naive first (required for resample), then JST after resampling
    df["event_time_utc"] = (
        pd.to_datetime(df["event_time_utc"]).dt.tz_convert("UTC").dt.tz_localize(None)
    )
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)

    # Resample M1 → selected granularity (in UTC to avoid boundary issues)
    resample_rule = _RESAMPLE_RULE.get(granularity)
    if resample_rule is not None:
        df = _resample(df, resample_rule)
        df = df.tail(n_bars).reset_index(drop=True)

    # Convert to JST for display
    df["event_time_utc"] += _JST

    if df.empty:
        st.info(f"{instrument} ({granularity}): データが足りません。M1バーが蓄積されるまでお待ちください。")
        return

    t_min = df["event_time_utc"].min()
    t_max = df["event_time_utc"].max()

    # Fetch signals (contains p_long/p_short in meta)
    # t_min is JST-naive; convert back to UTC for the DB query
    since_utc = t_min - _JST
    signals = _fetch_signals(engine, instrument, since_utc) if (show_signals or show_proba) else []
    sig_df = pd.DataFrame(signals) if signals else pd.DataFrame()
    if not sig_df.empty:
        sig_df["signal_time_utc"] = _utc_to_jst(sig_df["signal_time_utc"])
        sig_df = sig_df[
            (sig_df["signal_time_utc"] >= t_min) & (sig_df["signal_time_utc"] <= t_max)
        ].sort_values("signal_time_utc")

    # --- Build figure (1 or 2 rows) ---
    if show_proba and not sig_df.empty and "p_long" in sig_df.columns:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.65, 0.28],
            vertical_spacing=0.03,
        )
        candle_row = 1
        proba_row = 2
    else:
        fig = make_subplots(rows=1, cols=1)
        candle_row = 1
        proba_row = None

    # --- Candlestick ---
    fig.add_trace(
        go.Candlestick(
            x=df["event_time_utc"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=candle_row, col=1,
    )

    # --- Signal markers ---
    if show_signals and not sig_df.empty:
        price_range = df["high"].max() - df["low"].min()
        offset = price_range * 0.04
        indexed = df.set_index("event_time_utc")
        for direction, color, symbol, price_band, sign, label in [
            ("buy", "#2196f3", "triangle-up", "low", -1, "シグナル 買"),
            ("sell", "#ff9800", "triangle-down", "high", 1, "シグナル 売"),
        ]:
            sub = sig_df[sig_df["signal_direction"] == direction]
            if not sub.empty:
                price_col = indexed[price_band].reindex(
                    sub["signal_time_utc"], method="nearest"
                )
                fig.add_trace(
                    go.Scatter(
                        x=sub["signal_time_utc"].values,
                        y=(price_col + sign * offset).values,
                        mode="markers",
                        marker={"symbol": symbol, "size": 10, "color": color, "opacity": 0.85},
                        name=label,
                        hovertemplate=f"Signal: {direction}<br>Time: %{{x}}<br><extra></extra>",
                    ),
                    row=candle_row, col=1,
                )

    # --- TP/SL lines ---
    if show_tpsl and not sig_df.empty:
        adopted = sig_df[sig_df["signal_direction"].isin(["buy", "sell"])].copy()
        if not adopted.empty and "tp_pips" in adopted.columns:
            adopted = adopted.dropna(subset=["tp_pips", "sl_pips"])
            adopted = adopted[adopted["tp_pips"] > 0]
            if not adopted.empty:
                pip_sz = _PIP_SIZE.get(instrument, 0.0001)
                _bar_secs = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}.get(granularity, 60)
                df_close = df.set_index("event_time_utc")["close"].sort_index()
                tp_x: list = []
                tp_y: list = []
                sl_x: list = []
                sl_y: list = []
                for _, row in adopted.iterrows():
                    t = row["signal_time_utc"]
                    close_price = df_close.reindex([t], method="nearest").iloc[0]
                    tp_pips = float(row["tp_pips"])
                    sl_pips = float(row["sl_pips"])
                    direction = row["signal_direction"]
                    if direction == "buy":
                        abs_tp = close_price + tp_pips * pip_sz
                        abs_sl = close_price - sl_pips * pip_sz
                    else:
                        abs_tp = close_price - tp_pips * pip_sz
                        abs_sl = close_price + sl_pips * pip_sz
                    holding_s = float(row.get("holding_time_seconds") or 1800)
                    end_t = min(
                        t + pd.Timedelta(seconds=holding_s),
                        t_max + pd.Timedelta(seconds=_bar_secs),
                    )
                    tp_x += [t, end_t, None]
                    tp_y += [abs_tp, abs_tp, None]
                    sl_x += [t, end_t, None]
                    sl_y += [abs_sl, abs_sl, None]
                if tp_x:
                    fig.add_trace(
                        go.Scatter(
                            x=tp_x,
                            y=tp_y,
                            mode="lines",
                            line={"color": "#66bb6a", "width": 1.5, "dash": "dot"},
                            name="TP",
                            hovertemplate="TP: %{y:.5f}<extra></extra>",
                        ),
                        row=candle_row, col=1,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=sl_x,
                            y=sl_y,
                            mode="lines",
                            line={"color": "#ef5350", "width": 1.5, "dash": "dot"},
                            name="SL",
                            hovertemplate="SL: %{y:.5f}<extra></extra>",
                        ),
                        row=candle_row, col=1,
                    )

    # --- Trade markers ---
    if show_trades:
        trades = _fetch_trades(engine, instrument, account_id)
        if trades:
            tr_df = pd.DataFrame(trades)
            tr_df["entry_time"] = _utc_to_jst(tr_df["entry_time"])
            tr_df["exit_time"] = _utc_to_jst(tr_df["exit_time"])
            tr_df["entry_price"] = tr_df["entry_price"].astype(float)
            tr_df["exit_price"] = tr_df["exit_price"].astype(float)
            tr_df["pnl_realized"] = tr_df["pnl_realized"].astype(float)
            tr_df = tr_df[(tr_df["entry_time"] >= t_min) & (tr_df["entry_time"] <= t_max)]
            if not tr_df.empty:
                win = tr_df["pnl_realized"] >= 0
                fig.add_trace(
                    go.Scatter(
                        x=tr_df["entry_time"].values,
                        y=tr_df["entry_price"].values,
                        mode="markers",
                        marker={
                            "symbol": "circle-open",
                            "size": 8,
                            "color": "#ffffff",
                            "line": {"width": 2, "color": "#90caf9"},
                        },
                        name="エントリー",
                        hovertemplate="エントリー: %{x} JST<br>価格: %{y:.5f}<extra></extra>",
                    ),
                    row=candle_row, col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=tr_df.loc[win, "exit_time"].values,
                        y=tr_df.loc[win, "exit_price"].values,
                        mode="markers",
                        marker={"symbol": "x", "size": 9, "color": "#4caf50"},
                        name="決済（利益）",
                        hovertemplate="決済 利益: %{x} JST<br>損益: %{customdata:.0f}<extra></extra>",
                        customdata=tr_df.loc[win, "pnl_realized"].values,
                    ),
                    row=candle_row, col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=tr_df.loc[~win, "exit_time"].values,
                        y=tr_df.loc[~win, "exit_price"].values,
                        mode="markers",
                        marker={"symbol": "x", "size": 9, "color": "#f44336"},
                        name="決済（損失）",
                        hovertemplate="決済 損失: %{x} JST<br>損益: %{customdata:.0f}<extra></extra>",
                        customdata=tr_df.loc[~win, "pnl_realized"].values,
                    ),
                    row=candle_row, col=1,
                )

    # --- Probability sub-panel ---
    if proba_row is not None and not sig_df.empty:
        p_df = sig_df.dropna(subset=["p_long", "p_short"])
        if not p_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=p_df["signal_time_utc"].values,
                    y=p_df["p_long"].astype(float).values,
                    mode="lines",
                    line={"color": "#42a5f5", "width": 1.5},
                    name="p_long",
                    hovertemplate="p_long: %{y:.3f}<br>%{x} JST<extra></extra>",
                ),
                row=proba_row, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=p_df["signal_time_utc"].values,
                    y=p_df["p_short"].astype(float).values,
                    mode="lines",
                    line={"color": "#ef9a9a", "width": 1.5},
                    name="p_short",
                    hovertemplate="p_short: %{y:.3f}<br>%{x} JST<extra></extra>",
                ),
                row=proba_row, col=1,
            )
            fig.add_hline(
                y=_THRESHOLD,
                line_dash="dot",
                line_color="#ffd54f",
                line_width=1,
                annotation_text=f"閾値 {_THRESHOLD}",
                annotation_font_color="#ffd54f",
                annotation_font_size=10,
                row=proba_row, col=1,
            )

    # --- Initial visible range: latest N bars, rest scrollable ---
    visible = min(_DEFAULT_VISIBLE.get(granularity, 120), len(df))
    x_start = df["event_time_utc"].iloc[-visible]
    # Add half a bar of right-padding so the last candle isn't clipped
    bar_secs = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}.get(granularity, 60)
    x_end = df["event_time_utc"].iloc[-1] + pd.Timedelta(seconds=bar_secs // 2)

    # --- Layout ---
    bottom_row = proba_row if proba_row else candle_row
    chart_height = 600 if proba_row else 460

    fig.update_layout(
        height=chart_height,
        margin={"t": 20, "b": 10, "l": 10, "r": 10},
        legend={"orientation": "h", "y": -0.08},
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font={"color": "#e0e0e0"},
        # dragmode for pan-by-default (user can still zoom via toolbar)
        dragmode="pan",
    )

    # Disable rangeslider on all axes, then enable only on the bottom row
    fig.update_xaxes(rangeslider_visible=False)
    fig.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.06, bgcolor="#2a2a2a"),
        range=[x_start, x_end],
        row=bottom_row, col=1,
    )

    # Grid styling
    for axis in ("xaxis", "yaxis", "xaxis2", "yaxis2"):
        fig.update_layout(**{axis: {"gridcolor": "#333", "showgrid": True}})

    if proba_row:
        p_max = sig_df[["p_long", "p_short"]].max().max() if not sig_df.empty else 0.5
        fig.update_yaxes(
            title_text="確信度",
            row=proba_row, col=1,
            range=[0, max(0.5, p_max * 1.1)],
        )

    st.plotly_chart(fig, use_container_width=True)
