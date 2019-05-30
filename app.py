import requests
import flask, math
import sys,os
from flask import Flask, render_template, request, flash,session,redirect,url_for, jsonify, make_response, g
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask_googlemaps import GoogleMaps, Map, icons
import base64, django
from werkzeug.contrib.cache import SimpleCache
from base64 import b64encode, b64decode
from datetime import date, datetime
import openlibrary_api
import json, urllib2, io, jsonpickle


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
lm = LoginManager()
app = Flask(__name__, template_folder="templates")
app.config['GOOGLEMAPS_KEY'] = "AIzaSyAOeYMvF7kPJ7ZcAjOVWiRA8PjCk5E_TsM"
photos = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'static/images'
configure_uploads(app, photos)
GoogleMaps(app)
app.secret_key = 'supersecretkey'
lm.init_app(app)
cache = SimpleCache()

def api_login(username, password, response):
    resp_dict = json.loads(response.text)
    url = 'https://safe-thicket-54536.herokuapp.com/user/info/'+username
    user = requests.get(url)
    print(resp_dict)
    resp_dict2 = json.loads(user.text)
    session['user'] = resp_dict2['user']['username']
    session['token'] = resp_dict['token']
    g.user = session['user']
    g.token = session['token']
    return resp_dict['token']


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.before_request
def before_request():
    g.user = None
    g.token = None
    url = 'https://safe-thicket-54536.herokuapp.com/check_date'
    user = requests.get(url)
    if 'user' in session and 'token' in session:
        g.user = session['user']
        g.token = session['token']

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        session.pop('user', None)
        username = request.form['username']
        password = request.form['password']
        response = requests.post(
            'https://safe-thicket-54536.herokuapp.com/login',
            json={"username":username, "password":password},
        )
        print(response.text)
        if response.text == "Could not verify":
            return render_template('error.html')
        else:
            token = api_login(username, password, response)
        print(token)
        print(session['token'])
        return redirect(url_for('home'))
    else:
        return render_template('login.html')

@app.route('/getcoordinates', methods=['POST'])
def get_coordinates():
    data = request.get_json()
    requests.post('https://safe-thicket-54536.herokuapp.com/user/set/coordinates', json={"current_user": session['user'],
                                                                  "latitude": data['latitude'], "longitude": data['longitude']})
    return make_response('Success')

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    if g.user:
        session.pop('user', None)
        session.pop('token', None)
        return redirect('/')

@app.route('/signup/1', methods=['POST', 'GET'])
def check_username():
    if request.method == 'POST':
        username =request.form['username']
        response = requests.get(
            'https://safe-thicket-54536.herokuapp.com/user/info/'+username)
        print(response.text)
        if response.text == 'no user found!':
            return render_template('signup_1.html', username=username, password=request.form['password'])
        else:
            return render_template('error_signup.html', message="Username already taken.",
                                   message2="Please use a different one.")
    else:
        return render_template('signup_1.html')

def calculate_age(born2):
    today = date.today()
    born = datetime.strptime(born2, "%Y-%m-%d")
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def get_bday(born2):
    fmt = "%a, %d %b %Y %H:%M:%S GMT"
    born = datetime.strptime(born2, fmt).strftime('%B, %d %Y')
    return born

def get_followers(username):
    url = 'https://safe-thicket-54536.herokuapp.com/get-followers'
    response = requests.get(url,  headers={'x-access-token': session['token']}, json={"username": username})
    if response.text == 'No followers':
        return None
    else:
        followers_dict = json.loads(response.text)
        return followers_dict['followers']

def get_followings(username):
    url = 'https://safe-thicket-54536.herokuapp.com/get-following'
    response = requests.get(url,  headers={'x-access-token': session['token']}, json={"username": username})
    if response.text == 'No followers':
        return None
    else:
        following_dict = json.loads(response.text)
        return following_dict['following']

def follow_check(username):
    url = 'https://safe-thicket-54536.herokuapp.com/follow-check'
    print(username)
    response = requests.get(url, headers={'x-access-token': session['token']}, json={"username": username, "current_user": session['user']})
    response_dict = json.loads(response.text)
    print(response_dict)
    if response_dict['data'] == 'Following':
        return True
    else:
        return False

def get_notifications():
    notifications = requests.get('https://safe-thicket-54536.herokuapp.com/notifications', json={"current_user": session['user']},
                                 headers={'x-access-token': session['token']})
    notif_dict = json.loads(notifications.text)
    return notif_dict['notifications']

def get_unread():
    notifications = requests.get('https://safe-thicket-54536.herokuapp.com/notifications', json={"current_user": session['user']},
                                 headers={'x-access-token': session['token']})
    notif_dict = json.loads(notifications.text)
    return notif_dict['total']

def get_messages():
    messages = requests.get('https://safe-thicket-54536.herokuapp.com/get_messages',
                            json={"current_user": session['user']},
                            headers={'x-access-token': session['token']})
    message_dict = json.loads(messages.text)
    return message_dict['messages']

def get_inbox():
    inboxes = requests.get('https://safe-thicket-54536.herokuapp.com/get_inbox',
                           json={"current_user": session['user']},
                           headers={'x-access-token': session['token']})
    inboxes_dict = json.loads(inboxes.text)
    return inboxes_dict['inbox']

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        print('signup')
        username = request.form['username']
        password = request.form['password']
        age = calculate_age(request.form['birth_date'])
        if age <= 18:
            return render_template('error_signup.html', message='Age Requirement:',
                                   message2='You must be 18 or above.')
        address = request.form['address']
        response = requests.post(
            'https://safe-thicket-54536.herokuapp.com/signup',
            json={"first_name": request.form['first_name'], "last_name": request.form['last_name'],
                     "birth_date": request.form['birth_date'], "gender": request.form['gender'],
                    "contact_number": request.form['contact_number'], "username": username, "password": password, "address":address},
        )
        resp_dict = json.loads(response.text)
        api_login(username, password, response)

        return redirect('interests')
    else:
        return render_template('signup.html')

@app.route('/home', methods=['POST', 'GET'])
def home():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/books/latest'
        url2 = 'https://safe-thicket-54536.herokuapp.com/bookshelf/books/recent'
        url3 = 'https://safe-thicket-54536.herokuapp.com/bookshelf/books/toprated'
        books = requests.get(url, headers={'x-access-token': session['token']})
        books2 = requests.get(url2, headers={'x-access-token': session['token']})
        books3 = requests.get(url3, headers={'x-access-token': session['token']})
        action = requests.get('https://safe-thicket-54536.herokuapp.com/interests/view2/Action', headers={'x-access-token': session['token']})
        action_dict = json.loads(action.text)
        drama = requests.get('https://safe-thicket-54536.herokuapp.com/interests/view2/Drama', headers={'x-access-token': session['token']})
        drama_dict = json.loads(drama.text)
        horror = requests.get('https://safe-thicket-54536.herokuapp.com/interests/view2/Horror', headers={'x-access-token': session['token']})
        fiction = requests.get('https://safe-thicket-54536.herokuapp.com/category/view/Fiction', headers={'x-access-token': session['token']})
        nonfiction = requests.get('https://safe-thicket-54536.herokuapp.com/category/view/Non-Fiction', headers={'x-access-token': session['token']})
        acads = requests.get('https://safe-thicket-54536.herokuapp.com/category/view/Educational', headers={'x-access-token': session['token']})
        notifications = requests.get('https://safe-thicket-54536.herokuapp.com/notifications', json= {"current_user": session['user']}, headers={'x-access-token': session['token']})
        notif_dict = json.loads(notifications.text)
        horror_dict = json.loads(horror.text)
        book_dict = json.loads(books.text)
        book2_dict = json.loads(books2.text)
        book3_dict = json.loads(books3.text)
        fict_dict = json.loads(fiction.text)
        nonfict_dict = json.loads(nonfiction.text)
        acad_dict = json.loads(acads.text)
        messages = requests.get('https://safe-thicket-54536.herokuapp.com/get_messages', json={"current_user": session['user']},
                                headers={'x-access-token': session['token']})
        message_dict = json.loads(messages.text)
        inboxes = requests.get('https://safe-thicket-54536.herokuapp.com/get_inbox', json={"current_user": session['user']},
                               headers={'x-access-token': session['token']})
        inboxes_dict = json.loads(inboxes.text)
        print(message_dict)
        print(notif_dict)
        return render_template('dashboard.html', notifications=notif_dict['notifications'], unread=notif_dict['total'], books2=book2_dict['book'], books=book_dict['book'],\
                               horrorbooks=horror_dict['book'], actionbooks=action_dict['book'], \
                               dramabooks=drama_dict['book'], user=session['user'], acadbooks=acad_dict['book'], \
                               fictionbooks=fict_dict['book'], books3=book3_dict['book'], nonficbooks=nonfict_dict['book'],
                               inboxes=inboxes_dict['inbox'], messages=message_dict['messages'])
    else:
        return redirect('unauthorized')

@app.route('/unauthorized', methods=['POST', 'GET'])
def unauthorized():
    return render_template('unauthorized.html')

@app.route('/add_unpublishedbook', methods=['POST', 'GET'])
def add_unpublishedbook():
    if g.user:
        if request.method == 'POST':
            fiction = {'Action', 'Adventure', 'Drama', 'Horror', 'Mystery', 'Mythology'}
            non_fiction = {'Biography', 'Essay', 'Journalism', 'Personal Narrative', 'Reference Book', 'Speech'}
            educational = {'English', 'Math', 'History', 'Science'}
            genre = request.form['genre']
            if genre in fiction:
                category = "Fiction"
            elif genre in non_fiction:
                category = "Non-Fiction"
            else:
                category = "Educational"

            methods = request.form.get('methods')
            print(methods)
            if methods == 'For Sale':
                price = request.form.get('price2')
                print(price)
            else:
                price = 0
            if methods == 'For Rent':
                priceRate = request.form.get('price')
                print(priceRate)
            else:
                priceRate = 0

            response = requests.post(
                'https://safe-thicket-54536.herokuapp.com/user/addbook', headers={'x-access-token': session['token']},
                json={"current_user": session['user'], 'title': request.form['title'], "edition": None,
                      "year": None, "author_name": request.form['author_name'], "publisher_name":"None", "isbn":None,
                      "description": request.form['description'], "price": price, "price_rate": priceRate,
                      "genre": request.form['genre'], "quantity": request.form['quantity'], "category": category, "method": methods, "book_cover": 'default.jpg'},
            )
            resp = json.loads(response.text)
            print(resp['message'])
            if resp['message'] == 'The book is already in your bookshelf!':
                return render_template('addbook.html', message=resp['message'], color='danger', x='&times;', notifications=get_notifications(), unread=get_unread())
            return redirect('home')
        else:
            return render_template('addbook.html', display='none',  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')

@app.route('/interests', methods=['POST', 'GET'])
def interests():
    if g.user:
        if request.method == 'POST':
            interests = request.form.getlist('interests')
            print(interests)
            if len(interests) == 1:
                interests = request.form.get('interests')
                url = 'https://safe-thicket-54536.herokuapp.com/interests/'+interests
                requests.post(url, headers={'x-access-token': session['token']}, json={"current_user": session['user']})
            else:
                for interest in interests:
                    url='https://safe-thicket-54536.herokuapp.com/interests/'+interest
                    response = requests.post(url, json={"current_user": session['user']})

            return redirect('home')

        return render_template('interest.html')

    else:
        return redirect('unauthorized')

@app.route('/addbook', methods=['POST', 'GET'])
def addbook():
    if g.user:
        if request.method == 'POST':
            fiction = {'Action', 'Adventure', 'Drama', 'Horror', 'Mystery', 'Mythology'}
            non_fiction = {'Biography', 'Essay', 'Journalism', 'Personal Narrative', 'Reference Book', 'Speech'}
            educational = {'English', 'Math', 'History', 'Science'}
            genre = request.form['genre']
            if genre in fiction:
                category = "Fiction"
            elif genre in non_fiction:
                category = "Non-Fiction"
            else:
                category = "Educational"

            methods = request.form.getlist('methods')
            priceRate = 0
            price = 0
            print('methods')
            print(request.form.getlist('methods'))
            if len(methods) == 1:
                methods = request.form.get('methods')
                if methods == 'For Sale':
                    price = request.form.get('price2')
                    print(price)
                else:
                    price = 0
                if methods == 'For Rent':
                    priceRate = request.form.get('price')
                    print(priceRate)
                else:
                    priceRate = 0
            print(methods)
            for x in methods:
                if x == 'For Sale':
                    price = request.form.get('price2')
                if x == 'For Rent':
                    priceRate = request.form.get('price')

            print(category)
            response = requests.post(
                'https://safe-thicket-54536.herokuapp.com/user/addbook', headers={'x-access-token': session['token']},
                json={"current_user": session['user'], 'title': request.form['title'],
                      "year": request.form['year'], "isbn": request.form['isbn'],
                      "publisher_name": request.form['publisher'], "author_name": request.form['author'],
                        "category": category, "book_cover": request.form['book_cover'],
                      "description": request.form['description'], "price": price, "price_rate": priceRate,
                      "genre": genre, "quantity": request.form['quantity'], "method": methods}
            )
            print(response.text)
            if response.text == 'The book is already in your bookshelf!':
                return render_template('addbook_isbn.html', display2='none', display='block',  notifications=get_notifications(), unread=get_unread())
            return render_template('addbook_isbn.html', display2='block', display='none',  notifications=get_notifications(), unread=get_unread())
        else:
            return render_template('addbook_isbn.html', display='none', display2='none',  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')




@app.route('/addbook/step-1', methods=['POST', 'GET'])
def addbook_step1():
    if g.user:
        if request.method == 'POST':
            book = {}
            book['title'] = request.form['title']
            book['description'] = request.form['description']
            book['book_cover'] = request.form['book_cover']
            book['author_name'] = request.form['author_name']
            book['publisher'] = request.form['publisher']
            book['year'] = request.form['year']
            book['isbn'] = request.form['isbn']
            print(book)

            return render_template('addbook_step1.html', book=book,  notifications=get_notifications(), unread=get_unread())
        else:
            book = {}
            book['title'] = request.form['title']
            book['description'] = request.form['description']
            book['book_cover'] = request.form['book_cover']
            book['author_name'] = request.form['author_name']
            book['publisher'] = request.form['publisher']
            book['year'] = request.form['year']
            book['isbn'] = request.form['isbn']
            print(book)

            return render_template('addbook_step1.html', book=book,  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')


@app.route('/title/search/<search>', methods=['GET'])
def title_search(search):
    if g.user:
        output = []
        url = "https://www.googleapis.com/books/v1/volumes?q=intitle:{0}&key=AIzaSyAOeYMvF7kPJ7ZcAjOVWiRA8PjCk5E_TsM&maxResults=40".format(search)
        print(url)
        response = requests.get(url)
        resp = json.loads(response.text)
        print(response.text)
        response2 = requests.post('https://safe-thicket-54536.herokuapp.com/book/title', json={"title": search}, headers={'x-access-token': session['token']})
        print(response2.text)
        print(resp['totalItems'])
        if int(resp['totalItems']) == 0 and response2.text == 'Book not found':
            return render_template('addbook_noresult.html')
        elif int(resp['totalItems']) == 0:
            resp2 = json.loads(response2.text)
            return render_template('addbook_results.html', books={}, dbbooks=resp2['books'])
        else:
            for book_item in resp['items']:
                books = {}
                if((('publisher' in book_item['volumeInfo']) and ('industryIdentifiers' in book_item['volumeInfo']))
                  and (('imageLinks' in book_item['volumeInfo']) and ('authors' in book_item['volumeInfo'])))\
                    and ('description' in book_item['volumeInfo'] and 'publishedDate' in book_item['volumeInfo']):
                    books['title'] = book_item['volumeInfo']['title']
                    books['publishers'] = book_item['volumeInfo']['publisher']
                    books['isbn'] = book_item['volumeInfo']['industryIdentifiers'][0]['identifier']
                    books['book_cover'] = book_item['volumeInfo']['imageLinks']['thumbnail']
                    books['author_name'] = book_item['volumeInfo']['authors'][0]
                    books['description'] = book_item['volumeInfo']['description']
                    books['year'] = book_item['volumeInfo']['publishedDate']
                    output.append(books)
                else:
                    continue
            if response2.text != 'Book not found':
                resp2 = json.loads(response2.text)
                return render_template('addbook_results.html', books=output, dbbooks=resp2['books'],  notifications=get_notifications(), unread=get_unread())
            return render_template('addbook_results.html', books=output,  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')

@app.route('/author/search/<search>', methods=['GET'])
def author_search(search):
    if g.user:
        output = []
        print "djsjdjsdj"
        url = "https://www.googleapis.com/books/v1/volumes?q=inauthor:{0}&key=AIzaSyAOeYMvF7kPJ7ZcAjOVWiRA8PjCk5E_TsM&maxResults=40".format(search)
        response = requests.get(url)
        resp = json.loads(response.text)
        print search
        print resp
        response2 = requests.post('https://safe-thicket-54536.herokuapp.com/book/author', json={"author_name": search}, headers={'x-access-token': session['token']})
        print "dhdhhdhhdhdhdh"
        print(response2.text)
        if int(resp['totalItems']) == 0 and response2.text == 'Author not found!':
            return render_template('addbook_noresult.html')
        elif int(resp['totalItems']) == 0:
            resp2 = json.loads(response2.text)
            return render_template('addbook_results.html', books={}, dbbooks=resp2['books'])
        for book_item in resp['items']:
            books = {}
            if ((('publisher' in book_item['volumeInfo']) and ('industryIdentifiers' in book_item['volumeInfo']))
                and (('imageLinks' in book_item['volumeInfo']) and ('authors' in book_item['volumeInfo'])))\
                    and ('description' in book_item['volumeInfo'] and 'publishedDate' in book_item['volumeInfo']):
                books['title'] = book_item['volumeInfo']['title']
                books['publishers'] = book_item['volumeInfo']['publisher']
                books['isbn'] = book_item['volumeInfo']['industryIdentifiers'][0]['identifier']
                books['book_cover'] = book_item['volumeInfo']['imageLinks']['thumbnail']
                books['author_name'] = book_item['volumeInfo']['authors'][0]
                books['description'] = book_item['volumeInfo']['description']
                books['year'] = book_item['volumeInfo']['publishedDate']
                output.append(books)
            else:
                continue
        if response2.text != 'Author not found!':
            resp2 = json.loads(response2.text)
            return render_template('addbook_results.html', books=output, dbbooks=resp2['books'],  notifications=get_notifications(), unread=get_unread())
        else:
            return render_template('addbook_results.html', books=output,  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')

@app.route('/isbn/search', methods=['POST', 'GET'])
def isbn_search():
    if g.user:
        if request.method == 'POST':
            filter = request.form['searchfilter']
            search = request.form['search']
            print(filter)
            if filter == 'Title':
                return redirect(url_for('title_search', search=search))
            elif filter == 'Author':
                return redirect(url_for('author_search', search=search))
            else:
                isbn = request.form['search']
                response4 = requests.post('https://safe-thicket-54536.herokuapp.com/book/isbn', json={"isbn": isbn}, headers={'x-access-token': session['token']})
                url3 = "https://openlibrary.org/api/books?bibkeys=ISBN:{0}&jscmd=details&format=json".format(isbn)
                url = "https://openlibrary.org/api/books?bibkeys=ISBN:{0}&jscmd=data&format=json".format(isbn)
                url2 = "https://www.googleapis.com/books/v1/volumes?q=isbn:{0}&key=AIzaSyAOeYMvF7kPJ7ZcAjOVWiRA8PjCk5E_TsM".format(isbn)
                output = []
                book = {}
                response2 = requests.get(url2)
                resp2 = json.loads(response2.text)
                print(resp2['totalItems'])
                print(response4.text)
                if response4.text == 'Book not found':
                    response = requests.get(url)
                    resp = json.loads(response.text)
                    print(resp)
                    book['isbn'] = isbn
                    if (resp2['totalItems'] == 0) and (not resp):
                        return render_template('addbook_noresult.html')
                    elif not resp:
                        print(response2.text)
                        book['title'] = resp2['items'][0]['volumeInfo']['title']
                        if 'publisher' in resp2['items'][0]['volumeInfo']:
                            book['publishers'] = resp2['items'][0]['volumeInfo']['publisher']
                        else:
                            book['publishers'] = ''
                        book['book_cover'] = resp2['items'][0]['volumeInfo']['imageLinks']['thumbnail']
                        book['author_name'] = resp2['items'][0]['volumeInfo']['authors'][0]
                        book['description'] = resp2['items'][0]['volumeInfo']['description']
                        book['year'] = resp2['items'][0]['volumeInfo']['publishedDate']
                    else:
                        index = "ISBN:{0}".format(isbn)
                        book['title'] = resp[index]['title']
                        book['publishers'] = resp[index]['publishers'][0]['name']
                        if 'cover' in resp[index]:
                            book['book_cover'] = resp[index]['cover']['large']
                        else:
                            book['cover'] = '#'
                        book['author_name'] = resp[index]['authors'][0]['name']
                        date1 = resp[index]['publish_date']
                        book['year'] = date1
                        if resp2['totalItems'] != 0:
                            book['title'] = resp2['items'][0]['volumeInfo']['title']
                            if 'publisher' in resp2['items'][0]['volumeInfo']:
                                book['publishers'] = resp2['items'][0]['volumeInfo']['publisher']
                            else:
                                book['publishers'] = ''
                            if 'authors' in resp2['items'][0]['volumeInfo']:
                                book['author_name'] = resp2['items'][0]['volumeInfo']['authors'][0]
                            book['description'] = resp2['items'][0]['volumeInfo']['description']
                            book['year'] = resp2['items'][0]['volumeInfo']['publishedDate']
                    output.append(book)
                    return render_template('addbook_result.html', book=output[0])
                else:
                    resp4 = json.loads(response4.text)
                    print(resp4)
                    return render_template('addbook_result.html', book=resp4['book'][0],  notifications=get_notifications(), unread=get_unread())

        else:
            return render_template('addbook_result.html', book={},  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/<book_id>/upload/<num>', methods=['POST', 'GET'])
def add_book_pic(book_id, num):
    if request.method == 'POST' and 'photo' in request.files:
        filename = photos.save(request.files['photo'], session['user']+"/books")
        response = requests.post('https://safe-thicket-54536.herokuapp.com/book/picture',
                                 json={"current_user": session['user'], "filename": filename, "book_id": book_id, "num": num})
        message = json.loads(response.text)
        print[message['message']]
        return redirect(url_for('edit_ownbook', book_id=book_id, username=session['user']))
    return redirect(url_for('edit_ownbook', book_id=book_id, username=session['user']))


### PROFILE ###
@app.route('/profile', methods=['GET'])
def profile():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/'+session['user']
        user = requests.get(url)
        print(user.text)
        user_dict = json.loads(user.text)
        bday = get_bday(user_dict['user']['birth_date'])
        map = profilemap(session['user'])
        # profilepic = user_dict['user']['profpic']
        profilepic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ session['user'] +'/photo')
        ratings = requests.get('https://safe-thicket-54536.herokuapp.com/user/ratings',
                               json={"current_user": session['user'], "username": session['user']},
                               headers={'x-access-token': session['token']})
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/user/comments', json={"username": session['user']}, headers={'x-access-token': session['token']})
        ratings_dict = json.loads(ratings.text)
        comments_dict = json.loads(comments.text)
        username = session['user']
        followers = get_followers(username)
        following = get_followings(username)
        print(comments_dict)
        book_details = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/availability', headers={'x-access-token': session['token']}, json={"current_user": session['user']})
        books = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf', headers={'x-access-token': session['token']}, json={"current_user": session['user']})
        if books.text == "no books found":
            return render_template('profile.html', books={}, user=user_dict['user'], bday=bday, map=map,  profilepic=profilepic.img,
                                   ratings=ratings_dict['ratings'], comments=comments_dict['comments'], followers=followers, following=following,  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
        book_dict=json.loads(books.text)
        book_details_dict=json.loads(book_details.text)
        return render_template('profile.html', books=book_dict['book'], book_details=book_details_dict, user=user_dict['user'], profilepic=profilepic.img, bday=bday, map=map,
                               ratings=ratings_dict['ratings'], comments=comments_dict['comments'], followers=followers, following=following,  notifications=get_notifications(), unread=get_unread()
                               ,
                               inboxes=get_inbox(), messages=get_messages()
                               )
    else:
        return redirect('unauthorized')

@app.route('/profile/edit', methods=['POST', 'GET'])
def edit_profile():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/' + session['user']
        user = requests.get(url)
        user_dict = json.loads(user.text)
        map = profilemap(session['user'])
        bday = get_bday(user_dict['user']['birth_date'])
        # profilepic = (user_dict['user']['profpic'])
        profilepic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ session['user'] +'/photo')
        book_details = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/availability', headers={'x-access-token': session['token']},
                                    json={"current_user": session['user']})
        books = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf', headers={'x-access-token': session['token']}, json={"current_user": session['user']})
        # profilepic = user_dict['user']['profpic']
        ratings = requests.get('https://safe-thicket-54536.herokuapp.com/user/ratings',
                               json={"current_user": session['user'], "username": session['user']},
                               headers={'x-access-token': session['token']})
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/user/comments', json={"username": session['user']}, headers={'x-access-token': session['token']})
        ratings_dict = json.loads(ratings.text)
        comments_dict = json.loads(comments.text)
        if books.text == "no books found":
            return render_template('edit_profile.html', books={}, user=user_dict['user'], bday=bday,map=map, profilepic=profilepic.img, display='none',
                                   ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
        book_dict = json.loads(books.text)
        book_details_dict = json.loads(book_details.text)
        if request.method == 'POST':
            firstname = request.form['first_name']
            lastname = request.form['last_name']
            gender = request.form['gender']
            bdate = request.form['birth_date']
            age = calculate_age(bdate)
            if age < 18:
                books = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf', headers={'x-access-token': session['token']}, json={"current_user": session['user']})
                if books.text == "no books found":
                    return render_template('edit_profile.html', user=user_dict['user'], bday=bday, map=map,
                                           profilepic=profilepic.img, display='block', ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
                return render_template('edit_profile.html', user=user_dict['user'], books=book_dict['book'], bday=bday,
                                       map=map, profilepic=profilepic.img, display='block', ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())

            contact_num = request.form['contact_number']
            response = requests.post('https://safe-thicket-54536.herokuapp.com/user/edit', json={"username": session['user'], "first_name": firstname,
                                                                              "last_name": lastname, "birth_date": bdate, "gender": gender,
                                                                              "contact_num":contact_num}, headers={'x-access-token': session['token']})
            print(response.text)
            return redirect('profile')
        else:
            return render_template('edit_profile.html', user=user_dict['user'], books=book_dict['book'], bday=bday, map=map, profilepic=profilepic.img, display='none',
                                   ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
    else:
        return redirect('unauthorized')

@app.route('/profile/edit/birthday', methods=['GET', 'POST'])
def edit_profile_birthday():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/' + session['user']
        user = requests.get(url)
        user_dict = json.loads(user.text)
        map = profilemap(session['user'])
        bday = get_bday(user_dict['user']['birth_date'])
        # profilepic = (user_dict['user']['profpic'])
        profilepic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ session['user'] +'/photo')
        book_details = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/availability', headers={'x-access-token': session['token']},
                                    json={"current_user": session['user']})
        books = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf', headers={'x-access-token': session['token']}, json={"current_user": session['user']})
        # profilepic = user_dict['user']['profpic']
        ratings = requests.get('https://safe-thicket-54536.herokuapp.com/user/ratings',
                               json={"current_user": session['user'], "username": session['user']},
                               headers={'x-access-token': session['token']})
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/user/comments', json={"username": session['user']}, headers={'x-access-token': session['token']})
        ratings_dict = json.loads(ratings.text)
        comments_dict = json.loads(comments.text)
        if books.text == "no books found":
            return render_template('edit_profile_birthday.html', books={}, user=user_dict['user'], bday=bday,map=map, profilepic=profilepic.img, display='none',
                                   ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
        book_dict = json.loads(books.text)
        book_details_dict = json.loads(book_details.text)
        if request.method == 'POST':
            firstname = request.form['first_name']
            lastname = request.form['last_name']
            gender = request.form['gender']
            bdate = request.form['birth_date']
            age = calculate_age(bdate)
            if age < 18:
                books = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf', headers={'x-access-token': session['token']}, json={"current_user": session['user']})
                if books.text == "no books found":
                    return render_template('edit_profile.html', user=user_dict['user'], bday=bday, map=map,
                                           profilepic=profilepic.img, display='block', ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
                return render_template('edit_profile.html', user=user_dict['user'], books=book_dict['book'], bday=bday,
                                       map=map, profilepic=profilepic.img, display='block', ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())

            contact_num = request.form['contact_number']
            response = requests.post('https://safe-thicket-54536.herokuapp.com/user/edit', json={"username": session['user'], "first_name": firstname,
                                                                              "last_name": lastname, "birth_date": bdate, "gender": gender,
                                                                              "contact_num":contact_num}, headers={'x-access-token': session['token']})
            print(response.text)
            return redirect('profile')
        else:
            return render_template('edit_profile_birthday.html', user=user_dict['user'], books=book_dict['book'], bday=bday, map=map, profilepic=profilepic.img, display='none',
                                   ratings=ratings_dict['ratings'], comments=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
    else:
        return redirect('unauthorized')

@app.route('/profile/<username>', methods=['GET', 'POST'])
def view_profile(username):
    if g.user:
        if username == session['user']:
            return redirect('profile')
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/'+username
        url2 = 'https://safe-thicket-54536.herokuapp.com/user/info/' + session['user']
        user = requests.get(url)
        user2 = requests.get(url2)
        ratings = requests.get('https://safe-thicket-54536.herokuapp.com/user/ratings', json={"current_user": session['user'], "username": username}, headers={'x-access-token': session['token']})
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/user/comments', json={"username": username}, headers={'x-access-token': session['token']})
        user_dict = json.loads(user.text)
        user2_dict = json.loads(user2.text)
        ratings_dict = json.loads(ratings.text)
        comments_dict = json.loads(comments.text)
        bday = get_bday(user_dict['user']['birth_date'])
        profilepic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ username +'/photo')
        viewer_profpic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ session['user'] +'/photo')
        map = profilemap_user(username)
        followers = get_followers(username)
        following = get_followings(username)
        followcheck = follow_check(username)
        book_details = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/availability', headers={'x-access-token': session['token']}, json={"current_user": username} )
        books = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf', headers={'x-access-token': session['token']}, json={"current_user": username})
        if books.text == "no books found":
            return render_template('user_profile.html', books={}, user=user_dict['user'], bday=bday, map=map, profilepic=profilepic.img, ratings=ratings_dict['ratings'], comments=comments_dict['comments'],
                                   viewer_profpic=viewer_profpic.img, followers=followers, following=following, followcheck=followcheck,  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
        book_dict=json.loads(books.text)
        book_details_dict=json.loads(book_details.text)
        return render_template('user_profile.html', books=book_dict['book'], book_details=book_details_dict, user=user_dict['user'], bday=bday, map=map, profilepic=profilepic.img,
                               ratings=ratings_dict['ratings'], comments=comments_dict['comments'], viewer_profpic=viewer_profpic.img, followers=followers, following=following, followcheck=followcheck,
                               notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages()
                               )
    else:
        return redirect('unauthorized')


@app.route('/profile/<username>/followers', methods=['GET'])
def followers(username):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/' + username
        user = requests.get(url)
        user_dict = json.loads(user.text)
        followers = get_followers(username)
        print(followers)
        return render_template('followers.html', followers=followers, user=user_dict['user'],  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')

@app.route('/profile/<username>/following', methods=['GET'])
def following(username):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/' + username
        user = requests.get(url)
        user_dict = json.loads(user.text)
        following = get_followings(username)
        print(following)
        return render_template('following.html', following=following, user=user_dict['user'],  notifications=get_notifications(), unread=get_unread())
    else:
        return redirect('unauthorized')

#SEARCHING IN YOUR OWN PROFILE
@app.route('/profile/search/book', methods=['POST'])
def profile_search():
    if g.user:
        search = request.form['search']
        username = request.form['username']
        print(search)
        print(username)
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/'+username
        user = requests.get(url, headers={'x-access-token': session['token']})
        books = requests.get('https://safe-thicket-54536.herokuapp.com/search/user/books', json={"username": username, "item": search},
                                                                        headers={'x-access-token': session['token']})
        book_dict = json.loads(books.text)
        user_dict = json.loads(user.text)
        bday = get_bday(user_dict['user']['birth_date'])
        # profilepic = user_dict['user']['profpic']
        profilepic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ session['user'] +'/photo')
        map = profilemap(username)
        return render_template('profile.html', books=book_dict['book'], user=user_dict['user'], bday=bday, map=map, profilepic=profilepic.img,  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
    else:
        return redirect('unauthorized')

#SEARCHING IN OTHER PROFILE
@app.route('/profile/<username>/search/book', methods=['POST'])
def profile_user_search(username):
    if g.user:
        search = request.form['search']
        username = username
        print(search)
        print(username)
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/'+username
        user = requests.get(url, headers={'x-access-token': session['token']})
        books = requests.get('https://safe-thicket-54536.herokuapp.com/search/user/books', json={"username": username, "item": search},
                                                                        headers={'x-access-token': session['token']})
        book_dict = json.loads(books.text)
        user_dict = json.loads(user.text)
        bday = get_bday(user_dict['user']['birth_date'])
        # profilepic = user_dict['user']['profpic']
        profilepic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ session['user'] +'/photo')
        map = profilemap_user(username)
        return render_template('user_profile.html', books=book_dict['book'], user=user_dict['user'], bday=bday, map=map, profilepic=profilepic.img,  notifications=get_notifications(), unread=get_unread(),
                                   inboxes=get_inbox(), messages=get_messages())
    else:
        return redirect('unauthorized')

def profilemap(username):
    user_details = requests.get('https://safe-thicket-54536.herokuapp.com/user/coordinates',
                                json={"current_user": username}, headers={'x-access-token': session['token']})
    users_details = requests.get('https://safe-thicket-54536.herokuapp.com/users/coordinates',
                                json={"current_user": username, "username": username}, headers={'x-access-token': session['token']})
    user = json.loads(user_details.text)
    users = json.loads(users_details.text)
    print(user)
    print(users)
    users1 =users['users']
    output = []
    user_1 = {}
    user_1['icon'] = 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
    profpic = user['user'][0]['profpic']
    user_1['lat'] = user['user'][0]['latitude']
    user_1['lng'] = user['user'][0]['longitude']
    user_1['infobox'] = """<h6 style="text-align:center;">{0}</h6><img src='data:image;base64, {1}' onerror="this.src='{{url_for('static', 
    filename='images/none.jpeg')}}'" alt="{2}" style="width:80px; height:80px;" alt=" " />""".format('My Current Location', profpic, user['user'][0]['username'])
    output.append(user_1)

    for user1 in users1:
        user_data = {}
        profpic2 = user1['other_profpic']
        user_data['icon'] = 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
        user_data['lat'] = user1['other_user_lat']
        user_data['lng'] = user1['other_user_lng']
        user_data['infobox'] = """<h6 style="text-align:center;">{0}</h6><img src='data:image;base64, {1}' onerror="this.src='{{url_for('static', 
        filename='images/none.jpeg')}}'" alt="{2}" style="width:80px; height:80px;" alt=" " />""".format(user1['other_username'],profpic2, user1['other_username'])
        output.append(user_data)

    print(output)
    user_lat=user['user'][0]['latitude']
    user_lng = user['user'][0]['longitude']
    profile_map = Map(
        identifier="Booksnearyou",
        lat=user_lat,
        lng=user_lng,
        style="width: 100%; height:500px;",
        circles=[{
            'stroke_color': '#528BE2',
            'stroke_opacity': 1.0,
            'stroke_weight': 7,
            'fill_color': '#528BE2',
            'fill_opacity': 0.2,
            'center': {
                'lat': user_lat,
                'lng': user_lng
            },
            'radius': 1500 * 50,
        }],
        markers=output
    )
    return profile_map

def profilemap_user(username):
    user_details = requests.get('https://safe-thicket-54536.herokuapp.com/user/coordinates',
                                json={"current_user": username}, headers={'x-access-token': session['token']})
    users_details = requests.get('https://safe-thicket-54536.herokuapp.com/users/coordinates',
                                json={"current_user": session['user'], "username": username}, headers={'x-access-token': session['token']})
    your_details = requests.get('https://safe-thicket-54536.herokuapp.com/user/coordinates',
                                json={"current_user": session['user']}, headers={'x-access-token': session['token']})
    user = json.loads(user_details.text)
    users = json.loads(users_details.text)
    you = json.loads(your_details.text)
    users1 =users['users']
    output = []
    you2 = {}
    you2['icon'] = 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
    profpic = you['user'][0]['profpic']
    you2['lat'] = you['user'][0]['latitude']
    you2['lng'] = you['user'][0]['longitude']
    you2['infobox'] = """<h6 style="text-align:center;">Your Location</h6><img src='data:image;base64, {0}' onerror="this.src='{{url_for('static', 
        filename='images/none.jpeg')}}'" alt="{1}" style="width:80px; height:80px;" alt=" " />""".format(profpic, you['user'][0]['username'])
    output.append(you2)
    user_1 = {}
    user_1['icon'] = 'http://maps.google.com/mapfiles/ms/icons/yellow-dot.png'
    profpic = user['user'][0]['profpic']
    user_1['lat'] = user['user'][0]['latitude']
    user_1['lng'] = user['user'][0]['longitude']
    user_1['infobox'] = """<h6 style="text-align:center;">{0}'s Location</h6><img src='data:image;base64, {1}' onerror="this.src='{{url_for('static', 
    filename='images/none.jpeg')}}'" alt="{2}" style="width:80px; height:80px;" alt=" " />""".format(user['user'][0]['username'], profpic, user['user'][0]['username'])
    output.append(user_1)

    for user1 in users1:
        user_data = {}
        profpic2 = user1['other_profpic']
        user_data['icon'] = 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
        user_data['lat'] = user1['other_user_lat']
        user_data['lng'] = user1['other_user_lng']
        user_data['infobox'] = """<h6 style="text-align:center;">{0}</h6><img src='data:image;base64, {1}' onerror="this.src='{{url_for('static', 
        filename='images/none.jpeg')}}'" alt="{2}" style="width:80px; height:80px;" alt=" " />""".format(user1['other_username'],profpic2, user1['other_username'])
        output.append(user_data)

    print(output)
    user_lat=user['user'][0]['latitude']
    user_lng = user['user'][0]['longitude']
    profile_map = Map(
        identifier="Booksnearyou",
        lat=user_lat,
        lng=user_lng,
        style="width: 100%; height:500px;",
        circles=[{
            'stroke_color': '#528BE2',
            'stroke_opacity': 1.0,
            'stroke_weight': 7,
            'fill_color': '#528BE2',
            'fill_opacity': 0.2,
            'center': {
                'lat': user_lat,
                'lng': user_lng
            },
            'radius': 1500 * 50,
        }],
        markers=output
    )
    return profile_map

@app.route('/image/<username>/profpic')
def user_profpicture(username):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/user/info/' + username
        user = requests.get(url)
        user_dict = json.loads(user.text)
        # profilepic = user_dict['user']['profpic']
        profilepic = requests.get('https://safe-thicket-54536.herokuapp.com/user/info/'+ session['user'] +'/photo')
        return app.response_class(profilepic.img, mimetype='application/octet-stream')
    else:
        return redirect('unauthorized')



@app.route('/profile/upload', methods=['POST'])
def add_profile_pic():
    if request.method == 'POST' and 'photo' in request.files:
        file = request.files['photo']
        # response = requests.post('https://safe-thicket-54536.herokuapp.com/profile/picture', json={"current_user": session['user'], "filename": b64encode(file.read())}, headers={'x-access-token': session['token']})
        response = request.post('https://safe-thicket-54536.herokuapp.com/user/info/'+ username +'/upload', { "img_type": 'image', "image": file})
        message = json.loads(response['msg'])
        return redirect('profile')
    return redirect('profile')

@app.route('/user/rate/<username>', methods=['POST'])
def rate_user(username):
    if g.user:
        ratings = request.form['stars']
        print(ratings)
        response = requests.post('https://safe-thicket-54536.herokuapp.com/rate/user', json={"ratings":ratings, "current_user":session['user'], "username":username}, headers={'x-access-token': session['token']})
        print(response.text)
        return redirect(url_for('view_profile', username=username))
    else:
        return redirect('unauthorized')

@app.route('/user/comment/<username>', methods=['POST'])
def comment_user(username):
    if g.user:
        comment = request.form['comment']
        response = requests.post('https://safe-thicket-54536.herokuapp.com/comment/user', json={"comment":comment, "current_user":session['user'], "username":username}, headers={'x-access-token': session['token']})
        print(response.text)
        return redirect(url_for('view_profile', username=username))
    else:
        return redirect('unauthorized')

### END PROFILE ###
@app.route('/book/rate/<contains_id>/<book_id>/<username>', methods=['POST'])
def rate_book(contains_id, book_id, username):
    if g.user:
        ratings = request.form['stars']
        print(ratings)
        response = requests.post('https://safe-thicket-54536.herokuapp.com/rate-book', json={"ratings":ratings, "username":session['user'], "book_id":book_id, "owner": username}, headers={'x-access-token': session['token']})
        print(response.text)
        return redirect(url_for('viewbook', book_id=book_id, username=username))
    else:
        return redirect('unauthorized')

@app.route('/book/comment/<contains_id>/<book_id>/<username>', methods=['POST'])
def comment_book(contains_id, book_id, username):
    if g.user:
        comment = request.form['comment']
        response = requests.post('https://safe-thicket-54536.herokuapp.com/comment-book', json={"comment":comment, "username":session['user'], "book_id":book_id, "owner":username}, headers={'x-access-token': session['token']})
        print(response.text)
        return redirect(url_for('viewbook', book_id=book_id, username=username))
    else:
        return redirect('unauthorized')

@app.route('/book/comment2  /<book_id>/<username>', methods=['POST'])
def comment_book2(book_id, username):
    if g.user:
        comment = request.form['comment']
        rating = request.form['review_rating']
        response = requests.post('https://safe-thicket-54536.herokuapp.com/review/book', json={"rating": rating, "comment": comment, "current_user":session['user'], "book_id":book_id})
        print(response.text)
        return redirect(url_for('viewbook', book_id=book_id, username=username))
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/<username>/<book_id>', methods=['GET'])
def viewbook(book_id, username):
    if g.user:
        book = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/book', json={"book_id": book_id, "username": username, "current_user": session['user']}, headers={'x-access-token': session['token']})
        bookdb = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/bookdb',
                            json={"book_id": book_id, "username": username, "current_user": session['user']},
                            headers={'x-access-token': session['token']})
        book_dict = json.loads(book.text)
        book_dictdb = json.loads(bookdb.text)
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/bookshelf/comments/book', json={"username": username, "book_id":book_id}, headers={'x-access-token': session['token']})
        comments2 = requests.get('https://safe-thicket-54536.herokuapp.com/bookshelf/review/book',
                                json={"username": username, "book_id": book_id})
        comments_dict = json.loads(comments.text)
        comments2_dict = json.loads(comments2.text)
        print(comments2_dict)
        print(book_dictdb['book'])
        print(len(comments_dict['comments']))
        borrower = requests.get('https://safe-thicket-54536.herokuapp.com/borrow_check',
                                json={"username": username, "book_id": book_id},
                                headers={'x-access-token': session['token']})
        if username == session['user']:
            if borrower.text != 'Book not borrowed':
                borrower_dict = json.loads(borrower.text)
                return render_template('own_product_borrowed.html',  notifications=get_notifications(), unread=get_unread(), borrower= borrower_dict['borrower'][0], books=book_dict['book'], booksdb=book_dictdb['book'], comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']), comments2=comments_dict['comments'])
            else:
                return render_template('own_product.html',  notifications=get_notifications(), comments2=comments2_dict['comments'], unread=get_unread(), books=book_dict['book'], booksdb=book_dictdb['book'], comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']))
        else:
            if borrower.text != 'Book not borrowed':
                borrower_dict = json.loads(borrower.text)
                return render_template('single_product_borrowed.html',  notifications=get_notifications(), unread=get_unread(), borrower=borrower_dict['borrower'][0],
                                       books=book_dict['book'], booksdb=book_dictdb['book'],
                                       comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']),
                                       comments2=comments_dict['comments'])
            else:
                return render_template('single_product.html',  notifications=get_notifications(), unread=get_unread(), books=book_dict['book'], booksdb=book_dictdb['book'], comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']), comments2=comments2_dict['comments'])
    else:
        return redirect('unauthorized')


@app.route('/bookshelf/edit/<book_id>', methods=['GET', 'POST'])
def editbook(book_id):
    if g.user:
        book = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/book', json={"username": session['user'], "book_id": book_id, "current_user": session['user']}, headers={'x-access-token': session['token']})
        book_dict = json.loads(book.text)
        if request.method == 'POST':
            quantity = request.form['quantity']
            methods = request.form.getlist('methods')
            price = request.form.get('price')
            price_rate = request.form.get('price_rate')
            if 'For Sale' not in methods:
                price=0
            if 'For Rent' not in methods:
                price_rate=0
            book = requests.post('https://safe-thicket-54536.herokuapp.com/user/edit/book', json={"username": session['user'], "quantity":quantity,
                            "methods": methods, "price": price, "price_rate": price_rate, "book_id": book_id}, headers={'x-access-token': session['token']})
            print(book.text)
            return redirect(url_for('viewbook', book_id=book_id, username=session['user']))
        else:
            return render_template('edit_ownbook.html',  notifications=get_notifications(), unread=get_unread(), username=session['user'], books=book_dict['book'])

    else:
        return redirect('unauthorized')

@app.route('/bookshelf/remove/<book_id>', methods=['POST', 'GET'])
def remove_book(book_id):
    if g.user:
        book = requests.post('https://safe-thicket-54536.herokuapp.com/user/bookshelf/remove/book', json={"book_id":book_id, "username":session['user']}, headers={'x-access-token': session['token']})
        print(book.text)
        return redirect('home')
    else:
        return redirect('unauthorized')

@app.route('/genre/<genre_name>/<page_num>', methods=['GET'])
def view_genre(genre_name, page_num):
    if g.user:
        books = requests.get('https://safe-thicket-54536.herokuapp.com/interests/view/'+genre_name, json={'page_num': page_num},headers={'x-access-token': session['token']})
        print(books.text)
        book_dict = json.loads(books.text)
        print(book_dict)
        return render_template('genre.html',  notifications=get_notifications(), unread=get_unread(), books=book_dict['book'], genre_name=genre_name,
                               paginate=jsonpickle.decode(book_dict['totalBooks'][0]['paginate']),
                               totalbooks=(int(math.ceil(float(book_dict['totalBooks'][0]['totalBooks']) / 39))) + 1)
    else:
        return redirect('unauthorized')

@app.route('/bookstore/<page_num>', methods=['GET'])
def store(page_num):
    if g.user:
        books = requests.get('https://safe-thicket-54536.herokuapp.com/bookshelf/books', json={"pagenum": page_num}, headers={'x-access-token': session['token']})
        book_dict = json.loads(books.text)
        print(book_dict)
        if not book_dict['book']:
            return render_template('no_books_shop.html', books={})
        print(int(math.ceil(float(book_dict['totalBooks'][0]['totalBooks'])/24))+1)
        return render_template('shop2.html',  notifications=get_notifications(), unread=get_unread(), books=book_dict['book'], paginate=jsonpickle.decode(book_dict['totalBooks'][0]['paginate']), totalbooks=(int(math.ceil(float(book_dict['totalBooks'][0]['totalBooks'])/20)))+1)
    else:
        return redirect('unauthorized')

@app.route('/bookstore/search/<page_num>', methods=['POST'])
def store_search(page_num):
    if g.user:
        genre = request.form.get('genre')
        time = request.form.get('time')
        search = request.form.get('search')
        print(genre)
        print(time)
        print(search)
        books = requests.get('https://safe-thicket-54536.herokuapp.com/store/search', json={"pagenum": page_num,
                             "genre": genre, "time": time, "search": search},
                             headers={'x-access-token': session['token']})
        if books.text == 'No book found!':
            return render_template('no_books_shop.html', books={})
        book_dict = json.loads(books.text)
        print(book_dict)
        print(books.text)
        return render_template('shop2.html', books=book_dict['book'],  notifications=get_notifications(), unread=get_unread(),
                               paginate=jsonpickle.decode(book_dict['totalBooks'][0]['paginate']),
                               totalbooks=(int(math.ceil(float(book_dict['totalBooks'][0]['totalBooks']) / 20))) + 1)
    else:
        return redirect('unauthorized')
@app.route('/bookshelf/wishlist/<bookshelf_id>/<book_id>', methods=['POST', 'GET'])
def add_wishlist(bookshelf_id, book_id):
    if g.user:
        if request.method == 'POST':
            url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/wishlist'
            response= requests.post(url, json={"bookshelf_id": bookshelf_id, "username":session['user'], "book_id":book_id}, headers={'x-access-token': session['token']})
            book_dict=json.loads(response.text)
            print(response.text)
            url2 = 'https://safe-thicket-54536.herokuapp.com/bookshelf/wishlist/user'
            books = requests.get(url2, json={"current_user": session['user']}, headers={'x-access-token': session['token']})
            book_dict2 = json.loads(books.text)
            if book_dict['message'] == "You can't add your own book to your wishlist":
                if not book_dict2['book']:
                    return render_template('no_books_wishlist.html',  notifications=get_notifications(), unread=get_unread(), message=book_dict['message'], none='block')
                return render_template('wishlist.html', books=book_dict2['book'],  notifications=get_notifications(), unread=get_unread(), message=book_dict['message'],display='block')
            elif book_dict['message'] == 'Book is already in wishlist':
                return render_template('wishlist.html', books=book_dict2['book'],  notifications=get_notifications(), unread=get_unread(), message=book_dict['message'], display='block')
            elif book_dict['message'] == 'Failed to add':
                if not book_dict2['book']:
                    return render_template('no_books_wishlist.html',  notifications=get_notifications(), unread=get_unread(), message=book_dict['message'],display='block')
                return render_template('wishlist.html',  notifications=get_notifications(), unread=get_unread(), books=book_dict2['book'], message=book_dict['message'],display='block')
            else:
                return render_template('wishlist.html',  notifications=get_notifications(), unread=get_unread(), books=book_dict2['book'], display='none')
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/wishlist/remove/<username>/<book_id>', methods=['GET', 'POST'])
def remove_wishlist(username, book_id):
    if g.user:
        url= 'https://safe-thicket-54536.herokuapp.com/bookshelf/remove_wishlist'
        response = requests.post(url, json={"book_id": book_id, "bookshelf_owner": username, "username": session['user']}, headers={'x-access-token': session['token']})
        book_dict = json.loads(response.text)
        return redirect('wishlist')
    else:
        return redirect('unauthorized')

@app.route('/wishlist', methods=['GET'])
def wishlist():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/wishlist/user'
        books = requests.get(url, json={"current_user": session['user']}, headers={'x-access-token': session['token']})
        book_dict = json.loads(books.text)
        print(book_dict['book'])
        if not book_dict['book']:
            return render_template('no_books_wishlist.html', display='none',notifications=get_notifications(), unread=get_unread())
        return render_template('wishlist.html',  notifications=get_notifications(), unread=get_unread(), books=book_dict['book'], display='none')
    else:
        return redirect('unauthorized')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == "POST":
            r = requests.get('https://safe-thicket-54536.herokuapp.com/search', json={'item': request.form['info'], 'current_user': session['user']})
            print(r.text)
            book_dict = json.loads(r.text)
            return render_template("result.html", books=book_dict['book'])
    else:
        return "error"


@app.route('/viewresult', methods=['GET'])
def viewresult():
    if g.user:
        book = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/', json={'current_user': session['user']})
        if book.text == "no books found":
            return render_template('single_product.html', books={})
        book_dict=json.loads(book.text)
        print(book_dict['book'])
        return render_template('single_product.html',  notifications=get_notifications(), unread=get_unread(), books=book_dict['book'])
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/borrow/<username>/<bookshelf_id>/<book_id>', methods=['GET','POST'])
def add_borrow(bookshelf_id, book_id, username):
    if g.user:
        print(bookshelf_id)
        print(book_id)
        print(username)
        book = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/book',
                            json={"book_id": book_id, "username": username, "current_user": session['user']},
                            headers={'x-access-token': session['token']})
        book_dict = json.loads(book.text)
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/bookshelf/comments/book',
                                json={"username": username, "book_id": book_id},
                                headers={'x-access-token': session['token']})
        comments_dict = json.loads(comments.text)
        if request.method == 'POST':
            date_end = request.form['date']
            end_date = datetime.strptime(date_end, "%Y-%m-%d").date()
            print(date_end)
            today = date.today()
            if end_date < today:
                return render_template('error_borrow.html',  notifications=get_notifications(), unread=get_unread(), message="Invalid Date!", books=book_dict['book'],
                                   comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']),
                                   comments2=comments_dict['comments'])
            elif end_date == today:
                return render_template('error_borrow.html',  notifications=get_notifications(), unread=get_unread(), message="Invalid Date!", books=book_dict['book'],
                                   comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']),
                                   comments2=comments_dict['comments'])
            else:
                url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/borrow_book'
                response = requests.post(url, headers={'x-access-token': session['token']},
                                         json={"bookshelf_id": bookshelf_id, "book_owner": username,
                                               "book_borrower": session['user'], "book_id": book_id,
                                                "end": date_end})
                print response.text
                response_dict = json.loads(response.text)
                # print response_dict['message']
                if response_dict['message'] == "You've already requested for this book.":
                    return render_template('error_borrow.html',  notifications=get_notifications(), unread=get_unread(), message=response_dict, books=book_dict['book'],
                                           comments=comments_dict['comments'][0:5],
                                           total=len(comments_dict['comments']),
                                           comments2=comments_dict['comments'])
                else:
                    return redirect(url_for('waitinglist'))
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/rent/<username>/<bookshelf_id>/<book_id>', methods=['GET','POST'])
def add_rent(bookshelf_id, book_id, username):
    if g.user:
        print(bookshelf_id)
        print(book_id)
        print(username)
        book = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/book',
                            json={"book_id": book_id, "username": username, "current_user": session['user']},
                            headers={'x-access-token': session['token']})
        book_dict = json.loads(book.text)
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/bookshelf/comments/book',
                                json={"username": username, "book_id": book_id},
                                headers={'x-access-token': session['token']})
        comments_dict = json.loads(comments.text)
        if request.method == 'POST':
            date_end = request.form['date']
            price_rate = request.form['price_rate']
            end_date = datetime.strptime(date_end, "%Y-%m-%d").date()
            print(date_end)
            today = date.today()
            if end_date < today:
                return render_template('error_borrow.html',  notifications=get_notifications(), unread=get_unread(), message="Invalid Date!", books=book_dict['book'],
                                   comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']),
                                   comments2=comments_dict['comments'])
            elif end_date == today:
                return render_template('error_borrow.html',  notifications=get_notifications(), unread=get_unread(), message="Invalid Date!", books=book_dict['book'],
                                   comments=comments_dict['comments'][0:5], total=len(comments_dict['comments']),
                                   comments2=comments_dict['comments'])
            else:
                url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/rent_book'
                response = requests.post(url, headers={'x-access-token': session['token']},
                                         json={"bookshelf_id": bookshelf_id, "book_owner": username,
                                               "book_borrower": session['user'], "book_id": book_id,
                                                "end": date_end, "price_rate": price_rate})
                print (response)
                response_dict = json.loads(response.text)
                if response_dict['message'] == "You've already requested for this book.":
                    return render_template('error_borrow.html', message=response.text, books=book_dict['book'],
                                           comments=comments_dict['comments'][0:5],
                                           total=len(comments_dict['comments']),
                                           comments2=comments_dict['comments'],
                                           notifications=get_notifications(), unread=get_unread()
                                           )
                else:
                    return redirect(url_for('waitinglist'))
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/purchase/<username>/<bookshelf_id>/<book_id>', methods=['GET','POST'])
def add_purchase(bookshelf_id, book_id, username):
    if g.user:
        book = requests.get('https://safe-thicket-54536.herokuapp.com/user/bookshelf/book',
                            json={"book_id": book_id, "username": username, "current_user": session['user']},
                            headers={'x-access-token': session['token']})
        book_dict = json.loads(book.text)
        print(book)
        comments = requests.get('https://safe-thicket-54536.herokuapp.com/bookshelf/comments/book',
                                json={"username": username, "book_id": book_id},
                                headers={'x-access-token': session['token']})
        comments_dict = json.loads(comments.text)
        if request.method == 'POST':
            price = request.form['price']
            url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/purchase_book'
            response = requests.post(url, headers={'x-access-token': session['token']},
                                     json={"book_buyer": session['user'], "bookshelf_id": bookshelf_id,
                                           "book_id": book_id, "price": price})
            print(response)
            response_dict = json.loads(response.text)
            if response_dict['message'] == "You've already requested for this book.":
                return render_template('error_borrow.html', message=response_dict['response'], books=book_dict['book'],
                                       comments=comments_dict['comments'][0:5],
                                       total=len(comments_dict['comments']),
                                       comments2=comments_dict['comments'],  notifications=get_notifications(), unread=get_unread())
            else:
                return redirect(url_for('waitinglist'))
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/borrow/remove/<username>/<book_id>', methods=['GET','POST'])
def remove_borrow(username, book_id):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/remove_borrow'
        print(username)
        response = requests.post(url, headers={'x-access-token': session['token']},
                                 json={"book_id": book_id, "bookshelf_owner": session['user'], "username": username})
        return redirect(url_for('requestlist'))
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/borrow/cancel/<username>/<book_id>', methods=['GET','POST'])
def cancel_borrow(username, book_id):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/remove_borrow'
        print(username)
        response = requests.post(url, headers={'x-access-token': session['token']},
                                 json={"book_id": book_id, "bookshelf_owner": username, "username": session['user']})
        return redirect(url_for('waitinglist'))
    else:
        return redirect('unauthorized')

@app.route('/user/waitinglist', methods=['GET','POST'])
def waitinglist():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/borrow/user'
        books = requests.get(url, headers={'x-access-token': session['token']}, json={"current_user": session['user']})
        if books.text == 'No books found!':
            return render_template('waitinglist.html', books={},  notifications=get_notifications(), unread=get_unread())
        else:
            book_dict = json.loads(books.text)
            return render_template('waitinglist.html', books=book_dict['books'],  notifications=get_notifications(), unread=get_unread())

    else:
        return redirect('unauthorized')

@app.route('/user/requestlist', methods=['GET','POST'])
def requestlist():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/requests/user'
        books = requests.get(url, headers={'x-access-token': session['token']}, json={"current_user": session['user']})
        if books.text == 'No books found!':
            return render_template('requestslist.html', books={},  notifications=get_notifications(), unread=get_unread())
        else:
            book_dict = json.loads(books.text)
            return render_template('requestslist.html', books=book_dict['books'],  notifications=get_notifications(), unread=get_unread())

    else:
        return redirect('unauthorized')

@app.route('/bookshelf/confirm/verification/<username>/<book_id>', methods=['GET', 'POST'])
def verification_code(book_id, username):
    if g.user:
        book = requests.get('https://safe-thicket-54536.herokuapp.com/verification-code-details',
                            json={"book_id": book_id, "book_borrower": username, "book_owner": session['user']},
                            headers={'x-access-token': session['token']})
        code = requests.get('https://safe-thicket-54536.herokuapp.com/verification-code',
                            json={"book_id": book_id, "book_borrower": username, "book_owner": session['user']},
                            headers={'x-access-token': session['token']})
        book_dict = json.loads(book.text)
        print(book_dict)
        code_dict = json.loads(code.text)
        print(code_dict)
        return render_template('own_product_code.html', books=book_dict['books'], code = code_dict['code'][0],
                               notifications=get_notifications(), unread=get_unread()
                               )
    else:
        return redirect('unauthorized')

@app.route('/bookshelf/confirm/verification/<username>/<book_id>/input', methods=['GET', 'POST'])
def verification_input(book_id, username):
    if g.user:
        book = requests.get('https://safe-thicket-54536.herokuapp.com/verification-code-details',
                            json={"book_id": book_id, "book_borrower": session['user'], "book_owner": username},
                            headers={'x-access-token': session['token']})
        book_dict = json.loads(book.text)
        return render_template('single_product_code.html', book=book_dict['books'][0],
                               notifications=get_notifications(), unread=get_unread()
                               )
    else:
        return redirect('unauthorized')


@app.route('/bookshelf/confirm/<username>/<book_id>', methods=['POST'])
def confirm(book_id, username):
    if g.user:
        code = request.form['code']
        url = 'https://safe-thicket-54536.herokuapp.com/bookshelf/confirm'
        response = requests.post(url, headers={'x-access-token': session['token']}, json={"book_owner": username, "code": code, "book_borrower": session['user'], "book_id": book_id})
        print(response.text)
        response_dict = json.loads(response.text)
        if response_dict['message'] == 'Code invalid':
            book = requests.get('https://safe-thicket-54536.herokuapp.com/verification-code-details',
                                json={"book_id": book_id, "book_borrower": session['user'], "book_owner": username},
                                headers={'x-access-token': session['token']})
            book_dict = json.loads(book.text)
            return render_template('single_product_code.html', book=book_dict['books'][0], error='Code invalid.',  notifications=get_notifications(), unread=get_unread())
        else:
            return redirect(url_for('home'))
    else:
        return redirect('unauthorized')

@app.route('/verify/book-return/<username>/<book_id>', methods=['POST'])
def verify_return(book_id, username):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/borrow_return'
        response = requests.post(url, headers={'x-access-token': session['token']}, json={"owner": session['user'], "borrower": username, "book_id": book_id})
        return redirect(url_for('home'))
    else:
        return redirect('unauthorized')

@app.route('/verify/book-return-rent/<username>/<book_id>', methods=['POST'])
def verify_return_rent(book_id, username):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/rent_return'
        response = requests.post(url, headers={'x-access-token': session['token']}, json={"owner": session['user'], "borrower": username, "book_id": book_id})
        return redirect(url_for('home'))
    else:
        return redirect('unauthorized')

@app.route('/verify/book-return-request/<username>/<book_id>', methods=['POST'])
def verify_return_request(book_id, username):
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/borrow_return_request'
        print(username)
        response = requests.post(url, headers={'x-access-token': session['token']}, json={"owner": username, "borrower": session['user'], "book_id": book_id})

        return redirect(url_for('home'))
    else:
        return redirect('unauthorized')

@app.route('/mark-read', methods=['POST'])
def mark_read():
    if g.user:
        url = 'https://safe-thicket-54536.herokuapp.com/mark-read'
        user = requests.post(url, json={"current_user": session['user']})
        return 'yehey'
    else:
        return redirect('unauthorized')

@app.route('/update', methods=['GET'])
def update():
    notifications = requests.get('https://safe-thicket-54536.herokuapp.com/notifications', json={"current_user": session['user']},
                                 headers={'x-access-token': session['token']})
    notif_dict = json.loads(notifications.text)
    #return jsonify({'result' : 'success', 'member_num' : member.random})
    return render_template('notification.html', notifications=notif_dict['notifications'], unread=notif_dict['total'])

@app.route('/follow/<username>')
def follow(username):
    if g.user:
        follow = requests.post('https://safe-thicket-54536.herokuapp.com/follow', json={"current_user": session['user'], "username":username},
                                     headers={'x-access-token': session['token']})
        return redirect(url_for('view_profile', username=username))
    else:
        return redirect('unauthorized')

@app.route('/unfollow/<username>', methods=['GET'])
def unfollow(username):
    if g.user:
        follow = requests.post('https://safe-thicket-54536.herokuapp.com/unfollow',
                               json={"current_user": session['user'], "username": username},
                               headers={'x-access-token': session['token']})
        return redirect(url_for('view_profile', username=username))
    else:
        return redirect('unauthorized')

@app.route('/notifications/all', methods=['GET'])
def notifications_all():
    if g.user:
        notifications = requests.get('https://safe-thicket-54536.herokuapp.com/notifications', json={"current_user": session['user']},
                                     headers={'x-access-token': session['token']})
        notif_dict = json.loads(notifications.text)
        return render_template('notifications_all.html', notifications=notif_dict['notifications'], unread=notif_dict['total'])
    else:
        return redirect('unauthorized')

@app.route('/activities/all', methods=['GET'])
def activity_logs():
    if g.user:
        notifications = requests.get('https://safe-thicket-54536.herokuapp.com/notifications', json={"current_user": session['user']},
                                     headers={'x-access-token': session['token']})
        notif_dict = json.loads(notifications.text)
        activities = requests.get('https://safe-thicket-54536.herokuapp.com/activity_logs', json={"current_user": session['user']},
                                     headers={'x-access-token': session['token']})
        act_dict = json.loads(activities.text)
        return render_template('activitylogs.html', notifications=notif_dict['notifications'], unread=notif_dict['total'], activities=act_dict['activities'])
    else:
        return redirect('unauthorized')

@app.route('/send_message', methods=['POST'])
def messages():
    if g.user:
        name = request.form['name']
        content = request.form['content']
        id = request.form.get('id')
        print(id)
        message1 = requests.post('https://safe-thicket-54536.herokuapp.com/message', json={"current_user": session['user'], "name": name, "content":content},
                                     headers={'x-access-token': session['token']})
        inboxes = requests.get('https://safe-thicket-54536.herokuapp.com/get_inbox', json={"current_user": session['user']},
                                                                  headers={'x-access-token': session['token']})
        inboxes_dict = json.loads(inboxes.text)
        messages = requests.get('https://safe-thicket-54536.herokuapp.com/get_messages', json={"current_user": session['user']},
                               headers={'x-access-token': session['token']})
        message_dict = json.loads(messages.text)
        return render_template('direct_messages.html', inboxes=inboxes_dict['inbox'], messages=message_dict['messages'], username=name, id=id)
    else:
        return redirect('unauthorized')

@app.route('/update_message', methods=['GET'])
def update_message():
    inboxes = requests.get('https://safe-thicket-54536.herokuapp.com/get_inbox', json={"current_user": session['user']},
                           headers={'x-access-token': session['token']})
    inboxes_dict = json.loads(inboxes.text)
    messages = requests.get('https://safe-thicket-54536.herokuapp.com/get_messages', json={"current_user": session['user']},
                            headers={'x-access-token': session['token']})
    message_dict = json.loads(messages.text)
    return render_template('direct_messages.html', inboxes=inboxes_dict['inbox'], messages=message_dict['messages'])

@app.route('/update/message', methods=['GET'])
def update_message_2():
    messages = requests.get('https://safe-thicket-54536.herokuapp.com/get_messages',
                            json={"current_user": session['user']},
                            headers={'x-access-token': session['token']})
    message_dict = json.loads(messages.text)
    return render_template('directmessage2.html', messages=message_dict['messages'])


@app.route('/direct_messages', methods=['GET'])
def message_page():
    if g.user:
        inboxes = requests.get('https://safe-thicket-54536.herokuapp.com/get_inbox', json={"current_user": session['user']},
                                                                  headers={'x-access-token': session['token']})
        inboxes_dict = json.loads(inboxes.text)
        print(inboxes_dict)
        messages = requests.get('https://safe-thicket-54536.herokuapp.com/get_messages', json={"current_user": session['user']},
                               headers={'x-access-token': session['token']})
        message_dict = json.loads(messages.text)
        print(message_dict)
        print(message_dict)
        return render_template('direct_message.html', inboxes=inboxes_dict['inbox'], messages=message_dict['messages'],
                               notifications=get_notifications(), unread=get_unread()
                               )
    else:
        return redirect('unauthorized')

@app.route('/direct_messages/<username>', methods=['GET'])
def message_person(username):
    if g.user:
        inboxes = requests.get('https://safe-thicket-54536.herokuapp.com/get_inbox', json={"current_user": session['user']},
                                                                  headers={'x-access-token': session['token']})
        inboxes_dict = json.loads(inboxes.text)
        messages = requests.get('https://safe-thicket-54536.herokuapp.com/get_messages', json={"current_user": session['user']},
                               headers={'x-access-token': session['token']})
        message_dict = json.loads(messages.text)
        return render_template('direct_message.html', inboxes=inboxes_dict['inbox'], messages=message_dict['messages'], username=username,
                               notifications=get_notifications(), unread=get_unread()
                               )
    else:
        return redirect('unauthorized')

if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True, threaded=True)