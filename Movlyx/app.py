from flask import Flask, render_template, request, redirect, url_for, session
import requests, oracledb

app = Flask(__name__)
app.secret_key = "movlyx_key"

API_KEY = "09a1fbaff2d95589a99607645adce44d"
BASE_URL = "https://api.themoviedb.org/3"

def db_query(sql, params=None, fetch=False, commit=False):
    import oracledb
    conn = None
    res = None
    try:
        
        conn = oracledb.connect(user="samir1", password="12345", dsn="localhost/orcl")
        cur = conn.cursor()
        
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
            
        if fetch:
          
            res = list(cur.fetchall())
        
        if commit:
            conn.commit()
            
        cur.close()
        return res
    except Exception as e:
        print(f"!!! DATABASE ERROR: {e}")
        return [] if fetch else None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def tmdb_get(path, params={}):
    params.update({"api_key": API_KEY, "language": "en-US"})
    r = requests.get(f"{BASE_URL}{path}", params=params)
    return r.json() if r.status_code == 200 else {"results": []}

@app.route("/")
def index():
    
    q = request.args.get('q', '')
    p = request.args.get('page', 1, type=int)
    t = request.args.get('type', 'popular')
    g = request.args.get('genre', '')       
    y = request.args.get('year', '')        
    r = request.args.get('rating', '')    

    # Menyu üçün janrlar
    genres = tmdb_get("/genre/movie/list").get("genres", [])

    if q:
        path = "/search/movie"
        params = {"query": q, "page": p}
    else:
       
        path = "/discover/movie"
        params = {
            "page": p,
            "with_genres": g,
            "primary_release_year": y,
            "vote_average.gte": r, 
            "sort_by": "popularity.desc"
        }
       
        if not (g or y or r):
            path = f"/movie/{t}"
            params = {"page": p}

    data = tmdb_get(path, params)
    
    return render_template("index.html", 
                           movies=data.get("results", []), 
                           current_page=p, 
                           current_type=t, 
                           query=q, 
                           genres=genres, 
                           cur_genre=g, 
                           cur_year=y, 
                           cur_rating=r)


@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):
   
    movie = None
    cast = []
    trailer_key = None
    similar = []
   

    try:
        
        movie = tmdb_get(f"/movie/{movie_id}")
        if not movie:
            return "Film tapılmadı", 404

      
        credits_data = tmdb_get(f"/movie/{movie_id}/credits")
        if credits_data:
            cast = credits_data.get("cast", [])[:6]

        
        video_data = tmdb_get(f"/movie/{movie_id}/videos")
        if video_data and 'results' in video_data:
            for v in video_data['results']:
                if v.get('type') == 'Trailer':
                    trailer_key = v.get('key')
                    break

        
        sim_data = tmdb_get(f"/movie/{movie_id}/similar")
        if sim_data:
            similar = sim_data.get("results", [])[:5]

       

    except Exception as e:
        print(f"Xəta baş verdi: {e}")
 
    return render_template("details.html", 
                           movie=movie, 
                           cast=cast, 
                           trailer_key=trailer_key, 
                           similar=similar 
                           )

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        try:
            db_query("INSERT INTO users (username, password) VALUES (:1, :2)", (request.form["username"], request.form["password"]), commit=True)
            return redirect(url_for("login"))
        except: return render_template("signup.html", error="Username exists!")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db_query("SELECT user_id, username FROM users WHERE username=:1 AND password=:2", (request.form["username"], request.form["password"]), fetch=True)
        if u:
            session.update({"user_id": u[0][0], "username": u[0][1]})
            return redirect(url_for("index"))
        return render_template("login.html", error="Wrong credentials!")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/add_favorite/<int:movie_id>")
def add_favorite(movie_id):
    if "user_id" not in session: return redirect(url_for("login"))
    m = tmdb_get(f"/movie/{movie_id}")
    try: db_query("INSERT INTO favorites (user_id, movie_id, movie_title, poster_path) VALUES (:1, :2, :3, :4)", (session["user_id"], movie_id, m['title'], m['poster_path']), commit=True)
    except: pass
    return redirect(request.referrer or url_for("index"))

@app.route("/favorites")
def show_favorites():
    if "user_id" not in session: return redirect(url_for("login"))
    return render_template("favorites.html", fav_movies=db_query("SELECT movie_id, movie_title, poster_path FROM favorites WHERE user_id=:1", (session["user_id"],), fetch=True))

@app.route("/remove_favorite/<int:movie_id>")
def remove_favorite(movie_id):
    db_query("DELETE FROM favorites WHERE user_id=:1 AND movie_id=:2", (session["user_id"], movie_id), commit=True)
    return redirect(url_for("show_favorites"))





if __name__ == "__main__":
    app.run(debug=True)
