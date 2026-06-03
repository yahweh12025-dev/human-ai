import yaml
import sys

with open('raw_policy.txt', 'r') as f:
    content = f.read()

parts = content.split('---', 1)
yaml_part = parts[1] if len(parts) > 1 else parts[0]
policy = yaml.safe_load(yaml_part)

if 'filesystem_policy' in policy and 'read_write' in policy['filesystem_policy']:
    if '/home/yahwehatwork' not in policy['filesystem_policy']['read_write']:
        policy['filesystem_policy']['read_write'].append('/home/yahwehatwork')

with open('current_policy.yaml', 'w') as f:
    yaml.dump(policy, f, sort_keys=False)
