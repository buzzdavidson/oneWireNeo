__author__ = 'sdavidson'
import unittest
import onewireneo
from onewireneo import FEATURES

class OneWireNeoTests(unittest.TestCase):
    def testGetFamilyInfo(self):
        thermoFamily = onewireneo.getFamilyInfo('10')
        assert(thermoFamily.familyCode == '10')
        assert(FEATURES.Temperature in  thermoFamily.features)
        assert(thermoFamily.description == 'High Precision Digital Thermometer')

    def testGetFamilyInfoString(self):
        thermoFamily = onewireneo.getFamilyInfo('20');
        assert(str(thermoFamily) == 'Quad A/D Converter: Family Code: 20, Features: [Temperature, Voltage]')

    def getTestData_ds18s20(self):
        return {
            'id': '10.147A0A020800',
            'power' : '1',
            'family' : '10',
            'locator': 'FFFFFFFFFFFF',
            'type': 'DS18S20',
            'crc8': '00',
            'temphigh': '48.125',
            'templow':'12.8',
            'temperature': '37.2'
        }

    def getTestData_ds2405(self):
        return {
            'id': '05.147A0A020800',
            'power' : '1',
            'family' : '05',
            'locator': 'FFFFFFFFFFFF',
            'type': 'DS2405',
            'crc8': '00',
            'PIO': '0',
            'Sensed': '1'
        }

    def getTestData_ds2406(self):
        mem = self.getMemoryBytes(128)
        return {
            'id': '12.000012ED0000',
            'power' : '1',
            'family' : '12',
            'type': 'DS2406',
            'crc8': '00',
            'channels': '2',
            'memory': mem,
            'Pio.a': '1',
            'Pio.b': '0',
            'Pio.all': '1',
            'Pio.byte': '1',
            'sensed.a': '1',
            'sensed.b': '0',
            'sensed.ALL': '1',
            'sensed.BYTE': '1',
            'pages/page.0': self.getMemoryPage(mem, 32, 0),
            'pages/page.1': self.getMemoryPage(mem, 32, 1),
            'pages/page.2': self.getMemoryPage(mem, 32, 2),
            'pages/page.3': self.getMemoryPage(mem, 32, 3),
            'pages/page.ALL': mem,
            'TAI8570/pressure': '192.5',
            'TAI8570/sibling': '12.000012EFFFFF',
            'TAI8570/temperature': '22.875',
            'T8A/volt.0': '4.75',
            'T8A/volt.1': '4.85',
            'T8A/volt.2': '4.65',
            'T8A/volt.3': '4.95',
            'T8A/volt.4': '5.01',
            'T8A/volt.5': '4.98',
            'T8A/volt.6': '0',
            'T8A/volt.7': '1.375'
        }

    def getMemoryBytes(self, count):
        cyclestring='1234567890ABCDEF'
        output = list()
        i = 0
        while i < count:
            output.append(cyclestring[i % len(cyclestring)])
            i += 1
        return ''.join(output)

    def getMemoryPage(self, inputData, bytesPerPage, pageNumber):
        start = pageNumber * bytesPerPage
        end = start + bytesPerPage
        return inputData[start:end]

    def getTestData_ds2404(self):
        mem = self.getMemoryBytes(512)
        testData = {
            'id': '04.147A0A020800',
            'power' : '1',
            'family' : '04',
            'locator': 'FFFFFFFFFFFF',
            'type': 'DS2404',
            'crc8': '00',
            'cycle': '12',
            'date': '2011/04/03 23:12:57',
            'delay': '0',
            'memory': mem,
            'udate': '1301872377'
        }
        for i in range(0, 15):
            testData['pages/page.%d' % i] = self.getMemoryPage(mem, 32, i)
        return testData


    def testFam10Finders(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds18s20(), [FEATURES.Temperature])
        assert(len(outData) == 4)
        assert(outData['id'] == '10.147A0A020800')
        assert(outData['family'] == '10')
        assert(outData['type'] == 'DS18S20')
        #assert(outData['temphigh'] == '48.125')
        #assert(outData['templow'] == '12.8')
        assert(outData['temperature'] == '37.2')

    def testFam10Finders_emptyRequestGetsBaseItems(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds18s20(), [])
        assert(len(outData) == 3)
        assert(outData['id'] == '10.147A0A020800')
        assert(outData['family'] == '10')
        assert(outData['type'] == 'DS18S20')

    def testFam10Finders_wrongFamilyGetsBaseItems(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds18s20(), [FEATURES.Current])
        assert(len(outData) == 3)
        assert(outData['id'] == '10.147A0A020800')
        assert(outData['family'] == '10')
        assert(outData['type'] == 'DS18S20')

    def testDs2404_memory(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2404(), [FEATURES.Memory])
        assert(len(outData) == 18)
        assert(outData['type'] == 'DS2404')
        for i in range(0,14):
            keyname = 'pages/page.%d' % i
            assert(outData.has_key(keyname))
            assert(outData[keyname] == '1234567890ABCDEF1234567890ABCDEF')
        

    def testDs2404_clock(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2404(), [FEATURES.Clock])
        assert(len(outData) == 5)
        assert(outData['date'] == '2011/04/03 23:12:57')
        assert(outData['udate'] == '1301872377')

    def testDs2404_counter(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2404(), [FEATURES.Counter])
        assert(len(outData) == 4)
        assert(outData['cycle'] == '12')

    def testDs2404_clockAndCounter(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2404(), [FEATURES.Clock, FEATURES.Counter])
        assert(len(outData) == 6)
        assert(outData['date'] == '2011/04/03 23:12:57')
        assert(outData['udate'] == '1301872377')
        assert(outData['cycle'] == '12')

    def testDs2405(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2405(), [FEATURES.Pio, FEATURES.Sense])
        assert(len(outData) == 5)
        assert(outData['pio'] == '0')
        assert(outData['sensed'] == '1')

    def testGetDesiredSensors(self):
        sensorList = ['01.FFFFFFFFFFFF', '10.147A0A020800', '35.431246AA4FBA', '43.FACBACC12343']
        testList = onewireneo.getDesiredSensors(sensorList, set([FEATURES.Temperature]))
        assert(len(testList) == 2)
        assert('10.147A0A020800' in testList)
        assert('35.431246AA4FBA' in testList)

    def testAagTai8570_temperature(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2406(), [FEATURES.Temperature])
        assert(len(outData) == 5)
        assert(outData['tai8570/temperature'] == '22.875')
        # TODO: this should add a 'temperature' attribute if not present - client should not be aware of idiosyncrasies

    def testAagTai8570_pressure(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2406(), [FEATURES.Pressure])
        assert(len(outData) == 5)
        assert(outData['tai8570/pressure'] == '192.5')
        # TODO: this should add a 'pressure' attribute if not present - client should not be aware of idiosyncrasies

    def testAagTai8570_voltage(self):
        outData = onewireneo.getMatchingAttributes(self.getTestData_ds2406(), [FEATURES.Voltage])
        assert(len(outData) == 12)
        assert(outData['t8a/volt.0'] == '4.75')
        assert(outData['t8a/volt.1'] == '4.85')
        assert(outData['t8a/volt.2'] == '4.65')
        assert(outData['t8a/volt.3'] == '4.95')
        assert(outData['t8a/volt.4'] == '5.01')
        assert(outData['t8a/volt.5'] == '4.98')
        assert(outData['t8a/volt.6'] == '0')
        assert(outData['t8a/volt.7'] == '1.375')

    def getAagTai8570_properties(self):
        return  ['id', 'power', 'family', 'type', 'crc8', 'channels', 'memory', 'Pio.a', 'Pio.b', 'Pio.all', 'Pio.byte',
        'sensed.a', 'sensed.b', 'sensed.ALL', 'sensed.BYTE', 'pages/page.0', 'pages/page.1', 'pages/page.2',
        'pages/page.3', 'pages/page.ALL', 'TAI8570/pressure', 'TAI8570/sibling', 'TAI8570/temperature', 'T8A/volt.0',
        'T8A/volt.1', 'T8A/volt.2', 'T8A/volt.3', 'T8A/volt.4', 'T8A/volt.5', 'T8A/volt.6', 'T8A/volt.7']

    def testGetDesiredAttributes_temp(self):
        outData = onewireneo.getDesiredAttributes(self.getAagTai8570_properties(), [FEATURES.Temperature])
        assert(len(outData) == 5)
        assert('id' in outData);
        assert('family' in outData);
        assert('type' in outData);
        assert('TAI8570/temperature' in outData);

    def testIsDesiredSensor_sepchars(self):
        testSensor = '/10.5D4470010800/'
        check = onewireneo.isDesiredSensor(testSensor,set([FEATURES.Temperature]))
        assert(check);

    #def testFoo(self):
        #tester = onewireneo.OneWireNeo('192.168.0.42:4304', [FEATURES.Temperature, FEATURES.Humidity, FEATURES.Pressure])


    # TODO: DS1963S, family code 18
    # TODO: DS2423, family code 1D
    # TODO: DS2437, family code 1E
    # TODO: DS2450, family code 20
    # TODO: DS2438, family code 26
    # TODO: DS2408, family code 29
    # TODO: DS2760, family code 30 (weather station)
    # TODO: DS2740, family code 36
    # TODO: HobbyBoards UV

if __name__ == '__main__':
    unittest.main()




