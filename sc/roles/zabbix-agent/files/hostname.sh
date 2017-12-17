#!/bin/sh
### BEGIN INIT INFO
# Provides:          set-aws-public-hostname
# Required-Start:
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start daemon at boot time
# Description:       Enable service provided by daemon.
### END INIT INFO

hostname=`curl http://169.254.169.254/latest/meta-data/public-hostname`
hostname $hostname

echo "Hostname=$hostname" > /etc/zabbix/zabbix_agentd.d/hostname.conf && /usr/sbin/service zabbix-agent restart
