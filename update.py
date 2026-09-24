
from os import path as ospath
from subprocess import run as srun

UPSTREAM_REPO = "https://github.com/itsDev-Developer/manwa"  # SSH URL for private repo
UPSTREAM_BRANCH = "master"
GITHUB_EMAIL = "srk100m@gmail.com"
GITHUB_USERNAME = "SasukeXDev"

if UPSTREAM_REPO is not None:
    if ospath.exists(".git"):
        srun(["rm", "-rf", ".git"])
    try:
        update = srun(
            [
                f"git init -q \
                && git config --global user.email {GITHUB_EMAIL} \
                && git config --global user.name {GITHUB_USERNAME} \
                && git add . \
                && git commit -sm update -q \
                && git remote add origin {UPSTREAM_REPO} \
                && git fetch origin -q \
                && git reset --hard origin/{UPSTREAM_BRANCH} -q"
            ],
            shell=True,
        )
        
        if update.returncode == 0:
            print("Successfully updated with latest commit from UPSTREAM_REPO")
        else:
            print("Something went wrong while updating, check UPSTREAM_REPO if valid or not!")
    except Exception as err:
        print(err)
