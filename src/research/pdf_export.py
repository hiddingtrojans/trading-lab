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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
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
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='Body',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor='#333333',
            spaceAfter=6,
            leading=14,
        ))
        
        # Code/Monospace (for tables)
        self.styles.add(ParagraphStyle(
            name='Monospace',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Courier',
            textColor='#333333',
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
    
    def add_text(self, text: str, preserve_formatting: bool = False):
        """Add body text."""
        if preserve_formatting:
            # Use Preformatted for tables and fixed-width text
            self.story.append(Preformatted(text, self.styles['Monospace']))
        else:
            # Clean up text for paragraph formatting
            # Replace emojis with text equivalents
            text = text.replace('🔬', '[RESEARCH]')
            text = text.replace('📊', '[METRICS]')
            text = text.replace('💰', '[VALUATION]')
            text = text.replace('🏢', '[BUSINESS]')
            text = text.replace('📍', '[LOCATION]')
            text = text.replace('📈', '[UP]')
            text = text.replace('📉', '[DOWN]')
            text = text.replace('✅', '[CHECK]')
            text = text.replace('⚠️', '[WARNING]')
            text = text.replace('🚀', '[ROCKET]')
            text = text.replace('🟢', '[GREEN]')
            text = text.replace('🔴', '[RED]')
            text = text.replace('🟠', '[ORANGE]')
            text = text.replace('⚪', '[NEUTRAL]')
            
            # Split by lines and add as paragraphs
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    self.story.append(Spacer(1, 0.05*inch))
                elif line.startswith('═') or line.startswith('─') or line.startswith('━'):
                    # Skip separator lines
                    continue
                elif len(line) > 100 and not line.startswith('  '):
                    # Long line - split into paragraphs
                    self.story.append(Paragraph(line, self.styles['Body']))
                else:
                    # Short line or indented - preserve as is
                    self.story.append(Paragraph(line, self.styles['Body']))
    
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
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
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
    
    # Split output into sections by step markers
    sections = []
    current_section = []
    
    for line in analysis_output.split('\n'):
        if '📍 Step' in line or '═' * 50 in line or '═' * 60 in line or '═' * 70 in line:
            if current_section:
                sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    
    if current_section:
        sections.append('\n'.join(current_section))
    
    # Process each section
    for section in sections:
        if not section.strip():
            continue
        
        lines = section.split('\n')
        # Find section title
        title = None
        content_start = 0
        
        for i, line in enumerate(lines):
            if '📍 Step' in line:
                # Extract step title
                if ':' in line:
                    title = line.split(':', 1)[1].strip()
                else:
                    title = line.replace('📍', '').strip()
                content_start = i + 1
                break
            elif line.startswith('═') and len(line) > 20:
                # Section header
                title = lines[i+1] if i+1 < len(lines) else None
                content_start = i + 2
                break
        
        if title:
            exporter.add_section(title)
        
        # Add content
        content = '\n'.join(lines[content_start:])
        content = content.strip()
        
        if content:
            # Check if it looks like a table
            is_table = '│' in content or ('  ' in content and len([l for l in content.split('\n') if l.strip()]) > 3)
            exporter.add_text(content, preserve_formatting=is_table)
    
    # Generate PDF
    pdf_path = exporter.export()
    return pdf_path

