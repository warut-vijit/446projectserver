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
python3 main.py
    --image-dir <directory of reference images>
    --port 8000
    --db-path <database file>
    --secret-key <hard-to-guess>
    --setup
```

In order to test, try running
```
python3 sample_request.py
    --netid <netid>
    --token <token>
    --image-dir <directory of submission images>
    --server "localhost:8000"
```
This command should return `0.0`: the reference image and the submitted one are exactly the same.
