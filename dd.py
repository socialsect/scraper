import pandas as pd

input_file = r"C:\Users\DELL\Desktop\vinayak\scrapling\email-scraper\output\emails.csv"
output_file = r"C:\Users\DELL\Desktop\vinayak\scrapling\email-scraper\output\dd.csv"

df = pd.read_csv(input_file)

# Keep email column only
df = df[['email']]

# Clean
df['email'] = df['email'].astype(str).str.strip().str.lower()

# Keep only valid-looking emails
df = df[df['email'].str.contains(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', regex=True)]

# Remove duplicates
df = df.drop_duplicates(subset=['email'])

df.to_csv(output_file, index=False)

print(f"Unique emails: {len(df)}")