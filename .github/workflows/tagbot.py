# NOTE: In order to write comment and edit labels, this script requires workflows with write permissions.
# It should not use any untrusted third party code, or any code checked into the repository itself
# as that could indirectly grant PRs the ability to edit labels and comments on PRs.

import json
import os
from pathlib import Path

import requests
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
args = parser.parse_args()


event_path = os.getenv('GITHUB_EVENT_PATH')
repo = os.getenv('GITHUB_REPOSITORY')
base_branch_name = os.getenv('GITHUB_BASE_REF')

with open(args.input, 'w') as f:
    analysis = json.load(f)

print('Adjusting labels')
current_labels = [label['name'] for label in data['pull_request']['labels']]
labels_add = [label for label in analysis['labels'] if label not in current_labels]
labels_del = [label for label in analysis['not_labels'] if label in current_labels]

url = f'{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/labels'

headers = {
    'Accept': 'application/vnd.github+json',
    'Authorization': f'Bearer {token}',
    'X-GitHub-Api-Version': '2022-11-28',
}

if labels_add:
    print(f'Setting labels: {labels_add} at {url}')
    response = requests.post(url, headers=headers, json={'labels': labels_add})
    if response.status_code == 200:
        print(f'Labels {labels_add} added successfully.')
    else:
        print(f'Failed to add labels: {response.status_code}, {response.text}')

for label in labels_del:
    print(f'Removing label: {label} at {url}')
    response = requests.delete(f'{url}/{label}', headers=headers)
    if response.status_code == 200:
        print(f'Label {label} removed successfully.')
    else:
        print(f'Failed to delete label: {response.status_code}, {response.text}')

# Search for comment by bot to potentially replace
url = f'{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments'
response = requests.get(url, headers=headers)
comment_id = None
for existing_comment in response.json():
    if existing_comment['user']['login'] == 'github-actions[bot]':  # Bot username in GitHub Actions
        comment_id = existing_comment['id']

# Write comment with diff
if 'comment' in analysis:
    comment = analysis['comment']

    if len(comment) >= 65536:
        # Comment is too long to post, so post a message saying that
        comment = 'Diff of new easyconfig(s) against existing ones is too long for a GitHub comment. '
        comment += 'Use `--review-pr` (and `--review-pr-filter` / `--review-pr-max`) locally.'

    if comment_id:
        # Update existing comment
        url = f'{GITHUB_API_URL}/repos/{repo}/issues/comments/{comment_id}'
        response = requests.patch(url, headers=headers, json={'body': comment})
        if response.status_code == 200:
            print('Comment updated successfully.')
        else:
            print(f'Failed to update comment: {response.status_code}, {response.text}')
    else:
        # Post a new comment
        url = f'{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments'
        response = requests.post(url, headers=headers, json={'body': comment})
        if response.status_code == 201:
            print('Comment posted successfully.')
        else:
            print(f'Failed to post comment: {response.status_code}, {response.text}')
else:
    # TODO remove comment
    pass
