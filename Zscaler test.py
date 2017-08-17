import requests, logging, json, iso8601, pytz
from datetime import datetime
from time import strftime, gmtime
from collections import defaultdict

logging.basicConfig(level = logging.INFO)
payload = {'username': '<UN>', 'password': '<PASS>'}
site = '<LINK>'
date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
date_format2 = '%Y-%m-%d %H:%M:%S.%f'
events = {}
message = ''
total_downtime = {}
up = defaultdict(list)
down = defaultdict(list)

def downtime():
    test = ''
    with requests.Session() as s:
        p = s.post(site + 'login/doLogin.html', data = payload)
        start = 1496188801
        end = 1498780800
        current = start
        while(current < end):
            data = '{"jsonrpc":"2.0","method":"event/getEnterpriseEvents","params":{"edgeId":[],"interval":{"start":%s,"end":%s}},"id":15}'%(current*1000, (current+86400)*1000)
            current = current + 86400
            json_data = s.post(site + 'portal/', data=data, verify=False).json()
            for i in json_data['result']['data']:
                if (i['event'] == 'VPN_DATACENTER_STATUS'):
                    details = json.loads(i['detail'])
                    if (details['ikeState'] == 'UP'):
                        uptime = i['eventTime']
                        uptime = iso8601.parse_date(uptime)
                        up[details['dataCenterLogicalId']].append(uptime)
                    elif (details['ikeState'] == 'DOWN'):
                        downtime = i['eventTime']
                        downtime = iso8601.parse_date(downtime)
                        down[details['dataCenterLogicalId']].append(downtime)

        for key, value in up.items():
            up[key].sort()

        for key, value in down.items():
            down[key].sort()
            
        for key, value in up.items():
            for i in range(len(value)):
                for j in range(len(value)):
                    try:
                        if (value[j]>down[key][i]):
                            downtime = value[j] - down[key][i]
                            if (key not in total_downtime):
                                total_downtime[key] = downtime
                            else:
                                total_downtime[key] = total_downtime[key] + downtime
                            break
                    except IndexError:
                        try:
                            localized = pytz.utc.localize(datetime.fromtimestamp(end))
                            downtime = localized - down[key][i]
                        except IndexError:
                            pass
                        try:
                            if (key not in total_downtime):
                                total_downtime[key] = downtime
                            else:
                                total_downtime[key] = total_downtime[key] + downtime
                        except UnboundLocalError:
                            pass
                        

downtime()
with requests.Session() as s:
    p = s.post(site + 'login/doLogin.html', data = payload)
    data = '{"jsonrpc":"2.0","method":"enterprise/getEnterpriseDataCenters","params":{"with":["edgeCount","profileCount","events"]},"id": 13}'
    json_data = s.post(site + 'portal/', data=data, verify=False).json()
    for i in json_data['result']:
        if (i['status']['primary'] == 'CONNECTED'):
            primary_uptime = i['status']['activity']['primary']['lastStatusEvent']
            a = datetime.strptime(primary_uptime, date_format)
            b = datetime.strptime(str(datetime.utcnow()), date_format2)
            primary_uptime = b-a
        else:
            primary_uptime = 'Disconnected'
            
        if (i['status']['secondary'] == 'CONNECTED'):
            secondary_uptime = i['status']['activity']['secondary']['lastStatusEvent']
            a = datetime.strptime(secondary_uptime, date_format)
            b = datetime.strptime(str(datetime.utcnow()), date_format2)
            secondary_uptime = b-a
        else:
            secondary_uptime = 'Disconnected'

        if (i['status']['primaryRedundant'] == 'CONNECTED'):
            primary_red_uptime = i['status']['activity']['primary']['redundant']['lastStatusEvent']
            a = datetime.strptime(primary_red_uptime, date_format)
            b = datetime.strptime(str(datetime.utcnow()), date_format2)
            primary_red_uptime = b-a
        else:
            primary_red_uptime = 'Disconnected'

        if (i['status']['secondaryRedundant'] == 'CONNECTED'):
            secondary_red_uptime = i['status']['activity']['secondary']['lastStatusEvent']
            a = datetime.strptime(secondary_red_uptime, date_format)
            b = datetime.strptime(str(datetime.utcnow()), date_format2)
            secondary_red_uptime = b-a
        else:
            secondary_red_uptime = 'Disconnected'

        log_id = i['logicalId']
        
        events[i['name']] = (log_id, primary_uptime, secondary_uptime, primary_red_uptime, secondary_red_uptime)
        
    for key, value in events.items():
        try:
            downtime_res = total_downtime[value[0]]
        except KeyError:
            downtime_res = 'None'
        message = message + ('%s\nTotal downtime: %s\nPrimary uptime: %s\nSecondary uptime: %s\nPrimary redundant uptime: %s\
\nSecondary redundant uptime: %s\n\n')%(key, downtime_res, value[1], value[2], value[3], value[4])
    print(message)
