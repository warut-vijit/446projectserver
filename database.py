import hashlib
import sqlite3 as lite
import sys

def sha256(*args):
    message = "".join(args)
    m = hashlib.sha256()
    m.update(message.encode('utf-8'))
    return m.hexdigest()

# Wrapper class around a SQLite3 database
class DB:
    def __init__(self, path, secret_key):
        self.con = lite.connect(path)
        self.secret_key = secret_key

    def setup(self):
        cur = self.con.cursor()
        cur.execute("CREATE TABLE Students(ID INTEGER PRIMARY KEY, NetID TEXT UNIQUE, Name TEXT, Submissions INT DEFAULT 0)")
        cur.execute("CREATE TABLE Logs(ID INTEGER PRIMARY KEY, UserID INT, Date DATE DEFAULT CURRENT_TIMESTAMP)")

    def student_auth(self, netid, token):
        cur = self.con.cursor()
        cur.execute("SELECT ID FROM Students WHERE NetID='{}'".format(netid))
        matches = cur.fetchall()
        if len(matches) == 0:
            return None 
        uid = matches[0][0]
        reference_hash = sha256(self.secret_key, netid)
        if reference_hash == token:
            return uid
        else:
            return None

    def student_submit(self, uid):
        cur = self.con.cursor()
        cur.execute("UPDATE Students SET Submissions = Submissions + 1 WHERE ID = {}".format(uid))
        cur.execute("INSERT INTO Logs (UserID) VALUES({})".format(uid))
        self.con.commit()

    def readtbl(self, tblname):
        cur = self.con.cursor()
        cur.execute("SELECT * FROM {}".format(tblname))
        rows = cur.fetchall()
        for row in rows:
            print(row)

    def add_student(self, netid, name):
        cur = self.con.cursor()
        cur.execute("INSERT INTO Students (NetID, Name) VALUES('{}','{}')".format(netid, name))
        self.con.commit()
