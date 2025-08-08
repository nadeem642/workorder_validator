import os
import json
import requests
import markdown
from dotenv import load_dotenv
from flask import Flask, render_template, request, flash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "fallback_secret_key")

load_dotenv()
# Load Groq API key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("Groq API key not set in environment variable GROQ_API_KEY.")

def validate_workorder_with_groq(workorder_text):
    prompt = f"""
You are an experienced Network and Security Engineer.

Given the following workorder/configuration block, perform a professional validation. Your tasks are:

1. ✅ Extract only the **relevant networking configuration details** (e.g., VLANs, Interfaces, Port Types, IPs, VPNs, ACLs).
2. ❌ Identify any **missing critical elements** needed for the configuration to be functional and secure — such as missing ACL rules, IP addresses, or descriptions.
3. ⚠️ Highlight any **real technical misconfigurations or poor practices** only (avoid suggesting changes to valid scenarios like /30 on routed interfaces).
4. 🛠️ Provide **realistic and role-appropriate suggestions** for improvement (e.g., adding deny rules in ACLs, checking for description consistency, confirming correct port types).

🧠 Keep your validation scoped to what a professional network engineer would care about — avoid superficial comments like topology or device models unless they impact functionality.

Return the result in well-structured Markdown with these sections:

### ✅ Present Information
(Only list actual working configurations.)

### ❌ Missing Information
(Only list required elements that would be expected for this configuration to work correctly.)

### ⚠️ Issues Found
(Only include real technical misconfigurations or bad practices.)

### 🛠️ Suggested Fixes
(Offer actionable fixes and improvements.)

Workorder:
\"\"\"{workorder_text}\"\"\"
"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(f"Groq API error: {response.status_code} {response.text}")

    return response.json()["choices"][0]["message"]["content"]


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    work_order_text = ""

    if request.method == 'POST':
        work_order_text = request.form.get('work_order', '').strip()
        if not work_order_text:
            flash("Please enter a work order description.", "error")
        else:
            try:
                result = validate_workorder_with_groq(work_order_text)
                result = markdown.markdown(result , extensions=["extra", "sane_lists"])
            except Exception as e:
                flash(f"Error: {str(e)}", "error")

    return render_template('index.html', result=result, work_order_text=work_order_text)

if __name__ == '__main__':
    app.run(host='0.0.0.0')