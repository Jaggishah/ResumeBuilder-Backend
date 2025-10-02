from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re

class ResumeAgent:
    def __init__(self, model_name="gemma3:1b"):
        """Initialize the ResumeAgent with Ollama model"""
        self.llm = OllamaLLM(model=model_name)
        self.output_parser = StrOutputParser()
        self._setup_prompt_templates()
    
    def _setup_prompt_templates(self):
        """Setup different prompt templates for various resume tasks"""
        self.resume_template = PromptTemplate(
            input_variables=["current_content", "instructions"],
            template="""You are a professional resume parser. Your task is to extract resume information and return it as a JSON object.

Given the following resume content:
{current_content}

Parse the content and create a JSON structure following these guidelines:
{instructions}

"""
        )
        
        # Enhancement template for improving resume content
        self.enhancement_template = PromptTemplate(
            input_variables=["section_name", "content", "instructions"],
            template="""You are a professional resume enhancement expert. Your task is to enhance and improve resume content.

Given the following Section name: {section_name}
Given the following Section Content:
{content}

Instructions: {instructions}

"""
        )
        
        # Create the chains using modern LangChain pattern
        self.resume_chain = self.resume_template | self.llm | self.output_parser
        self.enhancement_chain = self.enhancement_template | self.llm | self.output_parser
    
    def _clean_json_response(self, response: str) -> str:
        """Clean the response to ensure it's valid JSON"""
        # Remove any markdown code blocks
        response = response.replace("```json", "").replace("```", "")
        # Remove leading/trailing whitespace
        response = response.strip()
        return response

    async def process_resume(self, current_content: str, instructions: str) -> str:
        """
        Process the resume content with given instructions
        
        Args:
            current_content (str): Current resume content
            instructions (str): Instructions for modifying the resume
            
        Returns:
            str: Modified resume content as JSON string
        """
        try:
            # Use the modern chain invoke method
            response = await self.resume_chain.ainvoke({
                "current_content": current_content,
                "instructions": instructions
            })
            
            # Clean any markdown or formatting
            cleaned_response = self._clean_json_response(response)
            
            # Try to parse JSON to validate it
            try:
                json.loads(cleaned_response)
                return cleaned_response
            except json.JSONDecodeError as e:
                print(f"LLM returned invalid JSON. Error: {e}")
                print("Attempting to fix JSON format...")
                # Try to extract JSON from the response if it's not properly formatted
                json_match = re.search(r'(\{.*\})', cleaned_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    # Validate the extracted JSON
                    json.loads(json_str)  # Will raise error if still invalid
                    return json_str
                raise
                
        except Exception as e:
            print(f"Error processing resume: {e}")
            raise
    
    async def enhance_content(self, section_name: str, content: str, instructions: str = None) -> str:
        """
        Enhance specific resume section content
        
        Args:
            section_name (str): Name of the resume section being enhanced
            content (str): Current content to enhance
            instructions (str): Specific instructions for enhancement
            
        Returns:
            str: Enhanced content
        """
        try:
            if not instructions:
                instructions = f"Make this more professional, impactful, and compelling. Use action verbs, quantify achievements where possible, and ensure clarity."
            
            # Use the enhancement chain
            response = await self.enhancement_chain.ainvoke({
                "section_name": section_name,
                "content": content,
                "instructions": instructions
            })
            
            # Clean the response (remove any extra formatting)
            enhanced_content = response.strip()
            
            return enhanced_content
            
        except Exception as e:
            print(f"Error enhancing content: {e}")
            raise
        