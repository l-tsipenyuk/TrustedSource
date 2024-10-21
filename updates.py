import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import itertools
load_dotenv()
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def get_date_range():
    today = date.today()
    first_day = today.replace(day=1)
    return first_day, today

def fetch_webpage(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return None

def scrape_jpost_articles(base_url):
    articles = []
    html = fetch_webpage(base_url)
    if not html:
        return articles

    soup = BeautifulSoup(html, 'html.parser')
    
    large_item = soup.find('div', class_='category-five-articles-large-item-wrap')
    if large_item:
        link = large_item.find('a', href=True)
        if link:
            title = link.get('title', '')
            url = link['href']
            author = large_item.find('span', class_='reporter')
            author = author.text if author else "Unknown"
            articles.append({'title': title, 'link': url, 'source': 'Jerusalem Post', 'author': author})

    small_items = soup.find_all('div', class_='category-five-articles-small-item-wrap')
    for item in small_items:
        link = item.find('a', href=True)
        if link:
            title = link.get('title', '')
            url = link['href']
            author = item.find('span', class_='reporter')
            author = author.text if author else "Unknown"
            articles.append({'title': title, 'link': url, 'source': 'Jerusalem Post', 'author': author})

    return articles

def scrape_conversation_articles(base_url):
    articles = []
    page = 1
    while True:
        url = f"{base_url}&page={page}"
        html = fetch_webpage(url)
        if not html:
            break
        soup = BeautifulSoup(html, 'html.parser')
        article_containers = soup.find_all('article', class_='result')
        if not article_containers:
            break
        for container in article_containers:
            title_element = container.find('h1', class_='legacy')
            if title_element:
                title = title_element.text.strip()
                link = title_element.find('a')['href']
                articles.append({'title': title, 'link': f"https://theconversation.com{link}", 'source': 'The Conversation'})
        page += 1
    return articles

def parse_nrel_date(date_string):
    months = {
        'Jan.': 1, 'Feb.': 2, 'Mar.': 3, 'Apr.': 4, 'May': 5, 'June': 6,
        'July': 7, 'Aug.': 8, 'Sept.': 9, 'Oct.': 10, 'Nov.': 11, 'Dec.': 12
    }
    pattern = r'(\w+\.?)\s+(\d{1,2}),\s+(\d{4})'
    match = re.match(pattern, date_string)
    if match:
        month, day, year = match.groups()
        return date(int(year), months[month], int(day))
    raise ValueError(f"Unable to parse date: {date_string}")

def scrape_nrel_articles(base_url, start_date, end_date):
    articles = []
    page = 1
    while True:
        url = f"{base_url}?page={page}"
        html = fetch_webpage(url)
        if not html:
            break
        soup = BeautifulSoup(html, 'html.parser')
        article_containers = soup.find_all('div', class_='media-block')
        if not article_containers:
            break
        for container in article_containers:
            date_element = container.find('p', class_='date')
            if date_element:
                try:
                    article_date = parse_nrel_date(date_element.text.strip())
                    if start_date <= article_date <= end_date:
                        title_element = container.find('h3', class_='header')
                        if title_element:
                            title = title_element.text.strip()
                            link = title_element.find('a')['href']
                            articles.append({'title': title, 'link': f"https://www.nrel.gov{link}", 'source': 'NREL'})
                    elif article_date < start_date:
                        return articles
                except ValueError as e:
                    print(f"Error parsing date: {e}")
        page += 1
    return articles

def scrape_doe_articles(base_url):
    articles = []
    page = 0
    while True:
        url = f"{base_url}&page={page}"
        print(f"Scraping DOE page {page + 1}...")
        html = fetch_webpage(url)
        if not html:
            break
        soup = BeautifulSoup(html, 'html.parser')
        article_containers = soup.find_all('div', class_='search-result')
        if not article_containers:
            break
        for container in article_containers:
            title_element = container.find('a', class_='search-result-title')
            if title_element:
                title = title_element.text.strip()
                link = f"https://www.energy.gov{title_element['href']}"
                articles.append({'title': title, 'link': link, 'source': 'Department of Energy'})
        page += 1
    return articles

def parse_yesenergy_date(date_string):
    return datetime.strptime(date_string, '%b %d, %Y').date()

def scrape_yesenergy_articles(base_urls, start_date, end_date):
    articles = []
    for base_url in base_urls:
        page = 1
        while True:
            url = f"{base_url}/page/{page}" if page > 1 else base_url
            print(f"Scraping YesEnergy blog page {page} for {base_url}...")
            html = fetch_webpage(url)
            if not html:
                break
            soup = BeautifulSoup(html, 'html.parser')
            article_containers = soup.find_all('div', class_='blog-card__content')
            if not article_containers:
                break
            
            articles_found = False
            for container in article_containers:
                date_element = container.find('span', class_='blog-card__date')
                if date_element:
                    try:
                        article_date = parse_yesenergy_date(date_element.text.strip())
                        if start_date <= article_date <= end_date:
                            title_element = container.find('h3', class_='blog-card__title')
                            if title_element:
                                title = title_element.text.strip()
                                link = container.find('a')['href']
                                tag_element = container.find('span', class_='badge')
                                tag = tag_element.text.strip() if tag_element else "YesEnergy Blog"
                                articles.append({
                                    'title': title,
                                    'link': link,
                                    'source': f"YesEnergy Blog - {tag}",
                                    'date': article_date
                                })
                                articles_found = True
                        elif article_date < start_date:
                            articles_found = False
                            break
                    except ValueError as e:
                        print(f"Error parsing date: {e}")
            
            if not articles_found:
                break
            
            next_page = soup.find('a', class_='next')
            if not next_page:
                break
            page += 1
    
    return articles

def parse_iea_date(date_string):
    return datetime.strptime(date_string, '%d %B %Y').date()

def scrape_iea_articles(base_url, category, start_date, end_date):
    articles = []
    page = 1
    while True:
        url = f"{base_url}&page={page}"
        print(f"Scraping IEA {category} page {page}...")
        html = fetch_webpage(url)
        if not html:
            break
        soup = BeautifulSoup(html, 'html.parser')
        article_containers = soup.find_all('article')
        if not article_containers:
            break
        
        articles_found = False
        for container in article_containers:
            date_element = container.find('div', class_='m-news-detailed-listing__date')
            if date_element:
                try:
                    article_date = parse_iea_date(date_element.text.strip())
                    if start_date <= article_date <= end_date:
                        title_element = container.find('h5', class_='m-news-detailed-listing__title')
                        if title_element:
                            title = title_element.text.strip()
                            link = "https://www.iea.org" + container.find('a')['href']
                            articles.append({
                                'title': title,
                                'link': link,
                                'source': f"IEA - {category}",
                                'date': article_date,
                                'category': category
                            })
                            articles_found = True
                    elif article_date < start_date:
                        articles_found = False
                        break
                except ValueError as e:
                    print(f"Error parsing date: {e}")
        
        if not articles_found:
            break
        
        page += 1
    
    return articles

def parse_microgrid_date(date_string):
    month_dict = {
        'Jan.': 1, 'Feb.': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
        'July': 7, 'Aug.': 8, 'Sept.': 9, 'Oct.': 10, 'Nov.': 11, 'Dec.': 12
    }
    
    parts = date_string.split()
    
    if len(parts) != 3:
        raise ValueError(f"Unexpected date format: {date_string}")
    
    month, day, year = parts
    
    day = day.rstrip('.,')
    
    if month not in month_dict:
        raise ValueError(f"Unknown month: {month}")
    
    month_num = month_dict[month]
    
    return date(int(year), month_num, int(day))

def scrape_microgrid_articles(base_urls, start_date, end_date):
    articles = []
    for base_url in base_urls:
        page = 1
        while True:
            url = f"{base_url}/page/{page}/" if page > 1 else base_url
            print(f"Scraping Microgrid Knowledge page {page} from {base_url}...")
            html = fetch_webpage(url)
            if not html:
                break
            soup = BeautifulSoup(html, 'html.parser')
            article_containers = soup.find_all('div', class_='item small')
            if not article_containers:
                break
            
            articles_found = False
            for container in article_containers:
                date_element = container.find('div', class_='date')
                if date_element:
                    try:
                        article_date = parse_microgrid_date(date_element.text.strip())
                        if start_date <= article_date <= end_date:
                            title_element = container.find('div', class_='title-text')
                            if title_element:
                                title = title_element.text.strip()
                                link = container.find('a', class_='title-wrapper')['href']
                                articles.append({
                                    'title': title,
                                    'link': link,
                                    'source': "Microgrid Knowledge",
                                    'date': article_date,
                                    'category': "Microgrids"
                                })
                                articles_found = True
                        elif article_date < start_date:
                            articles_found = False
                            break
                    except ValueError as e:
                        print(f"Error parsing date: {e}")
            
            if not articles_found:
                break
            
            page += 1
    
    return articles

def send_email(subject, body, sender_email, receiver_email, password):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, password)
            server.send_message(message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")

def filter_conversation_articles(articles):
    keywords = [
        "energy", "hydrogen", "storage", "EV", "climate", "green", "electricity", 
        "electric", "net zero", "grid", "emissions", "AI", "carbon", "power", 
        "warming", "pollution", "methane", "technology", "renewable", "sustainable"
    ]
    
    filtered_articles = []
    for article in articles:
        if any(keyword.lower() in article['title'].lower() for keyword in keywords):
            filtered_articles.append(article)
    
    return filtered_articles

def fix_nrel_link(link):
    if link.startswith('https://www.nrel.govhttps://www.nrel.gov'):
        return link.replace('https://www.nrel.govhttps://www.nrel.gov', 'https://www.nrel.gov')
    return link

def fix_microgrid_link(link):
    parts = link.split('/')
    if len(parts) > 2:
        return f"https://www.microgridknowledge.com/{'/'.join(parts[3:])}"
    return link

def categorize_article(article):
    title = article['title'].lower()
    source = article['source'].lower()
    
    if 'jerusalem post' in source or 'israel' in title:
        return "Energy in Israel"
    elif any(keyword in title for keyword in ['grid', 'microgrid', 'smart grid']):
        return "Grids"
    elif any(keyword in title for keyword in ['hydrogen', 'methane', 'gas', 'biofuel']):
        return "Hydrogen"
    elif any(keyword in title for keyword in ['electricity', 'power', 'renewable energy', 'solar', 'wind', 'renewables']):
        return "Electricity and Renewables"
    elif any(keyword in title for keyword in ['electric car', 'ev']):
        return "Electric Vehicles"
    elif any(keyword in title for keyword in ['climate', 'climate change', 'mitigation', 'carbon capture', 'carbon', 'pollution', 'microplastic']):
        return "Climate Change"
    elif any(keyword in title for keyword in ['ai', 'data', 'data center']):
        return "AI and Data"
    else:
        return "Other"

def format_article(article, index):
    formatted = f"{index}. {article['title']}\n"
    formatted += f"Source: {article['source']}\n"
    formatted += f"Link: {article['link']}\n"
    return formatted

def main():
    start_date, end_date = get_date_range()
    
    jpost_url = "https://www.jpost.com/business-and-innovation/energy-and-infrastructure"
    nrel_url = "https://www.nrel.gov/news/news.html"
    conversation_energy_url = f"https://theconversation.com/global/search?q=energy&sort=relevancy&language=en&date=custom&date_from={start_date}&date_to={end_date}"
    conversation_climate_tech_url = f"https://theconversation.com/global/search?q=climate+tech&sort=relevancy&language=en&date=custom&date_from={start_date}&date_to={end_date}"
    doe_url = f"https://www.energy.gov/newsroom?field_display_date_from={start_date}&field_display_date_to={end_date}"
    yesenergy_urls = [
        "https://blog.yesenergy.com/yeblog/tag/industry-news-trends",
        "https://blog.yesenergy.com/yeblog/tag/market-driver-alerts-live-power",
        "https://blog.yesenergy.com/yeblog/tag/renewable-energy",
        "https://blog.yesenergy.com/yeblog/tag/energy-storage-battery-technology"
    ]
    iea_urls = [
        ("https://www.iea.org/news?technology%5B2%5D=smart-grids", "Smart Grids"),
        ("https://www.iea.org/news?technology%5B3%5D=electric-vehicles", "Electric Vehicles"),
        ("https://www.iea.org/news?technology%5B0%5D=hydrogen", "Hydrogen"),
        ("https://www.iea.org/news?technology%5B0%5D=bioenergy", "Bioenergy"),
        ("https://www.iea.org/news?technology%5B1%5D=wind", "Wind")
    ]
    microgrid_urls = [
        "https://www.microgridknowledge.com/microgrids",
        "https://www.microgridknowledge.com/infrastructure",
        "https://www.microgridknowledge.com/resources"
    ]

    all_articles = []

    print("Scraping Jerusalem Post articles...")
    all_articles.extend(scrape_jpost_articles(jpost_url))

    print("Scraping The Conversation energy articles...")
    conversation_energy_articles = scrape_conversation_articles(conversation_energy_url)
    all_articles.extend(filter_conversation_articles(conversation_energy_articles))

    print("Scraping The Conversation climate tech articles...")
    conversation_climate_articles = scrape_conversation_articles(conversation_climate_tech_url)
    all_articles.extend(filter_conversation_articles(conversation_climate_articles))

    print("Scraping NREL articles...")
    nrel_articles = scrape_nrel_articles(nrel_url, start_date, end_date)
    for article in nrel_articles:
        article['link'] = fix_nrel_link(article['link'])
    all_articles.extend(nrel_articles)

    print("Scraping Department of Energy articles...")
    all_articles.extend(scrape_doe_articles(doe_url))

    print("Scraping YesEnergy blog articles...")
    all_articles.extend(scrape_yesenergy_articles(yesenergy_urls, start_date, end_date))

    print("Scraping IEA articles...")
    for url, category in iea_urls:
        all_articles.extend(scrape_iea_articles(url, category, start_date, end_date))

    print("Scraping Microgrid Knowledge articles...")
    microgrid_articles = scrape_microgrid_articles(microgrid_urls, start_date, end_date)
    for article in microgrid_articles:
        article['link'] = fix_microgrid_link(article['link'])
    all_articles.extend(microgrid_articles)

    unique_articles = []
    seen_titles = set()

    for article in all_articles:
        if article['title'] not in seen_titles:
            unique_articles.append(article)
            seen_titles.add(article['title'])

    # Categorize articles
    categorized_articles = {}
    for article in unique_articles:
        category = categorize_article(article)
        if category not in categorized_articles:
            categorized_articles[category] = []
        categorized_articles[category].append(article)

    # Sort categories
    category_order = [
        "Energy in Israel", "Grids", "Hydrogen", "Electricity and Renewables",
        "Electric Vehicles", "Climate Change", "AI and Data", "Other"
    ]
    sorted_categories = sorted(
        categorized_articles.items(),
        key=lambda x: category_order.index(x[0]) if x[0] in category_order else len(category_order)
    )

    # Format email body
    sources = set(article['source'] for article in unique_articles)
    email_body = f"""
    <html>
    <body>
    <p>Hi! This is an automatically generated email with news for {start_date.strftime('%B %Y')} from {', '.join(sources)}.</p>
    """

    for category, articles in sorted_categories:
        email_body += f"<h2>{category}</h2>"
        for i, article in enumerate(articles, 1):
            email_body += f"<p>{format_article(article, i)}</p>"
        email_body += "<hr>"

    email_body += """
    </body>
    </html>
    """

    if not unique_articles:
        email_body = f"<p>No articles were found for {start_date.strftime('%B %Y')}. There might be an issue with accessing the websites.</p>"

    # Email configuration
    sender_email = os.getenv('SENDER_EMAIL')
    receiver_email = os.getenv('RECEIVER_EMAIL')
    password = os.getenv('EMAIL_PASSWORD')
    subject = f"Energy News Articles for {start_date.strftime('%B %Y')}"

    if not all([sender_email, receiver_email, password]):
        print("Error: One or more email configuration variables are missing.")
        print(f"sender email {sender_email}, receiver email {receiver_email}, password {password}, subject {subject}")
        return

    try:
        # Create message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = receiver_email
        message['Subject'] = subject

        # Attach HTML content
        message.attach(MIMEText(email_body, 'html'))

        # Send email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, password)
            server.send_message(message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")

if __name__ == "__main__":
    main()