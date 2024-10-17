from flask import Flask, render_template, request, jsonify, redirect, url_for, session 
import pandas as pd
import requests
from requests.exceptions import RequestException
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load the datasets
movies = pd.read_csv('C:/Users/USER/Documents/CineIntellect_final/script/cleaned_movies_with_credits.csv')
movies.rename(columns={'tagline': 'tags'}, inplace=True)

# Preprocess the data
def preprocess_data(movies):
    required_columns = ['title', 'genres', 'vote_average', 'runtime', 'release_date', 'original_language', 'id', 'overview', 'cast', 'crew']
    if not all(col in movies.columns for col in required_columns):
        raise ValueError(f"DataFrame must contain {required_columns} columns.")
    
    movies['tags'] = movies['overview'] + ' ' + movies['title'] + ' ' + movies['genres'].apply(lambda x: ' '.join([g['name'] for g in eval(x)])) + ' ' + movies['cast'] + ' ' + movies['crew']
    movies = movies.dropna(subset=['tags', 'title'])
    
    return movies

movies = preprocess_data(movies)

# Create TF-IDF matrix and compute similarity
def create_tfidf_matrix(movies):
    tfidf = TfidfVectorizer(stop_words='english')
    return tfidf.fit_transform(movies['tags'])

def compute_similarity(tfidf_matrix):
    return cosine_similarity(tfidf_matrix, tfidf_matrix)

# Get movie recommendations
def get_recommendations(title, cosine_sim, movies, top_n=10, genre_filter=None, min_rating=None, lang_filter=None, runtime_range=None):
    recommendations = movies.copy()

    if title and title in movies['title'].values:
        idx = movies[movies['title'] == title].index[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:top_n + 1]
        
        movie_indices = [i[0] for i in sim_scores]
        recommendations = movies.iloc[movie_indices]

    if genre_filter:
        recommendations = recommendations[recommendations['genres'].apply(lambda x: any(genre['name'] == genre_filter for genre in eval(x)))]
    
    if min_rating is not None:
        recommendations = recommendations[recommendations['vote_average'] >= min_rating]

    if lang_filter:
        recommendations = recommendations[recommendations['original_language'] == lang_filter]

    if runtime_range:
        recommendations = recommendations[(recommendations['runtime'] >= runtime_range[0]) & (recommendations['runtime'] <= runtime_range[1])]

    return recommendations.head(top_n)

# Fetch posters, movie details, and trailers
def fetch_posters(movie_ids, api_key):
    posters = {}
    for movie_id in movie_ids:
        url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}'
        attempt = 0
        while attempt < 3:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    poster_path = data.get('poster_path')
                    if poster_path:
                        posters[movie_id] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                    else:
                        posters[movie_id] = None
                    break
                else:
                    posters[movie_id] = None
                    break
            except RequestException:
                attempt += 1
                time.sleep(2)
                if attempt == 3:
                    posters[movie_id] = None
    return posters

def fetch_movie_details(movie_id, api_key):
    url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        overview = data.get('overview', 'No overview available.')
        release_date = data.get('release_date', 'Unknown')
        vote_average = data.get('vote_average', 'N/A')
        return {
            'overview': overview,
            'release_date': release_date,
            'vote_average': vote_average
        }
    else:
        return {
            'overview': 'No details available.',
            'release_date': 'Unknown',
            'vote_average': 'N/A'
        }

def fetch_trailer(movie_id, api_key):
    url = f'https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        videos = response.json().get('results', [])
        for video in videos:
            if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                return f"https://www.youtube.com/embed/{video['key']}"
    return None

# Function to fetch trending movies
def fetch_trending_movies(api_key):
    url = f'https://api.themoviedb.org/3/trending/movie/week?api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('results', [])
    return []

# Fetch top-rated movies
def fetch_top_rated_movies(api_key):
    url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={api_key}&language=en-US&page=1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['results']
    else:
        print("Error fetching top-rated movies:", response.status_code)
        return []

DUMMY_USERNAME = "Group4SSG"
DUMMY_PASSWORD = "password"

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == DUMMY_USERNAME and password == DUMMY_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials, please try again."
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    api_key = '5a349a8c71ce723633d050fbee15696a'  
    trending_movies = fetch_trending_movies(api_key)
    top_rated_movies = fetch_top_rated_movies(api_key)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        genre_filter = request.form.get('genre')
        min_rating = float(request.form.get('min_rating', 0.0))
        lang_filter = request.form.get('language')

        runtime_input = request.form.get('runtime')
        if runtime_input:
            runtime_range = runtime_input.split(',')
            runtime_range = (int(runtime_range[0]), int(runtime_range[1])) if len(runtime_range) == 2 else None
        else:
            runtime_range = None

        tfidf_matrix = create_tfidf_matrix(movies)
        cosine_sim = compute_similarity(tfidf_matrix)

        recommendations = get_recommendations(
            title if title else None,
            cosine_sim,
            movies,
            top_n=10,
            genre_filter=genre_filter,
            min_rating=min_rating,
            lang_filter=lang_filter,
            runtime_range=runtime_range
        )

        if recommendations.empty:
            return jsonify({"message": "No recommendations based on your inputs."})

        movie_ids = recommendations['id'].tolist()
        posters = fetch_posters(movie_ids, api_key)

        results = []
        for i in range(len(recommendations)):
            movie_title = recommendations.iloc[i]['title']
            movie_id = recommendations.iloc[i]['id']
            poster_url = posters.get(movie_id)
            movie_details = fetch_movie_details(movie_id, api_key)
            trailer_url = fetch_trailer(movie_id, api_key)

            results.append({
                'title': movie_title,
                'overview': movie_details['overview'],
                'release_date': movie_details['release_date'],
                'rating': movie_details['vote_average'],
                'poster_url': poster_url,
                'trailer_url': trailer_url,
            })

        # Store recommendations in session to access on a different page
        session['recommendations'] = results
        return redirect(url_for('recommendations'))

    return render_template('dashboard.html', trending_movies=trending_movies, top_rated_movies=top_rated_movies)

@app.route('/recommendations', methods=['GET'])
def recommendations():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    results = session.get('recommendations', [])
    return render_template('recommendations.html', recommendations=results)

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('recommendations', None)  
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
