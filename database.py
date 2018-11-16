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
        cur.execute("CREATE TABLE Students(ID INTEGER PRIMARY KEY, NetID TEXT UNIQUE, Name TEXT, Remaining INT DEFAULT 0, Submissions INT DEFAULT 0)")
        cur.execute("CREATE TABLE Logs(ID INTEGER PRIMARY KEY, UserID INT, Date DATE DEFAULT CURRENT_TIMESTAMP, val_error FLOAT, total_err FLOAT)")

    def student_auth(self, netid, token):
        cur = self.con.cursor()
        cur.execute("SELECT ID FROM Students WHERE NetID='{}'".format(netid))
        matches = cur.fetchone()
        if len(matches) == 0:
            return None
        uid = matches[0]
        reference_hash = sha256(self.secret_key, netid)
        if reference_hash == token:
            return uid
        else:
            return None

    def student_credits(self, uid):
        cur = self.con.cursor()
        cur.execute("SELECT Remaining FROM Students WHERE ID = {}".format(uid))
        return cur.fetchone()[0]

    def student_submit(self, uid, val_error, total_err):
        cur = self.con.cursor()
        cur.execute("UPDATE Students SET Submissions = Submissions + 1 WHERE ID = {}".format(uid))
        cur.execute("UPDATE Students SET Remaining = Remaining - 1 WHERE ID = {}".format(uid))
        cur.execute("INSERT INTO Logs (UserID, val_error, total_err) VALUES('{}', '{}', '{}')".format(uid, val_error, total_err))
        self.con.commit()
        cur.execute("SELECT * FROM Students WHERE ID = {}".format(uid))
        print(cur.fetchall())
        cur.execute("SELECT * FROM Logs WHERE UserID = {}".format(uid))
        print(cur.fetchall())

    def readtbl(self, tblname):
        cur = self.con.cursor()
        cur.execute("SELECT * FROM {}".format(tblname))
        rows = cur.fetchall()
        for row in rows:
            print(row)

    def batch_add_student(self, filename):
        cur = self.con.cursor()
        for student in open(filename):
            netid, name, _ = student.split(",")
            cur.execute("INSERT INTO Students (NetID, Name) VALUES('{}','{}')".format(netid, name))
        self.con.commit()

    def add_student(self, netid, name):
        cur = self.con.cursor()
        cur.execute("INSERT INTO Students (NetID, Name) VALUES('{}','{}')".format(netid, name))
        self.con.commit()

    def get_leaderboard(self):
        cur = self.con.cursor()
        cur.execute("SELECT DISTINCT NetID, val_error FROM Logs INNER JOIN Students ON Logs.UserID=Students.ID GROUP BY UserID ORDER BY date ASC")
        rows = cur.fetchall()
        rows = sorted(rows, key=lambda x: x[1])
        return rows

    def restore_submission_credits(self, credits):
        print("[!] Restoring all student submission credits")
        cur = self.con.cursor()
        cur.execute("UPDATE Students SET Remaining = {}".format(credits))
        self.con.commit()
