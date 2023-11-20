#!/usr/bin/env python
# coding: utf-8

from selenium import webdriver
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

from utils import get_logger, getNowAsString, writeDictToFile, readDictFromFile
from blog_post import save_blog_posts_to_file
from linkedin_utils import linkedin_rel_date2datetime

logger = get_logger("linkedin_post_scraper.__main__", logging.INFO)

# Define global constants
PAGE = 'https://www.linkedin.com/company/mgm-technology-partners-gmbh'
SCROLL_PAUSE_TIME = 1.5
DATA_DIRECTORY = os.getenv('DATA_DIRECTORY') or 'data'
os.makedirs(DATA_DIRECTORY, exist_ok=True)

TMP_DIRECTORY = os.getenv('TMP_DIRECTORY') or f"{DATA_DIRECTORY}/tmp_linkedin"
os.makedirs(TMP_DIRECTORY, exist_ok=True)

FILENAME_SOUP = "linkedin_soup.html"
NO_DATE = "__no_date__"

FILENAME_RAW_POSTS = f"{TMP_DIRECTORY}/raw_posts.json"

SELENIUM_RUNNER = 'http://selenium:4444'
# GLOBAL_BROWSER = None  # We need to declare this global variable, will set it later

CREDENTIALS_FILE = "../credentials.txt"
MAX_PAGES = 4

# Read credentials
logger.info("Gathering credentials")
try:
    f = open(CREDENTIALS_FILE, "r")
    contents = f.read()
    username = contents.replace("=", ",").split(",")[1]
    password = contents.replace("=", ",").split(",")[3]
except:
    f = open(CREDENTIALS_FILE, "w+")
    username = input('Enter your linkedin username: ')
    password = input('Enter your linkedin password: ')
    f.write("username={}, password={}".format(username, password))
    f.close()


def create_loggedin_browser():
    """
    Creatinmg a new browser session and logging in to LinkedIn
    """

    logger = get_logger(create_loggedin_browser.__name__, logging.INFO)

    # access Webriver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--incognito")

    logger.info('Requesting remote browser/driver...')
    browser = webdriver.Remote(SELENIUM_RUNNER, options=chrome_options)
    logger.info(
        f"Received remote browser/driver 😜 See what's goinmg on here: http://localhost:4444/ui#/sessions")

    # Open login page
    browser.get(
        'https://www.linkedin.com/login?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin')

    # Enter login info:
    # .find_element_by_id('username')
    elementID = browser.find_element(by=By.ID, value='username')
    elementID.send_keys(username)

    # find_element_by_id('password')
    elementID = browser.find_element(by=By.ID, value='password')
    elementID.send_keys(password)
    # Note: replace the keys "username" and "password" with your LinkedIn login info
    elementID.submit()

    # Check if we got a special verification page
    if 'quick verification' in browser.page_source:
        logger.warning(f"I think I got a special verification page!")
        now = datetime.now()
        filename = f"{TMP_DIRECTORY}/screen_after_login_" + \
            now.strftime('%Y-%m-%d_%H-%M-%S.png')
        browser.save_screenshot(filename)
        logger.info(
            f"Screenshot of the suspicious page saved here: {filename}")
        verification_code = input(
            "Please enter the verification code from your email: ")
        elementID = browser.find_element(
            by=By.ID, value='input__email_verification_pin')
        elementID.send_keys(verification_code)
        elementID.submit()

    return browser


def browser_go_to_company_page(browser=None, max_pages=MAX_PAGES):
    """
    Goes to the company page and scrolls to the bottom of the page
    """
    # TODO: Pass in the company page as argument

    logger = get_logger(browser_go_to_company_page.__name__, logging.INFO)
    if browser is None:
        browser = create_loggedin_browser()

    company_posts_page = PAGE + '/posts/'
    logger.info(f"{company_posts_page=}")
    browser.get(company_posts_page)

    # Get scroll height
    last_height = browser.execute_script("return document.body.scrollHeight")
    scroll_page = 0

    while True:
        # Scroll down to bottom
        # click_visible_menues(browser)
        browser.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

        scroll_page += 1
        logger.info(f"Scrolling page {scroll_page}")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = browser.execute_script(
            "return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        if max_pages > 0:
            if scroll_page == max_pages:
                break
    return


def retrieve_container_elements(browser=None, max_pages=MAX_PAGES):
    """
    Retrieve the container elements from the page
    """
    logger = get_logger(retrieve_container_elements.__name__, logging.INFO)
    if browser is None:
        browser = create_loggedin_browser()
    browser_go_to_company_page(browser, max_pages=max_pages)
    container_elements = browser.find_elements(
        By.CLASS_NAME, "occludable-update")
    logger.info(
        f"No of container elements before filter: {len(container_elements)}")
    container_elements = [element for element in container_elements if len(
        element.find_elements(By.CLASS_NAME, "update-components-actor")) > 0]
    logger.info(
        f"No of container elements after filter: {len(container_elements)}")
    return container_elements, browser


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
    """
    The URL of a linkedIn post is not directly accessible. It needs to 
    be created via an extra server round trip.
    This function clicks on the button that creates the URL and then retrieves it.
    """
    logger = get_logger(get_post_url.__name__, logging.WARN)
    elements = browser.find_elements(
        By.XPATH, "//*[text()='Copy link to post']")
    if len(elements) != 1:
        logger.warning(
            f"Number of list of elements that should give me the URL of the blogpost: {len(elements)}")
        return None
    try:
        elements[0].click()
        root = tk.Tk()
        blog_post_url = root.clipboard_get()
        logger.info(f"URL of blog post: {blog_post_url}")
        return blog_post_url
    except Exception as e:
        logger.warning(
            f"Could not extract blog post url, retrurning None. Error: {e}")
        return None


def extract_blog_post_url_from_container_element(browser, container_element):
    logger = get_logger(
        extract_blog_post_url_from_container_element.__name__, logging.INFO)
    # logger.info(f"Extracting from container of type {type(container_element)}")
    buttons = container_element.find_elements(
        By.CLASS_NAME, 'feed-shared-control-menu__trigger')
    if len(buttons) != 1:
        logger.info(
            f"No of buttons found in container: {len(buttons)}. Cannot process this container.")
        return None

    button = buttons[0]
    actions = ActionChains(browser)
    actions.send_keys(Keys.ESCAPE).perform()
    browser.execute_script(
        'arguments[0].scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });', button)

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
    logger.ingfo(f"Preparing {len(blogs)} blog containers to be saved")
    blogs_to_save = {}
    for blog_id, blog in blogs.items():
        blog_to_save = blog
        blog_to_save["soup"] = blog["soup"].prettify()
        blogs_to_save[blog_id] = blog_to_save
    try:
        writeDictToFile(dictionary=blogs_to_save,
                        fullFilename=FILENAME_RAW_POSTS)
        logger.info(f"Blog containers written to {FILENAME_RAW_POSTS}")
    except Exception as e:
        logger.warn(
            f"could not write {len(blogs)} blog containers to file {FILENAME_RAW_POSTS}: {e}")
    return


def read_blog_containers_from_file():
    logger = get_logger(read_blog_containers_from_file.__name__, logging.INFO)
    containers = {}
    try:
        containers = readDictFromFile(fullFilename=FILENAME_RAW_POSTS)
    except Exception as e:
        logger.warning(
            f"Could not read blog containers from file {FILENAME_RAW_POSTS}. Raising Error.")
        raise e
    # Delete the _stats entry
    containers.pop("_stats", None)
    for container_id, container in containers.items():
        # convert string to BeautifulSoup object
        try:
            containers[container_id]["soup"] = bs(
                container["soup"], "html.parser")
        except Exception as e:
            logger.error(
                f"Copuld not transform htmnl to beautifoulds soup object. Error {e} ")
            container[container_id]["soup"] = None
    logger.info(
        f"Read {len(containers)} blog containersc from file {FILENAME_RAW_POSTS}.")
    return containers


def extract_text_from_soup(soup: bs):
    logger = get_logger(extract_text_from_soup.__name__,
                        log_level=logging.INFO)

    # In 'container', find the first <div> element with class 'feed-shared-update-v2__description-wrapper'.
    # Assign this element to 'text_box'.
    text_box = soup.find(
        "div", {"class": "feed-shared-update-v2__description-wrapper"})

    # If 'text_box' is not None (i.e., if such an element was found in 'container')...
    if text_box:
        # ...find the first <span> element within 'text_box' that has the 'dir' attribute set to 'ltr'.
        # Extract its text content, strip leading and trailing whitespace, and assign this cleaned text to 'text'.
        text = text_box.find("span", {"dir": "ltr"}).text.strip()

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
    logger = get_logger(
        extract_blogs_from_container_elements.__name__, logging.INFO)
    blogs = {}
    for container_element in container_elements:
        blog_url = extract_blog_post_url_from_container_element(
            browser, container_element)
        blog_source = container_element.get_attribute('outerHTML')
        blog_soup = bs(blog_source.encode("utf-8"),
                       "html.parser")
        blog_text = extract_text_from_soup(blog_soup)
        if (len(blog_text) == 0):
            logger.warning(
                f"Cannot extract text from container, so container has no value and is skipped")
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


def get_blog_containers(browser=None, force_retrieval=False, max_pages=MAX_PAGES):
    logger = get_logger(get_blog_containers.__name__, logging.INFO)
    if force_retrieval:
        logger.info(
            f"Retrieving blog containers: {force_retrieval=} {max_pages=}")
        if browser is None:
            browser = create_loggedin_browser()
        container_elements, browser = retrieve_container_elements(
            browser, max_pages)
        blog_containers = extract_blogs_from_container_elements(
            browser, container_elements)
        return blog_containers
    try:
        blog_containers = read_blog_containers_from_file()
        return blog_containers
    except Exception as e:
        logger.warning(
            f"Could not read blog containers from file, retrieving from website")
        container_elements, browser = retrieve_container_elements(
            browser, max_pages)
        blog_containers = extract_blogs_from_container_elements(
            browser, container_elements)
        write_blog_containers_to_file(blog_containers)
        return blog_containers


def extract_date_string_from_soup(soup: bs):
    logger = get_logger(
        extract_date_string_from_soup.__name__, log_level=logging.WARN)

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
        logger.error(
            f"Could not extract human readable date from soup! soup: {soup}")
        return NO_DATE


def test_extract_date_string_from_soup():
    containers = get_blog_containers()
    human_readable_date = extract_date_string_from_soup(containers[0]["soup"])
    print(human_readable_date)


def simplify_content(content):
    content = re.sub('\n +', '\n', content)
    content = re.sub('\n+', '\n\n', content)
    content = content.replace("{", "&#123;").replace("}", "&#125;")
    return content


def extract_all_from_container(container):
    logger = get_logger(extract_all_from_container.__name__, logging.INFO)
    blog_post = {}
    blog_post["date_human_readable"] = extract_date_string_from_soup(
        container["soup"])
    blog_post["posted_date"] = linkedin_rel_date2datetime(
        blog_post["date_human_readable"])
    blog_post["text"] = simplify_content(
        extract_text_from_soup(container["soup"]))
    blog_post["original_url"] = container["url"]
    logger.info(f"{blog_post['posted_date']} - {blog_post['text'][:30]}")
    return blog_post


def extract_all_from_containers():
    logger = get_logger(extract_all_from_containers.__name__, logging.INFO)
    containers = get_blog_containers()
    blog_posts = []

    for container_id, container in containers.items():
        try:
            logger.info(f"Processing container id {container_id}")
            blog_post = extract_all_from_container(container)
            blog_posts.append(blog_post)
        except Exception as e:
            logger.warning(f"Container id {container_id} not added: {str(e)}")
            pass
    return blog_posts


blog_posts = extract_all_from_containers()


if (len(blog_posts) != len(get_blog_containers())):
    logger.info(
        "Not all containers could be transformed to blog_posts! No of conatiner: {len(containers)}, no of blog posts: {len(blog_posts)}")


blog_post_index = 1
print(blog_posts[blog_post_index])
# blog_posts


# ## Saving blog posts to files


save_blog_posts_to_file(blog_posts)
