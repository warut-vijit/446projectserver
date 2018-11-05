import argparse
from database import DB
from io import BytesIO
import numpy as np
from os import path
from PIL import Image
from twisted.internet import reactor, endpoints, task
from twisted.web import server, resource

class Server(resource.Resource):
    isLeaf = True
    numberRequests = 0

    def render_GET(self, request):
        self.numberRequests += 1
        request.setHeader(b"content-type", b"text/plain")
        content = u"I am request #{}\n".format(self.numberRequests)
        return content.encode("ascii")

    def render_POST(self, request):
        try:
            netid = request.args[b"netid"][0].decode("ascii")
            token = request.args[b"token"][0].decode("ascii")
            image_id = request.args[b"id"][0].decode("ascii")
            image_bytes = request.args[b"image"][0]
        except KeyError:
            return b"Request must have fields 'netid', 'token', 'id', 'image'"

        # authenticate user
        uid = database.student_auth(netid, token)
        if uid is None:
            return b"NetID-token combination not recognized"

        # check user rate limit
        if database.student_credits(uid) <= 0:
            return b"Please wait a while before sending more requests."

        # create numpy array from student submission
        try:
            stream = BytesIO(image_bytes)
            with Image.open(stream) as submitted_pil:
                submitted_image = np.asarray(submitted_pil).transpose(-1, 0, 1)
        except Exception:
            return "Image data is not in a valid .PNG format."

        # create numpy array from corresponding reference
        reference_filename = path.join(args.image_dir, image_id + ".png")
        if not path.isfile(reference_filename):
            return "No image with ID {} found in validation set.".format(
                image_id.decode("ascii"),
            ).encode("ascii")
        with Image.open(reference_filename) as reference_pil:
            reference_image = np.asarray(reference_pil).transpose(-1, 0, 1)

        if submitted_image.shape != reference_image.shape:
            return "User-submitted image of shape {} does match {}.".format(
                submitted_image.shape,
                reference_image.shape,
            ).encode("ascii")

        rmse = np.sqrt(np.mean(np.square(reference_image - submitted_image)))

        # record submission
        database.student_submit(uid)

        return str(rmse).encode("ascii")

def restore_credit_failure(failure):
    print(failure.getBriefTraceback())
    reactor.stop()

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
    loop = task.LoopingCall(database.restore_submission_credits, credits=args.credit_max)
    loopDeferred = loop.start(args.credit_interval * 3600)
    loopDeferred.addErrback(restore_credit_failure)

    print("[!] Starting twisted reactor")
    reactor.run()
