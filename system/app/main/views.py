from django.shortcuts import render
from .models import FinancialData
from django.db.models import Sum
import json

def financials_view(request):
    # Fetch all companies and distinct years for the dropdown filters
    companies = FinancialData.objects.values_list('company_name', flat=True).distinct()
    # years = FinancialData.objects.dates('report_date', 'year', order='DESC').values_list('year', flat=True)
    years = sorted(set(fd.report_date.year for fd in FinancialData.objects.all()))

    # Get selected filters from request
    selected_company = request.GET.get('company', None)
    selected_year = request.GET.get('year', None)

    # Start with all data
    financial_data = FinancialData.objects.all().order_by('report_date')

    # Apply filters
    if selected_company:
        financial_data = financial_data.filter(company_name=selected_company)
    if selected_year:
        financial_data = financial_data.filter(report_date__year=selected_year)

    for f in financial_data:
        total_debt = (f.debt_short_term or 0) + (f.debt_long_term or 0)
        f.debt_ratio = total_debt / f.total_assets if f.total_assets else 0
    
    # Aggregate metrics
    total_debt = financial_data.aggregate(
        total=Sum('debt_short_term') + Sum('debt_long_term')
    )['total'] or 0

    inflation_rate = "RBZ data needed"
    earnings_quality = financial_data.filter(auditor_opinion__iexact='unqualified').count()

    # Chart data
    debt_data = list(financial_data.values(
        'company_name',
        'report_date',
        'normalized_debt_short_term',
        'normalized_debt_long_term'
    ))

    # debt_data_json = json.dumps(debt_data, default=str) if debt_data else '[]'

    debt_data_json = json.dumps(debt_data, default=str) if debt_data else '[]'

    # Final context
    context = {
        "companies": companies,
        "years": years,
        "selected_company": selected_company,
        "selected_year": selected_year,
        "total_debt": f"{total_debt:,}",
        "inflation_rate": inflation_rate,
        "earnings_quality": earnings_quality,
        "financial_data": financial_data,
        "debt_data": debt_data,
        "debt_data_json": debt_data_json,
    }

    return render(request, "main/index.html", context)
