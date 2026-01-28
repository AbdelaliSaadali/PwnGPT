from fpdf import FPDF
import os

class PwnGPTPDF(FPDF):
    def __init__(self, logo_path="PwnGPT.png"):
        super().__init__()
        self.logo_path = logo_path
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Logo
        if os.path.exists(self.logo_path):
             try:
                self.image(self.logo_path, 10, 8, 33)
             except: pass
        
        # Title
        self.set_font('Helvetica', 'B', 14)
        # Cyber Green Color
        self.set_text_color(0, 255, 65) 
        
        # Determine X position for right assignment
        # Width - Margin - Text Width is hard to calc exactly without specific text, 
        # but cell(0) extends to right margin.
        self.cell(0, 10, 'PwnGPT Operation Report', 0, 0, 'R')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def clean_text(text):
    """Removes unsupported characters."""
    try:
        # Encode to latin-1, ignore errors (drops chars), then decode back
        return text.encode('latin-1', 'ignore').decode('latin-1')
    except:
        return ""

def generate_pdf_report(md_text: str, output_path: str, logo_path: str = "PwnGPT.png"):
    pdf = PwnGPTPDF(logo_path)
    pdf.add_page()
    
    # Body Font
    pdf.set_font("Helvetica", size=11)
    
    # Simple Markdown Parser
    lines = md_text.split('\n')
    
    in_code_block = False
    
    for line in lines:
        line = line.strip()
        line = clean_text(line)
        
        # Skip empty lines if they are just whitespace (but keep some paragraph spacing)
        # We handle spacing via ln() calls below usually.
        
        if line.startswith("```"):
            in_code_block = not in_code_block
            if in_code_block:
                pdf.ln(2) # Spacing before code
                pdf.set_fill_color(30, 30, 30) 
                pdf.set_text_color(200, 200, 200)
                pdf.set_font("Courier", size=10)
            else:
                pdf.set_fill_color(255, 255, 255)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", size=11)
                pdf.ln(2) # Spacing after code
            continue
            
        # Ensure we are at the left margin
        pdf.set_x(15)
        
        if in_code_block:
             # Code block - Fixed width to ensure background fills
             pdf.multi_cell(0, 5, line, fill=True)
             
        else:
            # Headers
            if line.startswith("# "):
                pdf.ln(6)
                pdf.set_font("Helvetica", 'B', 16)
                pdf.set_text_color(0, 200, 50)
                pdf.multi_cell(0, 8, line.replace("# ", ""))
                pdf.set_text_color(0, 0, 0) 
                pdf.set_font("Helvetica", size=11)
                
            elif line.startswith("## "):
                pdf.ln(4)
                pdf.set_font("Helvetica", 'B', 14)
                pdf.set_text_color(0, 150, 40)
                pdf.multi_cell(0, 8, line.replace("## ", ""))
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", size=11)
                
            elif line.startswith("### "):
                pdf.ln(2)
                pdf.set_font("Helvetica", 'B', 12)
                pdf.multi_cell(0, 6, line.replace("### ", ""))
                pdf.set_font("Helvetica", size=11)
                
            elif line.startswith("- "):
                 pdf.multi_cell(0, 6, f"  - {line[2:]}")

            else:
                # Normal text
                clean_line = line.replace("**", "")
                if clean_line:
                    pdf.multi_cell(0, 6, clean_line)

    pdf.output(output_path)
