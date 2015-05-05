import sqlite3
import os

class Db(object):

    def __init__(self, db='chami.sqlite'):
        self.db = db
        self.conn = sqlite3.connect(db)

        #self.create_table()

    def create_table(self):
        c = self.conn.cursor()

        c.execute('''PRAGMA foreign_keys = ON''')

        c.execute('''DROP TABLE IF EXISTS course''')
        c.execute('''DROP TABLE IF EXISTS folder''')
        c.execute('''DROP TABLE IF EXISTS file''')

        c.execute('''CREATE TABLE IF NOT EXISTS course
                 (cId text PRIMARY KEY, libelle text, update_date text DEFAULT '1960-01-01 00:00:00')''')

        c.execute('''CREATE TABLE IF NOT EXISTS folder
                 (fId text, libelle text, cId text, parent text, PRIMARY KEY(fId, cId))''')

        c.execute('''CREATE TABLE IF NOT EXISTS file 
                 (fId text, cId text, filename text, update_date text, url text UNIQUE)''')

        c.execute('''CREATE TABLE IF NOT EXISTS mycourses
                 (cId text PRIMARY KEY REFERENCES course(cId))''')

        self.conn.commit()

    def insert_course(self, course):
        c = self.conn.cursor()
        c.execute('''INSERT OR IGNORE INTO course VALUES (?, ?, ?)''', (course.id, course.name, course.date))

        self.conn.commit()

    def insert_my_course(self, cId):
        c = self.conn.cursor()
        c.execute('''INSERT OR IGNORE INTO mycourses VALUES (?)''', (cId,))

        self.conn.commit()

    def insert_folder(self, folder):
        c = self.conn.cursor()

        c.execute('''INSERT OR IGNORE INTO folder VALUES (?, ?, ?, ?)''', (folder.location, folder.name, folder.course, folder.parent))

        self.conn.commit()

    def insert_file(self, filee):
        c = self.conn.cursor()
        #print('unique url ', filee.url)
        try:
            c.execute('''INSERT OR IGNORE INTO file VALUES (?, ?, ?, ?, ?)''', (filee.folder, filee.course, filee.name, filee.date, filee.url))
        except sqlite3.IntegrityError:
            print('ERROR URL')
            pass

        self.conn.commit()

    def select_courses(self, regex=None):
        c = self.conn.cursor()
        if regex:
            c.execute('''SELECT * FROM course WHERE cId LIKE :r OR libelle LIKE :r''', {'r': '%' + regex + '%'})
        else:
            c.execute('''SELECT * FROM course''')

        return c.fetchall()

    def select_my_courses(self, regex=None):
        c = self.conn.cursor()
        request = '''SELECT * FROM course INNER JOIN mycourses WHERE course.cId = mycourses.cId'''
        if regex:
            request += ''' AND cId LIKE :r OR libelle LIKE :r''', {'r': '%' + regex + '%'}
        
        c.execute(request)

        return c.fetchall()

    def select_course(self, course_id):
        c = self.conn.cursor()
        c.execute('''SELECT * FROM course WHERE cId = :cId''', {'cId': course_id})

        return c.fetchall()

    def select_folders(self, course_id=None, parent=None):
        c = self.conn.cursor()

        params = {}
        statement = '''SELECT * FROM folder WHERE cId = :cId'''
        params['cId'] = course_id

        if parent:
            statement += ''' AND parent = :parent'''
            params['parent'] = parent

        c.execute(statement, params)

        return c.fetchall()

    def select_files(self, course_id=None, folder=None, url=None):
        c = self.conn.cursor()

        statement = '''SELECT * FROM file'''
        where = []
        params = {}

        if course_id is not None:
            where.append('cId = :course_id')
            params['course_id'] = course_id

        if folder is not None:
            where.append('fId = :folder')
            params['folder'] = folder

        if url is not None:
            where.append('url = :url')
            params['url'] = url

        if where:
            statement = '{} WHERE {}'.format(statement, ' AND '.join(where))

        c.execute(statement, params)

        return c.fetchall()

    def update_course(self, course, date=None):
        print('db update course', course, date)
        c = self.conn.cursor()

        c.execute('''UPDATE course SET update_date = ? WHERE cId = ?''', (date, course))



# # Save (commit) the changes
# conn.commit()

# # We can also close the connection if we are done with it.
# # Just be sure any changes have been committed or they will be lost.
# conn.close()
