import json
import os
import pathlib
import unidecode
import re as re

from datetime import datetime, timedelta
from typing import Dict,  Optional

from PIL import Image
from requests import Response, Session
from sys import exit
import logging

INTERNAL_DATE_FORMAT = "%Y-%m-%d"


class color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


internalDateFormat = "%Y-%m-%d %H:%M:%S"


def get_logger(name, log_level=logging.WARN):
    # Get a logger with the given name
    logger = logging.getLogger(name)
    # Disable propagation to the root logger. Makes sense in Jupyter only...
    logger.propagate = False
    logger.setLevel(log_level)

    # Check if the logger has handlers already
    if not logger.handlers:
        # Create a handler
        handler = logging.StreamHandler()

        # Set a format that includes the logger's name
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def transformDate2String(dateToTransform: datetime) -> str:
    logger = get_logger(transformDate2String.__name__)
    try:
        dateStr = dateToTransform.strftime(INTERNAL_DATE_FORMAT)
    except:
        logger.error(
            f"Error transforming date: {dateToTransform}. Continuing with empty date string.")
        dateStr = ""
    return dateStr


def transformString2Date(stringToTransform: str) -> Optional[datetime]:
    """Transforms a String that holds a date in my standard format to a Date. 
        In case it can't transform it, it return None."""
    try:
        dateObj = datetime.strptime(stringToTransform, internalDateFormat)
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


def areVariablesSet(varNames) -> bool:
    # log("areVariablesSet", "Checking if vars are set: ", varNames)
    for varName in varNames:
        if not isVariableSet(varName):
            return False
    # log("areVariablesSet", "All vars are set: ", varNames)
    return True


def isVariableSet(varName: str) -> bool:
    if (os.getenv(varName) is None) or (os.getenv(varName) == ""):
        log("isVariableSet", "Error",
            f'Variable {varName} is not set in environment.')
        return False
    return True


def writeDictToFile(*, dictionary: Dict, fullFilename: str) -> Dict:
    """Writes a dictionary to a file. Also updates the _stats element."""
    logger = get_logger(writeDictToFile.__name__, logging.INFO)
    if not isinstance(dictionary, dict):
        raise TypeError("Expected a dictionary, but got a " +
                        str(type(dictionary)))
    # log("writeDictToFile", "Len of dict to write: ", len(dictionary), " type: ", type(dictionary))
    nowStr = getNowAsString()
    dictionary.setdefault("_stats", {"lastWritten": nowStr})
    dictionary["_stats"]["lastWritten"] = nowStr
    dictionary["_stats"]["counter"] = len(dictionary)-1
    stats = dictionary["_stats"]
    del dictionary["_stats"]
    # log("writeDictToFile", "Len of dict after deleting _stats: ", len(dictionary), " type: ", type(dictionary))
    dictionary = dict(sorted(dictionary.items()))
    # log("writeDictToFile", "Len of dict after sorting: ", len(dictionary), " type: ", type(dictionary))
    sortedDictionary = {"_stats": stats, **dictionary}
    # log("writeDictToFile", "Len of sorted dict to write: ", len(sortedDictionary), " type: ", type(dictionary))
    dictDump = json.dumps(sortedDictionary, sort_keys=False, indent=2)

    # Make sure that the directory in which we want to write exists.
    directory = os.path.dirname(os.path.abspath(fullFilename))
    # log('writeDictToFile', 'Writing to dir ', directory)
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
                logger.warning(
                    f"Read file {fullFilename} successfully but does not contain _stats.lastWritten.")
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


# test_readDictFromFile()


def dateStringDistanceInDays(dateStr1: str, dateStr2: str) -> int:
    date1 = transformString2Date(dateStr1)
    date2 = transformString2Date(dateStr2)
    if not (date1 and date2):
        return -1
    diff: timedelta = abs(date1 - date2)
    diffInDays = diff.days
    return diffInDays


def dateStringDistanceInHours(dateStr1: str, dateStr2: str) -> int:
    date1 = transformString2Date(dateStr1)
    date2 = transformString2Date(dateStr2)
    if not (date1 and date2):
        return -1
    diff: timedelta = abs(date1 - date2)
    diffInSeconds = 0
    if (diff.days > 0):
        diffInSeconds += diff.days * 24*60*60
    diffInSeconds += diff.seconds
    diffInHours = diffInSeconds / (60*60)
    # log("dateStringDistanceInHours", "Date1: ", dateStr1,
    #     ", Date2: ", dateStr2, ", Diff in h: ", diffInHours)
    return diffInHours


def getImageSize(filename: str) -> Dict:
    """Returns the size of the image in the file given.
    If it's a svg it returns None."""
    file_extension = pathlib.Path(filename).suffix
    # log("getImageSize: ",
    #     "File extension: ", file_extension)
    if file_extension == ".svg":
        return {}
    elif not os.path.exists(filename):
        log("getImageSize: ",     "File does not exist: ", filename)
        return {}
    else:
        try:
            img = Image.open(filename)
            width = img.width
            height = img.height
            return {"width": width, "height": height}
        except:
            log("getImageSize: ",     "Could not open image file: ", filename)
            return {}


def loadPage(httpSession: Session, url: str) -> Optional[Response]:
    try:
        page = httpSession.get(url)
        return page
    except:
        log("loadPage", url, ": Error!")
        return None


def createLoggedInHttpSession(*, loginUrl: str, username: str, password: str) -> Session:
    s = Session()
    # log('createLoggedInHttpSession', 'Logging in to ', loginUrl)
    login_data = {"os_username": username,  # CONFLUENCE_USER,
                  "os_password": password}  # CONFLUENCE_PASSWORD}
    try:
        s.post(loginUrl, login_data)  # CONFLUENCE_LOGIN_URL
    except Exception as e:
        log("createLoggedInHttpSession: Error: ",
            "Could not create HTTP Session.", e)
        exit()
    return s


def log(name: str,  *args, end: str = "\n"):
    strToPrint = color.BOLD + name + ": " + color.END
    for arg in args:
        strToPrint += str(arg)
    print(strToPrint, end=end)


def simplify_text(some_text: str) -> str:
    """
    Simplifies a text to be used as a filename
    """
    simplified_text = some_text.replace('"', "'")
    simplified_text = unidecode.unidecode(simplified_text)
    simplified_text = re.sub("[^A-Za-z\-_]+", "_", simplified_text)
    simplified_text = re.sub('_+', '_', simplified_text)
    return simplified_text
