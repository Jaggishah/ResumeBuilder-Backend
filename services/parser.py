import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import Dict, List, Any
import yaml
from .agent import ResumeAgent
import asyncio

class PDFResumeParser:
    def __init__(self):
        """Initialize the PDF resume parser with LLM agent"""
        self.template_content = None
    
    def extract_raw_text(self, pdf_path: str) -> str:
        """Extract raw text from PDF"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                full_text += text + "\n"
            
            doc.close()
            return full_text.strip()
            
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize the extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple empty lines to double
        text = re.sub(r'\n\s*\n', '\n\n', text)       # Clean double spacing
        text = re.sub(r'[ \t]+', ' ', text)           # Multiple spaces to single
        text = re.sub(r'[ \t]*\n[ \t]*', '\n', text)  # Remove spaces around newlines
        
        # Fix common PDF extraction issues
        text = text.replace('•', '- ')
        text = text.replace('◦', '- ')
        text = text.replace('▪', '- ')
        text = text.replace('○', '- ')
        text = text.replace('\u2022', '- ')  # Unicode bullet
        
        # Remove page numbers and headers/footers (common patterns)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip likely page numbers
            if re.match(r'^Page \d+$|^\d+$', line):
                continue
            
            # Skip very short lines that are likely artifacts
            if len(line) < 2:
                continue
                
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def extract_structured_sections(self, text: str) -> Dict[str, str]:
        """Attempt to identify and separate different resume sections"""
        
        # Common section headers (case insensitive)
        section_patterns = {
            'contact': r'(contact|personal|info)',
            'summary': r'(summary|objective|profile|about)',
            'experience': r'(experience|employment|work|career|professional)',
            'education': r'(education|academic|qualification|degree)',
            'skills': r'(skills|competencies|technical|technologies)',
            'projects': r'(projects|portfolio)',
            'certifications': r'(certification|certificate|credential)',
            'achievements': r'(achievement|award|honor|accomplishment)',
            'volunteer': r'(volunteer|community|service)',
            'languages': r'(language|linguistic)',
            'interests': r'(interest|hobby|personal)'
        }
        
        sections = {'raw_text': text}
        lines = text.split('\n')
        current_section = 'unknown'
        section_content = {}
        
        for line in lines:
            line_clean = line.strip()
            
            # Check if this line is a section header
            found_section = None
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line_clean, re.IGNORECASE):
                    # Additional check: section headers are usually short and may be all caps
                    if len(line_clean) < 50:
                        found_section = section_name
                        break
            
            if found_section:
                current_section = found_section
                if current_section not in section_content:
                    section_content[current_section] = []
            else:
                # Add content to current section
                if current_section not in section_content:
                    section_content[current_section] = []
                if line_clean:  # Only add non-empty lines
                    section_content[current_section].append(line_clean)
        
        # Convert lists to strings
        for section, content in section_content.items():
            sections[section] = '\n'.join(content)
        
        return sections
    
    def create_llm_prompt(self, pdf_path: str) -> str:
        """Create a complete prompt for LLM processing"""
        
        # Extract and clean text
        raw_text = self.extract_raw_text(pdf_path)
        if not raw_text:
            return "Error: Could not extract text from PDF"
        
        cleaned_text = self.clean_text(raw_text)
        filename = Path(pdf_path).name
        
        # Try to identify sections
        sections = self.extract_structured_sections(cleaned_text)
        
        # Create comprehensive prompt
        prompt = f"""RESUME PARSING REQUEST
{'='*60}

RAW RESUME TEXT:
{'-'*30}
{cleaned_text}
{'-'*30}

DETECTED SECTIONS:
"""
        
        # Add detected sections if any were found
        for section_name, content in sections.items():
            if section_name != 'raw_text' and content.strip():
                prompt += f"\n{section_name.upper()}:\n{content}\n"
        
        prompt += f"""
{'-'*30}


"""

        return prompt
    
    def save_prompt_to_file(self, pdf_path: str, output_file: str = None):
        """Save the generated LLM prompt to a text file"""
        
        prompt = self.create_llm_prompt(pdf_path)
        
        if output_file is None:
            output_file = f"{Path(pdf_path).stem}_llm_prompt.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        print(f"LLM prompt saved to: {output_file}")
        return prompt

    def run(self,path:str):
        
        # Path to your PDF resume
        pdf_path = path  # Change this to your PDF file
        
        if not Path(pdf_path).exists():
            print(f"PDF file not found: {pdf_path}")
            print("Please place your resume PDF in the same directory.")
            return
        
        print("Parsing PDF resume for LLM processing...")
        print("="*50)

        print("\n2. Creating LLM prompt...")
        


        return self.save_prompt_to_file(pdf_path)
    


