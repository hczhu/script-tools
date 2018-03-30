#!/bin/bash

set -ex

run=$1

if [ "$run" = "apt" ]; then run=""; fi
if [ "$run" = "" ]; then
    sudo apt-get install \
        libboost-all-dev \
        libevent-dev \
        libdouble-conversion-dev \
        libgoogle-glog-dev \
        libgflags-dev \
        libiberty-dev \
        liblz4-dev \
        liblzma-dev \
        libsnappy-dev \
        zlib1g-dev \
        binutils-dev \
        libjemalloc-dev \
        libssl-dev \
        pkg-config \
        bison \
        flex \
        libboost-all-dev \
        libunwind8-dev \
        libelf-dev \
        libdwarf-dev
fi

if [ "$run" = "zlib" ]; then run=""; fi
if [ "$run" = "" ]; then
    wget https://zlib.net/zlib-1.2.11.tar.gz
    tar xvf zlib-1.2.11.tar.gz
    cd zlib-1.2.11
    ./configure
    make
    sudo make install
    cd -
fi

if [ "$run" = "krb" ]; then run=""; fi
if [ "$run" = "" ]; then
    wget https://kerberos.org/dist/krb5/1.16/krb5-1.16.tar.gz.asc
    tar xvf krb5-1.16.tar.gz
    cd krb5-1.16/src
    ./configure
    make
    sudo make install
    make clean
    cd ..
fi

if [ "$run" = "mstch" ]; then run=""; fi
if [ "$run" = "" ]; then
    git clone https://github.com/no1msd/mstch
    cd mstch
    mkdir build
    cd build
    cmake ..
    make
    sudo make install
    make clean
    cd ../..
fi

if [ "$run" = "double" ]; then run=""; fi
if [ "$run" = "" ]; then
    git clone https://github.com/google/double-conversion.git
    cd double-conversion
    sudo scons install
    cd ..
fi

if [ "$run" = "gflags" ]; then run=""; fi
if [ "$run" = "" ]; then
    git clone https://github.com/gflags/gflags.git
    cd gflags
    cmake . && make && sudo make install
    rm -fr CMakeCache.txt && cmake . -DBUILD_SHARED_LIBS=ON && make && sudo make install
    make clean
    cd ..
fi

if [ "$run" = "" ]; then
    git clone https://github.com/google/glog.git
    cd glog
    cmake . && make && sudo make install
    rm -fr CMakeCache.txt && cmake . -DBUILD_SHARED_LIBS=ON && make && sudo make install
    cd ..
    
    git clone https://github.com/facebook/folly
    cd folly
    wget https://github.com/google/googletest/archive/release-1.8.0.tar.gz && \
      tar zxf release-1.8.0.tar.gz && \
      rm -f release-1.8.0.tar.gz && \
      cd googletest-release-1.8.0 && \
      cmake configure . && \
      make && \
      sudo make install && \
      cd ..
    
    cmake configure . && \
      make -j $(nproc) && \
      sudo make install
    
    rm -fr CMakeCache.txt && cmake configure . -DBUILD_SHARED_LIBS=ON && \
      make -j $(nproc) && \
      sudo make install
    
    # add -fPIC to CMake/FollyCompilerUnix.cmake
    cmake configure . && \
      make folly_fingerprint && \
      sudo cp -f libfolly_fingerprint.a /usr/local/lib/libfolly_fingerprint.a  
    cd ..
    
    git clone https://github.com/facebook/zstd.git
    cd zstd && make && sudo make install && make check && cd ..
    
    git clone https://github.com/facebook/wangle.git
    cd wangle/wangle
    cmake .
      make && \
      ctest && \
      sudo make install
    cd ../..
    
    git clone https://github.com/facebook/proxygen.git
    cd proxygen/proxygen
    autoreconf -ivf && ./configure && make && sudo make install
    cd ../..
fi

if [ "$run" = "rsocket" ]; then run=""; fi
if [ "$run" = "" ]; then
    git clone https://github.com/rsocket/rsocket-cpp.git
    cd rsocket-cpp
    mkdir -p build
    cd build
    # Append '-ldl -levent -lboost_context -ldouble-conversion -lgflags -lboost_regex' after '-fuse-ld=' in CMakeList.txt
    cmake ../
    make -j
    # ./tests
    cd ../..
fi

if [ "$run" = "curl" ]; then run=""; fi
if [ "$run" = "" ]; then
    wget https://curl.haxx.se/download/curl-7.59.0.tar.gz
    tar xvf curl-7.59.0.tar.gz
    cd curl-7.59.0/
    cmake .
    make
    sudo make install
    cd ..
fi

if [ "$run" = "fbthrift" ]; then run=""; fi
if [ "$run" = "" ]; then
    git clone https://github.com/facebook/fbthrift.git
    cd fbthrift/build
    cmake ..
    make
    sudo make install
    cd ../..
fi
