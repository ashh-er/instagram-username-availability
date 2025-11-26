# instagram-username-availability
This tool checks the availability of Instagram usernames based on official username rules, using multi-threading and safe request delays to avoid rate-limits. It automatically generates all valid usernames within your desired character range and logs available ones to a file.
🔥 Features
Feature	Status
Generates usernames 1–30 characters	✔️ (adjustable)
Only lowercase letters, numbers, _ and .	✔️
Rejects invalid names automatically	✔️
Multi-threaded for high speed	✔️
Saves available usernames to a file	✔️
Random delay to avoid rate-limit	✔️
Optional rate & thread control	✔️
📌 Username Rules Applied

1–30 characters allowed

Only a-z, 0-9, ., _

Cannot start or end with .

Cannot contain ..

Case-insensitive (all generated lowercase)

Each username checked via request → 200 = taken, 404 = free

🛠 Requirements
Python 3.8+
pip install requests

🚀 Run the Script
python tiktok_checker.py


Or choose thread count:

python instagram_checker.py --threads 10


The script will begin scanning and save available usernames to:

available_instagram.txt

⚠️ Notes

Keep thread count low to avoid Instagram rate-limits

Increase delay or add proxies for massive bulk scanning

Too fast = blocks → the script automatically waits & resumes

Future Add-Ons (Optional)
