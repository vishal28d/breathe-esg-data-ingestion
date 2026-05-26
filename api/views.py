"""
Views for the Breathe ESG API.
"""
import json
import decimal
from datetime import datetime

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    Tenant, Facility, DataImport, RawDataRecord, NormalizedRecord, EmissionFactor
)
from .serializers import (
    TenantSerializer, DataImportSerializer, NormalizedRecordSerializer, EmissionFactorSerializer
)
from .parsers import parse_sap_csv, parse_utility_csv, parse_travel_json
from .sample_travel import SAMPLE_TRAVEL_DATA


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _apply_emission_factor(record: NormalizedRecord):
    """Look up and apply an emission factor for CO2e estimation."""
    if record.normalized_value is None:
        return
    try:
        ef = EmissionFactor.objects.get(
            category=record.category,
            unit=record.normalized_unit
        )
        record.co2e_kg = record.normalized_value * ef.kg_co2e_per_unit
        record.emission_factor_used = ef
    except EmissionFactor.DoesNotExist:
        pass


def _persist_records(import_event: DataImport, parsed_rows: list, tenant: Tenant,
                     plant_code_map: dict = None):
    plant_code_map = plant_code_map or {}
    row_count = 0
    error_count = 0

    for i, (raw_dict, norm_fields, warnings, row_status) in enumerate(parsed_rows):
        raw_record = RawDataRecord.objects.create(
            import_event=import_event,
            row_index=i,
            raw_json=json.dumps(raw_dict, default=str),
        )

        # Bug 8 fix: work on a copy so we don't mutate the original parsed dict,
        # which makes the raw_json stored in RawDataRecord remain accurate.
        fields = dict(norm_fields)
        plant_code = fields.pop('plant_code', '')
        facility_name = fields.pop('facility_name', '')
        facility = None
        if plant_code and plant_code in plant_code_map:
            facility = plant_code_map[plant_code]

        rec = NormalizedRecord(
            import_event=import_event,
            raw_record=raw_record,
            tenant=tenant,
            facility=facility,
            validation_warnings=json.dumps(warnings),
            status=row_status,
            **fields,
        )
        _apply_emission_factor(rec)
        rec.save()

        row_count += 1
        if row_status == 'ERROR':
            error_count += 1

    import_event.row_count = row_count
    import_event.error_count = error_count
    import_event.status = 'DONE'
    import_event.save()


# ---------------------------------------------------------------------------
# Tenant endpoints
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
def tenants(request):
    if request.method == 'GET':
        qs = Tenant.objects.all().order_by('name')
        return Response(TenantSerializer(qs, many=True).data)
    serializer = TenantSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Import history
# ---------------------------------------------------------------------------

@api_view(['GET'])
def imports_list(request):
    tenant_id = request.GET.get('tenant')
    qs = DataImport.objects.select_related('tenant').order_by('-imported_at')
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return Response(DataImportSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Dashboard: normalized records
# ---------------------------------------------------------------------------

@api_view(['GET'])
def records_list(request):
    qs = NormalizedRecord.objects.select_related(
        'tenant', 'facility', 'import_event', 'emission_factor_used'
    ).order_by('-created_at')

    tenant_id = request.GET.get('tenant')
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    scope = request.GET.get('scope')
    if scope:
        qs = qs.filter(scope=scope)
    rec_status = request.GET.get('status')
    if rec_status:
        qs = qs.filter(status=rec_status)
    source_type = request.GET.get('source_type')
    if source_type:
        qs = qs.filter(import_event__source_type=source_type)
    category = request.GET.get('category')
    if category:
        qs = qs.filter(category=category)

    return Response(NormalizedRecordSerializer(qs, many=True).data)


@api_view(['GET', 'PATCH'])
def record_detail(request, pk):
    try:
        record = NormalizedRecord.objects.get(pk=pk)
    except NormalizedRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(NormalizedRecordSerializer(record).data)

    allowed_fields = {'status', 'edit_note', 'co2e_kg', 'normalized_value',
                      'normalized_unit', 'category', 'scope', 'description'}
    for field in allowed_fields:
        if field in request.data:
            setattr(record, field, request.data[field])

    if request.data.get('status') == 'APPROVED':
        record.approved_at = timezone.now()

    record.edited_at = timezone.now()
    record.save()
    return Response(NormalizedRecordSerializer(record).data)


@api_view(['POST'])
def approve_record(request, pk):
    try:
        record = NormalizedRecord.objects.get(pk=pk)
    except NormalizedRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    record.status = 'APPROVED'
    record.approved_at = timezone.now()
    record.save()
    return Response({'status': 'approved', 'id': pk})


@api_view(['POST'])
def bulk_approve(request):
    ids = request.data.get('ids', [])
    updated = NormalizedRecord.objects.filter(pk__in=ids, status='PENDING').update(
        status='APPROVED',
        approved_at=timezone.now(),
    )
    return Response({'approved': updated})


# ---------------------------------------------------------------------------
# Ingest: SAP CSV upload
# ---------------------------------------------------------------------------

@api_view(['POST'])
def ingest_sap(request):
    tenant_id = request.data.get('tenant_id')
    file_obj = request.FILES.get('file')

    if not tenant_id or not file_obj:
        return Response({'error': 'tenant_id and file are required'}, status=400)

    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return Response({'error': 'Tenant not found'}, status=404)

    plant_map = {f.plant_code: f for f in Facility.objects.filter(tenant=tenant) if f.plant_code}

    import_event = DataImport.objects.create(
        tenant=tenant, source_type='SAP', filename=file_obj.name, status='PROCESSING',
    )
    try:
        file_bytes = file_obj.read()
        parsed_rows = parse_sap_csv(file_bytes)
        _persist_records(import_event, parsed_rows, tenant, plant_map)
    except Exception as e:
        import_event.status = 'FAILED'
        import_event.notes = str(e)
        import_event.save()
        return Response({'error': str(e)}, status=500)

    return Response(DataImportSerializer(import_event).data, status=201)


# ---------------------------------------------------------------------------
# Ingest: Utility CSV upload
# ---------------------------------------------------------------------------

@api_view(['POST'])
def ingest_utility(request):
    tenant_id = request.data.get('tenant_id')
    file_obj = request.FILES.get('file')

    if not tenant_id or not file_obj:
        return Response({'error': 'tenant_id and file are required'}, status=400)

    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return Response({'error': 'Tenant not found'}, status=404)

    import_event = DataImport.objects.create(
        tenant=tenant, source_type='UTILITY', filename=file_obj.name, status='PROCESSING',
    )
    try:
        file_bytes = file_obj.read()
        parsed_rows = parse_utility_csv(file_bytes)
        _persist_records(import_event, parsed_rows, tenant)
    except Exception as e:
        import_event.status = 'FAILED'
        import_event.notes = str(e)
        import_event.save()
        return Response({'error': str(e)}, status=500)

    return Response(DataImportSerializer(import_event).data, status=201)


# ---------------------------------------------------------------------------
# Ingest: Corporate Travel (simulated API pull)
# ---------------------------------------------------------------------------

@api_view(['POST'])
def ingest_travel(request):
    tenant_id = request.data.get('tenant_id')
    if not tenant_id:
        return Response({'error': 'tenant_id is required'}, status=400)

    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return Response({'error': 'Tenant not found'}, status=404)

    import_event = DataImport.objects.create(
        tenant=tenant, source_type='TRAVEL', filename='navan_api_pull', status='PROCESSING',
        notes='Simulated Navan API pull. In production: GET /v1/bookings with OAuth2 token.',
    )
    try:
        parsed_rows = parse_travel_json(SAMPLE_TRAVEL_DATA)
        _persist_records(import_event, parsed_rows, tenant)
    except Exception as e:
        import_event.status = 'FAILED'
        import_event.notes = str(e)
        import_event.save()
        return Response({'error': str(e)}, status=500)

    return Response(DataImportSerializer(import_event).data, status=201)


# ---------------------------------------------------------------------------
# Dashboard summary stats
# ---------------------------------------------------------------------------

@api_view(['GET'])
def dashboard_stats(request):
    tenant_id = request.GET.get('tenant')
    qs = NormalizedRecord.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    total = qs.count()
    pending = qs.filter(status='PENDING').count()
    approved = qs.filter(status='APPROVED').count()
    flagged = qs.filter(status='FLAGGED').count()
    error = qs.filter(status='ERROR').count()

    scope_co2e = {}
    for scope_num in [1, 2, 3]:
        # Bug 5 fix: use DB-level aggregation instead of loading all records into Python.
        result = qs.filter(scope=scope_num).aggregate(total=Sum('co2e_kg'))
        scope_co2e[f'scope_{scope_num}'] = float(result['total'] or 0)

    import_qs = DataImport.objects.all()
    if tenant_id:
        import_qs = import_qs.filter(tenant_id=tenant_id)

    return Response({
        'total_records': total,
        'pending': pending,
        'approved': approved,
        'flagged': flagged,
        'error': error,
        'co2e_by_scope': scope_co2e,
        'total_imports': import_qs.count(),
    })


# ---------------------------------------------------------------------------
# Emission factors list
# ---------------------------------------------------------------------------

@api_view(['GET'])
def emission_factors(request):
    qs = EmissionFactor.objects.all().order_by('category')
    return Response(EmissionFactorSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Raw record detail (audit trail)
# ---------------------------------------------------------------------------

@api_view(['GET'])
def raw_record_detail(request, pk):
    try:
        record = NormalizedRecord.objects.get(pk=pk)
    except NormalizedRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if not record.raw_record:
        return Response({'error': 'No raw record linked'}, status=404)

    return Response({
        'row_index': record.raw_record.row_index,
        'raw_json': json.loads(record.raw_record.raw_json),
        'created_at': record.raw_record.created_at,
    })
