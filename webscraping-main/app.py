from flask import Flask, request, render_template, jsonify, redirect, url_for
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from flask_ngrok import run_with_ngrok
import phonenumbers
import sqlite3

app = Flask(__name__)
run_with_ngrok(app)


# Create a SQLite database and table to store scraped data
conn = sqlite3.connect('scraped_data.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS scraped_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE,
        emails TEXT,
        mobiles TEXT,
        social_links TEXT,
        linked_emails TEXT,
        linked_mobiles TEXT
    )
''')
conn.commit()
conn.close()

# Create a table for admin credentials
conn = sqlite3.connect('admin_credentials.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
''')
conn.commit()
conn.close()

# Add admin credentials to the database (replace 'admin_username' and 'admin_password' with your desired credentials)
conn = sqlite3.connect('admin_credentials.db')
cursor = conn.cursor()
cursor.execute('INSERT OR REPLACE INTO admin_credentials (username, password) VALUES (?, ?)', ('admin_username', 'admin_password'))
conn.commit()
conn.close()

def extract_information(url, store_data=True):
    conn = sqlite3.connect('scraped_data.db')
    cursor = conn.cursor()

    try:
        # Check if the URL is already in the database
        cursor.execute('SELECT * FROM scraped_data WHERE url=?', (url,))
        row = cursor.fetchone()

        if row:
            # If the URL is found in the database, return the stored data
            _, _, emails, mobiles, social_links, linked_emails, linked_mobiles = row
            emails = emails.split(', ')
            mobiles = mobiles.split(', ')
            social_links = social_links.split(', ')
            linked_emails = linked_emails.split(', ')
            linked_mobiles = linked_mobiles.split(', ')
        else:
            # Otherwise, scrape the data as before
            response = requests.get(url)
            content = response.text
            soup = BeautifulSoup(content, 'html.parser')

            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            
            emails = list(set(re.findall(email_pattern, content)))

            mobiles = extract_phone_numbers(content)
            mobiles = list(set(mobiles))

            social_links = set()
            base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
            for a in soup.find_all('a', href=True):
                link = a['href']
                if 'twitter.com' in link or 'facebook.com' in link or 'youtube.com' in link or 'linkedin.com' in link:
                    social_links.add(link)

            linked_emails = set()
            linked_mobiles = set()
            for link in social_links:
                linked_response = requests.get(link)
                linked_content = linked_response.text
                linked_emails.update(re.findall(email_pattern, linked_content))
                linked_mobiles.update(extract_phone_numbers(linked_content))
            linked_mobiles = list(set(linked_mobiles))

            # Store the scraped data in the database
            if store_data:
                cursor.execute('INSERT INTO scraped_data (url, emails, mobiles, social_links, linked_emails, linked_mobiles) VALUES (?, ?, ?, ?, ?, ?)', (url, ', '.join(emails), ', '.join(mobiles), ', '.join(social_links), ', '.join(linked_emails), ', '.join(linked_mobiles)))
                conn.commit()

            # Scrape and store data from sublinks
            if store_data:
                for a in soup.find_all('a', href=True):
                    sublink = a['href']
                    if not sublink.startswith('http'):
                        sublink = urlparse(url)._replace(path=sublink).geturl()
                    extract_information(sublink, store_data=False)

        conn.close()
        return emails, mobiles, social_links, linked_emails, linked_mobiles

    except Exception as e:
        conn.close()
        return [], [], [], [], []




# Function to extract and validate phone numbers using phonenumbers library
def extract_phone_numbers(text):
    phone_numbers = []
    for match in phonenumbers.PhoneNumberMatcher(text, "IN"):  # "IN" for Indian numbers
        phone_number = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
        phone_numbers.append(phone_number)
    return phone_numbers

@app.route('/')
def login():
    return render_template('index.html')

@app.route('/user', methods=['GET'])
def user():
    return render_template('user.html')


@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('admin_credentials.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_credentials WHERE username=? AND password=?', (username, password))
    admin = cursor.fetchone()
    conn.close()

    if admin:
        return redirect(url_for('user'))
    else:
        return "Invalid username or password"

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    emails, mobiles, social_links, linked_emails, linked_mobiles = extract_information(url)

    # Return data in the expected JSON format
    response_data = {
        'email': emails,
        'mobile': mobiles,
        'social': social_links,
        'linked_email': linked_emails,
        'linked_mobile': linked_mobiles
    }

    return jsonify(response_data)


if __name__ == '__main__':
    app.run(debug=True)