
import os
import logging
from utils import transformDate2String, get_logger, simplify_text
from typing import Any, Dict, Optional

# Setting my variables
DATA_DIRECTORY = os.getenv('DATA_DIRECTORY') or 'data'
BLOGS_DIRECTORY = os.getenv('BLOGS_DIRECTORY') or f"{DATA_DIRECTORY}/blogs"
os.makedirs(BLOGS_DIRECTORY, exist_ok=True)


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
        posted_date_for_filename = transformDate2String(posted_date)
    except:
        createdDateStrForFilename = "_no_date_"
    simplified_title = build_simplified_title(blog_post)[:LEN_OF_FILENAME-13]
    filename = f"{BLOGS_DIRECTORY}/{posted_date_for_filename}-{simplified_title}.md"
    logger.info(filename)
    return filename


# for blog_pxsbuild_filename(blog_post))


def build_frontmatter(blog_post):
    posted_date = blog_post["posted_date"]
    title = build_title(blog_post)
    original_url = blog_post["original_url"]
    frontMatter = ("---\n"
                   "layout: post\n"
                   "date: " + transformDate2String(posted_date) + "\n"
                   'title: "' + title + '"\n'
                   "originalUrl: \"" + original_url + "\"\n")
    # "tags: linkedin " + linkedin_user_based_tags + "\n" +
    # "author: \"" + author + "\"\n")
    frontMatter += "---\n\n"
    return frontMatter


def save_blog_post_to_file(blog_post: Dict) -> None:
    content = blog_post["text"]
    filename = build_filename(blog_post)
    frontmatter = build_frontmatter(blog_post)
    path = os.path.dirname(filename)
    # log("saveToFile", "Saving to file ", filename)
    os.makedirs(path, exist_ok=True)
    with open(filename, 'w') as file:
        file.write(frontmatter)
        file.write(content)
        file.close()


def save_blog_posts_to_file(blog_posts):
    for blog_post in blog_posts:
        save_blog_post_to_file(blog_post)
