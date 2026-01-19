"""
CSV parser using pandas
"""
import io
from typing import Dict, Any
import logging
import pandas as pd

from .base_parser import BaseParser
from ..models.schemas import ParserConfig, DocumentMetadata, ExtractionMethod
from ..exceptions import ParserException


logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """Parser for CSV files using pandas"""
    
    def __init__(self, config: ParserConfig):
        """
        Initialize CSV parser
        
        Args:
            config: Parser configuration
        """
        super().__init__(config)
    
    def parse(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse CSV file using pandas
        
        Args:
            file_content: CSV file bytes
            file_name: Name of the CSV file
            
        Returns:
            dict: Extracted content and metadata
            
        Raises:
            ParserException: If parsing fails
        """
        try:
            self.logger.info(f"Parsing CSV: {file_name}")
            
            # Read CSV with pandas
            df = pd.read_csv(io.BytesIO(file_content))
            
            # Convert to text
            content = df.to_string()
            
            # Convert to structured data
            records = df.to_dict('records')
            
            if not self._validate_content(content):
                raise ParserException("Extracted content is empty or invalid")
            
            # Create metadata
            metadata = DocumentMetadata(
                extraction_method=ExtractionMethod.PANDAS,
                rows=len(df),
                columns=len(df.columns),
                column_names=list(df.columns)
            )
            
            self.logger.info(
                f"Successfully parsed CSV: {file_name} "
                f"({len(df)} rows, {len(df.columns)} columns)"
            )
            
            return self._create_result(content, metadata, records)
            
        except ParserException:
            raise
        except Exception as e:
            raise ParserException(
                f"Unexpected error parsing CSV {file_name}",
                original_error=e
            )
