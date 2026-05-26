import os

from openai import OpenAI

endpoint = "https://uniride-resource.services.ai.azure.com/openai/v1"
deployment_name = "DeepSeek-V3.2-Speciale-1"
api_key = os.environ.get("AZURE_OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("AZURE_OPENAI_API_KEY environment variable is required")

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
)

print(completion.choices[0].message)
