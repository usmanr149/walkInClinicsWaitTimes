from flask import Flask, render_template, jsonify, request
import sqlite3
from flask import g

import datetime

import configparser

import geocoder

import requests
import urllib

config = configparser.ConfigParser()
config.read("./.properties")

api = config['SECTION_HEADER']['api']
port2 = "162.106.216.28"

app = Flask(__name__)

DATABASE = '/Users/usmriz/PycharmProjects/waitTimesDB/waitTimes.db'

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
            <div class="radiotext" style="text-align: center;" > (last updated: {1})</div>""".format(row[1],
                                                                                                     datetime.datetime.fromtimestamp(
                                                                                                         row[2]/1000).strftime(
                                                                                                         '%H:%M %p'))
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

def getStatus(curr_time, open_, close, breakOpen=None, breakClose=None, type_='HTML'):

    def fixClose(x):
        if x > 12:
            x-=12
            if x == 12:
                return str(12) + ":" + str("%02d" % ((x%1)*60,)) + " AM"
            else:
                return str("%02d" % (int(x % 12),)) + ":" + str("%02d" % ((x%1)*60,)) + " PM"
        else:
            return str("%02d" % (int(x % 12),)) + ":" + str("%02d" % ((x%1)*60,)) + " PM"

    # check if the clinic is currently during it's open time
    try:
        if curr_time >= open_ and curr_time <= close:
            #if it is then check for break time
            if  breakOpen != None and breakClose != None:
                if curr_time >= breakOpen and curr_time <= breakClose:
                    if type_ == 'HTML':
                        return "On Break"
                    else:
                        return False
                else:
                    if type_ == 'HTML':
                        return "Open till {0}".format(fixClose(close))
                    else:
                        return True

            else:
                if type_ == 'HTML':
                    return "Open till {0}".format(fixClose(close))
                else:
                    return True
        else:
            if type_ == 'HTML':
                return "Clinic Closed"
            else:
                return False
    except TypeError:
        if type_ == 'HTML':
            return "Clinic Closed"
        else:
            return False

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
    result = [(row[0], getStatus(curr_time, row[1], row[2], row[3], row[4])) for row in rows]
    cur.close()
    #result = dict(zip([row[0] for row in rows], [getOtherWalkInClinicsStatus(curr_time, row[1], row[2], row[3], row[4]) for row in rows]))
    return render_template("otherWalkInClinics.html", rows=result, api=api)

@app.route('/getHospitalWaitTimesHTML')
def getHospitalWaitTimesHTML():
    cur = get_db().cursor()
    cur.execute("""select hospitalWaitTimes.ID, 
                    hospitalWaitTimes.waitTime, 
                    hospitalNames.Name,
                    hospitalAddresses.lat, 
                    hospitalAddresses.lon 
                    FROM 
                    hospitalWaitTimes 
                    LEFT JOIN hospitalNames ON 
                    hospitalWaitTimes.ID = hospitalNames.ID 
                    LEFT JOIN hospitalAddresses ON 
                    hospitalAddresses.ID = hospitalWaitTimes.ID;""")
    rows = cur.fetchall()
    html = ["""
    <div id="table">
      <table style='padding-left: 5px;'>
        <tbody>
        <tr>
        <td style="text-align: center;"  width=60%;><span style="color: #ff0000;">
        <strong>Hospital</strong></span></td>
        <td style="text-align: center;">
        <span style="color: #ff0000;" width=40%> <strong><br>Wait Time</br><br id="0">Last Updated: {0}</strong>
        </span></td></tr>""".format(rows[-1][1])]
    radioTextRow = """
        <tr>
                        <td>
                        <div class="radio"><label> <input
                        name="optradio" type="radio" value="{3}"/>{2}</label></div>
                        </td>
                        <td>
                            <div class="radiotext" style="text-align: center;">
                            <label for="regular" id="{0}">{1}</label></div>
                        </td>
                        </tr>
            """.format
    html = html + [radioTextRow(row[0], row[1], row[2], str(row[3])+','+str(row[4])) for row in rows[:-1]]
    html.append("""
        </tbody>
      </table>
   </div>
    """)

    return jsonify(table="".join(html).replace("\n",""))

@app.route('/')
def main():
    cur = get_db().cursor()
    cur.execute("""select hospitalWaitTimes.ID, 
                    hospitalWaitTimes.waitTime, 
                    hospitalNames.Name,
                    hospitalAddresses.lat, 
                    hospitalAddresses.lon 
                    FROM 
                    hospitalWaitTimes 
                    LEFT JOIN hospitalNames ON 
                    hospitalWaitTimes.ID = hospitalNames.ID 
                    LEFT JOIN hospitalAddresses ON 
                    hospitalAddresses.ID = hospitalWaitTimes.ID;""")
    rows = cur.fetchall()
    html = ["""
        <div id="table">
          <table style='padding-left: 5px;'>
            <tbody>
            <tr>
            <td style="text-align: center;"  width=60%;><span style="color: #ff0000;">
            <strong>Hospital</strong></span></td>
            <td style="text-align: center;">
            <span style="color: #ff0000;" width=40%> <strong><br>Wait Time</br><br id="0">Last Updated: {0}</strong>
            </span></td></tr>""".format(rows[-1][1])]

    radioTextRow = """
                <tr>
                                <td>
                                <div class="radio"><label> <input
                                name="optradio" type="radio" value="{3}"/>{2}</label></div>
                                </td>
                                <td>
                                    <div class="radiotext" style="text-align: center;">
                                    <label for="regular" id="{0}">{1}</label></div>
                                </td>
                                </tr>
            """.format
    html = html + [radioTextRow(row[0], row[1], row[2], str(row[3])+','+str(row[4])) for row in rows[:-1]]
    html.append("""
            </tbody>
          </table>
       </div>
        """)

    return render_template("view2.html", table="".join(html).replace("\n",""), api=api)

@app.route('/medicentreWaitTimesHTML')
def getMedicentreWaitTimesHTML():

    def updateTime(x):
        if isinstance(x, int):
            return datetime.datetime.fromtimestamp(x).strftime('%H:%M %p')
        else:
            return x

    cur = get_db().cursor()
    cur.execute("""select medicentreWaitTimes.ID, 
        medicentreWaitTimes.waitTime, 
        medicentreWaitTimes.lastUpdated,
        medicentreNames.Name,
        medicentreAddresses.lat, 
        medicentreAddresses.lon 
        FROM 
        medicentreWaitTimes
        LEFT JOIN medicentreNames ON 
        medicentreWaitTimes.ID = medicentreNames.ID 
        LEFT JOIN medicentreAddresses ON 
        medicentreAddresses.ID = medicentreWaitTimes.ID;""")
    rows = cur.fetchall();
    cur.close()
    html = ["""
         <div>
      <table style='padding-left: 5px;'>
        <tbody>
        <tr>
        <td style="text-align: center;"  width=60%;><span style="color: #ff0000;">
        <strong>Medicentre</strong></span></td>
        <td style="text-align: center;">
        <span style="color: #ff0000;" width=40%> <strong>Wait Time</strong>
        </span></td></tr>
    """]
    radioTextRow = """
             <tr>
                            <td>
                            <div class="radio"><label> <input
                            name="optradio" type="radio" value="{4}"/>{3}</label></div>
                            </td>
                            <td id="{0}">
                                <div class="radiotext" style="text-align: center;">
                                <label for="regular">{1}</label></div>
                                <div class="radiotext" style="text-align: center;">(last updated: {2})</div>
                            </td>
                            </tr>
        """.format
    html = html + [radioTextRow(row[0], row[1], updateTime(row[2]),
                                row[3], str(row[4])+","+str(row[5])) for row in rows]
    """html = html + [radioTextRow(row[0], row[1], row[2],
                                row[3], str(row[4]) + "," + str(row[5])) for row in rows]"""

    html.append("""
        </tbody>
      </table>
   </div>
    """)

    return jsonify(table="".join(html).replace("\n", ""))

@app.route("/otherWalkInClinicsHTML")
def otherWalkInClinicsHTML():
    # get current day of week
    dow = datetime.datetime.today().weekday()
    curr_time = datetime.datetime.now().hour + datetime.datetime.now().minute / 60
    cur = get_db().cursor()
    cur.execute("""select otherWalkInClinicsNames.Name, 
            otherWalkInClinicsTimes.Open, 
            otherWalkInClinicsTimes.Close, 
            otherWalkInClinicsTimes.breakOpen, 
            otherWalkInClinicsTimes.breakClose,
			otherWalkInClinicsAddresses.lat,
			otherWalkInClinicsAddresses.lon
            from otherWalkInClinicsTimes left join 
            otherWalkInClinicsNames 
            ON
            otherWalkInClinicsNames.ID = otherWalkInClinicsTimes.ID
			left join otherWalkInClinicsAddresses 
			ON otherWalkInClinicsNames.ID=
			otherWalkInClinicsAddresses.ID
			where otherWalkInClinicsTimes.DayofWeek={0};""".format(dow))
    rows = cur.fetchall()
    result = [(row[0], getStatus(curr_time, row[1], row[2], row[3], row[4]), str(row[5]) + "," + str(row[6])) for row in
              rows]
    cur.execute("""
        SELECT waitTime FROM medicentreWaitTimes WHERE waitTime<>"";
            """)
    rows = cur.fetchall()

    if len(rows) > 0:
        avgWaitTime = sum([int(r[0].split(":")[0]) + int(r[0].split(":")[1])/60 for r in rows]) / len(rows)
    else:
        avgWaitTime = 24
    cur.close()

    if isinstance(avgWaitTime, float):
        html = ["""
            <div>
          <table style='padding-left: 5px;'>
            <tbody>
            <tr>
            <td style="text-align: center;"  width=60%;><span style="color: #ff0000;">
            <strong>Other Walk-In Clinics</strong></span></td>
            <td style="text-align: center;">
            <span style="color: #ff0000;" width=40%> <strong>Wait Time: {0}</strong>
            </span></td></tr>
        """.format(str("%02d" % (int(avgWaitTime//1),)) + ":" + str("%02d" % (int((avgWaitTime%1)*60),)))]
    else:
        html = ["""
                    <div>
                  <table style='padding-left: 5px;'>
                    <tbody>
                    <tr>
                    <td style="text-align: center;"  width=60%;><span style="color: #ff0000;">
                    <strong>Other Walk-In Clinics</strong></span></td>
                    <td style="text-align: center;">
                    <span style="color: #ff0000;" width=40%> <strong>Wait Time: {0}</strong>
                    </span></td></tr>
                """.format("Indeterminate")]
    radioTextRow = """
        <tr>
                            <td>
                            <div class="radio"><label> <input
                            name="optradio" type="radio" value="{2}"/>{0}</label></div>
                            </td>
                            <td>
                                <div class="radiotext" style="text-align: center;">
                                <label for="regular">{1}</label></div>
                            </td>
                            </tr>
    """.format
    html = html + [radioTextRow(row[0], row[1], row[2]) for row in result]
    html.append("""
        </tbody>
      </table>
   </div>
    """)
    return jsonify(table="".join(html).replace("\n", ""))

@app.route('/recommendation')
@app.route('/recommend')
def recommend():
    origin = request.args.get('origin', 0, type=str)
    mode = request.args.get('mode',0,type=str)
    bestTime, where, type = getRecommendation(origin, mode)
    #if bestTime != None:
    #    bestTime = datetime.datetime.fromtimestamp(bestTime / 1000).strftime('%Y-%m-%d %H:%M %p')
    return jsonify(where=where, type=type, bestTime=bestTime)


def getRecommendation(address, mode='TRANSIT'):
    def getTimeInMilliseconds(x):
        if isinstance(x, str):
            return float(x.split(":")[0])*3600*1000 + float(x.split(":")[1])*60*1000
        else:
            return 0

    if mode == 'TRANSIT':
        mode = "TRANSIT,WALK"

    correctAddress = False

    try:
        if isinstance(float(address.split(",")[0]), float) and isinstance(float(address.split(",")[1]), float):
            correctAddress = True
            add = [float(address.split(",")[0]), float(address.split(",")[1])]
    except:
        g = geocoder.google(address)
        if isinstance(g.latlng, list) and len(g.latlng) > 1:
            correctAddress = True
            add = [g.latlng[0], g.latlng[1]]

    bestTime = None
    recomendation = None
    typeofrecommendation = None

    # make sure the google address yields a result
    if correctAddress:
        dow = datetime.datetime.today().weekday()
        time_ = datetime.datetime.now()
        # read in the current medicentre wait times
        dow = datetime.datetime.today().weekday()
        cur = get_db().cursor()
        cur.execute("""
            select medicentreNames.Name,
                medicentreWaitTimes.waitTime,
                medicentreTimes.Open,
                medicentreTimes.Close,
                medicentreTimes.breakOpen,
                medicentreTimes.breakClose,
				medicentreAddresses.lat,
				medicentreAddresses.lon
                FROM medicentreWaitTimes left join 
                medicentreTimes ON
                medicentreTimes.ID = medicentreWaitTimes.ID
					left join
					medicentreAddresses ON 
					medicentreAddresses.ID = medicentreWaitTimes.ID
					left join
					medicentreNames ON 
					medicentreAddresses.ID = medicentreNames.ID
                where 	medicentreTimes.DayofWeek={0} and 
				medicentreWaitTimes.waitTime<>"";
                """.format(dow))
        rows_M = cur.fetchall()
        cur.execute("""
            select  otherWalkInClinicsNames.Name,
				otherWalkInClinicsTimes.Open,
				otherWalkInClinicsTimes.Close,
				otherWalkInClinicsTimes.breakOpen,
				otherWalkInClinicsTimes.breakClose,
				otherWalkInClinicsTimes.DayofWeek,
                otherWalkInClinicsAddresses.lat, 
                otherWalkInClinicsAddresses.lon 
                FROM otherWalkInClinicsTimes LEFT JOIN 
                otherWalkInClinicsAddresses ON 
                otherWalkInClinicsTimes.ID = otherWalkInClinicsAddresses.ID
				LEFT JOIN 
				otherWalkInClinicsNames ON 
				otherWalkInClinicsNames.ID = otherWalkInClinicsAddresses.ID
                where otherWalkInClinicsTimes.DayofWeek={0};
            """.format(dow))
        rows_O = cur.fetchall()
        cur.execute("""
                    SELECT waitTime FROM medicentreWaitTimes WHERE waitTime<>"";
                    """)
        rows = cur.fetchall()
        if len(rows) > 0:
            avgMWaitTime = sum([int(r[0].split(":")[0]) + int(r[0].split(":")[1]) / 60 for r in rows]) / len(rows)
        else:
            avgMWaitTime = 15/60
        cur.execute("""
            SELECT hospitalNames.Name,
				hospitalWaitTimes.waitTime,
                hospitalAddresses.lat, 
                hospitalAddresses.lon FROM hospitalWaitTimes 
                left join hospitalAddresses ON 
                hospitalWaitTimes.ID=hospitalAddresses.ID 
				left join hospitalNames ON 
				hospitalNames.ID = hospitalAddresses.ID;
            """.format(dow))
        rows_H = cur.fetchall()
        cur.close()

        for row in rows_M:
            url = """http://{5}:8080/otp/routers/default/plan?fromPlace={0}&toPlace={1}&time={2}&date={3}&mode={4}&maxWalkDistance=804.672&arriveBy=false&wheelchair=false&locale=en""".format(
                urllib.parse.quote(str(add[0])+","+str(add[1])),
                urllib.parse.quote(str(row[6])+","+str(row[7])),
                urllib.parse.quote(time_.strftime("%I:%M%p")),
                urllib.parse.quote(time_.strftime("%m-%d-%Y")),
                mode, port2)
            try:
                response = requests.get(url).json()
                # the response is the unix timestamp in milliseconds
                arrTime = float(response["plan"]["itineraries"][0]["endTime"]) + getTimeInMilliseconds(row[1])
                if getStatus(datetime.datetime.fromtimestamp(arrTime/1000).hour +
                                     datetime.datetime.fromtimestamp(arrTime / 1000).minute/60, open_=row[2],
                             close=row[3],type_='bool') and \
                        (bestTime == None or arrTime < bestTime):
                    bestTime = arrTime
                    recomendation = row[0]
                    typeofrecommendation = 'medicentres'
            except KeyError:
                pass
        for row in rows_O:
            url = """http://{5}:8080/otp/routers/default/plan?fromPlace={0}&toPlace={1}&time={2}&date={3}&mode={4}&maxWalkDistance=804.672&arriveBy=false&wheelchair=false&locale=en""".format(
                urllib.parse.quote(str(add[0]) + "," + str(add[1])),
                urllib.parse.quote(str(row[6]) + "," + str(row[7])),
                urllib.parse.quote(time_.strftime("%I:%M%p")),
                urllib.parse.quote(time_.strftime("%m-%d-%Y")),
                mode, port2)
            try:
                response = requests.get(url).json()
                # the response is the unix timestamp in milliseconds
                arrTime = float(response["plan"]["itineraries"][0]["endTime"]) + \
                          avgMWaitTime*3600*1000
                if getStatus(datetime.datetime.fromtimestamp(arrTime/1000), row[1], row[2], row[3], row[4], type_='bool') and \
                        (bestTime == None or arrTime < bestTime):
                    bestTime = arrTime
                    recomendation = row[0]
                    typeofrecommendation = 'other'
            except KeyError:
                pass
        for row in rows_H:
            url = """http://{5}:8080/otp/routers/default/plan?fromPlace={0}&toPlace={1}&time={2}&date={3}&mode={4}&maxWalkDistance=804.672&arriveBy=false&wheelchair=false&locale=en""".format(
                urllib.parse.quote(str(add[0]) + "," + str(add[1])),
                urllib.parse.quote(str(row[2]) + "," + str(row[3])),
                urllib.parse.quote(time_.strftime("%I:%M%p")),
                urllib.parse.quote(time_.strftime("%m-%d-%Y")),
                mode, port2)
            try:
                response = requests.get(url).json()
                # the response is the unix timestamp in milliseconds
                arrTime = float(response["plan"]["itineraries"][0]["endTime"]) + \
                          getTimeInMilliseconds(row[1])
                if bestTime == None or arrTime < bestTime:
                    bestTime = arrTime
                    recomendation = row[0]
                    typeofrecommendation = 'hospitals'
            except KeyError:
                pass
        return datetime.datetime.fromtimestamp(bestTime/1000).strftime("%Y-%m-%d %I:%M %p"), recomendation, typeofrecommendation
    return bestTime, recomendation, typeofrecommendation

if __name__ == "__main__":
    app.run(debug=True, port=7010, threaded=True)
    #print(getStatus(12, 9, 16, 11, 13, "bool"))
    #getRecommendation("53.544373699999994,-113.48768109999999")