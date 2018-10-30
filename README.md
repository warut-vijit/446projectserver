# CS 446 Project Validation Script

RESTful API to do validation set evaluation for chest x-ray superresolution and denoising.

## Installation and Setup Instructions

This script uses the Twisted framework for networking and numpy for computing the loss function.
Install all dependencies using
```
pip3 install -r requirements.txt
```

In order to rate limit students, this software uses user tokens issued to each student. An easy way to issue and validate tokens is to have a secret key, and then issue tokens by hashing this secret key with students' netIDs. Requests should have a token, an image ID, and the image bytes itself.


## Usage

In order to launch the server, run
```
python3 twisted_resource.py --image-dir <directory of reference images> --port 8000
```

In order to test, try running
```
curl -X POST --form "image=@<path to reference images>/00000001_000.png"
    --form "token=<token>"
    --form "id=00000001_000"
    localhost:8000
```
This command should return `0.0`: the reference image and the submitted one are exactly the same.
