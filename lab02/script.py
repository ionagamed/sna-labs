from typing import Dict

import re
import subprocess
import shlex
from time import sleep


def run_and_check(command: str):
    print("-" * 80)
    print(f"$ {command}")

    process = subprocess.run(command, stdout=subprocess.PIPE, shell=True)
    process.check_returncode()

    try:
        print(process.stdout.decode("utf-8"))
    except:  # docker ps may output something UNUSUAL
        print(process.stdout)

    return process.stdout


def parse_ssh_config(filename: str) -> Dict[str, str]:
    result = {}
    with open(filename, "r") as f:
        for line in f:
            if not line.startswith("#") and line.strip():
                k, v = re.split(r"\s+", line.strip(), 1)
                result[k] = v
    return result


def write_ssh_config(values: Dict[str, str], filename: str):
    with open(filename, "w") as f:
        f.write("\n".join(f"{k} {v}" for k, v in values.items()))


def configure_sshd():
    config = parse_ssh_config("./sshd_config")
    config["X11Forwarding"] = "no"
    config["UsePAM"] = "no"
    config["PasswordAuthentication"] = "no"
    write_ssh_config(config, "./sshd_config")

    run_and_check("docker exec lygin_sna_lab_ssh_1 /etc/init.d/ssh reload")

    # copying the public key
    run_and_check("docker cp ./example_keypair.pub lygin_sna_lab_ssh_1:/root/.ssh/authorized_keys")
    run_and_check("docker exec lygin_sna_lab_ssh_1 chmod 400 /root/.ssh/authorized_keys")
    run_and_check("docker exec lygin_sna_lab_ssh_1 chown root:root /root/.ssh/authorized_keys")

    # fixing permissions on local key
    run_and_check("chmod 400 ./example_keypair")


def main():
    # checking docker version and existence on the target machine
    run_and_check("docker version")

    # pulling openssh and hackmd through compose
    run_and_check("docker-compose pull")

    # check list of images
    run_and_check("docker image ls")

    # fetching dockerfiles for display
    run_and_check("curl https://raw.githubusercontent.com/rastasheep/ubuntu-sshd/master/18.04/Dockerfile")
    run_and_check("curl https://raw.githubusercontent.com/hackmdio/docker-hackmd/master/debian/Dockerfile")

    # unzip postgres-data (it is not kept in the repo as-is, because of the empty dirs)
    run_and_check("if [[ ! -e postgres-data ]] then unzip postgres-data.zip; fi")

    # upping the containers and creating networks (defined in docker-compose.yml)
    run_and_check("docker-compose -p lygin_sna_lab up -d")

    # show inspection of networks
    run_and_check("docker inspect lygin_sna_lab_br_default")
    run_and_check("docker inspect lygin_sna_lab_br_internal")

    # inspections do not show the required routing tables, fetching them
    # (and some other packages)
    subcommand = "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -yq iproute2 iputils-ping"
    run_and_check(f"docker exec lygin_sna_lab_ssh_1 /bin/bash -c \"{subcommand}\"")

    # hackmd container doesn't have internet, let's create a sample network
    # connect, and then disconnect the container
    run_and_check("docker network create lygin_sna_lab_internet")
    run_and_check("docker network connect lygin_sna_lab_internet lygin_sna_lab_hackmd_1")
    run_and_check(f"docker exec lygin_sna_lab_hackmd_1 /bin/bash -c \"{subcommand}\"")
    run_and_check("docker network disconnect lygin_sna_lab_internet lygin_sna_lab_hackmd_1")
    run_and_check("docker network rm lygin_sna_lab_internet")

    # showing the actual routing table
    run_and_check("docker exec -it lygin_sna_lab_ssh_1 ip route list")
    run_and_check("docker exec -it lygin_sna_lab_hackmd_1 ip route list")

    # show the running containers
    run_and_check("docker ps")

    # check that hackmd container is accessible from ssh container
    run_and_check("docker exec lygin_sna_lab_ssh_1 ping -c 1 hackmd")

    # check that hackmd container does not have internet
    run_and_check("docker exec lygin_sna_lab_hackmd_1 /bin/bash -c \"ping -c 1 8.8.8.8 || true\"")

    configure_sshd()

    # connect to the hackmd service by binding the port to localhost
    command = "ssh -L 31337:hackmd:3000 -i ./example_keypair -p 31338 root@localhost"
    ssh_process = subprocess.Popen(shlex.split(command))


    print("=" * 80)
    print(f"$ {command}")
    print("Visit http://localhost:31337 to check out hackmd")
    print("Waiting for SSH to close")
    ssh_process.wait()



if __name__ == "__main__":
    main()
    # configure_sshd()
