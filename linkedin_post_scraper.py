#!/usr/bin/env python
# coding: utf-8

from selenium import webdriver
import unidecode
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from bs4 import BeautifulSoup as bs
import time
from datetime import datetime, timedelta
import re as re
from importlib.metadata import version
from typing import Any, Dict, Optional
import os
import types
import logging
import tkinter as tk
import json
import hashlib


# Define global constants
PAGE = 'https://www.linkedin.com/company/mgm-technology-partners-gmbh'
SCROLL_PAUSE_TIME = 1.5
DATA_DIRECTORY = os.getenv('DATA_DIRECTORY') or 'data'
os.makedirs(DATA_DIRECTORY, exist_ok=True)

BLOGS_DIRECTORY = os.getenv('BLOGS_DIRECTORY') or f"{DATA_DIRECTORY}/blogs"
os.makedirs(BLOGS_DIRECTORY, exist_ok=True)

TMP_DIRECTORY = os.getenv('TMP_DIRECTORY') or f"{DATA_DIRECTORY}/tmp_linkedin"
os.makedirs(TMP_DIRECTORY, exist_ok=True)

FILENAME_SOUP = "linkedin_soup.html"
INTERNAL_DATE_FORMAT = "%Y-%m-%d"
NO_DATE = "__no_date__"

FILENAME_RAW_POSTS = f"{TMP_DIRECTORY}/raw_posts.json"

SELENIUM_RUNNER = 'http://selenium:4444'
GLOBAL_BROWSER = None # We need to declare this global variable, will set it later

# Read credentials
try:
    f= open("credentials.txt","r")
    contents = f.read()
    username = contents.replace("=",",").split(",")[1]
    password = contents.replace("=",",").split(",")[3]
except:
    f= open("credentials.txt","w+")
    username = input('Enter your linkedin username: ')
    password = input('Enter your linkedin password: ')
    f.write("username={}, password={}".format(username,password))
    f.close()


## Utils

def get_logger(name, log_level=logging.WARN):
    # Get a logger with the given name
    logger = logging.getLogger(name)
    logger.propagate = False  # Disable propagation to the root logger. Makes sense in Jupyter only...
    logger.setLevel(log_level)

    # Check if the logger has handlers already
    if not logger.handlers:
        # Create a handler
        handler = logging.StreamHandler()

        # Set a format that includes the logger's name
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
    
def transformDate2String(dateToTransform: datetime) -> str:
    logger = get_logger(transformDate2String.__name__)
    try:
        dateStr = dateToTransform.strftime(INTERNAL_DATE_FORMAT)
    except:
        logger.error(f"Error transforming date: {dateToTransform}. Continuing with empty date string.")
        dateStr = ""
    return dateStr

def transformString2Date(stringToTransform: str) -> Optional[datetime]:
    """Transforms a String that holds a date in my standard format to a Date. 
        In case it can't transform it, it return None."""
    try:
        dateObj = datetime.strptime(stringToTransform, INTERNAL_DATE_FORMAT)
    except:
        log("transformString2Date", "Error transforming string to date: ",
            stringToTransform)
        dateObj = None
    return dateObj

def getNowAsString() -> str:
    return transformDate2String(datetime.now())

def getMinDateAsString() -> str:
    return transformDate2String(datetime(1970, 1, 1))

def stripBlanks(str):
    return str.strip(" \t")
import logging


def writeDictToFile(*, dictionary: Dict, fullFilename: str) -> Dict:
    """Writes a dictionary to a file. Also updates the _stats element."""
    logger = get_logger(writeDictToFile.__name__, logging.INFO)
    if not isinstance(dictionary, dict):
        raise TypeError("Expected a dictionary, but got a " + str(type(dictionary)))
    #log("writeDictToFile", "Len of dict to write: ", len(dictionary), " type: ", type(dictionary))
    nowStr = getNowAsString()
    dictionary.setdefault("_stats", {"lastWritten": nowStr})
    dictionary["_stats"]["lastWritten"] = nowStr
    dictionary["_stats"]["counter"] = len(dictionary)-1
    stats = dictionary["_stats"]
    del dictionary["_stats"]
    #log("writeDictToFile", "Len of dict after deleting _stats: ", len(dictionary), " type: ", type(dictionary))
    dictionary = dict(sorted(dictionary.items()))
    #log("writeDictToFile", "Len of dict after sorting: ", len(dictionary), " type: ", type(dictionary))
    sortedDictionary = {"_stats": stats, **dictionary}
    #log("writeDictToFile", "Len of sorted dict to write: ", len(sortedDictionary), " type: ", type(dictionary))
    dictDump = json.dumps(sortedDictionary, sort_keys=False, indent=2)

    # Make sure that the directory in which we want to write exists.
    directory = os.path.dirname(os.path.abspath(fullFilename))
    #log('writeDictToFile', 'Writing to dir ', directory)
    try:
        os.makedirs(directory)
    except FileExistsError:
        # directory already exists, so no need to create it - all good
        pass

    with open(fullFilename, 'w') as file:
        file.write(dictDump)
    return sortedDictionary

def readDictFromFile(*, fullFilename: str) -> Dict:
    """Reads a dictionary from a file. Chacks that the dictionary read has a _stats.lastWritten entry."""
    logger = get_logger(readDictFromFile.__name__, logging.INFO)
    data = {}
    try:
        with open(fullFilename, "r+") as file:
            data = json.load(file)
            if data == None: 
                return {}
            if data.get("_stats", {}).get("lastWritten") == None:
                logger.warning(f"Read file {fullFilename} successfully but does not contain _stats.lastWritten.")
            return data
    except IOError as e:
        logger.warning(f"Could not open file {fullFilename}")
        raise e
    return data

def test_writeDictToFile():
    data = {
        "hello": "world",
        "now": "what"
    }
    writeDictToFile(dictionary=data, fullFilename="test.json")

def test_readDictFromFile():
    data = {
        "hello": "world",
        "now": "what"
    }
    FILENAME = "test.json"

    # Write and then read it
    writeDictToFile(dictionary=data, fullFilename=FILENAME)
    data2 = readDictFromFile(fullFilename=FILENAME)

    # Delete test data, try to read it - even though it doesn't exist
    try:
        os.remove(FILENAME)
    except FileNotFoundError:
        pass
    try:
        data3 = readDictFromFile(fullFilename=FILENAME)
    except:
        print("All good, I am in an exception as I expected it to be")

test_readDictFromFile()


# ## Login to LinkedIn

def create_loggedin_browser():
    logger = get_logger(create_loggedin_browser.__name__, logging.INFO)

    #access Webriver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--incognito")

    logger.info('Requesting remote browser/driver...')
    browser = webdriver.Remote(SELENIUM_RUNNER, options=chrome_options)
    logger.info('Received remote browser/driver 😜')
    
    #Open login page
    browser.get('https://www.linkedin.com/login?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin')
    
    #Enter login info:
    elementID = browser.find_element(by=By.ID, value='username')   #.find_element_by_id('username')
    elementID.send_keys(username)
    
    elementID = browser.find_element(by=By.ID, value='password')#find_element_by_id('password')
    elementID.send_keys(password)
    #Note: replace the keys "username" and "password" with your LinkedIn login info
    elementID.submit()

    # Check if we got a special verification page
    if 'quick verification' in browser.page_source:
        logger.warning(f"I think I got a special verification page!")
        now = datetime.datetime.now()
        filename = "screen_after_login_" + now.strftime('%Y-%m-%d_%H-%M-%S.png')
        browser.save_screenshot(filename)
        

    return browser


# Note: To see the running browser/driver sessions on the selenium runner service, go [here](http://localhost:4444/ui#/sessions)

def login_global_browser():
    logger = get_logger(login_global_browser.__name__, logging.INFO)
    global GLOBAL_BROWSER # We need to explicitly declare that we mean the gllobal var here...

    if GLOBAL_BROWSER is not None:
        logger.info('Quitting existing browser/driver session')
        try:
            GLOBAL_BROWSER.quit()
        except:
            logger.warn('Failed quitting existing browser/driver. Ignoring, trying to create a new one anyways.')
    GLOBAL_BROWSER = create_loggedin_browser()

login_global_browser()


# ## Load posts page & scroll to bottom

def browser_go_to_page(browser, max_pages=0):
    logger = get_logger(browser_go_to_page.__name__, logging.INFO)
    #Go to webpage
    company_posts_page = PAGE + '/posts/'
    logger.info(f"{company_posts_page=}")
    browser.get(company_posts_page)
    
    # Get scroll height
    last_height = browser.execute_script("return document.body.scrollHeight")
    scroll_page = 0
    
    while True:
        # Scroll down to bottom
        #click_visible_menues(browser)
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
        scroll_page += 1
        logger.info(f"Scrolling page {scroll_page}")
        
        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)
    
        # Calculate new scroll height and compare with last scroll height
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        if max_pages > 0:
            if scroll_page == max_pages:
                break
                
    return 

def get_page_source(browser, max_pages=0):
    logger = get_logger(get_page_source.__name__, logging.INFO)
    browser_go_to_page(browser, max_pages)

    company_page = browser.page_source   
    return company_page



def get_linkedin_browser(browser, max_pages=0):
    browser_go_to_page(browser, max_pages=max_pages)
    return browser


# ## Retrieve data from loaded page

def retrieve_container_elements(browser, max_pages):
    logger = get_logger(retrieve_container_elements.__name__, logging.INFO)
    linkedin_browser = get_linkedin_browser(browser, max_pages=max_pages)
    container_elements = linkedin_browser.find_elements(By.CLASS_NAME, "occludable-update")
    logger.info(f"No of container elements before filter: {len(container_elements)}")
    container_elements = [element for element in container_elements if len(element.find_elements(By.CLASS_NAME,"update-components-actor")) > 0]
    logger.info(f"No of container elements after filter: {len(container_elements)}")
    return container_elements, linkedin_browser


def is_element_in_viewport(driver, element):
    return driver.execute_script("""
        var elem = arguments[0];
        var rect = elem.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    """, element)


def get_post_url(browser):
    logger = get_logger(get_post_url.__name__, logging.WARN)
    elements = browser.find_elements(By.XPATH, "//*[text()='Copy link to post']")
    if len(elements) != 1:
        logger.warning(f"Number of list of elements that should give me the URL of the blogpost: {len(elements)}")
        return None
    try:
        elements[0].click()
        root = tk.Tk()
        blog_post_url = root.clipboard_get()
        logger.info(f"URL of blog post: {blog_post_url}")
        return blog_post_url
    except Exception as e:
        logger.warn(f"Could not extract blog post url, retrurning None. Error: {e}")
        return None

def extract_blog_post_url_from_container_element(browser, container_element):
    logger = get_logger(extract_blog_post_url_from_container_element.__name__, logging.INFO)
    #logger.info(f"Extracting from container of type {type(container_element)}")
    buttons = container_element.find_elements(By.CLASS_NAME, 'feed-shared-control-menu__trigger')  
    if len(buttons) != 1:
        logger.info(f"No of buttons found in container: {len(buttons)}. Cannot process this container.")
        return None
        
    button = buttons[0]
    actions = ActionChains(browser)
    actions.send_keys(Keys.ESCAPE).perform()
    browser.execute_script('arguments[0].scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });', button)
    
    if not button.is_displayed():  
        logger.warn("Button not displayed, cannot process container")
        return None
        
    actions.send_keys(Keys.ESCAPE).perform()
    time.sleep(1)  
    button.click()
    time.sleep(5)  
    url = get_post_url(browser)                
    actions.send_keys(Keys.ESCAPE).perform()
    return url


def write_blog_containers_to_file(blogs):
    logger = get_logger(write_blog_containers_to_file.__name__, logging.INFO)
    # Prepare blogs to be saveable i.e. serializable
    blogs_to_save = {}
    for blog_id, blog in blogs:
        blog_to_save = blog
        blog_to_save["soup"] = blog["soup"].prettify()
        blogs_to_save[blog_id] = blog_to_save
    try:
        writeDictToFile(dictionary=blogs_to_save,fullFilename=FILENAME_RAW_POSTS)
    except Exception as e:
        logger.warn(f"could not write {len(blogs)} blog containers to file {FILENAME_RAW_POSTS}: {e}")        
    return 

def read_blog_containers_from_file():
    logger = get_logger(read_blog_containers_from_file.__name__, logging.INFO)
    blogs = {}
    try:
        blogs = readDictFromFile(fullFilename=FILENAME_RAW_POSTS)
    except Exception as e:
        logger.warning(f"Could not read blog containers from file {FILENAME_RAW_POSTS}. Raising Error.")
        raise e
    for blog_id, blog in blogs:
        blog[blog_id]["soup"] = bs(blog["soup"], "html.parser")  # convert string to BeautifulSoup object
    logger.info(f"Read {len(blogs)} blog containersc from file {FILENAME_RAW_POSTS}.")
    return blogs


def extract_text_from_soup(soup: bs):
    logger = get_logger(extract_text_from_soup.__name__, log_level=logging.INFO)

    # In 'container', find the first <div> element with class 'feed-shared-update-v2__description-wrapper'.
    # Assign this element to 'text_box'.
    text_box = soup.find("div", {"class":"feed-shared-update-v2__description-wrapper"})
    
    # If 'text_box' is not None (i.e., if such an element was found in 'container')...
    if text_box:
        # ...find the first <span> element within 'text_box' that has the 'dir' attribute set to 'ltr'.
        # Extract its text content, strip leading and trailing whitespace, and assign this cleaned text to 'text'.
        text = text_box.find("span", {"dir":"ltr"}).text.strip()
        
        # Return 'text'.
        return text
    else:
        # If 'text_box' is None (i.e., if no such <div> element was found in 'container')...
        # ...print an error message.
        logger.warning(f"Could not extract text from soup!")
        
        # Uncomment the following line to print the 'container' for debugging purposes.
        # print(f"Container: {container}")
        
        # Return an empty string.
        return ""


def generate_id_from_text(blog_text):
    # Create a hash of the blog source
    hash_object = hashlib.sha256(blog_text.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig


def extract_blogs_from_container_elements(browser, container_elements):
    logger = get_logger(extract_blogs_from_container_elements.__name__, logging.INFO)
    blogs = {}
    for container_element in container_elements:
        blog_url = extract_blog_post_url_from_container_element(browser, container_element)
        blog_source = container_element.get_attribute('outerHTML')
        blog_soup = bs(blog_source.encode("utf-8"), "html")
        blog_text = extract_text_from_soup(blog_soup)
        if (len(blog_text) == 0):
            logger.warning(f"Cannot extract text from container, so container has no value and is skipped")
        else:
            blog_id = generate_id_from_text(blog_text)
            blog = {
                "url": blog_url,
                "source": blog_source,
                "soup": blog_soup,
                "scrape_date": getNowAsString()
            }
            blogs[blog_id] = blog
                         
    logger.info(f"No of extracted blogs: {len(blogs)}")
    write_blog_containers_to_file(blogs)
    return blogs


def get_blog_containers(force_retrieval=False, max_pages=0):
    logger = get_logger(get_blog_containers.__name__, logging.INFO)
    if force_retrieval:
        logger.info(f"Retrieving blog containers: {force_retrieval=} {max_pages=}")
        container_elements, browser = retrieve_container_elements(GLOBAL_BROWSER, max_pages)
        blog_containers = extract_blogs_from_container_elements(browser, container_elements)   
        return blog_containers
    try:
        blog_containers = read_blog_containers_from_file()
        return blog_containers
    except Exception as e:
        logger.warning(f"Could not read blog containers from file, retrieving from website")
        container_elements, browser = retrieve_container_elements(GLOBAL_BROWSER, max_pages)
        blog_containers = extract_blogs_from_container_elements(browser, container_elements)   
        return blog_containers

login_global_browser()
blog_container = get_blog_containers(force_retrieval=False, max_pages=3)


def extract_date_string_from_soup(soup: bs):
    logger = get_logger(extract_date_string_from_soup.__name__, log_level=logging.WARN)

    # Looking for the relative date (in d, w, mo, yr)
    # It has the shape: "1yr •"
    p = re.compile(r'\d{1,2}(h|d|w|mo|yr)\s•')
    m = re.compile(r'\d{1,2}(h|d|w|mo|yr)\s•').search(soup.prettify())
    dateHumanReadable = ""
    if m:
        dateHumanReadable = m.group()
        logger.info(f"Match found: {dateHumanReadable}")
        return dateHumanReadable
    else:
        logger.error(f"Could not extract human readable date from soup! soup: {soup}")
        return NO_DATE

def test_extract_date_string_from_soup():
    containers = get_blog_containers()
    human_readable_date = extract_date_string_from_soup(containers[0]["soup"])
    print(human_readable_date)

test_extract_date_string_from_soup()


def linkedin_rel_date2datetime(relative_date):
    """Transforms a relative date from LinkedIn to a datetime object.
    Transform "6d •" to a proper datetime"""

    logger = get_logger(linkedin_rel_date2datetime.__name__, log_level=logging.WARN)
    
    p = re.compile('\d{1,2}')
    m = p.search(relative_date)
    if m is None:
        logger.error(f"Amount not found in {relative_date}")
        exit
    amount = float(m.group())
    p = re.compile('(h|d|w|mo|yr)')
    m = p.search(relative_date)
    logger.info(f"m: {m}, type(m): {type(m)}")
    if m is None:
        logger.error(f"Unit not found in {relative_date}")
        exit
    unit = m.group()
    if unit == 'yr':
        amount *= 365*24
    elif unit == 'mo':
        amount *= 30*24
    elif unit == 'w':
        amount *= 7*24
    elif unit == 'd':
        amount *= 24
    logger.info(f" {relative_date} --> Amount in hours: {amount}")
    # Calculate the date from today's, and return it
    howRecent = timedelta(hours=amount)
    todaysDate = datetime.now()
    date = (todaysDate - howRecent)
    return date

# Some tests
rel_dates = ['2h •', '3d •', '1w •']
for rel_date in rel_dates:
    print(f"{rel_date} --> {linkedin_rel_date2datetime(rel_date)}")


def simplify_content(content):
    content = re.sub('\n +', '\n', content)
    content = re.sub('\n+', '\n\n', content)
    content = content.replace("{", "&#123;").replace("}", "&#125;")
    return content
    
def extract_all_from_container(container):
    logger = get_logger(extract_all_from_container.__name__, logging.INFO)
    blog_post = {}
    blog_post["date_human_readable"] = extract_date_string_from_soup(container["soup"])
    blog_post["posted_date"] = linkedin_rel_date2datetime(blog_post["date_human_readable"])
    blog_post["text"] = simplify_content(extract_text_from_soup(container["soup"]))
    blog_post["original_url"] = container["url"]
    logger.info(f"{blog_post['posted_date']} - {blog_post['text'][:30]}")
    return blog_post

def extract_all_from_containers():
    logger = get_logger(extract_all_from_containers.__name__, logging.INFO)
    containers = get_blog_containers()
    blog_posts = []
    
    for container_no, container in enumerate(containers):
        try:
            logger.info(f"Processing container # {container_no}")
            blog_post = extract_all_from_container(container)
            blog_posts.append(blog_post)
        except Exception as e:
            logger.warning(f"Container # {container_no} not added: {str(e)}")
            pass
    return blog_posts

blog_posts = extract_all_from_containers();


if (len(blog_posts) != len(get_blog_containers())):
    print("Not all containers could be transformed to blog_posts! No of conatiner: {len(containers)}, no of blog posts: {len(blog_posts)}")


blog_post_index = 1
print(blog_posts[blog_post_index])
#blog_posts


# ## Saving blog posts to files


def simplify_text(some_text: str) -> str:
    simplified_text = some_text.replace('"', "'")
    simplified_text = unidecode.unidecode(simplified_text)
    simplified_text = re.sub("[^A-Za-z\-_]+", "_", simplified_text)
    simplified_text = re.sub('_+', '_', simplified_text)
    return simplified_text


def build_title(blog_post):
    LEN_OF_TITLE = 35
    title = blog_post["text"][:LEN_OF_TITLE].replace('\n', ' ')
    return title

def build_title(blog_post):
    LEN_OF_TITLE = 35
    text = blog_post["text"]
    title = text[:LEN_OF_TITLE]
    
    if len(text) > LEN_OF_TITLE and text[LEN_OF_TITLE] != ' ':
        # Extend to the end of the current word
        while len(text) > len(title) and text[len(title)] != ' ':
            title += text[len(title)]
    
    # Replace newlines with spaces in the final title
    title = title.replace('\n', ' ')
    return title

def build_simplified_title(blog_post: Dict) -> str:
    simplified_title = simplify_text(build_title(blog_post))
    return simplified_title


def build_filename(blog_post: Dict) -> str:
    logger = get_logger(build_filename.__name__, logging.INFO)
    LEN_OF_FILENAME = 45
    posted_date = blog_post["posted_date"]
    try:
        posted_date_for_filename = posted_date.strftime(INTERNAL_DATE_FORMAT)
    except:
        createdDateStrForFilename = "_no_date_"    
    simplified_title = build_simplified_title(blog_post)[:LEN_OF_FILENAME-13]
    filename = f"{BLOGS_DIRECTORY}/{posted_date_for_filename}-{simplified_title}.md"
    logger.info(filename)
    return filename


for blog_post in blog_posts:
    print(build_filename(blog_post))


def build_frontmatter(blog_post):
    posted_date = blog_post["posted_date"]
    title = build_title(blog_post)
    original_url = blog_post["original_url"]
    frontMatter = ("---\n"
           "layout: post\n"
           "date: " + transformDate2String(posted_date) + "\n"
           'title: "' + title + '"\n'
           "originalUrl: \"" + original_url + "\"\n")
           #"tags: linkedin " + linkedin_user_based_tags + "\n" +
           #"author: \"" + author + "\"\n")
    frontMatter += "---\n\n"
    return frontMatter


def save_blog_post_to_file(blog_post: Dict) -> None:
    content = blog_post["text"]
    filename = build_filename(blog_post)
    frontmatter = build_frontmatter(blog_post)
    path = os.path.dirname(filename)
    #log("saveToFile", "Saving to file ", filename)
    os.makedirs(path, exist_ok=True)
    with open(filename, 'w') as file:
        file.write(frontmatter)
        file.write(content)
        file.close()

def save_blog_posts_to_file(blog_posts):
    for blog_post in blog_posts:
        save_blog_post_to_file(blog_post)

save_blog_posts_to_file(blog_posts)



