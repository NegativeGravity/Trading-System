import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from trader.domain.models import SignalType


def _create_figure(candles, trades_history, symbol):
    """
    Internal helper function to create the Plotly figure.
    Used by both file generator (CLI) and div generator (Web).
    """
    if not candles:
        return None

    df = pd.DataFrame([c.__dict__ for c in candles])

    # Create Subplots (Price + Volume)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, subplot_titles=(f'{symbol} Price', 'Volume'),
                        row_width=[0.2, 0.7])

    # Candlestick Chart (Top Panel)
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ), row=1, col=1)

    # Volume Chart (Bottom Panel)
    colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(
        x=df['timestamp'], y=df['volume'],
        marker_color=colors, name='Volume'
    ), row=2, col=1)

    # Prepare Trade Markers
    buy_entries_x, buy_entries_y = [], []
    sell_entries_x, sell_entries_y = [], []
    buy_exits_x, buy_exits_y, buy_exits_text = [], [], []
    sell_exits_x, sell_exits_y, sell_exits_text = [], [], []
    shapes = []

    for t in trades_history:
        # Handle both Dictionary (CLI) and ORM Object (Web)
        is_dict = isinstance(t, dict)

        if is_dict:
            t_type = t['type']
            t_open = t['open_time']
            t_close = t['close_time']
            t_entry = t['entry_price']
            t_exit = t['exit_price']
            t_profit = t['net_profit']
            t_ticket = t['ticket']
            t_reason = t['exit_reason']
        else:
            t_type = SignalType.BUY if t.direction == 'BUY' else SignalType.SELL
            t_open = t.open_time
            t_close = t.close_time
            t_entry = t.entry_price
            t_exit = t.exit_price
            t_profit = t.net_profit
            t_ticket = t.ticket
            t_reason = t.exit_reason

        hover_text = f"#{t_ticket} | P/L: ${t_profit:.2f}<br>{t_reason}"

        # Draw connection line
        shapes.append(dict(
            type="line", x0=t_open, y0=t_entry, x1=t_close, y1=t_exit,
            line=dict(color="gray", width=1, dash="dot"), opacity=0.5, xref="x", yref="y"
        ))

        if t_type == SignalType.BUY:
            buy_entries_x.append(t_open)
            buy_entries_y.append(t_entry)
            buy_exits_x.append(t_close)
            buy_exits_y.append(t_exit)
            buy_exits_text.append(hover_text)
        else:
            sell_entries_x.append(t_open)
            sell_entries_y.append(t_entry)
            sell_exits_x.append(t_close)
            sell_exits_y.append(t_exit)
            sell_exits_text.append(hover_text)

    # Add Markers
    fig.add_trace(go.Scatter(x=buy_entries_x, y=buy_entries_y, mode='markers', name='Buy Entry',
                             marker=dict(symbol='triangle-up', size=10, color='#2979ff')), row=1, col=1)
    fig.add_trace(go.Scatter(x=sell_entries_x, y=sell_entries_y, mode='markers', name='Sell Entry',
                             marker=dict(symbol='triangle-down', size=10, color='#ff9100')), row=1, col=1)

    fig.add_trace(
        go.Scatter(x=buy_exits_x, y=buy_exits_y, mode='markers', name='Buy Exit', text=buy_exits_text, hoverinfo='text',
                   marker=dict(symbol='circle', size=8, color='#2979ff', line=dict(width=1, color='white'))), row=1,
        col=1)
    fig.add_trace(go.Scatter(x=sell_exits_x, y=sell_exits_y, mode='markers', name='Sell Exit', text=sell_exits_text,
                             hoverinfo='text',
                             marker=dict(symbol='circle', size=8, color='#ff9100', line=dict(width=1, color='white'))),
                  row=1, col=1)

    # Layout Styling
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#1e1e1e',
        plot_bgcolor='#1e1e1e',
        height=700,
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis_rangeslider_visible=False,
        shapes=shapes,
        showlegend=True,
        legend=dict(orientation="h", y=1, x=0)
    )

    fig.update_xaxes(showgrid=True, gridcolor='#333', row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor='#333', row=1, col=1)
    fig.update_yaxes(showgrid=False, row=2, col=1)

    return fig


def generate_trade_chart(candles, trades_history, symbol, filename="backtest_chart.html"):
    """
    Saves the chart as an HTML file (For CLI / Run Backtest).
    """
    print("📊 Generating interactive trade chart...")
    fig = _create_figure(candles, trades_history, symbol)

    if fig:
        output_dir = r"G:\Trading-System\web_dashboard\media"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_path = os.path.join(output_dir, filename)
        fig.write_html(output_path)
        print(f"✅ Chart saved to: {output_path}")

        try:
            os.startfile(output_path)
        except:
            pass
    else:
        print("⚠️ No data to generate chart.")


def get_plot_div(candles, trades_history, symbol):
    """
    Returns the HTML div string (For Web / Views).
    """
    fig = _create_figure(candles, trades_history, symbol)
    if fig:
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    return "<div>No data available</div>"