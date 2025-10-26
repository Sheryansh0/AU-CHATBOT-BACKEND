import requests

# Test the chat endpoint
url = "http://127.0.0.1:5000/api/chat"

# Test data
data = {
    "message": "Tell me about Anurag University",
    "language": "English"
}

print("🧪 Testing Perplexity API locally...")
print(f"📤 Sending request to: {url}")
print(f"💬 Message: {data['message']}")
print("-" * 50)

try:
    response = requests.post(url, json=data, timeout=30)
    
    print(f"📊 Status Code: {response.status_code}")
    print(f"📦 Response:")
    print(response.json())
    
except requests.exceptions.Timeout:
    print("⏱️ Request timed out!")
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Response text: {response.text if 'response' in locals() else 'No response'}")
