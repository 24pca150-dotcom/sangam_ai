import sys
import os

# Add the backend directory to sys.path so we can import from rag
sys.path.append(os.path.abspath('d:/training/sangam-ai/backend'))

from rag.pipeline import generate_answer

result = generate_answer("உவமை")
print(result)
