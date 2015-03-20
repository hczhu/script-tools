#!/usr/bin/python
import sys
import random
import datetime

has_key_filter=False
key_set={}
output_passed=False
def random_select(n):
  cnt=0
  selected=[]
  while True:
    line=sys.stdin.readline()
    if line=="": break
    if has_key_filter and line.split()[0] not in key_set:
      if output_passed:
        sys.stderr.write(line)
        continue
    if len(selected)<n: selected.append(line)
    else:
      pos=random.randint(0,cnt)
      if pos < n:
        if output_passed: sys.stderr.write(selected[pos])
        selected[pos]=line
      else:
        if output_passed: sys.stderr.write(line)
    cnt+=1
  return selected

  def load_key_file(fname):
    all_key={}
    for line in file(fname):
      all_key[line.split()[0]]=1
    return all_key

if __name__=='__main__':
  if len(sys.argv)<2:
    print "Usage: sample.py sample_count [key file]"
    sys.exit()
  n=(int)(sys.argv[1])
  for opt in sys.argv[2:]:
    if opt=='-o': output_passed=True
    else:
      has_key_filter=True
      key_set=load_key_file(sys.argv[2])
  random.seed(datetime.datetime.now())
  out=random_select(n)
  for line in out:
    sys.stdout.write(line)
