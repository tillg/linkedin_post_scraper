from utils import get_logger
import logging
import re as re
from datetime import datetime, timedelta


def linkedin_rel_date2datetime(relative_date):
    """Transforms a relative date from LinkedIn to a datetime object.
    Transform "6d •" to a proper datetime"""

    logger = get_logger(linkedin_rel_date2datetime.__name__,
                        log_level=logging.WARN)

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
