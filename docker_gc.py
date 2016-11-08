import os
import sys
import base64
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from fabric.api import run
from fabric.api import settings
from pythonjsonlogger import jsonlogger

key = base64.b64decode(os.environ.get('ENV_SSH_PRIVATE_KEY'))
user = os.environ.get('ENV_SSH_USER')

hour_of_day = os.environ.get('ENV_HOUR_OF_DAY')
minute = os.environ.get('ENV_MINUTE_OF_HOUR')

hosts_string = os.environ.get('ENV_REGISTRY_HOST_LIST')

registry_hosts = hosts_string.split(',')
registry_gc = registry_hosts[:1]
other_hosts = registry_hosts[1:]

logging.basicConfig(level=os.environ.get('LOG_LEVEL', logging.INFO))
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
if os.environ.get('FORMATTER', 'json') == 'json':
    default_format = '%(message)s,' \
                     '%(funcName)s,' \
                     '%(levelname)s,' \
                     '%(lineno)s,' \
                     '%(asctime)s,' \
                     '%(module)s'
    log_format = os.environ.get('LOG_FORMAT', default_format)
    formatter = jsonlogger.JsonFormatter(fmt=log_format)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    root_log = logging.getLogger()
    root_log.handlers = []
    root_log.addHandler(handler)
log = logging.getLogger(__name__)


def docker_registry_gc():
    log.info("""Reloading registry instances with Read-only""")
    for host in other_hosts:
        with settings(host_string=host, key=key, user=user):
            run('sudo systemctl stop docker-registry')
            run('docker run -d -v \
            /etc/docker/registry/config.yml:/etc/docker/registry/config.yml:ro\
             -e ENV_REGISTRY_STORAGE_MAINTENANCE_READONLY_ENABLED=true --name \
              docker-registry-ro registry:2.5.1')
    log.info("""Reloading of registry instances completed.""")
    for host in registry_gc:
        log.info("""Executing a 2-step garbage collection process.""")
        with settings(host_string=host, key=key, user=user):
            run('docker exec -it docker-registry bin/registry garbage-collect \
            --dry-run /etc/docker/registry/config.yml')
    log.info("""Execution of the garbage-collection completed.""")
    for host in other_hosts:
        log.info("""Starting registry instances in normal mode.""")
        with settings(host_string=host, key=key, user=user):
            run('docker stop docker-registry-ro && \
            docker rm docker-registry-ro')
            run('sudo systemctl start docker-registry')


def main():
    sched = BlockingScheduler()
    logging.basicConfig()
    log.info("""Starting job with with parameters: \
    time: %s:%s, ssh_user: %s, registry_hosts: %s, \
    garbage_collector: \
     %s""" % (hour_of_day, minute, user, key, hosts_string, registry_gc))
    sched.scheduled_job('cron',
                        minute=minute,
                        hour=hour_of_day,
                        job=docker_registry_gc)
    sched.start()

if __name__ == '__main__':
    main()
