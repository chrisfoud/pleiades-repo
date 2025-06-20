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
                vpc_config.ISOLATED_SUBNET_MASK
            )
            
            # Add CloudFormation outputs for VPC ID
            CfnOutput(
                self, f"{vpc_config.VPV_ID}-id-output",
                value=vpc.vpc_id,
                description=f"VPC ID for {vpc_config.VPC_NAME}",
                export_name=f"{vpc_config.VPC_NAME}-id"
            )
        

    
    def create_vpc(self ,identifier ,vpc_name , vpc_cidr, vpc_maz_azs, nat_gw, public_subnet_mask, private_subnet_mask, isolated_subnet_mask):

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
        
        # Create Route Tables
        public_rt = ec2.CfnRouteTable(self, f"{identifier}-public-rt", vpc_id=self.vpc.vpc_id)
        ec2.CfnRoute(self, f"{identifier}-public-route", route_table_id=public_rt.ref, destination_cidr_block="0.0.0.0/0", gateway_id=self.vpc.internet_gateway_id)
        for i, subnet in enumerate(self.vpc.public_subnets):
            ec2.CfnSubnetRouteTableAssociation(self, f"{identifier}-pub-rt-assoc-{i}", route_table_id=public_rt.ref, subnet_id=subnet.subnet_id)
        
        private_rt = ec2.CfnRouteTable(self, f"{identifier}-private-rt", vpc_id=self.vpc.vpc_id)
        if nat_gw > 0:
            nat_gateway = ec2.CfnNatGateway(self, f"{identifier}-nat-gw", subnet_id=self.vpc.public_subnets[0].subnet_id, allocation_id=ec2.CfnEIP(self, f"{identifier}-eip").attr_allocation_id)
            ec2.CfnRoute(self, f"{identifier}-private-route", route_table_id=private_rt.ref, destination_cidr_block="0.0.0.0/0", nat_gateway_id=nat_gateway.ref)
        for i, subnet in enumerate(self.vpc.private_subnets):
            ec2.CfnSubnetRouteTableAssociation(self, f"{identifier}-priv-rt-assoc-{i}", route_table_id=private_rt.ref, subnet_id=subnet.subnet_id)
        
        isolated_rt = ec2.CfnRouteTable(self, f"{identifier}-isolated-rt", vpc_id=self.vpc.vpc_id)
        for i, subnet in enumerate(self.vpc.isolated_subnets):
            ec2.CfnSubnetRouteTableAssociation(self, f"{identifier}-iso-rt-assoc-{i}", route_table_id=isolated_rt.ref, subnet_id=subnet.subnet_id)
        
        # Create NACLs
        public_nacl = ec2.CfnNetworkAcl(self, f"{identifier}-public-nacl", vpc_id=self.vpc.vpc_id)
        ec2.CfnNetworkAclEntry(self, f"{identifier}-pub-nacl-http", network_acl_id=public_nacl.ref, rule_number=100, protocol=6, rule_action="allow", port_range=ec2.CfnNetworkAclEntry.PortRangeProperty(from_=80, to=80), cidr_block="0.0.0.0/0")
        ec2.CfnNetworkAclEntry(self, f"{identifier}-pub-nacl-https", network_acl_id=public_nacl.ref, rule_number=110, protocol=6, rule_action="allow", port_range=ec2.CfnNetworkAclEntry.PortRangeProperty(from_=443, to=443), cidr_block="0.0.0.0/0")
        ec2.CfnNetworkAclEntry(self, f"{identifier}-pub-nacl-out", network_acl_id=public_nacl.ref, rule_number=100, protocol=-1, rule_action="allow", cidr_block="0.0.0.0/0", egress=True)
        for i, subnet in enumerate(self.vpc.public_subnets):
            ec2.CfnSubnetNetworkAclAssociation(self, f"{identifier}-pub-nacl-assoc-{i}", network_acl_id=public_nacl.ref, subnet_id=subnet.subnet_id)
        
        private_nacl = ec2.CfnNetworkAcl(self, f"{identifier}-private-nacl", vpc_id=self.vpc.vpc_id)
        ec2.CfnNetworkAclEntry(self, f"{identifier}-priv-nacl-in", network_acl_id=private_nacl.ref, rule_number=100, protocol=-1, rule_action="allow", cidr_block=vpc_cidr)
        ec2.CfnNetworkAclEntry(self, f"{identifier}-priv-nacl-out", network_acl_id=private_nacl.ref, rule_number=100, protocol=-1, rule_action="allow", cidr_block="0.0.0.0/0", egress=True)
        for i, subnet in enumerate(self.vpc.private_subnets):
            ec2.CfnSubnetNetworkAclAssociation(self, f"{identifier}-priv-nacl-assoc-{i}", network_acl_id=private_nacl.ref, subnet_id=subnet.subnet_id)
        
        isolated_nacl = ec2.CfnNetworkAcl(self, f"{identifier}-isolated-nacl", vpc_id=self.vpc.vpc_id)
        ec2.CfnNetworkAclEntry(self, f"{identifier}-iso-nacl-in", network_acl_id=isolated_nacl.ref, rule_number=100, protocol=-1, rule_action="allow", cidr_block=vpc_cidr)
        ec2.CfnNetworkAclEntry(self, f"{identifier}-iso-nacl-out", network_acl_id=isolated_nacl.ref, rule_number=100, protocol=-1, rule_action="allow", cidr_block=vpc_cidr, egress=True)
        for i, subnet in enumerate(self.vpc.isolated_subnets):
            ec2.CfnSubnetNetworkAclAssociation(self, f"{identifier}-iso-nacl-assoc-{i}", network_acl_id=isolated_nacl.ref, subnet_id=subnet.subnet_id)
            
        # Return the VPC
        return self.vpc


