import argparse
import datetime
from database import DB
from io import BytesIO
import numpy as np
from os import path
from PIL import Image
from twisted.internet import reactor, endpoints, task
from twisted.web import server, resource

def restore_credit_failure(failure):
    """
    Error handler for async restore credit loop
    """
    print(failure.getBriefTraceback())
    reactor.stop()

def score_image(image_id, image_bytes):
    """
    Accepts binary data associated with the image
    Returns either
        - float : rmse error if successful
        - str : error message if unsuccessful
    """
    # create numpy array from student submission
    try:
        stream = BytesIO(image_bytes)
        with Image.open(stream) as submitted_pil:
            submitted_image = np.asarray(submitted_pil)
            if len(submitted_image.shape) == 3: # if image is rgb or rgba
                submitted_image = np.asarray(submitted_pil).transpose(-1, 0, 1)[0]
    except Exception:
        return "Image data is not in a valid .PNG format."

    # create numpy array from corresponding reference
    reference_filename = path.join(args.image_dir, image_id)
    if not path.isfile(reference_filename):
        return "No image with ID {} found in validation set.".format(
            image_id
        )
    with Image.open(reference_filename) as reference_pil:
        reference_image = np.asarray(reference_pil)
        if len(reference_image.shape) == 3: # if image is rgb or rgba
            reference_image = np.asarray(reference_pil).transpose(-1, 0, 1)[0]

    if submitted_image.shape != reference_image.shape:
        return "User-submitted image of shape {} does match {}.".format(
            submitted_image.shape,
            reference_image.shape,
        )

    rmse = np.sqrt(np.mean(np.square(reference_image - submitted_image)))
    return rmse

class Server(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        request.setHeader(b"content-type", b"text/plain")
        leaderboard = database.get_leaderboard()
        c = filter(lambda s: s[1]<9000, leaderboard)
        d = filter(lambda s: (9000<=s[1] and s[1]<20000), leaderboard)
        f = filter(lambda s: s[1]>=20000, leaderboard)
        cstr = ["{}: {}".format(*entry) for entry in c]
        dstr = ["{}: {}".format(*entry) for entry in d]
        fstr = ["{}: {}".format(*entry) for entry in f]
        retstr = ""
        retstr += "\n[-------------- A/B/C --------------]\n"
        retstr += "\n".join(cstr)
        retstr += "\n[---------------- D ----------------]\n"
        retstr += "\n".join(dstr)
        retstr += "\n[---------------- F ----------------]\n"
        retstr += "\n".join(fstr)
        return retstr.encode("ascii")

    def render_POST(self, request):
        try:
            netid = request.args[b"netid"][0].decode("ascii")
            token = request.args[b"token"][0].decode("ascii")
        except KeyError:
            return b"Request must have fields 'netid', 'token'"

        # authenticate user
        uid = database.student_auth(netid, token)
        if uid is None:
            return b"NetID-token combination not recognized"

        # check user rate limit
        if database.student_credits(uid) <= 0:
            return b"Please wait a while before sending more requests."

        # score each image
        val_rmse = 0.0
        total_rmse = 0.0
        submitted_images = 0
        for (k, v) in request.args.items():
            k = k.decode()
            if k[:4] == "test":
                submitted_images += 1
                score_image_ret = score_image(k, v[0])
                # print(score_image_ret)
                # just pass error through if raised
                if type(score_image_ret) == str:
                    return ("Image {}: ".format(k) + score_image_ret).encode("ascii")
                if int(k[5:10]) <= 2000: # first 2000 are validation set
                    val_rmse += score_image_ret
                total_rmse += score_image_ret

        if submitted_images < 3999:
            return "incomplete submission (check that you submitted all  images and that all images were named using the convention  test_xxxxx.png"

        # record submission
        database.student_submit(uid, val_rmse, total_rmse)

        return str(val_rmse).encode("ascii")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", help="Directory for reference images")
    parser.add_argument("--port", type=int, default=80, help="Port to run the server")
    parser.add_argument("--secret-key", help="Secret key used for authentication")
    parser.add_argument("--db-path", help="File directory path to database file")
    parser.add_argument("--setup", action="store_true", help="Build DB tables")
    parser.add_argument("--db-source", help="Path to netid-name pairs (only if --setup)")
    parser.add_argument("--credit-max", type=int, default=1000, help="Maximum credits for each student")
    parser.add_argument("--credit-interval", type=int, default=24, help="Interval for credit restore (hrs)")
    args = parser.parse_args()

    # initialize database connection, setup if necessary
    database = DB(args.db_path, args.secret_key)
    if args.setup:
        database.setup()
        database.batch_add_student(args.db_source)

    # initialize web endpoint
    endpoints.serverFromString(reactor, "tcp:{}".format(args.port)).listen(server.Site(Server()))

    # initialize periodic restore submission credits
    now = datetime.datetime.utcnow()
    next_midnight = (now.replace(hour=6, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1))
    delta = (next_midnight - now).total_seconds()
    loop = task.LoopingCall(database.restore_submission_credits, credits=args.credit_max)
    def credit_restore_loop_start():
        loopDeferred = loop.start(args.credit_interval * 3600)
        loopDeferred.addErrback(restore_credit_failure)
    reactor.callLater(delta, credit_restore_loop_start)

    print("[!] Starting twisted reactor")
    reactor.run()
