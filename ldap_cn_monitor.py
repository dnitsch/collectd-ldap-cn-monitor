'''
ldap cn=monitor collectd plugin written in Python.
Collects metrics from  LDAP's cn=monitor for Ping Directory and dispatches them to collectd process
Uses python-ldap
all connections are handled synchronously
'''
# Logging func taken from https://github.com/mleinart/collectd-haproxy

import collectd
import ldap
import ldap.filter as ldap_filter
import json, os, sys

NAME = 'ldap_cn_monitor'
VALUE_TYPE = 'gauge'
VERBOSE_LOGGING = True
DEFAULT_LDAP_URL = 'ldap://localhost'
DEFAULT_MONITOR_ADMIN = 'cn=Directory Manager'
DEFAULT_MONITOR_PWD = 'pwd1234'
DEFAULT_BASE_DN = 'cn=monitor'
DEFAULT_SEARCH_FILTER = '(|(cn=Work Queue)(cn=JVM*)(cn=HTTP*)(cn=Gauge CPU*)(cn=Active*)%s)'
DEFAULT_RETRIEVE_ATTRS = ['current-queue-size','current-administrative-session-queue-sizerejected-count','num-worker-threads','num-busy-worker-threads','value','average-connection-duration-millis','total-connections-accepted','total-invocation-count','current-active-connections','average-processing-time-millis','currentReservedMemoryMB','freeReservedMemoryMB','usedReservedMemoryMB','num-operations-in-progress','num-persistent-searches-in-progress']
DEFAULT_USER_FILTER = ''
DEFAULT_USER_ATTRS = ''
METRIC_TYPES = {
  'cpu.load': ('cpu_load', 'gauge')
}

class LDAPConnector:
    def __init__(self, ldap_url=DEFAULT_LDAP_URL, ldap_monitor_admin=DEFAULT_MONITOR_ADMIN, ldap_monitor_pwd=DEFAULT_MONITOR_PWD):
        self.ldap_url = ldap_url
        self.ldap_monitor_admin = ldap_monitor_admin
        self.ldap_monitor_pwd = ldap_monitor_pwd

    def init_bind(self):

        try:
            l_init = ldap.initialize(self.ldap_url)
            # you should  set this to ldap.VERSION2 if you're using a v2 directory
            # TODO: expose version choice of LDAP.
            l_init.protocol_version = ldap.VERSION3
            l_init.set_option(ldap.OPT_NETWORK_TIMEOUT, 2.0)
            l_init.set_option(ldap.OPT_TIMEOUT, 2.0)
            l_init.simple_bind_s(self.ldap_monitor_admin, self.ldap_monitor_pwd)
        except ldap.LDAPError as e:
            logger('err', 'LDAP init and bind failed: %s' % str(e))
            # print(str(e))

        return l_init

    def search(self, base_dn=DEFAULT_BASE_DN, search_filter=DEFAULT_USER_FILTER, retrieve_attrs=DEFAULT_USER_ATTRS):
        '''
        Sends a search command to LDAP
        Reads the result currently only using all Sends a search command to LDAP
        '''
        conn = self.init_bind()
        result = (ldap.LDAPError, None)
        searchScope = ldap.SCOPE_SUBTREE

        try:
            # using sync search
            # esc_search_filter = ldap_filter.escape_filter_chars(search_filter, 0)
            computed_filter = DEFAULT_SEARCH_FILTER % search_filter
            computed_attrs = DEFAULT_RETRIEVE_ATTRS + retrieve_attrs.split(',')
            sync_search = conn.search_s(base_dn, searchScope, computed_filter, computed_attrs)
            result = (ldap.RES_SEARCH_RESULT, sync_search)
        except ldap.LDAPError as e:
            logger('warn', 'LDAP search failed: %s' % str(e))
            result = (ldap.LDAPError, e)

        conn.unbind_s()
        return result


def walk_response(data_set):

    parsed_data = dict()

    if type(data_set) == list and len(data_set) >= 1:
        for data in data_set:
            if type(data) == tuple and len(data) == 2:
                metric_item = dict()
                for i in data[1]:
                    if i:
                        if type(data[1][i]) == list:
                            metric_item[i] = data[1][i][0]

            parsed_data[data[0]] = metric_item

    return parsed_data


def get_stats():

    ldap_parsed = []

    ldap_stats = LDAPConnector(LDAP_URL, LDAP_MONITOR_ADMIN, LDAP_MONITOR_PWD)

    res_type, raw_data = ldap_stats.search(BASE_DN, SEARCH_FILTER, RETRIEVE_ATTRS)
    if res_type == ldap.RES_SEARCH_RESULT:
        ldap_parsed = walk_response(raw_data)

    return ldap_parsed


### INIT configure object
def configure_callback(conf):
    global LDAP_URL, LDAP_MONITOR_ADMIN, LDAP_MONITOR_PWD, BASE_DN, SEARCH_FILTER, RETRIEVE_ATTRS
    LDAP_URL = DEFAULT_LDAP_URL
    LDAP_MONITOR_ADMIN = DEFAULT_MONITOR_ADMIN
    LDAP_MONITOR_PWD = DEFAULT_MONITOR_PWD
    BASE_DN = DEFAULT_BASE_DN
    SEARCH_FILTER = DEFAULT_USER_FILTER
    RETRIEVE_ATTRS = DEFAULT_USER_ATTRS


    for node in conf.children:
        if node.key == "url":
            LDAP_URL = node.values[0]
        elif node.key == "monitor_admin":
            LDAP_MONITOR_ADMIN = node.values[0]
        elif node.key == "monitor_pwd":
            LDAP_MONITOR_PWD = node.values[0]
        elif node.key == "base_dn":
            BASE_DN = node.values[0]
        elif node.key == "search_filter":
            SEARCH_FILTER = node.values[0]
        elif node.key == "attributes":
            RETRIEVE_ATTRS = node.values[0]
        else:
            logger('warn', 'Unknown config key: %s' % node.key)


### DISPATCH TO COLLECTD
def read_callback():
    logger('verb', "beginning read_callback")

    stats = get_stats()

    if not stats:
        logger('warn', "%s: No data received" % NAME)
        return

    for collectd_data in stats:
        if type(stats[collectd_data]) == dict and len(stats[collectd_data]) > 0:
            _type_instance = collectd_data.replace(',' + BASE_DN, '')
            for key in stats[collectd_data]:
                # if key in METRIC_TYPES:
                # key_root, val_type = METRIC_TYPES[key]
                value = bytes.decode(stats[collectd_data][key]) if type(stats[collectd_data][key]) == 'bytes' else stats[collectd_data][key]
                #
                # clean output in case addiotional non-numeric vals are passed in
                # clean_value = '0.00' if value.split(' ')[0] == 'N/A' else  value.split(' ')[0]
                #
                # test =  collectd_data.replace(',' + DEFAULT_BASE_DN, '') + "." + key
                val = collectd.Values(plugin=NAME, type=VALUE_TYPE)
                val.type_instance = _type_instance + "." + key
                val.values = [ value ]
                val.dispatch()


def logger(t, msg):
    if DEBUG_ON:
        print(t, msg)
    else:
        if t == 'err':
            collectd.error('%s: %s' % (NAME, msg))
        elif t == 'warn':
            collectd.warning('%s: %s' % (NAME, msg))
        elif t == 'verb':
            if VERBOSE_LOGGING:
                collectd.info('%s: %s' % (NAME, msg))
        else:
            collectd.notice('%s: %s' % (NAME, msg))


# DEBUG
DEBUG_ON = True if os.getenv("DEBUG") == "ON" else False

if DEBUG_ON:
    test_data = json.load(open(os.path.join(sys.path[0], './__test.json'), 'r'))
    LDAP_URL = test_data['LDAP_URL']
    LDAP_MONITOR_ADMIN = test_data['LDAP_MONITOR_ADMIN']
    LDAP_MONITOR_PWD = test_data['LDAP_MONITOR_PWD']
    BASE_DN = test_data['BASE_DN']
    SEARCH_FILTER = test_data['SEARCH_FILTER']
    RETRIEVE_ATTRS = test_data['RETRIEVE_ATTRS']
    read_callback()
else:
    # Register our callbacks to collectd
    collectd.register_config(configure_callback)
    collectd.register_read(read_callback)

