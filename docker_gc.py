import os
import sys
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from fabric.api import env
from fabric.api import hosts
from fabric.api import run
from fabric.api import settings
from pythonjsonlogger import jsonlogger

#env.keyfile = ssh_key.pem  os.environ.get('ENV_SSH_PRIVATE_KEY')
f = open('ssh_key.pem', 'w')
f.write(os.environ.get('ENV_SSH_PRIVATE_KEY'))
f.close

env.key_filename = 'ssh_key.pem'
#env.keyfile = os.environ.get('ENV_SSH_PRIVATE_KEY')
env.user = os.environ.get('ENV_SSH_USER')

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

sched = BlockingScheduler()
logging.basicConfig()

@sched.scheduled_job('cron', minute=minute, hour=hour_of_day)
def docker_registry_gc():
    for host in other_hosts:
        with settings(host_string = host):
           run('sudo systemctl stop docker-registry')
           run('docker run -d -v /etc/docker/registry/config.yml:/etc/docker/registry/config.yml:ro -e ENV_REGISTRY_STORAGE_MAINTENANCE_READONLY_ENABLED=true --name docker-registry-ro registry:latest')
        pass
    for host in registry_gc:
        with settings(host_string = host):
           run('docker exec -it docker-registy bin/registry garbage-collect --dry-run /etc/docker/registry/config.yml')
        pass
    for host in other_hosts:
       with settings(host_string = host):
          run('docker stop docker-registry-ro && docker rm docker-registry-ro')
          run('sudo systemctl start docker-registry')

sched.start()
