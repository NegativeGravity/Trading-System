import sys
import zlib
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse

PROJECT_ROOT = r"G:\Trading-System"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from .models import BacktestSession, ChartData

def dashboard(request):
    sessions = BacktestSession.objects.all().order_by('-created_at')
    return render(request, 'journal/dashboard.html', {'sessions': sessions})

def session_detail(request, session_id):
    session = get_object_or_404(BacktestSession, pk=session_id)
    trades = session.trades.all().order_by('open_time')
    return render(request, 'journal/session_detail.html', {
        'session': session,
        'trades': trades
    })

def session_chart_data(request, session_id):
    try:
        chart_obj = ChartData.objects.get(session_id=session_id)
        payload_bytes = bytes(chart_obj.payload)
        raw_json_bytes = zlib.decompress(payload_bytes)
        return HttpResponse(raw_json_bytes, content_type='application/json')
    except ChartData.DoesNotExist:
        return JsonResponse({"chart_data": [], "volume_data": [], "markers_data": []})
    except Exception as e:
        import traceback
        print(f"❌ API Error: {e}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)