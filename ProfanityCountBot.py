import praw
import configparser
import os
import datetime
import traceback
import pymysql
import pprint
import json
import re
from time import sleep
from os.path import sys

def main():
    print("ProfanityCountBot v.01 by u/KilometersFan")
    #Check for config file
    if not os.path.exists('configCustom.cfg'):
        print("No config file exists")
        sys.exit()
    #Grab config settings
    config = configparser.ConfigParser()
    config.read("configCustom.cfg")
    #Set config values
    USERNAME = config.get("Configuration","Username")
    PASSWORD = config.get("Configuration","Password")
    USERAGENT = config.get("Configuration","Useragent")
    CLIENT_ID = config.get("Configuration", "Client_ID")
    CLIENT_SECRET = config.get("Configuration","Client_Secret")
    SLEEP_TIME = 60
    #Login
    reddit = praw.Reddit(client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        user_agent=USERAGENT,
                        username=USERNAME,
                        password=PASSWORD)
    running = True
    profanity_list = parse_list()
    db = pymysql.connect("localhost", "root", "root", "reddithistory")
    cursor = db.cursor()
    while running:
        try:
            # get mentions
            inbox = reddit.inbox
            mentions = list(inbox.mentions())
            frequent_words = {}
            mention_count = 0
            #iterate over mentions
            for mention in mentions:
                count = 0
                counted_before = False
                update_freq_words = False
                if not mention.new:
                    break
                mention_count += 1
                # get author of parent comment the user mentioned the bot from or the submission if the comment was top-level
                mention_body = mention.body.lower().split(" ")
                user = ""
                if len(mention_body) > 1:
                    user = parse_specific_user(reddit, mention_body)
                if not user:
                    user = mention.parent().author
                # get previous user data from database
                sql = "SELECT * FROM userhistory WHERE UserID = '" + user.id +"'"
                cursor.execute(sql)
                lastcomment, newcomment, lastsubmission, newsubmission, lastprofanity = 0, 0, 0, 0, 0
                freq_words_string = ""
                # update info if the user had their profanities counted
                if cursor.rowcount == 0:
                    print(user.name + " has not had their profanities counted!")
                else:
                    results = cursor.fetchone()
                    lastcomment = results[1]
                    lastsubmission = results[2]
                    lastprofanity = results[3]
                    freq_words_string = results[4]
                    # parse the string and add the counts to the frequent_words dict
                    if freq_words_string:
                        frequent_words = json.loads(freq_words_string)
                        if(lastprofanity > len(frequent_words)):
                            lastprofanity -= lastprofanity - len(frequent_words)
                    counted_before = True
                
                comments = list(user.comments.new(limit=None))
                if comments:
                    newcomment = comments[0].created_utc
                # go through user's comments
                for comment in comments:
                    if comment.created_utc <= lastcomment:
                        break
                    words = comment.body.split(" ")
                    for word in words:
                        if word.lower() in profanity_list:
                            update_freq_words = True
                            count += 1
                            if frequent_words.get(word.lower()):
                                frequent_words[word.lower()] = frequent_words[word.lower()] + 1
                            else:
                                frequent_words[word.lower()] = 1
                # go through user's submissions
                submissions = list(user.submissions.new(limit=None))
                if submissions:
                    newsubmission = submissions[0].created_utc
                for submission in submissions:
                    if submission.created_utc <= lastsubmission:
                        break
                    # check submission title
                    words = submission.title.split(" ")
                    for word in words:
                        if word in profanity_list:
                            update_freq_words = True
                            count += 1
                            if frequent_words.get(word.lower()):
                                frequent_words[word.lower()] = frequent_words[word.lower()] + 1
                            else:
                                frequent_words[word.lower()] = 1
                    # check submission text
                    words = submission.selftext.split(" ")
                    for word in words:
                        if word in profanity_list:
                            update_freq_words = True
                            count += 1
                            if frequent_words.get(word.lower()) != None:
                                frequent_words[word.lower()] = frequent_words[word.lower()] + 1
                            else:
                                frequent_words[word.lower()] = 1
                count = lastprofanity + count
                # print out the user's profanity data and reply to the mentioner
                if mention_count > 0:
                    # temp variables 
                    creation_date = str(datetime.datetime.utcfromtimestamp(int(user.created_utc)).strftime('%m-%d-%Y'))
                    message = "Hello comrade. "
                    num_comments = len(comments)
                    num_submissions = len(submissions)
                    # message creation logic

                    if count > 1:
                        print("%s has used %d profanity since %s over %d comments and %d submissions." %(user.name, count, creation_date, num_comments, num_submissions))
                        message += "%s has used %d profanity since %s over %d comments and %d submissions." %(user.name, count, creation_date, num_comments, num_submissions)
                    elif count == 1:
                        print("%s has used %d profanities since %s over %d comments and %d submissions." %(user.name, count, creation_date, num_comments, num_submissions))
                        message += "%s has used %d profanities since %s over %d comments and %d submissions." %(user.name, count, creation_date, num_comments, num_submissions)
                    else:
                        print("%s has never used a profanity since %s over %d comments and %d submissions." %(user.name, creation_date, num_comments, num_submissions))
                        message += "%s has never used a profanity since %s over %d comments and %d submissions." %(user.name, creation_date, num_comments, num_submissions)
                    # generate table of proanities
                    profanities_list = list(frequent_words.keys())
                    profanities_list.sort()
                    if(len(profanities_list)):
                        message += "\n\nProfanities used: (NSFW)\n\nProfanity|Count\n:--|:--\n"
                        for key in profanities_list:
                            # remove word from user history and update profanity counts if that word was taken off the profnaity list beforehand
                            if key not in profanity_list:
                                old_count = count
                                count -= frequent_words.pop(key)
                                update_freq_words = True
                                message = message.replace(str(old_count), str(count))
                            else:
                                if(frequent_words[key] == 0):
                                    frequent_words.pop(key, None)
                                    continue
                                print(key + ": " + str(frequent_words[key]))
                                message +=  key + "|" + str(frequent_words[key]) + "\n"
                    temp_copy = frequent_words
                    # clear the dict for the next mentioner
                    frequent_words = {}
                    message += "\n\nNote: Reddit limits comment/submission getting by bots to 1000.\n\n*Beep boop, I'm a bot! I am currently under development and may not be working. If you have any suggestions for profanities to add or remove, send a message to /u/KilometersFan.*"
                    mention.reply(message)
                # mark mention as read
                mention.mark_read()
                # update the database
                if not counted_before:
                    sql = "INSERT INTO userhistory(UserID, LastCommentCreationTime, LastSubmissionCreationTime, LastProfanityCount) \
                            VALUES ('%s', %d, %d, %d)" % (user.id, newcomment, newsubmission, count)
                else:
                    sql = "UPDATE userhistory SET LastCommentCreationTime = %d, LastSubmissionCreationTime = %d, \
                        LastProfanityCount = %d WHERE UserID = '%s'" % (newcomment, newsubmission, count, user.id)
                cursor.execute(sql)
                db.commit()
                if update_freq_words:
                    sql = "UPDATE userhistory SET profanities = '%s' WHERE UserID = '%s'" % (json.dumps(temp_copy), user.id)
                    cursor.execute(sql)
                    db.commit()

        except KeyboardInterrupt:
            running = False
        except Exception as e:
            now = datetime.datetime.now()
            print(now.strftime("%m-%d-%Y %H:%M"))
            print(traceback.format_exc())
            print('ERROR:', e)
            print('Going to sleep for 60 seconds...\n')
            db.rollback()
            sleep(SLEEP_TIME)
            continue

# def get_user_history(user):
def parse_list():
    profanity_list = []
    with open("profanity_list.txt", "r") as file:
        for line in file.readlines():
            profanity_list.append(line.strip().lower())
    return profanity_list

def parse_specific_user(reddit, mention_body):
    username = ""
    index = 0
    # multiple ways to mention a user on reddit
    try:
        index = mention_body.index("u/profanitycountbot") + 1
    except:
        try:
            index = mention_body.index("/u/profanitycountbot") + 1
        except:
            return None
    if index < len(mention_body):
        if mention_body[index][0:2] == "u/":
            username = mention_body[index][2:]
            return reddit.redditor(username)
        elif mention_body[index][0:3] == "/u/":
            username = mention_body[index][3:]
            return reddit.redditor(username)
    return None
    
if __name__ == "__main__":
    main()