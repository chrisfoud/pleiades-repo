from aws_cdk import (
    Stack,
    Tags,
    CfnOutput,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as targets,
    aws_iam as iam,
    aws_ssm as ssm,
)
from constructs import Construct
from . import config

class NetworkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        
        super().__init__(scope, construct_id, **kwargs)

        
        for vpc_config in config.VPC_LIST:
            vpc = self.create_vpc(
                vpc_config.VPV_ID,
                vpc_config.VPC_NAME,
                vpc_config.VPC_CIDR,
                vpc_config.VPC_MAX_AZS,
                vpc_config.NAT_GATEWAY,
                vpc_config.PUBLIC_SUBNET_MASK,
                vpc_config.PRIVATE_SUBNET_MASK,
                vpc_config.ISOLATED_SUBNET_MASK,
                vpc_config.custom_subnets
            )
            
            # Add CloudFormation outputs for VPC ID
            CfnOutput(
                self, f"{vpc_config.VPV_ID}-id-output",
                value=vpc.vpc_id,
                description=f"VPC ID for {vpc_config.VPC_NAME}",
                export_name=f"{vpc_config.VPC_NAME}-id"
            )
        

    
    def create_vpc(self, identifier, vpc_name, vpc_cidr, vpc_maz_azs, nat_gw, public_subnet_mask, private_subnet_mask, isolated_subnet_mask, custom_subnets=None):

        self.vpc = ec2.Vpc(
            self, identifier,
            vpc_name=vpc_name,
            ip_addresses=ec2.IpAddresses.cidr(vpc_cidr),
            max_azs= vpc_maz_azs,
            nat_gateways= nat_gw,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask= public_subnet_mask
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, # Instances need egress to download packages
                    cidr_mask= private_subnet_mask
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask= isolated_subnet_mask
                )
            ]
        )
        Tags.of(self.vpc).add("Name", vpc_name)
        
        # Add custom subnets
        if custom_subnets:
            for subnet_config in custom_subnets:
                subnet = ec2.Subnet(
                    self, f"{identifier}-custom-{subnet_config['name']}",
                    vpc_id=self.vpc.vpc_id,
                    cidr_block=subnet_config['cidr'],
                    availability_zone=subnet_config['az']
                )
                
                # Route table association based on type
                if subnet_config['type'] == 'public':
                    # Associate with public route table (has IGW route)
                    for rt in self.vpc.public_subnets[0].route_table:
                        ec2.CfnSubnetRouteTableAssociation(
                            self, f"{identifier}-{subnet_config['name']}-rt-assoc",
                            subnet_id=subnet.subnet_id,
                            route_table_id=rt.route_table_id
                        )
                elif subnet_config['type'] == 'private':
                    # Associate with private route table (has NAT route)
                    for rt in self.vpc.private_subnets[0].route_table:
                        ec2.CfnSubnetRouteTableAssociation(
                            self, f"{identifier}-{subnet_config['name']}-rt-assoc",
                            subnet_id=subnet.subnet_id,
                            route_table_id=rt.route_table_id
                        )
                elif subnet_config['type'] == 'isolated':
                    # Create isolated route table (no internet routes)
                    isolated_rt = ec2.RouteTable(
                        self, f"{identifier}-{subnet_config['name']}-rt",
                        vpc=self.vpc
                    )
                    ec2.CfnSubnetRouteTableAssociation(
                        self, f"{identifier}-{subnet_config['name']}-rt-assoc",
                        subnet_id=subnet.subnet_id,
                        route_table_id=isolated_rt.route_table_id
                    )



        # Create SSM parameters for VPC ID
        ssm.StringParameter(
            self, f"{identifier}-vpc-id-param",
            parameter_name=f"/{vpc_name}/id",
            string_value=self.vpc.vpc_id,
            description=f"VPC ID for {vpc_name}"
        )
        
        # Create SSM parameters for public subnet IDs
        for i, subnet in enumerate(self.vpc.public_subnets):
            ssm.StringParameter(
                self, f"{identifier}-public-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/public-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Public Subnet {i+1} ID for {vpc_name}"
            )
            ssm.StringParameter(
                self, f"{identifier}-public-subnet-{i+1}-az-param",
                parameter_name=f"/{vpc_name}/public-subnet-{i+1}/az",
                string_value=subnet.availability_zone,
                description=f"Public Subnet {i+1} AZ for {vpc_name}"
            )
        
        # Create SSM parameters for private subnet IDs
        for i, subnet in enumerate(self.vpc.private_subnets):
            ssm.StringParameter(
                self, f"{identifier}-private-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/private-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Private Subnet {i+1} ID for {vpc_name}"
            )
            ssm.StringParameter(
                self, f"{identifier}-private-subnet-{i+1}-az-param",
                parameter_name=f"/{vpc_name}/private-subnet-{i+1}/az",
                string_value=subnet.availability_zone,
                description=f"Private Subnet {i+1} AZ for {vpc_name}"
            )
        
        # Create SSM parameters for isolated subnet IDs
        for i, subnet in enumerate(self.vpc.isolated_subnets):
            ssm.StringParameter(
                self, f"{identifier}-isolated-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/isolated-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Isolated Subnet {i+1} ID for {vpc_name}"
            )

        # Return the VPC
        return self.vpc


