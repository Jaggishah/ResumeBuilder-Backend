
from pathlib import Path
import asyncio
import os
import shutil
import subprocess
class RenderCVAgent:
    def __init__(self):
        pass

    async def create_pdf_with_rendercv(self,yaml_file_path: str, output_pdf_path: str) -> bool:
        """
        Create a PDF using RenderCV from a given YAML file.

        Args:
            yaml_file_path (str): Path to the YAML file.
            output_pdf_path (str): Desired output path for the generated PDF.
            """
        try:
            yaml_file = Path(yaml_file_path).resolve()
            pdf_file = Path(output_pdf_path).resolve()


            rendercv_exe = shutil.which("rendercv")
            print(f"RenderCV executable found at: {rendercv_exe}")
            if rendercv_exe is None:
                raise RuntimeError("rendercv not found in PATH")
            cwd = str(yaml_file.parent)
            print(f"Using working directory: {cwd}")
            args = [rendercv_exe, "render", str(yaml_file), "--pdf-path", str(pdf_file)]
            print(f"Running command: {' '.join(args)}")

            # Run the blocking subprocess in a thread so the async function doesn't block the event loop
            result = await asyncio.to_thread(
                subprocess.run,
                args,
                capture_output=True,
                text=True,
                cwd=cwd
            )

            print(f"Command stdout: {result.stdout.strip()}")
            print(f"Command stderr: {result.stderr.strip()}")

            # Check if the command was successful
            if result.returncode == 0:
                print("RenderCV command executed successfully")

                # Verify the PDF was created
                if os.path.exists(pdf_file):
                    file_size = os.path.getsize(pdf_file)
                    print(f"PDF created: {pdf_file} ({file_size} bytes)")
                    return True
                else:
                    print("PDF file was not found after command execution")
                    return False
            else:
                print(f"RenderCV command failed with return code: {result.returncode}")
                if result.stdout:
                    print(f"STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error running RenderCV command: {e}")
            return False