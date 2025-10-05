import os

# Access and print the HL_API environment variable
hl_api = os.environ.get('HL_API')

if hl_api:
    print(f"HL_API: {hl_api}")
else:
    print("HL_API environment variable is not set")
