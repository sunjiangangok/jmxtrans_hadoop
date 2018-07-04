#!/bin/python
# https://www.elastic.co/guide/en/elasticsearch/reference/6.2/cluster-nodes-stats.html
import httplib
import json
import os
import requests

import ConfigParser

def http_get(host, port, uri):
    conn = httplib.HTTPConnection(host, port=port)
    conn.request("GET", uri)
    res = conn.getresponse()
    return res.read()

def http_post(url, data):
    requests.post(url=url, data=data)

def cluster_info(item, host, uri):
    hostname = host.split(":")[0]
    port = host.split(":")[1]
    data = http_get(hostname, int(port), uri)
    data = json.loads(data)
    l = ["status", "active_shards", "number_of_pending_tasks", "number_of_nodes", "number_of_data_nodes"]
    res = {}
    for m in l:
        res[m] = data[m]
    return res

def fs_info(item, host, uri):
    hostname = host.split(":")[0]
    port = host.split(":")[1]
    data = http_get(hostname, int(port), uri)
    data = json.loads(data)
    res = {"total_in_bytes": 0, "available_in_bytes": 0}
    for m in res:
        for node in data['nodes']:
            if 'data' in data['nodes'][node]['roles']:
                res[m] += data['nodes'][node]['fs']['total'][m]
    res['available_fs_percent'] = float(res['available_in_bytes']) * 100 / float(res['total_in_bytes'])
    return res

def put_influxdb(data, db_addr, db_name, cluster, measurement):
    url = db_addr + "/write?db=" + db_name
    for m in data:
        value = measurement + ",cluster=" + str(cluster) + " " + str(m) + "=" + str(data[m])
        http_post(url, value)

def process_one_item(item, uri, cluster, host=None, db_addr=None, db_name=None):
    if item == "api_cluster":
        data = cluster_info(item, host, uri)
        if "status" in data:
            data["status"] = '"' + data["status"] + '"'
        put_influxdb(data, db_addr, db_name, cluster, "cluster_info")
        return None
    if item == "api_fs":
        data = fs_info(item, host, uri)
        put_influxdb(data, db_addr, db_name, cluster, "fs_info")
        return None

def get_db_cfg(config, section):
    host = config.get(section, "host")
    db_address = config.get(section, "db_address")
    db_name = config.get(section, "db_name")
    return (host, db_address, db_name)

if __name__ == "__main__":
    config = ConfigParser.ConfigParser()
    config.read('es_default.cfg')
    for section in config.sections():
        (host, db_address, db_name) = get_db_cfg(config, section)
        for item in config.options(section):
            if "api_" in item:
                process_one_item(item,
                                 config.get(section, item),
                                 section,
                                 host=host,
                                 db_addr=db_address,
                                 db_name=db_name)