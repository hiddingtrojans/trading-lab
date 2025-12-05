"""
PDF Export for Research Reports
"""

from io import BytesIO
from datetime import datetime
from typing import List, Optional
import sys

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted, Table, TableStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFExporter:
    """Export research analysis to PDF."""
    
    def __init__(self, ticker: str, output_path: Optional[str] = None):
        self.ticker = ticker.upper()
        if output_path:
            self.output_path = output_path
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_path = f"research_{self.ticker}_{timestamp}.pdf"
        
        self.story = []
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Setup custom styles for the PDF."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor='#1a1a1a',
            spaceAfter=12,
            alignment=TA_CENTER,
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor='#2c3e50',
            spaceAfter=8,
            spaceBefore=12,
        ))
        
        # Subsection
        self.styles.add(ParagraphStyle(
            name='Subsection',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor='#34495e',
            spaceAfter=6,
            spaceBefore=8,
        ))
        
        # Body text with proper wrapping
        self.styles.add(ParagraphStyle(
            name='Body',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor='#333333',
            spaceAfter=8,
            leading=14,
            alignment=TA_LEFT,
            wordWrap='CJK',  # Better word wrapping
        ))
        
        # Bullet point style
        bullet_style_name = 'CustomBullet'
        try:
            # Try to access it - if it doesn't exist, create it
            _ = self.styles[bullet_style_name]
        except KeyError:
            # Style doesn't exist, create it
            self.styles.add(ParagraphStyle(
                name=bullet_style_name,
                parent=self.styles['Body'],
                leftIndent=20,
                bulletIndent=10,
                spaceAfter=6,
            ))
        
        # Header style for subsections
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor='#2c3e50',
            spaceAfter=6,
            spaceBefore=10,
            fontName='Helvetica-Bold',
        ))
        
        # Code/Monospace (for tables)
        self.styles.add(ParagraphStyle(
            name='Monospace',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Courier',
            textColor='#333333',
            spaceAfter=4,
        ))
        
        # Small text for metadata
        self.styles.add(ParagraphStyle(
            name='Small',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor='#666666',
            spaceAfter=4,
        ))
    
    def add_title(self, title: str, subtitle: Optional[str] = None):
        """Add title page."""
        self.story.append(Spacer(1, 0.5*inch))
        self.story.append(Paragraph(title, self.styles['CustomTitle']))
        if subtitle:
            self.story.append(Spacer(1, 0.2*inch))
            self.story.append(Paragraph(subtitle, self.styles['Body']))
        self.story.append(Spacer(1, 0.3*inch))
        self.story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['Body']
        ))
        self.story.append(PageBreak())
    
    def add_section(self, title: str):
        """Add a section header."""
        self.story.append(Spacer(1, 0.2*inch))
        self.story.append(Paragraph(title, self.styles['SectionHeader']))
        self.story.append(Spacer(1, 0.1*inch))
    
    def add_subsection(self, title: str):
        """Add a subsection header."""
        self.story.append(Spacer(1, 0.1*inch))
        self.story.append(Paragraph(title, self.styles['Subsection']))
    
    def _clean_text(self, text: str) -> str:
        """Clean and escape text for PDF."""
        import html
        # Replace emojis with text equivalents
        replacements = {
            '🔬': 'RESEARCH',
            '📊': 'METRICS',
            '💰': 'VALUATION',
            '🏢': 'BUSINESS',
            '📍': 'LOCATION',
            '📈': '↑',
            '📉': '↓',
            '✅': '✓',
            '⚠️': 'WARNING',
            '🚀': 'ROCKET',
            '🟢': '●',
            '🔴': '●',
            '🟠': '●',
            '⚪': '○',
            '🥇': '1st',
            '🥈': '2nd',
            '🥉': '3rd',
        }
        for emoji, replacement in replacements.items():
            text = text.replace(emoji, replacement)
        # Escape HTML characters
        text = html.escape(text)
        return text
    
    def add_text(self, text: str, preserve_formatting: bool = False):
        """Add body text with proper wrapping."""
        if preserve_formatting:
            # Use Preformatted for tables and fixed-width text
            self.story.append(Preformatted(text, self.styles['Monospace']))
        else:
            # Process text line by line with better handling
            lines = text.split('\n')
            in_list = False
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines (but add small spacer)
                if not line:
                    if not in_list:
                        self.story.append(Spacer(1, 0.08*inch))
                    continue
                
                # Skip separator lines
                if line.startswith('═') or line.startswith('─') or line.startswith('━') or line.startswith('│'):
                    continue
                
                # Handle headers (lines that are all caps or have specific patterns)
                if (line.isupper() and len(line) > 5 and len(line) < 50) or \
                   (line.endswith(':') and len(line) < 50):
                    # Subsection header
                    cleaned = self._clean_text(line)
                    self.story.append(Spacer(1, 0.1*inch))
                    self.story.append(Paragraph(f"<b>{cleaned}</b>", self.styles['SubHeader']))
                    in_list = False
                    continue
                
                # Handle bullet points
                if line.startswith('•') or line.startswith('-') or line.startswith('✓') or line.startswith('⚠'):
                    cleaned = self._clean_text(line)
                    # Use bullet style if available, otherwise use Body
                    try:
                        bullet_style = self.styles['CustomBullet']
                    except KeyError:
                        bullet_style = self.styles['Body']
                    self.story.append(Paragraph(f"&bull; {cleaned[1:].strip()}", bullet_style))
                    in_list = True
                    continue
                
                # Handle numbered items
                if line[0].isdigit() and (line[1] == '.' or line[1] == ')'):
                    cleaned = self._clean_text(line)
                    try:
                        bullet_style = self.styles['CustomBullet']
                    except KeyError:
                        bullet_style = self.styles['Body']
                    self.story.append(Paragraph(cleaned, bullet_style))
                    in_list = True
                    continue
                
                # Regular paragraph - use proper wrapping
                cleaned = self._clean_text(line)
                
                # If it's a very long line, it's likely a paragraph that needs wrapping
                if len(line) > 80:
                    # This is a paragraph - let Paragraph handle wrapping
                    self.story.append(Paragraph(cleaned, self.styles['Body']))
                else:
                    # Short line - might be a label or single item
                    self.story.append(Paragraph(cleaned, self.styles['Body']))
                
                in_list = False
    
    def add_page_break(self):
        """Add a page break."""
        self.story.append(PageBreak())
    
    def export(self) -> str:
        """Generate the PDF file."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF export. Install it with: pip install reportlab"
            )
        
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=letter,
            rightMargin=0.7*inch,
            leftMargin=0.7*inch,
            topMargin=0.7*inch,
            bottomMargin=0.7*inch,
        )
        
        doc.build(self.story)
        return self.output_path


def export_analysis_to_pdf(ticker: str, analysis_output: str, output_path: Optional[str] = None) -> str:
    """
    Export full analysis output to PDF.
    
    Args:
        ticker: Stock ticker
        analysis_output: The full text output from analysis
        output_path: Optional custom output path
    
    Returns:
        Path to generated PDF file
    """
    if not REPORTLAB_AVAILABLE:
        print("\n❌ PDF export requires 'reportlab' library.")
        print("   Install it with: pip install reportlab")
        sys.exit(1)
    
    exporter = PDFExporter(ticker, output_path)
    
    # Add title
    exporter.add_title(
        f"Deep Research Report: {ticker}",
        "Comprehensive Stock Analysis"
    )
    
    # Better section parsing - split by major section markers
    lines = analysis_output.split('\n')
    sections = []
    current_section = []
    current_title = None
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for step markers
        if '📍 Step' in line:
            # Save previous section
            if current_section:
                sections.append((current_title, '\n'.join(current_section)))
            # Start new section
            if ':' in line:
                current_title = line.split(':', 1)[1].strip()
            else:
                current_title = line.replace('📍', '').replace('Step', '').strip()
            current_section = []
            i += 1
            continue
        
        # Check for major section headers (long separator lines)
        if (line.startswith('═') and len(line) > 50) or \
           (line.startswith('─') and len(line) > 50):
            # Look for header in next few lines
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # If next line looks like a header (has emoji or is short and descriptive)
                if next_line and len(next_line) < 80 and \
                   (any(c in next_line for c in '🔬📊💰🏢📈📉✅⚠️🚀') or 
                    next_line.isupper() or
                    'ANALYSIS' in next_line.upper() or
                    'REPORT' in next_line.upper()):
                    # This might be a subsection header
                    if current_section:
                        sections.append((current_title, '\n'.join(current_section)))
                    current_title = next_line
                    current_section = []
                    i += 2  # Skip separator and header
                    continue
        
        current_section.append(line)
        i += 1
    
    # Add last section
    if current_section:
        sections.append((current_title, '\n'.join(current_section)))
    
    # Process each section
    for title, content in sections:
        if not content.strip():
            continue
        
        # Add section header if we have one
        if title:
            exporter.add_section(title)
        
        # Clean up content
        content = content.strip()
        
        if content:
            # Check if it looks like a table (has │ or structured columns)
            has_table_markers = '│' in content
            has_structured_columns = False
            
            # Check for structured data (multiple spaces, aligned columns)
            lines_check = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('─')]
            if len(lines_check) > 3:
                # Check if lines have similar structure (potential table)
                first_line = lines_check[0]
                if '  ' in first_line and len(first_line.split()) > 3:
                    has_structured_columns = True
            
            is_table = has_table_markers or has_structured_columns
            
            exporter.add_text(content, preserve_formatting=is_table)
    
    # Generate PDF
    pdf_path = exporter.export()
    return pdf_path

