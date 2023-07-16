# linkedin_post_scraper

Scraping posts of a company from linkedin and saving them in markdown files.

## Problems / Solutions / Readings

### Getting the date of posts

LinkedIn seems to do it on purpose to not expose proper structures with proper data. One of the data that is obfouscated is the date when a post was published. The best we seem to get (as of today: 2023-07-10) is the relative date: `1w` means the post is a week old. 
An approach on how to convert this is done [in this Stack Overflow Post](https://codereview.stackexchange.com/questions/129899/scraping-the-date-of-most-recent-post-from-various-social-media-services) - even though bnoth the selectors don't work anymore nowadays, as well as the units: It used to be days/weeks/months, it is now w/mo/y.

### Installing components

To install Chromedriver I followed [this guide](https://www.kenst.com/installing-chromedriver-on-mac-osx/#:~:text=The%20easiest%20way%20to%20install,seeing%20it%20returns%20a%20version.). It basically boils down to `brew install cask chromedriver`. 
**Note**: I couldn't execute it at first as it was forbidden by Apple policies. So I had to `xattr -d com.apple.quarantine /usr/local/bin/chromedriver` to remove the quarantine flag.

To install Selenium for my jupyter notebook I followed [this guide](https://shanyitan.medium.com/how-to-install-selenium-and-run-it-successfully-via-jupyter-lab-c3f50d22a0d4)

### LinkedIn Post Scraper

Ideas and code snippets taken from [this repo](https://github.com/christophe-garon/Linkedin-Post-Scraper) and the [blog article](https://christophegaron.com/articles/mind/automation/scraping-linkedin-posts-with-selenium-and-beautiful-soup/) that goes with it. 

Note: This code base uses an old version of Beautifoul Soup, so the syntax is not valid anymore.