#!/usr/bin/python3
import sys
sys.stderr = open("/WWW/t/tjongkim/tmp/errorlog", "a")

import os
BASE_DIR = "/usr/local/WWW/A/t/tjongkim/"
os.environ["PYTHONPATH"] = "{0}.local/lib/python3.5/site-packages:{0}software/online_quiz".format(BASE_DIR)

from wsgiref.handlers import CGIHandler
from online_quiz import app

CGIHandler().run(app)

sys.exit(0)
