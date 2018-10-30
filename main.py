import argparse
from io import BytesIO
import numpy as np
from os import path
from PIL import Image
from twisted.internet import reactor, endpoints
from twisted.web import server, resource

class Server(resource.Resource):
    def render_GET(self, request):
        self.numberRequests += 1
        request.setHeader(b"content-type", b"text/plain")
        content = u"I am request #{}\n".format(self.numberRequests)
        return content.encode("ascii")

    def render_POST(self, request):
        token = request.args[b"token"][0]
        image_id = request.args[b"id"][0]
        image_bytes = request.args[b"image"][0]

        # create numpy array from student submission
        stream = BytesIO(image_bytes)
        with Image.open(stream) as submitted_pil:
            submitted_image = np.asarray(submitted_pil).transpose(-1, 0, 1)
        reference_filename = path.join(args.image_dir, image_id.decode("ascii") + ".png")

        # create numpy array from corresponding reference
        with Image.open(reference_filename) as reference_pil:
            reference_image = np.asarray(reference_pil).transpose(-1, 0, 1)

        rmse = np.sqrt(np.mean(np.square(reference_image - submitted_image)))
        
        return str(rmse).encode("ascii")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", help="Directory for reference images")
    parser.add_argument("--port", type=int, default=80, help="Port to run the server")
    args = parser.parse_args()
    endpoints.serverFromString(reactor, "tcp:8080".format(args.port)).listen(server.Site(Server()))
    print("Preparing to run reactor.")
    reactor.run()
