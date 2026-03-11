from django.urls import path

from . import views

urlpatterns = [
    path("storefront/inventory/", views.inventory_list, name="inventory-list"),
    path("storefront/sales/", views.sales_list, name="sales-list"),
]
