# NOTE: In order to write comment and edit labels, this script requires workflows with write permissions.
# It should not use any untrusted third party code, or any code checked into the repository itself
# as that could indirectly grant PRs the ability to edit labels and comments on PRs.

import os
import git
import requests
import json
import difflib
from datetime import datetime
from pathlib import Path


def get_first_commit_date(repo, file_path):
    commits = list(repo.iter_commits(paths=file_path))
    if commits:
        return commits[-1].committed_date
    else:
        print(f"{file_path} has no commit info, putting it last")
        return datetime.datetime.min


def sort_by_added_date(repo, file_paths):
    files_with_dates = [(get_first_commit_date(repo, file_path), file_path) for file_path in file_paths]
    sorted_files = sorted(files_with_dates, reverse=True)
    return [file for date, file in sorted_files]


def similar_easyconfigs(repo, new_file):
    possible_neighbours = [x for x in new_file.parent.glob('*.eb') if x != new_file]
    return sort_by_added_date(repo, possible_neighbours)


def diff(old, new):
    with open(old, 'r') as old_file, open(new, 'r') as new_file:
        old_lines = list(old_file)
        new_lines = list(new_file)
        return ''.join(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=str(old),
            tofile=str(new)))


def pr_ecs(pr_diff):
    new_ecs = []
    changed_ecs = []
    for item in pr_diff:
        if item.a_path.endswith('.eb'):
            if item.change_type == 'A':
                new_ecs.append(Path(item.a_path))
            else:
                changed_ecs.append(Path(item.a_path))
    return new_ecs, changed_ecs


GITHUB_API_URL = 'https://api.github.com'
event_path = os.getenv("GITHUB_EVENT_PATH")
token = os.getenv("GH_TOKEN")
repo = os.getenv("GITHUB_REPOSITORY")
base_branch_name = os.getenv("GITHUB_BASE_REF")

with open(event_path) as f:
    data = json.load(f)

pr_number = data['pull_request']['number']
merge_commit_sha = data['pull_request']['merge_commit_sha']

print("PR number:", pr_number)
print("Repo:", repo)
print("Base branch name:", base_branch_name)
print("Merge commit ref:", merge_commit_sha)

gitrepo = git.Repo(".")

target_commit = gitrepo.commit('origin/' + base_branch_name)
pr_commit = gitrepo.commit(merge_commit_sha)
pr_diff = target_commit.diff(pr_commit)

new_ecs, changed_ecs = pr_ecs(pr_diff)

print("Changed ECs:", changed_ecs)
print("Newly added ECs:", new_ecs)

new_software = 0
updated_software = 0
to_diff = dict()
for new_file in new_ecs:
    neighbours = similar_easyconfigs(gitrepo, new_file)
    print(f"Found {len(neighbours)} neighbours for {new_file}")
    if neighbours:
        updated_software += 1
        to_diff[new_file] = neighbours
    else:
        new_software += 1

print(f"Generating comment for {len(to_diff)} updates softwares")
# Limit comment size for large PRs:
if len(to_diff) > 20:  # Too much, either bad PR or some broad change. Not diffing.
    max_diffs_per_software = 0
elif len(to_diff) > 10:
    max_diffs_per_software = 1
elif len(to_diff) > 5:
    max_diffs_per_software = 2
else:
    max_diffs_per_software = 3

comment = ''
if max_diffs_per_software > 0:
    for new_file, neighbours in to_diff.items():
        compare_neighbours = neighbours[:max_diffs_per_software]
        if compare_neighbours:
            print(f"Diffs for {new_file}")
            comment += f'#### Updated software `{new_file.name}`\n\n'

        for neighbour in compare_neighbours:
            print(f"against {neighbour}")
            comment += '<details>\n'
            comment += f'<summary>Diff against <code>{neighbour.name}</code></summary>\n\n'
            comment += f'[{neighbour}](https://github.com/{repo}/blob/{base_branch_name}/{neighbour})\n\n'
            comment += '```diff\n'
            comment += diff(neighbour, new_file)
            comment += '```\n</details>\n\n'

print("Adjusting labels")
current_labels = [label['name'] for label in data['pull_request']['labels']]

labels_add = []
labels_del = []
for condition, label in [(changed_ecs, 'change'), (new_software, 'new'), (updated_software, 'update')]:
    if condition and label not in current_labels:
        labels_add.append(label)
    elif not condition and label in current_labels:
        labels_del.append(label)

url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/labels"

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
}

if labels_add:
    print(f"Setting labels: {labels_add} at {url}")
    response = requests.post(url, headers=headers, json={"labels": labels_add})
    if response.status_code == 200:
        print(f"Labels {labels_add} added successfully.")
    else:
        print(f"Failed to add labels: {response.status_code}, {response.text}")

for label in labels_del:
    print(f"Removing label: {label} at {url}")
    response = requests.delete(f'{url}/{label}', headers=headers)
    if response.status_code == 200:
        print(f"Label {label} removed successfully.")
    else:
        print(f"Failed to delete label: {response.status_code}, {response.text}")

# Write comment with diff
if updated_software:
    # Search for comment by bot to potentially replace
    url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments"
    response = requests.get(url, headers=headers)
    comment_id = None
    for existing_comment in response.json():
        if existing_comment["user"]["login"] == "github-actions[bot]":  # Bot username in GitHub Actions
            comment_id = existing_comment["id"]

    if comment_id:
        # Update existing comment
        url = f"{GITHUB_API_URL}/repos/{repo}/issues/comments/{comment_id}"
        response = requests.patch(url, headers=headers, json={"body": comment})
        if response.status_code == 200:
            print("Comment updated successfully.")
        else:
            print(f"Failed to update comment: {response.status_code}, {response.text}")
    else:
        # Post a new comment
        url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments"
        response = requests.post(url, headers=headers, json={"body": comment})
        if response.status_code == 201:
            print("Comment posted successfully.")
        else:
            print(f"Failed to post comment: {response.status_code}, {response.text}")
