from django.contrib import admin
from .models import Tenant, Facility, DataImport, RawDataRecord, NormalizedRecord, EmissionFactor


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    search_fields = ['name']


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'name', 'plant_code', 'location']
    list_filter = ['tenant']


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['category', 'unit', 'kg_co2e_per_unit', 'source']
    list_filter = ['category']


@admin.register(DataImport)
class DataImportAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'source_type', 'imported_at', 'status', 'row_count', 'error_count']
    list_filter = ['source_type', 'status', 'tenant']


@admin.register(NormalizedRecord)
class NormalizedRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'scope', 'category', 'activity_date_start',
                    'normalized_value', 'normalized_unit', 'co2e_kg', 'status']
    list_filter = ['scope', 'status', 'category', 'tenant']
    search_fields = ['description', 'category']


@admin.register(RawDataRecord)
class RawDataRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'import_event', 'row_index', 'created_at']
    list_filter = ['import_event__source_type']
