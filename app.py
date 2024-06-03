from flask import Flask, render_template, Response, redirect, url_for, session, request
import pyrebase
import cv2 as cv
import face_recognition
import numpy as np
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
import time 
import uuid
import base64
from io import BytesIO
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

password = "Error"
emailid = "Error"
username = "Error"
id_ans = "Error"

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : os.getenv('DATABASE_URL'),
    'storageBucket':os.getenv('STORAGE_BUCKET')
})

bucket = storage.bucket()
imgStudent = []

apiKey = os.getenv('API_KEY')
authDomain = os.getenv('AUTH_DOMAIN')
databaseURL = os.getenv('DATABASE_URL')
projectId = os.getenv('PROJECT_ID')
storageBucket = os.getenv('STORAGE_BUCKET')
messagingSenderId = os.getenv('MESSAGING_SENDER_ID')
appId = os.getenv('APP_ID')
measurementId = os.getenv('MEASUREMENT_ID')

config = {
    'apiKey': apiKey,
    'authDomain': authDomain,
    'databaseURL': databaseURL,
    'projectId': projectId,
    'storageBucket': storageBucket,
    'messagingSenderId': messagingSenderId,
    'appId': appId,
    'measurementId': measurementId,
    'databaseURL' : databaseURL
}

ref = db.reference('Info')

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()

app.secret_key = 'secret'


def get_info ():
    blobs = bucket.list_blobs()
    print (blobs)
    images = []
    imgList = []
    InfoIDs  = []

    for blob in blobs:
        imgname = blob.name.split('.')[0]
        InfoIDs.append(imgname)
        print(imgname)
        array = np.frombuffer(blob.download_as_string(), np.uint8)
        img_get = cv.imdecode(array, cv.COLOR_BGRA2BGR)
        imgList.append(img_get)
        images.append([imgname, img_get])
    return (images,imgList,InfoIDs)

def findEncodings(images):
    encodeList = []
    imgList = []
    InfoIDs  = []

    for img_name, img in images:
        imgRGB = cv.cvtColor(img, cv.COLOR_BGR2RGB)  
        encode = face_recognition.face_encodings(imgRGB)[0]
        encodeList.append(encode)

    return encodeList

print("Encoding Started ...........")
def encd (InfoIDs,images,imgList):
    global encodeListKnownwithIds,encodeListKnown
    encodeListKnown = findEncodings(images)
    encodeListKnownwithIds = [encodeListKnown, InfoIDs] 
    print(InfoIDs)
    print(imgList)
    return (encodeListKnownwithIds,encodeListKnown)

def login_by_email(encodeListKnownwithIds, encodeListKnown, InfoIDs):
    cap = cv.VideoCapture(0)

    cap.set(3, 640)
    cap.set(4, 480)
    global password, emailid, id
    timer = 0
    initialtime = time.time() 
    password = "Error"
    emailid = "Error"
    username = "Error"
    id_ans = "Error"
    id = "Error"

    while True:
        isTrue, img = cap.read()

        timer = time.time() - initialtime

        if not isTrue:  
            print("Error: Failed to capture frame")
            break

        imgS = cv.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv.cvtColor(imgS, cv.COLOR_BGR2RGB)
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

        faceCurrFrame = face_recognition.face_locations(imgS)
        encodeCurrFrame = face_recognition.face_encodings(imgS, faceCurrFrame)

        if faceCurrFrame:
            for encodeFace, faceloc in zip(encodeCurrFrame, faceCurrFrame):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                print("matches", matches)
                print("faceDis", faceDis)

                matchIndex = np.argmin(faceDis)
                print("matchind",matchIndex)

                if matches[matchIndex]:
                    id = InfoIDs[matchIndex]
                    # Get the Data
                    Information = db.reference(f'Info/{id}').get()
                    password = Information['password']
                    emailid = Information['emailid']
                    username = Information['username']
                    id_ans = id
                    print(Information)
                    

                    break
        global li
        li = [emailid, password, username, id_ans]
        print(timer)

        if password != "Error" and emailid != "Error":
            cap.release()
            cv.destroyAllWindows()
            return li

        if timer >= 30:
            cap.release()
            cv.destroyAllWindows()
            return li

    cap.release()
    cv.destroyAllWindows()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile/<string:user_id>')
def profile(user_id):
    li = session.get('li',[])
    blobs = bucket.list_blobs()
    for blob in blobs:
        if blob.name.split('.')[0] == li[3]:
            array = np.frombuffer(blob.download_as_string(), np.uint8)
            imx = cv.imdecode(array, cv.COLOR_BGRA2BGR)
            break
    
    is_success, buffer = cv.imencode(".jpg", imx)
    io_buf = BytesIO(buffer)
    base64_str = base64.b64encode(io_buf.getvalue()).decode('utf-8')

    return render_template('profile.html', email = li[0] , username = li[2], id_ans = li[3], image = base64_str)

@app.route('/register')
def register():
    if 'user' in session:
        return redirect('/profile/{}'.format(session['user']))
    
    return render_template('reg.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"

        email = request.form['email']
        password = request.form['password']
        username = request.form['username']
        file = request.files['file']

        if file.filename == '':
            return "No selected file"
        
        filename = str(uuid.uuid4()) + '_' + file.filename.rsplit('.', 1)[1]

        blob = bucket.blob(filename)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )

        key = filename.replace('.', '_')  

        user_data ={
            filename: {
                'emailid': email,
                'password': password,
                'username': username,
            }
        }
        for key,value in user_data.items():
            ref.child(key).set(value)
        
        user = auth.create_user_with_email_and_password(email, password)

        return redirect('/login')



@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user')
    return (redirect('/'))


@app.route('/login',methods=['POST','GET'])

def login():
    if 'user' in session:
        return redirect('/profile/{}'.format(session['user']))
    else:
        return login_process()

def login_process():
    emailid = "Error"
    password = "Error"
    username = "Error"
    id_ans = "Error"
    li = [emailid, password, username, id_ans]

    print(li[0])
    print(li[1])

    images,imgList,InfoIDs = get_info()
    encodeListKnownwithIds, encodeListKnown = encd(InfoIDs,images,imgList)
    li = login_by_email(encodeListKnownwithIds, encodeListKnown, InfoIDs)

    print(li[0])
    print(li[1])
    user = auth.sign_in_with_email_and_password(li[0], li[1])
    session['user'] = li[0]
    session['li'] = li
    return redirect('/profile/{}'.format(session['user']))
 

if __name__ == "__main__":
    app.run(debug=True)