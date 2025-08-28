#test.py
from openai import OpenAI

client = OpenAI(
  api_key="sk-proj-keyyy"
)

response = client.responses.create(
  model="gpt-4o-mini",
  input="write a haiku about ai",
  store=True,
)

print(response.output_text);