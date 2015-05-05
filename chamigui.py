import logging
import os
from Queue import Queue
import sys
import time
import threading

from PySide import QtCore, QtGui
from PySide.QtCore import *
from PySide.QtGui import *

from gui import Ui_MainWindow
from chami import Chami
from utils import local_path

# python2 /usr/local/lib/python3.2/dist-packages/PySide/scripts/uic.py gui.ui -o gui.py -x

# Queue used to store the urls to download
queue = Queue()


class ChamiGUI(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.tv1model = QStandardItemModel()
        self.tv2model = QStandardItemModel()

        self.chami = Chami()
        self.db = self.chami.db

        self.setMyCoursesTreeView()
        self.setAllCoursesTreeView()


        # Starts the url consommer/downloader thread/queue
        self.downloader = Downloader()
        self.downloader.updateProgress.connect(self.set_progress)
        self.downloader.start()

        self.ui.downloadButton.setEnabled(False)
        self.ui.downloadButton.clicked.connect(lambda: self.download())
        self.ui.connectButton.clicked.connect(lambda: self.connect())
        self.ui.searchButton.clicked.connect(lambda: self.search())
        
        self.ui.searchLineEdit.returnPressed.connect(lambda: self.search())
        self.ui.passLineEdit.returnPressed.connect(lambda: self.connect())

        self.ui.action_Update_db.triggered.connect(lambda: self.update_db())


    def update_db(self):
        thread = threading.Thread(target=self._update_db)
        thread.daemon = True
        thread.start()


    def _update_db(self):
        chami = Chami()
        chami.connect(self.ui.userLineEdit.text(), self.ui.passLineEdit.text())

        courses = chami.courses_to_be_updated()
        chami.update_db(courses)
        self.ui.statusbar.showMessage('Updating {} courses...'.format(len(courses)), 6000)
        

    def set_progress(self, url, remaining, percent):
        if remaining > 0:
            self.ui.statusbar.showMessage('Remaining files: {0} ({1}% of {2})'.format(remaining, percent, local_path(url)))
        else:
            self.ui.statusbar.showMessage('Download complete!')


    def connect(self):
        username = self.ui.userLineEdit.text()
        # if user enters 12345 or g12345 instead of G12345
        username = username.upper()
        if not 'G' in username:
            username = 'G' + username
            self.ui.userLineEdit.setText(username)

        connect = self.chami.connect(username, self.ui.passLineEdit.text())
        print('connected:', connect)
        if not connect:
            self.ui.statusbar.showMessage('Something went wrong when connecting, check user/password', 6000)
            self.ui.userLineEdit.setStyleSheet('QLineEdit { color: red }')
            self.ui.passLineEdit.setStyleSheet('QLineEdit { color: red }')
            self.ui.downloadButton.setEnabled(False)
        else:
            self.ui.statusbar.showMessage('Successfully connected!', 6000)
            self.ui.downloadButton.setEnabled(True)

            self.ui.connectButton.setText('Disconnect')
            self.ui.userLineEdit.setEnabled(False) #setStyleSheet('QLineEdit { color: green }')
            self.ui.passLineEdit.setEnabled(False) #setStyleSheet('QLineEdit { color: green }')
            self.ui.connectButton.clicked.connect(lambda: self.disconnect())

            self.downloader.set_session(self.chami.session)

    def disconnect(self):
        self.chami.disconnect()

        self.ui.statusbar.showMessage('Disconnected.', 6000)
        self.ui.downloadButton.setEnabled(False)

        self.ui.connectButton.setText('Connect')
        self.ui.userLineEdit.setEnabled(True)
        self.ui.passLineEdit.setEnabled(True)
        self.ui.connectButton.clicked.connect(lambda: self.connect())


    def search(self):
        self.setMyCoursesTreeView(self.ui.searchLineEdit.text())
        self.setAllCoursesTreeView(self.ui.searchLineEdit.text())

    def download(self):
        global queue

        for selectedIndex in (self.ui.treeView.selectedIndexes() + self.ui.treeView_2.selectedIndexes()):
            print(selectedIndex.data())
            urls = self.children_folders(selectedIndex.data(), selectedIndex, [])

            if selectedIndex.data() and urls and urls[0]:
                for url in urls:
                    print('Queueing {}'.format(url))
                    queue.put(url)

        # for j in jobs:
        #     print(j.url, j.status)

        # urls = [j.url for j in jobs if j.status == 403]

        # print(urls)

        # if urls:
        #     #msgBox = QMessageBox()
                #QMessageBox.warning(self, 'Download error', 'Some files could not be downloaded.', buttons=QMessageBox.Ok)
        #     #msgBox.setText('Some files could not be downloaded.')
        #     #msgBox.exec_()


    def parent_folder(self, folder, index, liste):
        parent = index.parent()
        liste.append(folder)
        
        if parent.data():
            self.parent_folder(parent.data(), parent, liste)
            return liste


    def children_folders(self, folder, index, liste):
        # XXX: refactoring really needed
        if self.ui.coursesTabWidget.currentIndex() == 0:
            if self.tv2model.itemFromIndex(index) and self.tv2model.itemFromIndex(index).rowCount() == 0:
                # could not find how to access url directly, has to use parent...
                item = self.tv2model.itemFromIndex(index)
                row = item.row()
                url = index.parent().child(row, 2).data()

                return [url]

            for row in range(self.tv2model.itemFromIndex(index).rowCount()):
                folder = index.child(row,0).data()
                
                if self.tv2model.itemFromIndex(index.child(row,0)).rowCount() > 0:
                    #print('recursive', folder)
                    self.children_folders(folder, index.child(row,0), liste)
                else:
                    url = index.child(row,2).data()
                    if url:
                        #print('appending', index.child(row,0).data())
                        liste.append(url)

        else:

            if self.tv1model.itemFromIndex(index) and self.tv1model.itemFromIndex(index).rowCount() == 0:
                # could not find how to access url directly, has to use parent...
                item = self.tv1model.itemFromIndex(index)
                row = item.row()
                url = index.parent().child(row, 2).data()

                return [url]

            for row in range(self.tv1model.itemFromIndex(index).rowCount()):
                folder = index.child(row,0).data()
                
                if self.tv1model.itemFromIndex(index.child(row,0)).rowCount() > 0:
                    #print('recursive', folder)
                    self.children_folders(folder, index.child(row,0), liste)
                else:
                    url = index.child(row,2).data()
                    if url:
                        #print('appending', index.child(row,0).data())
                        liste.append(url)

        return liste

    def setMyCoursesTreeView(self, regex=None):
        self.tv2model.clear()
        self.tv2model = self.setTreeView(self.db.select_my_courses(regex))

        self.ui.treeView_2.setModel(self.tv2model)
        self.ui.treeView_2.setSortingEnabled(True) # enable sorting
        self.ui.treeView_2.sortByColumn(1, Qt.SortOrder(Qt.AscendingOrder)) # sort by course name, A-Z
        self.ui.treeView_2.setSelectionMode(QAbstractItemView.ExtendedSelection) # single selection or Ctrl
        self.ui.treeView_2.header().setResizeMode(QHeaderView.ResizeToContents) # auto resize columns
        self.ui.treeView_2.setEditTriggers(QAbstractItemView.NoEditTriggers) # don't allow to change names
            
    def setAllCoursesTreeView(self, regex=None):
        self.tv1model.clear()
        self.tv1model = self.setTreeView(self.db.select_courses(regex))

        self.ui.treeView.setModel(self.tv1model)
        self.ui.treeView.setSortingEnabled(True) # enable sorting
        self.ui.treeView.sortByColumn(1, Qt.SortOrder(Qt.AscendingOrder)) # sort by course name, A-Z
        self.ui.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection) # single selection or Ctrl
        self.ui.treeView.header().setResizeMode(QHeaderView.ResizeToContents) # auto resize columns
        self.ui.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers) # don't allow to change names

    def setTreeView(self, courses):
        def append_folders(course_id=None, parent_folder=None, parent=None):

            folders = self.db.select_folders(course_id, parent_folder)

            for folder in folders:
                qsi_folder = append_files(course_id, folder[0], QStandardItem(folder[1]))

                parent.appendRow(append_folders(course_id, folder[0], qsi_folder))

            return parent

        def append_files(course_id=None, parent_folder=None, folder=None):

            files = self.db.select_files(course_id, parent_folder)

            for filee in files:
                folder.appendRow([QStandardItem(filee[2]), QStandardItem(filee[3]), QStandardItem(filee[4])])

            return folder


        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Course ID', 'Course Name', 'URL'])

        for course in courses:

            course_id = course[0]
            course = self.db.select_course(course_id)[0]

            parent = append_folders(course_id, '/', QStandardItem(course_id))

            model.appendRow([parent, QStandardItem(course[1])])

        return model

class Downloader(QtCore.QThread):
    #This is the signal that will be emitted during the processing.
    #By including int as an argument, it lets the signal know to expect
    #an integer argument when emitting.
    updateProgress = QtCore.Signal(str, int, int)

    def __init__(self, session=None):
        QtCore.QThread.__init__(self)
        self.session = session

    def set_session(self, session):
        self.session = session

    def run(self):
        global queue
        while True:
            url = queue.get()

            file_path = local_path(url)
            folder_path = '/'.join(file_path.split('/')[:-1])

            print('Consumming url... {}'.format(url))

            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path)
                except OSError:
                    print('Race condition', 'Who\'s there?')

            if not os.path.exists(file_path):
                r = self.session.get(url, stream=True, verify=False)

                if r.status_code == 200:
                    file_size = int(r.headers['content-length'])

                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(1024):
                            f.write(chunk)

                            file_percent = 100 * os.path.getsize(file_path) / file_size
                            if file_percent > 100:
                                file_percent = 100
                            self.updateProgress.emit(url, queue.unfinished_tasks, file_percent)


            queue.task_done()
            print('Task done, {} consummed'.format(url))
            print(queue.unfinished_tasks, url)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myapp = ChamiGUI()
    myapp.show()
    sys.exit(app.exec_())
