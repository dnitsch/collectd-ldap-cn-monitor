# collectd-ldap-cn-monitor

collectd python plugin to read out and parse cn=monitor metrics from ldap monitor

requirements:
---
`python-ldap` - should be part of core utils with most linux distros with python

setup:
---

Download the `ldap_cn_monitor.py` and place it, preferrably in a custom defined diretory to avoid collectd python package clashes e.g. `/var/my/collectd/modules/`. 

when defining the `ModulePath "/var/my/collectd/modules/ldap-cn-monitor/"` - Do not forget the traling slash. 

See example below, if placed in a separate conf file `LoadPlugin python` is required if not declared in the collectd.conf or elsewhere. 


options:
---
### url

The ldap fqdn or ip.
Either value will work ==> `"ldap://fqdn:389"` || `"ldap://127.0.0.1:389"`

Currently you can only define a single host or if using a load balanced URL the metrics will only be run agains the host which has answered the request.

default: `ldap://localhost`

### base_dn

The base DN against which to perform the ldapsearch

default: `"cn=monitor"`

### monitor_admin

The monitor or directory admin - must have cn=monitor read privelleges

default: `"cn=Directory Manager"`

### monitor_pwd

monitor_admin password 

default:  `"pwd1234"`

### search_filter

ldap filter to apply on the query.

Any filter attributes must follow the [RFC4515](https://tools.ietf.org/html/rfc4515.html) guidelines and will be appended to the default values which are common across most LDAP implementations.

**leave commented out if empty**

default: `"(|(cn=Work Queue)(cn=JVM*)(cn=HTTP*)(cn=Gauge CPU*)(cn=Active*))"`

useful values would be: `"(cn=dc_example_dc_com_changes*)"`


### attributes

Attributes to retrieve, again any attributes will be appended to the default list.

The values must a single string with comma separated values inside - sample `"foo,bar"`

**leave commented out if empty**

default: `['current-queue-size','current-administrative-session-queue-sizerejected-count','num-worker-threads','num-busy-worker-threads','value','average-connection-duration-millis','total-connections-accepted','total-invocation-count','current-active-connections','average-processing-time-millis','currentReservedMemoryMB','freeReservedMemoryMB','usedReservedMemoryMB','num-operations-in-progress','num-persistent-searches-in-progress']`

useful values would be: `"record-count,database-size-as-percentage-of-jvm-heap"`


example:
---

```conf
<Plugin python>
	ModulePath "/var/my/collectd/modules/ldap-cn-monitor/"
	LogTraces true
	Interactive false
	Import "ldap_cn_monitor"
	<Module ldap_cn_monitor>
		url "ldap://localhost"
		monitor_admin "cn=Directory Manager"
		monitor_pwd "pwd1234"
		base_dn "cn=monitor"
		# search_filter ""
		# attributes "foo,bar"
	</Module>
</Plugin>
```

cloudwatch example output:

[1]: https://i.ibb.co/wS38S9X/Screenshot-2019-03-11-at-17-26-57.png
![1]

application insights example output:

coming soon!

NOTES:
---
`SELinux` needs to be run in Permissive or Disabled mode
