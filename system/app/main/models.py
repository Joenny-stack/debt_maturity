from django.db import models

class FinancialData(models.Model):
    total_debt = models.DecimalField(max_digits=15, decimal_places=2)
    inflation_rate = models.DecimalField(max_digits=5, decimal_places=2)
    earnings_quality = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"FinancialData({self.total_debt}, {self.inflation_rate}, {self.earnings_quality})"
