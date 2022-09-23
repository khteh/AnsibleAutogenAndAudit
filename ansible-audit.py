#!/usr/bin/python3
import os, sys, yaml, argparse, smtplib, socket, stat, magic
from multiprocessing import Pool
from pathlib import Path
from shutil import copyfile
from itertools import islice
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from os.path import basename
parser = argparse.ArgumentParser(description='Audit ansible project structure and content')
parser.add_argument('path', nargs='+', help='Path to ansible project to perform audit')
parser.add_argument('--verbose', '-v', action='count', default=0)
args = parser.parse_args()
space =  '    '
branch = '|   '
# pointers:
tee =    '|-- '
last =   '|-- '
yaml_exceptions = {".gitignore", "ansible.cfg", "README.md", ".secret"}
 
def isYaml(path: str) -> bool:
    with open(path, 'r') as stream:
        try:
            yaml.load(stream, yaml.Loader)
        except (yaml.YAMLError, UnicodeDecodeError) as exception:
            return False
    return True
 
def tree(dir_path: Path, level: int=-1, depth: int=0, limit_to_directories: bool=False, length_limit: int=10000):
    """Given a directory Path object print a visual tree structure"""
    dir_path = Path(dir_path) # accept string coerceable to Path
    files = 0
    directories = 0
    errors = []
    project_tree = ""
    def inner(dir_path: Path, prefix: str='', level=-1, depth=0):
        nonlocal files, directories, errors, project_tree
        if not level:
            return # 0, stop iterating
        if limit_to_directories:
            contents = [d for d in dir_path.iterdir() if d.is_dir()]
        else:
            contents = list(dir_path.iterdir())
        pointers = [tee] * (len(contents) - 1) + [last]
        for pointer, path in zip(pointers, contents):
            if path.is_symlink():
                #yield prefix + pointer + path.name + f" -> {path.readlink()}" #Requires python 3.9 and above
                yield prefix + pointer + path.name + f" -> {os.readlink(path)}"
            elif path.is_dir() and path.name != ".git":
                yield prefix + pointer + path.name
                directories += 1
                extension = branch if pointer == tee else space
                yield from inner(path, prefix=prefix+extension, level=level-1, depth=depth+1)
            elif path.is_file() and not limit_to_directories and "ASCII text" == magic.from_file(f"{dir_path/path.name}"):
                global yaml_exceptions
                flag = isYaml(f"{dir_path}/{path.name}")
                if flag and path.suffix != ".yml" and path.name not in yaml_exceptions:
                    errors.append(f"Invalid suffix: {path.name}")
                elif not flag and path.suffix == ".yml":
                    errors.append(f"Invalid YAML: {path.name}")
                yield prefix + pointer + path.name
                files += 1
#    print(dir_path.name)
    project_tree = f"{dir_path.name}\r\n"
    iterator = inner(dir_path, level=level, depth=depth)
    [line for line in islice(iterator, length_limit)]
#    for line in islice(iterator, length_limit):
#        continue
#        print(line)
#        project_tree += f"{line}\r\n"
    if next(iterator, None):
        errors.append(f"... length_limit, {length_limit}, reached, counted:")
        project_tree += f"... length_limit, {length_limit}, reached, counted:\r\n"
    #print(f"\n{directories} directories" + (f", {files} files" if files else ''))
    project_tree += f"\n{directories} directories" + (f", {files} files" if files else '') + "\r\n"
    return errors
 
def validate(project):
    errors = []
    if not Path(f"{project}/.git").exists():
        errors.append(f"Project {project} is not tracked in GIT!")
 
    if not Path(f"{project}/.githooks").exists() or not Path(f"{project}/.githooks").is_dir():
        errors.append(f"Directory {project}/.githooks does NOT exist!")
 
    if not Path(f"{project}/.githooks/pre-commit").exists() or not Path(f"{project}/.githooks/pre-commit").is_file():
        errors.append(f"{project}/.githooks/pre-commit does NOT exist!")
    else:
        f = Path(f"{project}/.githooks/pre-commit")
        if not bool(f.stat().st_mode & stat.S_IEXEC):
            errors.append(f"{project}/.githooks/pre-commit is NOT executable!")
 
    if not Path(f"{project}/group_vars").exists() or not Path(f"{project}/group_vars").is_dir():
        errors.append(f"Directory {project}/group_vars does NOT exist!")
  
    if not Path(f"{project}/group_vars/all").exists() or not Path(f"{project}/group_vars/all").is_dir():
        errors.append(f"Directory {project}/group_vars/all does NOT exist!")
 
    if not Path(f"{project}/group_vars/all/all.yml").exists() or not Path(f"{project}/group_vars/all/all.yml").is_file():
        errors.append(f"{project}/group_vars/all/all.yml does NOT exist!")
    elif Path(f"{project}/group_vars/all/all.yml").stat().st_size == 0:
        errors.append(f"{project}/group_vars/all/all.yml variable file is empty!")
 
    if not Path(f"{project}/localhost.yml").exists() or not Path(f"{project}/localhost.yml").is_file():
        errors.append(f"{project}/localhost.yml inventory does NOT exist!")
    elif Path(f"{project}/localhost.yml").stat().st_size == 0:
        errors.append(f"{project}/localhost.yml inventory is empty!")
 
    if not Path(f"{project}/playbooks").exists() or not Path(f"{project}/playbooks").is_dir():
        errors.append(f"Directory {project}/playbooks does NOT exist!")
 
    if not Path(f"{project}/playbooks/gitpull.yml").exists() or not Path(f"{project}/playbooks/gitpull.yml").is_file():
        errors.append(f"{project}/playbooks/gitpull.yml playbook does NOT exist!")
    elif Path(f"{project}/playbooks/gitpull.yml").stat().st_size == 0:
        errors.append(f"{project}/playbooks/gitpull.yml playbook is empty!")
 
#    if not Path(f"{project}/playbooks/roles").exists() or not Path(f"{project}/playbooks/roles").is_symlink():
#        errors.append(f"{project}/playbooks/roles symlink does NOT exist!")
 
    if not Path(f"{project}/roles").exists() or not Path(f"{project}/roles").is_dir():
        errors.append(f"Directory {project}/roles does NOT exist!")
 
    if not Path(f"{project}/roles/git").exists() or not Path(f"{project}/roles/git").is_dir():
        errors.append(f"Directory {project}/roles/git does NOT exist!")
 
    if not Path(f"{project}/roles/git/tasks").exists() or not Path(f"{project}/roles/git/tasks").is_dir():
        errors.append(f"Directory {project}/roles/git/tasks does NOT exist!")
 
    if not Path(f"{project}/roles/git/vars").exists() or not Path(f"{project}/roles/git/vars").is_dir():
        errors.append(f"Directory {project}/roles/git/vars does NOT exist!")
 
    if not Path(f"{project}/roles/git/tasks/main.yml").exists() or not Path(f"{project}/roles/git/tasks/main.yml").is_file():
        errors.append(f"{project}/roles/git/tasks/main.yml does NOT exist!")
    elif Path(f"{project}/roles/git/tasks/main.yml").stat().st_size == 0:
        errors.append(f"{project}/roles/git/tasks/main.yml git role main task is empty!")
 
    if not Path(f"{project}/roles/git/vars/main.yml").exists() or not Path(f"{project}/roles/git/vars/main.yml").is_file():
        errors.append(f"{project}/roles/git/vars/main.yml does NOT exist!")
    elif Path(f"{project}/roles/git/vars/main.yml").stat().st_size == 0:
        errors.append(f"{project}/roles/git/vars/main.yml git role main vars is empty!")
    return errors
 
def work(path):
    print(f"Processing {path}...")
    errors = tree(Path(path))
    errors += validate(path)
    result = {}
    result["errors"] = errors
    result["project"] = path
    return result
 
if __name__ == '__main__':
    fails = 0
    content = ""
    summary = []
    projects = []
    for path in args.path:
        if Path(f"{path}").exists() and Path(path).is_dir():
            projects.append(path)
    total = len(projects)
    if not total:
        exit
    with Pool(10) as p:
        result = p.map(work, projects)
        for r in result:
            if r["errors"]:
                fails += 1
                summary.append({"Project": r["project"], "Errors": len(r["errors"])})
                content += f"Path: {r['project']}\t\tErrors: {len(r['errors'])}\r\n"
                for error in r["errors"]:
                    content += f"{error}\r\n"
            content += "\r\n==========\r\n\r\n"
        if fails:
            fqdn = socket.getfqdn()
            user = "preprod" if "preprod.domain.com" in fqdn else "development"
            msg = EmailMessage()
            msg["Subject"] = f"Ansible audit failed on {fails}/{total} projects!"
            msg["From"] = f"{user}@{fqdn}"
            msg["To"] =   "me@email.com"
            emailContent = "Project\t\tErrors\r\n"
            emailContent += "----------------------------\r\n"
            for i in summary:
                emailContent += i["Project"]
                emailContent += "\t"
                emailContent += str(i["Errors"])
                emailContent += "\r\n"
            emailContent += "\r\n----------------------------\r\n\r\n"
            emailContent += content
            msg.set_content(emailContent)
            s = smtplib.SMTP("mailhost.domain.com", 25)
            s.send_message(msg)
            s.quit()
#exit(-1 if errors else 0)
