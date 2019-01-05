'''
爬虫主程序文件
'''
import logging
import urllib.request
import threading
import time
import os
import queue
import random
import imghdr
import shutil
import requests
import config

import utils

class GetImageSpider(threading.Thread):
    '''
    工作线程类，专门根据url下载图片的工作蜘蛛类，爬取图片的小弟
    '''
    def __init__(self, ID, get_task_func, download_func, image_folder):
        threading.Thread.__init__(self)
        self.ID = ID
        self.get_task = get_task_func
        self.image_folder = image_folder
        self.download_func = download_func
        self.is_stop = False

    def run(self):
        logging.info("开启线程： %d" % (self.ID))
        while True:
            url = self.get_task()
            if self.is_stop and url is None:
                break
            elif url is None:
                continue
            self.download_func(url)
        logging.info("线程： %d 退出" % (self.ID))
    def stop(self):
        self.is_stop = True

class GetURLSpider(threading.Thread):
    '''
    工作线程类，专门根据预定义的蜘蛛网（BaseSpiderWeb子类）获取图片URL的工作蜘蛛类，爬取URL的小弟
    '''
    def __init__(self, ID, put_task_func, downloaded_func, Web, dev_mode = True,
                image_folder = ".", keywrods = ""):
        threading.Thread.__init__(self)
        self.ID = ID
        self.web = Web(put_task_func, downloaded_func, 
                        dev_mode, image_folder, keywrods)
        self.backend = self.web.download_backend

    def run(self):
        self.web.start_crawl()

class MasterSpider():
    '''
    蜘蛛包工头，负责招聘(创建)和管理多个工作蜘蛛小弟
    '''
    def __init__(self, web_class_list, image_folder = ".", 
                dev_mode = True, worker_num = 10):
        '''
        Description: 输出化函数
        Args:
            web_class_list: 所有要爬取网站的类名和网站支持的语言，具体的实例化在工作线程中，
                        目前支持的只有中文和英语，列表的格式为：[(class1,"chinese"),(class2,"english"),...]，
            image_folder: 保存图片的文件夹
            worker_num: 工作线程数量
        '''
        self.dev_mode = dev_mode
        self.worker_num = worker_num
        self.work_queue = queue.Queue()                 #任务队列，该类为线程安全
        self.get_url_spiders_list = []                  #下载url的蜘蛛线程对象列表
        self.get_images_spiders_list = []               #下载image的蜘蛛线程对象列表
        self.image_folder = image_folder                #保存图片的路径
        if not os.path.isdir(self.image_folder):
            os.makedirs(self.image_folder)
        #初始化工作线程对象
        not_download_backend_count = 0
        for i, web_class in enumerate(web_class_list):
            # if type(web_class) is not type:
            #     raise ValueError("Error parameter: web_class_list")
            #此处使用lambda的原因是为了将MasterSpider对象与MasterSpider方法绑定，
            #这样在GetURLSpider内部在不用感知类MasterSpider对象的情况下调用其方法，下面
            #创建GetImageSpider对象的情况一样
            if web_class[1] == "chinese":
                keywrods = config.keywords_chinese
            else:
                keywrods = config.keywords_english
            s = GetURLSpider(i, lambda url:self._put_url_2_spider_queue_func(url),
                            lambda url, cookies = None:self._download_and_save_url(url, cookies), web_class[0], self.dev_mode,
                            image_folder = self.image_folder, keywrods = keywrods)
            self.get_url_spiders_list.append(s)
            if not s.backend:
                not_download_backend_count += 1
        #如果所有的线程都不支持后台下载，则没有必要启动后台线程
        if not_download_backend_count == len(web_class_list):
            self.worker_num = 0

        for i in range(self.worker_num):
            s = GetImageSpider(i, lambda: self._get_url_from_queue(),
                                lambda url, cookies = None:self._download_and_save_url(url, cookies), self.image_folder)
            self.get_images_spiders_list.append(s)

        #TODO:后期考虑使用数据库组件，从而在保存断点和历史数据时更有效率
        #以下为从断点抓取功能设计的属性
        self.all_urls_file = "all_img_urls.txt"
        self.downloaded_urls_file = "downloaded_img_urls.txt"           #抓取成功url历史记录文件
        #不允许all_urls_file不存在但是downloaded_urls_file存在的情况
        assert os.path.exists(self.all_urls_file) or not os.path.exists(self.downloaded_urls_file),\
                 "all_img_urls.txt not found but downloaded_img_urls.txt found"

        self.all_file_lock = threading.Lock()                           #所有url文件锁
        self.all_urls_set = set()
        if os.path.exists(self.all_urls_file):
            with open(self.all_urls_file) as f:
                self.all_urls_set = {line.strip() for line in f.readlines()}
        #将文件中所有url加入到队列中，从而达到从断点处开始抓取机制
        if len(self.all_urls_set):
            for url in self.all_urls_set:
                self.work_queue.put(url)

        self.downloaded_file_lock = threading.Lock()                    #抓取成功url历史文件写入锁
        self.downloaded_urls_set = set()
        if os.path.exists(self.downloaded_urls_file):
            with open(self.downloaded_urls_file) as f:
                self.downloaded_urls_set = {line.strip() for line in f.readlines()}
        #比对所有url集合和已抓取url，如果内容相等，说明所有内容都抓取完成，这些文件都可删除
        if len(self.all_urls_set) > 0 and len(self.downloaded_urls_set) > 0 \
            and self.all_urls_set == self.downloaded_urls_set:
            os.remove(self.all_urls_file)
            os.remove(self.downloaded_urls_file)
            self.all_urls_set = set()
            self.downloaded_urls_set = set()

        random.seed(time.time())

    def start(self):
        '''
        Description: 开始干活
        '''
        logging.info("爬虫开始运行...")
        for s in self.get_url_spiders_list:
            s.start()
        for s in self.get_images_spiders_list:
            s.start()
        #等待素有URL线程退出
        for s in self.get_url_spiders_list:
            s.join()
        logging.debug("所有获取URL线程全部退出")
        #任务爬取完成，停止Image线程
        for s in self.get_images_spiders_list:
            s.stop()
            s.join()
        logging.info("所有网站爬取完成")

        #self._remove_redundant_img()

        logging.info("所有任务完成，程序退出")

    def _remove_redundant_img(self):
        logging.info("开始进行去重")
        cur_dir = os.path.abspath(".")
        os.chdir(self.image_folder)
        removed_imgs_folder = "removed_imgs"
        if not os.path.isdir(removed_imgs_folder):
            os.mkdir(removed_imgs_folder)

        imgs_list = [img for img in os.listdir() if os.path.isfile(img)]
        for i  in range(len(imgs_list) - 1):
            for img in imgs_list[i+1:]:
                if utils.compute_similarity_by_rgb_hist(imgs_list[i], img) > 0.95:
                    #此处并未删除文件，而是将重复文件移动到另外的文件夹，从而需使用者确认后手动删除
                    shutil.move(imgs_list[i], removed_imgs_folder)
                    break

        os.chdir(cur_dir)
        logging.info("去重完成，退出")

    def _get_url_from_queue(self):
        '''
        从队列中获取URL任务
        '''
        try:
            url = self.work_queue.get(timeout = 2)
        except queue.Empty as e:
            return None
        self.downloaded_file_lock.acquire()
        if url in self.downloaded_urls_set:
            url = None
        self.downloaded_file_lock.release()
        return url

    def _put_url_2_spider_queue_func(self, url):
        '''
        将URL放入到爬虫任务队列中
        '''
        self.all_file_lock.acquire()
        #重复任务不再入队列
        if url in self.all_urls_set:
            self.all_file_lock.release()
            return
        with open(self.all_urls_file, "a") as f:
            f.write(url+"\n")
        self.all_urls_set.add(url)
        self.all_file_lock.release()
        self.work_queue.put(url)

    def write_succ_url(self, url):
        self.downloaded_file_lock.acquire()
        with open(self.downloaded_urls_file, "a") as f:
            f.write(url+"\n")
        self.downloaded_urls_set.add(url)
        self.downloaded_file_lock.release()

    def _download_and_save_url(self, url, cookies = None):
        if self._download_pic(url, cookies):
            #将下载成功的URL加入到已下载URL集合中
            self.write_succ_url(url)

    def _create_file_name(self, file_ext):
        '''
        Description: 按照格式创建唯一的图片文件名
        Args: 
            file_ext：文件格式后缀，如jpg,png等
        Returns:
            返回保存文件的绝对路径
        '''
        localtime = time.localtime()
        randint = random.randint(1, 1000)
        #图片本地保存格式: "year-month-day-hour-minutes-seconds-randint"+文件格式后缀
        file_name = "%d-%d-%d-%d-%d-%d.%s" % (localtime.tm_year, localtime.tm_mon, localtime.tm_mday, localtime.tm_hour,
                                                localtime.tm_min, localtime.tm_sec, file_ext)
        return os.path.join(self.image_folder, file_name) 

    def _download_pic(self, url, cookies = None):
        '''
        Description: 根据图片url下载图片数据，并保存在指定文件夹
        Args: 
            url: 图片url
        Returns:
            True:下载成功，False下载失败
        '''
        try:
            #使用与浏览器相同的header，防止网站反爬虫机制
            headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'\
                                'image/webp,image/apng,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
#                    'Cache-Control': 'max-age=0',
                    'Connection': 'keep-alive',
#                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '\
                                    '(KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'}
            if cookies:
                jar = requests.cookies.RequestsCookieJar()

                for cookie in cookies:
                    jar.set(cookie["name"], cookie["value"], domain = cookie["domain"], secure = cookie["secure"],
                        expiry = cookie["expiry"], httpOnly = cookie["httpOnly"], path = cookie["path"])

            # req = urllib.request.Request(url=url, headers = self.headers)
            # with urllib.request.urlopen(req, timeout=30) as img_req:
            #     data = img_req.read()
                img_req = requests.get(url, timeout = 10, headers = headers, 
                                        allow_redirects = True, cookies=jar)
            else:
                img_req = requests.get(url, timeout = 10, headers = headers, allow_redirects = True)
            if img_req.status_code != 200:
                logging.error("%s 请求出错, status code: %d" % (url, img_req.status_code))
                return False
            data = img_req.content
            if len(data) == 0:
                return False
            #获取文件格式
            file_ext = imghdr.what("", h = data)
            if file_ext is None:
                logging.error("%s 未知的图片格式" % (url))
                return False
            file_name = self._create_file_name(file_ext)
            with open(file_name, 'wb') as f:
                f.write(data)
        except Exception as e:
            logging.error(u'%s  %s请求出错:%s' % (time.ctime(), url, e))
            return False
        return True

if __name__ == "__main__":
    import test_urls

    logging.basicConfig(level = logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.FATAL)
    #测试用例
    class FakeWeb1:
        def __init__(self, put_task_func, downloaded_func):
            self.download_backend = True
            self.put_task_func = put_task_func
            self.downloaded_func = downloaded_func
            self.urls = test_urls.urls1
        def start_crawl(self):
            for url in self.urls * 2:
                self.put_task_func(url)
                time.sleep(1)
            logging.info("网站1爬取完成")

    class FakeWeb2:
        def __init__(self, put_task_func, downloaded_func):
            self.download_backend = True
            self.put_task_func = put_task_func
            self.downloaded_func = downloaded_func
            self.urls = test_urls.urls2
        def start_crawl(self):
            for url in self.urls:
                self.put_task_func(url)
                time.sleep(1)
            logging.info("网站2爬取完成")
                
    master_spider = MasterSpider([FakeWeb1, FakeWeb2], "./test")
    master_spider.start()
