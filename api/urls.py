from django.urls import path
from . import views

urlpatterns = [
    # Tenants
    path('tenants/', views.tenants),

    # Imports
    path('imports/', views.imports_list),

    # Ingestion
    path('ingest/sap/', views.ingest_sap),
    path('ingest/utility/', views.ingest_utility),
    path('ingest/travel/', views.ingest_travel),

    # Records — static paths MUST come before <int:pk> patterns (Bug 1 fix)
    path('records/', views.records_list),
    path('records/bulk-approve/', views.bulk_approve),   # static before dynamic
    path('records/<int:pk>/', views.record_detail),
    path('records/<int:pk>/approve/', views.approve_record),
    path('records/<int:pk>/raw/', views.raw_record_detail),

    # Stats
    path('stats/', views.dashboard_stats),

    # Emission factors
    path('emission-factors/', views.emission_factors),
]
