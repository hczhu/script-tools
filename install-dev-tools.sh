sudo apt-get install ctags
sudo apt-get install clang-formater
sudo apt-get install clang
sudo apt-get upgrade g++
sudo apt-get update && sudo apt-get install octave
sudo apt-get install\
    g++\
    automake\
    autoconf\
    autoconf-archive\
    libtool\
    libboost-all-dev\
    libevent-dev\
    libdouble-conversion-dev\
    libgoogle-glog-dev\
    libgflags-dev\
    liblz4-dev\
    liblzma-dev\
    libsnappy-dev\
    make\
    zlib1g-dev\
    binutils-dev\
    libjemalloc-dev\
    libssl-dev\
    pkg-config
sudo apt-get install     libiberty-dev
sudo apt-get install hg
sudo apt-get install Mercurial
sudo apt-get upgrade pip
sudo apt-get upgrade pip3.4
sudo apt-get update pip
sudo apt-get install pip
sudo apt-get install pip.3.4
sudo apt-get install pip3.4
sudo apt-get install gcc4.9
sudo apt-get install gcc-4.9
sudo apt-get install gcc
sudo apt-get upgrade gcc
sudo apt-get install gcc
sudo apt-get install gcc.59
sudo apt-get install gcc4.9
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
sudo apt-get install gcc-6 g++-6
sudo apt-get install openjdk-8-jdk
sudo apt-get update && sudo apt-get install oracle-java8-installer
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update && sudo apt-get install oracle-java8-installer
echo "deb [arch=amd64] http://storage.googleapis.com/bazel-apt stable jdk1.8" | sudo tee /etc/apt/sources.list.d/bazel.list
curl https://bazel.build/bazel-release.pub.gpg | sudo apt-key add -
sudo apt-get update && sudo apt-get install bazel
sudo apt-get upgrade bazel
sudo apt-get install cmake

curl -LO https://github.com/BurntSushi/ripgrep/releases/download/0.8.1/ripgrep_0.8.1_amd64.deb && sudo dpkg -i ripgrep_0.8.1_amd64.deb
