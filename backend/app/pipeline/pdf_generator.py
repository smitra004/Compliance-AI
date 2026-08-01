"""ReportLab PDF compliance audit report generator."""
from __future__ import annotations

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from app.models import ScanRecord

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        # No header/footer on cover page
        if self._pageNumber == 1:
            return
            
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#51596B"))
        
        # Draw running header
        self.drawString(54, 750, "ComplianceAI Audit Report — Confidential")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 742, 558, 742)
        
        # Draw running footer
        self.line(54, 55, 558, 55)
        self.drawString(54, 42, "nexuszenith compliance checker confidential")
        self.drawRightString(558, 42, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def escape_html(text: str) -> str:
    """Escapes XML reserved characters to prevent ReportLab Paragraph compiler crash."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


def generate_pdf_report(record: ScanRecord) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor("#16120E"),
        alignment=0, # Left-aligned
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#51596B"),
        spaceAfter=30
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#16120E"),
        spaceBefore=15,
        spaceAfter=15
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#16120E")
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#16120E")
    )

    center_style = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        alignment=1
    )

    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.white
    )

    story = []

    # ─── COVER PAGE ───
    story.append(Spacer(1, 40))
    # Brand logo accent
    story.append(Paragraph("<font size=10 color='#C9A96E'><b>PLATFORM COMPLIANCE AUDIT</b></font>", body_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("ComplianceAI Audit Report", title_style))
    story.append(Paragraph("Automated Document Verification & RAG Grounding Verdict", subtitle_style))
    
    # Divider line
    divider = Table([[""]], colWidths=[504])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor("#C9A96E")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0)
    ]))
    story.append(divider)
    story.append(Spacer(1, 30))

    # Metadata Grid
    created_str = record.created_at.strftime("%B %d, %Y at %I:%M %p UTC") if isinstance(record.created_at, datetime) else str(record.created_at)
    metadata_data = [
        [Paragraph("Document Name:", label_style), Paragraph(escape_html(record.document_name), body_style)],
        [Paragraph("Integrity Check (SHA-256):", label_style), Paragraph(escape_html(record.sha256_hash or "N/A"), body_style)],
        [Paragraph("Audit Timestamp:", label_style), Paragraph(escape_html(created_str), body_style)],
        [Paragraph("Requested By:", label_style), Paragraph(escape_html(record.uploaded_by), body_style)],
        [Paragraph("Compliance Target Status:", label_style), Paragraph(escape_html("Active / Monitored Registry"), body_style)]
    ]
    metadata_table = Table(metadata_data, colWidths=[160, 344], hAlign='LEFT')
    metadata_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 40))

    # Compliance Score KPI Widget
    score = record.compliance_score
    if score >= 85:
        score_color = colors.HexColor("#3B8E2F")
        score_bg = colors.HexColor("#EAF5E9")
        status_label = "COMPLIANT"
    elif score >= 60:
        score_color = colors.HexColor("#E08A0B")
        score_bg = colors.HexColor("#FFF8EA")
        status_label = "MODERATE RISK"
    else:
        score_color = colors.HexColor("#E2453C")
        score_bg = colors.HexColor("#FEECEB")
        status_label = "CRITICAL RISK"

    kpi_data = [
        [Paragraph(f"<font size=48 color='{score_color.hexval()}'><b>{score}%</b></font>", center_style)],
        [Paragraph(f"<font size=10 color='{score_color.hexval()}'><b>{status_label}</b></font>", center_style)]
    ]
    kpi_table = Table(kpi_data, colWidths=[240], hAlign='CENTER')
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), score_bg),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
        ('INNERGRID', (0,0), (-1,-1), 0.5, score_color),
        ('BOX', (0,0), (-1,-1), 1.5, score_color),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 40))

    # Summary Text Box
    story.append(Paragraph("<b>EXECUTIVE CONSENSUS SUMMARY</b>", label_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(escape_html(record.summary), body_style))
    
    story.append(PageBreak())

    # ─── DETAILED FINDINGS PAGE ───
    story.append(Paragraph("Detailed Audit Findings", h2_style))
    story.append(Paragraph("Below is the comprehensive ledger of violations compiled by the GDPR, Security, and Legal agents, grounded in matching reference guidelines.", body_style))
    story.append(Spacer(1, 15))

    # Findings Table
    table_data = [[
        Paragraph("<b>ID / Severity</b>", header_style),
        Paragraph("<b>Violation</b>", header_style),
        Paragraph("<b>Excerpt & Explanation</b>", header_style),
        Paragraph("<b>Policy Citation</b>", header_style)
    ]]

    for idx, v in enumerate(record.violations):
        sev_color = "#B85C38" if v.severity == "P1" else "#C2683E" if v.severity == "P2" else "#B8923A" if v.severity == "P3" else "#5A7A6A"
        sev_text = f"<b>{escape_html(v.severity.value)}</b><br/><font size=8>{escape_html(v.severity.label)}</font>"
        
        reg_label = {
            "gdpr": "GDPR Privacy",
            "iso27001": "ISO 27001",
            "sox": "SOX Financial",
            "internal_security": "Internal Security",
            "internal_hr": "Internal HR",
            "custom": "Custom Policy"
        }.get(v.source_regulation.value if hasattr(v.source_regulation, "value") else v.source_regulation, v.source_regulation)

        articles_line = ""
        if getattr(v, "regulation_articles", None):
            articles_esc = escape_html(" · ".join(v.regulation_articles))
            articles_line = f"<br/><font size=7.5 color='#B8923A'><b>Maps to:</b> {articles_esc}</font>"

        col1 = Paragraph(f"<font color='{sev_color}'>{sev_text}</font>", body_style)
        col2 = Paragraph(f"<b>{escape_html(v.title)}</b><br/><font size=8 color='#5C5248'>{escape_html(reg_label)}</font>{articles_line}", body_style)
        
        explanation_esc = escape_html(v.explanation)
        excerpt_esc = escape_html(v.excerpt)
        col3 = Paragraph(f"{explanation_esc}<br/><br/><i>Excerpt:</i> <font face='Courier' size=8.5 color='#333'>\"{excerpt_esc}\"</font>", body_style)
        
        if v.citation:
            cite_text_esc = escape_html(v.citation.text)
            cite_clause_esc = escape_html(v.citation.clause)
            cite_reg = {
                "gdpr": "GDPR",
                "iso27001": "ISO 27001",
                "sox": "SOX",
                "internal_security": "Int-Sec",
                "internal_hr": "Int-HR",
                "custom": "Custom"
            }.get(v.citation.regulation.value if hasattr(v.citation.regulation, "value") else v.citation.regulation, v.citation.regulation)
            col4 = Paragraph(f"<b>{escape_html(cite_reg)} {cite_clause_esc}</b><br/><font size=7.5 color='#51596B'>\"{cite_text_esc}\"<br/><i>Match: {(v.citation.similarity * 100):.0f}%</i></font>", body_style)
        else:
            col4 = Paragraph("<font color='#8A909C'>No citation grounding available.</font>", body_style)
            
        table_data.append([col1, col2, col3, col4])

    # 90pt, 110pt, 184pt, 120pt = 504pt (fits page margins perfectly)
    findings_table = Table(table_data, colWidths=[65, 105, 204, 130])
    findings_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#16120E")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    
    story.append(findings_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
