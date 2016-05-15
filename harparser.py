import sys, getopt
import json
import subprocess
import haralyzer
import os
import shutil
from subprocess import Popen
import re
import time
import numpy as np
import matplotlib.pyplot as plt
# har_location = "/home/ankitmit/har_files/"
# base_folder_location = "/home/ankitmit/Downloads/har_files_extracted/"
# profile_pref_file = "/home/ankitmit/.mozilla/firefox/jebepgb1.default-1463121075190/prefs.js"
# memory_list_file = "/home/ankitmit/Dropbox/StonyBrook/FCN/fcn_project/memory_list"
# sites_list_file = '/home/ankitmit/Dropbox/StonyBrook/FCN/fcn_project/top5_sites'
# cache_dir = '/home/ankitmit/.cache/mozilla/firefox/jebepgb1.default-1463121075190/cache2/entries/'

har_location = ''#"C:/Users/ankmittal/fcn_proj/har_files/"
base_folder_location = ''#"C:/Users/ankmittal/fcn_proj/har_files_extracted/"
profile_pref_file = ''#"C:/Users/ankmittal/AppData/Roaming/Mozilla/Firefox/Profiles/rxcg6djm.default/prefs.js"
memory_list_file = ''#"C:/Users/ankmittal/fcn_proj/code/memory_list"
sites_list_file = ''#"C:/Users/ankmittal/fcn_proj/code/top5_sites"
cache_dir = ''#"C:/Users/ankmittal/AppData/Local/Mozilla/Firefox/Profiles/rxcg6djm.default/cache2/entries/"

profile_path = None
current_result_dir = ""
cached = 0
memory_list = []
iteration = 0

def parseCommandLineArguments(argv):
    global har_location, base_folder_location,profile_pref_file, memory_list_file, sites_list_file, cache_dir
    try:
        opts, args = getopt.getopt(argv, 'h:b:p:m:s:c::')
    except getopt.GetoptError:
        print("Invalid arguments. Exiting the program")
        sys.exit(0)
    for opt, arg in opts:
        if opt == '-h':
            har_location = arg
        elif opt == '-b':
            base_folder_location = arg
        elif opt == '-p':
            profile_pref_file = arg
        elif opt == '-m':
            memory_list_file = arg
        elif opt == '-s':
            sites_list_file = arg
        elif opt == '-c':
            cache_dir = arg

def deleteProfileMemoryline():
    global profile_pref_file
    print("Deleting the existing value of cache memory limit from the prefs.js file")
    f = open(profile_pref_file,'r')
    new_lines = ""
    for line in f.readlines():
        if(line.find("user_pref(\"browser.cache.disk.capacity\"") != 0):
            new_lines += line
    f.close()
    f = open(profile_pref_file,'w')
    f.write(new_lines)
    f.close()

def remove_unwanted_white(str):
		str = re.sub("\s\s+" , " ", str)
		str = str.rstrip()
		str = str.lstrip()
		return str

class HAROut:
    def __init__(self, entry_time, entry_cache_text):
        self.time = entry_time
        self.cache_text = entry_cache_text

def openFireFox():
    global all_process_ids
    # cmd = "/usr/bin/firefox -jsconsole"
    # subprocess.Popen(cmd,  stdout=subprocess.PIPE, shell=True)
    cmd = '"C:\Program Files (x86)\Mozilla Firefox\\firefox.exe" -jsconsole'
    #print (cmd)
    os.popen(cmd)
    time.sleep(2)

def killFireFox():
    all_process_ids = ""
    cmd2 = "ps -eaf | grep firefox"
    proc = subprocess.Popen(cmd2,  stdout=subprocess.PIPE, shell=True)
    tmp = proc.stdout.read()
    all_process = tmp.split('\n')
    all_process_ids  = ""
    for process in all_process:
        process = remove_unwanted_white(process)
        if process != '':
            proc_split = process.split(' ')
            all_process_ids +=  " " + proc_split[1]
    kill_cmd = "kill -9 " + all_process_ids
    #print kill_cmd
    if all_process_ids != "":
        os.system(kill_cmd)

def findCacheType(entry):
    cache_text = None
    headers = entry['response']['headers']
    if len(headers) > 0:
        for header in headers:
            if header['name'] == 'Cache-Control':
                cache_text = header['name'] + ' - ' + header['value']
                return cache_text

def parseHARFile(file_path):
    url_load_time_dict = {}
    f = open(file_path, encoding="utf8")
    f_text = f.read()
    lines  = f_text.split('\n')
    page_id  = ""
    for line in lines:
        if line.find('"pageref":') >= 0:
            page_id_complete = line.split(':')[1]
            page_id_complete = page_id_complete.lstrip()
            page_id_complete = page_id_complete.rstrip()
            page_id = page_id_complete[1:len(page_id_complete) - 2]
            break
    if page_id == "":
        return
    har_page = haralyzer.HarPage(page_id, har_data=json.loads(f_text))
    for entry in har_page.entries:
        url = entry['request']['url']
        cache_text = findCacheType(entry)
        if url not in url_load_time_dict.keys():
            url_load_time_dict[url] = HAROut(entry['time'], cache_text)
    return url_load_time_dict

def generateData():
    global cached, memory_list, iteration, memory_list_file
    #getProfilePath()
    getMemoryList(memory_list_file)
    iteration = 0
    num_iterations = len(memory_list)
    while iteration < num_iterations:
        print("Iteration number :" + str(iteration + 1) + " to generate the HAR files for all the websites")
        deleteProfileMemoryline()
        updatePrefFile(memory_list[iteration])
        clearBrowserCache()
        onePass()
        cached = 1
        onePass()
        cached = 0
        iteration += 1

def createDirstructure():
    global current_result_dir
    os.mkdir(current_result_dir)
    os.mkdir(current_result_dir + "/cached/")
    os.mkdir(current_result_dir + "/uncached/")

def getWebsitesList(file_path):
    f = open(file_path, 'r')
    list_text = f.read()
    sites_list = list_text.split('\n')
    return sites_list

def onePass():
    global base_folder_location,current_result_dir, iteration, sites_list_file
    current_result_dir = base_folder_location + str(iteration)
    if not os.path.exists(current_result_dir):
        createDirstructure()
    if cached == 0:
        current_result_dir += "/uncached/"
    else:
        current_result_dir += "/cached/"

    sites_list = getWebsitesList(sites_list_file)

    for site in sites_list:
        processSingleWebsite(site)

def clearBrowserCache():
    global cache_dir
    print ("Clearing browser cache")
    files = getFilesInDir(cache_dir)
    for file in files:
        file_name = cache_dir + file
        os.remove(file_name)


def clearHARLocation():
    global har_location
    cmd = "rm " + har_location + "*"
    subprocess.call(cmd)

def checkHARFileWritten(path):
    fcount = len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))])
    return fcount > 0

def deleteHARFiles():
    global har_location
    files = getFilesInDir(har_location)
    for f in files:
        os.remove(f)

def getFilesInDir(dir_path):
    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
    return files

def moveHARFile(site_name):
    global har_location, current_result_dir
    file_name = ""
    files = getFilesInDir(har_location)
    for file in files:
        file_name = har_location + file
    dest_location = current_result_dir + site_name +".har"
    shutil.move(file_name, dest_location)
    #deleteHARFiles()

def processSingleWebsite(url):
    global current_result_dir, cached, har_location
    if url == '':
        return
    print ("Opening URL " + str(url))
    openFireFox()
    subprocess.call([r'C:\Program Files (x86)\Mozilla Firefox\\firefox.exe', '-new-tab', url])
    har_file_written = False
    while har_file_written is not True:
        time.sleep(2)
        har_file_written = checkHARFileWritten(har_location)
    os.system("taskkill /f /im firefox.exe")
    url = url.replace('.', '_')
    moveHARFile(url)

def plotGraph(y_values):
    global memory_list,memory_list_file
    if memory_list is None:
        getMemoryList(memory_list_file)
    if y_values is not None:
        plt.plot(memory_list, y_values, linewidth=2.0)
        plt.show()
    else:
        print("None")

def getMemoryList(file_path):
    global memory_list
    f = open(file_path, 'r')
    for line in f.readlines():
        line = line.rstrip()
        memory_list.append(line)

def analyseHARData():
    global base_folder_location
    result_dirs = os.listdir(base_folder_location)
    cached_files_list = []
    uncached_files_list = []
    total_time_cached_dict = {}
    total_time_uncached_dict = {}
    for dir in result_dirs:
        dir = base_folder_location + "/" + dir
        cached_path = dir + "/cached/"
        uncached_path = dir + "/uncached/"
        cached_files = [f for f in os.listdir(cached_path) if os.path.isfile(os.path.join(cached_path, f))]

        for file in cached_files:
            file_name = cached_path + file
            cached_files_list.append(file_name)
        count = 1
        for file in cached_files:
            if file not in total_time_cached_dict.keys():
                total_time_cached_dict[file] = []
            if file not in total_time_uncached_dict.keys():
                total_time_uncached_dict[file] = []
            final_text = ""
            image_cached_sum = 0
            image_uncached_sum = 0
            js_uncached_sum = 0
            js_cached_sum = 0
            css_uncached_sum = 0
            css_cached_sum = 0
            cached_file_name = cached_path + file
            uncached_file_name = uncached_path + file
            if os.path.exists(uncached_file_name):
                analysis_file = dir + "/analysis_file_" + file
                f = open(analysis_file, 'w')
                cached_har_file_details = parseHARFile(cached_file_name)
                uncached_har_file_details = parseHARFile(uncached_file_name)
                diff_text = ""
                image_elements = []
                css_elements = []
                js_elements = []
                if cached_har_file_details is not None and len(cached_har_file_details.keys()) > 0:
                    for key in cached_har_file_details.keys():
                        if key in uncached_har_file_details.keys():
                            if cached_har_file_details[key].cache_text is not None:
                                diff_text = key + ',' + cached_har_file_details[key].cache_text+ ', cached time - ' + str(cached_har_file_details[key].time) + ', uncached time - ' + str(uncached_har_file_details[key].time) +'\n'
                            else:
                                diff_text = key + ', cached time - ' + str(cached_har_file_details[key].time) + ', uncached time - ' + str(uncached_har_file_details[key].time) +'\n'
                            ext = getElementExt(key)
                            if ext is not None:
                                if ext in ['png','jpg', 'gif']:
                                    image_elements.append(diff_text)
                                    image_cached_sum += cached_har_file_details[key].time
                                    image_uncached_sum += uncached_har_file_details[key].time
                                elif ext == 'js':
                                    js_elements.append(diff_text)
                                    js_cached_sum += cached_har_file_details[key].time
                                    js_uncached_sum += uncached_har_file_details[key].time
                                elif ext == 'css':
                                    css_elements.append(diff_text)
                                    css_cached_sum += cached_har_file_details[key].time
                                    css_uncached_sum += uncached_har_file_details[key].time
                    total_uncached_sum = image_uncached_sum + js_uncached_sum + css_uncached_sum
                    total_cached_sum = js_cached_sum + image_cached_sum + css_cached_sum
                    final_text += 'Images:\n'
                    for text in image_elements:
                        final_text += text
                    final_text += 'CSS:\n'
                    for text in css_elements:
                        final_text += text
                    final_text += 'Javascript elements:\n'
                    for text in js_elements:
                        final_text += text
                    f.write(final_text)
                    f.write("=========================================================\n")
                    f.write ("Image Uncached sum - " + str(image_uncached_sum) + '\n' + "Image cached sum - " + str(image_cached_sum) + '\n')
                    f.write ("CSS Uncached sum - " + str(css_uncached_sum) + '\n' + "CSS cached sum - " + str(css_cached_sum) + '\n')
                    f.write ("JS Uncached sum - " + str(js_uncached_sum) + '\n' + "JS cached sum - " + str(js_cached_sum) + '\n')
                    f.write ("Total Uncached sum - " + str(total_uncached_sum) + '\n' + "Total cached sum - " + str(total_cached_sum) + '\n')
                    total_time_cached_dict[file].append(total_cached_sum)
                    total_time_uncached_dict[file].append(total_uncached_sum)
                count += 1
    for key in total_time_uncached_dict.keys():
        lst = total_time_uncached_dict[key]
        if lst is not None:
            print(key)
            #lst = lst.sort()
            plotGraph(lst)

def getElementExt(url):
    question_mark_index = url.find('?')
    if question_mark_index > -1:
        url = url[0:question_mark_index]
    url_split = url.split('/')
    last_element = url_split[len(url_split) - 1]
    ext = None
    if last_element.rfind('.' ) > -1:
        last_element_split = last_element.split('.')
        ext = last_element_split[len(last_element_split) - 1]
    return ext

def getProfilePath():
    global profile_path
    if profile_path is not None:
        f = open('/home/ankitmit/.mozilla/firefox/profiles.ini', 'r')
        for line in f.readlines():
            if line.find('=') >= 0:
                split_text = line.split('=')
                if split_text[0] == "Path":
                    profile_path = "/home/ankitmit/.mozilla/firefox/" + split_text[0]
                    break

def updatePrefFile(memory):
    global profile_pref_file
    print ("Updating the prefs.js file for the maximum cache memory to " + str(memory))
    f = open(profile_pref_file, 'a')
    memory = memory[:-1]
    txt = "user_pref(\"browser.cache.disk.capacity\"" + ", " + str(memory) + ");"
    f.write(txt)
    f.close()


def main(argv):
    parseCommandLineArguments(argv)
    generateData()
    analyseHARData()

if __name__ == "__main__":
    main(sys.argv[1:])