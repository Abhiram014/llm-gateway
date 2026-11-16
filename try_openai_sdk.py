from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",  # point the official SDK at OUR gateway
    api_key="not-needed-yet",             # our gateway doesn't check keys until Day 4
)

response = client.chat.completions.create(
    model="mock-1",
    messages=[{"role": "user", "content": "Are you really OpenAI?"}],
)

print(response.choices[0].message.content)
print(response.usage)