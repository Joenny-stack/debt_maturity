from django.db import models
from django.shortcuts import render

class FinancialData(models.Model):
    company_name = models.CharField(max_length=100)
    report_date = models.DateField()
    revenue = models.BigIntegerField(null=True, blank=True)
    ebitda = models.BigIntegerField(null=True, blank=True)
    operating_profit = models.BigIntegerField(null=True, blank=True)
    net_profit = models.BigIntegerField(null=True, blank=True)
    total_assets = models.BigIntegerField(null=True, blank=True)
    total_liabilities = models.BigIntegerField(null=True, blank=True)
    total_equity = models.BigIntegerField(null=True, blank=True)
    debt_short_term = models.BigIntegerField(null=True, blank=True)
    debt_long_term = models.BigIntegerField(null=True, blank=True)
    cash_equivalents = models.BigIntegerField(null=True, blank=True)
    hyperinflation_adjustment = models.CharField(max_length=10, blank=True, null=True)
    auditor_opinion = models.CharField(max_length=20, blank=True, null=True)
    currency = models.CharField(max_length=10)

    # ➕ New Fields (USD-normalized)
    exchange_rate = models.FloatField(null=True, blank=True)
    normalized_revenue = models.FloatField(null=True, blank=True)
    normalized_total_debt = models.FloatField(null=True, blank=True)
    normalized_total_assets = models.FloatField(null=True, blank=True)
    normalized_net_profit = models.FloatField(null=True, blank=True)
    normalized_debt_short_term = models.FloatField(null=True, blank=True)
    normalized_debt_long_term = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'financial_data'



