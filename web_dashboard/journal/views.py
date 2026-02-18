import sys
PROJECT_ROOT = r"G:\Trading-System"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from django.shortcuts import render, get_object_or_404
from django.utils.timezone import make_aware, is_naive
from .models import BacktestSession
from trader.executor.mt5_executor import MT5Executor
from trader.domain.models import Candle
import datetime
import json


def dashboard(request):
    sessions = BacktestSession.objects.all().order_by('-created_at')
    return render(request, 'journal/dashboard.html', {'sessions': sessions})


def session_detail(request, session_id):
    session = get_object_or_404(BacktestSession, pk=session_id)
    trades = session.trades.all().order_by('open_time')
    equity_curve = session.equity_curve.all().order_by('timestamp')

    chart_data = []
    volume_data = []
    markers_data = []

    mt5 = MT5Executor()

    if mt5.connect():
        start_buffer = session.start_date - datetime.timedelta(hours=4)
        end_buffer = session.end_date + datetime.timedelta(hours=4)
        duration_minutes = (end_buffer - start_buffer).total_seconds() / 60
        count = int(duration_minutes) + 1440

        raw_data = mt5.get_historical_data_as_dict(session.symbol, 1, count=count)

        if raw_data:
            for d in raw_data:
                c = Candle(symbol=session.symbol, **d)
                if is_naive(c.timestamp):
                    c.timestamp = make_aware(c.timestamp)

                if start_buffer <= c.timestamp <= end_buffer:
                    ts = int(c.timestamp.timestamp())

                    chart_data.append({
                        'time': ts,
                        'open': c.open,
                        'high': c.high,
                        'low': c.low,
                        'close': c.close
                    })

                    # داده حجم
                    color = '#26a69a' if c.close >= c.open else '#ef5350'
                    volume_data.append({
                        'time': ts,
                        'value': c.volume,
                        'color': color
                    })

        mt5.shutdown()

    for t in trades:
        entry_ts = int(t.open_time.timestamp())
        is_buy = t.direction == 'BUY'

        markers_data.append({
            'time': entry_ts,
            'position': 'belowBar' if is_buy else 'aboveBar',
            'color': '#2196F3' if is_buy else '#FF6D00',
            'shape': 'arrowUp' if is_buy else 'arrowDown',
            'text': f'ENTRY #{t.ticket}'
        })

        exit_ts = int(t.close_time.timestamp())
        win = t.net_profit > 0
        markers_data.append({
            'time': exit_ts,
            'position': 'aboveBar' if is_buy else 'belowBar',
            'color': '#00E676' if win else '#FF1744',
            'shape': 'circle',
            'text': f'EXIT ${t.net_profit:.2f}'
        })

    markers_data.sort(key=lambda x: x['time'])

    context = {
        'session': session,
        'trades': trades,
        'equity_curve': equity_curve,
        'chart_data_json': json.dumps(chart_data),
        'volume_data_json': json.dumps(volume_data),
        'markers_data_json': json.dumps(markers_data),
    }
    return render(request, 'journal/session_detail.html', context)