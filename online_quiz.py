#!/usr/bin/python3
# online_quiz.py: run online quiz
# usage: online_quiz.py (from cgi-bin directory)
# 20201211 erikt(at)xs4all.nl

import csrf
import csv
import datetime
from flask import Flask, Response
from flask import render_template
from flask import request
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import locale
from math import log
import os
import re
import secrets
import sys

locale.setlocale(category=locale.LC_ALL, locale="en_US.UTF-8")

BASE_URL = "/cgi-bin/online_quiz/"
DATA_DIR = "/home/cloud/software/online_quiz/"
LOG_FILE = "logfile.csv"
PARTICIPATE = "participate"
WAIT = "wait"
ENTER_ANSWERS = "enter_answers"
EXAMINE_RESULTS = "examine_results"
CHECK_ANSWERS = "check_answers"
MIN_RAND_NBR = 10000000
MAX_RAND_NBR = 99999999
START_QUIZ = "START_QUIZ"
END_QUIZ = "END_QUIZ"
PARTICIPANT = "PARTICIPANT"
ANSWER = "ANSWER"
STATUS = "STATUS"
WAITING = "waiting"
STARTED = "started"
FINISHED = "finished"
CHECKING = "checking"
CHECK = "CHECK"
DOWNLOAD = "download"
ERROR = "error"
HTML_SUFFIX = ".html"

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
csrf = CSRFProtect()
# csrf.init_app(app)


def get_random_number():
    return(MIN_RAND_NBR+secrets.randbelow(1+MAX_RAND_NBR-MIN_RAND_NBR))


def get_current_quiz_id():
    quiz_id = ""
    quiz_name = ""
    nbr_of_questions = ""
    try:
        infile = open(DATA_DIR+LOG_FILE, "r")
        csvreader = csv.reader(infile)
        for row in csvreader:
            if row[1] == START_QUIZ:
                quiz_id = row[2]
                quiz_name = row[3]
                nbr_of_questions = row[4]
            elif row[1] == END_QUIZ:
                quiz_id = ""
                quiz_name = ""
                nbr_of_questions = ""
        close(infile)
    except Exception as e:
        pass
    return(quiz_id, quiz_name, nbr_of_questions)

 
def write_log(row_in):
    row_out = [datetime.datetime.now().strftime("%Y%m%d:%H:%M:%S")]
    row_out.extend(row_in)
    outfile = open(DATA_DIR+LOG_FILE, "a")
    csvwriter = csv.writer(outfile)
    csvwriter.writerow(row_out)
    outfile.close()


def start_new_quiz(request_form):
    error_text = ""
    try:
        quiz_name = request_form["quiz_name"]
        if quiz_name == "":
            raise Exception("empty quiz name")
        nbr_of_questions = request_form["nbr_of_questions"]
        if int(nbr_of_questions) <= 0:
            raise Exception("invalid number of questions")
        participant_name = request_form["participant_name"]
        if participant_name == "":
            raise Exception("empty host name")
        quiz_id = str(get_random_number())
        participant_id = str(get_random_number())
        ip_address = request.remote_addr
        write_log([START_QUIZ, quiz_id, quiz_name, int(nbr_of_questions), participant_id, ip_address])
        write_log([PARTICIPANT, quiz_id, ip_address, participant_id, participant_name])
        write_log([STATUS, quiz_id, ip_address, participant_id, WAITING])
        return(quiz_id, participant_id, "")
    except Exception as e:
        error_text = ERROR+" (start_new_quiz): "+str(e)
    return("", "", error_text)


def read_answers(quiz_id, nbr_of_questions, ip_address, participant_id):
    answers = { str(i):"" for i in range(1,int(nbr_of_questions)+1) }
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        try:
            if row[1] == ANSWER and str(row[2]) == quiz_id and row[3] == ip_address and str(row[4]) == participant_id:
                answers[str(row[5])] = str(row[6]).strip()
        except Exception as e:
            pass
    infile.close()
    return(answers)


def read_answers_no_ip(quiz_id, nbr_of_questions, participant_id):
    answers = { str(i):"" for i in range(1,int(nbr_of_questions)+1) }
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        try:
            if row[1] == ANSWER and str(row[2]) == quiz_id and str(row[4]) == participant_id:
                answers[str(row[5])] = str(row[6]).strip()
        except Exception as e:
            pass
    infile.close()
    return(answers)


def read_checks(quiz_id, nbr_of_questions, participant_id_check):
    checks_participant_empty = { str(i):"" for i in range(1,int(nbr_of_questions)+1) }
    checks = { participant_id_check: dict(checks_participant_empty) }
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        try:
            if row[1] == CHECK and str(row[2]) == quiz_id:
                participant_id= str(row[3])
                question_id = str(row[5])
                check_status = str(row[6]).strip()
                if participant_id not in checks:
                    checks[participant_id] = dict(checks_participant_empty)
                checks[participant_id][question_id] = check_status
        except Exception as e:
            pass
    infile.close()
    check_counts = { str(i):"0/0" for i in range(1,int(nbr_of_questions)+1) }
    for participant_id in checks:
        for question_id in checks[participant_id]:
            if checks[participant_id][question_id] != "":
                correct, count = check_counts[question_id].split("/")
                count = str(int(count)+1)
                if checks[participant_id][question_id] == "correct":
                    correct = str(int(correct)+1)
                check_counts[question_id] = "/".join([correct, count])
    return(checks[participant_id_check], check_counts)


def read_results_from_logfile(quiz_id):
    results = {}
    quiz_name = ""
    quiz_date = ""
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == START_QUIZ and str(row[2]) == quiz_id:
            quiz_name = row[3]
            quiz_date = row[0][:8]
        elif row[1] == PARTICIPANT and str(row[2]) == quiz_id:
            participant_id = str(row[4])
            participant_name = str(row[5])
            key = " ".join([participant_id])
            if key in results:
                results[key]["participant_name"] = participant_name
            else:
                results[key] = { "checks": {}, "answers": {}, "status": "", "participant_name": participant_name, "participant_id": participant_id }
        elif row[1] == ANSWER and str(row[2]) == quiz_id:
            participant_id = str(row[4])
            question_nbr = str(row[5])
            answer = str(row[6]).strip()
            key = " ".join([participant_id])
            results[key]["answers"][question_nbr] = answer
        elif row[1] == CHECK and str(row[2]) == quiz_id:
            participant_id_check = str(row[3])
            question_nbr = str(row[5])
            check = str(row[6]).strip()
            key = " ".join([participant_id_check])
            results[key]["checks"][question_nbr] = check
        elif row[1] == STATUS and str(row[2]) == quiz_id:
            participant_id = str(row[4])
            key = " ".join([participant_id])
            status = row[5]
            results[key]["status"] = status
    infile.close()
    return(quiz_name, quiz_date, results)


def add_answers_given_to_results(results):
    for participant in results:
        answers_given = 0
        for question_nbr in results[participant]["answers"]:
            if results[participant]["answers"][question_nbr].strip() != "":
                answers_given += 1
        results[participant]["answers_given"] = answers_given
    return(results)


def add_solos_to_results(results):
    for participant in results:
        correct_answers = 0
        solos = []
        for question_nbr in results[participant]["checks"]:
            if results[participant]["checks"][question_nbr].strip() == "correct":
                correct_answers += 1
                global_correct_answers = [ p for p in results if question_nbr in results[p]["checks"] and results[p]["checks"][question_nbr].strip() == "correct" ]
                if len(global_correct_answers) == 1: solos.append(question_nbr)
        results[participant]["correct_answers"] = correct_answers
        results[participant]["answers_checked"] = len(results[participant]["checks"])
        results[participant]["solos"] = solos
    return(results)


def read_results(quiz_id):
    quiz_name, quiz_date, results = read_results_from_logfile(quiz_id)
    results = add_answers_given_to_results(results)
    results = add_solos_to_results(results)
    results = { p:results[p] for p in sorted(results, key=lambda p:(-results[p]["correct_answers"], results[p]["answers_checked"], -results[p]["answers_given"])) }
    return(quiz_name, quiz_date, results)


def read_status(quiz_id, ip_address, participant_id):
    status = ""
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == STATUS and str(row[2]) == quiz_id and row[3] == ip_address and str(row[4]) == participant_id:
            status = row[5]
    infile.close()
    return(status)


def make_quiz_result_text(quiz_id, participant_id):
    quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
    if len(error_text) > 0:
        raise(Exception(error_text))
    participant_name = get_participant_details(participant_id)
    checks, check_counts = read_checks(quiz_id, nbr_of_questions, participant_id)
    quiz_name, quiz_date, results = read_results(quiz_id)
    rank = [i+1 for i in range(0,len(results)) if list(results.keys())[i] == participant_id][0]
    text = f"{quiz_name} (date: {quiz_date}; {len(results)} participants; {nbr_of_questions} questions)\n\n"
    text += f"Name:  {participant_name}\n"
    text += f"Rank:  {rank}\n"
    text += f"Score: {results[participant_id]['correct_answers']}\n"
    text += f"Solos: {len(results[participant_id]['solos'])}\n\n"
    max_len_question_id = int(log(int(nbr_of_questions), 10))
    max_len_check_counts = 0
    for i in range(1,int(nbr_of_questions)+1):
        if len(check_counts[str(i)]) > max_len_check_counts:
            max_len_check_counts = len(check_counts[str(i)])
    for i in range(1,int(nbr_of_questions)+1):
        question_nbr = str(i)
        if len(results[participant_id]["solos"]) > 0:
            if question_nbr in results[participant_id]["solos"]: text += "SOLO "
            else: text += "     "
        text += f"{check_counts[question_nbr].rjust(max_len_check_counts)} "
        if not question_nbr in results[participant_id]["checks"]: check = "?"
        elif results[participant_id]["checks"][question_nbr] == "correct": check = "+"
        elif results[participant_id]["checks"][question_nbr] == "wrong": check = "-"
        else: check = "?"
        text += f"{check} {str(i).rjust(max_len_question_id)}. "
        if question_nbr in results[participant_id]["answers"]:
            text += results[participant_id]["answers"][question_nbr]
        text += "\n"
    filename = re.sub(" ","_",quiz_name.lower())
    return(text, filename)


def get_quiz_details(quiz_id):
    quiz_name = ""
    nbr_of_questions = ""
    error_text = ""
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == START_QUIZ and row[2] == quiz_id:
            quiz_name = str(row[3])
            nbr_of_questions = str(row[4])
    infile.close()
    if quiz_name == "" or nbr_of_questions == "": 
        error_text = f"unknown quiz: {quiz_id}"
    return(quiz_name, nbr_of_questions, error_text)


def get_participant_details(participant_id):
    participant_name = ""
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == PARTICIPANT and row[4] == participant_id:
            participant_name = row[5]
    return(participant_name)


def answering_started(quiz_id):
    return_value = False
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == ANSWER and row[2] == quiz_id:
            return_value = True
            break
        if row[1] == STATUS and row[2] == quiz_id and row[5] == STARTED:
            return_value = True
            break
    infile.close()
    return(return_value)


def is_host(quiz_id, participant_id, ip_address):
    infile = open(DATA_DIR+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    participant_id_host = ""
    ip_address_host = ""
    for row in csvreader:
        if row[1] == START_QUIZ and row[2] == quiz_id:
            participant_id_host = row[5]
            ip_address_host = row[6]
    infile.close()
    return(participant_id == participant_id_host and ip_address == ip_address_host)
 

@app.route("/",methods=["GET","POST"])
def init():
    return(render_template("index"+HTML_SUFFIX, start_quiz_url=BASE_URL+"start_quiz", participate_url=BASE_URL+PARTICIPATE))


@app.route("/start_quiz",methods=["GET","POST"])
def start_quiz():
    error_text = ""
    try:
        if not request.method == "POST":
            return(render_template("start_quiz"+HTML_SUFFIX, next_url=BASE_URL+"start_quiz", home_url=BASE_URL))
        else:
            quiz_id, participant_id, error_text = start_new_quiz(request.form)
            if len(error_text) > 0:
                raise(Exception(error_text))
            quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
            if len(error_text) > 0:
                raise(Exception(error_text))
            participant_name = get_participant_details(participant_id)
            quiz_name, quiz_date, results = read_results(quiz_id)
            return(render_template(WAIT+HTML_SUFFIX, next_url=BASE_URL+ENTER_ANSWERS, this_url=BASE_URL+WAIT, participate_url=request.host_url[0:len(request.host_url)-1]+BASE_URL+PARTICIPATE, quiz_id=quiz_id, quiz_name=quiz_name, participant_id=participant_id, participant_name=participant_name, results=results))
    except Exception as e:
        error_text += ERROR+" (start_quiz): "+str(e)
    return(render_template("start_quiz"+HTML_SUFFIX, next_url=BASE_URL, error_text=error_text))


@app.route("/"+PARTICIPATE,methods=["GET","POST"])
def participate():
    quiz_id = ""
    if request.method == "GET" and "quiz_id" in request.args: 
        quiz_id = request.args["quiz_id"]
    return(render_template(PARTICIPATE+HTML_SUFFIX, next_url=BASE_URL+WAIT,  home_url=BASE_URL, quiz_id=quiz_id))


@app.route("/"+WAIT,methods=["GET","POST"])
def wait():
    error_text = ""
    if request.method == "POST":
        try:
            quiz_id = request.form["quiz_id"]
            quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
            if len(error_text) > 0:
                raise(Exception(error_text))
            quiz_name, quiz_date, results = read_results(quiz_id)
            if "participant_id" in request.form:
                participant_id = request.form["participant_id"]
            else:
                participant_id = str(get_random_number())
            if participant_id not in results:
                participant_name = str(request.form["participant_name"]).strip()
                if participant_name == "":
                    raise(Exception("empty participant name"))
                write_log([PARTICIPANT, quiz_id, request.remote_addr, participant_id, participant_name])
                write_log([STATUS, quiz_id, request.remote_addr, participant_id, WAITING])
            participant_name = get_participant_details(participant_id)
            if "participant_name_new" in request.form:
                participant_name_new = request.form["participant_name_new"]
                if participant_name_new != "" and participant_name_new != participant_name:
                    write_log([PARTICIPANT, quiz_id, request.remote_addr, participant_id, participant_name_new])
                    participant_name = participant_name_new
            quiz_name, quiz_date, results = read_results(quiz_id)
            return(render_template(WAIT+HTML_SUFFIX, next_url=BASE_URL+ENTER_ANSWERS, this_url=BASE_URL+WAIT, participate_url=request.host_url[0:len(request.host_url)-1]+BASE_URL+PARTICIPATE, quiz_id=quiz_id, quiz_name=quiz_name, participant_id=participant_id, participant_name=participant_name, results=results))
        except Exception as e:
            error_text = ERROR+f" ({WAIT}): "+str(e)
    quiz_id, quiz_name, nbr_of_questions = get_current_quiz_id()
    return(render_template(ERROR+HTML_SUFFIX, next_url=BASE_URL+WAIT, quiz_name=quiz_name, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, error_text=error_text))


@app.route("/"+ENTER_ANSWERS,methods=["GET","POST"])
def enter_answers():
    error_text = ""
    if request.method == "POST":
        try:
            participant_id = request.form["participant_id"]
            quiz_id = request.form["quiz_id"]
            quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
            if len(error_text) > 0:
                raise(Exception(error_text))
            participant_name = get_participant_details(participant_id)
            ip_address = request.remote_addr
            if not answering_started(quiz_id) and not is_host(quiz_id, participant_id, ip_address):
                raise(Exception("You cannot enter answers yet. Please go back via the button 'Go Back' below"))
            answers = read_answers(quiz_id, nbr_of_questions, ip_address, participant_id)
            page_nbr = request.form["page_nbr"]
            status = read_status(quiz_id, ip_address, participant_id)
            if status == WAITING:
                write_log([STATUS, quiz_id, request.remote_addr, participant_id, STARTED])
                status = STARTED
            if status != STARTED:
                return(examine_results())
            last_changed_key = str(10*(int(page_nbr)-1))
            for key in request.form:
                key = str(key)
                answer = request.form[key]
                if re.search("^[0-9]+$",key) and key in answers and answer != answers[key]:
                    write_log([ANSWER, quiz_id, ip_address, participant_id, key, answer])
                    answers[key] = answer
                    last_changed_key = key
            return(render_template("enter_answers"+HTML_SUFFIX, next_url=BASE_URL+ENTER_ANSWERS, final_url=BASE_URL+EXAMINE_RESULTS, participant_name=participant_name, participant_id=participant_id, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, page_nbr=page_nbr, answers=answers, last_changed_key=last_changed_key, status=status))
        except Exception as e:
            error_text = ERROR+f" ({ENTER_ANSWERS}): "+str(e)
    quiz_id, quiz_name, nbr_of_questions = get_current_quiz_id()
    return(render_template(ERROR+HTML_SUFFIX, next_url=BASE_URL+WAIT, quiz_name=quiz_name, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, error_text=error_text))


@app.route("/"+EXAMINE_RESULTS,methods=["GET","POST"])
def examine_results():
    error_text = ""
    if request.method == "POST":
        try:
            participant_id = request.form["participant_id"]
            quiz_id = request.form["quiz_id"]
            quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
            if len(error_text) > 0:
                raise(Exception(error_text))
            participant_name = get_participant_details(participant_id)
            ip_address = request.remote_addr
            status = read_status(quiz_id, ip_address, participant_id)
            if status == STARTED:
                write_log([STATUS, quiz_id, request.remote_addr, participant_id, FINISHED])
                status = FINISHED
            quiz_name, quiz_date, results = read_results(quiz_id)
            return(render_template(EXAMINE_RESULTS+HTML_SUFFIX, next_url=BASE_URL+CHECK_ANSWERS, this_url=BASE_URL+EXAMINE_RESULTS, participant_name=participant_name, participant_id=participant_id, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, results=results, quiz_name=quiz_name))
        except Exception as e:
            error_text = ERROR+f" ({EXAMINE_RESULTS}): "+str(e)
    quiz_id, quiz_name, nbr_of_questions = get_current_quiz_id()
    return(render_template(ERROR+HTML_SUFFIX, next_url=BASE_URL+WAIT, quiz_name=quiz_name, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, error_text=error_text))


@app.route("/"+CHECK_ANSWERS,methods=["GET","POST"])
def check_answers():
    error_text = ""
    if request.method == "POST":
        try:
            participant_id = request.form["participant_id"]
            participant_id_check = request.form["participant_id_check"]
            participant_name_check = request.form["participant_name_check"]
            quiz_id = request.form["quiz_id"]
            quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
            if len(error_text) > 0:
                raise(Exception(error_text))
            participant_name = get_participant_details(participant_id)
            page_nbr = request.form["page_nbr"]
            ip_address = request.remote_addr
            status = read_status(quiz_id, ip_address, participant_id)
            if status == FINISHED:
                write_log([STATUS, quiz_id, request.remote_addr, participant_id, CHECKING])
                status = CHECKING
            answers = read_answers_no_ip(quiz_id, nbr_of_questions, participant_id_check)
            checks, check_counts = read_checks(quiz_id, nbr_of_questions, participant_id_check)
            for key in request.form:
                key = str(key)
                check = str(request.form[key]).strip()
                if re.search("^[0-9]+$",key) and key in checks and check != checks[key] and participant_id != participant_id_check:
                    write_log([CHECK, quiz_id, participant_id_check, participant_id, key, check])
                    checks[key] = check
            quiz_name, quiz_date, results = read_results(quiz_id)
            checks, check_counts = read_checks(quiz_id, nbr_of_questions, participant_id_check)
            return(render_template(CHECK_ANSWERS+HTML_SUFFIX, next_url=BASE_URL+CHECK_ANSWERS, final_url=BASE_URL+EXAMINE_RESULTS, download_url=BASE_URL+DOWNLOAD, participant_name=participant_name, participant_id=participant_id, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, answers=answers, participant_id_check=participant_id_check, participant_name_check=participant_name_check, page_nbr=page_nbr, checks=checks, results=results, check_counts=check_counts))
        except Exception as e:
            error_text = ERROR+f" ({CHECK_ANSWERS}): "+str(e)
    quiz_id, quiz_name, nbr_of_questions = get_current_quiz_id()
    return(render_template(ERROR+HTML_SUFFIX, next_url=BASE_URL+WAIT, quiz_name=quiz_name, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, error_text=error_text))


@app.route("/"+DOWNLOAD,methods=["GET","POST"])
def download():
    error_text = ""
    if request.method == "POST":
        try:
            participant_id_check = request.form["participant_id_check"]
            quiz_id = request.form["quiz_id"]
            text, filename = make_quiz_result_text(quiz_id, participant_id_check)
            return(Response(text, mimetype="text/plain", headers={"Content-disposition": f"attachment; filename={filename}.txt"}))
        except Exception as e:
            error_text = ERROR+f" ({DOWNLOAD}): "+str(e)
    quiz_id, quiz_name, nbr_of_questions = get_current_quiz_id()
    return(render_template(ERROR+HTML_SUFFIX, next_url=BASE_URL+WAIT, quiz_name=quiz_name, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, error_text=error_text))

