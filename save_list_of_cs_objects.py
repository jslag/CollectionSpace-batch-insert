#!/usr/bin/env python

import httplib2
import pickle
from lxml import etree
from cspace_constants import *

if __name__ == "__main__":
  cobjects = []

  h = httplib2.Http()
  h.add_credentials(CSPACE_USER, CSPACE_PASS)
  resp, content = h.request(CSPACE_URL + 'collectionobjects', 'GET')

  while True:
    root = etree.fromstring(content)
    for oid in root.findall('.//objectNumber'):
      cobjects.append(oid.text)

    itemcount = root.find('itemsInPage').text
    if itemcount != '40':
      # not a full page, must have been the last one
      break
    else:
      page = int(root.find('pageNum').text) + 1
      print "fetching page %s of objects from Collectionspace." % page
      resp, content = h.request(
        CSPACE_URL + 'collectionobjects?pgNum=%s' % page,
        'GET')

  output = open(CS_OBJECT_FILE, 'wb')
  pickle.dump(cobjects, output)
  output.close()

  print "Objects dumped.\n"
