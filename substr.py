#!/usr/bin/python
import sys
content = sys.stdin.read()
start = 0
end = len(content)
if len(sys.argv) > 1:
  start = int(sys.argv[1])
if len(sys.argv) > 2:
  end = int(sys.argv[2])

print content[start:end]
