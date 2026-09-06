import io
import uuid
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.tenants.models import Tenant
from apps.ingestion.models import IngestionBatch, RawRow
from apps.emissions.models import ActivityRecord
from apps.audit.models import AuditLog
from apps.ingestion.parsers.sap import parse_sap_file
from apps.ingestion.parsers.utility import parse_utility_csv
from apps.ingestion.parsers.travel import parse_travel_csv

class Command(BaseCommand):
    help = "Seeds demo tenant, superuser, and mock ingestion batch data for Breathe ESG."

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        # 1. Clear database
        AuditLog.objects.all().delete()
        ActivityRecord.objects.all().delete()
        RawRow.objects.all().delete()
        IngestionBatch.objects.all().delete()
        User = get_user_model()
        User.objects.all().delete()
        Tenant.objects.all().delete()

        self.stdout.write("Database cleared.")

        # 2. Create Demo Tenant
        tenant = Tenant.objects.create(
            name="Demo Corp",
            slug="demo-corp"
        )
        self.stdout.write(f"Tenant '{tenant.name}' created.")

        # 3. Create Superuser
        admin_user = User.objects.create_superuser(
            username="admin@demo.com",
            email="admin@demo.com",
            password="breathe2024",
            tenant=tenant
        )
        self.stdout.write("Superuser 'admin@demo.com' created with password 'breathe2024'.")

        # 4. Generate & Parse SAP Batch (Tab-Delimited)
        sap_data = (
            "WERKS\tBLDAT\tMENGE\tMEINS\tBKTXT\tMATNR\n"
            "IN01\t20240115\t500\tL\tDiesel Fuel IN01\tDIESEL-01\n"
            "IN01\t12.02.2024\t120\tGAL\tDiesel Fuel IN01\tDIESEL-01\n"
            "IN02\t20240228\t800\tL\tDiesel Fuel IN02\tDIESEL-01\n"
            "IN02\t10.03.2024\t150\tGAL\tDiesel Fuel IN02\tDIESEL-01\n"
            "IN01\t20240315\t5000\tKG\tSteel Coil Procurement\tSTEEL-COIL-1\n"
            "IN01\t20.04.2024\t12000\tG\tSmall steel parts\tSTEEL-02\n"
            "IN02\t20240415\t3\tT\tStructural Steel plant construction\tSTEEL-01\n"
            "IN01\t20240505\t10\tM3\tNatural Gas supply\tNATGAS-01\n"
            "IN02\t12.05.2024\t400\tL\tPetrol for generator\tPETROL-01\n"
            "IN01\t20240601\t1000\tKWH\tDiesel backup power\tDIESEL-01\n"
            "IN02\t20240615\t2.5\tMWH\tCo-generation gas power\tNATGAS-02\n"
            "IN01\t20240710\t500\tPCS\tOffice Chairs\tOFFICE-FURN\n"  # Fails
            "IN01\t20240715\t600\tL\tKerosene storage\tKEROSENE-01\n"
            "IN02\t20240820\t50\tGAL\tLPG cylinder replenishment\tLPG-02\n"
            "IN01\t20240825\t2000\tKG\tAluminum sheets\tALUM-01\n"
            "IN02\t20240905\t500\tKG\tPlastic packaging film\tPLAST-03\n"
            "IN01\t20240915\t150\tKG\tProcess chemicals\tCHEM-01\n"
            "IN01\t20241005\t800\tKG\tRecycled paper boxes\tPAPER-02\n"
            "IN02\t20241020\t1200\tL\tDiesel fuel bulk\tDIESEL-02\n"
            "IN01\t20241101\t2500\tKG\tStandard structural steel\tSTEEL-COIL-1\n"
        )
        sap_batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type="SAP_FUEL_PROC",
            status="PROCESSING",
            ingested_by=admin_user,
            notes="Demo seeding for SAP procurement data."
        )
        sap_batch.raw_file.save("sap_demo.txt", ContentFile(sap_data.encode('utf-8')))
        
        sap_file_wrapper = sap_batch.raw_file
        sap_file_wrapper.open('rb')
        parse_sap_file(sap_file_wrapper, sap_batch)
        sap_file_wrapper.close()
        
        self.stdout.write(f"SAP batch parsed: {sap_batch.row_count} rows, {sap_batch.error_count} errors.")

        # 5. Generate & Parse Utility Batch (UK Style CSV)
        util_uk_data = (
            "Account Number,Meter ID,Period Start,Period End,kWh Consumed,Peak kWh,Off-Peak kWh,Tariff,Cost (GBP)\n"
            "ACCT-UK-01,MTR-UK-881,2024-01-15,2024-02-14,12500,,,E-IND-01,2450.00\n"
            "ACCT-UK-01,MTR-UK-881,2024-02-15,2024-03-14,11800,,,E-IND-01,2310.00\n"
            "ACCT-UK-01,MTR-UK-882,2024-03-15,2024-04-14,15600,,,E-IND-02,3020.00\n"
            "ACCT-UK-01,MTR-UK-882,2024-04-15,2024-05-14,14800,,,E-IND-02,2900.00\n"
            "ACCT-UK-01,MTR-UK-881,2024-05-15,2024-06-14,13100,,,E-IND-01,2500.00\n"
            "ACCT-UK-01,MTR-UK-882,2024-06-15,2024-07-14,16200,,,E-IND-02,3100.00\n"
        )
        util_batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type="UTILITY_ELEC",
            status="PROCESSING",
            ingested_by=admin_user,
            notes="Demo seeding for Utility Electricity."
        )
        util_batch.raw_file.save("utility_demo.csv", ContentFile(util_uk_data.encode('utf-8')))
        
        util_file_wrapper = util_batch.raw_file
        util_file_wrapper.open('rb')
        parse_utility_csv(util_file_wrapper, util_batch)
        util_file_wrapper.close()
        
        self.stdout.write(f"Utility UK batch parsed: {util_batch.row_count} rows, {util_batch.error_count} errors.")

        # 6. Generate & Parse Utility Batch (US Style CSV with MWh and missing values)
        util_us_data = (
            "Service Address,Billing Period,Usage (MWh),Demand (kW),Rate Schedule,Amount Due ($)\n"
            "IN01 Facility,2024-01-15 - 2024-02-14,25.0,12,IND-US-A,4100.00\n"
            "IN02 Facility,2024-02-15 - 2024-03-14,22.0,10,IND-US-A,3600.00\n"
            "IN01 Facility,2024-03-15 - 2024-04-14,28.0,14,IND-US-A,4500.00\n"
            "IN02 Facility,2024-04-15 - 2024-05-14,30.0,8,IND-US-B,4900.00\n"
            "IN01 Facility,2024-05-15 - 2024-06-14,27.5,12,IND-US-A,4300.00\n"
            ",2024-06-15 - 2024-07-14,29.0,15,IND-US-A,4600.00\n" # Missing Service Address
        )
        util_us_batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type="UTILITY_ELEC",
            status="PROCESSING",
            ingested_by=admin_user,
            notes="Demo seeding for US Utility Electricity (MWh units)."
        )
        util_us_batch.raw_file.save("utility_us_demo.csv", ContentFile(util_us_data.encode('utf-8')))
        
        util_us_file_wrapper = util_us_batch.raw_file
        util_us_file_wrapper.open('rb')
        parse_utility_csv(util_us_file_wrapper, util_us_batch)
        util_us_file_wrapper.close()
        
        self.stdout.write(f"Utility US batch parsed: {util_us_batch.row_count} rows, {util_us_batch.error_count} errors.")

        # 7. Generate & Parse Corporate Travel Batch
        travel_data = (
            "Trip ID,Traveller Name,Traveller Email,Booking Date,Travel Date,Segment Type,Origin,Destination,Origin IATA,Destination IATA,Duration,Distance,Class,Cost,Currency,Carbon\n"
            "TRIP-01,John Doe,john.doe@demo.com,2024-01-10,2024-01-15,FLIGHT,Mumbai,London,BOM,LHR,,7200,ECONOMY,850,USD,\n"
            "TRIP-02,Jane Smith,jane.smith@demo.com,2024-01-12,2024-01-18,FLIGHT,Delhi,New York,DEL,JFK,,11750,BUSINESS,4200,USD,\n"
            "TRIP-03,John Doe,john.doe@demo.com,2024-01-10,2024-01-16,HOTEL,London,,,5,,,450,GBP,\n"
            "TRIP-04,Jane Smith,jane.smith@demo.com,2024-01-12,2024-01-19,HOTEL,New York,,,2,,,700,USD,\n"
            "TRIP-05,Alice Johnson,alice@demo.com,2024-02-05,2024-02-10,FLIGHT,Lucknow,Mumbai,LKO,BOM,,,ECONOMY,120,INR,\n" # Haversine test
            "TRIP-06,Bob Brown,bob@demo.com,2024-02-08,2024-02-15,FLIGHT,Bangalore,Singapore,BLR,SIN,,,BUSINESS,850,USD,\n" # Haversine test
            "TRIP-07,Alice Johnson,alice@demo.com,2024-02-05,2024-02-11,CAR,Delhi,Noida,,,,45,,30,USD,\n"
            "TRIP-08,Bob Brown,bob@demo.com,2024-02-08,2024-02-16,RAIL,Singapore,Kuala Lumpur,,,,350,,80,USD,\n"
            "TRIP-09,John Doe,john.doe@demo.com,2024-03-01,2024-03-05,FLIGHT,Delhi,London,DEL,LHR,,6700,FIRST,6500,USD,\n"
            "TRIP-10,Jane Smith,jane.smith@demo.com,2024-03-02,2024-03-06,HOTEL,London,,,4,,,900,GBP,\n"
            "TRIP-11,John Doe,john.doe@demo.com,2024-03-05,2024-03-08,CAR,London,Oxford,,,,95,,110,GBP,\n"
            "TRIP-12,Charlie Green,charlie@demo.com,2024-03-10,2024-03-15,FLIGHT,Unknown,Nowhere,XYZ,ABC,,,ECONOMY,300,USD,\n" # Fails
            "TRIP-13,Jane Smith,jane.smith@demo.com,2024-04-05,2024-04-10,FLIGHT,Mumbai,Singapore,BOM,SIN,,3900,ECONOMY,400,USD,\n"
            "TRIP-14,John Doe,john.doe@demo.com,2024-04-12,2024-04-15,HOTEL,Singapore,,,3,,,600,SGD,\n"
            "TRIP-15,Jane Smith,jane.smith@demo.com,2024-04-10,2024-04-12,CAR,Singapore,Changi,,,,25,,50,SGD,\n"
        )
        travel_batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type="CORP_TRAVEL",
            status="PROCESSING",
            ingested_by=admin_user,
            notes="Demo seeding for Corporate Travel data."
        )
        travel_batch.raw_file.save("travel_demo.csv", ContentFile(travel_data.encode('utf-8')))
        
        travel_file_wrapper = travel_batch.raw_file
        travel_file_wrapper.open('rb')
        parse_travel_csv(travel_file_wrapper, travel_batch)
        travel_file_wrapper.close()
        
        self.stdout.write(f"Travel batch parsed: {travel_batch.row_count} rows, {travel_batch.error_count} errors.")

        # 8. Set up 3–5 records in FLAGGED, APPROVED, or REJECTED state
        records = ActivityRecord.objects.filter(tenant=tenant)
        self.stdout.write(f"Total ActivityRecords created: {records.count()}")

        # Take specific records and transition them
        if records.count() >= 5:
            # Record 1 -> Approved
            r1 = records[0]
            before = {"status": r1.status}
            r1.status = "APPROVED"
            r1.reviewed_by = admin_user
            r1.reviewed_at = timezone.now()
            r1.review_notes = "Verified quantity against SAP purchase order ledger."
            r1.save()
            AuditLog.objects.create(
                tenant=tenant,
                activity_record=r1,
                actor=admin_user,
                action="APPROVED",
                before_state=before,
                after_state={"status": "APPROVED", "review_notes": r1.review_notes},
                ip_address="127.0.0.1"
            )

            # Record 2 -> Flagged
            r2 = records[1]
            before = {"status": r2.status}
            r2.status = "FLAGGED"
            r2.reviewed_by = admin_user
            r2.reviewed_at = timezone.now()
            r2.review_notes = "Gallons conversion looks abnormally high. Flagged for secondary check."
            r2.save()
            AuditLog.objects.create(
                tenant=tenant,
                activity_record=r2,
                actor=admin_user,
                action="FLAGGED",
                before_state=before,
                after_state={"status": "FLAGGED", "review_notes": r2.review_notes},
                ip_address="127.0.0.1"
            )

            # Record 3 -> Rejected
            r3 = records[2]
            before = {"status": r3.status}
            r3.status = "REJECTED"
            r3.reviewed_by = admin_user
            r3.reviewed_at = timezone.now()
            r3.review_notes = "Duplicate entry of plant fuel receipt."
            r3.save()
            AuditLog.objects.create(
                tenant=tenant,
                activity_record=r3,
                actor=admin_user,
                action="REJECTED",
                before_state=before,
                after_state={"status": "REJECTED", "review_notes": r3.review_notes},
                ip_address="127.0.0.1"
            )

            # Record 4 -> Approved and Locked
            r4 = records[3]
            before = {"status": r4.status}
            r4.status = "APPROVED"
            r4.reviewed_by = admin_user
            r4.reviewed_at = timezone.now()
            r4.save()
            AuditLog.objects.create(
                tenant=tenant,
                activity_record=r4,
                actor=admin_user,
                action="APPROVED",
                before_state=before,
                after_state={"status": "APPROVED"},
                ip_address="127.0.0.1"
            )
            
            # Lock it
            before = {"status": r4.status}
            r4.status = "LOCKED"
            r4.save()
            AuditLog.objects.create(
                tenant=tenant,
                activity_record=r4,
                actor=admin_user,
                action="LOCKED",
                before_state=before,
                after_state={"status": "LOCKED"},
                ip_address="127.0.0.1"
            )

            self.stdout.write("Transitioned demo records to APPROVED, FLAGGED, REJECTED, and LOCKED states.")

        self.stdout.write("Database seeding complete!")
