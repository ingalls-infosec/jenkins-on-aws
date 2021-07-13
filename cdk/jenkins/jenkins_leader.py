from aws_cdk import (
    aws_ecs_patterns as ecs_patterns,
    aws_ecs as ecs,
    aws_ecr_assets as ecr,
    aws_ec2 as ec2,
    aws_servicediscovery as sd,
    aws_iam as iam,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elb,
    aws_efs as efs,
    core
)
import json
import inspect

from configparser import ConfigParser

config = ConfigParser()
config.read('./config.ini')


class JenkinsLeader(core.Stack):

    def __init__(self, scope: core.Stack, id: str, cluster, vpc, worker, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.cluster = cluster
        self.vpc = vpc
        self.worker = worker



        # Building a custom image for jenkins leader.
        self.container_image = ecr.DockerImageAsset(
            self, "JenkinsleaderDockerImage",
            directory='./docker/leader/'
        )

        
        if config['DEFAULT']['fargate_enabled'] == "yes" or not config['DEFAULT']['ec2_enabled'] == "yes":
            
#region EFS
            # set up EFS filesystem
            self.file_system = efs.FileSystem(scope=self,
                id="JenkinsEFS",
                vpc=self.vpc.vpc,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                encrypted=True
            )

            self.file_system.add_access_point(
                id="JenkinsEFSAcessPoint",
                path='/',
            )

            self.volume_config = ecs.Volume(
                name="JenkinsEFS",
                efs_volume_configuration= ecs.EfsVolumeConfiguration(
                    file_system_id=self.file_system.file_system_id,
                )
            )

            self.mount_point = ecs.MountPoint(
                read_only=False,
                container_path="/var/jenkins_home",
                source_volume=self.volume_config.name
            )
#endregion

#region logging
            # self.service_log_group = logs.LogGroup(
            #     self,
            #     'JenkinsOnAWS-SLG',
            #     log_group_name="/ecs/JenkinsOnAWS-SLG"
            # )

            # self.service_log_driver = ecs.AwsLogDriver(
            #     log_group=self.service_log_group,
            #     stream_prefix='JenkinsOnAWS-SLG'
            # )
#endregion


#region new task definition
            #new method for task definition
            self.jenkins_task2 = ecs.FargateTaskDefinition(
                self, "JenkinsLeader",
                volumes=[self.volume_config],
                cpu=int(config['DEFAULT']['fargate_cpu']),
                memory_limit_mib=int(config['DEFAULT']['fargate_memory_limit_mib']),
            )


            self.jenkins_container = self.jenkins_task2.add_container(
                "Jenkins",
                image=ecs.ContainerImage.from_docker_image_asset(self.container_image),
                #logging=self.service_log_driver,
                #logging=ecs.AwsLogDriver(stream_prefix='JenkinsOnAWS',log_group=self.service_log_group),
                logging=ecs.AwsLogDriver(stream_prefix='JenkinsOnAWS'),
                environment={
                    # https://github.com/jenkinsci/docker/blob/leader/README.md#passing-jvm-parameters
                    'JAVA_OPTS': '-Djenkins.install.runSetupWizard=false',
                    # https://github.com/jenkinsci/configuration-as-code-plugin/blob/leader/README.md#getting-started
                    'CASC_JENKINS_CONFIG': '/config-as-code.yaml',
                    'network_stack': self.vpc.stack_name,
                    'cluster_stack': self.cluster.stack_name,
                    'worker_stack': self.worker.stack_name,
                    'cluster_arn': self.cluster.cluster.cluster_arn,
                    'aws_region': config['DEFAULT']['region'],
                    'jenkins_url': config['DEFAULT']['jenkins_url'], 
                    'subnet_ids': ",".join([x.subnet_id for x in self.vpc.vpc.private_subnets]),
                    'security_group_ids': self.worker.worker_security_group.security_group_id,
                    'execution_role_arn': self.worker.worker_execution_role.role_arn,
                    'task_role_arn': self.worker.worker_task_role.role_arn,
                    'worker_log_group': self.worker.worker_logs_group.log_group_name,
                    'worker_log_stream_prefix': self.worker.worker_log_stream.log_stream_name,
                    'JENKINS_HOME':'/var/jenkins_home'
                }
            )

            self.jenkins_container.add_port_mappings(
                ecs.PortMapping(container_port=8080)
            )
#endregion


            #original method for task definition
            # # Task definition details to define the Jenkins leader container
            # self.jenkins_task = ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
            #     image=ecs.ContainerImage.from_docker_image_asset(self.container_image),
            #     #task_definition=self.jenkins_task2,
            #     container_port=8080,
            #     enable_logging=True,
            #     environment={
            #         # https://github.com/jenkinsci/docker/blob/leader/README.md#passing-jvm-parameters
            #         'JAVA_OPTS': '-Djenkins.install.runSetupWizard=false',
            #         # https://github.com/jenkinsci/configuration-as-code-plugin/blob/leader/README.md#getting-started
            #         'CASC_JENKINS_CONFIG': '/config-as-code.yaml',
            #         'network_stack': self.vpc.stack_name,
            #         'cluster_stack': self.cluster.stack_name,
            #         'worker_stack': self.worker.stack_name,
            #         'cluster_arn': self.cluster.cluster.cluster_arn,
            #         'aws_region': config['DEFAULT']['region'],
            #         'jenkins_url': config['DEFAULT']['jenkins_url'], 
            #         'subnet_ids': ",".join([x.subnet_id for x in self.vpc.vpc.private_subnets]),
            #         'security_group_ids': self.worker.worker_security_group.security_group_id,
            #         'execution_role_arn': self.worker.worker_execution_role.role_arn,
            #         'task_role_arn': self.worker.worker_task_role.role_arn,
            #         'worker_log_group': self.worker.worker_logs_group.log_group_name,
            #         'worker_log_stream_prefix': self.worker.worker_log_stream.log_stream_name,
            #         'JENKINS_HOME':'/var/jenkins_home'
            #     },
            # )


            # Create the Jenkins leader service
            self.jenkins_leader_service_main = ecs_patterns.ApplicationLoadBalancedFargateService(
                self, "JenkinsleaderService",
                cpu=int(config['DEFAULT']['fargate_cpu']),
                memory_limit_mib=int(config['DEFAULT']['fargate_memory_limit_mib']),
                cluster=self.cluster.cluster,
                desired_count=1,
                enable_ecs_managed_tags=True,
                cloud_map_options=ecs.CloudMapOptions(name="leader", dns_record_type=sd.DnsRecordType('A')),
                #task_image_options=self.jenkins_task,
                task_definition=self.jenkins_task2,
            )
            #print(dir(self.jenkins_leader_service_main))
            #print(inspect.getmembers(self.jenkins_leader_service_main))
            #print(json.dumps(self.jenkins_leader_service_main))
            #print(json.dumps(self.jenkins_task))
            self.jenkins_leader_service = self.jenkins_leader_service_main.service
            self.jenkins_leader_task = self.jenkins_leader_service.task_definition
            
            self.jenkins_leader_service.task_definition.default_container.add_mount_points(self.mount_point)


            # Enable connection between leader and EFS on 2049
            self.jenkins_leader_service.connections.allow_from(
                other=self.file_system,
                port_range=ec2.Port(
                    protocol=ec2.Protocol.TCP,
                    string_representation='leader to EFS 2049',
                    from_port=2049,
                    to_port=2049
                )
            )

        if config['DEFAULT']['ec2_enabled'] == "yes":
            self.jenkins_load_balancer = elb.ApplicationLoadBalancer(
                self, "JenkinsleaderELB",
                vpc=self.vpc.vpc,
                internet_facing=True,
            )

            self.listener = self.jenkins_load_balancer.add_listener("Listener", port=80)
            #self.listener = self.jenkins_load_balancer.add_listener("Listener2", port=443)

            self.jenkins_leader_task = ecs.Ec2TaskDefinition(
                self, "JenkinsleaderTaskDef",
                network_mode=ecs.NetworkMode.AWS_VPC,
                volumes=[ecs.Volume(name="efs_mount", host=ecs.Host(source_path='/mnt/efs'))],
            )

            self.jenkins_leader_task.add_container(
                "JenkinsleaderContainer",
                image=ecs.ContainerImage.from_ecr_repository(self.container_image.repository),
                cpu=int(config['DEFAULT']['ec2_cpu']),
                memory_limit_mib=int(config['DEFAULT']['ec2_memory_limit_mib']),
                environment={
                    # https://github.com/jenkinsci/docker/blob/leader/README.md#passing-jvm-parameters
                    'JAVA_OPTS': '-Djenkins.install.runSetupWizard=false',
                    # https://github.com/jenkinsci/configuration-as-code-plugin/blob/leader/README.md#getting-started
                    'CASC_JENKINS_CONFIG': '/config-as-code.yaml',
                    'network_stack': self.vpc.stack_name,
                    'cluster_stack': self.cluster.stack_name,
                    'worker_stack': self.worker.stack_name,
                    'cluster_arn': self.cluster.cluster.cluster_arn,
                    'aws_region': config['DEFAULT']['region'],
                    'jenkins_url': config['DEFAULT']['jenkins_url'],  
                    'subnet_ids': ",".join([x.subnet_id for x in self.vpc.vpc.private_subnets]),
                    'security_group_ids': self.worker.worker_security_group.security_group_id,
                    'execution_role_arn': self.worker.worker_execution_role.role_arn,
                    'task_role_arn': self.worker.worker_task_role.role_arn,
                    'worker_log_group': self.worker.worker_logs_group.log_group_name,
                    'worker_log_stream_prefix': self.worker.worker_log_stream.log_stream_name
                },
                logging=ecs.LogDriver.aws_logs(
                    stream_prefix="Jenkinsleader",
                    log_retention=logs.RetentionDays.ONE_WEEK
                ),
            )

            self.jenkins_leader_task.default_container.add_mount_points(
                ecs.MountPoint(
                    container_path='/var/jenkins_home',
                    source_volume="efs_mount",
                    read_only=False
                )
            )

            self.jenkins_leader_task.default_container.add_port_mappings(
                ecs.PortMapping(
                    container_port=8080,
                    host_port=8080
                )
            )

            self.jenkins_leader_service = ecs.Ec2Service(
                self, "EC2leaderService",
                task_definition=self.jenkins_leader_task,
                cloud_map_options=ecs.CloudMapOptions(name="leader", dns_record_type=sd.DnsRecordType('A')),
                desired_count=1,
                min_healthy_percent=0,
                max_healthy_percent=100,
                enable_ecs_managed_tags=True,
                cluster=self.cluster.cluster,
            )

            self.target_group = self.listener.add_targets(
                "JenkinsleaderTarget",
                port=80,
                targets=[
                    self.jenkins_leader_service.load_balancer_target(
                        container_name=self.jenkins_leader_task.default_container.container_name,
                        container_port=8080,
                    )
                ],
                deregistration_delay=core.Duration.seconds(10)
            )

        # Opening port 5000 for leader <--> worker communications
        self.jenkins_leader_service.task_definition.default_container.add_port_mappings(
            ecs.PortMapping(container_port=50000, host_port=50000)
        )

        # Enable connection between leader and Worker
        self.jenkins_leader_service.connections.allow_from(
            other=self.worker.worker_security_group,
            port_range=ec2.Port(
                protocol=ec2.Protocol.TCP,
                string_representation='leader to Worker 50000',
                from_port=50000,
                to_port=50000
            )
        )

        # Enable connection between leader and Worker on 8080
        self.jenkins_leader_service.connections.allow_from(
            other=self.worker.worker_security_group,
            port_range=ec2.Port(
                protocol=ec2.Protocol.TCP,
                string_representation='leader to Worker 8080',
                from_port=8080,
                to_port=8080
            )
        )

        # IAM Statements to allow jenkins ecs plugin to talk to ECS as well as the Jenkins cluster #
        self.jenkins_leader_task.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:RegisterTaskDefinition",
                    "ecs:DeregisterTaskDefinition",
                    "ecs:ListClusters",
                    "ecs:DescribeContainerInstances",
                    "ecs:ListTaskDefinitions",
                    "ecs:DescribeTaskDefinition",
                    "ecs:DescribeTasks"
                ],
                resources=[
                    "*"
                ],
            )
        )

        self.jenkins_leader_task.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:ListContainerInstances"
                ],
                resources=[
                    self.cluster.cluster.cluster_arn
                ]
            )
        )

        self.jenkins_leader_task.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:RunTask"
                ],
                resources=[
                    "arn:aws:ecs:{0}:{1}:task-definition/fargate-workers*".format(
                        self.region,
                        self.account,
            )
                ]
            )
        )

        self.jenkins_leader_task.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:StopTask"
                ],
                resources=[
                    "arn:aws:ecs:{0}:{1}:task/*".format(
                        self.region,
                        self.account
                    )
                ],
                conditions={
                    "ForAnyValue:ArnEquals": {
                        "ecs:cluster": self.cluster.cluster.cluster_arn
                    }
                }
            )
        )

        self.jenkins_leader_task.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "iam:PassRole"
                ],
                resources=[
                    self.worker.worker_task_role.role_arn,
                    self.worker.worker_execution_role.role_arn
                ]
            )
        )
        # END OF JENKINS ECS PLUGIN IAM POLICIES #
