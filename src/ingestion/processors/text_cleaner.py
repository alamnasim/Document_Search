"""
Text cleaning utilities for postprocessing document extraction outputs.
Handles cleaning of docling granite and other parser outputs.
"""

import re
from typing import Optional


class TextCleaner:
    """Cleans and normalizes extracted text from various document parsers."""
    
    def __init__(self):
        # Compile regex patterns for better performance
        self.location_pattern = re.compile(r'<loc_\d+>')
        self.html_tag_pattern = re.compile(r'</?[^>]+>')
        self.multiple_spaces = re.compile(r'\s{2,}')
        self.multiple_newlines = re.compile(r'\n{3,}')
        
    def clean_docling_output(self, text: str) -> str:
        """
        Clean docling granite output by removing location markers and HTML tags.
        
        Args:
            text: Raw text output from docling granite
            
        Returns:
            Cleaned text with HTML tags and location markers removed
            
        Example:
            Input: '<loc_0><_HTML_>Hello <br> World</p>'
            Output: 'Hello World'
        """
        if not text:
            return ""
        
        # Remove location markers (e.g., <loc_0>, <loc_500>)
        cleaned = self.location_pattern.sub('', text)
        
        # Replace <br> and <br/> tags with spaces
        cleaned = re.sub(r'<br\s*/?>', ' ', cleaned, flags=re.IGNORECASE)
        
        # Replace </p> tags with newlines to preserve paragraph structure
        cleaned = re.sub(r'</p>', '\n', cleaned, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags (including <_HTML_>, <p>, etc.)
        cleaned = self.html_tag_pattern.sub('', cleaned)
        
        # Normalize whitespace
        cleaned = self._normalize_whitespace(cleaned)
        
        return cleaned.strip()
    
    def clean_generic_html(self, text: str) -> str:
        """
        Remove HTML tags and normalize whitespace from generic HTML content.
        
        Args:
            text: Text with HTML tags
            
        Returns:
            Plain text without HTML tags
        """
        if not text:
            return ""
        
        # Replace common block elements with newlines
        block_elements = ['</p>', '</div>', '</h1>', '</h2>', '</h3>', 
                         '</h4>', '</h5>', '</h6>', '</li>', '</tr>']
        cleaned = text
        for element in block_elements:
            cleaned = re.sub(element, '\n', cleaned, flags=re.IGNORECASE)
        
        # Replace <br> with newlines
        cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
        
        # Remove all HTML tags
        cleaned = self.html_tag_pattern.sub('', cleaned)
        
        # Decode common HTML entities
        cleaned = self._decode_html_entities(cleaned)
        
        # Normalize whitespace
        cleaned = self._normalize_whitespace(cleaned)
        
        return cleaned.strip()
    
    def clean_ocr_artifacts(self, text: str) -> str:
        """
        Remove common OCR artifacts and special characters.
        
        Args:
            text: Text potentially containing OCR artifacts
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        cleaned = text
        
        # Remove common OCR artifacts
        artifacts = [
            r'\|',  # Vertical bars
            r'[•◦▪▫]',  # Bullet points (keep if needed)
            r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]',  # Control characters
        ]
        
        for pattern in artifacts:
            cleaned = re.sub(pattern, ' ', cleaned)
        
        # Fix common OCR mistakes (optional - can be expanded)
        replacements = {
            r'\bl\b': 'I',  # Single 'l' often misread as 'I'
            r'\bO\b': '0',  # Single 'O' often misread as '0'
        }
        
        for pattern, replacement in replacements.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Normalize whitespace
        cleaned = self._normalize_whitespace(cleaned)
        
        return cleaned.strip()
    
    def clean_paddleocr_output(self, text: str) -> str:
        """
        Clean PaddleOCR output by handling newlines and spacing issues.
        
        PaddleOCR often outputs text with:
        - Mid-sentence line breaks that should be spaces
        - Missing spaces between words
        - Multiple consecutive newlines
        
        Args:
            text: Raw text output from PaddleOCR
            
        Returns:
            Cleaned text with proper spacing and line breaks
            
        Example:
            Input: "The lion (Panthera leo) isa large catof the genus Panthera\nnative to Africa"
            Output: "The lion (Panthera leo) is a large cat of the genus Panthera native to Africa"
        """
        if not text:
            return ""
        
        cleaned = text
        
        # Fix missing spaces between words (common OCR errors)
        # Pattern 1: lowercase letter followed by uppercase letter without space
        cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
        
        # Pattern 2: Punctuation followed by letter without space (e.g., "India.It")
        cleaned = re.sub(r'([.!?])([A-Z])', r'\1 \2', cleaned)
        
        # Pattern 3: Fix common missing spaces - look for lowercase+common_word patterns
        # More precise: only match specific compound errors, not valid words
        # Examples: "isa " -> "is a ", "catof " -> "cat of "
        common_patterns = [
            (r'\bisa\b', 'is a'),
            (r'\bhasa\b', 'has a'),
            (r'\bwasa\b', 'was a'),
            (r'\bina\b', 'in a'),
            (r'\bona\b', 'on a'),
            (r'\bata\b', 'at a'),
            (r'\btoa\b', 'to a'),
            (r'\bfora\b', 'for a'),
            (r'\basa\b', 'as a'),
            (r'\bbya\b', 'by a'),
            (r'\boran\b', 'or an'),
            (r'\basan\b', 'as an'),
            # Only split if 3+ letters before suffix to avoid breaking valid words
            (r'\b([a-z]{3,})of\b', r'\1 of'),  # catof -> cat of (but not "of")
            (r'\b([a-z]{3,})to\b', r'\1 to'),  # goto -> go to (but not "to")
            (r'\b([a-z]{3,})it\b', r'\1 it'),  # makeit -> make it (but not "it")
        ]
        
        for pattern, replacement in common_patterns:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        # Replace single newlines that break sentences with spaces
        # Keep double newlines as paragraph breaks
        lines = cleaned.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                # Empty line - keep as paragraph break marker
                result_lines.append('')
                continue
            
            # Check if this line should join with previous
            if i > 0 and result_lines and result_lines[-1]:
                prev_line = result_lines[-1]
                # Join if previous line doesn't end with sentence-ending punctuation
                if not prev_line[-1] in '.!?:;':
                    result_lines[-1] = prev_line + ' ' + line
                    continue
            
            result_lines.append(line)
        
        # Join lines and handle paragraph breaks
        cleaned = '\n'.join(result_lines)
        
        # Collapse multiple newlines to maximum of 2 (paragraph break)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Clean up extra spaces
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        # Remove spaces before punctuation
        cleaned = re.sub(r' +([.,!?;:])', r'\1', cleaned)
        
        return cleaned.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace by collapsing multiple spaces and newlines.
        
        Args:
            text: Text with irregular whitespace
            
        Returns:
            Text with normalized whitespace
        """
        # Replace tabs with spaces
        text = text.replace('\t', ' ')
        
        # Collapse multiple spaces into one
        text = self.multiple_spaces.sub(' ', text)
        
        # Collapse multiple newlines into maximum of two
        text = self.multiple_newlines.sub('\n\n', text)
        
        # Remove spaces at line beginnings/ends
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    def _decode_html_entities(self, text: str) -> str:
        """
        Decode common HTML entities to their text equivalents.
        
        Args:
            text: Text with HTML entities
            
        Returns:
            Text with decoded entities
        """
        entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
        }
        
        result = text
        for entity, char in entities.items():
            result = result.replace(entity, char)
        
        return result
    
    def clean_all(self, text: str, source: str = "docling") -> str:
        """
        Apply all cleaning operations based on source type.
        
        Args:
            text: Raw text to clean
            source: Source of the text ("docling", "html", "ocr", "paddle_ocr")
            
        Returns:
            Fully cleaned text
        """
        if not text:
            return ""
        
        if source == "docling":
            cleaned = self.clean_docling_output(text)
        elif source == "html":
            cleaned = self.clean_generic_html(text)
        elif source == "ocr":
            cleaned = self.clean_ocr_artifacts(text)
        elif source == "paddle_ocr":
            cleaned = self.clean_paddleocr_output(text)
        else:
            # Default: clean HTML tags and normalize
            cleaned = self.clean_generic_html(text)
        
        return cleaned


# Convenience functions for quick usage
def clean_docling_text(text: str) -> str:
    """Quick function to clean docling granite output."""
    cleaner = TextCleaner()
    return cleaner.clean_docling_output(text)


def clean_html_text(text: str) -> str:
    """Quick function to clean HTML from text."""
    cleaner = TextCleaner()
    return cleaner.clean_generic_html(text)


def clean_text(text: str, source: str = "docling") -> str:
    """Quick function to clean text based on source."""
    cleaner = TextCleaner()
    return cleaner.clean_all(text, source)


if __name__ == "__main__":
    # Test examples
    cleaner = TextCleaner()
    
    # Test docling output
    docling_text = (
        "<loc_0><loc_0><loc_500><loc_500><_HTML_>The lion (Panthera leo) is a large cat "
        "of the genus Panthera <br> native to Africa and India. It has a <br> muscular, "
        "deep-chested <br> body, short, rounded head, round ears, and a hairy tuft at "
        "<br> the end of its tail. <br> </p>"
    )
    
    print("Original text:")
    print(docling_text)
    print("\nCleaned text:")
    print(cleaner.clean_docling_output(docling_text))
    print("\n" + "="*80)
    
    # Test HTML cleaning
    html_text = "<div><h1>Title</h1><p>This is a <br> paragraph</p></div>"
    print("\nHTML text:")
    print(html_text)
    print("\nCleaned HTML:")
    print(cleaner.clean_generic_html(html_text))
