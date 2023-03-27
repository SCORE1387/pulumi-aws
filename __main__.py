"""An AWS Python Pulumi program"""

import base64
import pulumi
from pulumi_aws import lb, ec2, autoscaling, GetAmiFilterArgs
import vpc

config = pulumi.Config();
instance_type = config.require('instance_type');
ami_id = config.require('ami_id')
asg_config = config.require_object("asg")

## Load Balancer

alb_target_group = lb.TargetGroup(
    "pulumi-alb-target-group",
	port=80,
	protocol="HTTP",
	target_type="instance",
	vpc_id=vpc.vpc.id
)

alb = lb.LoadBalancer(
    "pulumi-alb",
    internal=False,
    load_balancer_type="application",
    ip_address_type="ipv4",
    security_groups=[vpc.alb_sg.id],
    subnets=vpc.subnet_ids,
    tags={
        'Name': 'pulumi-alb',
    },
)

alb_listener = lb.Listener("pulumi-alb-listener",
    load_balancer_arn=alb.arn,
    port=80,
    protocol="HTTP",
    default_actions=[
        lb.ListenerDefaultActionArgs(
            type="forward",
            target_group_arn=alb_target_group.arn,
        )
    ]
)

## Auto Scaling Group

# ami = ec2.get_ami(
#     most_recent=True,
#     owners=["137112412989"],
#     filters=[
#         GetAmiFilterArgs(name="name", values=["amzn-ami-hvm-*"])
#     ]
# )

user_data = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello World from $(hostname -f)</h1>" > /var/www/html/index.html
"""
user_data_base64 = base64.b64encode(user_data.encode()).decode()

asg_launch_template = ec2.LaunchTemplate(
    "pulumi-asg-launch-template",
    name_prefix="pulumi-instance",
    image_id=ami_id,
    instance_type=instance_type,
    user_data=user_data_base64,
    network_interfaces=[
        ec2.LaunchTemplateNetworkInterfaceArgs(
            security_groups=[vpc.asg_sg.id],
            associate_public_ip_address="true",
        )
    ],
)

asg = autoscaling.Group(
    "pulumi-asg",
    desired_capacity=asg_config.get("desired"),
    min_size=asg_config.get("min"),
    max_size=asg_config.get("max"),
    vpc_zone_identifiers=vpc.subnet_ids,
    launch_template=autoscaling.GroupLaunchTemplateArgs(
        id=asg_launch_template.id,
        version="$Latest",
    )
)

asg_attachment_bar = autoscaling.Attachment(
    "asgAttachmentBar",
    autoscaling_group_name=asg.id,
    lb_target_group_arn=alb_target_group.arn,
)


## Exports

pulumi.export('alb_url', alb.dns_name)
