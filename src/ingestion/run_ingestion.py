#!/usr/bin/env python3
"""
Main entry point for the ingestion pipeline
Runs automatic data ingestion when changes happen on S3 (via SQS)
"""
import os
import sys
import logging
import signal
import time
import threading
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.ingestion.config import IngestionConfig
from src.ingestion.services import (
    S3Service,
    ElasticsearchService,
    LLMService,
    EmbeddingService,
    SyncService
)
from src.ingestion.services.ocr_service import OCRService
from src.ingestion.models.schemas import ParserConfig, PipelineConfig
from src.ingestion.pipeline.ingestion_pipeline import IngestionPipeline


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ingestion.log')
    ]
)
logger = logging.getLogger(__name__)


class IngestionService:
    """Service wrapper for the ingestion pipeline"""
    
    def __init__(self):
        self.pipeline = None
        self.sync_service = None
        self.running = False
        
    def initialize(self):
        """Initialize all services and pipeline"""
        logger.info("=" * 60)
        logger.info("🚀 Starting Document Ingestion Service")
        logger.info("=" * 60)
        
        # Validate configuration
        logger.info("📋 Validating configuration...")
        try:
            IngestionConfig.validate()
            IngestionConfig.print_config()
        except ValueError as e:
            logger.error(f" Configuration validation failed: {e}")
            logger.error("Please check your .env file and ensure all required variables are set")
            sys.exit(1)
        
        # Initialize services
        logger.info("🔧 Initializing services...")
        try:
            s3_service = S3Service()
            es_service = ElasticsearchService()
            llm_service = LLMService()
            embedding_service = EmbeddingService()
            
            # Initialize OCR service if not using LLM for OCR
            ocr_service = None
            if not IngestionConfig.USE_LLM_FOR_OCR:
                logger.info("🔧 Initializing PaddleOCR service...")
                ocr_service = OCRService(
                    host=IngestionConfig.OCR_ENDPOINT,
                    port=IngestionConfig.OCR_PORT
                )
            
            logger.info(" All services initialized successfully")
        except Exception as e:
            logger.error(f" Service initialization failed: {e}")
            sys.exit(1)
        
        # Configure parser
        parser_config = ParserConfig(
            chunk_size=1000,
            chunk_overlap=200,
            enable_embeddings=True,
            llm_timeout=120,
            embedding_timeout=60
        )
        
        # Configure pipeline
        pipeline_config = PipelineConfig(
            batch_size=10,
            enable_queue=IngestionConfig.SQS_ENABLED,
            queue_poll_interval=30,
            retry_attempts=3,
            retry_delay=5
        )
        
        # Create pipeline
        logger.info("🔨 Creating ingestion pipeline...")
        self.pipeline = IngestionPipeline(
            s3_service=s3_service,
            elasticsearch_service=es_service,
            llm_service=llm_service,
            embedding_service=embedding_service,
            parser_config=parser_config,
            pipeline_config=pipeline_config,
            ocr_service=ocr_service,
            use_llm_for_ocr=IngestionConfig.USE_LLM_FOR_OCR
        )
        
        logger.info(" Ingestion pipeline created successfully")
        
        # Initialize background sync service if enabled
        if IngestionConfig.ENABLE_BACKGROUND_SYNC:
            sync_interval = IngestionConfig.SYNC_INTERVAL_HOURS * 3600  # Convert to seconds
            self.sync_service = SyncService(
                s3_service=s3_service,
                elasticsearch_service=es_service,
                check_interval=sync_interval
            )
            logger.info(" Background sync service initialized")
        else:
            logger.info("  Background sync disabled")
        
    def start_automatic_processing(self):
        """Start automatic processing with queue monitoring"""
        if not self.pipeline:
            logger.error(" Pipeline not initialized")
            return
        
        # Optionally run a full ingest on first run
        if IngestionConfig.FIRST_RUN_FULL_INGEST:
            logger.info("🌟 First-run mode: ingesting entire bucket contents")
            logger.info("")
            
            prefixes = [
                "docx_data/",
                "pdf_images/",
                "xls_data/"
            ]
            
            overall_start = time.time()
            total_stats = {
                "total_files": 0, 
                "processed": 0, 
                "failed": 0, 
                "duplicates": 0,
                "timing_breakdown": {}
            }
            
            for prefix in prefixes:
                try:
                    logger.info(f"📂 Ingesting prefix: {prefix}")
                    stats = self.pipeline.process_all_files(prefix=prefix)
                    total_stats["total_files"] += stats.get("total_files", 0)
                    total_stats["processed"] += stats.get("processed", 0)
                    total_stats["failed"] += stats.get("failed", 0)
                    total_stats["duplicates"] += stats.get("duplicates", 0)
                    
                    # Aggregate timing data
                    if "avg_timing" in stats:
                        for key, value in stats["avg_timing"].items():
                            if key not in total_stats["timing_breakdown"]:
                                total_stats["timing_breakdown"][key] = []
                            total_stats["timing_breakdown"][key].append(value)
                    
                except Exception as e:
                    logger.error(f" Error ingesting prefix {prefix}: {e}")
            
            overall_time = time.time() - overall_start
            success_rate = (total_stats["processed"] / total_stats["total_files"] * 100) if total_stats["total_files"] else 0.0
            
            # Calculate average timing across all prefixes
            avg_overall_timing = {}
            for key, values in total_stats["timing_breakdown"].items():
                if values:
                    avg_overall_timing[key] = sum(values) / len(values)
            
            # Final summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("🎉 OVERALL INGESTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"📊 Total Files Processed: {total_stats['total_files']}")
            logger.info(f" Successfully Indexed: {total_stats['processed']}")
            logger.info(f"🔁 Duplicates Skipped: {total_stats['duplicates']}")
            logger.info(f" Failed: {total_stats['failed']}")
            logger.info(f"📈 Overall Success Rate: {success_rate:.1f}%")
            logger.info(f"⏱️  Total Processing Time: {overall_time:.2f}s ({overall_time/60:.1f} minutes)")
            
            if avg_overall_timing:
                logger.info("")
                logger.info("⏱️  AVERAGE TIMING PER OPERATION:")
                for key, value in sorted(avg_overall_timing.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"   • {key.replace('_', ' ').title()}: {value:.3f}s")
            
            logger.info("=" * 80)
            logger.info("")
            
            # If SQS is not enabled, stop after full ingest
            if not IngestionConfig.SQS_ENABLED:
                logger.info("🛑 SQS disabled. Ending after first-run full ingest.")
                return
        
        # Check if SQS is configured and enabled
        use_sqs = bool(IngestionConfig.SQS_QUEUE_URL) and IngestionConfig.SQS_ENABLED

        if use_sqs:
            logger.info("🔔 SQS Queue configured - Setting up queue processing...")
            try:
                self.pipeline.setup_queue_processing(
                    queue_url=IngestionConfig.SQS_QUEUE_URL,
                    aws_access_key_id=IngestionConfig.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=IngestionConfig.AWS_SECRET_ACCESS_KEY,
                    aws_region=IngestionConfig.AWS_REGION
                )
                logger.info(" Queue processing configured")
            except Exception as e:
                logger.error(f" Failed to setup queue processing: {e}")
                logger.info("  Falling back to direct S3 polling...")
                use_sqs = False
        else:
            logger.info("  SQS disabled or not configured - no queue processing will start")
        
        # Start processing
        logger.info("=" * 60)
        if use_sqs:
            logger.info(" Starting automatic ingestion with SQS queue monitoring")
            logger.info(f"📥 Queue: {IngestionConfig.SQS_QUEUE_URL}")
        else:
            logger.info(" Starting automatic ingestion with S3 polling")
            logger.info(f"📦 Bucket: {IngestionConfig.S3_BUCKET_NAME}")
        logger.info(f"🔍 Elasticsearch Index: {IngestionConfig.ELASTICSEARCH_INDEX}")
        logger.info(f"⏱️  Poll Interval: 30 seconds")
        
        # Show background sync info
        if IngestionConfig.ENABLE_BACKGROUND_SYNC:
            logger.info(f"🔄 Background Sync: Enabled (every {IngestionConfig.SYNC_INTERVAL_HOURS}h)")
        else:
            logger.info("🔄 Background Sync: Disabled")
        
        logger.info("=" * 60)
        logger.info("✨ Service is running. Press Ctrl+C to stop.")
        logger.info("")
        
        # Determine if we should keep running
        keep_running = use_sqs or (IngestionConfig.ENABLE_BACKGROUND_SYNC and self.sync_service)
        
        # If no SQS and no background sync, we end here (first-run handled above)
        if not keep_running:
            logger.info(" Nothing else to do without SQS or Background Sync. Exiting.")
            return

        self.running = True
        
        # Start background sync in a separate thread if enabled
        sync_thread = None
        if self.sync_service:
            logger.info("🔄 Starting background sync thread...")
            sync_thread = threading.Thread(
                target=self.sync_service.start_background_sync,
                daemon=True
            )
            sync_thread.start()
            logger.info(" Background sync thread started")
        
        # If SQS enabled, start queue processing
        if use_sqs:
            try:
                # Start queue processing (blocking call)
                self.pipeline.start_queue_processing(use_queue=True)
            except KeyboardInterrupt:
                logger.info("\n  Received shutdown signal...")
                self.stop()
            except Exception as e:
                logger.error(f" Error in automatic processing: {e}", exc_info=True)
                self.stop()
                sys.exit(1)
        else:
            # No SQS, but background sync is running - just keep service alive
            logger.info("📡 Background sync running. Service will stay alive.")
            logger.info("   Press Ctrl+C to stop.")
            try:
                # Keep the main thread alive while background sync runs
                while self.running:
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("\n  Received shutdown signal...")
                self.stop()
    
    def stop(self):
        """Stop the ingestion service"""
        if self.running:
            logger.info("🛑 Stopping ingestion service...")
            if self.pipeline:
                self.pipeline.stop_queue_processing()
            if self.sync_service:
                self.sync_service.stop_background_sync()
            self.running = False
            logger.info(" Service stopped successfully")
            logger.info(f"📊 Session ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"\n  Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start service
    service = IngestionService()
    
    try:
        service.initialize()
        service.start_automatic_processing()
    except KeyboardInterrupt:
        logger.info("\n  Interrupted by user")
        service.stop()
    except Exception as e:
        logger.error(f" Fatal error: {e}", exc_info=True)
        service.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
