from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
import random
import time
import sys

from helpers import *

# configure application
app = Flask(__name__)
app.jinja_env.globals.update(usd=usd)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
# configure CS50 Library to use SQLite database
db = SQL("sqlite:///topscore.db")

@app.route("/")
@login_required
def index():
    
    #show all scores by the current user with the best score at the top
    username = db.execute("SELECT username FROM users WHERE user_id=:id", 
                          id = session["user_id"])
    scores = db.execute("SELECT * FROM scores WHERE user_id=:id ORDER BY correct DESC", 
                        id = session["user_id"])
    length = len(scores)
    
    date = 0
    correct = 0
    wrong = 0
    percentage = 0
    
    #iterate through the scores for each score by the user
    for i in scores:
        date = i["date"]
        correct = i["correct"]
        wrong = i["wrong"]
        #avoid dividing by zero
        if correct == 0:
            percentage = 0
        elif correct != 0:
            percentage = round(correct / (correct + wrong) * 100, 2)
        
    
    return render_template("index.html", username=username[0]["username"],
                           date = date, scores = scores, correct = correct,
                           wrong = wrong, percentage = percentage)
        
@app.route("/play", methods=["GET", "POST"])
@login_required
def play():
    
    #instructions and play button to start the timer
    if request.method == "POST":
        #if play button has been pressed
        start_time = time.time()
        db.execute("UPDATE answer SET start_time = :start_time", start_time=start_time)
        return redirect(url_for("quiz"))
            
    else:
        #set wrong as -1 then it goes to zero after play is pressed
        #use tempscore and answer databases to temporarily store the previous data when the page is updated
        db.execute("UPDATE tempscore SET correct = 0, wrong = -1")
        db.execute("UPDATE answer SET answer = 0")
        return render_template("play.html")
       
        
@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    
    #play the game
    #set the difficulty of the quiz
    random1 = random.randint(1, 50)
    random2 = random.randint(1, 100 - random1)
    random3 = random.randint(1, 12)
    random4 = random.randint(1, 12)
    random5 = random3 * random4
    signs = ['+', '*', '-', '/']
    start_times = db.execute("SELECT start_time FROM answer")
    start_time = start_times[0]["start_time"]
    randomSign = random.choice(signs)
    lastAnswers = db.execute("SELECT answer FROM answer")
    lastAnswer = lastAnswers[0]["answer"]
    myInput = request.form.get("answer", type = int)
    score = db.execute("SELECT * from tempscore")
    correct = score[0]["correct"]
    wrong = score[0]["wrong"]
    t_end = start_time + 60
    
    #continue the gameplay until one minute has passed
    while time.time() < t_end:

        if lastAnswer == None:
            lastAnswer = 0
        if lastAnswer == myInput:
            correct += 1
            db.execute("UPDATE tempscore SET correct = :correct", correct=correct)
        else:
            wrong += 1
            db.execute("UPDATE tempscore SET wrong = :wrong", wrong=wrong)
        #addition up to 100
        if randomSign == "+":
            answer = random1 + random2
            db.execute("UPDATE answer SET answer = :answer", answer=answer)
            return render_template("quiz.html", correct = correct, wrong = wrong, random1 = random1, random2 = random2, randomSign = randomSign, lastAnswer = lastAnswer, myInput = myInput)
        #multiplication up to 144
        elif randomSign == "*":
            answer = random3 * random4
            randomSign = "&times"
            db.execute("UPDATE answer SET answer = :answer", answer=answer)
            return render_template("quiz.html", correct = correct, wrong = wrong, random1 = random3, random2 = random4, randomSign = randomSign, lastAnswer = lastAnswer, myInput = myInput)
        #positive answer subtraction only
        elif randomSign == "-":
            if random1 >= random2:
                answer = random1 - random2
                db.execute("UPDATE answer SET answer = :answer", answer=answer)
                return render_template("quiz.html", correct = correct, wrong = wrong, random1 = random1, random2 = random2, randomSign = randomSign, lastAnswer = lastAnswer, myInput = myInput)
        
            else:
                answer = random2 - random1
                db.execute("UPDATE answer SET answer = :answer", answer=answer)
                return render_template("quiz.html", correct = correct, wrong = wrong, random1 = random2, random2 = random1, randomSign = randomSign, lastAnswer = lastAnswer, myInput = myInput)
        #answers to division all integers in the 12 times table or smaller
        elif randomSign == "/":
            answer = random5 / random4
            randomSign = "&divide"
            db.execute("UPDATE answer SET answer = :answer", answer=answer)
            return render_template("quiz.html", correct = correct, wrong = wrong, random1 = random5, random2 = random4, randomSign = randomSign, lastAnswer = lastAnswer, myInput = myInput)

    return redirect(url_for("end"))        
        
        
@app.route("/end", methods=["GET", "POST"])
@login_required
def end():
    
    #final score screen
    if request.method == "POST":
        # after clicking button
        
        return redirect(url_for("index"))
    
    else:
        #display final score and add the score to the database to be included on the homepage and leaderboard
        score = db.execute("SELECT * from tempscore")
        correct = score[0]["correct"]
        wrong = score[0]["wrong"]
        if correct == 0:
            percentage = 0
        elif correct != 0:
            percentage = round(correct / (correct + wrong) * 100, 2)
        date = time.strftime("%d/%m/%Y")
        usernames = db.execute("SELECT username FROM users WHERE user_id=:id", id = session["user_id"])
        username = usernames[0]["username"]
        db.execute("INSERT INTO scores (correct, wrong, percentage, date, user_id, username) VALUES (:correct, :wrong, :percentage, :date, :user_id, :username)", correct=correct, wrong=wrong, percentage=percentage, date=date, user_id=session["user_id"], username = username)
        return render_template("end.html", correct = correct, wrong = wrong)
        

@app.route("/leaderboard")
@login_required
def leaderboard():
    
    #display all top scores in order
    scores = db.execute("SELECT * FROM scores ORDER BY correct DESC")
    username = 0
    date = 0
    correct = 0
    wrong = 0
    percentage = 0
    
    
    for i in scores:
        username = i["username"]
        date = i["date"]
        correct = i["correct"]
        wrong = i["wrong"]
        if correct == 0:
            percentage = 0
        elif correct != 0:
            percentage = round(correct / (correct + wrong) * 100, 2)

    return render_template("leaderboard.html", username=username,
                           date = date, scores = scores, correct = correct,
                           wrong = wrong, percentage = percentage)
    
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"),
                                                    rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
     # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # ensure username was submitted and is unique
        if not request.form.get("username"):
            return apology("must provide username")
        
        # ensure username is unique
        # query database for username    
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username = request.form.get("username"))
        if len(rows) != 0:
            return apology("username already exists")
        
        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        
        # ensure password was confirmed
        elif not request.form.get("password") == request.form.get("confirm_password"):
            return apology("password confirmed incorrectly")
    
        # secure password
        hash = pwd_context.hash(request.form.get("password"))

        # add user to database
        db.execute("INSERT INTO users (username, hash)\
                    VALUES(:username, :hash)", 
                    username=request.form.get("username"), hash=hash)
        
        # query database for username    
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username = request.form.get("username"))
        
        # remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # redirect user to home page
        return redirect(url_for("index"))
        
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
