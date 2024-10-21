import tweepy
import os

# Wstaw swoje klucze API
api_key = os.getenv('TWEEPY_API_KEY')
api_secret_key = os.getenv('TWEEPY_SECRET_KEY')

access_token = os.getenv('TWEEPY_ACCESS_TOKEN')
access_token_secret = os.getenv('TWEEPY_SECRET_TOKEN')




# Autoryzacja
auth = tweepy.OAuth1UserHandler(api_key, api_secret_key, access_token, access_token_secret)
tweepy_api = tweepy.API(auth)


def fetch_market_news():
    """Pobiera wiadomości rynkowe z Twittera"""
    tweets = tweepy_api.search_tweets(q="#crypto", count=10)
    return [tweet.text for tweet in tweets]

# Wywołanie funkcji
news = fetch_market_news()
print(news)