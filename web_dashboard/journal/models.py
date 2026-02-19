from django.db import models

class BacktestSession(models.Model):
    agent_name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    timeframe = models.CharField(max_length=10)
    initial_balance = models.FloatField()
    spread_points = models.FloatField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    final_balance = models.FloatField()
    net_profit = models.FloatField()
    win_rate = models.FloatField()
    max_drawdown_percent = models.FloatField()
    max_drawdown_amount = models.FloatField()
    total_trades = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class Trade(models.Model):
    session = models.ForeignKey(BacktestSession, on_delete=models.CASCADE, related_name='trades')
    ticket = models.IntegerField()
    direction = models.CharField(max_length=10)
    entry_price = models.FloatField()
    exit_price = models.FloatField()
    sl = models.FloatField(default=0.0)
    tp = models.FloatField(default=0.0)
    volume = models.FloatField()
    gross_profit = models.FloatField()
    net_profit = models.FloatField()
    open_time = models.DateTimeField()
    close_time = models.DateTimeField()
    duration_minutes = models.FloatField()
    entry_reason = models.CharField(max_length=255, null=True, blank=True)
    exit_reason = models.CharField(max_length=255, null=True, blank=True)

class EquityPoint(models.Model):
    session = models.ForeignKey(BacktestSession, on_delete=models.CASCADE, related_name='equity_curve')
    timestamp = models.DateTimeField()
    balance = models.FloatField()
    equity = models.FloatField()
    drawdown_percent = models.FloatField()

class ChartData(models.Model):
    session = models.OneToOneField(BacktestSession, on_delete=models.CASCADE, related_name='chart_data_cache')
    payload = models.BinaryField()