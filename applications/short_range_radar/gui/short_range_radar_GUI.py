import sys
from PyQt5.QtGui import QIcon
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication, QDialog, QInputDialog, QMainWindow, QVBoxLayout, QFileDialog , QMessageBox
from PyQt5.QtCore import QSize, QTimer 
from PyQt5 import uic
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from time import sleep, time
import struct
import csv

class ObjectDetecter():

    def __init__(self, max_range_,n_horizontal_zones_):
        self.max_range = max_range_
        self.n_horizontal_zones = n_horizontal_zones_
        self.n_zones = self.max_range * self.n_horizontal_zones

        self.zones_n_hits = np.zeros((self.max_range, self.n_horizontal_zones))
        self.iteration_hit = np.zeros((self.max_range, self.n_horizontal_zones))

    def discretize(self, range, azimuth):
        ind_1 = int(np.floor(self.max_range - range))
        ind_2 = 0
        if 15 < azimuth < 45:
            ind_2 = 4
        elif 45 < azimuth < 75:
            ind_2 = 3
        elif 75 < azimuth < 115:
            ind_2 = 2
        elif 115 < azimuth < 145:
            ind_2 = 1
        else:
            ind_2 = 0
        return ind_1, ind_2

    def update(self, r_points, azimuth_points):
        self.iteration_hit[:, :] = 0
        for r, az in zip(r_points, azimuth_points):
            ind_1, ind_2 = self.discretize(r, az)
            self.iteration_hit[ind_1, ind_2] = 1
        ind_hits = (self.iteration_hit == 1)
        ind_no_hits = (self.iteration_hit == 0)
        self.zones_n_hits[ind_hits] += 1
        self.zones_n_hits[ind_no_hits] = 0

        ind_object_detected = np.argwhere(self.zones_n_hits > 3)
        return ind_object_detected

class Ventana(QMainWindow):
    
    # Método constructor de la clase
    def __init__(self):
        # Iniciar el objeto QMainWindow
        QMainWindow.__init__(self)
        # Cargar la configuración del archivo .ui en el objeto
        uic.loadUi("./resources/ui/uRAD_GUI_v1.0.ui", self)

        pg.setConfigOption('background', 'w')
        pg.setConfigOptions(antialias=False)

        # Declaramos algunas variables como globales para que puedan ser utilizadas por los distintos métodos de la clase
        global run, debugProtocol, fileName , visible , numDetectedObj, playbackTimestamp, playbackNumOfPoints, playbackPointCloud, playbackIteration, runningPlayback, max_range, angle_zones, detectedObjZones, objetDetector, plotsToRemove
        run = False
        visible = True
        numDetectedObj = 0
        fileName = ''
        playbackIteration = 0
        debugProtocol = False
        runningPlayback = False
        max_range = 10
        angle_zones = 5
        detectedObjZones = np.zeros((max_range,angle_zones))
        objetDetector = ObjectDetecter(max_range,angle_zones)
        plotsToRemove = []

        # Conectamos el botón de refrescar los puertos serie con su SLOT correspondiente
        self.refreshConfigPortButton.clicked.connect(self.update_config_ports_list)
        self.refreshDataPortButton.clicked.connect(self.update_data_ports_list) 
        # Conectamos el botón de Run/Stop con el método "run_stop_code"
        self.runStopButton.toggled.connect(self.run_stop_code)
        self.visibility.clicked.connect(self.check_visibility)

        # Conectamos el botón de SaveData sus métodos correspondientes
        self.toolButton.clicked.connect(self.select_results_file)
        self.toolButtonPlayback.clicked.connect(self.select_playback_file)
       
        # Insertamos en los comboBox configPort y dataPort la lista de puertos serie disponibles
        self.update_data_ports_list()
        self.update_config_ports_list()

        # Declaramos y configuramos el puerto serie.
        global configPort, dataPort
        configPort = serial.Serial()
        configPort.baudrate = 115200
        configPort.timeout = 2
        configPort.bytesize = serial.EIGHTBITS
        configPort.parity = serial.PARITY_NONE
        configPort.stopbits = serial.STOPBITS_ONE
        configPort.xonxoff = False
        configPort.rtscts = False
        configPort.dsrdtr = False
        configPort.write_timeout = 2
        dataPort = serial.Serial()
        dataPort.baudrate = 921600
        dataPort.timeout = 2
        dataPort.bytesize = serial.EIGHTBITS
        dataPort.parity = serial.PARITY_NONE
        dataPort.stopbits = serial.STOPBITS_ONE
        dataPort.xonxoff = False
        dataPort.rtscts = False
        dataPort.dsrdtr = False
        dataPort.write_timeout = 2

        # Creamos la gráfica y aplicamos estilos
        global XYPlot
        font = QtGui.QFont()
        font.setPixelSize(15)
        MyFigure = QVBoxLayout(self.widgetXY)
        MyWindow = pg.QtGui.QMainWindow()
        MyView = pg.GraphicsLayoutWidget()
        MyWindow.setCentralWidget(MyView)
        XYPlot = MyView.addPlot()
        XYPlot.setMouseEnabled(x=False, y=False)
        XYPlot.setMenuEnabled(False)
        XYPlot.showGrid(y=True)
        XYPlot.showGrid(x=True)
        #XYPlot.setXRange(-10, 10)
        #XYPlot.setYRange(0, 10)
        XYPlot.setAspectLocked()
        
        labelStyle = {'color': '#000', 'font-size': '15px'}
        XYPlot.setLabel('left', 'Y (m)', **labelStyle)
        XYPlot.setLabel('bottom', 'X (m)', **labelStyle)
        XYPlot.hideButtons()
      
        XYPlot.getAxis("left").setTickFont(font)
        XYPlot.addLegend(offset=(0., .5))
        XYPlot.getAxis("left").setTextPen('k')
        XYPlot.getAxis("bottom").setTickFont(font)
        XYPlot.getAxis("bottom").setTextPen('k')
        MyFigure.addWidget(MyWindow)
      

    # Métodos que actualizan las listas desplegables que contienen los puertos disponibles
    def update_data_ports_list(self):
        self.PortsListData.clear()
        ports = list(serial.tools.list_ports.comports())
        index = 0
        for i in range(len(ports)):
            if ("Standard" in ports[i].description):
                index = i
                self.PortsListData.insertItem(i, ports[i].device + ' Standard')
            else:
                self.PortsListData.insertItem(i, ports[i].device)
        self.PortsListData.setCurrentIndex(index)

    def check_visibility(self):
        global visible  
        if visible == True:
            visible = False
            self.background1.setVisible(False)
            
        elif visible == False:
            visible = True
            self.background1.setVisible(True)
            
    
    def update_config_ports_list(self):
        self.PortsListConfig.clear()
        ports = list(serial.tools.list_ports.comports())
        index = 0
        for i in range(len(ports)):
            if ("Enhanced" in ports[i].description):
                index = i
                self.PortsListConfig.insertItem(i, ports[i].device + ' Enhanced')
            else:
                self.PortsListConfig.insertItem(i, ports[i].device)
        self.PortsListConfig.setCurrentIndex(index)
    
    # Enviamos la configuración
    def openRadar(self, configPort, dataPort):
        global max_range_selected, max_azimuth_selected

        configPort.open()
        dataPort.open()
        dataPort.reset_output_buffer()

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
            'aoaFovCfg -1 %d %d -150 150\n' % (-max_azimuth_selected/2, max_azimuth_selected/2),
            'cfarFovCfg -1 0 0 %d\n' % (max_range_selected),
            'cfarFovCfg -1 1 -4.68 4.68\n',
            'calibData 0 0 0\n',
            'sensorStart\n'
        ]

        response = bytearray([])
        while(configPort.in_waiting > 0):
            response += configPort.read(1)
        if (debugProtocol):
            print(response.decode())

        for i in range(len(commands)):
            configPort.write(bytearray(commands[i].encode()))
            sleep(20e-3)
            response = bytearray([])
            while(configPort.in_waiting > 0):
                response += configPort.read(1)
            if (debugProtocol):
                print(response.decode())
        
        success = True

        return success

    def getRadarData(self, dataPort):

        packetHeader = bytearray([])

        syncPattern = 0x708050603040102

        tlvHeaderLen = 8
        headerLen = 40
        max_iterations = 20

        success = False
        iterations = 0

        while(not success and iterations < max_iterations):

            timePacket = time()

            packetHeader += dataPort.read(headerLen-len(packetHeader))

            iterations += 1

            sync, version, totalPacketLen, platform, frameNumber, timeCpuCycles, numDetectedObj, numTLVs, subFrameNumber =  struct.unpack('Q8I', packetHeader[:headerLen])

            if (sync == syncPattern):

                packetHeader = bytearray([])
                packetPayload = dataPort.read(totalPacketLen-headerLen)

                detectedObjects = np.zeros((numDetectedObj, 6))
                if (debugProtocol):
                    print('numDetectedObj: %d' % numDetectedObj)

                for i in range(numTLVs):

                    tlvType, tlvLength = struct.unpack('2I', packetPayload[:tlvHeaderLen])
                    if (debugProtocol):
                        print('tlvType: %d, tlvLength: %d' % (tlvType, tlvLength))

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

                            if (debugProtocol):
                                print('x: %1.3f m, y: %1.3f m, z: %1.3f m, v: %1.3f m/s, snr: %d, noise: %d' % (detectedObjects[j, 0], detectedObjects[j, 1], detectedObjects[j, 2], detectedObjects[j, 3], detectedObjects[j, 4], detectedObjects[j, 5]))

                            packetPayload = packetPayload[4:]
                    
                    elif (tlvType == 6):

                        interFrameProcessingTime, transmitOutputTime, interFrameProcessingMargin, interChirpProcessingMargin, activeFrameCPULoad, interFrameCPULoad = struct.unpack('6I', packetPayload[:24])
                        packetPayload = packetPayload[tlvLength:]
                    
                    elif (tlvType == 9):

                        tempReportValid, tempDataTime, tmpRx0Sens, tmpRx1Sens, tmpRx2Sens, tmpRx3Sens, tmpTx0Sens, tmpTx1Sens, tmpTx2Sens, tmpPmSens, tmpDig0Sens, tmpDig1Sens = struct.unpack('iI10h', packetPayload[:28])
                        packetPayload = packetPayload[tlvLength:]

                success = True

            else:
                packetHeader = packetHeader[1:]
            
        if success:
            return timePacket, detectedObjects
        else:
            return False

    # Método que controla la captura de tramas IQ, es llamado por la señal emitida por el botón de Run/Stop
    def run_stop_code(self, booleanState):
        global run, max_range_selected, max_azimuth_selected
        run = booleanState
        if (run):
            max_range_selected = int(self.MaxRange_Desired.currentText())
            max_azimuth_selected = int(self.MaxAzimuth_Desired.currentText())
            self.MaxRange_Desired.setEnabled(False)
            self.MaxAzimuth_Desired.setEnabled(False)
            self.runStopButton.setText("Stop")
            self.plot_auxilary_lines()
            self.run_code()
        else:
            #self.MaxRange_Desired.setEnabled(True)
            #self.MaxAzimuth_Desired.setEnabled(True)
            self.runStopButton.setText("Run")

    def run_code(self):

        global configPort, dataPort , numDetectedObj, max_range_selected, max_azimuth_selected
        
        # Si no está el radar configurado, configurarlo
        if (not dataPort.isOpen()):

            PortName = self.PortsListConfig.currentText()
            configPort.port = PortName.split()[0]
            PortName = self.PortsListData.currentText()
            dataPort.port = PortName.split()[0]

            success = self.openRadar(configPort, dataPort)

        timePacket, PointCloud = self.getRadarData(dataPort)
        numDetectedObj = PointCloud.shape[0]

        condition = []
        if (numDetectedObj > 0):

            x = PointCloud[:numDetectedObj, 0]
            y_original = PointCloud[:numDetectedObj, 1]
            y = y_original - 1
            z = PointCloud[:numDetectedObj, 2]
            v = PointCloud[:numDetectedObj, 3]
            snr = PointCloud[:numDetectedObj, 4]
            noise = PointCloud[:numDetectedObj, 5]

            r = (x**2+y**2)**(1/2)
            az = np.sign(y)*np.arccos(x/np.sqrt(x**2 + y**2)) * 180/np.pi

            condition = np.logical_and.reduce((y > 0, r < max_range_selected, (az - 90) < max_azimuth_selected/2, (az - 90) > -max_azimuth_selected/2))

            x_filtered = x[condition]
            y_filtered = y[condition]
            r_filtered = r[condition]
            az_filtered = az[condition]

            detectedObjZones[:,:] = 0
            ind_object_detected = objetDetector.update(r_filtered, az_filtered)
            detectedObjZones[ind_object_detected] = 1

            self.plot_points_and_zones(x_filtered, y_filtered, ind_object_detected)

        if (fileName != '' and self.SaveDataCheckBox.isChecked()):
            try:
                fileID = open(fileName, "a")
                PointCloud_str = ''
                    
                for i in range(numDetectedObj):
                    PointCloud_str += '%1.3f %1.3f %1.3f %1.3f %d %d ' % (x[i],y_original[i],z[i],v[i],snr[i], noise[i])

                fileID.write(PointCloud_str + '%1.3f\n' % timePacket)
                fileID.close()
            except:
                print('Error saving file')
                raise
        
        if run:
            timer = QTimer()
            timer.singleShot(10, self.run_code)
        else:
            # Detener ejecución radar y cerrar puertos
            dataPort.close()
            stop_command = 'sensorStop\n'
            configPort.write(bytearray(stop_command.encode()))
            sleep(20e-3)
            response = bytearray([])
            while(configPort.in_waiting > 0):
                response += configPort.read(1)
            if (debugProtocol):
                print(response.decode())
            configPort.close()

    def plot_auxilary_lines(self):
        XYPlot.clear()

        r_max = max_range_selected
        az_max = max_azimuth_selected/2

        az1 = 15
        az2 = 45
        az3 = 75

        # Internal lines
        x1 = r_max*np.sin(-az1*np.pi/180)
        y1 = r_max*np.cos(-az1*np.pi/180)
        x2 = r_max*np.sin(az1*np.pi/180)
        y2 = r_max*np.cos(az1*np.pi/180)

        XYPlot.plot((0, x1), (0, y1), pen=pg.mkPen((42, 150, 125), width=2))
        XYPlot.plot((0, x2), (0, y2), pen=pg.mkPen((42, 150, 125), width=2))

        # Medium lines
        if (max_azimuth_selected >= 90):
            x1 = r_max*np.sin(-az2*np.pi/180)
            y1 = r_max*np.cos(-az2*np.pi/180)
            x2 = r_max*np.sin(az2*np.pi/180)
            y2 = r_max*np.cos(az2*np.pi/180)

            XYPlot.plot((0, x1), (0, y1), pen=pg.mkPen((42, 150, 125), width=2))
            XYPlot.plot((0, x2), (0, y2), pen=pg.mkPen((42, 150, 125), width=2))

        # External lines
        if (max_azimuth_selected == 150):
            x1 = r_max*np.sin(-az3*np.pi/180)
            y1 = r_max*np.cos(-az3*np.pi/180)
            x2 = r_max*np.sin(az3*np.pi/180)
            y2 = r_max*np.cos(az3*np.pi/180)

            XYPlot.plot((0, x1), (0, y1), pen=pg.mkPen((42, 150, 125), width=2))
            XYPlot.plot((0, x2), (0, y2), pen=pg.mkPen((42, 150, 125), width=2))

        plots = []
        for r in range(1,r_max+1):
            x1 = r*np.sin(-az_max*np.pi/180)
            x2 = r*np.sin(az_max*np.pi/180)
            x_radius = np.linspace(x1, x2, num=51)
            y_radius = (r**2-x_radius**2)**(1/2)

            p = XYPlot.plot(x_radius, y_radius, pen=pg.mkPen((42, 150, 125), width=2))
            plots.append(p)

    def plot_points_and_zones(self, x, y, ind_object_detected):
        global plotsToRemove
        # Clear plots and zones
        for p in plotsToRemove:
            XYPlot.removeItem(p)
        plotsToRemove = []

        # Plot points
        points_plot = XYPlot.plot(x, y, pen=(0,0,0,0), symbolBrush=(0,0,0,255), symbolSize=8)
        plotsToRemove.append(points_plot)

        # Fil zones
        brush_red = pg.mkBrush(255,0,0,200)
        brush_orange = pg.mkBrush(255,173,3,200)
        brush_yellow = pg.mkBrush(252,227,3,200)

        for ind in ind_object_detected:
            r_ind_low = max_range - ind[0] - 1
            az_ind = ind[1]
            az_left = 0
            az_right = 0
            if az_ind == 0:
                az_left = -75
                az_right = -45
            elif az_ind == 1:
                az_left = -45
                az_right = -15
            elif az_ind == 2:
                az_left = -15
                az_right = 15
            elif az_ind == 3:
                az_left = 15
                az_right = 45
            elif az_ind == 4:
                az_left = 45
                az_right = 75

            # Fill
            #Low range
            x1 = r_ind_low*np.sin(az_left*np.pi/180)
            x2 = r_ind_low*np.sin(az_right*np.pi/180)
            x_radius = np.linspace(x1, x2, num=51)
            y_radius = (r_ind_low**2-x_radius**2)**(1/2)

            p1 = pg.PlotDataItem(x_radius, y_radius, pen=pg.mkPen((255,0,0), width=2))

            x1 = (r_ind_low + 1)*np.sin(az_left*np.pi/180)
            x2 = (r_ind_low + 1)*np.sin(az_right*np.pi/180)
            x_radius = np.linspace(x1, x2, num=51)
            y_radius = ((r_ind_low + 1)**2-x_radius**2)**(1/2)
            
            p2 = pg.PlotDataItem(x_radius, y_radius, pen=pg.mkPen((255,0,0), width=2))

            if r_ind_low <= max_range_selected/3:
                brush_ = brush_red
            elif max_range_selected/3 < r_ind_low <= (max_range_selected/3) * 2:
                brush_ = brush_orange
            else:
                brush_ = brush_yellow

            fill = pg.FillBetweenItem(p1, p2, brush=brush_)
            XYPlot.addItem(fill)
            plotsToRemove.append(fill)

    def run_playback_file(self):
        global max_range_selected, max_azimuth_selected, playbackIteration, max_range, max_azimuth
        
        #playbackTimestamp
        numOfPoints = int(playbackNumOfPoints[playbackIteration])
        x = playbackPointCloud[playbackIteration, :numOfPoints, 0]
        y = playbackPointCloud[playbackIteration, :numOfPoints, 1] - 1
        z = playbackPointCloud[playbackIteration, :numOfPoints, 2]
        v = playbackPointCloud[playbackIteration, :numOfPoints, 3]

        r = (x**2+y**2)**(1/2)
        az = np.sign(y)*np.arccos(x/np.sqrt(x**2 + y**2)) * 180/np.pi

        condition = np.logical_and.reduce((y > 0, r < max_range_selected, (az - 90) < max_azimuth_selected/2, (az - 90) > -max_azimuth_selected/2))

        x = x[condition]
        y = y[condition]
        z = z[condition]
        r = r[condition]
        az = az[condition]

        detectedObjZones[:,:] = 0
        ind_object_detected = objetDetector.update(r, az)
        detectedObjZones[ind_object_detected] = 1

        self.plot_points_and_zones(x, y, ind_object_detected)
        
        playbackIteration += 1

        # setting for loop to set value of progress bar
        self.progressBar.setValue(int(100*playbackIteration/len(playbackTimestamp)))
  
        if (playbackIteration >= len(playbackTimestamp) or not runningPlayback):
           
            #self.toolButtonPlayback.setEnabled(True)
            self.runStopButton.setEnabled(True)
            
            # Poner logotipo de Play en Playback button
            self.toolButtonPlayback.setIcon(QIcon('./resources/images/playback.png'))
        
        else:

            timer = QTimer()
            timer.singleShot(50, self.run_playback_file)
            
            

    def select_results_file(self):
        global fileName
        fileName = QFileDialog.getSaveFileName(self, "Save file", "./", ".txt")
        fileName = fileName[0] + fileName[1]

    def read_playback_file(self, filepath):

        # Open file to count lines (iterations)
        with open(filepath) as csv_file:
            # Data is stored as a csv delimited by spaces
            csv_reader = csv.reader(csv_file, delimiter=';')
            # initialize iteration counter
            line_count = 0
            # iterate through all the rows
            for row in csv_reader:
                # increment iteration counter
                line_count += 1
        
        # Initialize output variables
        timestamp = np.zeros(line_count)
        numOfPoints = np.zeros(line_count)
        PointCloud = np.zeros((line_count, 100, 6))

        # Open again the file to write variables
        with open(filepath) as csv_file:
            # Data is stored as a csv delimited by spaces
            csv_reader = csv.reader(csv_file, delimiter=' ')
            # initialize iteration counter
            line_count = 0
            
            
            # iterate through all the rows
            for row in csv_reader:
                
                # extract number of detected points (6 data fields per detected point)
                numOfPoints[line_count] = int(np.floor((len(row)-1)/6))
                # extract timestamp
                timestamp[line_count] = row[-1]
                
            
                for i in range(int(numOfPoints[line_count])):
                    
                    PointCloud[line_count, i, :] = np.array(row[i*6:(i+1)*6], dtype=np.float64)

                # increment iteration counter
                line_count += 1
                
                #print(line_count)
                #print('Import: %1.1f' % (100*line_count/len(numOfPoints)))
            
        return timestamp, numOfPoints, PointCloud

    def select_playback_file(self):

        global runningPlayback

        if (not run):

            if (not runningPlayback):
                print(run, runningPlayback)
                global fileName, playbackTimestamp, playbackNumOfPoints, playbackPointCloud, playbackIteration, max_range_selected, max_azimuth_selected
                fileName = QFileDialog.getOpenFileName(self, "Open File", "../", "*.txt")
                #fileName = fileName[0] + fileName[1]
                fileName = fileName[0]
                if fileName != "":
                    max_range_selected = int(self.MaxRange_Desired.currentText())
                    max_azimuth_selected = int(self.MaxAzimuth_Desired.currentText())
                    print(max_range_selected, max_azimuth_selected)
                    self.MaxRange_Desired.setEnabled(False)
                    self.MaxAzimuth_Desired.setEnabled(False)
                    playbackTimestamp, playbackNumOfPoints, playbackPointCloud = self.read_playback_file(fileName)
                    if (len(playbackTimestamp) > 0):
                        # Poner logotipo de Pause en Playback button
                        self.toolButtonPlayback.setIcon(QIcon('./resources/images/stop.png'))
                        self.toolButtonPlayback.setIconSize(QSize(200, 60))
                        playbackIteration = 0
                        #self.toolButtonPlayback.setEnabled(False)
                        self.runStopButton.setEnabled(False)
                        runningPlayback = True
                        self.plot_auxilary_lines()
                        self.run_playback_file()
            else:
                runningPlayback = False

# Instancia para iniciar una aplicación
app = QApplication(sys.argv)

# Crear un objeto de la clase
_ventana = Ventana()

# Mostrar la ventana
_ventana.show()

# Ejecutamos la aplicación
app.exec_()
