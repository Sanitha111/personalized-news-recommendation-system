from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from webdriver_manager.chrome import ChromeDriverManager

# Mapping of categories to specific BBC News section URLs
bbc_urls = {
    "Politics": "https://www.bbc.com/news/politics",
    "Technology": "https://www.bbc.com/news/technology",
    "Health": "https://www.bbc.com/news/health",
    "Entertainment": "https://www.bbc.com/news/entertainment_and_arts",
    "Science": "https://www.bbc.com/news/science_and_environment",
    "Business": "https://www.bbc.com/news/business",
    "India": "https://www.bbc.com/news/world/asia/india"
}

# Setup Chrome WebDriver with webdriver-manager
def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Fetch and categorize news from BBC
def fetch_news(app, mysql):
    logging.info("🔄 Starting categorized crawl from BBC News...")

    driver = setup_driver()
    news_list = []

    try:
        for category, url in bbc_urls.items():
            logging.info(f"📂 Crawling category: {category} — {url}")
            driver.get(url)

            wait = WebDriverWait(driver, 10)
            # Fetch headlines and links
            headlines = wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//h3 | //h2[@data-testid='card-headline']")
            ))

            for headline in headlines:
                title = headline.text.strip()
                link = None
                try:
                    # Try finding the parent <a> element for the link
                    parent_links = headline.find_elements(By.XPATH, './ancestor::a[1]')
                    if parent_links:
                        link = parent_links[0].get_attribute('href')
                except Exception as e:
                    logging.error(f"Error finding link for {title}: {e}")

                # Only append news articles with a title and link
                if title and link:
                    news_list.append({
                        "title": title,
                        "url": link,
                        "category": category
                    })

        if not news_list:
            logging.warning("⚠️ No articles found across all categories.")
        else:
            logging.info(f"✅ Total articles fetched: {len(news_list)}")
            for i, article in enumerate(news_list, 1):
                logging.info(f"{i}. {article['title']} - Category: {article['category']}")

        # Store to DB
        with app.app_context():
            cur = mysql.connection.cursor()
            for news in news_list:
                cur.execute("""
                    INSERT INTO news_articles (title, url, category)
                    VALUES (%s, %s, %s)
                """, (news['title'], news['url'], news['category']))
            mysql.connection.commit()
            cur.close()
            logging.info("✅ Articles stored in DB by category.")

        return news_list

    except Exception as e:
        logging.error(f"❌ Error during categorized crawl: {e}")
        return []

    finally:
        driver.quit()

# Optional standalone execution for testing
if __name__ == "__main__":
    from db_config import init_db
    from flask import Flask

    app = Flask(__name__)
    app.config.from_object('config.Config')
    mysql = init_db(app)
    fetch_news(app, mysql)
