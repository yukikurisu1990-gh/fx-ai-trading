"""Panel: Candlestick Chart — OHLCV with trade entry/exit and signal overlays."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=30)
def _fetch_candles(_engine: object, instrument: str, limit: int) -> list[dict]:
    return dashboard_query_service.get_market_candles(
        _engine,
        instrument=instrument,
        tier="M1",
        limit=limit,  # type: ignore[arg-type]
    )


@st.cache_data(ttl=30)
def _fetch_trades(_engine: object, instrument: str, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_trade_markers(
        _engine,
        instrument=instrument,
        account_id=account_id,  # type: ignore[arg-type]
    )


@st.cache_data(ttl=30)
def _fetch_signals(_engine: object, instrument: str) -> list[dict]:
    return dashboard_query_service.get_decision_markers(
        _engine,
        instrument=instrument,  # type: ignore[arg-type]
    )


@st.cache_data(ttl=60)
def _list_instruments(_engine: object) -> list[str]:
    return dashboard_query_service.list_candle_instruments(_engine)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed — candlestick chart unavailable.")
        return

    st.subheader("ロウソク足チャート")

    instruments = _list_instruments(engine)
    if not instruments:
        st.info("ロウソク足データなし。`python scripts/seed_demo_data.py` を実行してください。")
        return

    col_inst, col_bars = st.columns([2, 1])
    with col_inst:
        instrument = st.selectbox(
            "通貨ペア",
            instruments,
            key="chart_candlestick.instrument",
        )
    with col_bars:
        n_bars = st.select_slider(
            "本数",
            options=[50, 100, 200, 500, 1440, 4320, 10080],
            value=1440,
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

    col_signals, col_trades = st.columns(2)
    with col_signals:
        show_signals = st.checkbox("シグナル表示", value=True, key="chart_candlestick.signals")
    with col_trades:
        show_trades = st.checkbox(
            "取引エントリー/決済表示", value=True, key="chart_candlestick.trades"
        )

    candles = _fetch_candles(engine, instrument, n_bars)
    if not candles:
        st.info(f"{instrument} のロウソク足データなし。")
        return

    df = pd.DataFrame(candles)
    df["event_time_utc"] = (
        pd.to_datetime(df["event_time_utc"]).dt.tz_convert("UTC").dt.tz_localize(None)
    )
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)

    fig = go.Figure()

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
        )
    )

    t_min = df["event_time_utc"].min()
    t_max = df["event_time_utc"].max()

    if show_signals:
        signals = _fetch_signals(engine, instrument)
        if signals:
            sig_df = pd.DataFrame(signals)
            sig_df["signal_time_utc"] = (
                pd.to_datetime(sig_df["signal_time_utc"]).dt.tz_convert("UTC").dt.tz_localize(None)
            )
            sig_df = sig_df[
                (sig_df["signal_time_utc"] >= t_min) & (sig_df["signal_time_utc"] <= t_max)
            ]
            price_range = df["high"].max() - df["low"].min()
            offset = price_range * 0.04
            indexed = df.set_index("event_time_utc")
            for direction, color, symbol, price_band, sign in [
                ("buy", "#2196f3", "triangle-up", "low", -1),
                ("sell", "#ff9800", "triangle-down", "high", 1),
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
                            name=f"シグナル {'買' if direction == 'buy' else '売'}",
                            hovertemplate=(
                                f"Signal: {direction}<br>Time: %{{x}}<br><extra></extra>"
                            ),
                        )
                    )

    if show_trades:
        trades = _fetch_trades(engine, instrument, account_id)
        if trades:
            tr_df = pd.DataFrame(trades)
            tr_df["entry_time"] = (
                pd.to_datetime(tr_df["entry_time"]).dt.tz_convert("UTC").dt.tz_localize(None)
            )
            tr_df["exit_time"] = (
                pd.to_datetime(tr_df["exit_time"]).dt.tz_convert("UTC").dt.tz_localize(None)
            )
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
                        hovertemplate="エントリー: %{x}<br>価格: %{y:.5f}<extra></extra>",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=tr_df.loc[win, "exit_time"].values,
                        y=tr_df.loc[win, "exit_price"].values,
                        mode="markers",
                        marker={"symbol": "x", "size": 9, "color": "#4caf50"},
                        name="決済（利益）",
                        hovertemplate="決済 利益: %{x}<br>損益: %{customdata:.0f}<extra></extra>",
                        customdata=tr_df.loc[win, "pnl_realized"].values,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=tr_df.loc[~win, "exit_time"].values,
                        y=tr_df.loc[~win, "exit_price"].values,
                        mode="markers",
                        marker={"symbol": "x", "size": 9, "color": "#f44336"},
                        name="決済（損失）",
                        hovertemplate="決済 損失: %{x}<br>損益: %{customdata:.0f}<extra></extra>",
                        customdata=tr_df.loc[~win, "pnl_realized"].values,
                    )
                )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=420,
        margin={"t": 20, "b": 20, "l": 10, "r": 10},
        legend={"orientation": "h", "y": -0.15},
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font={"color": "#e0e0e0"},
        xaxis={"gridcolor": "#333", "showgrid": True},
        yaxis={"gridcolor": "#333", "showgrid": True},
    )
    st.plotly_chart(fig, use_container_width=True)
