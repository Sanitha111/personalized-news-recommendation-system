from  summarizer import Summarizer  # CORRECT import
import requests
from bs4 import BeautifulSoup

# Initialize the BERT model
bert_model = Summarizer()

def summarize_article(url):
    try:
        # Fetch the article content from the URL
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract paragraphs from the article
        paragraphs = soup.find_all('p')
        article_text = ' '.join([para.text for para in paragraphs])

        # Generate a summary using the BERT model
        summary = bert_model(article_text)

        return summary
    except Exception as e:
        return f"Error while summarizing the article: {e}"
