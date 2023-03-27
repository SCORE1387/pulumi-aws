import pulumi
from pulumi_aws import ec2, get_availability_zones, lb

## VPC

vpc = ec2.Vpc(
    'pulumi-vpc',
    cidr_block='10.10.0.0/16',
    instance_tenancy='default',
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        'Name': 'pulumi-vpc',
    },
)

igw = ec2.InternetGateway(
    'pulumi-vpc-ig',
    vpc_id=vpc.id,
    tags={
        'Name': 'pulumi-vpc-ig',
    },
)

route_table = ec2.RouteTable(
    'pulumi-vpc-rt',
    vpc_id=vpc.id,
    routes=[ec2.RouteTableRouteArgs(
        cidr_block='0.0.0.0/0',
        gateway_id=igw.id,
    )],
    tags={
        'Name': 'pulumi-vpc-rt',
    },
)

## Subnets, one for each AZ in a region

zones = get_availability_zones()
subnet_ids = []

for zone in zones.names:
    vpc_subnet = ec2.Subnet(
        f'pulumi-vpc-subnet-{zone}',
        assign_ipv6_address_on_creation=False,
        vpc_id=vpc.id,
        map_public_ip_on_launch=True,
        cidr_block=f'10.10.{len(subnet_ids)}.0/24',
        availability_zone=zone,
        tags={
            'Name': f'pulumi-vpc-subnet-{zone}',
        },
    )
    ec2.RouteTableAssociation(
        f'pulumi-vpc-rt-association-{zone}',
        route_table_id=route_table.id,
        subnet_id=vpc_subnet.id,
    )
    subnet_ids.append(vpc_subnet.id)

## Security Groups

alb_sg = ec2.SecurityGroup(
	"pulumi-alb-http-sg",
	description="Allow HTTP/HTTPS traffic to ALB",
    vpc_id=vpc.id,
	ingress=[
        ec2.SecurityGroupIngressArgs(
            cidr_blocks=['0.0.0.0/0'],
            from_port=443,
            to_port=443,
            protocol='tcp',
            description='Allow HTTPS'
        ),
        ec2.SecurityGroupIngressArgs(
            cidr_blocks=['0.0.0.0/0'],
            from_port=80,
            to_port=80,
            protocol='tcp',
            description='Allow HTTP'
        ),
    ],
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol='-1',
            from_port=0,
            to_port=0,
            cidr_blocks=['0.0.0.0/0'],
        )
    ],
)

asg_sg = ec2.SecurityGroup(
	"pulumi-asg-http-sg",
	description="Allow HTTP/HTTPS traffic from ALB to ASG Instances",
    vpc_id=vpc.id,
	ingress=[
        ec2.SecurityGroupIngressArgs(
            security_groups=[alb_sg.id],
            from_port=443,
            to_port=443,
            protocol='tcp',
            description='Allow HTTPS'
        ),
        ec2.SecurityGroupIngressArgs(
            security_groups=[alb_sg.id],
            from_port=80,
            to_port=80,
            protocol='tcp',
            description='Allow HTTP'
        ),
    ],
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol='-1',
            from_port=0,
            to_port=0,
            cidr_blocks=['0.0.0.0/0'],
        )
    ],
)

allow_ssh_sg = ec2.SecurityGroup(
	"pulumi-allow-ssh-sg",
	description="Allow SSH traffic",
    vpc_id=vpc.id,
	ingress=[
        ec2.SecurityGroupIngressArgs(
            cidr_blocks=['0.0.0.0/0'],
            from_port=22,
            to_port=22,
            protocol='tcp',
            description='Allow SSH'
        ),
    ],
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol='-1',
            from_port=0,
            to_port=0,
            cidr_blocks=['0.0.0.0/0'],
        )
    ],
)
