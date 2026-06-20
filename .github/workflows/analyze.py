# script analyzes the PR, writes a json with tags and comment into a json file

import json
import os
from pathlib import Path

import git
import argparse


def get_first_commit_date(repo, file_path):
    commits = list(repo.iter_commits(paths=file_path))
    if commits:
        return commits[-1].committed_date
    else:
        raise ValueError(f'{file_path} has no commit info, this should not happen')


def sort_by_added_date(repo, file_paths):
    files_with_dates = [(get_first_commit_date(repo, file_path), file_path) for file_path in file_paths]
    sorted_files = sorted(files_with_dates, reverse=True)
    return [file for date, file in sorted_files]


def similar_easyconfigs(repo, new_file, new_ecs):
    possible_neighbours = [x for x in new_file.parent.glob('*.eb') if x not in new_ecs]
    return sort_by_added_date(repo, possible_neighbours)


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


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()

repo = os.getenv('GITHUB_REPOSITORY')
base_branch_name = os.getenv('GITHUB_BASE_REF')

print('Base branch name:', base_branch_name)

gitrepo = git.Repo('.')

target_commit = gitrepo.commit('origin/' + base_branch_name)
print('Target commit ref:', target_commit)
merge_commit = gitrepo.head.commit
print('Merge commit:', merge_commit)
pr_diff = target_commit.diff(merge_commit)

new_ecs, changed_ecs = pr_ecs(pr_diff)
modified_workflow = any(item.a_path.startswith('.github/workflows/') for item in pr_diff)


print('Changed ECs:', ', '.join(str(p) for p in changed_ecs))
print('Newly added ECs:', ', '.join(str(p) for p in new_ecs))
print('Modified workflow:', modified_workflow)


# Check for new and updated software.
# First, try to determine if the software exists. If so,
# we'll generate a comment diffing against existing EasyConfigs
# to make review easier.
new_software = 0
updated_software = 0
to_diff = {}
for new_file in new_ecs:
    neighbours = similar_easyconfigs(gitrepo, new_file, new_ecs)
    print(f'Found {len(neighbours)} neighbours for {new_file}')
    if neighbours:
        updated_software += 1
        to_diff[new_file] = neighbours
    else:
        new_software += 1

print(f'Generating comment for {len(to_diff)} updates softwares')
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
            print(f'Diffs for {new_file}')
            comment += f'#### Updated software `{new_file.name}`\n\n'

        for neighbour in compare_neighbours:
            print(f'against {neighbour}')
            comment += '<details>\n'
            comment += f'<summary>Diff against <code>{neighbour.name}</code></summary>\n\n'
            comment += f'[{neighbour}](https://github.com/{repo}/blob/{base_branch_name}/{neighbour})\n\n'
            comment += '```diff\n'
            comment += gitrepo.git.diff(f'HEAD:{neighbour}', f'HEAD:{new_file}')
            comment += '\n```\n</details>\n\n'

# After that, try to add additional labels based on the PR contents.
# Add manual_label if download_instructions is present. This reads the file.
manual_download = False
for file in new_ecs + changed_ecs:
    if file.is_file():
        with file.open() as f:
            content = f.read()
        if 'download_instructions' in content:
            manual_download = True
            break

# Add toolchain labels based on matching new added / changed filenames againt our toolchain policy
# This doesn't include NVHPC yet, and needs to be adapted together with the test suite
# when adding new toolchains and their respective labels.
# We are only checking the file names here and will not read the actual file.
gcc_tc_gen_map = {
    '10.2': '2020b',
    '10.3': '2021a',
    '11.2': '2021b',
    '11.3': '2022a',
    '12.2': '2022b',
    '12.3': '2023a',
    '13.2': '2023b',
    '13.3': '2024a',
    '14.2': '2025a',
    '14.3': '2025b',
    '15.2': '2026.1',
}

ic_tc_gen_map = {
    '2021.2.0': '2021a',
    '2021.4.0': '2021b',
    '2022.1.0': '2022a',
    '2023.1.0': '2023a',
    '2023.2.1': '2023b',
    '2024.2.0': '2024a',
    '2025.1.1': '2025a',
    '2025.2.0': '2025b',
    '2025.3.3': '2026.1',
}

llvm_tc_gen_map = {
    '20.1.5': '2023b',
    '20.1.8': '2025b',
    '21.1.8': '2026.1',
}

toolchain_names = ['foss', 'gompi', 'gfbf', 'iimpi', 'iimkl', 'intel', 'llvm-compilers', 'lfbf',
                   'lompi', 'lmpich', 'lfoss', 'lmpflf']
toolchain_present = {}
for toolchain_ver in gcc_tc_gen_map.values():
    toolchain_present[toolchain_ver] = False

for file in new_ecs + changed_ecs:
    file_path = str(file)
    # Check for GCCcore / GCC
    for gcc_version, toolchain_version in gcc_tc_gen_map.items():
        if f'-GCCcore-{gcc_version}' in file_path or f'-GCC-{gcc_version}' in file_path:
            toolchain_present[toolchain_version] = True
            continue
    # Check for intel-compilers
    for intel_version, toolchain_version in ic_tc_gen_map.items():
        if f'-intel-compilers-{intel_version}' in file_path:
            toolchain_present[toolchain_version] = True
            continue
    for llvm_version, toolchain_version in llvm_tc_gen_map.items():
        if f'-llvm-compilers-{llvm_version}' in file_path:
            toolchain_present[toolchain_version] = True
            continue
    # Check for common toolchains with our toolchain naming
    for toolchain_version in gcc_tc_gen_map.values():
        if any(f'-{toolchain_name}-{toolchain_version}' in file_path for toolchain_name in toolchain_names):
            toolchain_present[toolchain_version] = True
            continue

label_checks = [(changed_ecs, 'change'),
                (new_software, 'new'),
                (updated_software, 'update'),
                (modified_workflow, 'workflow'),
                (manual_download, 'manual_download')]

result = {
    'labels': [label for condition, label in label_checks if condition],
    'not_labels': [label for condition, label in label_checks if not condition],
}

if updated_software:
    result['comment'] = comment

with open(args.output, 'w') as f:
    json.dump(result, f)
