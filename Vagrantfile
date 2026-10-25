# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"

  config.vm.provision "shell", inline: <<-SHELL
    apt update
    apt install -y python3-pip python3-venv
    mkdir -p /opt/creep
    chown vagrant:vagrant /opt/creep
  SHELL

  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    python3 -m venv /opt/creep
    source /opt/creep/bin/activate
    python3 -m pip install --upgrade build pytest twine wheel
    python3 -m build /vagrant/
  SHELL

  config.vm.post_up_message = """\
# Enable environment:
$ source /opt/creep/bin/activate
# Run tests:
$ python3 -m pytest /vagrant/
# Upload package to test repository:
$ python3 -m twine upload --repository testpypi /vagrant/dist/*
# Upload package to production repository:
$ python3 -m twine upload /vagrant/dist/*\
"""
end
