from google.oauth2.service_account import Credentials
import gspread

# Define the API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Authenticate with your service account key
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Open your Google Sheet by name
sheet = client.open("Project November 7th").sheet1   # change "Watermelon Budget" to your sheet’s exact name

# Test writing to the sheet
sheet.append_row(["2025-09-03", "36", "Test Item", "1000", "", "", "Testing"])

print("✅ Test row added successfully!")
