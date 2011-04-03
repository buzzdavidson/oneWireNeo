from datetime import datetime

__author__ = 'sdavidson'

import re
from pyowfs import Connection
from enum import Enum
from urlparse import urlparse

'''
    Available 1-Wire Features
'''
FEATURES = Enum('Temperature', 'Humidity', 'Pressure', 'Counter', 'Voltage', 'Current', 'Sense', 'Pio',
                     'Memory', 'Clock', 'Illumination', 'UV', 'CO2', "LCD")
PROPERTY_STATUS = Enum('New', 'Indeterminate', 'Decreased', 'Stable', 'Increased', 'Changed', 'Missing')
PROPERTY_KIND = Enum('Numeric','String','Timestamp','Boolean','Binary')
SENSOR_STATUS = Enum('New', 'Available', 'Missing')

'''
    Represents a single "Family" of 1-Wire devices
'''
class OneWireFamily:
    def __init__(self, familyCode, description, features = frozenset()):
        self.familyCode = familyCode
        self.description = description
        self.features = features

    def __str__(self):
        return "%s: Family Code: %s, Features: %s" % (self.description, self.familyCode, list(self.features))

class OneWireNeo:

    def __init__(self, address='localhost:4304', desiredFeatures=None):
        # TODO: trap and report errors on connect.
        print("Connecting to " + address)
        self._root = Connection(address)
        print("Connected")
        self._desiredFeatures = desiredFeatures
        self._address = address
        self._connected = False
        self._firstCycle = True
        self._sensors = dict()
        self._updateSensors()

    def refresh(self):
        self._updateSensors()

    def _updateSensors(self):
        try:
            print('Refreshing sensors')
            knownSensors = set(self._sensors)
            for foundSensor in self._root.iter_sensors():
                self._connected = True
                spath = foundSensor.path
                if self._sensors.has_key(spath):
                    print('Found existing sensor at path %s' % spath)
                    knownSensors.remove(spath)
                    self._sensors[spath]._status = SENSOR_STATUS.Available
                    self._sensors[spath].update(foundSensor)
                else:
                    # TODO: check if sensor is in desired features
                    if isDesiredSensor(spath, self._desiredFeatures):
                        print('Found new sensor at path %s' % spath)
                        sensor = OneWireNeoSensor(foundSensor, self._desiredFeatures)
                        self._sensors[spath] = sensor
                    else:
                        print("Skipping sensor at [%s], its not in desired set")
            # anything left in knownSensors?
            if len(knownSensors) > 0:
                print("Some sensors seem to have gone missing!") # TODO: callback here(?)
                for sensor in knownSensors:
                    sensor._status = SENSOR_STATUS.Missing
        finally:
            self._firstCycle = False
            print(str(self))

    def __str__(self):
        retval = '\nOneWireNeo: Server'
        if self._connected:
            retval += ' Connected to ' + self._address
            retval += str(", %d Registered Sensors" % len(self._sensors))
            retval += str("\n%s" % ('-' * 80))
            keyList = sorted(self._sensors.keys())
            for key in keyList:
                sensor = self._sensors[key]
                retval += str("\n%s\t%s\t%s\t%s" % (sensor._id, getSensorDescription(sensor._id), sensor._status, sensor._lastRead))
        else:
            retval += ' Not connected.'
        retval += '\n'
        return retval


    # DONE: use case: get list of sensors matching desired features

    # DONE: use case: get properties of single sensor

    # TODO: use case: allow single property to be changed

    # TODO: use case: display memory as clean hex

    # TODO: use case: callback on property change

    # TODO: use case: indicate whether property has changed.  if numeric, indicate whether it has gone up or down.

    # TODO: use case: ensure property values are trimmed.

    # TODO: use case: allow cached property to be specified by sensor

    # TODO: use case: callback on sensor availability change (new, missing, returned)


class OneWireNeoSensor:
    def __init__(self, sensor, desiredFeatures=None):
        self._status = SENSOR_STATUS.New
        self._properties = dict()
        self._path = sensor.path
        self._id = sensor.path.strip('/')
        self._cached = True
        self._lastRead = None
        self._desiredFeatures = desiredFeatures
        self.update(sensor)

    def update(self, sensor):
        print("Updating sensor [%s]" % (self._path))
        knownProperties = set(self._properties)
        for propName in self._getFlatPropertyList(sensor):
            if self._properties.has_key(propName):
                knownProperties.remove(propName)
                print("found existing property: " + propName)
                self._properties[propName].update(sensor)
            else:
                print("found new property: " + propName)
                self._properties[propName] = OneWireNeoProperty(sensor, propName)
        if (len(knownProperties) > 0):
            print("Some properties seem to have gone missing!") # TODO: callback here(?)
            for propName in knownProperties:
                self._properties[propName]._status = PROPERTY_STATUS.Missing
        self._lastRead = datetime.now()

    '''
        Generate a flat property name list which only contains properties in our set of desired features.
    '''
    def _getFlatPropertyList(self, sensor):
        print("fetching flattened property list")
        inProperties = list()
        self._fetchFlatProperties(sensor, sensor, inProperties)
        print("Base property list is %s" % str(inProperties))
        outProperties = getDesiredAttributes(inProperties, self._desiredFeatures)
        print("Filtered property list is %s" % str(outProperties))
        return outProperties

    '''
        Recursively build list of property names to generate the flat list expected by the matching algorithm.
    '''
    def _fetchFlatProperties(self, baseitem, curitem, propList):
        basepath = ''
        if (baseitem != curitem):
            # we've recursed.  if baseitem path is '/10.5D4470010800/' and curitem path is
            # '/10.5D4470010800/errata/', new base path will be 'errata/'
            basepath = curitem.path[len(baseitem.path):]

        print("fetching properties with base path [%s]" % (basepath))
        for item in curitem.iter_entries():
            if type(item).__name__ == 'Dir':
                print("recursing to fetch child directory")
                self._fetchFlatProperties(baseitem, item, propList)
            else:
                propList.append(basepath + str(item))

class OneWireNeoProperty:
    def __init__(self, sensor, path):
        self._kind = self._determinePropertyKind(sensor, path)
        self._writable = self._determinePropertyMutability(sensor, path)
        self._path = sensor.path + path
        self._status = PROPERTY_STATUS.New
        self._lastRead = None
        self._value = None
        self._updateValue(sensor)

    def update(self, sensor):
        self._status = PROPERTY_STATUS.Indeterminate
        self._updateValue(sensor)

    def _updateValue(self, sensor):
        propval = sensor.capi.get(self._path)
        if self._kind == PROPERTY_KIND.Numeric:
            testVal = float(propval)
            if self._value is None:
                self._status = PROPERTY_STATUS.Changed
            else:
                if testVal == self._value:
                    self._status = PROPERTY_STATUS.Stable
                else:
                    self._status = PROPERTY_STATUS.Decreased if testVal < self._value else PROPERTY_STATUS.Increased
            self._value = testVal
        else:
            self._status = PROPERTY_STATUS.Stable if propval == self._value else PROPERTY_STATUS.Changed
            self._value = propval

        self._lastRead = datetime.now()

    def _determinePropertyKind(self, sensor, path):
        #TODO: determine property kind
        return PROPERTY_KIND.String

    def _determinePropertyMutability(self, sensor, path):
        #TODO: determine property mutability
        return False

'''
    Placeholder for unknown family code
'''
_UNKNOWN_FAMILY = OneWireFamily('FF', 'Unknown Family Code')

'''
    Maps family codes to available 1-Wire features.  Compiled manually from owfs page.
    See http://owfs.org/index.php?page=family-code-lookup for details.
    While this list is more-or-less complete, it does eliminate some of the more esoteric
    features from individual 1-Wire slave devices.  YMMV.
'''
_FAMILY_FEATURES = {
    '01' : OneWireFamily('01', 'ID Only Tag'),
    '02' : OneWireFamily('02', 'Memory Button', frozenset([FEATURES.Memory])),
    '04' : OneWireFamily('04', 'Real Time Clock', frozenset([FEATURES.Memory, FEATURES.Clock, FEATURES.Counter])),
    '05' : OneWireFamily('05', 'Addressable Switch', frozenset([FEATURES.Pio, FEATURES.Sense])),
    '06' : OneWireFamily('06', 'Memory Button', frozenset([FEATURES.Memory])),
    '08' : OneWireFamily('08', 'Memory Button', frozenset([FEATURES.Memory])),
    '09' : OneWireFamily('09', 'Memory Button', frozenset([FEATURES.Memory])),
    '0A' : OneWireFamily('0A', 'Memory Button', frozenset([FEATURES.Memory])),
    '0B' : OneWireFamily('0B', 'Memory Button', frozenset([FEATURES.Memory])),
    '0C' : OneWireFamily('0C', 'Memory Button', frozenset([FEATURES.Memory])),
    '0F' : OneWireFamily('0F', 'Memory Button', frozenset([FEATURES.Memory])),
    '10' : OneWireFamily('10', 'High Precision Digital Thermometer', frozenset([FEATURES.Temperature])),
    '12' : OneWireFamily('12', 'Dual Addressable Switch', frozenset([FEATURES.Temperature, FEATURES.Pressure, FEATURES.Voltage, FEATURES.Sense, FEATURES.Pio, FEATURES.Memory])),
    '14' : OneWireFamily('14', 'Quad A/D Converter', frozenset([FEATURES.Memory])),
    '18' : OneWireFamily('18', 'Monetary Button with SHA-1', frozenset([FEATURES.Memory])),
    '1B' : OneWireFamily('1B', 'Battery ID/Monitor', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Counter])),
    '1C' : OneWireFamily('1C', 'EEPROM with Address Inputs', frozenset([FEATURES.Sense, FEATURES.Pio, FEATURES.Memory])),
    '1D' : OneWireFamily('1D', 'RAM with Counter', frozenset([FEATURES.Memory, FEATURES.Counter])),
    '1E' : OneWireFamily('1E', 'Smart Battery Monitor', frozenset([FEATURES.Temperature, FEATURES.Clock, FEATURES.Voltage])),
    '1F' : OneWireFamily('1F', 'MicroLAN Coupler'),
    '20' : OneWireFamily('20', 'Quad A/D Converter', frozenset([FEATURES.Temperature, FEATURES.Voltage])),
    '21' : OneWireFamily('21', 'Thermachron Temperature Logging iButton', frozenset([FEATURES.Temperature, FEATURES.Clock])),
    '22' : OneWireFamily('22', 'Economy Digital Thermometer', frozenset([FEATURES.Temperature])),
    '23' : OneWireFamily('23', 'EEPROM', frozenset([FEATURES.Memory])),
    '24' : OneWireFamily('24', 'Real Time Clock', frozenset([FEATURES.Clock])),
    '26' : OneWireFamily('26', 'Smart Battery Monitor', frozenset([FEATURES.Temperature, FEATURES.Pressure, FEATURES.Voltage, FEATURES.Humidity, FEATURES.Clock, FEATURES.Illumination])),
    '27' : OneWireFamily('27', 'Time Chip', frozenset([FEATURES.Clock])),
    '28' : OneWireFamily('28', 'Programmable Resolution Digital Thermometer', frozenset([FEATURES.Temperature])),
    '29' : OneWireFamily('29', '8 Channel Addressable Switch', frozenset([FEATURES.Pio, FEATURES.Sense, FEATURES.LCD])),
    '2C' : OneWireFamily('2C', 'Digital Potentiometer'),
    '2D' : OneWireFamily('2D', 'EEPROM', frozenset([FEATURES.Memory])),
    '2E' : OneWireFamily('2E', 'Battery Monitor and Charge Controller', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
    '30' : OneWireFamily('30', 'Hi-Precision Li+ Battery Monitor', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
    '35' : OneWireFamily('35', 'Multi-Chemistry Battery Fuel Gauge', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
    '36' : OneWireFamily('36', 'High-Precision Columb Counter', frozenset([FEATURES.Voltage, FEATURES.Sense, FEATURES.Pio])),
    '37' : OneWireFamily('37', 'Password Protected Memory Button', frozenset([FEATURES.Memory])),
    '3A' : OneWireFamily('3A', 'Dual Channel Addressable Switch', frozenset([FEATURES.Sense, FEATURES.Pio])),
    '3B' : OneWireFamily('3B', 'Digital Thermometer with ID', frozenset([FEATURES.Temperature])),
    '3D' : OneWireFamily('3D', 'Stand-Alone Fuel Gauge', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
    '42' : OneWireFamily('42', 'Digital Thermometer with Sequence Detect and PIO', frozenset([FEATURES.Temperature, FEATURES.Sense, FEATURES.Pio])),
    '43' : OneWireFamily('43', 'EEPROM', frozenset([FEATURES.Memory])),
    '51' : OneWireFamily('51', 'Multi-Chemistry Battery Fuel Gauge', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
    'EE' : OneWireFamily('EE', 'HobbyBoards Microprocessor-Based Slave with Temperature', frozenset([FEATURES.Temperature,FEATURES.UV])),
    'EF' : OneWireFamily('EF', 'HobbyBoards Microprocessor-Based Slave', frozenset([FEATURES.UV])),
    'FF' : _UNKNOWN_FAMILY
}

# TODO: duplicate value to standard key IIF (a) std key doesnt exist, (b) one value exists in category
# TODO: add facility to standardize: mem pages= pages.0, etc
'''
    Defines default property names for each feature.  Helps to eliminate some of the inconsistencies in the
    owfs codebase when referring to properties.
'''
_FEATURE_DEFAULT_PROPS = {
    FEATURES.Temperature: 'temperature',
    FEATURES.Humidity: 'humidity',
    FEATURES.Pressure: 'pressure',
    FEATURES.Counter: 'counter',
    FEATURES.Voltage: 'voltage'
}

'''
    Map property names to default features; this is the main associative element in this code.
'''
_SOURCE_PATTERNS = {
    FEATURES.Temperature: ['(TAI8570/)?temperature[\d]?','fasttemp','templow','temphigh','type[A-Z]/temperature'],
    FEATURES.Humidity: ['(HIH4000/)?(HTM1735/)?humidity'],
    FEATURES.Pressure: ['(TAI8570/)?(B1-R1-A/)?pressure'],
    FEATURES.Counter: ['counter(s)?\.[AB]', 'counter(s)\.ALL', '(readonly/)?(counter/)?cycle(s)?', 'counter', 'page(s)?/count(er)?(s?)\.[\d]+', 'page(s)?/count(er)?(s)?.ALL'],
    FEATURES.Voltage: ['(8bit/)?volt(s)?(2)?', '(8bit/)?(T8A/)?volt(2)?\.[a-z,0-9]','(8bit/)?(T8A/)?volt(2)?\.all', 'V[AD]D', 'vbias', 'vis', 'volthours'],
    FEATURES.Current: ['current','amphours'],
    FEATURES.Sense: ['sensed', 'sensed\.[a-z]', 'sensed\.all', 'sensed\.byte'],
    FEATURES.Pio: ['pio', 'pio\.[a-z]', 'pio\.all', 'pio\.byte', 'branch'],
    FEATURES.Memory: ['application', 'memory','page\.ALL', 'page\.[\d]+', 'pages/page\.[\d]+', 'pages/page\.ALL'],
    FEATURES.Clock: ['(u)?date', 'readonly/clock', 'disconnect/(u)?date', 'endcharge/(u)?date', 'clock/(u)?date' ],
    FEATURES.Illumination: ['S3-R1-A/(illumination)?(current)?(gain)?'],
    FEATURES.UV: ['uvi/uvi','uvi/uvi-offset','uvi/in_case', 'uvi/valid'],
    FEATURES.CO2: ['co2/ppm', 'co2/power', 'co2/status'],
    FEATURES.LCD: []
}

'''
    Compiles property matchers from _SOURCE_PATTERNS into regex matchers to improve performance
'''
#TODO: check efficiency of this methodology.  Is there a more appropriate place to init library-level data?
_finderMatchers = dict()
for key, value in _SOURCE_PATTERNS.items():
    matcherList = list()
    for pattern in value:
        matcherList.append(re.compile(pattern, re.IGNORECASE))
    _finderMatchers[key] = matcherList

'''
    Retrieve family information for a given 1-Wire family code.
    Use this method rather than accessing _FAMILY_MEMBERS directly.
'''
def getFamilyInfo(code):
    return _FAMILY_FEATURES.get(code, _UNKNOWN_FAMILY)

'''
    Retrieve list of attribute names which match the desired features
    This method normalizes output - property names will always be all lowercase.
'''
def getMatchingAttributes(inputData, desiredFeatures=None):
    # TODO: add sensor alias if found!
    # TODO - handle 'None' for desiredFeatures - implies "all"
    retval = dict()
    # Add default properties - these are always present
    for attr in ['id', 'family', 'type']:
        if inputData.has_key(attr):
            retval[attr.lower()] = inputData[attr]
    # Then add matching entries for each feature in desiredFeatures
    for feature in desiredFeatures:
        # Determine list of keys for requested feature
        featureKeys = set()
        for key in inputData.iterkeys():
            for matcher in _finderMatchers[feature]:
                if matcher.match(key):
                    featureKeys.add(key)
                    break
        # Then add matching properties for this feature to dictionary
        for attr in featureKeys:
            if inputData.has_key(attr):
                retval[attr.lower()] = inputData[attr]
    return retval

def getDesiredAttributes(attributeList, desiredFeatures=None):
    retval = set()
    for attr in ('id', 'family', 'type'):
        if attr in attributeList:
            retval.add(attr)
    for feature in desiredFeatures:
        for attr in attributeList:
            for matcher in _finderMatchers[feature]:
                if matcher.match(attr):
                    retval.add(attr)
    return list(retval)

'''
    Determine which sensors in supplied list provide the desired features
'''
def getDesiredSensors(sensorList, desiredFeatures):
    retval = set()
    for sensor in sensorList:
        if isDesiredSensor(sensor, desiredFeatures):
            retval.add(sensor)
    return retval

def isDesiredSensor(sensorName, desiredFeatures):
    #print("Checking sensor named " + sensorName)
    tokenized = sensorName.partition('.')
    familyCode = tokenized[0].strip('/')
    #print("Family code is: " + familyCode)
    familyMetadata = getFamilyInfo(familyCode)
    #TODO: handle 'None' for desiredFeatures: implies all
    #print "meta: " + str(familyMetadata.features)
    #print "desired: " + str(desiredFeatures)
    # TODO: check if desired is list and convert to set...
    if len(familyMetadata.features) < 1:
        rv = False
    else:
        rv = bool(familyMetadata.features & desiredFeatures)
    #print("isDesiredSensor result is " + str(rv))
    return rv

def getSensorDescription(sensorId):
    tokenized = sensorId.partition('.')
    familyCode = tokenized[0].strip('/')
    familyMetadata = getFamilyInfo(familyCode)
    return familyMetadata.description
    
