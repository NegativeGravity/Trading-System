import os
import json
from typing import List, Dict, Any
from trader.domain.models import SignalType


class TradeChartGenerator:
    def __init__(self, candles: List[Any], trades_history: List[Dict[str, Any]], symbol: str):
        self.candles = candles
        self.trades = trades_history
        self.symbol = symbol
        self.chart_data = []
        self.volume_data = []
        self.markers_data = []

    def _prepare_data(self) -> None:
        if not self.candles:
            return

        for c in self.candles:
            ts = int(c.timestamp.timestamp())

            self.chart_data.append({
                'time': ts,
                'open': float(c.open),
                'high': float(c.high),
                'low': float(c.low),
                'close': float(c.close)
            })

            color = '#26a69a' if c.close >= c.open else '#ef5350'
            self.volume_data.append({
                'time': ts,
                'value': int(c.volume),  # Cast uint64 to native Python int
                'color': color
            })

    def _prepare_markers(self) -> None:
        if not self.trades:
            return

        for t in self.trades:
            is_dict = isinstance(t, dict)
            t_type = t['type'] if is_dict else (SignalType.BUY if t.direction == 'BUY' else SignalType.SELL)
            t_open = t['open_time'] if is_dict else t.open_time
            t_close = t['close_time'] if is_dict else t.close_time

            # Cast numpy types to native Python types
            t_profit = float(t['net_profit'] if is_dict else t.net_profit)
            t_ticket = int(t['ticket'] if is_dict else t.ticket)

            open_ts = int(t_open.timestamp())
            close_ts = int(t_close.timestamp())
            is_buy = (t_type == SignalType.BUY)

            self.markers_data.append({
                'time': open_ts,
                'position': 'belowBar' if is_buy else 'aboveBar',
                'color': '#2196F3' if is_buy else '#FF6D00',
                'shape': 'arrowUp' if is_buy else 'arrowDown',
                'text': f'ENTRY #{t_ticket}'
            })

            is_win = t_profit > 0
            self.markers_data.append({
                'time': close_ts,
                'position': 'aboveBar' if is_buy else 'belowBar',
                'color': '#00E676' if is_win else '#FF1744',
                'shape': 'circle',
                'text': f'EXIT ${t_profit:.2f}'
            })

        self.markers_data.sort(key=lambda x: x['time'])

    def save_html(self, filename: str = "backtest_chart.html") -> None:
        self._prepare_data()
        self._prepare_markers()

        if not self.chart_data:
            return

        base_dir = os.path.dirname(os.path.dirname(__file__))
        template_path = os.path.join(base_dir, 'templates', 'tv_template.html')

        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        html_content = html_content.replace('{{SYMBOL}}', self.symbol)
        html_content = html_content.replace('{{CHART_DATA}}', json.dumps(self.chart_data))
        html_content = html_content.replace('{{VOLUME_DATA}}', json.dumps(self.volume_data))
        html_content = html_content.replace('{{MARKERS_DATA}}', json.dumps(self.markers_data))

        output_dir = r"G:\Trading-System\web_dashboard\media"
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        try:
            os.startfile(output_path)
        except Exception:
            pass


def generate_trade_chart(candles, trades_history, symbol, filename="backtest_chart.html"):
    generator = TradeChartGenerator(candles, trades_history, symbol)
    generator.save_html(filename)