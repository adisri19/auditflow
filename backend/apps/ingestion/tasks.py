import logging
from celery import shared_task
from apps.ingestion.models import IngestionBatch
from apps.ingestion.parsers.sap import parse_sap_file
from apps.ingestion.parsers.utility import parse_utility_csv
from apps.ingestion.parsers.travel import parse_travel_csv

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2)
def parse_ingestion_batch(self, batch_id):
    try:
        batch = IngestionBatch.objects.get(id=batch_id)
    except IngestionBatch.DoesNotExist:
        logger.error(f"IngestionBatch {batch_id} does not exist.")
        return

    batch.status = "PROCESSING"
    batch.save(update_fields=['status'])

    try:
        if not batch.raw_file:
            raise ValueError("No raw file attached to batch.")

        batch.raw_file.open('rb')
        try:
            if batch.source_type == 'SAP_FUEL_PROC':
                parse_sap_file(batch.raw_file, batch)
            elif batch.source_type == 'UTILITY_ELEC':
                parse_utility_csv(batch.raw_file, batch)
            elif batch.source_type == 'CORP_TRAVEL':
                parse_travel_csv(batch.raw_file, batch)
            else:
                raise ValueError(f"Invalid source type: {batch.source_type}")
        finally:
            batch.raw_file.close()

        batch.refresh_from_db()
        if batch.status != "FAILED":
            batch.status = "DONE"
            batch.save(update_fields=['status'])

    except Exception as exc:
        logger.exception(f"Error processing IngestionBatch {batch_id}: {exc}")
        batch.status = "FAILED"
        batch.error_message = str(exc)
        batch.save(update_fields=['status', 'error_message'])
        self.retry(exc=exc, countdown=2 ** self.request.retries, max_retries=2)
