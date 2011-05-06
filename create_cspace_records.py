#!/usr/bin/env python

import httplib2
import pickle

from lxml import etree
from collections import defaultdict
from pprint import pprint
from cspace_constants import *

# locationName is where it's currently at
# identifier doesn't always seem to be there, nor description
# TODO: drill deeper into measurements
# TODO: handle image info
STANDARD_OBJECT_FIELDS = [
  'description', 
  'descriptiveNote',
  'displayCreationDate', 
  'displayEdition',
  'displayMaterialsTech', 
  'displayMeasurements', 
  'identifier', 
  'inscriptions',
  'locationName',
  'objectWorkType',
  'recordInfoLink',
  'title', 
  'workID', 
  ]
REPEAT_OBJECT_FIELDS = [
  'subjectTerm', 
  ]
# TODO can we get the cdwalite:birthdate attr off of vitalDatesCreator?
ARTIST_FIELDS = [
  'displayCreator',
  'genderCreator',
  'nationalityCreator', 
  'roleCreator',
  'vitalDatesCreator', 
  ]

def create_cspace_record(record, resume_token, existing_records):
    object_values = defaultdict(lambda: None)

    for fieldname in STANDARD_OBJECT_FIELDS:
      element = record.find('.//{http://www.getty.edu/CDWA/CDWALite/}%s' % fieldname)
      if element is not None:
        object_values[fieldname] = element.text

    for fieldname in REPEAT_OBJECT_FIELDS:
      object_values[fieldname] = []
      elements = record.findall(".//{http://www.getty.edu/CDWA/CDWALite/}%s" % fieldname)
      for element in elements:
        object_values[fieldname].append(element.text)

    # 
    # Can't have bare ampersands. There don't seem to be any encoded
    # ampersands coming our way, so we just do a replace.
    #
    for k in object_values.keys():
      if type(object_values[k]) != type([]) and object_values[k] is not None:
        object_values[k] = object_values[k].replace("&", "&amp;")

    # TODO handle creators
    #creators = record.findall(".//{http://www.getty.edu/CDWA/CDWALite/}indexingCreatorSet")
    #for creator in creators:
    #  person = {}
    #  for field in ARTIST_FIELDS:
    #    element = record.find(".//{http://www.getty.edu/CDWA/CDWALite/}%s" % field)
    #    if element is not None:
    #      person[field] = (element.text)
    #  creator_values.append(person)

    # 
    # This only seems to happen with objects that have been deleted
    #
    if not 'workID' in object_values:
      print "No workID in this object. Skipping."
      return 0

    if object_values['workID'] in existing_records:
      print "CollectionSpace already has %s, skipping." % object_values['workID']
      return 0

    h = httplib2.Http()
    h.add_credentials(CSPACE_USER, CSPACE_PASS)

    #
    # TODO these lines suggest that we might want to handle possibly
    # repeating values a little more intelligently, if we end up
    # tracking more of them
    #
    concepts = []
    for concept in object_values['subjectTerm']:
      concepts.append("<contentConcept>%s</contentConcept>" % concept)

    #
    # Schema is at https://source.collectionspace.org/collection-space/src/services/tags/v1.5/services/collectionobject/jaxb/src/main/resources/collectionobjects_common.xsd
    #
    # updated to account for
    # http://wiki.collectionspace.org/display/collectionspace/Imports+Service+Home
    #     
    object_xml = u'''
    <imports>
      <import seq="1" service="CollectionObjects" type="CollectionObject">
        <schema xmlns:collectionobjects_common="http://collectionspace.org/collectionobject/" name="collectionobjects_common">
          <collectionobjects_common:objectNumber>%s</collectionobjects_common:objectNumber>
          <collectionobjects_common:titleGroupList>
              <collectionobjects_common:titleGroup>
                  <collectionobjects_common:title>%s</collectionobjects_common:title>
                  <collectionobjects_common:titleLanguage>eng</collectionobjects_common:titleLanguage>
              </collectionobjects_common:titleGroup>
          </collectionobjects_common:titleGroupList>
          <collectionobjects_common:objectProductionDates>
            <collectionobjects_common:objectProductionDate>%s</collectionobjects_common:objectProductionDate>
          </collectionobjects_common:objectProductionDates>
          <collectionobjects_common:materialGroupList>
            <collectionobjects_common:materialGroup>
              <collectionobjects_common:material>%s</collectionobjects_common:material>
            </collectionobjects_common:materialGroup>
          </collectionobjects_common:materialGroupList>
          <collectionobjects_common:contentConcepts>
            %s
          </collectionobjects_common:contentConcepts>
          <collectionobjects_common:objectNameList>
            <collectionobjects_common:objectNameGroup>
              <collectionobjects_common:objectName>%s</collectionobjects_common:objectName>
              <collectionobjects_common:objectNameCurrency>current</collectionobjects_common:objectNameCurrency>
              <collectionobjects_common:objectNameType>classified</collectionobjects_common:objectNameType>
              <collectionobjects_common:objectNameSystem>In-house</collectionobjects_common:objectNameSystem>
              <collectionobjects_common:objectNameLanguage>eng</collectionobjects_common:objectNameLanguage>
            </collectionobjects_common:objectNameGroup>
          </collectionobjects_common:objectNameList>
          <collectionobjects_common:physicalDescription>%s</collectionobjects_common:physicalDescription>
          <collectionobjects_common:editionNumber>%s</collectionobjects_common:editionNumber>
          <collectionobjects_common:dimensionSummary>%s</collectionobjects_common:dimensionSummary>
          <collectionobjects_common:inscriptionContent>%s</collectionobjects_common:inscriptionContent>
          <collectionobjects_common:owners>
            <collectionobjects_common:owner>%s</collectionobjects_common:owner>
          </collectionobjects_common:owners>
        </schema>
      </import>
    </imports>
    ''' % (object_values['workID'], 
           object_values['title'],
           object_values['displayCreationDate'],
           object_values['displayMaterialsTech'], 
           "\n".join(concepts),
           object_values['objectWorkType'], 
           object_values['descriptiveNote'], 
           object_values['displayEdition'], 
           object_values['dimensionSummary'], 
           object_values['inscriptions'], 
           object_values['locationName'], 
           )

    resp, content = h.request(
      CSPACE_URL + 'imports',
      'POST',
      body = object_xml.encode('utf-8'),
      headers = {'Content-Type': 'application/xml'}
      )

    if resp['status'] == '200':
      if object_values['title'] is None:
        print "Inserted '%s' into collectionspace\n" % object_values['workID'].encode('utf-8')
      else:
        print "Inserted '%s' into collectionspace\n" % object_values['title'].encode('utf-8')
      return 1
    else:
      print "\nSomething went wrong with %s:" % object_values['workID'].encode('utf-8')
      print "record:"
      ovd = {}
      for key in object_values.keys():
        ovd[key] = object_values[key]
      pprint(ovd)
      print "Response: %s" % resp
      print "Content: %s\n" % content
      return 0

def parse_oai(xml, existing_records):
  root = etree.fromstring(xml)
  records = root.find('{http://www.openarchives.org/OAI/2.0/}ListRecords')
  records_created = 0
  resume_token = None

  for record in records:
    if record.tag == '{http://www.openarchives.org/OAI/2.0/}resumptionToken':
      resume_token = record.text
      print "Resuming with %s\n" % resume_token
    else:
      records_created += create_cspace_record(record, resume_token, 
        existing_records)
  return (resume_token, records_created)

def find_objects_in_cspace():
  pickle_file = open(CS_OBJECT_FILE, 'rb')
  cobjects = pickle.load(pickle_file)
  pickle_file.close()
  return cobjects

if __name__ == "__main__":
  h = httplib2.Http()
  resp, content = h.request(
    OAI_URL + '?verb=ListRecords&metadataPrefix=cdwalite&set=object',
    'GET'
    )

  existing_records = find_objects_in_cspace()

  total_records_created = 0
  resume_token, records_created = parse_oai(content, existing_records)
  total_records_created += records_created

  while True:
    resp, content = h.request(
      OAI_URL + "?verb=ListRecords&resumptionToken=%s"  % resume_token,
      'GET'
      )
    resume_token, records_created = parse_oai(content, existing_records)
    total_records_created += records_created

    if resume_token is None:
      break

  print "All records processed. Created %s new records.\n" % total_records_created
