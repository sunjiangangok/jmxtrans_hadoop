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
    l = ["status", "active_shards", "number_of_pending_tasks", "number_of_nodes", "active_shards_percent_as_number"]
    res = {}
    for m in l:
        res[m] = data[m]
    return res

def get_percent(data):
    for m in data:
        available_percent = float(m["available_in_bytes"]) * 100 / float(m["total_in_bytes"])
    return available_percent

def fs_info(item, host, uri):
    hostname = host.split(":")[0]
    port = host.split(":")[1]
    data = http_get(hostname, int(port), uri)
    data = json.loads(data)
    res = {"total_in_bytes": 0, "available_in_bytes": 0}
    max_percent = 0.0
    l = []
    for node in data['nodes']:
        if 'data' in data['nodes'][node]['roles']:
            total = data['nodes'][node]['fs']['total']['total_in_bytes']
            available = data['nodes'][node]['fs']['total']['available_in_bytes']
            res['available_in_bytes'] += available
            res['total_in_bytes'] += total

            percent = get_percent(data['nodes'][node]['fs']['data'])
            l.append(percent)

    max_percent = float(100) - min(l)
    res['use_in_bytes'] = res['total_in_bytes'] - res['available_in_bytes']
    res['use_fs_percent'] = float(res['use_in_bytes']) * 100 / float(res['total_in_bytes'])
    res['max_percent'] = max_percent
    del(res['available_in_bytes'])
    return res

def io_stats(item, host, uri, cluster):
    hostname = host.split(":")[0]
    port = host.split(":")[1]
    data = http_get(hostname, int(port), uri)
    data = json.loads(data)
    res = {"read_kilobytes": 0, "write_kilobytes": 0}
    file = "." + str(cluster)
    last = {"read_kilobytes": 0, "write_kilobytes": 0}
    for node in data['nodes']:
        if 'data' in data['nodes'][node]['roles']:
            stats = data['nodes'][node]['fs']['io_stats']['total']
            res['read_kilobytes'] += stats['read_kilobytes']
            res['write_kilobytes'] += stats['write_kilobytes']
    try:
        with open(file, 'r') as json_file:
            last = json.load(json_file)
        with open(file, 'w') as json_file:
            json_file.write(json.dumps(res))
        for m in res:
            res[m] -= last[m]
    except:
        with open(file, 'w') as json_file:
            json_file.write(json.dumps(res))
        return None

    return res

def put_influxdb(data, db_addr, db_name, cluster, measurement):
    url = db_addr + "/write?db=" + db_name
    try:
        for m in data:
            value = measurement + ",cluster=" + str(cluster) + " " + str(m) + "=" + str(data[m])
            http_post(url, value)
    except:
        return None

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
    if item == "api_io":
        data = io_stats(item, host, uri, cluster)
        put_influxdb(data, db_addr, db_name, cluster, "io_stats")
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