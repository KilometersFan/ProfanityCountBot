import praw
import configparser
import os
import datetime
import traceback
import pymysql
import pprint
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
            # frequent_words = {}
            mention_count = 0
            #iterate over mentions
            for mention in mentions:
                count = 0
                counted_before = False
                if not mention.new:
                    break
                mention_count += 1
                # get author of parent comment the user mentioned the bot from or the submission if the comment was top-level
                user = mention.parent().author
                # get previous user data from database
                sql = "SELECT * FROM userhistory WHERE UserID = '" + user.id +"'"
                cursor.execute(sql)
                lastcomment, newcomment = 0, 0
                lastsubmission, newsubmission = 0, 0
                lastprofanity = 0
                if cursor.rowcount == 0:
                    print(user.name + " has not had their profanities counted!")
                else:
                    results = cursor.fetchone()
                    lastcomment = results[1]
                    lastsubmission = results[2]
                    lastprofanity = results[3]
                    counted_before = True
                
                comments = list(user.comments.new())
                if comments:
                    newcomment = comments[0].created_utc
                # go through user's comments
                for comment in comments:
                    if comment.created_utc <= lastcomment:
                        break
                    words = comment.body.split(" ")
                    for word in words:
                        if word.lower() in profanity_list:
                            count += 1
                            # if frequent_words.get(word.lower()) != None:
                            #     frequent_words[word.lower()] = frequent_words[word.lower()] + 1
                            # else:
                            #     frequent_words[word.lower()] = 1
                # go through user's submissions
                submissions = list(user.submissions.new())
                if submissions:
                    newsubmission = submissions[0].created_utc
                for submission in submissions:
                    if submission.created_utc <= lastsubmission:
                        break
                    # check submission title
                    words = submission.title.split(" ")
                    for word in words:
                        if word in profanity_list:
                            count += 1
                            # if frequent_words.get(word.lower()) != None:
                            #     frequent_words[word.lower()] = frequent_words[word.lower()] + 1
                            # else:
                            #     frequent_words[word.lower()] = 1
                    # check submission text
                    words = submission.selftext.split(" ")
                    for word in words:
                        if word in profanity_list:
                            count += 1
                            # if frequent_words.get(word.lower()) != None:
                            #     frequent_words[word.lower()] = frequent_words[word.lower()] + 1
                            # else:
                            #     frequent_words[word.lower()] = 1
                count = lastprofanity + count
                # print out the user's profanity data
                if mention_count > 0:
                    creation_date = datetime.datetime.utcfromtimestamp(int(user.created_utc)).strftime('%m-%d-%Y')
                    message = ""
                    if count > 1:
                        print(user.name + " has used " + str(count) + " profanities since " + str(creation_date))
                        message = user.name + " has used " + str(count) + " profanities since " + str(creation_date)
                    elif count == 1:
                        print(user.name + " has used " + str(count) + " profanity since " + str(creation_date))
                        message = user.name + " has used " + str(count) + " profanity since " + str(creation_date)
                    else:
                        print(user.name + " has never used a profanity!")
                        message = user.name + " has never used a profanity!"
                    # message += "&nbsp Profanities used: (NSFW)"
                    # for key in list(frequent_words.keys()):
                        # print(key + ": " + str(frequent_words[key]))
                        # message += "&nbsp >! " + key + ": " + str(frequent_words[key])
                    # frequent_words = dict.fromkeys(frequent_words,0)
                    mention.reply(message)
                # mark mention as read
                mention.mark_read()
                if not counted_before:
                    sql = "INSERT INTO userhistory(UserID, LastCommentCreationTime, LastSubmissionCreationTime, LastProfanityCount) \
                            VALUES ('%s', %d, %d, %d)" % (user.id, newcomment, newsubmission, count)
                    cursor.execute(sql)
                    db.commit()
                else:
                    sql = "UPDATE userhistory SET LastCommentCreationTime = %d, LastSubmissionCreationTime = %d, \
                        LastProfanityCount = %d WHERE UserId = '%s'" % (newcomment, newsubmission, count, user.id)
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
if __name__ == "__main__":
    main()