import smtplib, requests, logging, json, iso8601, pytz
from email.mime.text import MIMEText
from time import strftime, gmtime
from datetime import datetime
from collections import defaultdict
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level = logging.INFO)
date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
date_format2 = '%Y-%m-%d %H:%M:%S.%f'
payload = {'username': '<UN>', 'password': '<PASS>'}
site = '<LINK>'
trigger_up = defaultdict(list)
trigger_down = defaultdict(list)
total_downtime = {}
instances = {}

def send_mail():
    message = get_message()
    date = strftime('%Y/%m/%d', gmtime())
    msg = MIMEText(message)
    msg['From'] = '<FROMMAIL>'
    msg['To'] = '<TOMAIL>'
    msg['Subject'] = 'Daily Update: %s' %date

    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login('<EMAIL>', '<PASS>')
    mail.send_message(msg)
    print('message sent')
    mail.quit()
    return

def link_uptime():
    with requests.Session() as s:
        p = s.post(site + 'login/doLogin.html', data = payload)
        end = 1496275199
        start = 1493596800
        end_date = datetime.fromtimestamp(1496275199)
        current = start #change to set to last month
        while (current<end):
            data = '{"jsonrpc":"2.0","method":"event/getEnterpriseEvents","params":{"edgeId":[],"interval":{"start":%s,"end":%s}},"id":9}'%(current*1000, (current+86400)*1000)
            current = current + 86400
            json_data = s.post(site + 'portal/', data=data, verify=False).json()
            for i in json_data['result']['data']:
                if (i['event'] == 'LINK_ALIVE'):
                    j = json.loads(i['detail'])
                    up_time = i['eventTime']
                    up_time = iso8601.parse_date(up_time)
                    trigger_up[(i['edgeName'], j['logicalId'])].append(up_time)
                if (i['event'] == 'LINK_DEAD'):
                    j = json.loads(i['detail'])
                    down_time = i['eventTime']
                    down_time = iso8601.parse_date(down_time)
                    trigger_down[(i['edgeName'], j['logicalId'])].append(down_time)

        for key, value in trigger_up.items():
            trigger_up[key].sort()
            
        for key, value in trigger_down.items():
            trigger_down[key].sort()
                   
        for key, value in trigger_up.items(): #key - link code / value - link up events
            for i in range(len(value)): #events
                for j in range(len(value)):
                    try:
                        if (value[j]>trigger_down[key][i]):
                            downtime = value[j] - trigger_down[key][i]
                            if (key not in total_downtime):
                                total_downtime[key] = downtime
                            else:
                                total_downtime[key] = total_downtime[key] + downtime
                            break
                    except IndexError:
                        try:
                            localized = pytz.utc.localize(datetime.fromtimestamp(end))
                            downtime = localized - trigger_down[key][i]
                        except IndexError:
                            pass
                        try:
                            if (key not in total_downtime):
                                total_downtime[key] = downtime
                            else:
                                total_downtime[key] = total_downtime[key] + downtime
                        except UnboundLocalError:
                            pass
                            
    print('link uptime done') 
        
def get_message():
    message = ''
    with requests.Session() as s:
        p = s.post(site + 'login/doLogin.html', data = payload)
        data = '{"jsonrpc":"2.0","method":"enterprise/getEnterpriseEdges","params":{"with":["site","configuration","recentLinks"]},"id":6}'
        json_data = s.post(site + 'portal/', data=data, verify=False).json()
        for i in range((len(json_data['result']))):
            name = json_data['result'][i]['name']
            status = json_data['result'][i]['edgeState']
            if (status == 'CONNECTED'):
                uptime = json_data['result'][i]['edgeStateTime']
                a = datetime.strptime(uptime, date_format)
                b = datetime.strptime(str(datetime.utcnow()), date_format2)
                uptime = b-a
            else:
                uptime = 'N/A'
            i_d = str(json_data['result'][i]['id'])
            sys_up = json_data['result'][i]['systemUpSince']
            sys_up = sys_up.replace('T', ' ')
            sys_up = sys_up.replace('Z', ' ')
            srv_up = json_data['result'][i]['serviceUpSince']
            srv_up = srv_up.replace('T', ' ')
            srv_up = srv_up.replace('Z', ' ')
            file = open('test.txt', 'w')
            file.write(str(json_data))
            file.close()
            message = message + 'Edge name: %s\nEdge status: %s\nEdge uptime: %s\nID: %s\nSystem up since: %s\nService up since: %s\n'\
                %(name, status, uptime, i_d, sys_up, srv_up)
            if (status == 'CONNECTED'):
                for j in range(len(json_data['result'][i]['recentLinks'])):
                    isp = json_data['result'][i]['recentLinks'][j]['isp']
                    link_uptime = json_data['result'][i]['recentLinks'][j]['lastEvent']
                    try:
                        a = datetime.strptime(link_uptime, date_format)
                        b = datetime.strptime(str(datetime.utcnow()), date_format2)
                        link_uptime = b-a
                    except:
                        link_uptime = 'N/A'
                    link_ip = json_data['result'][i]['recentLinks'][j]['ipAddress']
                    net_side = json_data['result'][i]['recentLinks'][j]['networkSide']
                    net_type = json_data['result'][i]['recentLinks'][j]['networkType']
                    edgelink = json_data['result'][i]['name']
                    logical_id = json_data['result'][i]['recentLinks'][j]['logicalId']
                    try:
                        downtime = total_downtime[(edgelink, json_data['result'][i]['recentLinks'][j]['logicalId'])]
                        instances = len(trigger_down[(edgelink, logical_id)])
                    except KeyError:
                        downtime = 'N/A'
                        instances = 'N/A'
                    if (downtime != 'N/A' and instances == 0):
                        downtime = 'N/A'
                        instances = 'N/A'
                    message = message + '\tLink %s:\n\tISP: %s\n\tLink uptime: %s\n\tLink IP: %s\n\tNetwork Side: %s\n\tNetwork Type: %s\n\tTotal downtime for last month: %s (%s instances)\n'\
                        %(str(j+1), isp, link_uptime, link_ip, net_side, net_type, downtime, str(instances))
            message = message + '\n'
    return message

link_uptime()   
'''sched = BlockingScheduler()
sched.add_job(send_mail, 'interval', seconds = 20, start_date = '2017-06-30 06:00', timezone = 'GMT')
#start_date = '2017-06-30 06:00', timezone = 'Asia/Singapore'
sched.start()'''
send_mail()



