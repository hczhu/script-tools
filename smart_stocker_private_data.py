#!/usr/bin/python

import gdata.docs
import gdata.docs.service
import gdata.spreadsheet.service
import re, os
import sys

def LoginMyGoogle(email_file, password_file):
  # Connect to Google
  gd_client = gdata.spreadsheet.service.SpreadsheetsService()
  gd_client.email = file(email_file).readline().strip()
  gd_client.password = file(password_file).readline().strip()
  gd_client.source = 'smart-stocker'
  try:
    gd_client.ProgrammaticLogin()
    return gd_client
  except Exception, e:
    sys.stderr.write('Failed to login google account. Exception ' + str(e) +'\n')
  return None
    
def GetTransectionRecords(gd_client):
  if gd_client is None:
    return []
  try:
    feeds = gd_client.GetListFeed('0Akv9eeSdKMP0dHBzeVIzWTY1VUlQcFVKOWFBZkdDeWc', 'od6').entry
    rows = []
    for row in feeds:
      rows.append({key : row.custom[key].text for key in row.custom.keys()})  
    return rows
  except Exception, e:
    sys.stderr.write('Failed to read transaction sheet. Exception ' + str(e) +'\n')
  return []

if __name__ == "__main__":
 client = LoginMyGoogle('/Users/hcz/.smart-stocker-google-email.txt', '/Users/hcz/.smart-stocker-google-password.txt')
 for row in GetTransectionRecords(client)[0:5]:
   print row
  
