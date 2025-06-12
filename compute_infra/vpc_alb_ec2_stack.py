# vpc_alb_ec2_stack.py
from aws_cdk import (
    Stack,
    Tags,
    CfnOutput,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
)
from constructs import Construct
from . import config # Import from the same directory

class VpcAlbEc2Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Retrieve configuration from the config file
        app_config = config.AppInfrastructureConfig

        # 1. Create VPC
        # The VPC will span across 'MAX_AZS' availability zones and create public subnets
        # suitable for the ALB and private subnets for the EC2 instances.
        self.vpc = ec2.Vpc(
            self,
            app_config.VPC.VPC_CFN_ID,
            vpc_name=app_config.VPC.VPC_NAME,
            max_azs=app_config.VPC.MAX_AZS,
            nat_gateways=app_config.VPC.MAX_AZS, # One NAT Gateway per public subnet (AZ)
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, # Instances need egress to download packages
                    cidr_mask=24
                )
            ]
        )
        Tags.of(self.vpc).add("Name", app_config.VPC.VPC_NAME)
        Tags.of(self.vpc).add("Description", "VPC for web application with ALB and EC2")

        # 2. Create Security Group for EC2 instances
        # This security group will allow inbound traffic from the ALB's security group
        # on the configured listener port (e.g., HTTP 80).
        self.ec2_security_group = ec2.SecurityGroup(
            self,
            "EC2SecurityGroup",
            vpc=self.vpc,
            description="Allow HTTP(S) traffic from ALB",
            allow_all_outbound=True # Allow instances to reach the internet for updates/downloads
        )
        # Add a self-referencing rule to allow instances within the security group to communicate
        self.ec2_security_group.connections.allow_from(
            self.ec2_security_group,
            ec2.Port.all_traffic(),
            "Allow internal communication within EC2 instances"
        )
        Tags.of(self.ec2_security_group).add("Name", f"{app_config.VPC.VPC_NAME}-EC2-SG")

        # 3. Create EC2 Instances
        # Iterate through the EC2_INSTANCES list from config and provision each instance.
        self.ec2_instances = []
        for instance_config in app_config.EC2_INSTANCES:
            # Create IAM Role for EC2 Instance to allow it to be managed by SSM (optional but good practice)
            instance_role = iam.Role(
                self,
                f"EC2InstanceRole-{instance_config.INSTANCE_CFN_ID}",
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
                ]
            )

            # Create the EC2 instance
            instance = ec2.Instance(
                self,
                instance_config.INSTANCE_CFN_ID,
                instance_type=instance_config.INSTANCE_TYPE,
                machine_image=instance_config.MACHINE_IMAGE,
                vpc=self.vpc,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                security_group=self.ec2_security_group,
                role=instance_role,
                user_data=ec2.UserData.custom(instance_config.USER_DATA_SCRIPT) if instance_config.USER_DATA_SCRIPT else None,
                # Optionally add a key pair for SSH access, but not required for simple web server
                # key_name="YourKeyPairName"
            )
            Tags.of(instance).add("Name", instance_config.INSTANCE_NAME)
            self.ec2_instances.append(instance)

        # 4. Create Security Group for ALB
        # This security group will allow inbound HTTP/HTTPS traffic from anywhere.
        self.alb_security_group = ec2.SecurityGroup(
            self,
            "ALBSecurityGroup",
            vpc=self.vpc,
            description="Allow HTTP(S) traffic to ALB",
            allow_all_outbound=True
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(app_config.ALB.LISTENER_PORT),
            "Allow HTTP(S) traffic from anywhere"
        )
        Tags.of(self.alb_security_group).add("Name", f"{app_config.VPC.VPC_NAME}-ALB-SG")

        # 5. Allow ALB to send traffic to EC2 instances
        # This rule ensures the ALB can communicate with the instances in their security group.
        self.ec2_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.tcp(app_config.ALB.LISTENER_PORT),
            description="Allow traffic from ALB"
        )

        # 6. Create Application Load Balancer (ALB)
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            app_config.ALB.ALB_CFN_ID,
            vpc=self.vpc,
            internet_facing=True, # Make it internet-facing
            security_group=self.alb_security_group,
            load_balancer_name=app_config.ALB.ALB_NAME
        )
        Tags.of(self.alb).add("Name", app_config.ALB.ALB_NAME)
        Tags.of(self.alb).add("Description", "ALB for web application")


        # 7. Create Target Group
        # A target group registers the EC2 instances so the ALB can forward requests to them.
        self.target_group = elbv2.ApplicationTargetGroup(
            self,
            "ApplicationTargetGroup",
            vpc=self.vpc,
            port=app_config.ALB.LISTENER_PORT,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[] # Initialize with empty targets, we'll add them separately
        )
        
        # Register EC2 instances with the target group
        for i, instance in enumerate(self.ec2_instances):
            self.target_group.add_target(elbv2.InstanceTarget(instance))
            
        Tags.of(self.target_group).add("Name", f"{app_config.ALB.ALB_NAME}-TG")


        # 8. Add Listener to ALB
        # The listener checks for connection requests using the protocol and port that you configure.
        self.listener = self.alb.add_listener(
            "ALBListener",
            port=app_config.ALB.LISTENER_PORT,
            open=True # Automatically adds security group rule for the listener port
        )
        # Forward all requests from the listener to our target group.
        self.listener.add_target_groups("DefaultTargetGroup",
            target_groups=[self.target_group]
        )

        # Output the ALB DNS Name
        CfnOutput(
            self,
            "ALBDnsName",
            value=self.alb.load_balancer_dns_name,
            description="The DNS name of the Application Load Balancer"
        )

        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="The ID of the VPC"
        )
