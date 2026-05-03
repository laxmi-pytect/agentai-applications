# test_auth.py
import os, base64, requests
from dotenv import load_dotenv
load_dotenv()

auth_url = os.environ["FHIR_AUTH_URL"]
username = os.environ["FHIR_USERNAME"]
password = os.environ["FHIR_PASSWORD"]
base_url = os.environ["FHIR_BASE_URL"]

b64 = base64.b64encode(f"{username}:{password}".encode()).decode()
resp = requests.post(auth_url, headers={
    "Authorization": f"Basic {b64}",
    "Content-Type": "application/x-www-form-urlencoded"
}, data="grant_type=client_credentials&scope=system%2FPatient.read")

print("Auth status:", resp.status_code)
print("Response:", resp.json())

token = resp.json()["access_token"]
fhir_resp = requests.get(f"{base_url}/Patient?_count=1",
    headers={"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"})
print("FHIR status:", fhir_resp.status_code)
print("FHIR body:", fhir_resp.text[:500])
