from app import mysql, app

def create_tables():
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            print("Connected to MySQL!")

            # Create Users Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    preferences TEXT
                )
            """)
            print("Users table checked/created.")

            # Create News Articles Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category VARCHAR(100),
                    content TEXT,
                    published_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("News articles table checked/created.")

            mysql.connection.commit()
            cur.close()
            print("✅ Database tables created successfully!")

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_tables()
