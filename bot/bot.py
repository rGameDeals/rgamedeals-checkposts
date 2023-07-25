import sqlite3
import time
import praw
import prawcore
import requests
import logging
import re
import os
import datetime
import yaml
import schedule
import pymysql
from slack import WebClient

con = pymysql.connect(
    host=os.environ['MYSQL_HOST'],
    user=os.environ['MYSQL_USER'],
    passwd=os.environ['MYSQL_PASS'],
    db=os.environ['MYSQL_DB']
)

REDDIT_CID=os.environ['REDDIT_CID']
REDDIT_SECRET=os.environ['REDDIT_SECRET']
REDDIT_USER = os.environ['REDDIT_USER']
REDDIT_PASS = os.environ['REDDIT_PASS']
REDDIT_SUBREDDIT= os.environ['REDDIT_SUBREDDIT']

SLACK_HOOK= os.environ['SLACK_HOOK']

AGENT="python:CheckPostsBot:0.1 (by dgc1980)"

reddit = praw.Reddit(client_id=REDDIT_CID,
                     client_secret=REDDIT_SECRET,
                     password=REDDIT_PASS,
                     user_agent=AGENT,
                     username=REDDIT_USER)
subreddit = reddit.subreddit(REDDIT_SUBREDDIT)

#slack_client = WebClient(os.environ.get('SLACK_API'))
#
#starterbot_id = slack_client.api_call("auth.test")["user_id"]

apppath='/app/config/'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')



os.environ['TZ'] = 'America/Los_Angeles'


cursorObj = con.cursor()


def docheck():
  logging.info("running check on reps")
  con.ping(reconnect=True)
  cursorObj.execute('SELECT * FROM rep_posts WHERE  posttime >  ' +  str( int(time.time()) - (86400 * 90)  ) + " AND reported = 0" )
  rows = cursorObj.fetchall()
  print( len(rows) )
  counter=0
  for row in rows:
   try:
    counter+=1
    #logging.info( "checking " + row[2] )
    if row[4] == 0:
      submission = reddit.submission( row[2])
      if row[5] == None:
        cursorObj.execute('UPDATE rep_posts SET poster = %s WHERE postid = %s', ( submission.author.name , row[2] ) )
        con.commit()
      if submission.author is None:
        logging.info("check - reporting " + row[2])
        data = { "text": 'post https://redd.it/' + row[2] + '/ has been deleted by https://reddit.com/u/' + row[5] }
        url = SLACK_HOOK
        r = requests.post(url, json=data)

        #slack_message = 'post https://redd.it/' + row[2] + '/ has been deleted by https://reddit.com/u/' + row[5]
        #slack_client.api_call("chat.postMessage", channel='#mod-bots',  text=slack_message)


        logging.info( "*** " + row[2] + " has been removed by /u/" + row[5] )
        cursorObj.execute('UPDATE rep_posts SET reported = 1 WHERE postid = "' + row[2] + '"')
        con.commit()
    time.sleep(1)
   except:
    logging.info("error in check")
    time.sleep(1)
  logging.info("done check on reps")

def docheck_all(days):
  logging.info("running check all - " + str(days))
  con.ping(reconnect=True)
  cursorObj.execute('SELECT * FROM all_posts WHERE  posttime >  ' +  str( int(time.time()) - (86400 * days)  ) + " AND reported = 0" )
  rows = cursorObj.fetchall()
  print( len(rows) )
  counter=0
  for row in rows:
    time.sleep(1)
    counter+=1
    #logging.info( "checking " + row[2] )

    try:
     if row[4] == 0:
      submission = reddit.submission( row[2])

      if row[5] == None:
        cursorObj.execute('UPDATE rep_posts SET poster = %s WHERE postid = %s', ( submission.author.name , row[2] ) )
        con.commit()
 
      if submission.author is None:
        if submission.banned_by is None:
            logging.info("check all - reporting " + row[2])
            cursorObj.execute('SELECT count(*) from all_posts where reported = 1 and poster = %s',(row[5],))
            rowa = cursorObj.fetchall()
  
            data = { "text": '`all` post https://redd.it/' + row[2] + '/ has been deleted by https://reddit.com/u/' + row[5] + "  there have been " + str(rowa[0][0]+1) + " submissions deleted - https://deleted.coolify.rgamedeals.net/?name=" + row[5]  }
            url = SLACK_HOOK
            r = requests.post(url, json=data)
            logging.info( "*** " + row[2] + " has been removed by /u/" + row[5] )

  
            cursorObj.execute('UPDATE all_posts SET reported = 1 WHERE postid = %s', ( row[2]) )
            con.commit()
        else:
          cursorObj.execute('DELETE from all_posts WHERE postid = "' + row[2] + '"')
          con.commit()
    except:
      print("error on https://redd.it/"+row[2])
  logging.info("done check all")



def docheck_1h():
  logging.info("running small check")
  con.ping(reconnect=True)
  cursorObj.execute('SELECT * FROM all_posts WHERE  posttime >  ' +  str( int(time.time()) - (60*60)  ) + " AND reported = 0" )
  rows = cursorObj.fetchall()
  counter=0
  for row in rows:
    counter+=1
    #logging.info( "checking " + row[2] )
    try:
     if row[4] == 0:
      submission = reddit.submission( row[2])
      if submission.author is None:
           data = { "text": '(1hr) `all` post https://redd.it/' + row[2] + '/ has been deleted by https://reddit.com/u/' + row[5] + "  there have been " + str(rowa[0][0]+1) + " submissions deleted - https://deleted.coolify.rgamedeals.net/?name=" + row[5]  }
           url = SLACK_HOOK
           r = requests.post(url, json=data)
           logging.info( "*** " + row[2] + " has been removed by /u/" + row[5] )

           cursorObj.execute('UPDATE all_posts SET reported = 1 WHERE postid = %s', ( row[2]) )
           con.commit()
    except:
      print("error on https://redd.it/"+row[2])
    time.sleep(1)
  logging.info("done small check")


schedule.every(10).minutes.do(docheck_1h)
schedule.every(6).hours.do(docheck)
schedule.every(24).hours.do(docheck_all,120)
#schedule.every(7).days.do(docheck_all,120)

url = SLACK_HOOK
data = { "text": 'bot started' }
r = requests.post(url, json=data)
docheck_all(30)

while 1:
    schedule.run_pending()
    time.sleep(30)
