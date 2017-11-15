from flask import Flask, render_template, jsonify
import sqlite3
from flask import g

import datetime

import configparser

config = configparser.ConfigParser()
config.read("./.properties")

api = config['SECTION_HEADER']['api']

app = Flask(__name__)

DATABASE = '/Users/usmanr/PycharmProjects/waitTimesDB/waitTimes.db'

# the application must either have an active application context (which is always true if there is a request in flight)
# or create an application context itself
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def dict_from_row(row):
    return dict(zip(row.keys(), row))

@app.route('/updateMedicentreWaitTimes')
def updateMedicentreWaitTimes():
    cur = get_db().cursor()
    cur.execute("""select * FROM medicentreWaitTimes;""")
    rows = cur.fetchall();
    cur.close()
    html = {}
    for row in rows:
        html[row[0]] = """<div
            class="radiotext" style="text-align: center;">
            <label id="Belmont_time" for="regular">{0}</label></div>
            <div class="radiotext" style="text-align: center;" > (last updated: {1})</div>""".format(row[1], row[2])
    return jsonify(result=html)

@app.route('/updateHospitalWaitTimes')
def updateHospitalWaitTimes():
    cur = get_db().cursor()
    cur.execute("""select * FROM hospitalWaitTimes;""")
    rows = cur.fetchall();
    cur.close()
    dict_ = dict(zip([row[0] for row in rows], [row[1] for row in rows]))
    return jsonify(result=dict_)

@app.route('/hospitalWaitTimes')
def hospitalWaitTimes():
    cur = get_db().cursor()
    cur.execute("""select hospitalWaitTimes.ID, waitTime, Name FROM 
	hospitalWaitTimes, hospitalNames where 
	hospitalNames.ID = hospitalWaitTimes.ID;""")
    rows =cur.fetchall()
    return render_template("hospitalWaitTimes.html", lastUpdated = "Last Updated: {0}".format(rows[-1][1]), rows=rows[:-1], api=api)

def getOtherWalkInClinicsStatus(curr_time, open, close, breakOpen=None, breakClose=None):
    # check if the clinic is currently during it's open time
    try:
        if curr_time >= open and curr_time <= close:
            #if it is then check for break time
            if  breakOpen != "" and breakClose != "":
                if curr_time >= breakOpen and curr_time <= breakClose:
                    return "On Break"
            else:
                return "Open till {0}".format(close)
        else:
            return "Clinic Closed"
    except TypeError:
        return "Clinic Closed"

@app.route('/otherWalkInClinicsTimes')
def otherWalkInClinicsTimes():
    #get current day of week
    dow = datetime.datetime.today().weekday()
    curr_time = datetime.datetime.now().hour + datetime.datetime.now().minute/60
    cur = get_db().cursor()
    cur.execute("""select otherWalkInClinicsNames.Name, 
        otherWalkInClinicsTimes.Open, 
        otherWalkInClinicsTimes.Close, 
        otherWalkInClinicsTimes.breakOpen, 
        otherWalkInClinicsTimes.breakClose
        from otherWalkInClinicsTimes inner join 
        otherWalkInClinicsNames 
        ON
        otherWalkInClinicsNames.ID = otherWalkInClinicsTimes.ID
        WHERE otherWalkInClinicsTimes.DayofWeek={0};""".format(dow))
    rows = cur.fetchall()
    cur.close()
    result = [(row[0], getOtherWalkInClinicsStatus(curr_time, row[1], row[2], row[3], row[4])) for row in rows]
    #result = dict(zip([row[0] for row in rows], [getOtherWalkInClinicsStatus(curr_time, row[1], row[2], row[3], row[4]) for row in rows]))
    return render_template("otherWalkInClinics.html", rows=result, api=api)

@app.route('/')
@app.route('/home')
def home():
    return render_template("home.html")

@app.route('/medicentreWaitTimes')
def medicentreWaitTimes():
    cur = get_db().cursor()
    cur.execute("""select medicentreWaitTimes.ID, waitTime, lastUpdated, Name FROM 
	medicentreWaitTimes, medicentreNames where 
	medicentreWaitTimes.ID = medicentreNames.ID;""")
    rows = cur.fetchall();
    cur.close()
    return render_template("medicentreWaitTimes.html", rows=rows, api=api)

if __name__ == "__main__":
    app.run(debug=True, port=7010, threaded=True)