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

    st.subheader("Candlestick Chart")

    instruments = _list_instruments(engine)
    if not instruments:
        st.info("No candle data available. Run `python scripts/seed_demo_data.py` to populate.")
        return

    col_inst, col_bars = st.columns([2, 1])
    with col_inst:
        instrument = st.selectbox(
            "Instrument",
            instruments,
            key="chart_candlestick.instrument",
        )
    with col_bars:
        n_bars = st.select_slider(
            "Bars",
            options=[50, 100, 200, 500],
            value=200,
            key="chart_candlestick.n_bars",
        )

    col_signals, col_trades = st.columns(2)
    with col_signals:
        show_signals = st.checkbox(
            "Show strategy signals", value=True, key="chart_candlestick.signals"
        )
    with col_trades:
        show_trades = st.checkbox(
            "Show trade entries/exits", value=True, key="chart_candlestick.trades"
        )

    candles = _fetch_candles(engine, instrument, n_bars)
    if not candles:
        st.info(f"No candle data for {instrument}.")
        return

    df = pd.DataFrame(candles)
    df["event_time_utc"] = pd.to_datetime(df["event_time_utc"])
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
            sig_df["signal_time_utc"] = pd.to_datetime(sig_df["signal_time_utc"])
            sig_df = sig_df[
                (sig_df["signal_time_utc"] >= t_min) & (sig_df["signal_time_utc"] <= t_max)
            ]
            for direction, color, symbol in [
                ("buy", "#2196f3", "triangle-up"),
                ("sell", "#ff9800", "triangle-down"),
            ]:
                sub = sig_df[sig_df["signal_direction"] == direction]
                if not sub.empty:
                    price_col = df.set_index("event_time_utc")["close"].reindex(
                        sub["signal_time_utc"], method="nearest"
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=sub["signal_time_utc"].values,
                            y=price_col.values,
                            mode="markers",
                            marker={"symbol": symbol, "size": 10, "color": color, "opacity": 0.7},
                            name=f"Signal {direction}",
                            hovertemplate=(
                                f"Signal: {direction}<br>"
                                "Time: %{x}<br>Price: %{y:.5f}<extra></extra>"
                            ),
                        )
                    )

    if show_trades:
        trades = _fetch_trades(engine, instrument, account_id)
        if trades:
            tr_df = pd.DataFrame(trades)
            tr_df["entry_time"] = pd.to_datetime(tr_df["entry_time"])
            tr_df["exit_time"] = pd.to_datetime(tr_df["exit_time"])
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
                        name="Entry",
                        hovertemplate="Entry: %{x}<br>Price: %{y:.5f}<extra></extra>",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=tr_df.loc[win, "exit_time"].values,
                        y=tr_df.loc[win, "exit_price"].values,
                        mode="markers",
                        marker={"symbol": "x", "size": 9, "color": "#4caf50"},
                        name="Exit (Win)",
                        hovertemplate="Exit WIN: %{x}<br>PnL: %{customdata:.0f}<extra></extra>",
                        customdata=tr_df.loc[win, "pnl_realized"].values,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=tr_df.loc[~win, "exit_time"].values,
                        y=tr_df.loc[~win, "exit_price"].values,
                        mode="markers",
                        marker={"symbol": "x", "size": 9, "color": "#f44336"},
                        name="Exit (Loss)",
                        hovertemplate="Exit LOSS: %{x}<br>PnL: %{customdata:.0f}<extra></extra>",
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
