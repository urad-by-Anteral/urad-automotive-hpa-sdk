import serial
import struct
import numpy as np
from time import time, sleep
import sys
from object_detector import ObjectDetecter

savePointCloud = True
saveDetectionZones = True
printPointCloud = False

#############################################################
### CONFIGURATION PARAMETERS ###
max_azimuth = 90	# View angle of the radar. Possible values are 30, 90 or 150 
max_range = 4		# Detection max range of the radar. Possible values are 4, 6, 8 or 10

### COMUNICATION PARAMETERS ###
configPort_name = 'COM26'
dataPort_name = 'COM25'

### OUTPUT FILES ###
pointCloud_fileName = './output_files/PointCloud.txt'
detectedZones_fileName = './output_files/DetectedZones.txt'
#############################################################

syncPattern = 0x708050603040102

possible_ranges = [4,6,8,10]
possible_azimuth = [30,90,150]
if max_range not in possible_ranges or max_azimuth not in possible_azimuth:
	sys.exit("Range or value not set corretly")

try:

	commands = [
            'flushCfg\n',
            'dfeDataOutputMode 1\n',
            'channelCfg 15 1 0\n',
            'adcCfg 2 1\n',
            'adcbufCfg -1 0 1 1 1\n',
            'profileCfg 0 77 8 7 200 0 0 20 1 384 2000 0 0 30\n',
            'chirpCfg 0 0 0 0 0 0 0 1\n',
            'chirpCfg 1 1 0 0 0 0 0 0\n',
            'frameCfg 0 0 32 0 33.33 1 0\n',
            'lowPower 0 0\n',
            'guiMonitor -1 1 0 0 0 0 0\n',
            'cfarCfg -1 0 2 8 4 3 0 15 1\n',
            'cfarCfg -1 1 0 8 4 4 1 15 1\n',
            'multiObjBeamForming -1 1 0.5\n',
            'clutterRemoval -1 0\n',
            'calibDcRangeSig -1 0 -5 8 256\n',
            'extendedMaxVelocity -1 1\n',
            'lvdsStreamCfg -1 0 0 0\n',
            'compRangeBiasAndRxChanPhase 0.0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0\n',
            'measureRangeBiasAndRxChanPhase 0 1.5 0.2\n',
            'CQRxSatMonitor 0 3 19 125 0\n',
            'CQSigImgMonitor 0 127 6\n',
            'analogMonitor 0 0\n',
            'aoaFovCfg -1 %d %d -150 150\n' % (-max_azimuth/2, max_azimuth/2),
            'cfarFovCfg -1 0 0 %d\n' % (max_range),
            'cfarFovCfg -1 1 -4.68 4.68\n',
            'calibData 0 0 0\n',
            'sensorStart\n'
        ]

	#print('Opening ports')
	configPort = serial.Serial(configPort_name, 115200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.3)
	dataPort = serial.Serial(dataPort_name, 921600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.3)
	dataPort.reset_output_buffer()

	response = bytearray([])
	while(configPort.in_waiting > 0):
		response += configPort.read(1)
	print(response.decode())

	for i in range(len(commands)):
		configPort.write(bytearray(commands[i].encode()))
		sleep(20e-3)
		response = bytearray([])
		while(configPort.in_waiting > 0):
			response += configPort.read(1)
		print(response.decode())

	packetHeader = bytearray([])

	tlvHeaderLen = 8
	headerLen = 40

	max_range_total = 10
	angle_zones = 5
	n_zones = max_range_total * angle_zones
	detectionZones = np.zeros((max_range_total,angle_zones))
	objetDetector = ObjectDetecter(max_range_total,angle_zones)

	while(True):

		timePacket = time()

		packetHeader += dataPort.read(headerLen-len(packetHeader))

		sync, version, totalPacketLen, platform, frameNumber, timeCpuCycles, numDetectedObj, numTLVs, subFrameNumber =  struct.unpack('Q8I', packetHeader[:headerLen])

		if (sync == syncPattern):

			packetHeader = bytearray([])
			packetPayload = dataPort.read(totalPacketLen-headerLen)

			detectedObjects = np.zeros((numDetectedObj, 6))
			print('numDetectedObj: %d' % numDetectedObj)

			for i in range(numTLVs):

				tlvType, tlvLength = struct.unpack('2I', packetPayload[:tlvHeaderLen])

				if (tlvType > 20 or tlvLength > 10000):
					packetHeader = bytearray([])
					break

				packetPayload = packetPayload[tlvHeaderLen:]

				if (tlvType == 1):

					for j in range(numDetectedObj):

						x, y, z, v = struct.unpack('4f', packetPayload[:16])
						
						detectedObjects[j, 0] = x
						detectedObjects[j, 1] = y
						detectedObjects[j, 2] = z
						detectedObjects[j, 3] = v

						packetPayload = packetPayload[16:]

				elif (tlvType == 7):

					for j in range(numDetectedObj):

						snr, noise = struct.unpack('2H', packetPayload[:4])

						detectedObjects[j, 4] = snr
						detectedObjects[j, 5] = noise

						if (printPointCloud):
							print('x: %1.3f m, y: %1.3f m, z: %1.3f m, v: %1.3f m/s, snr: %d, noise: %d' % (detectedObjects[j, 0], detectedObjects[j, 1], detectedObjects[j, 2], detectedObjects[j, 3], detectedObjects[j, 4], detectedObjects[j, 5]))

						packetPayload = packetPayload[4:]

			x = detectedObjects[:numDetectedObj, 0]
			y = detectedObjects[:numDetectedObj, 1] - 1

			condition = (y>0)
			x = x[condition]
			y = y[condition]

			r = (x**2+y**2)**(1/2)
			az = np.sign(y)*np.arccos(x/np.sqrt(x**2 + y**2)) * 180/np.pi

			detectionZones[:,:] = 0
			ind_object_detected = objetDetector.update(r, az)
			detectionZones[ind_object_detected] = 1

			if (savePointCloud):
				if (numDetectedObj > 0):
					results_string = ''
					for j in range(numDetectedObj):
						results_string += '%1.3f %1.3f %1.3f %1.3f %d %d ' % (detectedObjects[j, 0], detectedObjects[j, 1], detectedObjects[j, 2], detectedObjects[j, 3], detectedObjects[j, 4], detectedObjects[j, 5])
					filePoints = open(pointCloud_fileName, 'a')
					filePoints.write(results_string + '%1.3f\n' % timePacket)
					filePoints.close()

			if (saveDetectionZones):
				flat_zones = detectionZones.flatten()
				results_string = ''
				for j in range(n_zones):
					results_string += '%d ' % (flat_zones[j])
				fileZones = open(detectedZones_fileName, 'a')
				fileZones.write(results_string + '%1.3f\n' % timePacket)
				fileZones.close()

			if (numTLVs > 0):
				print(' ')

		else:
			packetHeader = packetHeader[1:]

except:

	print('Closing ports')
	configPort.close()
	dataPort.close()
	raise
