from flask import redirect, render_template, request, url_for
from flask import Flask, request
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, IntegerField, validators
import numpy, pandas as pd, sqlite3, random, string, hashlib, datetime
import plotly.express as px
import plotly
from json import dumps

app = Flask("__main__")
app.config["SECRET_KEY"] = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(64))
csrf = CSRFProtect(app=app)


class VotingForm(FlaskForm):
    vote = IntegerField("vote", validators=[validators.DataRequired()])

def get_device_fingerprint():
    user_agent = request.headers.get('User-Agent', '')
    ip = request.remote_addr
    fingerprint = hashlib.sha256(f"{user_agent}{ip}".encode()).hexdigest()
    return fingerprint



@app.route("/", methods=["GET", "POST"])
def index():
    form = VotingForm()
    conn = sqlite3.connect("voting.db")
    cur = conn.cursor()
    cur.execute("SELECT * from candidates")
    data = cur.fetchall()

    id = []
    names = []
    parties = []

    for x in data:
        id.append(x[0])
        names.append(x[1])
        parties.append(x[2])

    if form.validate_on_submit():
        fingerp = get_device_fingerprint()
        cur = conn.cursor()
        cur.execute("SELECT * FROM votes WHERE fingerprint=?", [str(fingerp)])
        if len(cur.fetchall()) == 0:
            vote = form.vote.data
            timestamp = datetime.datetime.now()
            data = (fingerp, timestamp, vote)
            cur = conn.cursor()
            cur.execute("INSERT INTO votes(fingerprint, date_of_vote, vote) VALUES(?, ?, ?)", data)
            conn.commit()
        return redirect("/results")
    return render_template("index.html", form=form, ids=id, names=names, parties=parties)



@app.get("/results")
def results():
    conn = sqlite3.connect("voting.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), candidate_name, candidate_party FROM candidates INNER JOIN votes on votes.vote = candidates.candidate_id GROUP BY candidate_name")
    data = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM votes")
    total_votes = cur.fetchone()[0]
    processed_data = []
    for x in data:
        b = list(x)
        b[0] = round((b[0]/total_votes) * 100, 2)
        processed_data.append(tuple(b))
    
    gjson = None
    df = pd.DataFrame(data=processed_data, columns=["Ilość głosów (%)", "Kandydat", "Ugrupowanie"])
    fig = px.bar(df, x="Kandydat", y="Ilość głosów (%)")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    fig.update_layout(font=dict(color="#fff"))
    gjson = dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template("result.html", json=gjson, total_votes=total_votes)
    


app.run("0.0.0.0")