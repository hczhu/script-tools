#!/bin/bash
if [ $# -lt 2 ]
then
  echo "Usage: $0 old_string new_string"
  exit 0
fi
cmd1="sed -i \"s/$1/$2/g\" \`grep $1 -rl ./ | grep h$\`"
cmd2="sed -i \"s/$1/$2/g\" \`grep $1 -rl ./ | grep cpp$\`"
echo $cmd1
echo $cmd2
echo "Go?"
read ans
if [ "$ans" = "Y" ]
then
  $cmd1
  $cmd2
else
  echo "Quit"
fi
