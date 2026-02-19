import json
import zlib
from typing import List, Dict, Any
from trader.domain.models import SignalType
from journal.models import ChartData, BacktestSession


def export_tv_data(session_id: int, candles: List[Any], trades: List[Dict[str, Any]]) -> None:
    chart_data = []
    volume_data = []
    markers_data = []

    for c in candles:
        ts = int(c.timestamp.timestamp())
        chart_data.append({
            'time': ts,
            'open': float(c.open),
            'high': float(c.high),
            'low': float(c.low),
            'close': float(c.close)
        })
        color = '#26a69a' if c.close >= c.open else '#ef5350'
        volume_data.append({
            'time': ts,
            'value': int(c.volume),
            'color': color
        })

    for t in trades:
        is_dict = isinstance(t, dict)
        t_type = t['type'] if is_dict else (SignalType.BUY if t.direction == 'BUY' else SignalType.SELL)
        t_open = t['open_time'] if is_dict else t.open_time
        t_close = t['close_time'] if is_dict else t.close_time
        t_profit = float(t['net_profit'] if is_dict else t.net_profit)
        t_ticket = int(t['ticket'] if is_dict else t.ticket)

        open_ts = int(t_open.timestamp())
        close_ts = int(t_close.timestamp())
        is_buy = (t_type == SignalType.BUY)

        markers_data.append({
            'time': open_ts,
            'position': 'belowBar' if is_buy else 'aboveBar',
            'color': '#2196F3' if is_buy else '#FF6D00',
            'shape': 'arrowUp',
            'text': f'ENTRY #{t_ticket}'
        })

        markers_data.append({
            'time': close_ts,
            'position': 'aboveBar' if is_buy else 'belowBar',
            'color': '#00E676' if t_profit > 0 else '#FF1744',
            'shape': 'circle',
            'text': f'EXIT ${t_profit:.2f}'
        })

    markers_data.sort(key=lambda x: x['time'])

    used_times = set()
    for m in markers_data:
        while m['time'] in used_times:
            m['time'] += 1
        used_times.add(m['time'])

    payload = {
        "chart_data": chart_data,
        "volume_data": volume_data,
        "markers_data": markers_data
    }

    compressed_data = zlib.compress(json.dumps(payload).encode('utf-8'), level=3)

    session = BacktestSession.objects.get(id=session_id)
    ChartData.objects.update_or_create(
        session=session,
        defaults={'payload': compressed_data}
    )