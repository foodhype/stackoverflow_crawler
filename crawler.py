from bs4 import BeautifulSoup
import time
import urllib2
from urlparse import urljoin


class StackOverflowCrawler(object):
    def __init__(self):
        self.base_url = "http://stackoverflow.com"
        self.visited = set()
        self.remaining = []
        self.limit = 10
        self.crawl_rate = 1

    def crawl(self, start_url):
        if not start_url.startswith(self.base_url):
            raise ValueError("Cannot crawl external domains.")

        self.remaining.append(start_url)
        while self.remaining and len(self.visited) < self.limit:
            current_url = self.remaining.pop()
        
            print "Crawling %s..." % (current_url)
        
            self.visited.add(current_url)
            response = urllib2.urlopen(current_url)
            html = response.read()
            soup = BeautifulSoup(html)

            if current_url != start_url:
                yield self.extract_data(soup)

            for link in soup.find_all("a",
                        attrs={"class": "question-hyperlink"}):
                link_url = urljoin(self.base_url, link.get("href"))
                if (link_url not in self.visited and
                        link_url.startswith(self.base_url + "/questions")):
                    self.remaining.append(link_url)
            
            # Don't crawl too hard.
            time.sleep(self.crawl_rate)


    def extract_data(self, soup):
        question = None
        question_title = soup.title.string
        question_text = None
        question_upvote_count = None

        for question_div in soup.find_all("div", "question"):
            for question_container in question_div.find_all("div", "post-text"):
                question_text = question_container.contents
                break

            for upvote_count_container in question_div.find_all("span", "vote-count-post "): # <- This space is annoying but necessary.
                question_upvote_count = int(upvote_count_container.contents[0])
                break

        if (question_title is not None and
                question_text is not None and
                question_upvote_count is not None):
            question = StackOverflowQuestion(question_title, question_text, question_upvote_count)

        answers = []
       
        for answer_div in soup.find_all("div", "answer"):
            answer_text = None
            answer_upvote_count = None
            
            for answer_container in answer_div.find_all("div", "post-text"):
                answer_text = answer_container.contents
                break

            for upvote_count_span in question_div.find_all("span", "vote-count-post "):
                answer_upvote_count = int(upvote_count_container.contents[0])
                break
            
            if (answer_text is not None and
                    answer_upvote_count is not None):

                answers.append(StackOverflowAnswer(answer_text, answer_upvote_count))

        if question and answers:
            return PageMetadata(question, answers)
        else:
            return None


class PageMetadata(object):
    def __init__(self, question, answers):
        self.question = question
        self.answers = answers

    def __str__(self):
        return "\n".join([str(self.question), str(self.answers)])


class StackOverflowQuestion(object):
    def __init__(self, title, text, upvote_count):
        self.title = title
        self.text = text
        self.upvote_count = upvote_count

    def __str__(self):
        return "\n".join([str(self.title), str(self.text), str(self.upvote_count)])


class StackOverflowAnswer(object):
    def __init__(self, text, upvote_count):
        self.text = text
        self.upvote_count = upvote_count

    def __str__(self):
        return "\n".join([str(self.text), str(self.upvote_count)])


def main():
    crawler = StackOverflowCrawler()
    for page_metadata in crawler.crawl("http://stackoverflow.com/questions/tagged/java"):
        if page_metadata is not None:
            print page_metadata.question.title

if __name__ == "__main__":
    main()
