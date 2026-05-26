"""
Serializers for the Breathe ESG REST API.
"""
from rest_framework import serializers
from .models import Tenant, Facility, DataImport, NormalizedRecord, EmissionFactor


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'created_at']


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ['id', 'tenant', 'name', 'plant_code', 'location']


class DataImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImport
        fields = ['id', 'tenant', 'source_type', 'filename', 'imported_at',
                  'status', 'row_count', 'error_count', 'notes']


class NormalizedRecordSerializer(serializers.ModelSerializer):
    import_source = serializers.CharField(source='import_event.source_type', read_only=True)
    import_filename = serializers.CharField(source='import_event.filename', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True, allow_null=True)

    class Meta:
        model = NormalizedRecord
        fields = [
            'id', 'import_event', 'import_source', 'import_filename',
            'tenant', 'tenant_name', 'facility', 'facility_name',
            'scope', 'category', 'sub_category',
            'activity_date_start', 'activity_date_end',
            'original_value', 'original_unit',
            'normalized_value', 'normalized_unit',
            'co2e_kg', 'description',
            'status', 'validation_warnings',
            'approved_by', 'approved_at',
            'edit_note', 'edited_at',
            'created_at',
        ]
        read_only_fields = ['id', 'import_event', 'import_source', 'import_filename',
                            'tenant_name', 'facility_name', 'created_at']


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = ['id', 'category', 'unit', 'kg_co2e_per_unit', 'source']
