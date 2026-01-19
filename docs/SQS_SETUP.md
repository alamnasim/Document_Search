# AWS SQS Setup Guide

Complete guide to set up Amazon Simple Queue Service (SQS) for real-time document ingestion in the Document Search project.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1: Create SQS Queue](#step-1-create-sqs-queue)
- [Step 2: Configure S3 Event Notifications](#step-2-configure-s3-event-notifications)
- [Step 3: Configure Application](#step-3-configure-application)
- [Step 4: Test the Setup](#step-4-test-the-setup)

## Overview

SQS enables **real-time document ingestion** by receiving notifications whenever files are created or deleted in your S3 bucket. This provides:

- **Real-time Processing**: Documents are indexed within seconds of upload
- **Automatic Deletion**: Removes documents from Elasticsearch when deleted from S3
- **Reliability**: Message queue ensures no events are lost
- **Scalability**: Handles high-volume file operations

### Architecture

```
S3 Bucket -> Event Notification -> SQS Queue -> Ingestion Service -> Elasticsearch
```

**Supported Events:**
- `s3:ObjectCreated:*` - File uploads (PUT, POST, Copy)
- `s3:ObjectRemoved:*` - File deletions

## Prerequisites

- AWS Account with permissions to:
  - Create SQS queues
  - Configure S3 event notifications
  - Modify S3 bucket policies
- AWS CLI installed (optional but recommended)
- S3 bucket already created

## Step 1: Create SQS Queue

### Option A: AWS Console

1. **Navigate to SQS Console**
   - Go to [AWS SQS Console](https://console.aws.amazon.com/sqs/)
   - Click **Create queue**

2. **Configure Queue Settings**
   ```
   Type: Standard Queue
   Name: document-ingestion-queue
   
   Configuration:
   - Visibility timeout: 60 seconds
   - Message retention period: 4 days
   - Delivery delay: 0 seconds
   - Maximum message size: 256 KB
   - Receive message wait time: 0 seconds (short polling)
   ```

3. **Access Policy**
   - Scroll to **Access policy**
   - Choose **Advanced**
   - Add this policy (replace `YOUR_BUCKET_NAME` and `YOUR_ACCOUNT_ID`):

   ```json
   {
     "Version": "2012-10-17",
     "Id": "AllowS3ToSendMessage",
     "Statement": [
       {
         "Sid": "AllowS3EventNotifications",
         "Effect": "Allow",
         "Principal": {
           "Service": "s3.amazonaws.com"
         },
         "Action": "SQS:SendMessage",
         "Resource": "arn:aws:sqs:YOUR_REGION:YOUR_ACCOUNT_ID:document-ingestion-queue",
         "Condition": {
           "ArnLike": {
             "aws:SourceArn": "arn:aws:s3:::YOUR_BUCKET_NAME"
           }
         }
       }
     ]
   }
   ```

4. **Create Queue**
   - Click **Create queue**
   - Copy the **Queue URL** (e.g., `https://sqs.us-east-1.amazonaws.com/123456789012/document-ingestion-queue`)

### Option B: AWS CLI

```bash
# Create the queue
aws sqs create-queue --queue-name document-ingestion-queue

# Get the queue URL
QUEUE_URL=$(aws sqs get-queue-url --queue-name document-ingestion-queue --query 'QueueUrl' --output text)
echo "Queue URL: $QUEUE_URL"

# Get queue ARN
QUEUE_ARN=$(aws sqs get-queue-attributes --queue-url $QUEUE_URL --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

# Set queue policy to allow S3 notifications
aws sqs set-queue-attributes --queue-url $QUEUE_URL --attributes '{
  "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"s3.amazonaws.com\"},\"Action\":\"SQS:SendMessage\",\"Resource\":\"'$QUEUE_ARN'\",\"Condition\":{\"ArnLike\":{\"aws:SourceArn\":\"arn:aws:s3:::YOUR_BUCKET_NAME\"}}}]}"
}'
```

## Step 2: Configure S3 Event Notifications

### Option A: AWS Console

1. **Navigate to S3 Bucket**
   - Go to [S3 Console](https://s3.console.aws.amazon.com/)
   - Select your bucket (e.g., `document-search-proj`)

2. **Configure Event Notifications**
   - Go to **Properties** tab
   - Scroll to **Event notifications**
   - Click **Create event notification**

3. **Create Notification for File Uploads**
   ```
   Event name: DocumentCreated
   
   Event types:
    All object create events
     or select specific:
      s3:ObjectCreated:Put
      s3:ObjectCreated:Post
      s3:ObjectCreated:Copy
      s3:ObjectCreated:CompleteMultipartUpload
   
   Destination:
    SQS queue
   Queue: document-ingestion-queue
   ```
   - Click **Save changes**

4. **Create Notification for File Deletions**
   - Click **Create event notification** again
   ```
   Event name: DocumentDeleted
   
   Event types:
    All object removal events
     or select specific:
      s3:ObjectRemoved:Delete
      s3:ObjectRemoved:DeleteMarkerCreated
   
   Destination:
    SQS queue
   Queue: document-ingestion-queue
   ```
   - Click **Save changes**

### Option B: AWS CLI

```bash
# Set your bucket name
BUCKET_NAME="document-search-proj"
QUEUE_ARN="arn:aws:sqs:us-east-1:123456789012:document-ingestion-queue"

# Create notification configuration JSON
cat > notification.json <<EOF
{
  "QueueConfigurations": [
    {
      "Id": "DocumentCreated",
      "QueueArn": "$QUEUE_ARN",
      "Events": [
        "s3:ObjectCreated:*"
      ]
    },
    {
      "Id": "DocumentDeleted",
      "QueueArn": "$QUEUE_ARN",
      "Events": [
        "s3:ObjectRemoved:*"
      ]
    }
  ]
}
EOF

# Apply the notification configuration
aws s3api put-bucket-notification-configuration \
  --bucket $BUCKET_NAME \
  --notification-configuration file://notification.json

# Verify the configuration
aws s3api get-bucket-notification-configuration --bucket $BUCKET_NAME
```

## Step 3: Configure Application

Update your `.env` file with SQS configuration:

```bash
# Enable SQS processing
SQS_ENABLED=true

# Set your SQS queue URL (from Step 1)
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/document-ingestion-queue

# First-run configuration
# Set to true for initial full bucket ingestion
# Set to false to only process new SQS events
FIRST_RUN_FULL_INGEST=false

# Background sync (recommended as safety net)
ENABLE_BACKGROUND_SYNC=true
SYNC_INTERVAL_HOURS=6
```

## Step 4: Test the Setup

### 1. Start the Ingestion Service

```bash
python src/ingestion/run_ingestion.py
```

You should see:
```
 SQS Queue configured - Setting up queue processing...
 Queue processing configured
 Starting automatic ingestion with SQS queue monitoring
 Queue: https://sqs.us-east-1.amazonaws.com/...
```

### 2. Test File Upload

Upload a test file to S3:

```bash
# Using AWS CLI
aws s3 cp test-document.pdf s3://document-search-proj/pdf_images/

# Or using Python boto3
python -c "
import boto3
s3 = boto3.client('s3')
s3.upload_file('test-document.pdf', 'document-search-proj', 'pdf_images/test-document.pdf')
"
```

**Expected Behavior:**
- Within 30 seconds, you should see ingestion logs:
```
Polled 1 S3 events from queue
Processing queue event (create): pdf_images/test-document.pdf
Processing file: test-document.pdf (pdf)
 Processed test-document.pdf in 2.5s
 Processed and deleted queue message
```

### 3. Test File Deletion

Delete the file from S3:

```bash
aws s3 rm s3://document-search-proj/pdf_images/test-document.pdf
```

**Expected Behavior:**
- Within 30 seconds, you should see deletion logs:
```
Polled 1 S3 events from queue
Processing queue event (delete): pdf_images/test-document.pdf
  Deleting document: pdf_images/test-document.pdf
 Deleted 1 document(s) for S3 key: pdf_images/test-document.pdf
 Processed and deleted queue message
```

### 4. Verify in Elasticsearch

```bash
# Check document count
curl -X GET "localhost:9200/documents_v3/_count?pretty"

# Search for the document
curl -X POST "localhost:9200/documents_v3/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"file_name": "test-document.pdf"}}}'
```

## Troubleshooting

### Issue: "No messages received from queue"

**Possible Causes:**
1. S3 event notifications not configured
2. Queue policy doesn't allow S3 to send messages
3. Wrong queue URL in `.env`

**Solutions:**
```bash
# Verify S3 notifications are configured
aws s3api get-bucket-notification-configuration --bucket YOUR_BUCKET_NAME

# Test by sending a manual message
aws sqs send-message \
  --queue-url YOUR_QUEUE_URL \
  --message-body '{"Records":[{"eventName":"ObjectCreated:Put","s3":{"bucket":{"name":"document-search-proj"},"object":{"key":"test.pdf"}}}]}'

# Check for messages in queue
aws sqs receive-message --queue-url YOUR_QUEUE_URL
```

### Issue: "Access Denied" when polling SQS

**Solution:** Ensure your AWS credentials have SQS permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:*:*:document-ingestion-queue"
    }
  ]
}
```

### Issue: Messages stuck in queue (not deleted)

**Possible Causes:**
1. Processing fails before message deletion
2. Visibility timeout too short

**Solutions:**
```bash
# Check dead-letter queue (if configured)
aws sqs receive-message --queue-url YOUR_DLQ_URL

# Increase visibility timeout
aws sqs set-queue-attributes \
  --queue-url YOUR_QUEUE_URL \
  --attributes VisibilityTimeout=120

# Purge stuck messages (use with caution!)
aws sqs purge-queue --queue-url YOUR_QUEUE_URL
```

### Issue: Duplicate processing

**Cause:** SQS Standard queues can deliver messages more than once.

**Solution:** The application handles duplicates automatically through content hashing:
```
  Duplicate detected: test.pdf (content hash: abc123...)
 Skipping duplicate document
```

### Issue: High latency (messages delayed)

**Possible Causes:**
1. Ingestion service not running
2. Processing is slow (OCR bottleneck)
3. SQS polling interval too long

**Solutions:**
- Ensure ingestion service is running
- Check OCR service health: `curl http://localhost:8088/health`
- Verify poll interval (default: 30 seconds)
- Check logs for processing bottlenecks

## Monitoring

### View Queue Metrics

**AWS Console:**
- Go to SQS Console -> Select queue -> Monitoring tab
- Key metrics:
  - `ApproximateNumberOfMessagesVisible` - Messages waiting
  - `NumberOfMessagesReceived` - Total received
  - `NumberOfMessagesDeleted` - Successfully processed

**AWS CLI:**
```bash
aws sqs get-queue-attributes \
  --queue-url YOUR_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name NumberOfMessagesReceived \
  --dimensions Name=QueueName,Value=document-ingestion-queue \
  --start-time 2026-01-18T00:00:00Z \
  --end-time 2026-01-18T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

## Best Practices

1. **Enable Dead-Letter Queue (DLQ)**
   - Captures messages that fail processing repeatedly
   - Configure after 3-5 receive attempts
   
   ```bash
   # Create DLQ
   aws sqs create-queue --queue-name document-ingestion-dlq
   
   # Configure on main queue
   aws sqs set-queue-attributes \
     --queue-url YOUR_QUEUE_URL \
     --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"YOUR_DLQ_ARN\",\"maxReceiveCount\":\"5\"}"}'
   ```

2. **Use Background Sync as Safety Net**
   - Even with SQS, keep background sync enabled
   - Catches any missed events or queue failures
   - Set interval based on needs (6-24 hours)

3. **Monitor Queue Depth**
   - Set CloudWatch alarms for queue backlog
   - Alert if messages exceed threshold (e.g., 100+)

4. **Test Both Upload and Delete**
   - Verify both event types work
   - Check Elasticsearch reflects changes

5. **Secure Access**
   - Use IAM roles for EC2/ECS instead of access keys
   - Restrict queue policy to specific S3 bucket
   - Rotate credentials regularly

## SQS vs Background Sync Comparison

| Feature | SQS (Real-time) | Background Sync (Periodic) |
|---------|-----------------|----------------------------|
| Latency | < 1 second | Hours (configurable) |
| Reliability | 99.9%+ | 100% (full scan) |
| Setup Complexity | High (AWS config) | Low (just enable) |
| AWS Cost | ~$0.40/million requests | None (uses existing APIs) |
| Use Case | Production, real-time needs | Development, safety net |




