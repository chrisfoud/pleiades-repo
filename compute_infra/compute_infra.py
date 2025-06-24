from aws_cdk import (
    Stack,
    Tags,
    Duration,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as targets,
    aws_iam as iam,
    aws_ssm as ssm,
)
from constructs import Construct
from . import config
from network_infra import config as network_config

class ComputeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        
        super().__init__(scope, construct_id, **kwargs)



        vpcs = {}
        alb_target_groups = {}
        alb_security_groups = {}
        
        for i, vpc_config in enumerate(network_config.VPC_LIST):
            vpc_id = ssm.StringParameter.value_from_lookup(self, f"/{vpc_config.VPC_NAME}/id")
            vpc = self.importVPC(f'vpc-{i}', vpc_id)
            
            # Get public subnets for this VPC
            public_subnet_ids = []
            for j in range(1, 4):
                subnet_id = ssm.StringParameter.value_from_lookup(
                    self, 
                    f"/{vpc_config.VPC_NAME}/public-subnet-{j}/id"
                )
                public_subnet_ids.append(subnet_id)

            # Get private subnets for this VPC
            private_subnet_ids = []
            for j in range(1, 4):
                subnet_id = ssm.StringParameter.value_from_lookup(
                    self, 
                    f"/{vpc_config.VPC_NAME}/private-subnet-{j}/id"
                )
                private_subnet_ids.append(subnet_id)

            vpcs[vpc_config.VPC_NAME] = {
                'vpc': vpc,
                'public_subnet_ids': public_subnet_ids,
                'private_subnet_ids': private_subnet_ids
            }

        
        for compute_config in config.ALB_LIST:
            vpc_data = vpcs[compute_config.ALB_VPC]
            alb, target_group, alb_sg= self.create_alb(
                compute_config.ALB_NAME,
                vpc_data['vpc'],
                vpc_data['public_subnet_ids'],
                compute_config.ALB_VPC,
                compute_config.ALB_SG_ID,
                compute_config.CERTIFICATE_ARN,
                compute_config.SG_DESC
            )
            alb_target_groups[compute_config.ALB_NAME] = target_group
            alb_security_groups[compute_config.ALB_NAME] = alb_sg

        for compute_config in config.EC2_LIST:
            vpc_data = vpcs[compute_config.EC2_VPC]
            instance = self.create_ec2(
                compute_config.EC2_NAME,
                vpc_data['vpc'],
                vpc_data['private_subnet_ids'],
                compute_config.EC2_VPC,
                compute_config.EC2_INSTANCE_TYPE,
                compute_config.AMI_REGION,
                compute_config.EC2_SUBNET,
                compute_config.AMI_ID,
                compute_config.EC2_KEYPAIR,
                compute_config.EC2_ALB,
                alb_target_groups,
                alb_security_groups
            )


    def importVPC(self, identifier, imported_vpc_id):
        self.vpc_lookup = ec2.Vpc.from_lookup(
            self, identifier,
            vpc_id = imported_vpc_id,
        )
        return self.vpc_lookup

###############################################################################################################
# ALB
###############################################################################################################

    def create_alb(self, alb_name, vpc, public_subnet_ids,vpc_name, sg_id=None, certificate_arn=None, SG_desc=None):

        if sg_id:
            alb_security_group = ec2.SecurityGroup.from_security_group_id(
                self, 
                f"{alb_name}-imported-sg", 
                sg_id
            )
        else:
            alb_security_group = ec2.SecurityGroup(
                self,
                f"{alb_name}-sg",
                vpc=vpc,
                allow_all_outbound=True,
                description=f"Security group for {alb_name}"
            )
            alb_security_group.add_ingress_rule(
                ec2.Peer.any_ipv4(),
                ec2.Port.tcp(80),
                "Allow HTTP traffic"
            )
            alb_security_group.add_ingress_rule(
                ec2.Peer.any_ipv4(),
                ec2.Port.tcp(443),
                "Allow HTTPS traffic"
            )
        

        public_subnets = []
        if public_subnet_ids:
            for i, subnet_id in enumerate(public_subnet_ids):
                az = ssm.StringParameter.value_from_lookup(
                    self, 
                    f"/{vpc_name}/public-subnet-{i+1}/az"
                )
                public_subnets.append(
                    ec2.Subnet.from_subnet_attributes(
                        self, 
                        f"{alb_name}-PublicSubnet{i+1}",
                        subnet_id=subnet_id,
                        availability_zone=az
                    )
                )


        alb = elbv2.ApplicationLoadBalancer(
            self,
            alb_name,
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
            vpc_subnets=ec2.SubnetSelection(subnets=public_subnets)
        )
        Tags.of(alb).add("Name", alb_name)

        target_group = elbv2.ApplicationTargetGroup(
            self,
            f"{alb_name}-tg",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                protocol=elbv2.Protocol.HTTP,
                port="80",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                healthy_threshold_count=2,
                unhealthy_threshold_count=5
            )
        )
        

        http_listener = alb.add_listener(
            "HttpListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_action=elbv2.ListenerAction.forward([target_group])
        )
        

        if certificate_arn:
            https_listener = alb.add_listener(
                "HttpsListener",
                port=443,
                certificates=[elbv2.ListenerCertificate(certificate_arn)],
                protocol=elbv2.ApplicationProtocol.HTTPS,
                default_action=elbv2.ListenerAction.forward([target_group])
            )
        

        ssm.StringParameter(
            self,
            f"{alb_name}-param",
            parameter_name=f"/{alb_name}/arn",
            string_value=alb.load_balancer_arn,
            description=f"ALB ARN for {alb_name}"
        )
        

        ssm.StringParameter(
            self,
            f"{alb_name}-tg-param",
            parameter_name=f"/{alb_name}/target-group/arn",
            string_value=target_group.target_group_arn,
            description=f"Target Group ARN for {alb_name}"
        )
        
        return alb, target_group, alb_security_group
        
###############################################################################################################
# EC2
###############################################################################################################

    def create_ec2(self,ec2_name, vpc, private_subnet_ids,vpc_name, instance_type, ami_region, specific_subnet, ami_id, key_name, ec2_alb, alb_target_groups, alb_security_groups):
        ec2_role = iam.Role(
            self,
            f"{ec2_name}-role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
            ]
        )
        
        instance_profile = iam.CfnInstanceProfile(
            self,
            f"{ec2_name}-instance-profile",
            roles=[ec2_role.role_name]
        )
        ec2_security_group = ec2.SecurityGroup(
            self,
            f"{ec2_name}-sg",
            vpc=vpc,
            allow_all_outbound=True,
            description=f"Security group for {ec2_name}"
        )
        
        ec2_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(3389),
            "Allow RDP traffic"
        )
        
        if ec2_alb is not None:
            alb_sg = alb_security_groups[ec2_alb]
            ec2_security_group.add_ingress_rule(
                 ec2.Peer.security_group_id(alb_sg.security_group_id),
                ec2.Port.tcp(80),
                "Allow HTTP traffic from ALB"
            )

        private_subnets = []
        if specific_subnet and private_subnet_ids:
            # Use specific subnet
            subnet_index = int(specific_subnet) - 1
            subnet_id = private_subnet_ids[subnet_index]
            az = ssm.StringParameter.value_from_lookup(
                self, 
                f"/{vpc_name}/private-subnet-{specific_subnet}/az"
            )
            private_subnets.append(
                ec2.Subnet.from_subnet_attributes(
                    self, 
                    f"{ec2_name}-PrivateSubnet{specific_subnet}",
                    subnet_id=subnet_id,
                    availability_zone=az
                )
            )
        elif private_subnet_ids:
            # Use all subnets (random placement)
            for i, subnet_id in enumerate(private_subnet_ids):
                az = ssm.StringParameter.value_from_lookup(
                    self, 
                    f"/{vpc_name}/private-subnet-{i+1}/az"
                )
                private_subnets.append(
                    ec2.Subnet.from_subnet_attributes(
                        self, 
                        f"{ec2_name}-PrivateSubnet{i+1}",
                        subnet_id=subnet_id,
                        availability_zone=az
                    )
                )

        user_data = ec2.UserData.for_windows()
        user_data.add_commands(
            "powershell -Command \"Install-WindowsFeature -name Web-Server -IncludeManagementTools\""
        )

        instance = ec2.Instance(
                self,
                ec2_name,
                vpc=vpc,
                instance_type=ec2.InstanceType(instance_type),
                machine_image=ec2.MachineImage.generic_windows({ami_region: ami_id}),
                security_group=ec2_security_group,
                vpc_subnets=ec2.SubnetSelection(subnets=private_subnets),
                key_name=key_name,
                user_data=user_data,
                role=ec2_role
            )

        if ec2_alb is not None:
            target_group = alb_target_groups[ec2_alb]
            target_group.add_target(targets.InstanceTarget(instance))

        Tags.of(instance).add("Name", ec2_name)

        return instance