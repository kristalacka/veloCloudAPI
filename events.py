import requests, logging, smtplib, iso8601, pytz, json
from datetime import datetime, timedelta
from collections import defaultdict
from email.mime.text import MIMEText
from time import strftime, gmtime
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level = logging.INFO)
site = '<LINK>'
date_format = '%Y-%m-%dT%H:%M:%S.%fZ'

def get_message():
    message = ''
    Edges_up = defaultdict(list)
    Edges_down = defaultdict(list)
    edge_up_events = defaultdict(list)
    edge_down_events = defaultdict(list)
    down_trigger = ''
    nr = 0
    total_uptime = {}
    total_downtime = {}
    
    payload = {'username': '<UN>', 'password': '<PASS>'}
    with requests.Session() as s:
        p = s.post(site + 'login/doLogin.html', data = payload)
        end = 1496275199
        start = 1493596800
        current = start #change to set to last month
        while (current<end):
            data = '{"jsonrpc":"2.0","method":"event/getEnterpriseEvents","params":{"edgeId":[],"interval":{"start":%s,"end":%s}},"id":9}'%(current*1000, (current+86400)*1000)
            current = current + 86400
            json_data = s.post(site + 'portal/', data=data, verify=False).json()
            for i in json_data['result']['data']:
                if (i['event'] == 'EDGE_DOWN'):
                        j = json.loads(i['detail'])
                        zone = j['timezone']
                        trigger_time = j['triggerTime']
                        down_trigger = trigger_time
                        last_contact = j['lastContact']
                        parsed_trigger = iso8601.parse_date(trigger_time)
                        parsed_contact = iso8601.parse_date(last_contact)
                        trigger_time = parsed_trigger.astimezone(pytz.timezone(zone))
                        last_contact = parsed_contact.astimezone(pytz.timezone(zone))
                        edge_info = 'Trigger time: %s\nLast contact: %s (time zone: UTC%s [Edge local time])\n' %(trigger_time.strftime("%Y-%m-%d %H:%M:%S"), last_contact.strftime("%Y-%m-%d %H:%M:%S"), datetime.now(pytz.timezone(zone)).strftime('%z'))
                        Edges_down[i['edgeName']].append(edge_info)
                        edge_down_events[i['edgeName']].append(trigger_time)
                if (i['event'] == 'EDGE_UP'):
                        j = json.loads(i['detail'])
                        zone = j['timezone']
                        trigger_time = j['triggerTime']
                        last_contact = j['lastContact']
                        parsed_trigger = iso8601.parse_date(trigger_time)
                        parsed_contact = iso8601.parse_date(last_contact)
                        trigger_time = parsed_trigger.astimezone(pytz.timezone(zone))
                        last_contact = parsed_contact.astimezone(pytz.timezone(zone))
                        edge_info = 'Trigger time: %s\nLast contact: %s (time zone: UTC%s [Edge local time])\n' %(trigger_time.strftime("%Y-%m-%d %H:%M:%S"), last_contact.strftime("%Y-%m-%d %H:%M:%S"), datetime.now(pytz.timezone(zone)).strftime('%z'))
                        Edges_up[i['edgeName']].append(edge_info)
                        edge_up_events[i['edgeName']].append(trigger_time)

    for key, value in Edges_up.items():
        sorted_together = sorted(zip(edge_up_events[key], value))
        edge_up_events[key] = [x[0] for x in sorted_together]
        Edges_up[key] = [x[1] for x in sorted_together]

    for key, value in Edges_down.items():
        sorted_together = sorted(zip(edge_down_events[key], value))
        edge_down_events[key] = [x[0] for x in sorted_together]
        Edges_up[key] = [x[1] for x in sorted_together]
        
    for key, value in edge_up_events.items():
        for i in range(len(value)):
            try:
                downtime = value[i] - edge_down_events[key][i]
                if (key not in total_downtime):
                    total_downtime[key] = downtime
                else:
                    total_downtime[key] = total_downtime[key] + downtime
            except IndexError:
                downtime = 'N/A'
            Edges_down[key][i] = Edges_down[key][i] + 'Downtime: %s\n'%downtime

    for key, value in edge_up_events.items():
        for i in range(len(value)):
            try:
                uptime = value[i+1] - edge_down_events[key][i]
                if (key not in total_uptime):
                    total_uptime[key] = uptime
                else:
                    total_uptime[key] = total_uptime[key] + uptime
            except IndexError:
                uptime = 'N/A'
            Edges_up[key][i] = Edges_up[key][i] + 'Uptime: %s\n'%uptime
                
            
    for key, value in Edges_up.items():
        try:
            message = message + key + '\n\nUP: ' + str(len(value)) + ' (uptime: ' + str(total_uptime[key]) + ')\n'
        except KeyError:
            message = message + key + '\nUP: ' + str(len(value)) + ' (uptime: N/A)\n'
        for j in value:
            message = message + j + '\n'
        for key2, value2 in Edges_down.items():
            if (key2 == key):
                try:
                    message = message + '\nDOWN: ' + str(len(value)) + ' (downtime: ' + str(total_downtime[key]) + ')\n'
                except KeyError:
                    message = message + '\nDOWN: ' + str(len(value)) + ' (downtime: N/A)\n'
                for k in value2:
                    message = message + k + '\n'
        message = message + '\n--------------------------------------\n\n'
        
    return message

def send_mail():
    message = get_message()
    date = strftime('%Y/%m/%d', gmtime())
    msg = MIMEText(message)
    msg['From'] = '<FROMMAIL>'
    msg['To'] = '<TOMAIL>'
    msg['Subject'] = 'Montly Edge Uptime Update: %s' %date

    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login('<EMAIL>', '<PASS>')
    mail.send_message(msg)
    print('message sent')
    mail.quit()
    return
    
'''sched = BlockingScheduler()
#sched.add_job(send_mail, 'cron', day = 1, start_date = '2017-06-30 06:00', timezone = 'Asia/Singapore')
sched.add_job(send_mail, 'interval', seconds = 120, start_date = '2017-06-30 06:00', timezone = 'GMT')
sched.start() '''
send_mail()

