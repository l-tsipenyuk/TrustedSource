import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import re

def get_date_range():
    today = date.today()
    first_day = today.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return first_day, last_day

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
    page = 1
    while True:
        url = f"{base_url}/page/{page}"
        html = fetch_webpage(url)
        if not html:
            break
        soup = BeautifulSoup(html, 'html.parser')
        article_containers = soup.find_all('div', class_=['category-five-articles-small-item-wrap', 'category-five-articles-large-item-wrap'])
        if not article_containers:
            break
        for container in article_containers:
            article = container.find('a', href=True)
            if article:
                title = article.get('title', '')
                link = article['href']
                articles.append({'title': title, 'link': link, 'source': 'Jerusalem Post'})
        page += 1
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

def main():
    start_date, end_date = get_date_range()
    
    jpost_url = "https://www.jpost.com/business-and-innovation/energy-and-infrastructure"
    nrel_url = "https://www.nrel.gov/news/news.html"
    conversation_energy_url = f"https://theconversation.com/global/search?q=energy&sort=relevancy&language=en&date=custom&date_from={start_date}&date_to={end_date}"
    conversation_climate_tech_url = f"https://theconversation.com/global/search?q=climate+tech&sort=relevancy&language=en&date=custom&date_from={start_date}&date_to={end_date}"
    doe_url = f"https://www.energy.gov/newsroom?field_display_date_from={start_date}&field_display_date_to={end_date}"

    print("Scraping Jerusalem Post articles...")
    jpost_articles = scrape_jpost_articles(jpost_url)

    print("Scraping The Conversation energy articles...")
    conversation_energy_articles = scrape_conversation_articles(conversation_energy_url)

    print("Scraping The Conversation climate tech articles...")
    conversation_climate_tech_articles = scrape_conversation_articles(conversation_climate_tech_url)

    print("Scraping NREL articles...")
    nrel_articles = scrape_nrel_articles(nrel_url, start_date, end_date)

    print("Scraping Department of Energy articles...")
    doe_articles = scrape_doe_articles(doe_url)

    all_articles = jpost_articles + conversation_energy_articles + conversation_climate_tech_articles + nrel_articles + doe_articles
    unique_articles = []
    seen_titles = set()

    for article in all_articles:
        if article['title'] not in seen_titles:
            unique_articles.append(article)
            seen_titles.add(article['title'])

    if unique_articles:
        print(f"\nFound {len(unique_articles)} unique articles for {start_date.strftime('%B %Y')}:")
        for i, article in enumerate(unique_articles, 1):
            print(f"\nArticle {i}:")
            print(f"Source: {article['source']}")
            print(f"Title: {article['title']}")
            print(f"Link: {article['link']}")
    else:
        print(f"\nNo articles were found for {start_date.strftime('%B %Y')}. There might be an issue with accessing the websites.")

if __name__ == "__main__":
    main()