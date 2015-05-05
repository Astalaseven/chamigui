import logging
import time

import requests
import requests.packages.urllib3 as urllib3
from BeautifulSoup import BeautifulSoup as bs

from db import Db
from utils import *

urllib3.disable_warnings()

class Course(object):

    def __init__(self, name=None, url=None, folders=None, date='1960-01-01 00:00:00'):
        self.name = name
        self.url = url
        self.folders = folders
        self.date = date

    @property
    def year(self):
        if '12' in self.url:
            return 1
        elif '34' in self.url:
            return 2
        elif '56' in self.url:
            return 3
        else:
            return 0
    
    @property
    def id(self):
        return extract_id(self.url)

class Folder(object):

    def __init__(self, name=None, location=None, course=None, parent=None):
        self.name = name
        self.location = location
        self.course = course
        self.parent = parent

class File(object):

    def __init__(self, folder=None, course=None, name=None, date=None, url=None):
        self.name = name
        self.folder = folder 
        self.course = course
        self.date = date
        self.url = url
    

class Chami(object):

    def __init__(self, username=None, password=None, site_url=None):
        self.username = username
        self.password = password
        self.site_url = 'https://elearning.esi.heb.be'
        self.db = Db()

        self.session = requests.Session()

    def connect(self, username=None, password=None, ssl_verify=False):
        payload = {'login': username, 'password': password}

        return not 'user_password_incorrect' in self.session.post(self.index_url, data=payload, verify=ssl_verify).url

    def disconnect(self):
        self.session.get('{}/index.php?logout=logout'.format(self.site_url))

    @property
    def index_url(self):
        return '%s/%s' % (self.site_url, 'index.php')

    @property
    def courses_url(self):
        return '%s/%s' % (self.site_url, 'main/auth/courses.php?action=display_courses&category_code=ALL&hidden_links=0')

    @property
    def my_courses_url(self):
        return '%s/%s' % (self.site_url, 'user_portal.php')

    def get_courses(self):
        html = self.session.get(self.courses_url, verify=False).content
        soup = bs(html).find('body', {'class': 'section-mycourses '})

        for course in soup.findAll('div', {'class': 'span4'}):
            # if course in span and has link to access it
            if course.find('div', {'class': 'categories-course-description'}) \
                and course.find('a', {'class': 'btn btn-primary'}):
                    name = course.find('h3').text
                    url = course.find('a', {'class': 'btn btn-primary'})['href']

                    print(name, url)

                    self.db.insert_course(Course(name, url))
        
        return self.db.select_courses()

    def get_my_courses(self):
        def extract_course_id(url):
            return url.split('/')[4]

        html = self.session.get(self.my_courses_url, verify=False).content
        soup = bs(html).find('section', {'id': 'main_content'})

        for course in soup.findAll('div', {'class': 'well course-box'}):
            self.db.insert_my_course(extract_course_id(course.find('a')['href']))

        return self.db.select_my_courses()

    def download(self):
        course = self.courses[2]
        print("course url " + course.url)


    def update_db(self, courses):

        for course in courses:

            # # Initialize a pool, 5 threads in this case
            # pool = workerpool.WorkerPool(size=5)

            # # Loop over urls.txt and create a job to download the URL on each line
            # for url in open("urls.txt"):
            #     job = DownloadJob(url.strip())
            #     pool.put(job)

            # # Send shutdown jobs to all threads, and wait until all the jobs have been completed
            # pool.shutdown()
            # # pool.wait()

            print('update_db_course', course, time.strftime('%Y-%m-%d %H:%M:%S'))
            self.course_folders(course_id=course)
            self.db.update_course(course, date=time.strftime('%Y-%m-%d %H:%M:%S'))


    def courses_to_be_updated(self):
        courses_to_update = []
        for course in self.db.select_courses():
            print(course)
            date_updated_course = course[2]
            course_url = '%s/main/document/document.php?cidReq=%s' % (self.site_url, course[0])

            soup = bs(self.session.get(course_url).content)

            if soup.find('table', {'class': 'data_table'}):
                folders = soup.find('table', {'class': 'data_table'}).findAll('tr')[1:] # don't take first line
                for folder in folders:
                    date_updated_folder = folder.find('small').text

                    if date_updated_folder > date_updated_course:
                        #print('Needs to be updated!')
                        courses_to_update.append(course[0])
                        break
        print('{} courses need to be updated'.format(len(courses_to_update)))

        return courses_to_update



    def course_folders(self, url=None, course_id=None):
        if not course_id:
            course_id = extract_id(url)

        doc_url = '%s/main/document/document.php?cidReq=%s' % (self.site_url, course_id)

        print('doc_url', doc_url)
        soup = bs(self.session.get(doc_url).content)

        s_folders = soup.findAll('option')

        level = 0
        parents = [None] * 50

        for folder in s_folders:

            name = folder.text
            location = folder['value']

            if 'DELETED' in name:
                continue

            folder_level = convert_folder_level(name)

            if folder_level > 0:
                parent = parents[folder_level - 1]
            else:
                parent = None

            parents[folder_level] = location
            actual_level = folder_level            

            self.db.insert_folder(Folder(clean_folder_name(name), location, course_id, parent))

            self.folder_files(location, course_id)


    def folder_files(self, folder_location, course_id):
        folder_url = '%s/main/document/document.php?id=%s&cidReq=%s' % (self.site_url, folder_location, course_id)

        soup = bs(self.session.get(folder_url).content)
        soup = soup.find('table', {'class': 'data_table'})

        # do not check first line of table
        if soup:
            for line in soup.findAll('tr')[1:]:
                href = line.find('a')['href']
                # is link downloadable?
                if 'courses' in href and 'document' in href:
                    #print(line)
                    url = line.find('a')['href']
                    name = line.find('a')['title']
                    date = line.find('small').text

                    #print(url, name, date)

                    #print(folder_location, course_id, name, date, url)
                    self.db.insert_file(File(folder_location, course_id, name, date, url))
                    #print('folders', self.db.select_folders(course_id='TMP34RAGR'))
                    #print(self.db.select_files(course_id='TMP34RAGR', folder='/'))
                    #exit()
                    #print(line.find('a')['href'])
    

if __name__ == '__main__':
    chami = Chami()

    #print(chami.index_url)
    #chami.update_courses()
    # print("preupdate")
    # chami.update_db()
    # print("postupdate")

    chami.get_my_courses()
