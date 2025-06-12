from aws_cdk import (
    Stack,
    aws_elasticbeanstalk as elasticbeanstalk,
    aws_iam as iam,
    CfnOutput,
    CfnTag,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    Tags,
)
from constructs import Construct
from compute_infra import config

class EC2ALBStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(self, "EC2ALBVPC",
            max_azs=2,  # Use 2 Availability Zones
            nat_gateways=1,  # Create a NAT Gateway for private subnets
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # Create a security group for the EC2 instances
        instance_sg = ec2.SecurityGroup(self, "InstanceSG",
            vpc=vpc,
            description="Security group for EC2 instances",
            allow_all_outbound=True
        )
        
        # Allow HTTP traffic from the ALB to the instances
        instance_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from ALB"
        )

        # Create a security group for the ALB
        alb_sg = ec2.SecurityGroup(self, "ALBSG",
            vpc=vpc,
            description="Security group for ALB",
            allow_all_outbound=True
        )
        
        # Allow HTTP traffic from anywhere to the ALB
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from internet"
        )

        # Create an Auto Scaling Group
        asg = autoscaling.AutoScalingGroup(self, "ASG",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
            security_group=instance_sg,
            min_capacity=2,
            max_capacity=4,
            desired_capacity=2,
        )
        
        # Add user data to install a simple web server
        asg.add_user_data(
            "yum update -y",
            "yum install -y httpd",
            "systemctl start httpd",
            "systemctl enable httpd",
            "echo '<html><body><h1>Hello from EC2 instance</h1></body></html>' > /var/www/html/index.html"
        )

        # Create an Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(self, "ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )

        # Add a listener to the ALB
        listener = alb.add_listener("Listener",
            port=80,
            open=True  # Allow connections on port 80
        )

        # Add the ASG as a target to the ALB
        listener.add_targets("ApplicationFleet",
            port=80,
            targets=[asg]
        )

        # Output the ALB DNS name
        CfnOutput(self, "LoadBalancerDNS",
            value=alb.load_balancer_dns_name,
            description="DNS name of the load balancer"
        )

class BeanstalkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)