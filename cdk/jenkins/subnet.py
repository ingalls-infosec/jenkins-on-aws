from aws_cdk import (
    aws_ec2,
    core
)
from configparser import ConfigParser

config = ConfigParser()
config.read('./config.ini')


class Subnet(core.Stack):
    def __init__(self, scope: core.Stack, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        return [aws_ec2.aws_ec2.SubnetSelection(subnets=[aws_ec2.Subnet.from_subnet_id(self,config['DEFAULT']['subnetname'], config['DEFAULT']['subnetid'])])]


