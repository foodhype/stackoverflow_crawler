from bs4 import BeautifulSoup
from collections import deque
import ctypes
import os
import time
import urllib2
from urlparse import urljoin


class StackOverflowCrawler(object):
    def __init__(self):
        self.base_url = "http://stackoverflow.com"
        self.visited = set()
        self.remaining = []
        self.limit = float("inf")
        self.crawl_rate = 1
        self.valid_tags = set(["java"])
        self.minimum_question_upvote_count = 10
        self.minimum_answer_upvote_count = 10

    def crawl(self, start_url):
        if not start_url.startswith(self.base_url):
            raise ValueError("Cannot crawl external domains.")

        self.remaining.append(start_url)
        while self.remaining and len(self.visited) < self.limit:
            current_url = self.remaining.pop()

            print "Crawling %s...\n\n" % (current_url)
        
            self.visited.add(current_url)
            response = urllib2.urlopen(current_url)
            html = response.read()
            soup = BeautifulSoup(html)

            if current_url != start_url:
                yield self.extract_data(soup, current_url)

            for link in soup.find_all("a"):
                link_url = urljoin(self.base_url, link.get("href"))

                if (link_url not in self.visited and
                        link_url.startswith(self.base_url + "/questions")):
                    self.remaining.append(link_url)
            
            # Don't crawl too hard.
            time.sleep(self.crawl_rate)


    def java_pages_crawl(self):
        for page_no in xrange(1, 14703):
            page_url = "http://stackoverflow.com/questions/tagged/java?page=%d&sort=votes&pagesize=50" % (page_no)
            
            print "Crawling page %d: %s\n" % (page_no, page_url)
      
            response = urllib2.urlopen(page_url)

            # Don't crawl too hard.
            time.sleep(self.crawl_rate)

            self.visited.add(page_url)
            html = response.read()
            page_soup = BeautifulSoup(html)


            for questions_container in page_soup.find_all(id="questions"):
                for link in questions_container.find_all("a", "question-hyperlink"):
                    link_url = urljoin(self.base_url, link.get("href"))

                    if (link_url not in self.visited and
                            link_url.startswith(self.base_url + "/questions") and
                            not link_url.startswith(self.base_url + "/questions/tagged")):

                        print "Crawling %s...\n" % (link_url)

                        response = urllib2.urlopen(link_url)

                        # Don't crawl too hard.
                        time.sleep(self.crawl_rate)

                        self.visited.add(link_url)
                        child_html = response.read()
                        link_soup = BeautifulSoup(child_html)

                        yield self.extract_data(link_soup, link_url)
                  

    def extract_data(self, soup, url):
        page_title = soup.title.string
        page_id = ctypes.c_size_t(hash(url)).value
        question = None
        question_text = None
        question_upvote_count = None
        question_tags = []

        for question_div in soup.find_all("div", "question"):
            for question_container in question_div.find_all("div", "post-text"):
                question_text = question_container.contents
                break

            for upvote_count_container in question_div.find_all("span", "vote-count-post "): # <- This space is annoying but necessary.
                question_upvote_count = int(upvote_count_container.contents[0])
                break
            
            for tag_container in soup.find_all("div", "post-taglist"):
                for tag_hyperlink in tag_container.find_all("a", "post-tag"):
                    question_tags.append(tag_hyperlink.contents[0])
                if not any(str(tag) in self.valid_tags for tag in question_tags):
                    return None
                break

        if (question_text is not None and
                question_upvote_count is not None and
                question_upvote_count >= self.minimum_question_upvote_count):
            question = StackOverflowQuestion(question_text,
                    question_upvote_count, question_tags)

        answers = []
       
        for answer_div in soup.find_all("div", "answer"):
            answer_text = None
            answer_upvote_count = None
            
            for answer_container in answer_div.find_all("div", "post-text"):
                answer_text = answer_container.contents
                break

            for upvote_count_container in answer_div.find_all("span", "vote-count-post "): # <- This space is annoying but necessary.
                answer_upvote_count = int(upvote_count_container.contents[0])
                break

            if (answer_text is not None and
                    answer_upvote_count is not None and
                    answer_upvote_count >= self.minimum_answer_upvote_count):
                answers.append(StackOverflowAnswer(answer_text, answer_upvote_count))

        if question and answers:
            return PageMetadata(page_title, page_id, url, question, answers)


class PageMetadata(object):
    def __init__(self, title, page_id, url, question, answers):
        self.title = str(title)
        self.url = str(url)
        self.page_id = page_id
        self.question = question
        self.answers = answers

    def __str__(self):
        return "\n".join(["<h1>",
                self.title,
                "</h1>",
                str(self.question),
                "\n".join([str(answer) for answer in self.answers])])


class StackOverflowQuestion(object):
    def __init__(self, text, upvote_count, tags):
        self.text = "".join(map(str, text[1:-1]))
        self.upvote_count = upvote_count
        self.tags = [str(tag) for tag in tags]

    def __str__(self):
        return self.text


class StackOverflowAnswer(object):
    def __init__(self, text, upvote_count):
        self.text = "".join(map(str, text[1:-1]))
        self.upvote_count = upvote_count

    def __str__(self):
        return self.text


def main():
    crawler = StackOverflowCrawler()
    if not os.path.exists("pages"):
        os.makedirs("pages")
    for page_metadata in crawler.java_pages_crawl():
        if page_metadata is not None:
            f = open("pages/" + str(page_metadata.page_id) + ".question.html", "w")
            f.write("\n".join(["<h1>",
                    page_metadata.title,
                    "</h1>",
                    str(page_metadata.question)]))
            f.close()
            f = open("pages/" + str(page_metadata.page_id) + ".answer.html", "w")
            f.write("\n".join([str(answer) for answer in page_metadata.answers]))
            f.close()
            print "saved."


if __name__ == "__main__":
    main()
