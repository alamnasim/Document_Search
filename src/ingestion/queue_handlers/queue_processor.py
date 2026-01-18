"""
Queue processor for handling S3 events
"""
import logging
import time
from typing import Callable, Optional
from datetime import datetime

from .s3_event_handler import S3EventHandler


logger = logging.getLogger(__name__)


class QueueProcessor:
    """Processor for S3 event queue"""
    
    def __init__(
        self,
        event_handler: S3EventHandler,
        poll_interval: int = 30
    ):
        """
        Initialize queue processor
        
        Args:
            event_handler: S3 event handler instance
            poll_interval: Polling interval in seconds
        """
        self.event_handler = event_handler
        self.poll_interval = poll_interval
        self.running = False
        self.last_check_timestamp = None
        logger.info(f"QueueProcessor initialized: interval={poll_interval}s")
    
    def start_polling(
        self,
        callback: Callable[[str], bool],
        use_queue: bool = True
    ):
        """
        Start polling for new files
        
        Args:
            callback: Function to call with S3 key of new file
            use_queue: Whether to use SQS queue or direct polling
        """
        self.running = True
        logger.info("Started polling for S3 events")
        
        try:
            while self.running:
                try:
                    if use_queue:
                        self._process_queue_events(callback)
                    else:
                        self._process_direct_polling(callback)
                    
                    time.sleep(self.poll_interval)
                    
                except KeyboardInterrupt:
                    logger.info("Polling interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}", exc_info=True)
                    time.sleep(self.poll_interval)
        
        finally:
            self.running = False
            logger.info("Stopped polling")
    
    def stop_polling(self):
        """Stop the polling loop"""
        self.running = False
        logger.info("Stopping polling...")
    
    def _process_queue_events(self, callback: Callable[[str, str], bool]):
        """Process events from SQS queue"""
        events = self.event_handler.poll_queue()
        
        for event in events:
            s3_key = event['s3_key']
            event_type = event.get('event_type', 'create')
            receipt_handle = event['receipt_handle']
            
            logger.info(f"Processing queue event ({event_type}): {s3_key}")
            
            try:
                # Call the callback function with event type
                success = callback(s3_key, event_type)
                
                # Delete message if processed successfully
                if success:
                    self.event_handler.delete_message(receipt_handle)
                    logger.info(f" Processed and deleted queue message: {s3_key}")
                else:
                    logger.warning(f"  Processing failed for: {s3_key}")
                    
            except Exception as e:
                logger.error(f"Error processing {s3_key}: {e}", exc_info=True)
    
    def _process_direct_polling(self, callback: Callable[[str], bool]):
        """Process events using direct S3 polling"""
        new_files = self.event_handler.detect_new_files(
            self.last_check_timestamp
        )
        
        for s3_key in new_files:
            logger.info(f"Processing new file: {s3_key}")
            
            try:
                callback(s3_key)
                logger.info(f" Processed: {s3_key}")
                
            except Exception as e:
                logger.error(f"Error processing {s3_key}: {e}", exc_info=True)
        
        # Update last check timestamp
        self.last_check_timestamp = datetime.utcnow().isoformat()
