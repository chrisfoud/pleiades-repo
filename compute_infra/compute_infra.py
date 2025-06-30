from aws_cdk import (
    Stack,
    Tags,
    CfnOutput,
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

            # Store VPC data for later reference by ALB and EC2 resources
            vpcs[vpc_config.VPC_NAME] = {
                'vpc': vpc,
                'public_subnet_ids': public_subnet_ids,
                'private_subnet_ids': private_subnet_ids
            }

        # Create Application Load Balancers from configuration
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
            # Store ALB resources for EC2 instance association
            alb_target_groups[compute_config.ALB_NAME] = target_group
            alb_security_groups[compute_config.ALB_NAME] = alb_sg

        # Create EC2 instances from configuration
        for compute_config in config.EC2_LIST:
            vpc_data = vpcs[compute_config.EC2_VPC]
            instance = self.create_ec2(
                compute_config.EC2_NAME,
                vpc_data['vpc'],
                compute_config.EC2_VPC,
                compute_config.EC2_INSTANCE_TYPE,
                compute_config.AMI_REGION,
                compute_config.EC2_SUBNET_NAME,
                compute_config.EC2_AZ,
                compute_config.AMI_ID,
                compute_config.EC2_KEYPAIR,
                compute_config.EC2_ALB,
                alb_target_groups,
                alb_security_groups,
                compute_config.EC2_SG_ID
            )


    def importVPC(self, identifier, imported_vpc_id):
        """Import existing VPC by ID for use in compute resources"""
        self.vpc_lookup = ec2.Vpc.from_lookup(
            self, identifier,
            vpc_id = imported_vpc_id,
        )
        return self.vpc_lookup

###############################################################################################################
# ALB - Application Load Balancer Creation
###############################################################################################################

    def create_alb(self, alb_name, vpc, public_subnet_ids,vpc_name, sg_id=None, certificate_arn=None, SG_desc=None):
        """Create Application Load Balancer with target group and security group"""

        # Create or import security group for ALB
        if sg_id:
            # Use existing security group
            alb_security_group = ec2.SecurityGroup.from_security_group_id(
                self, 
                f"{alb_name}-imported-sg", 
                sg_id
            )
        else:
            # Create new security group with HTTP/HTTPS access
            alb_security_group = ec2.SecurityGroup(
                self,
                f"{alb_name}-sg",
                vpc=vpc,
                allow_all_outbound=True,
                description=f"Security group for {alb_name}"
            )
            # Allow inbound HTTP traffic
            alb_security_group.add_ingress_rule(
                ec2.Peer.any_ipv4(),
                ec2.Port.tcp(80),
                "Allow HTTP traffic"
            )
            # Allow inbound HTTPS traffic
            alb_security_group.add_ingress_rule(
                ec2.Peer.any_ipv4(),
                ec2.Port.tcp(443),
                "Allow HTTPS traffic"
            )
        

        # Build list of public subnets for ALB deployment
        public_subnets = []
        if public_subnet_ids:
            for i, subnet_id in enumerate(public_subnet_ids):
                # Lookup availability zone from SSM parameter
                az = ssm.StringParameter.value_from_lookup(
                    self, 
                    f"/{vpc_name}/public-subnet-{i+1}/az"
                )
                # Create subnet reference for ALB
                public_subnets.append(
                    ec2.Subnet.from_subnet_attributes(
                        self, 
                        f"{alb_name}-PublicSubnet{i+1}",
                        subnet_id=subnet_id,
                        availability_zone=az
                    )
                )


        # Create internet-facing Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(
            self,
            alb_name,
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
            vpc_subnets=ec2.SubnetSelection(subnets=public_subnets)
        )
        Tags.of(alb).add("Name", alb_name)

        # Create target group for EC2 instances with health checks
        target_group = elbv2.ApplicationTargetGroup(
            self,
            f"{alb_name}-tg",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",                              # Health check endpoint
                protocol=elbv2.Protocol.HTTP,
                port="80",
                interval=Duration.seconds(30),          # Check every 30 seconds
                timeout=Duration.seconds(10),           # 10 second timeout
                healthy_threshold_count=2,              # 2 successful checks = healthy
                unhealthy_threshold_count=5             # 5 failed checks = unhealthy
            )
        )
        

        # Add HTTP listener to forward traffic to target group
        http_listener = alb.add_listener(
            "HttpListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_action=elbv2.ListenerAction.forward([target_group])
        )
        

        # Add HTTPS listener if SSL certificate is provided
        if certificate_arn:
            https_listener = alb.add_listener(
                "HttpsListener",
                port=443,
                certificates=[elbv2.ListenerCertificate(certificate_arn)],
                protocol=elbv2.ApplicationProtocol.HTTPS,
                default_action=elbv2.ListenerAction.forward([target_group])
            )
        

        # Store ALB ARN in SSM Parameter Store for reference
        ssm.StringParameter(
            self,
            f"{alb_name}-param",
            parameter_name=f"/{alb_name}/arn",
            string_value=alb.load_balancer_arn,
            description=f"ALB ARN for {alb_name}"
        )
        
        # Store Target Group ARN in SSM Parameter Store
        ssm.StringParameter(
            self,
            f"{alb_name}-tg-param",
            parameter_name=f"/{alb_name}/target-group/arn",
            string_value=target_group.target_group_arn,
            description=f"Target Group ARN for {alb_name}"
        )
        
        return alb, target_group, alb_security_group
        
###############################################################################################################
# EC2 - Elastic Compute Cloud Instance Creation
###############################################################################################################

    def create_ec2(self,ec2_name, vpc, vpc_name, instance_type, ami_region, subnet_name, az, ami_id, key_name, ec2_alb, alb_target_groups, alb_security_groups, sg_id=None):
        """Create EC2 instance with IAM role, security group, and optional ALB association"""
        # Create IAM role for EC2 instance with SSM access
        ec2_role = iam.Role(
            self,
            f"{ec2_name}-role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
            ]
        )
        
        # Create instance profile for the IAM role
        instance_profile = iam.CfnInstanceProfile(
            self,
            f"{ec2_name}-instance-profile",
            roles=[ec2_role.role_name]
        )
        
        # Create or import security group for EC2 instance
        if sg_id:
            # Import existing security group by ID or name
            if sg_id.startswith('sg-'):
                ec2_security_group = ec2.SecurityGroup.from_security_group_id(
                    self, 
                    f"{ec2_name}-imported-sg", 
                    sg_id
                )
            else:
                ec2_security_group = ec2.SecurityGroup.from_lookup_by_name(
                    self,
                    f"{ec2_name}-imported-sg",
                    sg_id,
                    vpc
                )
        else:
            # Create new security group with RDP and ALB access
            ec2_security_group = ec2.SecurityGroup(
                self,
                f"{ec2_name}-sg",
                vpc=vpc,
                allow_all_outbound=True,
                description=f"Security group for {ec2_name}"
            )
            
            # Allow RDP access for Windows instances
            ec2_security_group.add_ingress_rule(
                ec2.Peer.any_ipv4(),
                ec2.Port.tcp(3389),
                "Allow RDP traffic"
            )
            
            # Allow HTTP traffic from ALB if associated
            if ec2_alb is not None:
                alb_sg = alb_security_groups[ec2_alb]
                ec2_security_group.add_ingress_rule(
                     ec2.Peer.security_group_id(alb_sg.security_group_id),
                    ec2.Port.tcp(80),
                    "Allow HTTP traffic from ALB"
                )

        # Lookup subnet ID from SSM Parameter Store by name and AZ
        subnet_id = ssm.StringParameter.value_from_lookup(
            self,
            f"/{vpc_name}/{subnet_name}-subnet/{az}/id"
        )
        
        # Create subnet reference for EC2 instance placement
        subnet = ec2.Subnet.from_subnet_attributes(
            self,
            f"{ec2_name}-subnet",
            subnet_id=subnet_id,
            availability_zone=az
        )

        # Configure user data to install IIS web server on Windows
        user_data = ec2.UserData.for_windows()
        user_data.add_commands(
            "powershell -Command \"Install-WindowsFeature -name Web-Server -IncludeManagementTools\""
        )

        # Create EC2 instance with specified configuration
        instance = ec2.Instance(
                self,
                ec2_name,
                vpc=vpc,
                instance_type=ec2.InstanceType(instance_type),
                machine_image=ec2.MachineImage.generic_windows({ami_region: ami_id}),
                security_group=ec2_security_group,
                vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
                key_name=key_name,                      # SSH key for access
                user_data=user_data,                    # Bootstrap script
                role=ec2_role                           # IAM role for permissions
            )

        # Register instance with ALB target group if specified
        if ec2_alb is not None:
            target_group = alb_target_groups[ec2_alb]
            target_group.add_target(targets.InstanceTarget(instance))

        # Add name tag to instance
        Tags.of(instance).add("Name", ec2_name)

        return instance