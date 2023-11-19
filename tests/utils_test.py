from linkedin_post_scraper import utils
from datetime import datetime, timedelta


def test_transformDate2String():
    date_string = "2023-11-19 14:55:54.723733"
    date_format = "%Y-%m-%d %H:%M:%S.%f"
    date_object = datetime.strptime(date_string, date_format)
    result_string = utils.transformDate2String(date_object)
    expected_result = "2023-11-19"

    assert (result_string == expected_result)
