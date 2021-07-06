#!/usr/bin/env python3

from aws_cdk import core
from os import getenv
from configparser import ConfigParser
from jenkins.network import Network
from jenkins.ecs import ECSCluster
from jenkins.jenkins_leader import JenkinsLeader
from jenkins.jenkins_worker import JenkinsWorker

config = ConfigParser()
config.read('./config.ini')

stack_name = config['DEFAULT']['stack_name'] 
account = getenv('CDK_DEFAULT_ACCOUNT')
region = getenv('CDK_DEFAULT_REGION')

service_discovery_namespace = 'jenkins'

app = core.App()
env_USA = core.Environment(account=config['DEFAULT']['account'] , region=config['DEFAULT']['region'] )
network = Network(app, stack_name + 'Network',env=env_USA)
ecs_cluster = ECSCluster(app, stack_name + 'ECS', vpc=network.vpc, service_discovery_namespace=service_discovery_namespace,env=env_USA)
jenkins_workers = JenkinsWorker(app, stack_name + "Worker", vpc=network.vpc, cluster=ecs_cluster,env=env_USA)
jenkins_leader_service = JenkinsLeader(app, stack_name + 'JenkinsLeader', cluster=ecs_cluster, vpc=network, worker=jenkins_workers,env=env_USA)

app.synth()
