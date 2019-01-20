import http.client, urllib.request, urllib.parse, urllib.error, base64, json, time, requests, cv2, numpy, pyodbc

class FaceID(object):
    """The FaceID Class"""

    conn = http.client.HTTPSConnection('northeurope.api.cognitive.microsoft.com')
    cam = cv2.VideoCapture(0)

    headers = {
        # Request headers
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': '700bad17d5d6443bad2fd69b0da27cdc',
    }

    def connectSQLDatabase(self):
        server = 'univision.database.windows.net'
        database = 'UniVision'
        username = 'adminunivision'
        password = '!univision19012019'
        driver= '{ODBC Driver 17 for SQL Server}'
        cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)
        cursor = cnxn.cursor()
        return cursor

    def createGroup(self, groupId, groupName):

        params = urllib.parse.urlencode({})

        body = {
            "name" : '{}'.format(groupName),
        }

        try:
            self.conn.request("PUT", "/face/v1.0/persongroups/" + groupId + "?%s" % params, json.dumps(body), self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print("GROUP CREATED")
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    def addPerson(self, name, targetGroup):

        params = urllib.parse.urlencode({})

        body = {
            "name": '{}'.format(name),
        }

        try:
            self.conn.request("POST", "/face/v1.0/persongroups/" + targetGroup + "/persons?%s" % params, json.dumps(body), self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print("PERSON ADDED: ", name)
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    def addFace(self, targetName, targetGroup, URL):

        # WARNING: going off the assumption that there are no duplicate names
        listOfPersons = json.loads(self.listPersonsInGroup(targetGroup))
        personId = ""
        for person in listOfPersons:
            if person["name"] == targetName:
                personId = person["personId"]
                break

        params = urllib.parse.urlencode({})

        body = {
            "url" : '{}'.format(URL)
        }

        try:
            self.conn.request("POST", "/face/v1.0/persongroups/" + targetGroup + "/persons/" + personId + "/persistedFaces?%s" % params, json.dumps(body), self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print("FACE ADDED TO", targetName)
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    # returns a json list of people in a group
    def listPersonsInGroup(self, targetGroup):

        params = urllib.parse.urlencode({})

        try:
            self.conn.request("GET", "/face/v1.0/persongroups/" + targetGroup + "/persons?%s" % params, "{body}", self.headers)
            response = self.conn.getresponse()
            data = response.read()
            return data
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    def trainGroup(self, targetGroup):

        params = urllib.parse.urlencode({})

        try:
            self.conn.request("POST", "/face/v1.0/persongroups/" + targetGroup + "/train?%s" % params, "{body}", self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print("GROUP TRAINED")
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    def takeFrame(self):
        s, img = self.cam.read()
        return cv2.imencode(".jpg",img)[1].tostring()

    # Returns faceId to be fed into identifyFace, returns -1 (integer) if no face found
    def detectFace(self, imgData):

        detectHeaders = {'Content-Type': 'application/octet-stream', 
                   'Ocp-Apim-Subscription-Key': '700bad17d5d6443bad2fd69b0da27cdc'}

        url = 'https://northeurope.api.cognitive.microsoft.com/face/v1.0/detect'

        params = urllib.parse.urlencode({
            'returnFaceId': 'true',
            'returnFaceLandmarks': 'false',
            # 'returnFaceAttributes': '{string}',
        })

        try:
            # response = requests.post(url, data=imgData, headers=headers, params=params)
            response = requests.post(url, headers=detectHeaders, data=imgData)
            print(response)
            return response.json()[0]["faceId"]
        except IndexError:
            print("NO FACE DETECTED")
            return -1
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    def identifyFace(self, faceId, targetGroup):

        params = urllib.parse.urlencode({})

        body = {
            'faceIds' : [faceId],
            'personGroupId' : targetGroup
        }

        try:
            self.conn.request("POST", "/face/v1.0/identify?%s" % params, json.dumps(body), self.headers)
            response = self.conn.getresponse()
            data = json.loads(response.read())

            if not data or not data[0]["candidates"]:
                raise IndexError()

            candidatePersonId = data[0]["candidates"][0]["personId"]
            listOfPersons = json.loads(self.listPersonsInGroup(targetGroup))
            for person in listOfPersons:
                if person["personId"] == candidatePersonId:
                    print("PERSON IDENTIFIED: " + person["name"])
                    return person["name"]

        except IndexError:
            print("***** Idk something went wrong *****")
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    def addStudentToDatabase(self, id, name, programme, cursor):
        query = "INSERT INTO students (studentID, studentName, studentProgramme) VALUES ('" + id + "', '" + name + "', '" + programme + "');"
        cursor.execute(query)

    def takeAttendance(self, timetableKey, cursor):
        try:
            while True:
                imgData = self.takeFrame()
                detectedFaceId = self.detectFace(imgData)
                if detectedFaceId != -1:
                    studentId = self.identifyFace(detectedFaceId, "testgroup")
                    if studentId:
                        checkPresentQuery = "SELECT * FROM attendance WHERE (studentID = '" + studentId + "' AND timetableKey = '" + timetableKey + "');"
                        cursor.execute(checkPresentQuery)
                        data = cursor.fetchone()
                        if not data:
                            print('Not in database, add:')
                            addQuery = "INSERT INTO attendance (studentID, timetableKey) VALUES ('" + studentId + "', '" + timetableKey + "');"
                            cursor.execute(addQuery)
                            cursor.commit()
        except KeyboardInterrupt:
            self.conn.close()

    def hackCambridgeTrainInit(self):
        self.createGroup("testgroup", "hello group")
        self.addPerson("0000000", "testgroup")
        self.addPerson("1111111", "testgroup")
        self.addPerson("2222222", "testgroup")
        self.addFace("0000000", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Matt/46854334_1320054438135017_7272253035202478080_o.jpg")
        self.addFace("0000000", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Matt/40646988_1267616973378764_4509956788853932032_n.jpg")
        self.addFace("0000000", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Matt/50425886_1359944970812630_2846946035958284288_o.jpg")
        self.addFace("0000000", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Matt/47173225_1322186427921818_2925789588129579008_o.jpg")
        self.addFace("0000000", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Matt/LRM_EXPORT_471358170522868_20181228_220101328-2.jpeg")
        self.addFace("1111111", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Neil/IMG_3102.JPG")
        self.addFace("1111111", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Neil/IMG_9449.PNG")
        self.addFace("1111111", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Neil/vsco5a9442a42aaee.JPG")
        self.addFace("1111111", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Neil/IMG_1818.JPG")
        self.addFace("2222222", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Raf/raf1.png")
        self.addFace("2222222", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Raf/raf2.jpg")
        self.addFace("2222222", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Raf/raf3.png")
        self.addFace("2222222", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Raf/raf4.png")
        self.addFace("2222222", "testgroup", "https://raw.githubusercontent.com/the-raspberry-pi-guy/UniVision/master/Faces/Raf/raf5.png")
        self.trainGroup("testgroup")
        time.sleep(2) # Give a second to train database

    def hackCambridgeDatabaseInit(self, cursor):
        self.addStudentToDatabase("0000000", "Matt Timmons-Brown", "BEng Computer Science & Electronics", cursor)
        self.addStudentToDatabase("1111111", "Neil Weidinger", "BSc Computer Science & Artificial Intelligence", cursor)
        self.addStudentToDatabase("2222222", "Rafael Anderka", "BSc Computer Science", cursor)

    def main(self):
        cursor = self.connectSQLDatabase()
#        self.hackCambridgeTrainInit() # Init only once
#        self.hackCambridgeDatabaseInit(cursor) # Also init only once
        self.listPersonsInGroup("testgroup")
        print('--------------------------')
        self.takeAttendance("1" ,cursor)

if __name__ == "__main__":
    app = FaceID()
    app.main()
