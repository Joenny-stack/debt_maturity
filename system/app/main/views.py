from django.shortcuts import render
from .models import FinancialData
from django.db.models import Sum
import pandas as pd
import json
from scipy.stats import spearmanr

def financials_view(request):
    # 1. Filters
    companies = FinancialData.objects.values_list('company_name', flat=True).distinct()
    years = sorted(set(fd.report_date.year for fd in FinancialData.objects.all()))
    selected_company = request.GET.get('company', None)
    selected_year = request.GET.get('year', None)
    opinion_filter = request.GET.get('opinion', None)

    # 2. Filtered queryset
    financial_data = FinancialData.objects.all().order_by('report_date')
    if selected_company:
        financial_data = financial_data.filter(company_name=selected_company)
    if selected_year:
        financial_data = financial_data.filter(report_date__year=selected_year)
    if opinion_filter == "problematic":
        financial_data = financial_data.filter(
            auditor_opinion__in=["qualified", "adverse", "Adverse Conclusion"]
        )

    # 3. Debt ratio & opinion scoring
    score_map = {
        "unqualified": 0,
        "qualified": 1,
        "disclaimer": 2,
        "adverse": 3,
        "adverse conclusion": 3,
    }

    scores = []
    opinion_counts = {k: 0 for k in score_map.keys()}
    opinion_counts["Other"] = 0

    for f in financial_data:
        total_debt = (f.debt_short_term or 0) + (f.debt_long_term or 0)
        f.debt_ratio = total_debt / f.total_assets if f.total_assets else 0

        opinion = f.auditor_opinion.strip().lower() if f.auditor_opinion else None
        score = score_map.get(opinion)
        f.opinion_score = score
        if score is not None:
            scores.append(score)
            opinion_counts[opinion] += 1
        else:
            opinion_counts["Other"] += 1

    avg_opinion_score = round(sum(scores) / len(scores), 2) if scores else None

    # 4. Chart data
    debt_data = list(financial_data.values(
        'company_name', 'report_date', 'normalized_debt_short_term', 'normalized_debt_long_term'
    ))
    debt_data_json = json.dumps(debt_data, default=str)

    # 5. Correlation and scatter plot data
    correlation_comment = "Not enough data"
    correlation_result = None
    correlation_method = "Spearman"
    scatter_data = []

    valid = financial_data.exclude(
        debt_short_term=None,
        debt_long_term=None,
        total_assets=None,
        auditor_opinion=None
    )

    df = pd.DataFrame()
    if valid.exists():
        df = pd.DataFrame.from_records(valid.values(
            "debt_short_term", "debt_long_term", "total_assets", "auditor_opinion"
        ))

    if not df.empty:
        df["debt_ratio"] = (df["debt_short_term"].astype(float) + df["debt_long_term"].astype(float)) / df["total_assets"].astype(float)
        df["opinion_score"] = df["auditor_opinion"].str.strip().str.lower().map(score_map)
        df = df.dropna(subset=["debt_ratio", "opinion_score"])

        if len(df) >= 3:
            corr, pval = spearmanr(df["debt_ratio"], df["opinion_score"])
            correlation_result = {"correlation": round(corr, 3), "p_value": round(pval, 4)}

            if pval > 0.05:
                correlation_comment = "⚠️ No statistically significant relationship"
            elif abs(corr) < 0.2:
                correlation_comment = "🔍 Very weak relationship"
            elif abs(corr) < 0.4:
                correlation_comment = "🟡 Weak relationship"
            elif abs(corr) < 0.6:
                correlation_comment = "🟠 Moderate correlation"
            else:
                correlation_comment = "🔴 Strong correlation"

        scatter_data = df[["debt_ratio", "opinion_score"]].to_dict(orient="records")

    # 6. Summary metrics
    total_debt = financial_data.aggregate(
        total=Sum('debt_short_term') + Sum('debt_long_term')
    )['total'] or 0
    inflation_rate = "RBZ data needed"
    earnings_quality = financial_data.filter(auditor_opinion__iexact='unqualified').count()

    # 7. Context
    context = {
        "companies": companies,
        "years": years,
        "selected_company": selected_company,
        "selected_year": selected_year,
        "opinion_filter": opinion_filter,
        "total_debt": f"{total_debt:,}",
        "inflation_rate": inflation_rate,
        "earnings_quality": earnings_quality,
        "financial_data": financial_data,
        "debt_data": debt_data,
        "debt_data_json": debt_data_json,
        "avg_opinion_score": avg_opinion_score,
        "opinion_counts_json": json.dumps(opinion_counts),
        "correlation_result": correlation_result,
        "correlation_comment": correlation_comment,
        "correlation_method": correlation_method,
        "scatter_data_json": json.dumps(scatter_data),
    }

    return render(request, "main/index.html", context)
