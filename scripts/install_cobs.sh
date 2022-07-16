mkdir -p cobs_installation && cd cobs_installation
# curl -L https://github.com/iqbal-lab-org/cobs/releases/download/v$1/cobs-$1.tar.gz -o cobs.tar.gz
curl -L https://www.dropbox.com/s/o1wnfebfs33oclq/cobs-0.2.0.tar.gz?dl=1 -o cobs.tar.gz
tar -zxvf cobs.tar.gz
mkdir build && cd build

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  cmake -DCMAKE_C_COMPILER=x86_64-conda-linux-gnu-gcc -DCMAKE_CXX_COMPILER=x86_64-conda-linux-gnu-g++ -DCMAKE_BUILD_TYPE=Release -DCONDA=1 ..
elif [[ "$OSTYPE" == "darwin"* ]]; then
  cmake -DCMAKE_C_COMPILER=x86_64-apple-darwin*-gcc-11 -DCMAKE_CXX_COMPILER=x86_64-apple-darwin*-g++-11 -DCMAKE_BUILD_TYPE=Release ..
else
  echo "Unsupported OS"
  exit 1
fi

make -j1
make test
cd ../../
cp cobs_installation/build/src/cobs $2
$2 -h
