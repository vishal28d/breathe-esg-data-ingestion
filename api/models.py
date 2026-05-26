"""
Data models for Breathe ESG ingestion platform.

Key design decisions:
- Multi-tenancy via Tenant FK on all data rows (row-level isolation).
- RawDataRecord stores original source bytes for audit trail.
- NormalizedRecord is the analyst-facing, normalized row.
- EmissionFactor is a lookup table keyed by (category, unit) -> kg CO2e.
- Scope 1/2/3 is an explicit field, not inferred, to avoid logic drift.
- Status drives the review workflow: PENDING -> APPROVED or FLAGGED.
"""
from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """Represents a client company ingesting data."""
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Facility(models.Model):
    """A physical site belonging to a tenant. Used to map plant codes for SAP."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='facilities')
    name = models.CharField(max_length=255)
    # SAP plant code as-is — e.g. "WERK_001"
    plant_code = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.tenant.name} / {self.name}"


class EmissionFactor(models.Model):
    """
    Lookup table: (category, unit) -> kg_co2e_per_unit.
    Sources: DEFRA 2023, EPA eGRID, IPCC AR6 for flights.
    """
    category = models.CharField(max_length=100)  # e.g. "diesel", "electricity_uk", "flight_economy"
    unit = models.CharField(max_length=50)        # e.g. "litres", "kWh", "km"
    kg_co2e_per_unit = models.DecimalField(max_digits=12, decimal_places=6)
    source = models.CharField(max_length=255)

    class Meta:
        # Bug 10 fix: prevent duplicate (category, unit) pairs which would cause
        # MultipleObjectsReturned in _apply_emission_factor().
        unique_together = [['category', 'unit']]

    def __str__(self):
        return f"{self.category} / {self.unit} -> {self.kg_co2e_per_unit} kg CO2e"


class DataImport(models.Model):
    """
    One upload/pull event. Provides lineage: where did this batch of rows come from?
    """
    SOURCE_CHOICES = [
        ('SAP', 'SAP Flat File'),
        ('UTILITY', 'Utility Portal CSV'),
        ('TRAVEL', 'Corporate Travel API'),
    ]
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='imports')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    filename = models.CharField(max_length=512, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSING')
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source_type} import at {self.imported_at:%Y-%m-%d %H:%M} ({self.status})"


class RawDataRecord(models.Model):
    """
    Immutable store of what actually arrived.
    Stored as JSON string — we never modify this after write.
    This is the source-of-truth for audit purposes.
    """
    import_event = models.ForeignKey(DataImport, on_delete=models.CASCADE, related_name='raw_records')
    row_index = models.IntegerField()  # Row number in the original file
    raw_json = models.TextField()      # JSON-serialized original row dict
    created_at = models.DateTimeField(auto_now_add=True)


class NormalizedRecord(models.Model):
    """
    The parsed, unit-normalized, validated row.
    Analysts interact with this model.
    Edits here are tracked via `edited_by` / `edit_note` — the raw record remains untouched.
    """
    SCOPE_CHOICES = [
        (1, 'Scope 1 – Direct'),
        (2, 'Scope 2 – Purchased Energy'),
        (3, 'Scope 3 – Value Chain'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('FLAGGED', 'Flagged / Suspicious'),
        ('ERROR', 'Error – Could Not Parse'),
    ]

    import_event = models.ForeignKey(DataImport, on_delete=models.CASCADE, related_name='records')
    raw_record = models.OneToOneField(
        RawDataRecord, null=True, blank=True, on_delete=models.SET_NULL
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='records')
    facility = models.ForeignKey(
        Facility, null=True, blank=True, on_delete=models.SET_NULL
    )

    # Categorization
    scope = models.IntegerField(choices=SCOPE_CHOICES, null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)  # e.g. "diesel", "electricity", "flight"
    sub_category = models.CharField(max_length=100, blank=True)  # e.g. "economy_class"

    # Activity data — normalized to a single value + unit
    activity_date_start = models.DateField(null=True, blank=True)
    activity_date_end = models.DateField(null=True, blank=True)
    original_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    original_unit = models.CharField(max_length=50, blank=True)
    normalized_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    normalized_unit = models.CharField(max_length=50, blank=True)  # always SI: litres, kWh, km

    # Computed emission estimate (best effort at ingest time)
    co2e_kg = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    emission_factor_used = models.ForeignKey(
        EmissionFactor, null=True, blank=True, on_delete=models.SET_NULL
    )

    # Description / notes from source
    description = models.TextField(blank=True)

    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    validation_warnings = models.TextField(blank=True)  # JSON array of warning strings
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='approved_records'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    edit_note = models.TextField(blank=True)  # Analyst can leave a note when editing
    edited_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='edited_records'
    )
    edited_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} | {self.activity_date_start} | {self.normalized_value} {self.normalized_unit} | {self.status}"
