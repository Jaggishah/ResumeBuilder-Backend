from fastapi import HTTPException, UploadFile
from typing import Dict, Any, List
import uuid
import os
from pathlib import Path
import json
from bson import ObjectId
from beanie import PydanticObjectId
from services import parser, agent, yaml_converter, rendercvAgent, groq_agent
from database.models import Resume
from controllers.user_controller import UserController
import re
from langchain_community.document_loaders import WebBaseLoader

class ResumeController:
    def __init__(self):
        self.parser_instance = parser.PDFResumeParser()
        self.agent_instance = agent.ResumeAgent()
        self.groq_agent_instance = groq_agent.GroqAgent()
        self.user_controller = UserController()
        self.rendercv_agent = rendercvAgent.RenderCVAgent()

    async def upload_and_parse_resume(self, file: UploadFile, username: str, email: str = None, user_id: str = None) -> Dict[str, Any]:
        """Handle resume upload and parsing"""

        user = await self.user_controller.create_or_get_user(username, email=email)
        # Save uploaded file temporarily
        temp_path = f"temp_{uuid.uuid4()}.pdf"
        try:
            with open(temp_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Parse PDF content
            text_content = self.parser_instance.extract_raw_text(temp_path)
            
            if not text_content:
                raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
            # Get AI-parsed JSON
            instructions_path = Path(__file__).parent.parent / "prompts" / "instructions.txt"
            instructions = instructions_path.read_text(encoding="utf-8")
            
            json_content = await self.groq_agent_instance.process_resume(
                current_content=text_content, 
                instructions=instructions
            )

            print(f"LLM returned JSON content: {json_content}")
            
            # Parse and validate JSON
            try:
                parsed_data = json.loads(json_content)
            except json.JSONDecodeError:
                # Try to extract useful information using regex instead
                resume_data = {}

                # Extract basic info like name, email, phone
                name_match = re.search(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text_content)
                if name_match:
                    resume_data['name'] = name_match.group(1)

                email_match = re.search(r'[\w\.-]+@[\w\.-]+', text_content)
                if email_match:
                    resume_data['email'] = email_match.group(0)
                    
                phone_match = re.search(r'(\+\d{1,2}\s?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}', text_content)
                if phone_match:
                    resume_data['phone'] = phone_match.group(0)

                # Extract education - look for degrees
                education = []
                edu_sections = re.findall(r'(?:Education|EDUCATION).*?(?:Experience|EXPERIENCE|\n\n)', text_content, re.DOTALL)
                if edu_sections:
                    for section in edu_sections:
                        degrees = re.findall(r'((?:Bachelor|Master|PhD|B\.S\.|M\.S\.|M\.A\.|B\.A\.).*?)(?:\n\n|\d{4})', section, re.DOTALL)
                        for degree in degrees:
                            education.append({"degree": degree.strip()})
                    
                resume_data['education'] = education

                # Extract experience sections
                experience = []
                exp_sections = re.findall(r'(?:Experience|EXPERIENCE).*?(?:Education|EDUCATION|\n\n)', text_content, re.DOTALL)
                if exp_sections:
                    job_titles = re.findall(r'^(.*?)\n', exp_sections[0], re.MULTILINE)
                    for job in job_titles[:3]:  # Get first 3 jobs
                        if len(job.strip()) > 0:
                            experience.append({"title": job.strip()})

                resume_data['experience'] = experience

                # Use this as a fallback JSON
                json_content = json.dumps(resume_data)
                parsed_data = resume_data
                print("Warning: LLM returned invalid JSON, used regex extraction instead.")
                return {
                    "title": file.filename,
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "json_data": parsed_data
                }
            
            # Return parsed data directly without saving to database
            return {
                "title": file.filename,
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "json_data": parsed_data
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    async def get_resume_by_id(self, resume_id: str) -> Dict[str, Any]:
        """Get resume data by ID"""
        try:
            resume = await Resume.get(PydanticObjectId(resume_id))
        except:
            raise HTTPException(status_code=400, detail="Invalid resume ID")
            
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return resume
    
    async def update_resume_data(self, resume_id: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update resume data"""
        try:
            resume = await Resume.get(ObjectId(resume_id))
        except:
            raise HTTPException(status_code=400, detail="Invalid resume ID")
            
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        resume.set_json_data(resume_data)
        await resume.save()
        
        return resume
        
    
    async def list_all_resumes(self) -> List[Dict[str, Any]]:
        """List all resumes"""
        resumes = await Resume.find_all().sort(-Resume.updated_at).to_list()
        return [
            r
            for r in resumes
        ]
    
    async def generate_pdf_from_resume(self, resume_id: str) -> Dict[str, Any]:
        """Generate PDF from resume data"""
        try:
            resume = await Resume.get(ObjectId(resume_id))
        except:
            raise HTTPException(status_code=400, detail="Invalid resume ID")
            
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        try:
            # Convert to YAML
            yaml_content = yaml_converter.convert_to_rendercv(resume.get_json_data())
            
            # Save YAML file
            yaml_path = f"resume_{resume_id}.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            
            # Generate PDF using async function
            pdf_path = f"resume_{resume_id}.pdf"
       
            success = await self.rendercv_agent.create_pdf_with_rendercv(yaml_path, pdf_path)
            
            if success:
                # Update resume with paths
                resume.yaml_content = yaml_content
                resume.pdf_path = pdf_path
                await resume.save()
                
                return {
                    "id": str(resume.id),
                    "pdf_path": pdf_path,
                    "yaml_path": yaml_path,
                    "message": "PDF generated successfully"
                }
            else:
                raise HTTPException(status_code=500, detail="PDF generation failed")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

    async def analyze_ats_compatibility(
        self, 
        resume_file: UploadFile = None, 
        resume_text: str = None, 
        job_description: str = None, 
        job_url: str = None
    ) -> Dict[str, Any]:
        """Analyze resume against job requirements for ATS compatibility"""
        try:
            # Extract resume content
            if resume_file:
                # Save uploaded file temporarily
                temp_path = f"temp_ats_{uuid.uuid4()}.pdf"
                try:
                    with open(temp_path, "wb") as buffer:
                        content = await resume_file.read()
                        buffer.write(content)
                    
                    # Extract text from PDF
                    resume_content = self.parser_instance.extract_raw_text(temp_path)
                    
                    if not resume_content:
                        raise HTTPException(status_code=400, detail="Could not extract text from resume file")
                        
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
            elif resume_text:
                resume_content = resume_text
            else:
                raise HTTPException(status_code=400, detail="Either resume_file or resume_text must be provided")
            
            # Get job description
            if job_url:
                try:
                    print(f"Scraping job description from URL: {job_url}")
                    # Use LangChain WebBaseLoader to scrape the job posting
                    loader = WebBaseLoader(job_url)
                    documents = loader.load()
                    
                    if documents and len(documents) > 0:
                        # Extract text content from the scraped page
                        scraped_content = documents[0].page_content
                       
                        
                        # Clean and extract relevant job description content
                        job_content = self._extract_job_description(scraped_content)
                      
                        if not job_content or len(job_content.strip()) < 100:
                            job_content = scraped_content[:3000]  # Use first 3000 chars as fallback
                            
                        print(f"Successfully scraped {len(job_content)} characters from job URL")
                    else:
                        raise Exception("No content found at the provided URL")
                        
                except Exception as e:
                    print(f"Error scraping job URL: {e}")
                    # Fallback to a basic message if scraping fails
                    job_content = f"Could not scrape job description from {job_url}. Please provide job description manually. Error: {str(e)}"
                    
            elif job_description:
                job_content = job_description
            else:
                raise HTTPException(status_code=400, detail="Either job_description or job_url must be provided")
            
            # Perform ATS analysis using AI
            ats_analysis_prompt = f"""
            Analyze the following resume against the job requirements for ATS (Applicant Tracking System) compatibility.
            
            RESUME:
            {resume_content}
            
            JOB REQUIREMENTS:
            {job_content}
            
            Provide a detailed ATS analysis including:
            1. Overall ATS Score (0-100)
            2. Keyword matching analysis
            3. Skills alignment
            4. Missing keywords that should be added
            5. Formatting recommendations
            6. Specific improvement suggestions
            
            Return the analysis in a structured format with scores and recommendations.
            """
            
            # Use Groq agent for analysis
            analysis_result = await self.groq_agent_instance.enhance_content(
                section_name="ats_analysis",
                content=resume_content,
                instructions=ats_analysis_prompt
            )
            
            # Parse keywords from resume and job description
            resume_keywords = self._extract_keywords(resume_content)
            job_keywords = self._extract_keywords(job_content)
            
            # Calculate keyword match score
            matching_keywords = set(resume_keywords) & set(job_keywords)
            keyword_match_score = (len(matching_keywords) / len(job_keywords)) * 100 if job_keywords else 0
            
            # Calculate overall compatibility score
            compatibility_score = min(90, max(20, keyword_match_score + 15))
            
            # Analyze different resume sections
            section_analysis = {
                "summary": {
                    "score": min(85, max(30, keyword_match_score + 10)),
                    "feedback": "Professional summary effectively highlights key qualifications" if keyword_match_score > 50 else "Summary needs more relevant keywords",
                    "suggestions": ["Include more industry-specific keywords", "Quantify achievements in summary"]
                },
                "experience": {
                    "score": min(90, max(25, keyword_match_score + 20)),
                    "feedback": "Experience section shows relevant background" if keyword_match_score > 60 else "Experience section could better align with job requirements",
                    "suggestions": ["Use action verbs", "Add quantifiable results", "Include relevant technologies"]
                },
                "skills": {
                    "score": min(95, max(40, keyword_match_score + 25)),
                    "feedback": "Skills section matches job requirements well" if keyword_match_score > 70 else "Skills section needs enhancement",
                    "suggestions": ["Add missing technical skills", "Group related skills together", "Include proficiency levels"]
                },
                "education": {
                    "score": min(80, max(50, keyword_match_score + 5)),
                    "feedback": "Education section is properly formatted",
                    "suggestions": ["Include relevant coursework", "Add GPA if above 3.5", "Include certifications"]
                }
            }
            
            # Identify formatting issues
            formatting_issues = []
            if len(resume_content) < 500:
                formatting_issues.append("Resume appears too short")
            if "•" not in resume_content and "-" not in resume_content:
                formatting_issues.append("Consider using bullet points for better readability")
            if not any(section in resume_content.lower() for section in ["experience", "education", "skills"]):
                formatting_issues.append("Standard section headings are missing")
            
            # Identify strengths
            strengths = []
            if keyword_match_score > 70:
                strengths.append("Strong keyword alignment with job requirements")
            if len(matching_keywords) > 10:
                strengths.append("Good variety of relevant skills mentioned")
            if any(word in resume_content.lower() for word in ["led", "managed", "developed", "implemented"]):
                strengths.append("Uses strong action verbs")
            if any(char.isdigit() for char in resume_content):
                strengths.append("Includes quantifiable achievements")
            
            return {
                "overall_score": round(compatibility_score, 1),
                "compatibility_score": round(compatibility_score, 1),
                "keyword_match_percentage": round(keyword_match_score, 1),
                "missing_keywords": list(set(job_keywords) - set(resume_keywords))[:15],  # Limit to 15
                "matched_keywords": list(matching_keywords)[:15],  # Limit to 15
                "suggestions": [
                    "Incorporate missing keywords naturally throughout your resume",
                    "Use industry-standard section headings (Summary, Experience, Education, Skills)",
                    "Quantify achievements with specific numbers and percentages",
                    "Include both technical skills and soft skills relevant to the role",
                    "Optimize resume format for ATS parsing (avoid tables, images, complex formatting)",
                    "Use standard fonts like Arial, Calibri, or Times New Roman",
                    "Save resume as .docx or .pdf format",
                    "Include relevant certifications and training"
                ],
                "section_analysis": section_analysis,
                "formatting_issues": formatting_issues,
                "strengths": strengths
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error analyzing ATS compatibility: {str(e)}")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
        
        # Clean and split text into words
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        
        # Filter out stop words and short words
        keywords = [word for word in words if word not in stop_words and len(word) >= 3]
        
        # Count frequency and return top keywords
        from collections import Counter
        word_counts = Counter(keywords)
        
        # Return top 50 most frequent words
        return [word for word, count in word_counts.most_common(50)]
    
    def _extract_job_description(self, scraped_content: str) -> str:
        """Extract relevant job description content from scraped webpage with LinkedIn-specific targeting"""
        
        # LinkedIn-specific class and structure targeting
        linkedin_patterns = [
            r'class="decorated-job-posting__details"[^>]*>(.*?)</div>',
            r'class="show-more-less-html__markup"[^>]*>(.*?)</div>',
            r'class="jobs-description__content"[^>]*>(.*?)</div>',
            r'class="job-description"[^>]*>(.*?)</div>',
            r'data-testid="job-description"[^>]*>(.*?)</div>'
        ]
        
        # Try LinkedIn-specific patterns first
        for pattern in linkedin_patterns:
            matches = re.findall(pattern, scraped_content, re.DOTALL | re.IGNORECASE)
            if matches:
                # Clean HTML tags and extract text
                linkedin_content = []
                for match in matches:
                    # Remove HTML tags
                    clean_text = re.sub(r'<[^>]+>', '', match)
                    # Decode HTML entities
                    clean_text = clean_text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                    clean_text = clean_text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
                    # Normalize whitespace
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    if len(clean_text) > 100:  # Only include substantial content
                        linkedin_content.append(clean_text)
                
                if linkedin_content:
                    combined = "\n\n".join(linkedin_content)
                    print(f"Extracted {len(combined)} characters using LinkedIn-specific patterns")
                    return combined
        
        # General job description indicators (fallback)
        job_indicators = [
            "job description", "job summary", "position summary", "role description",
            "responsibilities", "requirements", "qualifications", "duties", "description",
            "about the role", "what you'll do", "key responsibilities", "job details",
            "essential skills", "desired skills", "experience required", "role overview",
            "position details", "job requirements", "key qualifications"
        ]
        
        # Convert to lowercase for searching
        content_lower = scraped_content.lower()
        
        # Try to find job description sections
        job_sections = []
        
        for indicator in job_indicators:
            if indicator in content_lower:
                # Find all occurrences of the indicator
                start_positions = []
                pos = content_lower.find(indicator)
                while pos != -1:
                    start_positions.append(pos)
                    pos = content_lower.find(indicator, pos + 1)
                
                for start_pos in start_positions:
                    # Extract content starting from this position
                    section_start = max(0, start_pos - 50)  # Include some context before
                    section_end = min(len(scraped_content), start_pos + 3000)  # Increased length for more content
                    
                    section = scraped_content[section_start:section_end]
                    
                    # Remove HTML tags if present
                    section = re.sub(r'<[^>]+>', ' ', section)
                    
                    # Clean up the content
                    section = re.sub(r'\s+', ' ', section)  # Normalize whitespace
                    section = re.sub(r'[^\w\s\-\.\,\;\:\(\)\n\r]', '', section)  # Remove special chars but keep basic punctuation
                    
                    if len(section.strip()) > 200:  # Only include substantial sections
                        job_sections.append(section.strip())
        
        # If we found job-specific sections, combine them
        if job_sections:
            # Remove duplicates and combine
            unique_sections = []
            for section in job_sections:
                if not any(section in existing for existing in unique_sections):
                    unique_sections.append(section)
            
            combined_content = "\n\n".join(unique_sections[:5])  # Limit to 5 best sections
            print(f"Extracted {len(combined_content)} characters using job description indicators")
            return combined_content
        
        # Enhanced paragraph extraction as fallback
        # Remove HTML tags first
        clean_content = re.sub(r'<[^>]+>', ' ', scraped_content)
        
        # Split into paragraphs by line breaks or periods
        paragraphs = re.split(r'[\n\r]+|\.{2,}', clean_content)
        
        # Filter paragraphs that likely contain job info
        job_paragraphs = []
        job_keywords = [
            'experience', 'skill', 'requirement', 'responsible', 'manage', 'develop',
            'bachelor', 'master', 'degree', 'years', 'team', 'project', 'software',
            'technical', 'knowledge', 'ability', 'proficient', 'familiar', 'expert'
        ]
        
        for para in paragraphs:
            para = para.strip()
            if len(para) > 100:  # Only substantial paragraphs
                para_lower = para.lower()
                # Check if paragraph contains job-related keywords
                keyword_count = sum(1 for keyword in job_keywords if keyword in para_lower)
                if keyword_count >= 2:  # Require at least 2 job-related keywords
                    job_paragraphs.append(para)
        
        if job_paragraphs:
            result = "\n\n".join(job_paragraphs[:8])  # Limit to first 8 relevant paragraphs
            print(f"Extracted {len(result)} characters using enhanced paragraph extraction")
            return result
        
        # Last resort: return cleaned content with length limit
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        result = clean_content[:2500] if clean_content else ""
        print(f"Used fallback extraction: {len(result)} characters")
        return result


