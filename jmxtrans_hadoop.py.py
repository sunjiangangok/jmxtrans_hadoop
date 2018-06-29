#!/bin/python
import httplib
import json
import os
import requests

import ConfigParser

def http_get(host, port, uri):
    conn = httplib.HTTPConnection(host, port=port)
    conn.request("GET", uri)
    res = conn.getresponse()
    return res

def http_post(url, data):
    requests.post(url=url, data=data)

def get_item(metric, data, name, cluster):
    l = []
    for m in metric:
        if '_rate' in m:
            total = m.split(":")[1].split("/")[1]
            use = m.split(":")[1].split("/")[0]
            rate = m.split(":")[0]
            item = name + ",cluster=" + cluster + " " + rate + "=" + str(float(data[use])/float(data[total]))
            l.append(item)
            continue
        item = name + ",cluster=" + cluster + " " + m + "=" + str(data[m])
        l.append(item)
    return l

def get_data(ip1, ip2, port, uri):
    res = http_get(ip1, port, uri)
    data = res.read()
    if "This is standby RM" not in data:
        return data
    else:
        res = http_get(ip2, port, uri)
        return res.read()

def save_data(url, data):
    for m in data:
        http_post(url, m)

def put_influxdb(section, active_ip, port, db_addr,
                 metric=None, name=None, db_name=None, standby_ip=None):
    data = get_data(active_ip, standby_ip, port, "/jmx")
    data = json.loads(data)
    url = db_addr + "/write?db=" + db_name
    for m in data['beans']:
        if m['name'] in metric:
            key = m['name']
            item_data = get_item(metric[key], m, name, section)
            save_data(url, item_data)

if __name__ == "__main__":
    config = ConfigParser.ConfigParser()
    config.read('default.cfg')
    for section in config.sections():
        active_ip = config.get(section, "active_ip")
        standby_ip = config.get(section, "standby_ip")
        active_port = config.get(section, "active_port")
        db_address = config.get(section, "db_address")
        metric = config.get(section, "metric")
        name = config.get(section, "name")
        dbname = config.get(section, "db_name")
        put_influxdb(section, active_ip, active_port, db_address,
                     metric=json.loads(metric),
                     db_name=dbname,
                     name=name,
                     standby_ip=standby_ip)