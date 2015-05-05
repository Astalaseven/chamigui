def extract_id(url):
    return url.split('/')[-2]

def clean_folder_name(folder):
    return folder.split('&mdash; ')[-1]

def convert_folder_level(name):
    folder_level = name.count('&nbsp;') + name.count('&mdash;')

    return (folder_level + 2) / 3

def local_path(url):
    url = '/'.join([url.split('/')[4]] + url.split('/')[6:])
    return url
