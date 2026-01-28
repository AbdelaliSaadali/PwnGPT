from utils_pdf import generate_pdf_report
import os

with open('/Users/mac/.gemini/antigravity/brain/9a433abb-6e44-417a-956f-56312dce4ffe/sample_writeup.md', 'r') as f:
    text = f.read()

generate_pdf_report(text, 'sample_report.pdf', logo_path='PwnGPT.png')
print('PDF Generated successfully.')
