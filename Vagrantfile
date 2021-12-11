# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/hirsute64"

  config.vm.provision "shell", inline: <<-SHELL
    sudo apt update
    sudo apt install -y python3-venv python3-pip
    python3 -m pip install --upgrade build
    python3 -m pip install --upgrade twine
    python3 -m build /vagrant/
  SHELL

  config.vm.post_up_message = """\
Test upload:
$ python3 -m twine upload --repository testpypi /vagrant/dist/*
Prod upload:
$ python3 -m twine upload /vagrant/dist/*\
"""
end
