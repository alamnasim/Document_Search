"""
Main ingestion pipeline orchestrating all components
"""
import logging
import uuid
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

from ..models.schemas import (
    ParserConfig,
    PipelineConfig,
    ProcessedDocument,
    IngestionResult,
    FileType,
    DocumentMetadata,
    S3FileInfo
)
from ..services import (
    S3Service,
    ElasticsearchService,
    LLMService,
    EmbeddingService
)
from ..services.ocr_service import OCRService
from ..parsers import (
    PDFParser,
    DOCXParser,
    ImageParser,
    CSVParser,
    ExcelParser
)
from ..processors import TextChunker, MetadataExtractor
from ..queue_handlers import S3EventHandler, QueueProcessor
from ..exceptions import (
    IngestionException,
    ParserException,
    S3Exception,
    ElasticsearchException
)


logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Main ingestion pipeline for processing documents from S3 to Elasticsearch"""
    
    def __init__(
        self,
        s3_service: S3Service,
        elasticsearch_service: ElasticsearchService,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        parser_config: Optional[ParserConfig] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        ocr_service: Optional[OCRService] = None,
        use_llm_for_ocr: bool = True
    ):
        """
        Initialize ingestion pipeline
        
        Args:
            s3_service: S3 service instance
            elasticsearch_service: Elasticsearch service instance
            llm_service: LLM service instance
            embedding_service: Embedding service instance
            parser_config: Parser configuration
            pipeline_config: Pipeline configuration
            ocr_service: OCR service instance (if use_llm_for_ocr=False)
            use_llm_for_ocr: If True, use LLM for OCR; if False, use PaddleOCR
        """
        self.s3_service = s3_service
        self.elasticsearch_service = elasticsearch_service
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.ocr_service = ocr_service
        self.use_llm_for_ocr = use_llm_for_ocr
        
        # Use default configs if not provided
        self.parser_config = parser_config or ParserConfig()
        self.pipeline_config = pipeline_config or PipelineConfig()
        
        # Initialize processors
        self.text_chunker = TextChunker(self.parser_config)
        self.metadata_extractor = MetadataExtractor()
        
        # Initialize parsers based on OCR method
        if use_llm_for_ocr:
            logger.info("Using LLM for PDF/Image OCR")
            self.parsers = {
                FileType.PDF: PDFParser(self.parser_config, llm_service=self.llm_service, use_llm=True),
                FileType.DOCX: DOCXParser(self.parser_config),
                FileType.DOC: DOCXParser(self.parser_config),
                FileType.PNG: ImageParser(self.parser_config, llm_service=self.llm_service, use_llm=True),
                FileType.JPG: ImageParser(self.parser_config, llm_service=self.llm_service, use_llm=True),
                FileType.JPEG: ImageParser(self.parser_config, llm_service=self.llm_service, use_llm=True),
                FileType.TIFF: ImageParser(self.parser_config, llm_service=self.llm_service, use_llm=True),
                FileType.CSV: CSVParser(self.parser_config),
                FileType.XLSX: ExcelParser(self.parser_config),
                FileType.XLS: ExcelParser(self.parser_config)
            }
        else:
            logger.info("Using PaddleOCR for PDF/Image OCR")
            self.parsers = {
                FileType.PDF: PDFParser(self.parser_config, ocr_service=self.ocr_service, use_llm=False),
                FileType.DOCX: DOCXParser(self.parser_config),
                FileType.DOC: DOCXParser(self.parser_config),
                FileType.PNG: ImageParser(self.parser_config, ocr_service=self.ocr_service, use_llm=False),
                FileType.JPG: ImageParser(self.parser_config, ocr_service=self.ocr_service, use_llm=False),
                FileType.JPEG: ImageParser(self.parser_config, ocr_service=self.ocr_service, use_llm=False),
                FileType.TIFF: ImageParser(self.parser_config, ocr_service=self.ocr_service, use_llm=False),
                FileType.CSV: CSVParser(self.parser_config),
                FileType.XLSX: ExcelParser(self.parser_config),
                FileType.XLS: ExcelParser(self.parser_config)
            }
        
        # Queue processor (optional)
        self.queue_processor = None
        
        logger.info(" IngestionPipeline initialized")
    
    def setup_queue_processing(
        self,
        queue_url: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "us-east-1"
    ):
        """
        Set up queue processing for automatic ingestion
        
        Args:
            queue_url: SQS queue URL
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            aws_region: AWS region
        """
        event_handler = S3EventHandler(
            bucket_name=self.s3_service.bucket_name,
            queue_url=queue_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region
        )
        
        self.queue_processor = QueueProcessor(
            event_handler,
            poll_interval=self.pipeline_config.queue_poll_interval
        )
        
        logger.info(" Queue processing configured")
    
    def start_queue_processing(self, use_queue: bool = True):
        """
        Start automatic queue processing
        
        Args:
            use_queue: Whether to use SQS queue or direct polling
        """
        if not self.queue_processor:
            raise IngestionException(
                "Queue processor not configured. Call setup_queue_processing first."
            )
        
        def process_callback(s3_key: str, event_type: str = 'create') -> bool:
            """Callback for processing files (create/delete)"""
            try:
                if event_type == 'delete':
                    # Handle file deletion
                    logger.info(f"  Deleting document: {s3_key}")
                    success = self.elasticsearch_service.delete_document_by_s3_key(s3_key)
                    return success
                else:
                    # Handle file creation/update
                    result = self.process_file(s3_key)
                    return result.success
            except Exception as e:
                logger.error(f"Failed to process {s3_key}: {e}")
                return False
        
        self.queue_processor.start_polling(process_callback, use_queue)
    
    def stop_queue_processing(self):
        """Stop queue processing"""
        if self.queue_processor:
            self.queue_processor.stop_polling()
    
    def process_file(self, s3_key: str) -> IngestionResult:
        """
        Process a single file through the pipeline with detailed timing and deduplication
        
        Args:
            s3_key: S3 object key
            
        Returns:
            IngestionResult: Result of processing with timing breakdown
        """
        start_time = time.time()
        timing = {}
        
        try:
            # S3 operations - get file info
            s3_start = time.time()
            file_info = self.s3_service.get_file_info(s3_key)
            file_type = self._get_file_type(file_info.file_name)
            timing['s3_metadata'] = time.time() - s3_start
            
            logger.info(f"Processing file: {file_info.file_name} ({file_type.value})")
            
            # Generate presigned URL
            url_start = time.time()
            presigned_url = self.s3_service.generate_presigned_url(
                s3_key,
                self.pipeline_config.presigned_url_expiration
            )
            file_info.presigned_url = presigned_url
            timing['presigned_url'] = time.time() - url_start
            
            # Get file content from S3
            download_start = time.time()
            file_content = self.s3_service.get_file_content(s3_key)
            timing['s3_download'] = time.time() - download_start
            
            # Parse document (LLM OCR, DOCX extraction, etc.)
            parse_start = time.time()
            parsed_result = self._parse_document(
                file_content,
                file_info.file_name,
                file_type
            )
            timing['parsing'] = time.time() - parse_start
            
            if not parsed_result.get("success"):
                raise ParserException(parsed_result.get("error", "Parsing failed"))
            
            content = parsed_result["content"]
            
            # Calculate content hash for deduplication
            hash_start = time.time()
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            timing['content_hashing'] = time.time() - hash_start
            
            # Check for duplicates if enabled
            is_duplicate = False
            if self.pipeline_config.enable_deduplication:
                dedup_start = time.time()
                is_duplicate = self.elasticsearch_service.check_duplicate(content_hash)
                timing['deduplication_check'] = time.time() - dedup_start
                
                if is_duplicate:
                    logger.info(f"  Duplicate content detected: {file_info.file_name} (hash: {content_hash[:16]}...) - SKIPPED")
                    return IngestionResult(
                        success=True,
                        file_name=file_info.file_name,
                        file_path=f"s3://{file_info.bucket_name}/{s3_key}",
                        message="Duplicate content - skipped",
                        processing_time=time.time() - start_time,
                        timing=timing,
                        is_duplicate=True
                    )
            
            # Chunk text
            chunk_start = time.time()
            chunks = self.text_chunker.chunk_text(content)
            timing['chunking'] = time.time() - chunk_start
            
            # Generate embeddings if enabled
            embeddings_generated = 0
            if self.parser_config.enable_embeddings:
                embed_start = time.time()
                chunks = self.embedding_service.generate_chunk_embeddings(chunks)
                timing['embedding'] = time.time() - embed_start
                embeddings_generated = sum(1 for c in chunks if c.embedding)
            
            # Create processed document
            doc_id = str(uuid.uuid4())
            
            processed_doc = ProcessedDocument(
                doc_id=doc_id,
                file_name=file_info.file_name,
                file_path=f"s3://{file_info.bucket_name}/{s3_key}",
                presigned_url=presigned_url,
                file_type=file_type,
                file_size=file_info.file_size,
                upload_date=datetime.utcnow(),
                content=content,
                content_hash=content_hash,
                chunks=chunks,
                metadata=parsed_result["metadata"],
                structured_data=parsed_result.get("structured_data")
            )
            
            # Index in Elasticsearch
            index_start = time.time()
            self.elasticsearch_service.index_document(processed_doc)
            timing['elasticsearch_indexing'] = time.time() - index_start
            
            processing_time = time.time() - start_time
            timing['total'] = processing_time
            
            result = IngestionResult(
                success=True,
                doc_id=doc_id,
                file_name=file_info.file_name,
                file_path=f"s3://{file_info.bucket_name}/{s3_key}",
                message="Document processed and indexed successfully",
                processing_time=processing_time,
                chunks_created=len(chunks),
                embeddings_generated=embeddings_generated,
                timing=timing
            )
            
            # Enhanced logging with detailed timing breakdown
            timing_details = []
            for key in ['s3_download', 'parsing', 'content_hashing', 'deduplication_check', 'chunking', 'embedding', 'elasticsearch_indexing']:
                if key in timing:
                    timing_details.append(f"{key.replace('_', ' ')}={timing[key]:.2f}s")
            
            timing_str = ", ".join(timing_details)
            logger.info(
                f" Processed {file_info.file_name} in {processing_time:.2f}s "
                f"({len(chunks)} chunks, {embeddings_generated} embeddings) | "
                f"Timing: [{timing_str}]"
            )
            
            return result
            
        except S3Exception as e:
            return self._create_error_result(s3_key, str(e), start_time, timing)
        except ParserException as e:
            return self._create_error_result(s3_key, str(e), start_time, timing)
        except ElasticsearchException as e:
            return self._create_error_result(s3_key, str(e), start_time, timing)
        except Exception as e:
            logger.error(f"Unexpected error processing {s3_key}", exc_info=True)
            return self._create_error_result(s3_key, str(e), start_time, timing)
    
    def process_batch(
        self,
        s3_keys: List[str]
    ) -> List[IngestionResult]:
        """
        Process multiple files in batch
        
        Args:
            s3_keys: List of S3 object keys
            
        Returns:
            list: List of IngestionResult objects
        """
        results = []
        
        logger.info(f"Processing batch of {len(s3_keys)} files")
        
        for s3_key in s3_keys:
            result = self.process_file(s3_key)
            results.append(result)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Batch complete: {success_count}/{len(s3_keys)} successful"
        )
        
        return results
    
    def process_all_files(self, prefix: str = "") -> Dict[str, Any]:
        """
        Process all files in S3 bucket with detailed timing and statistics
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            dict: Processing statistics with timing breakdown
        """
        logger.info(f"Processing all files with prefix: {prefix or '(none)'}")
        
        batch_start = time.time()
        
        # Create index if not exists
        self.elasticsearch_service.create_index(delete_if_exists=False)
        
        # Get all files
        s3_keys = self.s3_service.list_files(prefix)
        
        if not s3_keys:
            logger.info("No files found to process")
            return {
                "total_files": 0,
                "processed": 0,
                "failed": 0,
                "duplicates": 0,
                "success_rate": 0.0
            }
        
        logger.info(f"Found {len(s3_keys)} files in S3")
        
        # Process in batches
        results = []
        batch_size = self.pipeline_config.batch_size
        
        for i in range(0, len(s3_keys), batch_size):
            batch = s3_keys[i:i + batch_size]
            batch_results = self.process_batch(batch)
            results.extend(batch_results)
        
        # Calculate detailed statistics
        total_files = len(results)
        success_count = sum(1 for r in results if r.success and not r.is_duplicate)
        duplicate_count = sum(1 for r in results if r.is_duplicate)
        failed_count = sum(1 for r in results if not r.success)
        
        # Aggregate timing statistics
        timing_stats = {}
        for result in results:
            if result.timing:
                for key, value in result.timing.items():
                    if key != 'total':
                        if key not in timing_stats:
                            timing_stats[key] = []
                        timing_stats[key].append(value)
        
        # Calculate averages
        avg_timing = {key: sum(values)/len(values) for key, values in timing_stats.items()}
        
        total_time = time.time() - batch_start
        
        stats = {
            "total_files": total_files,
            "processed": success_count,
            "duplicates": duplicate_count,
            "failed": failed_count,
            "success_rate": (success_count / total_files) * 100 if total_files else 0.0,
            "total_processing_time": total_time,
            "avg_timing": avg_timing
        }
        
        # Enhanced summary logging
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 INGESTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"📁 Prefix: {prefix or '(all files)'}")
        logger.info(f"📈 Total Files: {total_files}")
        logger.info(f" Successfully Processed: {success_count}")
        logger.info(f"🔁 Duplicates Skipped: {duplicate_count}")
        logger.info(f" Failed: {failed_count}")
        logger.info(f"📊 Success Rate: {stats['success_rate']:.1f}%")
        logger.info(f"⏱️  Total Time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        
        if avg_timing:
            logger.info("")
            logger.info("⏱️  AVERAGE TIMING PER FILE:")
            for key, value in sorted(avg_timing.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   • {key.replace('_', ' ').title()}: {value:.3f}s")
        
        logger.info("=" * 80)
        logger.info("")
        
        return stats
        
        logger.info(
            f" Pipeline complete: {success_count}/{len(s3_keys)} successful "
            f"({stats['success_rate']:.1f}%)"
        )
        
        return stats
    
    def _get_file_type(self, file_name: str) -> FileType:
        """
        Determine file type from filename
        
        Args:
            file_name: Name of the file
            
        Returns:
            FileType: Detected file type
            
        Raises:
            IngestionException: If file type not supported
        """
        extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        try:
            return FileType(extension)
        except ValueError:
            raise IngestionException(f"Unsupported file type: {extension}")
    
    def _parse_document(
        self,
        file_content: bytes,
        file_name: str,
        file_type: FileType
    ) -> Dict[str, Any]:
        """
        Parse document using appropriate parser
        
        Args:
            file_content: File bytes
            file_name: File name
            file_type: File type
            
        Returns:
            dict: Parsed result
        """
        parser = self.parsers.get(file_type)
        
        if not parser:
            raise ParserException(f"No parser available for {file_type.value}")
        
        return parser.parse(file_content, file_name)
    
    def _create_error_result(
        self,
        s3_key: str,
        error_msg: str,
        start_time: float,
        timing: Optional[Dict[str, float]] = None
    ) -> IngestionResult:
        """Create error result"""
        return IngestionResult(
            success=False,
            file_name=s3_key.split('/')[-1],
            file_path=f"s3://{self.s3_service.bucket_name}/{s3_key}",
            message="Processing failed",
            error=error_msg,
            processing_time=time.time() - start_time,
            timing=timing or {}
        )
