from django.urls import path
from .views import (
    ExportInventoryExcelView, ExportInventoryPDFView,
    ExportSalesReportPDFView, ExportSalesExcelView,
    ExportFinancialPDFView, ExportFinancialExcelView
)

urlpatterns = [
    path('inventory/excel/', ExportInventoryExcelView.as_view(), name='export-inventory-excel'),
    path('inventory/pdf/', ExportInventoryPDFView.as_view(), name='export-inventory-pdf'),
    path('sales/pdf/', ExportSalesReportPDFView.as_view(), name='export-sales-pdf'),
    path('sales/excel/', ExportSalesExcelView.as_view(), name='export-sales-excel'),
    path('financial/pdf/', ExportFinancialPDFView.as_view(), name='export-financial-pdf'),
    path('financial/excel/', ExportFinancialExcelView.as_view(), name='export-financial-excel'),
]
