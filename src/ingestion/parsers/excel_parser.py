"""
Excel parser using pandas
"""
import io
from typing import Dict, Any
import logging
import pandas as pd

from .base_parser import BaseParser
from ..models.schemas import ParserConfig, DocumentMetadata, ExtractionMethod
from ..exceptions import ParserException


logger = logging.getLogger(__name__)


class ExcelParser(BaseParser):
    """Parser for Excel files using pandas"""
    
    def __init__(self, config: ParserConfig):
        """
        Initialize Excel parser
        
        Args:
            config: Parser configuration
        """
        super().__init__(config)
    
    def parse(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse Excel file using pandas
        
        Args:
            file_content: Excel file bytes
            file_name: Name of the Excel file
            
        Returns:
            dict: Extracted content and metadata
            
        Raises:
            ParserException: If parsing fails
        """
        try:
            self.logger.info(f"Parsing Excel: {file_name}")
            
            # Read Excel with pandas
            excel_file = pd.ExcelFile(io.BytesIO(file_content))
            
            all_content = []
            all_records = {}
            total_rows = 0
            
            # Process each sheet
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheet_content = f"--- Sheet: {sheet_name} ---\n{df.to_string()}"
                all_content.append(sheet_content)
                all_records[sheet_name] = df.to_dict('records')
                total_rows += len(df)
            
            content = "\n\n".join(all_content)
            
            if not self._validate_content(content):
                raise ParserException("Extracted content is empty or invalid")
            
            # Create metadata
            metadata = DocumentMetadata(
                extraction_method=ExtractionMethod.PANDAS,
                sheets=excel_file.sheet_names,
                rows=total_rows
            )
            
            self.logger.info(
                f"Successfully parsed Excel: {file_name} "
                f"({len(excel_file.sheet_names)} sheets, {total_rows} rows)"
            )
            
            return self._create_result(content, metadata, all_records)
            
        except ParserException:
            raise
        except Exception as e:
            raise ParserException(
                f"Unexpected error parsing Excel {file_name}",
                original_error=e
            )
