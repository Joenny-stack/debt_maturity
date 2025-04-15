from django.shortcuts import render
from .models import FinancialData  # Example model

def index(request):
    data = FinancialData.objects.first()  # Fetch example data
    if data is None:
        context = {
            'total_debt': 'No data available',
            'inflation_rate': 'No data available',
            'earnings_quality': 'No data available'
        }
    else:
        context = {
            'total_debt': data.total_debt,
            'inflation_rate': data.inflation_rate,
            'earnings_quality': data.earnings_quality
        }
    return render(request, 'main/index.html', context)
