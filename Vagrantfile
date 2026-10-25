# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"

  config.vm.provision "shell", inline: <<-SHELL
    mkdir -p /opt/creep
    sudo chown vagrant:vagrant /opt/creep
    cd /opt/creep
    source bin/activate
    python3 -m pip install --upgrade build pytest setuptools twine wheel
    python3 -m build /vagrant/
  SHELL

  config.vm.post_up_message = """\
Test upload:
$ python3 -m twine upload --repository testpypi /vagrant/dist/*
Prod upload:
$ python3 -m twine upload /vagrant/dist/*\
"""
end
