#!/usr/local/bin/python3
from wsgiref.handlers import CGIHandler
from online_quiz import app

CGIHandler().run(app)
