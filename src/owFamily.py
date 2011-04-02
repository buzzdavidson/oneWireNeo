__author__ = 'sdavidson'

import enum
import re

FEATURES = enum.Enum('Temperature', 'Humidity', 'Pressure', 'Counter', 'Voltage', 'Current', 'Sense', 'Pio', 'Memory', 'Clock', 'Illumination', 'UV', 'CO2', "LCD")

class OwFamily:
    def __init__(self, familyCode, description, features = frozenset()):
        self.familyCode = familyCode
        self.description = description
        self.features = features
        # TODO

    def __str__(self):
        return "%s: Family Code: %s, Features: %s" % (self.description, self.familyCode, self.features)

class OwFamilyHelper:
    def __init__(self):
        self.__UNKNOWN_FAMILY = OwFamily('FF', 'Unknown Family Code')

        # Available features, by family
        self.__FAMILY_FEATURES = {
            '01' : OwFamily('01', 'ID Only Tag'),
            '02' : OwFamily('02', 'Memory Button', frozenset([FEATURES.Memory])),
            '04' : OwFamily('04', 'Real Time Clock', frozenset([FEATURES.Memory, FEATURES.Clock, FEATURES.Counter])),
            '05' : OwFamily('05', 'Addressable Switch', frozenset([FEATURES.Pio, FEATURES.Sense])),
            '06' : OwFamily('06', 'Memory Button', frozenset([FEATURES.Memory])),
            '08' : OwFamily('08', 'Memory Button', frozenset([FEATURES.Memory])),
            '09' : OwFamily('09', 'Memory Button', frozenset([FEATURES.Memory])),
            '0A' : OwFamily('0A', 'Memory Button', frozenset([FEATURES.Memory])),
            '0B' : OwFamily('0B', 'Memory Button', frozenset([FEATURES.Memory])),
            '0C' : OwFamily('0C', 'Memory Button', frozenset([FEATURES.Memory])),
            '0F' : OwFamily('0F', 'Memory Button', frozenset([FEATURES.Memory])),
            '10' : OwFamily('10', 'High Precision Digital Thermometer', frozenset([FEATURES.Temperature])),
            '12' : OwFamily('12', 'Dual Addressable Switch', frozenset([FEATURES.Temperature, FEATURES.Pressure, FEATURES.Voltage, FEATURES.Sense, FEATURES.Pio, FEATURES.Memory])),
            '14' : OwFamily('14', 'Quad A/D Converter', frozenset([FEATURES.Memory])),
            '18' : OwFamily('18', 'Monetary Button with SHA-1', frozenset([FEATURES.Memory])),
            '1B' : OwFamily('1B', 'Battery ID/Monitor', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Counter])),
            '1C' : OwFamily('1C', 'EEPROM with Address Inputs', frozenset([FEATURES.Sense, FEATURES.Pio, FEATURES.Memory])),
            '1D' : OwFamily('1D', 'RAM with Counter', frozenset([FEATURES.Memory, FEATURES.Counter])),
            '1E' : OwFamily('1E', 'Smart Battery Monitor', frozenset([FEATURES.Temperature, FEATURES.Clock, FEATURES.Voltage])),
            '1F' : OwFamily('1F', 'MicroLAN Coupler'),
            '20' : OwFamily('20', 'Quad A/D Converter', frozenset([FEATURES.Temperature, FEATURES.Voltage])),
            '21' : OwFamily('21', 'Thermachron Temperature Logging iButton', frozenset([FEATURES.Temperature, FEATURES.Clock])),
            '22' : OwFamily('22', 'Economy Digital Thermometer', frozenset([FEATURES.Temperature])),
            '23' : OwFamily('23', 'EEPROM', frozenset([FEATURES.Memory])),
            '24' : OwFamily('24', 'Real Time Clock', frozenset([FEATURES.Clock])),
            '26' : OwFamily('26', 'Smart Battery Monitor', frozenset([FEATURES.Temperature, FEATURES.Pressure, FEATURES.Voltage, FEATURES.Humidity, FEATURES.Clock, FEATURES.Illumination])),
            '27' : OwFamily('27', 'Time Chip', frozenset([FEATURES.Clock])),
            '28' : OwFamily('28', 'Programmable Resolution Digital Thermometer', frozenset([FEATURES.Temperature])),
            '29' : OwFamily('29', '8 Channel Addressable Switch', frozenset([FEATURES.Pio, FEATURES.Sense, FEATURES.LCD])),
            '2C' : OwFamily('2C', 'Digital Potentiometer'),
            '2D' : OwFamily('2D', 'EEPROM', frozenset([FEATURES.Memory])),
            '2E' : OwFamily('2E', 'Battery Monitor and Charge Controller', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
            '30' : OwFamily('30', 'Hi-Precision Li+ Battery Monitor', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
            '35' : OwFamily('35', 'Multi-Chemistry Battery Fuel Gauge', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
            '36' : OwFamily('36', 'High-Precision Columb Counter', frozenset([FEATURES.Voltage, FEATURES.Sense, FEATURES.Pio])),
            '37' : OwFamily('37', 'Password Protected Memory Button', frozenset([FEATURES.Memory])),
            '3A' : OwFamily('3A', 'Dual Channel Addressable Switch', frozenset([FEATURES.Sense, FEATURES.Pio])),
            '3B' : OwFamily('3B', 'Digital Thermometer with ID', frozenset([FEATURES.Temperature])),
            '3D' : OwFamily('3D', 'Stand-Alone Fuel Gauge', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
            '42' : OwFamily('42', 'Digital Thermometer with Sequence Detect and PIO', frozenset([FEATURES.Temperature, FEATURES.Sense, FEATURES.Pio])),
            '43' : OwFamily('43', 'EEPROM', frozenset([FEATURES.Memory])),
            '51' : OwFamily('51', 'Multi-Chemistry Battery Fuel Gauge', frozenset([FEATURES.Temperature, FEATURES.Voltage, FEATURES.Current, FEATURES.Sense, FEATURES.Pio])),
            'EE' : OwFamily('EE', 'HobbyBoards Microprocessor-Based Slave with Temperature', frozenset([FEATURES.Temperature,FEATURES.UV])),
            'EF' : OwFamily('EF', 'HobbyBoards Microprocessor-Based Slave', frozenset([FEATURES.UV])),
            'FF' : self.__UNKNOWN_FAMILY
        }

        # TODO: duplicate value to standard key IIF (a) std key doesnt exist, (b) one value exists in category
        # TODO: add facility to standardize: mem pages= pages.0, etc
        self.__FAMILY_DEFAULTS = {
            FEATURES.Temperature: 'temperature',
            FEATURES.Humidity: 'humidity',
            FEATURES.Pressure: 'pressure',
            FEATURES.Counter: 'counter',
            FEATURES.Voltage: 'voltage'
        }

        self.__SOURCE_PATTERNS = {
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

        #print("Compiling pattern matchers")
        self.finderMatchers = dict()
        for key, value in self.__SOURCE_PATTERNS.items():
            matcherList = list()
            for pattern in value:
                matcherList.append(re.compile(pattern, re.IGNORECASE))
            self.finderMatchers[key] = matcherList
            #print("[%s] contains %d patterns" % (key, matcherList.__len__()))

    def getFamilyInfo(self, code):
        return self.__FAMILY_FEATURES.get(code, self.__UNKNOWN_FAMILY)

    def getMatchingAttributes(self, inputData, desiredFeatures):
        # always include the basics: family, id, type
        retval = dict()
        self.__addAttributes(inputData, ['id', 'family', 'type'], retval)
        # then add matching entries for each feature in desiredFeatures
        for feature in desiredFeatures:
            self.__addAttributes(inputData, self.__getKeysForFeature(inputData, feature), retval)

        return retval

    def __addAttributes(self, inputData, attrs, outputData):
        for attr in attrs:
            if inputData.has_key(attr):
                outputData[attr.lower()] = inputData[attr]

    def __getKeysForFeature(self, inputData, feature):
        retval = set()
        matchList = self.finderMatchers[feature]
        for key in inputData.iterkeys():
            for matcher in matchList:
                if matcher.match(key):
                    print("Feature %s matched key %s" % (feature, key))
                    retval.add(key)
                    break
        return retval;

    def getDesiredSensors(self, sensorList, desiredFeatures):
        retval = set()
        for sensor in sensorList:
            tokenized = sensor.partition('.')
            familyCode = tokenized[0]
            familyMetadata = self.getFamilyInfo(familyCode)
            if familyMetadata.features & desiredFeatures:
                retval.add(sensor)
        return retval;
    