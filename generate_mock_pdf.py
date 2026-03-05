from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def create_mock_statement(filename, transactions):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>MOCK BANK STATEMENT - ACCOUNT: 1234-5678</b>", styles['Heading1']))
    elements.append(Paragraph("Statement Period: Jan 01, 2026 - Jan 31, 2026", styles['Normal']))
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    
    # Table Header
    data = [["Date", "Description", "Amount"]]
    data.extend(transactions)
    
    t = Table(data, colWidths=[100, 300, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    
    elements.append(t)
    doc.build(elements)


def create_encrypted_statement(filename, transactions, password):
    """Create a password-protected PDF statement using pikepdf.

    Steps:
      1. Generate an unencrypted PDF via reportlab.
      2. Encrypt it with pikepdf using the given password.
    """
    import tempfile, os
    import pikepdf

    # Build the unencrypted PDF first
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    create_mock_statement(tmp.name, transactions)

    # Encrypt it
    pdf = pikepdf.open(tmp.name)
    pdf.save(
        filename,
        encryption=pikepdf.Encryption(owner=password, user=password, R=6),
    )
    pdf.close()
    os.remove(tmp.name)


if __name__ == "__main__":
    txns = [
        ["2026-01-02", "PAYROLL DEPOSIT - TECH CORP", "5000.00"],
        ["2026-01-03", "WHOLE FOODS MARKET", "-150.25"],
        ["2026-01-05", "UBER RIDE", "-24.50"],
        ["2026-01-10", "NETFLIX SUB", "-15.99"],
        ["2026-01-12", "AMAZON WEBSERVICES", "-45.00"],
        ["2026-01-15", "RENT PAYMENT", "-2000.00"],
        ["2026-01-18", "LOCAL COFFEE SHOP", "-5.50"],
        ["2026-01-20", "UNKNOWN MERCHANT LUXURY WATCHES", "-8500.00"], # Anomaly!
        ["2026-01-22", "SHELL GAS STATION", "-45.00"],
        ["2026-01-25", "ELECTRICITY BILL", "-85.00"],
        ["2026-01-28", "GYM MEMBERSHIP", "-50.00"],
    ]

    # Unencrypted version
    create_mock_statement("mock_statement.pdf", txns)
    print("Created mock_statement.pdf (unencrypted)")

    # Encrypted version (password: test123)
    create_encrypted_statement("mock_statement_encrypted.pdf", txns, "test123")
    print("Created mock_statement_encrypted.pdf (password: test123)")
