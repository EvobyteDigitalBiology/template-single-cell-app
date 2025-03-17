#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import Tags
from zihelper import utils as ziutils

from awscdk.al_case_scrnaseq_stack_network import AlCaseScrnaseqStackNetwork
from awscdk.al_case_scrnaseq_stack_pg import AlCaseScrnaseqStackPG
from awscdk.al_case_scrnaseq_stack_django import AlCaseScrnaseqStackDjango
from awscdk.al_case_scrnaseq_stack_pipeline import AlCaseScrnaseqStackPipeline
from awscdk.al_case_scrnaseq_stack_ui import AlCaseScrnaseqStackUI

# Load configuration from yaml
cdk_config = ziutils.load_config_yaml('assets/cdk_config.yaml')
policy_config = ziutils.load_config_json('assets/policies.json')

app = cdk.App()

network_stack = AlCaseScrnaseqStackNetwork(app, "AlCaseScrnaseqStackNetwork", cdk_config)
db_stack = AlCaseScrnaseqStackPG(app, "AlCaseScrnaseqStackPG", cdk_config, network_stack)
django_stack = AlCaseScrnaseqStackDjango(app, "AlCaseScrnaseqStackDjango", cdk_config, policy_config, network_stack, db_stack)
pipeline_stack = AlCaseScrnaseqStackPipeline(app, "AlCaseScrnaseqStackPipeline", cdk_config, policy_config, network_stack)
ui_stack = AlCaseScrnaseqStackUI(app, "AlCaseScrnaseqStackUI", cdk_config, policy_config, network_stack)

db_stack.add_dependency(target = network_stack)
django_stack.add_dependency(target = db_stack)
ui_stack.add_dependency(target = django_stack)

Tags.of(network_stack).add('project', 'al-case-scrnaseq')
Tags.of(db_stack).add('project', 'al-case-scrnaseq')
Tags.of(django_stack).add('project', 'al-case-scrnaseq')
Tags.of(pipeline_stack).add('project', 'al-case-scrnaseq')
Tags.of(ui_stack).add('project', 'al-case-scrnaseq')

app.synth()
