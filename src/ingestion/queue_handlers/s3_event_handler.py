"""
S3 event handler for detecting new files
"""
import logging
import json
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3EventHandler:
    """Handler for S3 event notifications"""
    
    def __init__(
        self,
        bucket_name: str,
        queue_url: Optional[str] = None,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        aws_region: str = "us-east-1"
    ):
        """
        Initialize S3 event handler
        
        Args:
            bucket_name: S3 bucket name
            queue_url: Optional SQS queue URL for notifications
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            aws_region: AWS region
        """
        self.bucket_name = bucket_name
        self.queue_url = queue_url
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        # Initialize SQS client if queue URL provided
        if queue_url:
            self.sqs_client = boto3.client(
                'sqs',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
            logger.info(f" S3EventHandler initialized with queue: {queue_url}")
        else:
            self.sqs_client = None
            logger.info(" S3EventHandler initialized without queue")
    
    def setup_bucket_notification(
        self,
        queue_arn: str,
        events: List[str] = None
    ) -> bool:
        """
        Set up S3 bucket notification to SQS queue
        
        Args:
            queue_arn: ARN of the SQS queue
            events: List of S3 events to monitor (default: ObjectCreated)
            
        Returns:
            bool: True if successful
        """
        try:
            if events is None:
                events = ['s3:ObjectCreated:*']
            
            notification_config = {
                'QueueConfigurations': [
                    {
                        'QueueArn': queue_arn,
                        'Events': events
                    }
                ]
            }
            
            self.s3_client.put_bucket_notification_configuration(
                Bucket=self.bucket_name,
                NotificationConfiguration=notification_config
            )
            
            logger.info(
                f" Set up S3 notification: bucket={self.bucket_name}, "
                f"queue={queue_arn}"
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to setup bucket notification: {e}")
            return False
    
    def poll_queue(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Poll SQS queue for S3 events
        
        Args:
            max_messages: Maximum messages to retrieve
            
        Returns:
            list: List of S3 event notifications
        """
        if not self.sqs_client or not self.queue_url:
            logger.warning("No SQS queue configured")
            return []
        
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=20  # Long polling
            )
            
            messages = response.get('Messages', [])
            
            if not messages:
                return []
            
            events = []
            for message in messages:
                try:
                    body = json.loads(message['Body'])
                    
                    # Handle S3 test event
                    if body.get('Event') == 's3:TestEvent':
                        self._delete_message(message['ReceiptHandle'])
                        continue
                    
                    # Extract S3 records
                    if 'Records' in body:
                        for record in body['Records']:
                            if record.get('eventSource') == 'aws:s3':
                                event_name = record.get('eventName', '')
                                event_info = {
                                    'event_name': event_name,
                                    'event_type': 'delete' if 'ObjectRemoved' in event_name else 'create',
                                    's3_key': record['s3']['object']['key'],
                                    'size': record['s3']['object'].get('size', 0),
                                    'receipt_handle': message['ReceiptHandle']
                                }
                                events.append(event_info)
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                    continue
            
            logger.info(f"Polled {len(events)} S3 events from queue")
            return events
            
        except ClientError as e:
            logger.error(f"Failed to poll queue: {e}")
            return []
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete message from queue after processing
        
        Args:
            receipt_handle: Message receipt handle
            
        Returns:
            bool: True if successful
        """
        return self._delete_message(receipt_handle)
    
    def _delete_message(self, receipt_handle: str) -> bool:
        """Internal method to delete message"""
        if not self.sqs_client or not self.queue_url:
            return False
        
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete message: {e}")
            return False
    
    def detect_new_files(self, last_check_timestamp: Optional[str] = None) -> List[str]:
        """
        Detect new files added to S3 bucket (polling method)
        
        Args:
            last_check_timestamp: ISO format timestamp of last check
            
        Returns:
            list: List of S3 keys for new files
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name
            )
            
            if 'Contents' not in response:
                return []
            
            new_files = []
            
            for obj in response['Contents']:
                # If timestamp provided, filter by last modified
                if last_check_timestamp:
                    obj_modified = obj['LastModified'].isoformat()
                    if obj_modified > last_check_timestamp:
                        new_files.append(obj['Key'])
                else:
                    new_files.append(obj['Key'])
            
            logger.info(f"Detected {len(new_files)} new files")
            return new_files
            
        except ClientError as e:
            logger.error(f"Failed to detect new files: {e}")
            return []
