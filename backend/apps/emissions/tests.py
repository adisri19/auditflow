import threading
from decimal import Decimal
from datetime import date
from django.test import TransactionTestCase
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import connection
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.tenants.models import Tenant, User
from apps.ingestion.models import IngestionBatch, RawRow
from apps.emissions.models import ActivityRecord
from apps.emissions.views.workflow import RecordApproveView, RecordLockView
from apps.ingestion.parsers.sap import parse_sap_file
from apps.ingestion.parsers.utility import parse_utility_csv, split_billing_period
from apps.ingestion.parsers.travel import parse_travel_csv, haversine_km

class BreatheESGTestCase(TransactionTestCase):
    def setUp(self):
        # Create Tenants
        self.tenant_a = Tenant.objects.create(name="Tenant A", slug="tenant-a")
        self.tenant_b = Tenant.objects.create(name="Tenant B", slug="tenant-b")

    def test_multi_tenancy_isolation(self):
        # Create record for Tenant A
        batch_a = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        record_a = ActivityRecord.objects.create(
            tenant=self.tenant_a,
            batch=batch_a,
            scope=1,
            category="FUEL_COMBUSTION",
            activity_date=date(2024, 1, 1),
            quantity=Decimal("100.0"),
            unit="L",
            source_system="SAP"
        )

        # Create record for Tenant B
        batch_b = IngestionBatch.objects.create(tenant=self.tenant_b, source_type="SAP_FUEL_PROC")
        record_b = ActivityRecord.objects.create(
            tenant=self.tenant_b,
            batch=batch_b,
            scope=3,
            category="PROCUREMENT",
            activity_date=date(2024, 1, 1),
            quantity=Decimal("200.0"),
            unit="kg",
            source_system="SAP"
        )

        # Query and assert isolation
        records_a = ActivityRecord.objects.filter(tenant=self.tenant_a)
        records_b = ActivityRecord.objects.filter(tenant=self.tenant_b)

        self.assertEqual(records_a.count(), 1)
        self.assertEqual(records_a[0].id, record_a.id)

        self.assertEqual(records_b.count(), 1)
        self.assertEqual(records_b[0].id, record_b.id)

    def test_locked_record_immutability(self):
        batch = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        record = ActivityRecord.objects.create(
            tenant=self.tenant_a,
            batch=batch,
            scope=1,
            category="FUEL_COMBUSTION",
            activity_date=date(2024, 1, 1),
            quantity=Decimal("50.0"),
            unit="L",
            status="PENDING",
            source_system="SAP"
        )

        # Transition to APPROVED, then LOCKED
        record.status = "APPROVED"
        record.save()

        record.status = "LOCKED"
        record.save()

        # Try to modify fields on locked record and save
        record.quantity = Decimal("100.0")
        with self.assertRaises(ValidationError):
            record.save()

    def test_sap_parser(self):
        batch = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        sap_content = (
            "WERKS\tBLDAT\tMENGE\tMEINS\tBKTXT\tMATNR\n"
            "IN01\t20240115\t100\tGAL\tDiesel IN01\tDIESEL-01\n"
            "IN02\t20240212\t200\tL\tDiesel IN02\tDIESEL-01\n"
            "IN01\t20240320\t500\tPCS\tUnrecognized unit\tDIESEL-01\n"
        )
        file_obj = ContentFile(sap_content.encode('utf-8'))
        file_obj.name = "sap_test.txt"

        parse_sap_file(file_obj, batch)

        # Assertions
        self.assertEqual(batch.row_count, 3)
        self.assertEqual(batch.error_count, 1)  # PCS row fails
        self.assertEqual(batch.status, "DONE")

        records = ActivityRecord.objects.filter(batch=batch)
        self.assertEqual(records.count(), 2)

        # Gallon conversion check: 100 GAL * 3.78541 = 378.541 L
        rec1 = records.get(facility_code="IN01")
        self.assertAlmostEqual(float(rec1.quantity), 378.541)
        self.assertEqual(rec1.unit, "L")
        self.assertEqual(rec1.scope, 1)

    def test_utility_parser_day_split(self):
        # 1. Test splitting function directly
        start = date(2024, 1, 15)
        end = date(2024, 2, 14)
        splits = split_billing_period(start, end, Decimal("310.0"), Decimal("620.0"))

        # Jan 15-31: 17 days
        # Feb 1-14: 14 days
        # Total days: 31
        self.assertEqual(len(splits), 2)
        self.assertEqual(splits[0]["start"], date(2024, 1, 15))
        self.assertEqual(splits[0]["end"], date(2024, 1, 31))
        self.assertEqual(splits[0]["qty"], Decimal("170.0"))
        self.assertEqual(splits[0]["cost"], Decimal("340.0"))

        self.assertEqual(splits[1]["start"], date(2024, 2, 1))
        self.assertEqual(splits[1]["end"], date(2024, 2, 14))
        self.assertEqual(splits[1]["qty"], Decimal("140.0"))
        self.assertEqual(splits[1]["cost"], Decimal("280.0"))

    def test_travel_parser(self):
        batch = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="CORP_TRAVEL")
        travel_content = (
            "Trip ID,Traveller Name,Traveller Email,Booking Date,Travel Date,Segment Type,Origin,Destination,Origin IATA,Destination IATA,Duration,Distance,Class,Cost,Currency,Carbon\n"
            "TR1,John,j@d.com,20240101,20240105,FLIGHT,Mumbai,London,BOM,LHR,,7200,ECONOMY,800,USD,\n"
            "TR2,Jane,ja@d.com,20240101,20240106,FLIGHT,Delhi,New York,DEL,JFK,,,BUSINESS,3000,USD,\n"  # Haversine fallback
            "TR3,John,j@d.com,20240101,20240107,HOTEL,London,,,,3,,,400,GBP,\n"
        )
        file_obj = ContentFile(travel_content.encode('utf-8'))
        file_obj.name = "travel_test.csv"

        parse_travel_csv(file_obj, batch)

        self.assertEqual(batch.row_count, 3)
        self.assertEqual(batch.error_count, 0)

        # Distance fallback check (DEL->JFK)
        # DEL coordinates: (28.5562, 77.1000)
        # JFK coordinates: (40.6413, -73.7781)
        records = ActivityRecord.objects.filter(batch=batch)
        self.assertEqual(records.count(), 3)

        rec_flight_haversine = records.get(source_row_id="TR2")
        self.assertTrue(rec_flight_haversine.quantity > 11000)
        self.assertEqual(rec_flight_haversine.unit, "km")

        # Hotel record
        rec_hotel = records.get(source_row_id="TR3")
        self.assertEqual(rec_hotel.quantity, 3)
        self.assertEqual(rec_hotel.unit, "night")
        self.assertEqual(rec_hotel.co2e_kg, 3 * Decimal("31.2"))

    # === TASK 6 TESTS ===

    def test_unknown_iata_code_sets_parse_error(self):
        batch = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="CORP_TRAVEL")
        travel_content = (
            "Trip ID,Traveller Name,Traveller Email,Booking Date,Travel Date,Segment Type,Origin,Destination,Origin IATA,Destination IATA,Duration,Distance,Class,Cost,Currency,Carbon\n"
            "TR_UNKNOWN,Alice,a@example.com,20240101,20240105,FLIGHT,Unknown,Unknown,ZZZ,YYY,,,,,USD,\n"
        )
        file_obj = ContentFile(travel_content.encode('utf-8'))
        file_obj.name = "travel_unknown.csv"

        parse_travel_csv(file_obj, batch)

        self.assertEqual(batch.row_count, 1)
        self.assertEqual(batch.error_count, 1)
        raw_row = RawRow.objects.get(batch=batch, row_index=1)
        self.assertTrue(bool(raw_row.parse_error))
        self.assertIn("Could not calculate Haversine distance", raw_row.parse_error)
        self.assertEqual(ActivityRecord.objects.filter(batch=batch).count(), 0)

    def test_sap_invalid_unit_sets_parse_error(self):
        batch = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        sap_content = (
            "WERKS\tBLDAT\tMENGE\tMEINS\tBKTXT\tMATNR\n"
            "IN01\t20240115\t100\tINVALID_UNIT\tDiesel IN01\tDIESEL-01\n"
        )
        file_obj = ContentFile(sap_content.encode('utf-8'))
        file_obj.name = "sap_invalid.txt"

        parse_sap_file(file_obj, batch)

        self.assertEqual(batch.row_count, 1)
        self.assertEqual(batch.error_count, 1)
        raw_row = RawRow.objects.get(batch=batch, row_index=1)
        self.assertTrue(bool(raw_row.parse_error))
        self.assertIn("Unsupported unit", raw_row.parse_error)
        self.assertEqual(ActivityRecord.objects.filter(batch=batch).count(), 0)

    def test_billing_period_proration_splits_correctly(self):
        start = date(2024, 1, 15)
        end = date(2024, 2, 14)
        total_qty = Decimal("310.0")
        total_cost = Decimal("620.0")
        splits = split_billing_period(start, end, total_qty, total_cost)

        # 31 total days: 17 in Jan, 14 in Feb
        self.assertEqual(len(splits), 2)
        self.assertEqual(splits[0]["start"], date(2024, 1, 15))
        self.assertEqual(splits[0]["end"], date(2024, 1, 31))
        self.assertEqual(splits[0]["qty"], Decimal("170.0"))
        self.assertEqual(splits[0]["cost"], Decimal("340.0"))

        self.assertEqual(splits[1]["start"], date(2024, 2, 1))
        self.assertEqual(splits[1]["end"], date(2024, 2, 14))
        self.assertEqual(splits[1]["qty"], Decimal("140.0"))
        self.assertEqual(splits[1]["cost"], Decimal("280.0"))

        self.assertEqual(splits[0]["qty"] + splits[1]["qty"], total_qty)
        self.assertEqual(splits[0]["cost"] + splits[1]["cost"], total_cost)

    def test_duplicate_source_hash_not_double_ingested(self):
        batch1 = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        sap_content = (
            "WERKS\tBLDAT\tMENGE\tMEINS\tBKTXT\tMATNR\n"
            "IN01\t20240115\t100\tL\tDiesel IN01\tDIESEL-01\n"
        )
        file1 = ContentFile(sap_content.encode('utf-8'))
        file1.name = "sap1.txt"
        parse_sap_file(file1, batch1)

        records_first_ingest = ActivityRecord.objects.filter(tenant=self.tenant_a)
        self.assertEqual(records_first_ingest.count(), 1)
        original_hash = records_first_ingest.first().source_hash
        self.assertTrue(bool(original_hash))

        # Re-ingest exact same row into a second batch
        batch2 = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        file2 = ContentFile(sap_content.encode('utf-8'))
        file2.name = "sap2.txt"
        parse_sap_file(file2, batch2)

        # Assert no duplicate record created
        records_after_second = ActivityRecord.objects.filter(tenant=self.tenant_a)
        self.assertEqual(records_after_second.count(), 1)

    def test_lock_rejected_without_co2e(self):
        user = User.objects.create_user(username="auditor_test", tenant=self.tenant_a)
        batch = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        record = ActivityRecord.objects.create(
            tenant=self.tenant_a,
            batch=batch,
            scope=1,
            category="FUEL_COMBUSTION",
            activity_date=date(2024, 1, 1),
            quantity=Decimal("100.0"),
            unit="L",
            co2e_kg=None,  # Null co2e_kg
            status="APPROVED",
            source_system="SAP"
        )

        factory = APIRequestFactory()
        request = factory.post(f"/api/v1/records/{record.id}/lock/", {}, format='json')
        request.tenant = self.tenant_a
        force_authenticate(request, user=user)

        response = RecordLockView.as_view()(request, pk=record.id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('detail'), "co2e_kg must be set and greater than zero before locking")
        record.refresh_from_db()
        self.assertEqual(record.status, "APPROVED")

    def test_concurrent_approve_race_condition(self):
        user = User.objects.create_user(username="approver_concurrent", tenant=self.tenant_a)
        batch = IngestionBatch.objects.create(tenant=self.tenant_a, source_type="SAP_FUEL_PROC")
        record = ActivityRecord.objects.create(
            tenant=self.tenant_a,
            batch=batch,
            scope=1,
            category="FUEL_COMBUSTION",
            activity_date=date(2024, 1, 1),
            quantity=Decimal("50.0"),
            unit="L",
            co2e_kg=Decimal("134.0"),
            status="PENDING",
            source_system="SAP"
        )

        errors = []
        status_codes = []

        def worker():
            try:
                factory = APIRequestFactory()
                request = factory.post(f"/api/v1/records/{record.id}/approve/", {"review_notes": "approved by thread"}, format='json')
                request.tenant = self.tenant_a
                force_authenticate(request, user=user)
                response = RecordApproveView.as_view()(request, pk=record.id)
                status_codes.append(response.status_code)
            except Exception as e:
                # Capture any IntegrityError or unexpected crash
                errors.append(e)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert no integrity error is raised
        integrity_errors = [e for e in errors if isinstance(e, ValidationError) or "IntegrityError" in type(e).__name__]
        self.assertEqual(len(integrity_errors), 0, f"Integrity error raised: {integrity_errors}")
        record.refresh_from_db()
        self.assertEqual(record.status, "APPROVED")
