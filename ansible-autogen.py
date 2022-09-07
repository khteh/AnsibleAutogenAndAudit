#!/usr/bin/python3
import os, stat
from pathlib import Path
from shutil import copyfile
strInput = input("Please provide project name (Press 'q' or ENTER to quit): ")
if not strInput or strInput == '' or strInput == 'q':
    exit()
project = strInput
playbookPath = f"{project}/playbooks"
rolePath = f"{project}/roles"
#print(f"Auto-generate ansible tree for {project}... Confirm? (Y/N): ")
strInput = input(f"Auto-generate ansible tree for {project}... Confirm? (Y/N): ")
if not strInput or strInput == '' or strInput == 'q' or strInput == 'N' or strInput == 'n':
    exit()
if Path(f"{project}").exists():
    print(f"{project} exists. Exit without overwriting existing code....")
    exit(-1)
root = f"{project}"
Path(root).mkdir(parents=True, exist_ok=True)
with open(f"{root}/.gitignore", 'w') as f:
    print(".secret", file=f)
    print("*.swp", file=f)
githooks = f"{project}/.githooks"
Path(githooks).mkdir(exist_ok=True)
with open(f"{githooks}/pre-commit", 'w') as f:
    print("#!/bin/bash", file=f)
    print("echo pre-commit runs!", file=f)
    print("ANSIBLE_LINT=\"$(command -v ansible-lint)\"", file=f)
    print("if [[ ! -x $ANSIBLE_LINT ]]; then", file=f)
    print("    printf \"ansible-lint not available.\n Please install it with 'pip install --user ansible-lint'.\n\"", file=f)
    print("    exit 0", file=f)
    print("fi", file=f)
    print("PASS=true", file=f)
    print("printf \"\nValidating yaml files with ansible-lint\n\"", file=f)
    print("for FILE in `git status | egrep 'modified.*yml|modified.*yaml|new file.*yml|new file.*yaml' | awk -F: '{ print $2 }'`; do", file=f)
    print("    echo Processing $FILE...", file=f)
    print("    $ANSIBLE_LINT $FILE --force-color -p -v", file=f)
    print("    if [[ \"$?\" == 0 ]]; then", file=f)
    print("        printf \"\t\033[32mAnsible-Lint Passed: $FILE\033[0m\n\"", file=f)
    print("    else", file=f)
    print("        printf \"\t\033[41mAnsible-List Failed: $FILE\033[0m\n\"", file=f)
    print("        PASS=false", file=f)
    print("    fi", file=f)
    print("done", file=f)
    print("printf \"\nAnsible validation completed!\n\"", file=f)
    print("if ! $PASS; then", file=f)
    print("    printf \"\033[41mCOMMIT FAILED:\033[0m Your commit contains files that fail ansible-lint validation. \nFix the errors or skip this validation if required with --no-verify (not advised)\n\"", file=f)
    print("    exit 1", file=f)
    print("else", file=f)
    print("     printf \"\033[42mCOMMIT SUCCEEDED\033[0m\n\"", file=f)
    print("fi", file=f)
    print("exit $?", file=f)

f = Path(f"{project}/.githooks/pre-commit")

f.chmod(f.stat().st_mode | stat.S_IEXEC)
Path(playbookPath).mkdir(parents=True, exist_ok=True)
Path(rolePath).mkdir(parents=True, exist_ok=True)
pwd = Path.cwd()
os.chdir(playbookPath)
Path("roles").symlink_to("../roles")
os.chdir(pwd)
Path(f"{root}/group_vars/all").mkdir(parents=True, exist_ok=True)
Path(f"{rolePath}/git/vars").mkdir(parents=True, exist_ok=True)
Path(f"{rolePath}/git/tasks").mkdir(parents=True, exist_ok=True)
with open(f"{rolePath}/git/vars/main.yml", 'w') as f:
    print("git_username: \"{{ var_username }} \"", file=f)
    print("git_password: \"{{ var_password }} \"", file=f)
    print("repository: \"{{ var_repository }} \"", file=f)
    print("destination: \"{{ var_destination }} \"", file=f)

with open(f"{rolePath}/git/tasks/main.yml", 'w') as f:
    print("- name: Get latest code from repository", file=f)
    print("  git:", file=f)
    print("    repo: \"https://{{ git_username }}:{{ git_password }}@{{ repository }}\"", file=f)
    print("    dest: \"{{ destination }} \"", file=f)
    print("    version: \"{{ branch }} \"", file=f)
    print("    force: yes", file=f)
    print("  delegate_to: localhost", file=f)

with open(f"{playbookPath}/gitpull.yml", 'w') as f:
    print("# This is should be the FIRST playbook encapsulated within other playbooks", file=f)
    print("- hosts: local", file=f)
    print("  connection: local", file=f)
    print("  gather_facts: no\n", file=f)
    print("  roles:", file=f)
    print("  - git", file=f)

with open(f"{root}/ansible.cfg", 'w') as f:
    print("[defaults]", file=f)
    print("roles_path = roles", file=f)
    print("vault_password_file = .secret", file=f)

with open(f"{root}/group_vars/all/all.yml", 'w') as f:
    print("var_username: ", file=f)
    print("var_repository: ", file=f)
    print("var_destination: ", file=f)
    print("branch: master", file=f)

with open(f"{root}/group_vars/all/all_vault.yml", 'w') as f:
    print("# ansible-vault create --vault-id default@.secret group_vars/all/all_vault.yml", file=f)

with open(f"{root}/localhost.yml", 'w') as f:
    print("local:", file=f)
    print("  hosts:", file=f)
    print("    localhost:", file=f)
    print("      ansible_connection: local", file=f)
