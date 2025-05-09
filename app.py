from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask_mysqldb import MySQL
import logging
import crawler

# Import Config and MySQL initialization
from config import Config
from db_config import mysql, init_db

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)  # Load configuration properly
app.secret_key = 'your_secret_key'  # Should ideally be in Config too

# Initialize MySQL
mysql = init_db(app)

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)

# Setup logging
logging.basicConfig(level=logging.INFO)

# -------------------- ROUTES --------------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            flash('Email address is already registered. Please log in or use a different email address.', 'error')
            cur.close()
            return redirect(url_for('register'))

        cur.execute(
            "INSERT INTO users (username, email, password, preferences) VALUES (%s, %s, %s, %s)",
            (username, email, password, '')
        )
        mysql.connection.commit()
        cur.close()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user['password'], password_input):
            session['logged_in'] = True
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials or user not registered. Please register first.', 'error')
            return redirect(url_for('register'))

    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    cur = mysql.connection.cursor()
    cur.execute("SELECT preferences FROM users WHERE id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()

    user_preferences = result['preferences'].split(',') if result and result['preferences'].strip() else []

    if request.method == 'POST':
        selected_categories = request.form.getlist('categories')
        save_user_preferences(user_id, selected_categories)
        return redirect(url_for('display_articles'))

    categories = ['Politics', 'India' ,  'Health', 'Entertainment', 'Science', 'Business' ]
    return render_template('dashboard.html', categories=categories, user_preferences=user_preferences)

def save_user_preferences(user_id, selected_categories):
    preferences = ','.join(selected_categories)
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET preferences = %s WHERE id = %s", (preferences, user_id))
    mysql.connection.commit()
    cur.close()

@app.route('/display_articles')
def display_articles():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    cur = mysql.connection.cursor()
    cur.execute("SELECT preferences FROM users WHERE id = %s", (user_id,))
    preferences_result = cur.fetchone()
    cur.close()

    user_preferences = preferences_result['preferences'].split(',') if preferences_result and preferences_result['preferences'].strip() else []

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, title, category FROM news_articles")
    articles = cur.fetchall()
    cur.close()

    personalized_articles = [article for article in articles if article['category'] in user_preferences]

    return render_template('articles.html', articles=personalized_articles)

@app.route('/fetch_news')
def fetch_and_store_news():
    logging.info("Fetching and storing news articles...")
    news_list = crawler.fetch_news(app, mysql)
    return jsonify(news_list)

@app.route('/news')
def display_news():
    cur = mysql.connection.cursor()
    cur.execute("SELECT title, category FROM news_articles")
    news_articles = cur.fetchall()
    cur.close()

    if not news_articles:
        logging.info("No articles found in the database.")

    return render_template('news.html', news_articles=news_articles)

def get_article_by_id(article_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM news_articles WHERE id = %s", (article_id,))
    article = cur.fetchone()
    cur.close()
    return article

@app.route('/article/<int:article_id>')
def view_article(article_id):
    article = get_article_by_id(article_id)

    if not article:
        flash('Article not found.', 'error')
        return redirect(url_for('display_articles'))

    title = article['title']
    url = article['url']

    if not url:
        flash('No URL provided for this article.', 'warning')
        summary = 'Summary not available.'
    else:
        from summarization_helper import summarize_article  # Avoid circular import
        try:
            summary = summarize_article(url)
        except Exception as e:
            flash(f'Error while summarizing the article: {str(e)}', 'error')
            summary = 'Summary not available.'

    return render_template('article_detail.html', article=article, summary=summary)
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']

        # Fetch all articles from DB
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, title, content, category FROM news_articles")
        articles = cur.fetchall()
        cur.close()

        # Prepare the documents (titles + contents)
        documents = []
        id_mapping = {}
        for idx, article in enumerate(articles):
            combined_text = (article.get('title') or '') + ' ' + (article.get('content') or '')
            documents.append(combined_text)
            id_mapping[idx] = article

        # Add the user query as the last document
        documents.append(query)

        # Vectorize documents using TF-IDF
        tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf_vectorizer.fit_transform(documents)

        # Compute cosine similarity between query and all documents
        cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()

        # Combine articles with their similarity scores
        articles_with_scores = []
        for idx, score in enumerate(cosine_similarities):
            if score > 0:
                article = id_mapping[idx]
                article_with_score = dict(article)  # Make a copy to avoid mutating the original
                article_with_score['score'] = round(score, 3)  # Round for readability
                articles_with_scores.append(article_with_score)

        # Sort by score descending
        articles_with_scores.sort(key=lambda x: x['score'], reverse=True)

        return render_template('search.html', articles=articles_with_scores)

    return render_template('search.html', articles=None)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# -------------------- MAIN --------------------

if __name__ == '__main__':
    app.run(debug=True) 