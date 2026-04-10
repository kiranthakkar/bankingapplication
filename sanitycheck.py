import os

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIError


load_dotenv()


base_url = os.getenv("OCI_BASE_URL")
api_key = os.getenv("OCI_GENAI_API_KEY")
project_id = os.getenv("OCI_GENAI_PROJECT_ID")
model = "openai.gpt-oss-120b"


client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    project=project_id,
)


print("Base URL:", base_url)
print("Project ID set:", bool(project_id))
print("Model:", model)

try:
    response = client.responses.create(
        model=model,
        input="Reply with exactly: banking sanity check ok",
    )
    print("Response:", response.output_text)
except APIError as exc:
    print("API error status:", getattr(exc, "status_code", None))
    print("API error type:", type(exc).__name__)
    print("API error body:", getattr(exc, "body", None))
    raise
