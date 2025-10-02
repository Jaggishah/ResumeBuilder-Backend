from services import parser,agent,yaml_converter, json_parser,rendercvAgent

from pathlib import Path
import asyncio
import yaml




async def main():
    base_dir = Path(__file__).parent
    parser_instance = parser.PDFResumeParser()
    agent_instance = agent.ResumeAgent()
    instructions = (base_dir / "prompts" / "instructions.txt").read_text(encoding="utf-8")
    pdf_path = str(base_dir / "sample.pdf")  # Source PDF to analyze

    # Extract content from source PDF
    prompt = parser_instance.extract_raw_text(pdf_path)
    print("Reading source PDF content...")
    
    # Get modified content in JSON format
    print("Processing with LLM...")
    json_content = await agent_instance.process_resume(current_content=prompt, instructions=instructions)
    print("\nReceived JSON content from LLM")

    
    # Parse JSON content
    resume_data = json_parser.ResumeJSONParser().parse_json(json_content)
    if not resume_data:
        print("Error parsing JSON content. Please check the LLM output.")
        return
    
    # Create output PDF
    output_pdf = str(base_dir / "generated_resume.pdf")
    yaml_export_path = str(base_dir / "modified_resume.yaml")
    print(f"\nCreating PDF: {output_pdf}")
    
    try:
        # Generate YAML content
        yaml_str = yaml_converter.convert_to_rendercv(resume_data)
        
        # Write YAML to file
        with open(yaml_export_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        print(f"YAML exported to {yaml_export_path}")
        
        # Validate YAML structure
        cv_dict = yaml.safe_load(yaml_str)
        if 'cv' not in cv_dict:
            print("ERROR: YAML structure missing 'cv' key")
            return
        
        print("YAML structure validated successfully")
        
        # Create PDF using async RenderCV function
        success = await rendercvAgent.RenderCVAgent().create_pdf_with_rendercv(yaml_export_path, output_pdf)
        
        if success:
            print(f"Resume successfully created! Check {output_pdf}")
        else:
            print("Error creating PDF. Please check the YAML format and try again.")
            
    except Exception as e:
        print(f"Error in PDF generation process: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())