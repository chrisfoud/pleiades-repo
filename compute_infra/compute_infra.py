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
            vpc_data = vpcs[compute_config.VPC_NAME]
            alb = self.create_alb(
                compute_config.ALB_NAME,
                vpc_data['vpc'],
                vpc_data['public_subnet_ids'],
                compute_config.ALB_SG_ID,
                compute_config.CERTIFICATE_ARN,
                compute_config.SG_DESC
            )              

    def importVPC(self, identifier, imported_vpc_id):
        self.vpc_lookup = ec2.Vpc.from_lookup(
            self, identifier,
            vpc_id = imported_vpc_id,
        )
        return self.vpc_lookup

    def create_alb(self, alb_name, vpc, public_subnet_ids, sg_id=None, certificate_arn=None, SG_desc=None):

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
                public_subnets.append(ec2.Subnet.from_subnet_id(self, f"PublicSubnet{i+1}", subnet_id))

        alb = elbv2.ApplicationLoadBalancer(
            self,
            alb_name,
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
            vpc_subnets=ec2.SubnetSelection(subnets=public_subnets)
        )
        tag.of(alb, "Name", alb_name)

        target_group = elbv2.ApplicationTargetGroup(
            self,
            f"{alb_name}-tg",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
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
        
        return alb, target_group
        
        # def create_ec2(self, instance_id, instance_name, instance_type, vpc_id, subnet_id, sg_id, key_name, user_data, role_name, role_policy, role_policy_name, role_policy_desc):

        #     # Create an IAM role for the EC2 instance
        #     instance_role = iam.Role(
        #         self,
        #         role_name,
        #         assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        #         role_name=role_name,
        #     )

        #     # Add a policy to the IAM role
        #     instance_role.add_managed_policy(
        #         iam.ManagedPolicy.from_aws_managed_policy_name(role_policy)
        #     )

        #     # Create an EC2 instance
        #     instance = ec2.Instance(
        #         self,
        #         instance_id,
        #         instance_type=ec2.InstanceType(instance_type),
        #         machine_image=ec2.MachineImage.latest_amazon_linux2(),
        #         vpc=ec2.Vpc.from_lookup(self, "ImportedVPC", vpc_id),
        #         vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #         security_group=ec2.SecurityGroup.from_security_group_id(self, sg_id, sg_id),
        #         key_name=key_name,
        #         user_data=ec2.UserData.custom(user_data),
        #         role=instance_role
        #     )

        #     # Create an SSM parameter for the EC2 instance ID
        #     ssm.StringParameter(
        #         self,
        #         f"{instance_name}-param",
        #         parameter_name=f"/{instance_name}/id",
        #         string_value=instance.instance_id,
        #         description=f"EC2 Instance ID for {instance_name}"
        #     )

        #     return instance