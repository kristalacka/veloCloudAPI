from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
from time import strftime, gmtime
from collections import defaultdict
from email.mime.text import MIMEText
import requests, logging, json, iso8601, pytz, smtplib

logging.basicConfig(level = logging.INFO)
payload = {'username': '<UN>', 'password': '<PASS>'}
site = '<LINK>'
date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
date_format2 = '%Y-%m-%d %H:%M:%S.%f'
s30 = timedelta(seconds = 360)

def send_mail(zscaler, tunnel, time):
    time = time.replace('T', ' ')
    time = time.replace('Z', '')
    date = strftime('%Y/%m/%d', gmtime())
    msg = MIMEText('')
    msg['From'] = '<FROMEMAIL>'
    msg['To'] = '<TOEMAIL>'
    msg['Subject'] = '%s tunnel %s down (%s)'%(zscaler, tunnel, time)
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login('<EMAIL>', '<PASS>')
    mail.send_message(msg)
    print('message sent')
    mail.quit()
    return
    
def check_events():
    dc = False
    with requests.Session() as s:
        p = s.post(site + 'login/doLogin.html', data = payload)
        data = '{"jsonrpc":"2.0","method":"enterprise/getEnterpriseDataCenters","params":{"with":["edgeCount","profileCount","events"]},"id": 13}'
        json_data = s.post(site + 'portal/', data = data, verify = False).json()
        for i in json_data['result']:
            if (i['status']['primary'] == 'DISCONNECTED'):
                event_time = i['status']['activity']['primary']['lastStatusEvent']
                a = datetime.strptime(event_time, date_format)
                b = datetime.strptime(str(datetime.utcnow()), date_format2)
                downtime = b-a
                print(downtime)
                if (downtime<=s30):
                    dc = True
                    send_mail(i['name'], 'primary', event_time)
            if (i['status']['secondary'] == 'DISCONNECTED'):
                event_time = i['status']['activity']['secondary']['lastStatusEvent']
                a = datetime.strptime(event_time, date_format)
                b = datetime.strptime(str(datetime.utcnow()), date_format2)
                downtime = b-a
                print(downtime)
                if (downtime<=s30):
                    dc = True
                    send_mail(i['name'], 'secondary', event_time)
            if (i['status']['primaryRedundant'] == 'DISCONNECTED'):
                event_time = i['status']['activity']['primary']['redundant']['lastStatusEvent']
                a = datetime.strptime(event_time, date_format)
                b = datetime.strptime(str(datetime.utcnow()), date_format2)
                downtime = b-a
                print(downtime)
                if (downtime<=s30):
                    dc = True
                    send_mail(i['name'], 'primary redundant', event_time)
            if (i['status']['secondaryRedundant'] == 'DISCONNECTED'):
                event_time = i['status']['activity']['secondary']['redundant']['lastStatusEvent']
                a = datetime.strptime(event_time, date_format)
                b = datetime.strptime(str(datetime.utcnow()), date_format2)
                downtime = b-a
                print(downtime)
                if (downtime<=s30):
                    dc = True
                    send_mail(i['name'], 'secondary redundant', event_time)
        if (dc == True):
            time.sleep(320)
    return

        
sched = BlockingScheduler()
sched.add_job(check_events, 'interval', seconds = 30, start_date = '2017-07-09 16:00', timezone = 'GMT')
sched.start()
