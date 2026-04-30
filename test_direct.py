from openai import OpenAI

endpoint = "https://uniride-resource.services.ai.azure.com/openai/v1"
deployment_name = "DeepSeek-V3.2-Speciale-1"
api_key = "YF7tYODTYg1IWyfvkc0LGFUBadElrLZFnvzqWxPzIJMcZzG6j8VlJQQJ99CDACfhMk5XJ3w3AAAAACOGayNH"

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