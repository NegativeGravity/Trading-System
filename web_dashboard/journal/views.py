from django.shortcuts import render, get_object_or_404
from .models import BacktestSession
import plotly.express as px
import pandas as pd


def dashboard(request):
    sessions = BacktestSession.objects.all().order_by('-created_at')
    return render(request, 'dashboard.html', {
        'sessions': sessions,
        'total_profit': sum(s.net_profit for s in sessions)
    })


def session_detail(request, session_id):
    session = get_object_or_404(BacktestSession, id=session_id)
    trades = session.trades.all().order_by('open_time')

    df = pd.DataFrame(list(session.equity_curve.all().values('timestamp', 'equity')))
    if not df.empty:
        fig = px.line(df, x='timestamp', y='equity', title='Equity Curve')
        fig.update_layout(template='plotly_dark')
        chart = fig.to_html(full_html=False)
    else:
        chart = "No data"

    return render(request, 'session_detail.html', {
        'session': session,
        'trades': trades,
        'chart': chart
    })