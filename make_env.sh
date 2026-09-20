#!/usr/bin/bash

function pyinit() {
 export PYENV_ROOT="/home/cell0r/.pyenv";
 [[ -d "$HOME/.pyenv"/bin ]] && export PATH=""$HOME/.pyenv"/bin:$PATH";
 eval "$(pyenv init - bash)";
}

function nopyinit() {
 IFS=':'; list=($PATH); list2=; for obj in ${list[@]}; do [ ! "$obj" == "$HOME/.pyenv/shims" ] && list2=$list2$obj:; done; export PATH=$list2;
}

function venv {
 args=$1
 if [ "$args" == "-c" ] || [ "$args" == "-ca" ] || [ "$args" == "-ac" ]; then
  #python -m venv --system-site-packages venv;
  python -m venv venv;
 fi;
 if [ "$args" == "-a" ] || [ "$args" == "-ca" ] || [ "$args" == "-ac" ]; then
  source ./venv/bin/activate;
 fi;
}

pyinit
pyenv shell 3.10
venv -c
nopyinit
venv -a
