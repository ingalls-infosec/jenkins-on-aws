from aws_cdk import (
    aws_ec2,
    core
)
from configparser import ConfigParser

config = ConfigParser()
config.read('./config.ini')


class Network(core.Stack):
    def __init__(self, scope: core.Stack, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.vpc = aws_ec2.Vpc.from_lookup(self,"Vpc",vpc_name=config['DEFAULT']['vpcname'])
        #self.vpc = aws_ec2.Vpc.from_vpc_attributes(self,"Vpc",vpc_id=config['DEFAULT']['vpcid'],availability_zones=[config['DEFAULT']['availabilityzoneprivate'],config['DEFAULT']['availabilityzonepublic']],private_subnet_ids=[config['DEFAULT']['subnetid']])
        #self.vpc.private_subnets=self.vpc.select_subnets(availability_zones=[config['DEFAULT']['availabilityzone']])
        # (
        #     self, "Vpc",
        #     cidr=config['DEFAULT']['cidr'],
        # )

