#################################################################
#################################################################
############### Copyright 2009 Corey Clayton ####################
#################################################################
#################################################################
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

VERSION = 1.0


import sys, os, zlib
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from ui_dupfind import Ui_dupfind
from datetime import datetime

# create a global dictionary object that will map 
# file sizes to a list of files of that size
sDict = {}
#and one for hashes mapped to filenames
hDict = {}
#a reverse mapping: path -> hash
rMap = {}

iLst = []

class StartQt4(QtGui.QMainWindow):
	def __init__(self, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.thread = Worker()
		self.ui = Ui_dupfind()
		self.ui.setupUi(self)
		self.ui.treeWidget_dup.setSortingEnabled(True)
		# here we connect signals with our slots
		QtCore.QObject.connect(self.ui.pushButton_browse, QtCore.SIGNAL("clicked()"), self.file_dialog)
		QtCore.QObject.connect(self.ui.pushButton_scan, QtCore.SIGNAL("clicked()"), self.do_scan)
		QtCore.QObject.connect(self.ui.treeWidget_dup, QtCore.SIGNAL("itemClicked(QTreeWidgetItem *,int)"), self.dupItem_click)
		QtCore.QObject.connect(self.thread, SIGNAL("addItem_dup(QString)"), self.addItem_dup)
		QtCore.QObject.connect(self.thread, SIGNAL("statMsg(QString)"), self.statMsg)
		QtCore.QObject.connect(self.ui.actionAbout, QtCore.SIGNAL("triggered()"), self.aboutMe)
		
	def file_dialog(self):
		fd = QtGui.QFileDialog(self)
		fd.setFileMode(QtGui.QFileDialog.Directory)
		fd.setOption(QtGui.QFileDialog.ShowDirsOnly)
		d = fd.getExistingDirectory()
		self.ui.lineEdit_dir.setText(d)
		
	def do_scan(self):
		#clear everything
		sDict.clear
		hDict.clear
		rMap.clear
		
		self.ui.treeWidget_dup.clear()
		self.thread.scan(str(self.ui.lineEdit_dir.text()))
		
	def dupItem_click(self, item):
		self.ui.listWidget_all.clear()
		h = rMap[str(item.text(0))]
		for dup in hDict[h]:
			QtGui.QListWidgetItem(dup, self.ui.listWidget_all)
	
	def addItem_dup(self, string):
		fstat = os.stat(str(string))
		item = QtGui.QTreeWidgetItem()
		#file name
		item.setText(0, string)
		#file size
		fsize = fstat.st_size
		
		if fsize > 2 ** 30:
			item.setText(1, str(fsize/2**30) + " GiB")
		elif fsize > 2 ** 20:
			item.setText(1, str(fsize/2**20) + " MiB")
		elif fsize > 2 ** 10:
			item.setText(1, str(fsize/2**10) + " KiB")
		else:
			item.setText(1, str(fsize) + " Bytes")
		
		#mtime
		item.setText(2, str(datetime.fromtimestamp(fstat.st_mtime)))
		
		#ctime
		item.setText(3, str(datetime.fromtimestamp(fstat.st_ctime)))
		
		#atime
		item.setText(4, str(datetime.fromtimestamp(fstat.st_atime)))
		
		self.ui.treeWidget_dup.addTopLevelItem(item)
		iLst.append(item)
		
	def statMsg(self, string):
		#self.ui.statusbar.clearMessage()
		self.ui.statusbar.showMessage(string)
		
	def aboutMe(self):
		msg = QtGui.QMessageBox();
		msg.setText("DupFind version " + str(VERSION) + "\n\n:-)")
		msg.exec_()
			
class Worker(QThread):
	def __init__(self, parent = None):
		QThread.__init__(self, parent)
		self.exiting = False
		#do init here
	def __del__(self):
		self.exiting = True
		self.wait()
	def scan(self, path):
		self.dirpath = path
		self.start()
		
	def run(self):
		#here is the meat
		#this is the scan part
		self.walkdir(self.dirpath)
		for k, v in sDict.iteritems():
			if len(v) > 1:
				print "possible duplicates found:"
				for fname in v:
					h = self.genHash(fname)
					print "--> " + fname + " [" + str(h) + "]"
					if (h in hDict) == False: # we have a new hash
						hDict[h] = [fname]
					else: #append name to existing list for hash
						hDict[h].append(fname)
		for k, v in hDict.iteritems():
			if len(v) > 1:
				for fname in v:
					rMap[fname] = k
				self.emit(SIGNAL("addItem_dup(QString)"), v[0])
				
		self.emit(SIGNAL("statMsg(QString)"), "Done.")
				
	def walkdir(self, path, recursive=True):
		self.emit(SIGNAL("statMsg(QString)"), "Scanning directory: " + path)
		w = os.walk(path)
		try:
			wtpl = w.next()
		except StopIteration:
			print "generator depleted!"
		for name in wtpl[2]:
			st = os.stat(path + '/' + name)
			if (st.st_size in sDict) == False: #if this filesize is not in the dictionary
				#add it to the dict in a new list with size as a key
				sDict[st.st_size] = [path + '/' + name]
			else: #key exists, append to list
				sDict[st.st_size].append(path + '/' + name) 
			print "adding [" + str(st.st_size) + ":" + name + "]"
		if recursive==True:
			for d in wtpl[1]:
				self.walkdir(str(path + '/' + d))
				
	def genHash(self, path):
		self.emit(SIGNAL("statMsg(QString)"), "Hashing file: " + path)
		#crc32
		f = open(path)
		buff = f.read()
		f.close()
		return zlib.crc32(buff)
		
		
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = StartQt4()
    myapp.show()
    sys.exit(app.exec_())
