#!/usr/bin/python3
# online_quiz.py: run online quiz
# usage: online_quiz.py (from cgi-bin directory)
# 20201211 erikt(at)xs4all.nl

import csv
import datetime
import time
import sys
import os

if "PYTHONPATH" in os.environ:
    for path in os.environ["PYTHONPATH"].split(":"):
        sys.path.append(path)

from flask import Flask, Response
from flask import render_template
from flask import request
import locale
from math import log
from random import shuffle
import re
from random import randint


locale.setlocale(category=locale.LC_ALL, locale="en_US.UTF-8")


BASE_URL = "/cgi-bin/online_quiz/"
DATA_DIR = "/usr/local/WWW/A/t/tjongkim/private/online_quiz/quizzes/"
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
APPROVED = "approved"
CHECK = "CHECK"
CHECKER = "CHECKER"
DOWNLOAD = "download"
DOWNLOAD_ALL = "download_all"
ERROR = "error"
HTML_SUFFIX = ".html"
BACK = "back"
OPEN_CHECKING = "open_checking"
OPEN_ANSWERING = "open_answering"
DATE_FORMAT = "%Y%m%d:%H:%M:%S"


app = Flask(__name__)
dot_env_file = open(DATA_DIR+".env", "r")
for line in dot_env_file:
    if re.search("^SECRET_KEY", line):
        app.config['SECRET_KEY'] = line.split('"')[1]
dot_env_file.close()


def get_random_number():
    return(MIN_RAND_NBR+randint(0, 1+MAX_RAND_NBR-MIN_RAND_NBR))


def write_log(row_in, quiz_id, participant_id=None):
    row_out = [datetime.datetime.now().strftime("%Y%m%d:%H:%M:%S")]
    row_out.extend(row_in)
    if participant_id == None:
        outfile = open(DATA_DIR+quiz_id+"/"+LOG_FILE, "a")
    else:
        outfile = open(DATA_DIR+quiz_id+"/"+participant_id, "a")
    csvwriter = csv.writer(outfile)
    csvwriter.writerow(row_out)
    outfile.close()


def start_new_quiz(request_form):
    error_text = ""
    try:
        quiz_name = request_form["quiz_name"]
        if quiz_name == "":
            raise ValueError("empty quiz name")
        nbr_of_questions = request_form["nbr_of_questions"]
        if int(nbr_of_questions) <= 0:
            raise ValueError("invalid number of questions")
        participant_name = request_form["participant_name"]
        if participant_name == "":
            raise ValueError("empty host name")
        quiz_id = str(get_random_number())
        participant_id = str(get_random_number())
        ip_address = request.remote_addr
        os.mkdir(DATA_DIR+quiz_id)
        write_log([START_QUIZ, quiz_id, quiz_name, int(nbr_of_questions), participant_id, ip_address], quiz_id)
        write_log([PARTICIPANT, quiz_id, ip_address, participant_id, participant_name], quiz_id, participant_id=participant_id)
        write_log([STATUS, quiz_id, ip_address, participant_id, WAITING], quiz_id, participant_id=participant_id)
        return(quiz_id, participant_id, "")
    except Exception as e:
        error_text += ERROR+" (start_new_quiz): "+str(e)
    return("", "", error_text)


def read_answers(quiz_id, nbr_of_questions, ip_address, participant_id):
    answers = { str(i):"" for i in range(1,int(nbr_of_questions)+1) }
    infile = open(DATA_DIR+quiz_id+"/"+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        try:
            if row[1] == ANSWER and str(row[2]) == quiz_id and row[3] == ip_address and str(row[4]) == participant_id:
                answers[str(row[5])] = str(row[6]).strip()
        except Exception:
            pass
    infile.close()
    return(answers)


def read_answers_no_ip(quiz_id, nbr_of_questions, participant_id):
    answers = { str(i):"" for i in range(1,int(nbr_of_questions)+1) }
    infile = open(DATA_DIR+quiz_id+"/"+participant_id, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        try:
            if row[1] == ANSWER and str(row[2]) == quiz_id and str(row[4]) == participant_id:
                answers[str(row[5])] = str(row[6]).strip()
        except Exception:
            pass
    infile.close()
    return(answers)


def make_check_counts(checks, nbr_of_questions):
    check_counts = { str(i):"0/0" for i in range(1,int(nbr_of_questions)+1) }
    for participant_id in checks:
        for question_id in checks[participant_id]:
            if checks[participant_id][question_id] != "":
                correct, count = check_counts[question_id].split("/")
                count = str(int(count)+1)
                if checks[participant_id][question_id] == "correct":
                    correct = str(int(correct)+1)
                check_counts[question_id] = "/".join([correct, count])
    return(check_counts)


def read_checks(quiz_id, nbr_of_questions, participant_id_check):
    checks_participant_empty = { str(i):"" for i in range(1,int(nbr_of_questions)+1) }
    checks = { participant_id_check: dict(checks_participant_empty) }
    for file_name in os.listdir(DATA_DIR+quiz_id):
        if re.search("^[0-9]+$", file_name):
            infile = open(DATA_DIR+quiz_id+"/"+file_name, "r")
            csvreader = csv.reader(infile)
            for row in csvreader:
                try:
                    if row[1] == CHECK and str(row[2]) == quiz_id:
                        participant_id = str(row[3])
                        question_id = str(row[5])
                        check_status = str(row[6]).strip()
                        if participant_id not in checks:
                            checks[participant_id] = dict(checks_participant_empty)
                        checks[participant_id][question_id] = check_status
                except Exception:
                    pass
            infile.close()
    check_counts = make_check_counts(checks, nbr_of_questions)
    return(checks[participant_id_check], check_counts)


def read_results_from_logfile(quiz_id):
    results = {}
    quiz_name = ""
    quiz_date = ""
    infile = open(DATA_DIR+quiz_id+"/"+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    rows = []
    for row in csvreader:
        if str(row[2]) == quiz_id:
           rows.append(row)
    infile.close()
    for row in rows:
        if row[1] == START_QUIZ:
            quiz_name = row[3]
            quiz_date = row[0][:8]
    checkers = {}
    for file_name in sorted(os.listdir(DATA_DIR+quiz_id), reverse=True):
        if re.search("^[0-9]+$", file_name):
            infile = open(DATA_DIR+quiz_id+"/"+file_name, "r")
            csvreader = csv.reader(infile)
            rows = []
            for row in csvreader:
                if str(row[2]) == quiz_id:
                   rows.append(row)
            infile.close()
            for row in rows:
                if row[1] == PARTICIPANT:
                    participant_id = str(row[4])
                    participant_name = str(row[5])
                    key = " ".join([participant_id])
                    if key in results:
                        results[key]["participant_name"] = participant_name
                    else:
                        results[key] = { "checks": {}, "answers": {}, "status": "", "participant_name": participant_name, "participant_id": participant_id, "time": { STARTED: "", FINISHED: "" }  }
                elif row[1] == ANSWER:
                    participant_id = str(row[4])
                    question_nbr = str(row[5])
                    answer = str(row[6]).strip()
                    key = " ".join([participant_id])
                    results[key]["answers"][question_nbr] = answer
                elif row[1] == CHECK:
                    participant_id_check = str(row[3])
                    question_nbr = str(row[5])
                    check = str(row[6]).strip()
                    key = " ".join([participant_id_check])
                    results[key]["checks"][question_nbr] = check
                elif row[1] == STATUS:
                    participant_id = str(row[4])
                    key = " ".join([participant_id])
                    status = row[5]
                    results[key]["status"] = status
                    if status == STARTED:
                        results[key]["time"][STARTED] = row[0]
                    if status == FINISHED:
                        results[key]["time"][FINISHED] = row[0]
                        time_diff = datetime.datetime.strptime(results[key]["time"][FINISHED], DATE_FORMAT) - datetime.datetime.strptime(results[key]["time"][STARTED], DATE_FORMAT)
                        hours, minutes, seconds = str(time_diff).split(":")
                        minutes = int(minutes) + 60*int(hours)
                        results[key]["status"] += " ({0}:{1})".format(minutes, seconds)
                elif row[1] == CHECKER:
                    checker = str(row[3])
                    checkee = str(row[4])
                    checkers[checker] = checkee
    for checker in checkers:
        checkee = checkers[checker]
        results[checkee]["checker"] = results[checker]["participant_name"]
    return(quiz_name, quiz_date, results)


def sort_results_list(results_list):
    return([ result for result in sorted(results_list, key=lambda result:(-result["correct_answers"],
                                                                          result["answers_checked"],
                                                                          -len(result["solos"]),
                                                                          -result["answers_given"],
                                                                          result["participant_name"])) ])

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


def read_results(quiz_id, error_text=""):
    error_text += "R"
    quiz_name, quiz_date, results = read_results_from_logfile(quiz_id)
    error_text += "R"
    results = add_answers_given_to_results(results)
    results = add_solos_to_results(results)
    results_list = []
    error_text += "R"
    for key in results:
        results[key]["participant_id"] = key
        results_list.append(results[key])
    error_text += "R"
    results_dict = { result["participant_id"]:result for result in sorted(results_list, key=lambda result:(-result["correct_answers"], 
                                                                                                           result["answers_checked"], 
                                                                                                           -len(result["solos"]), 
                                                                                                           -result["answers_given"], 
                                                                                                           result["participant_name"])) }
    return(quiz_name, quiz_date, results_dict, error_text)


def read_status(quiz_id, ip_address, participant_id):
    status = ""
    infile = open(DATA_DIR+quiz_id+"/"+participant_id, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == STATUS and str(row[2]) == quiz_id and row[3] == ip_address and str(row[4]) == participant_id:
            status = row[5]
    infile.close()
    return(status)


def find_max_len_check_counts(check_counts):
    max_len_check_counts = 0
    for question_id in check_counts:
        if len(check_counts[question_id]) > max_len_check_counts:
            max_len_check_counts = len(check_counts[question_id])
    return(max_len_check_counts)


def make_quiz_result_text(quiz_id, participant_id):
    quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
    if len(error_text) > 0:
        raise ValueError(error_text)
    participant_name = get_participant_details(quiz_id, participant_id)
    checks, check_counts = read_checks(quiz_id, nbr_of_questions, participant_id)
    quiz_name, quiz_date, results, error_text = read_results(quiz_id)
    rank = [i+1 for i in range(0,len(results)) if list(results.keys())[i] == participant_id][0]
    text = "{0} (date: {1}; {2} participants; {3} questions)\n\n".format(quiz_name, quiz_date, len(results), nbr_of_questions)
    text += "Name:  {0}\n".format(participant_name)
    text += "Rank:  {0}\n".format(rank)
    text += "Score: {0}\n".format(results[participant_id]['correct_answers'])
    text += "Solos: {0}\n\n".format(len(results[participant_id]['solos']))
    max_len_question_id = 1+int(log(int(nbr_of_questions), 10))
    max_len_check_counts = find_max_len_check_counts(check_counts)
    for i in range(1,int(nbr_of_questions)+1):
        question_nbr = str(i)
        if len(results[participant_id]["solos"]) > 0:
            if question_nbr in results[participant_id]["solos"]: text += "SOLO "
            else: text += "     "
        text += "{0} ".format(check_counts[question_nbr].rjust(max_len_check_counts))
        if not question_nbr in results[participant_id]["checks"]: check = "?"
        elif results[participant_id]["checks"][question_nbr] == "correct": check = "+"
        elif results[participant_id]["checks"][question_nbr] == "wrong": check = "-"
        else: check = "?"
        text += "{0} {1}. ".format(check, str(i).rjust(max_len_question_id))
        if question_nbr in results[participant_id]["answers"]:
            text += results[participant_id]["answers"][question_nbr]
        text += "\n"
    filename = re.sub(" ","_",quiz_name.lower())
    return(text, filename)


def make_quiz_result_text_all(quiz_id):
    quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
    if len(error_text) > 0:
        raise ValueError(error_text)
    quiz_name, quiz_date, results, error_text = read_results(quiz_id)
    results_table = [["Name"]]
    for participant_id in results:
        results_table[-1].append(re.sub(",", "_", results[participant_id]["participant_name"]))
    results_table.append(["Scores"])
    for participant_id in results:
        results_table[-1].append(str(results[participant_id]["correct_answers"]))
    for i in range(1,int(nbr_of_questions)+1):
        question_nbr = str(i)
        results_table.append([question_nbr])
        for participant_id in results:
            if not question_nbr in results[participant_id]["checks"]:
                results_table[-1].append("")
            elif results[participant_id]["checks"][question_nbr] == "correct":
                results_table[-1].append("1")
            elif results[participant_id]["checks"][question_nbr] == "wrong":
                results_table[-1].append("0")
    text = ""
    for row in results_table:
        text += ",".join(row) + "\n"
    filename = re.sub(" ","_",quiz_name.lower()) + "_all"
    return(text, filename)


def get_quiz_details(quiz_id):
    quiz_name = ""
    nbr_of_questions = ""
    error_text = ""
    infile = open(DATA_DIR+quiz_id+"/"+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == START_QUIZ and row[2] == quiz_id:
            quiz_name = str(row[3])
            nbr_of_questions = str(row[4])
    infile.close()
    if quiz_name == "" or nbr_of_questions == "":
        error_text = "unknown quiz: {0}".format(quiz_id)
    return(quiz_name, nbr_of_questions, error_text)


def get_participant_details(quiz_id, participant_id):
    participant_name = ""
    infile = open(DATA_DIR+quiz_id+"/"+participant_id, "r")
    csvreader = csv.reader(infile)
    for row in csvreader:
        if row[1] == PARTICIPANT and row[4] == participant_id:
            participant_name = row[5]
    return(participant_name)


def answering_started(quiz_id):
    return_value = False
    infile = open(DATA_DIR+quiz_id+"/"+LOG_FILE, "r")
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


def is_quiz_host(quiz_id, participant_id, ip_address):
    infile = open(DATA_DIR+quiz_id+"/"+LOG_FILE, "r")
    csvreader = csv.reader(infile)
    participant_id_host = ""
    ip_address_host = ""
    for row in csvreader:
        if row[1] == START_QUIZ and row[2] == quiz_id:
            participant_id_host = row[5]
            ip_address_host = row[6]
    infile.close()
    return(participant_id == participant_id_host and ip_address == ip_address_host)


def get_checkee_id(quiz_id, participant_id):
    infile = open(DATA_DIR+quiz_id+"/"+participant_id, "r")
    csvreader = csv.reader(infile)
    checkee_id = ""
    for row in csvreader:
        if row[1] == CHECKER and row[2] == quiz_id and row[3] == participant_id:
            checkee_id = str(row[4])
    infile.close()
    return(checkee_id)


@app.route("/", methods=["GET"])
def init():
    return(render_template("index"+HTML_SUFFIX, start_quiz_url=BASE_URL+"start_quiz", participate_url=BASE_URL+PARTICIPATE))


@app.route("/start_quiz", methods=["GET","POST"])
def start_quiz():
    error_text = ""
    try:
        if not request.method == "POST":
            return(render_template("start_quiz"+HTML_SUFFIX, next_url=BASE_URL+"start_quiz", home_url=BASE_URL))
        else:
            quiz_id, participant_id, error_text = start_new_quiz(request.form)
            if len(error_text) > 0:
                raise ValueError(error_text)
            quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
            if len(error_text) > 0:
                raise ValueError(error_text)
            error_text += "5"
            participant_name = get_participant_details(quiz_id, participant_id)
            error_text += "6"
            quiz_name, quiz_date, results, error_text = read_results(quiz_id)
            error_text += "7"
            participate_url = request.host_url[0:len(request.host_url)-1]+BASE_URL+PARTICIPATE
            open_answering_url = request.host_url[0:len(request.host_url)-1]+BASE_URL+OPEN_ANSWERING
            open_checking_url = request.host_url[0:len(request.host_url)-1]+BASE_URL+OPEN_CHECKING
            error_text += "8 "+str(results)
            return(render_template(WAIT+HTML_SUFFIX, next_url=BASE_URL+ENTER_ANSWERS, this_url=BASE_URL+WAIT, participate_url=participate_url, open_answering_url=open_answering_url, open_checking_url=open_checking_url, quiz_id=quiz_id, quiz_name=quiz_name, participant_id=participant_id, participant_name=participant_name, results=sort_results_list(results.values())))
    except Exception as e:
        error_text += ERROR+" (start_quiz): "+str(e)
    return(render_template("start_quiz"+HTML_SUFFIX, next_url=BASE_URL, error_text=error_text))


@app.route("/"+PARTICIPATE, methods=["GET","POST"])
def participate():
    quiz_id = ""
    if request.method == "GET" and "quiz_id" in request.args:
        quiz_id = request.args["quiz_id"]
    return(render_template(PARTICIPATE+HTML_SUFFIX, next_url=BASE_URL+WAIT,  home_url=BASE_URL, quiz_id=quiz_id))


@app.route("/"+WAIT, methods=["POST"])
def wait():
    error_text = ""
    try:
        quiz_id = request.form["quiz_id"]
        quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
        if len(error_text) > 0:
            raise ValueError(error_text)
        error_text += "B"
        quiz_name, quiz_date, results, error_text = read_results(quiz_id)
        error_text += "C"+str(results)
        ip_address = request.remote_addr
        error_text += "D"
        if "participant_id" in request.form:
            error_text += "2"
            participant_id = request.form["participant_id"]
            error_text += "2"
        else:
            error_text += "3"
            participant_id = str(get_random_number())
            error_text += "3"
        error_text += "1"
        if participant_id not in results:
            error_text += "4"
            participant_name = str(request.form["participant_name"]).strip()
            error_text += "4"
            if participant_name == "":
                raise ValueError("empty participant name")
            error_text += "4"
            write_log([PARTICIPANT, quiz_id, ip_address, participant_id, participant_name], quiz_id, participant_id=participant_id)
            error_text += "4"
            write_log([STATUS, quiz_id, ip_address, participant_id, WAITING], quiz_id, participant_id=participant_id)
            error_text += "4"
        error_text += "1"
        participant_name = get_participant_details(quiz_id, participant_id)
        error_text += "1"
        if "participant_name_new" in request.form:
            participant_name_new = request.form["participant_name_new"]
            if participant_name_new != "" and participant_name_new != participant_name:
                write_log([PARTICIPANT, quiz_id, request.remote_addr, participant_id, participant_name_new], quiz_id, participant_id=participant_id)
                participant_name = participant_name_new
        error_text += "1"
        quiz_name, quiz_date, results, error_text = read_results(quiz_id)
        error_text += "1"
        participate_url = ""
        open_answering_url = ""
        open_checking_url = ""
        error_text += "1"
        if is_quiz_host(quiz_id, participant_id, ip_address):
            participate_url = request.host_url[0:len(request.host_url)-1]+BASE_URL+PARTICIPATE
            open_answering_url = request.host_url[0:len(request.host_url)-1]+BASE_URL+OPEN_ANSWERING
            open_checking_url = request.host_url[0:len(request.host_url)-1]+BASE_URL+OPEN_CHECKING
        error_text += "1"
        return(render_template(WAIT+HTML_SUFFIX, next_url=BASE_URL+ENTER_ANSWERS, this_url=BASE_URL+WAIT, participate_url=participate_url, open_answering_url=open_answering_url, open_checking_url=open_checking_url, quiz_id=quiz_id, quiz_name=quiz_name, participant_id=participant_id, participant_name=participant_name, results=sort_results_list(results.values())))
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(WAIT)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


@app.route("/"+ENTER_ANSWERS, methods=["POST"])
def enter_answers():
    error_text = ""
    try:
        quiz_id = request.form["quiz_id"]
        page_nbr = request.form["page_nbr"]
        participant_id = request.form["participant_id"]
        quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
        if len(error_text) > 0:
            raise ValueError(error_text)
        participant_name = get_participant_details(quiz_id, participant_id)
        ip_address = request.remote_addr
        if not answering_started(quiz_id) and not is_quiz_host(quiz_id, participant_id, ip_address):
            return(wait())
        answers = read_answers(quiz_id, nbr_of_questions, ip_address, participant_id)
        status = read_status(quiz_id, ip_address, participant_id)
        if status == WAITING:
            write_log([STATUS, quiz_id, request.remote_addr, participant_id, STARTED], quiz_id)
            write_log([STATUS, quiz_id, request.remote_addr, participant_id, STARTED], quiz_id, participant_id=participant_id)
            status = STARTED
        if status != STARTED:
            return(examine_results())
        last_changed_key = str(10*(int(page_nbr)-1))
        answers_changed = False
        for key in request.form:
            key = str(key)
            answer = request.form[key]
            if re.search("^[0-9]+$",key) and key in answers and answer != answers[key]:
                write_log([ANSWER, quiz_id, ip_address, participant_id, key, answer], quiz_id, participant_id=participant_id)
                answers[key] = answer
                last_changed_key = key
                answers_changed = True
        if answers_changed:
            return(back())
        return(render_template("enter_answers"+HTML_SUFFIX, next_url=BASE_URL+ENTER_ANSWERS, final_url=BASE_URL+EXAMINE_RESULTS, participant_name=participant_name, participant_id=participant_id, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, page_nbr=page_nbr, answers=answers, last_changed_key=last_changed_key, status=status))
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(ENTER_ANSWERS)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


@app.route("/"+EXAMINE_RESULTS, methods=["POST"])
def examine_results():
    error_text = ""
    try:
        quiz_id = request.form["quiz_id"]
        participant_id = request.form["participant_id"]
        quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
        if len(error_text) > 0:
            raise ValueError(error_text)
        error_text += "A"
        participant_name = get_participant_details(quiz_id, participant_id)
        error_text += "A"
        ip_address = request.remote_addr
        error_text += "A"
        status = read_status(quiz_id, ip_address, participant_id)
        error_text += "A"
        if status == STARTED:
            write_log([STATUS, quiz_id, request.remote_addr, participant_id, FINISHED], quiz_id, participant_id=participant_id)
            status = FINISHED
        error_text += "A"
        if "approve" in request.form:
            write_log([STATUS, quiz_id, request.remote_addr, participant_id, APPROVED], quiz_id, participant_id=participant_id)
            status = APPROVED
        error_text += "A:"+quiz_id
        quiz_name, quiz_date, results, error_text = read_results(quiz_id, error_text=error_text)
        error_text += "A"
        open_checking_url = ""
        error_text += "A"
        if is_quiz_host(quiz_id, participant_id, ip_address):
            open_checking_url = BASE_URL+OPEN_CHECKING
        error_text += "A"
        checkee_id = ""
        if get_checkee_id(quiz_id, participant_id) != "":
            checkee_id = "other"
        error_text += "A"
        return(render_template(EXAMINE_RESULTS+HTML_SUFFIX, next_url=BASE_URL+CHECK_ANSWERS, this_url=BASE_URL+EXAMINE_RESULTS, download_url=BASE_URL+DOWNLOAD, download_all_url=BASE_URL+DOWNLOAD_ALL, open_checking_url=open_checking_url, participant_name=participant_name, participant_id=participant_id, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, results=sort_results_list(results.values()), quiz_name=quiz_name, checkee_id=checkee_id))
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(EXAMINE_RESULTS)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


def anonymize_id(quiz_id, participant_id, participant_id_check):
    ip_address = request.remote_addr
    if participant_id_check == participant_id:
        return(participant_id)
    if is_quiz_host(quiz_id, participant_id, ip_address):
        return(participant_id_check)
    return("")


@app.route("/"+CHECK_ANSWERS, methods=["POST"])
def check_answers():
    error_text = ""
    try:
        error_text = "C"
        quiz_id = request.form["quiz_id"]
        error_text = "C"
        page_nbr = request.form["page_nbr"]
        error_text = "C"
        participant_id = request.form["participant_id"]
        error_text = "C"
        ip_address = request.remote_addr
        error_text = "C"
        if request.form["participant_id_check"] == participant_id:
            participant_id_check = participant_id
        elif request.form["participant_id_check"] == "":
            participant_id_check = get_checkee_id(quiz_id, participant_id)
        elif is_quiz_host(quiz_id, participant_id, ip_address): 
            participant_id_check = request.form["participant_id_check"]
        else:
            participant_id_check = participant_id
        error_text = "C"
        quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
        #if len(error_text) > 0:
        #    raise ValueError(error_text)
        error_text = "C"
        participant_name = get_participant_details(quiz_id, participant_id)
        participant_name_check = get_participant_details(quiz_id, participant_id_check)
        status = read_status(quiz_id, ip_address, participant_id)
        error_text = "C"
        if status == FINISHED and participant_id_check != participant_id:
            write_log([STATUS, quiz_id, request.remote_addr, participant_id, CHECKING], quiz_id, participant_id=participant_id)
            status = CHECKING
        error_text = "C"
        answers = read_answers_no_ip(quiz_id, nbr_of_questions, participant_id_check)
        checks, check_counts = read_checks(quiz_id, nbr_of_questions, participant_id_check)
        error_text = "C"
        if participant_id != participant_id_check or is_quiz_host(quiz_id, participant_id, ip_address):
            for key in request.form:
                key = str(key)
                check = str(request.form[key]).strip()
                if re.search("^[0-9]+$",key) and key in checks and check != checks[key]:
                    write_log([CHECK, quiz_id, participant_id_check, participant_id, key, check], quiz_id, participant_id=participant_id_check)
                    checks[key] = check
        error_text = "C"
        quiz_name, quiz_date, results, error_text = read_results(quiz_id)
        checks, check_counts = read_checks(quiz_id, nbr_of_questions, participant_id_check)
        error_text = "C"
        return(render_template(CHECK_ANSWERS+HTML_SUFFIX, next_url=BASE_URL+CHECK_ANSWERS, final_url=BASE_URL+EXAMINE_RESULTS, download_url=BASE_URL+DOWNLOAD, participant_name=participant_name, participant_id=participant_id, quiz_id=quiz_id, nbr_of_questions=nbr_of_questions, answers=answers, participant_id_check=anonymize_id(quiz_id, participant_id, participant_id_check), participant_name_check=participant_name_check, page_nbr=page_nbr, checks=checks, results=sort_results_list(results.values()), check_counts=check_counts))
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(CHECK_ANSWERS)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


@app.route("/"+DOWNLOAD, methods=["POST"])
def download():
    error_text = ""
    try:
        quiz_id = request.form["quiz_id"]
        participant_id = request.form["participant_id"]
        text, filename = make_quiz_result_text(quiz_id, participant_id)
        return(Response(text, mimetype="text/plain", headers={"Content-disposition": "attachment; filename={0}.txt".format(filename)}))
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(DOWNLOAD)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


@app.route("/"+DOWNLOAD_ALL, methods=["POST"])
def download_all():
    error_text = ""
    try:
        quiz_id = request.form["quiz_id"]
        participant_id = request.form["participant_id"]
        text, filename = make_quiz_result_text_all(quiz_id)
        return(Response(text, mimetype="text/plain", headers={"Content-disposition": "attachment; filename={0}.csv".format(filename)}))
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(DOWNLOAD_ALL)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


@app.route("/"+"show_answers", methods=["POST"])
def show_answers():
    error_text = ""
    try:
        quiz_id = request.form["quiz_id"]
        participant_id = request.form["participant_id"]
        ip_address = request.remote_addr
        results = {}
        if is_quiz_host(quiz_id, participant_id, ip_address):
            quiz_name, quiz_date, results, error_text = read_results_from_logfile(quiz_id)
        quiz_name, nbr_of_questions, error_text = get_quiz_details(quiz_id)
        inverted_results = []
        for i in range(1, int(nbr_of_questions)+1):
            answers = []
            for key in results:
                if str(i) in results[key]["answers"] and results[key]["answers"][str(i)] != "":
                    answers.append({"participant_name":results[key]["participant_name"], "answer":results[key]["answers"][str(i)], "checker":results[key]["checker"], "check":results[key]["checks"][str(i)]})
            answers = [answer for answer in sorted(answers, key=lambda answer: answer["answer"].lower())]
            inverted_results.append(answers)
        return(render_template("show_answers"+HTML_SUFFIX, next_url=BASE_URL+EXAMINE_RESULTS, participant_id=participant_id, quiz_id=quiz_id, results=sort_results_list(results.values()), nbr_of_questions=nbr_of_questions, inverted_results=inverted_results))
    except Exception as e:
        error_text += ERROR+" (show_answers): "+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


@app.route("/"+OPEN_CHECKING, methods=["POST"])
def open_checking():
    error_text = ""
    try:
        error_text += "x"
        quiz_id = request.form["quiz_id"]
        error_text += "y"
        participant_id = request.form["participant_id"]
        error_text += "z"
        ip_address = request.remote_addr
        error_text += "a"
        if is_quiz_host(quiz_id, participant_id, ip_address):
            quiz_name, quiz_date, results, error_text = read_results(quiz_id, error_text)
            error_text +=str(results) 
            finished_ids = []
            for key in  results:
                if re.search("^finished", results[key]["status"]):
                    finished_ids.append(key)
            shuffle(finished_ids)
            for i in range(0, len(finished_ids)):
                checker = finished_ids[i]
                checkee = finished_ids[i-1]
                write_log([CHECKER, quiz_id, checker, checkee], quiz_id, participant_id=checker)
        return(examine_results())
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(OPEN_CHECKING)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


@app.route("/"+OPEN_ANSWERING, methods=["POST"])
def open_answering():
    error_text = ""
    try:
        quiz_id = request.form["quiz_id"]
        participant_id = request.form["participant_id"]
        ip_address = request.remote_addr
        if is_quiz_host(quiz_id, participant_id, ip_address):
            write_log([ANSWER, quiz_id, ip_address, participant_id, "1", ""], quiz_id, participant_id=participant_id)
        return(wait())
    except Exception as e:
        error_text += ERROR+" ({0}): ".format(OPEN_ANSWERING)+str(e)
    return(render_template(ERROR+HTML_SUFFIX, error_text=error_text))


def back():
    return(render_template(BACK+HTML_SUFFIX))


@app.route("/ajax_submit_answer", methods=["POST"])
def ajax_submit_answer():
    quiz_id = request.form["quiz_id"]
    participant_id = request.form["participant_id"]
    question_id = request.form["question_id"]
    answer_string = request.form["answer_string"]
    ip_address = request.remote_addr
    write_log([ANSWER, quiz_id, ip_address, participant_id, question_id, answer_string], quiz_id, participant_id=participant_id)
    return()

