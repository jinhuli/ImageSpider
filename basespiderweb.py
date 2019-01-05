'''
在本框架中将主程序的爬取代码称为蜘蛛，将要爬取网站的图片资源
称为蜘蛛的猎物，蜘蛛如果要捕获到猎物必须要有网，所以本框架中
将能够获取到网站内部图片的行为定义为类（主要是类内部的方法），蜘蛛（爬取代码）
只要知道自己网的使用方法（定义行为的类），那么就能顺着网捕获到猎物（图片资源），
本文件主要是为该网定义一个抽象的行为类，使用者必须继承该类并重载相应的方法，蜘蛛才能正常工作
'''
import os
from abc import ABCMeta, abstractmethod
import time
import logging
from selenium import webdriver

class BaseSpiderWeb(metaclass=ABCMeta):
    '''
    抽象的蜘蛛网类，此类不可实例化，其他实体爬虫网络类需继承该类并
    对必要的方法进行进行重载，加abstractmethod注解的方法是子类必须实现的
    '''
    @abstractmethod
    def __init__(self, name, url, load_mode, keywords = None, put_url_2_queue_func = None,
                get_img_func = None,download_backend = True, dev_mode = False, user_info = None,
                able_get_original_from_main_page = False, switch_to_split = False,
                popup = False, image_folder = "."):
        ''' 
        Description:  初始化函数,抽象方法
        Args:
            name: 该网站的名称
            url: 网页首页URL
            load_mode: 网页展示内容的方式，是否使用了类似ajax的懒加载机制，或者是否使用了分页显示，
                    目前主流图片网站显示图片模式有：懒加载；分页；分页+懒加载，对应参数必须为
                    ["lazy", "split_page", "lazy_split_page"]，对于后两种模型可使用从中断
                    处重新爬取功能
            keywords: 网站为类似于百度图片的搜索网站，从主页输入图片关键词搜索，方便后期按关键字爬取不同的内容
            download_backend: 图片是否可在后台下载，由于某些网站的反爬虫机制，图片下载的线程必须和原网页一致
            put_url_2_queue_func: 将图片url传递给后台线程任务队列，当download_backend被传递非None值时，
                    该参数也必须非None
            get_img_func: 直接下载图片，而是不是将图片URL放入到后台线程任务队列，当download_backend = False时，
                    指定必须该参数
            dev_mode: 是否以开发者模式运行，开发者模式使用可视化的Chrome webdriver，方便调试，
                    非开发模式使用非可视化的Chrome webdriver headless模式, 方便使用终端服务器抓取
            user_info: 用户信息，字典类型，含有用户名和密码，例如：
                    用于需要登录的网站，由于现在一般登录中的验证码千奇百怪，
                    所以本框架对登录还不能提供完全自动化的处理，此处需要人工手动进行验证，
                    此时框架以开发模式运行，从而使用Chrome webdriver，建议使用者将有用户登录的
                    所有网站放在一个程序中抓取，将没有用户登录的网站放在一个程序中抓取，以提高效率
            able_get_original_from_main_page: 某些网站能从缩略图页面直接拿到原图URL，比如baidu图片，
                    所以添加该选项
            switch_to_split: 是否从lazy模式可以切换到split_page，有些网站从lazy模式可以切换到split_page模式，
                            从而可以方便抓取，该属性赋值为True时，一开始的load_mode应该传入切换后的模式，如
                            split_page或者lazy_split_page
            popup:页面是否会出现弹窗，出现的话，需调用close_popup方法关闭弹窗
            image_folder: 图片保存路径
        Notes:
            子类的初始化方法中只需要接受put_url_2_queue_func、get_img_func、dev_mode和keywords参数，以上其他参数类内部
            都是可以定义好的，而不需要外部使用时再传入
        '''
        self.driver = None
        self.name = name
        self.url = url
        if load_mode not in ["lazy", "split_page", "lazy_split_page"]:
            raise ValueError("Error parameter: load_mode")
        self.load_mode = load_mode
        self.keywords = keywords
        self.download_backend = download_backend
        if self.download_backend and (not put_url_2_queue_func or not callable(put_url_2_queue_func)):
            raise ValueError("Error parameter: put_url_2_queue_func")
        self.put_url_2_queue_func = put_url_2_queue_func

        if not get_img_func and not callable(get_img_func):
            raise ValueError("Error parameter: get_img_func")
        self.get_img_func = get_img_func

        self.dev_mode = dev_mode
        self.able_get_original_from_main_page = able_get_original_from_main_page
        self.switch_to_split = switch_to_split
        self.popup = popup
        self.image_folder = image_folder

        self.user_info = user_info
        if self.user_info:
            if ("username" not in user_info or "password" not in user_info):
                logging.error("Param user_info error")
                raise ValueError("Error parameter: user_info")
            self.dev_mode = True
        self.options = webdriver.ChromeOptions()    #浏览器选项  
        #self.options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
        #如果某些数据需要从浏览器上下载，则需要提供以下下载选项
        prefs = {'profile.default_content_settings.popups': 0, 'download.default_directory': self.image_folder}
        #prefs = {'profile.default_content_settings.popups': 0}
        self.options.add_experimental_option('prefs', prefs)
        #非开发模式使用chrome的headless模式
        if not self.dev_mode:
            #浏览器选项
            self.options.add_argument("--headless")
            self.options.add_argument("--disable-gpu")

        #数据是否为最后一页, 用来记录页面状态，子类应该在触发页面改变的方法中判断是否会
        #改变这个属性的状态
        self.last_page = False

        #以下为从中断处抓取功能设计字段, 单纯的lazy模式没必要使用中断功能
        if not "lazy" == self.load_mode:
            self.history_url_file_name = "%s-history-page.txt" % (self.name)        #记录爬取历史页面的URL文件名
            self.last_page_url = None
            if os.path.isfile(self.history_url_file_name):
                with open(self.history_url_file_name) as f:
                    lines = [line.strip() for line in f.readlines()]
                    if len(lines) > 0:
                        self.last_page_url = lines[-1]

    def __del__(self):
        '''
        Description:  销毁对象时，先关闭driver
        '''
        self.close_driver()

    def start_crawl(self):
        '''
        Description:  启动爬取方法，用于循环调用其他方法爬取网站所有图片数据;
                子类可重载本方法，从而根据网站具体情况自定义循环流程
        '''
        logging.info("网站: %s 开始爬取..." % (self.name))

        #历史页面第一个字符为#，说明是网站最后一页，即之前已经爬取完成
        if not "lazy" == self.load_mode and self.last_page_url[0] == "#":
            logging.info("网站: %s 所有url之前已经爬取完成，退出" % (self.name))
            return

        self.driver = webdriver.Chrome(chrome_options=self.options)
        self.driver.get(self.url)

        self._close_popup()
        #有必要时登录
        if self.user_info:
            self.login()
            # token, sess = self.login()
            # self.token = token              #登录后服务端返回的权限token
            # self.sess = sess                #后续使用的session
            self._close_popup()

        if not "lazy" == self.load_mode and self.last_page_url:
            self.load_last_page()
        else:
            #有必要是输入查询关键字
            if self.keywords:
                self.enter_keywords()
                self._close_popup()

            if self.switch_to_split:
                if not self.switch_to_split_mode():
                    logging.info("网站: %s 无法切换到split模式, 退出" % (self.name))
                    return
                self._close_popup()

        while not self.is_last_page():
            if self.load_mode == "lazy" or self.load_mode == "lazy_split_page":
                self.scroll_slider()

            if self.able_get_original_from_main_page:
                urls = self.get_original_urls_this_page()
            else:
                urls = self.get_abstract_urls_this_page()
            if urls is None:
                logging.error("%s, 当前页面未获取到任何url，退出" % (self.name))
                return
            self.iterate_all_url(urls)

            #lazy模式只有一页，不必循环
            if self.load_mode == "lazy":
                break

            self.goto_next_page()

        logging.info("网站: %s 所有url爬取完成，退出" % (self.name))
        #self.close_driver()

    def iterate_all_url(self, urls):
        '''
        Description: 迭代传入的URL列表，根据self.get_original_from_asbstract
            不同，识别传入的是abstract_urls列表还是original_img_url分别执行不用任务
        Args:
            urls: 传入的URL列表
        '''
        if urls is None:
            return

        for url in urls:
            if self.able_get_original_from_main_page:
                orig_url = url
            else:
                orig_url = self.get_original_img_url(url)
            
            if orig_url is None:
                logging.error("%s, 当前缩略页面%s页面对应的原图url为None" % (self.name, url))
                continue
            if self.download_backend:
                #将图片url传给后台下载
                self.put_url_2_queue_func(orig_url)
            else:
                #直接下载图片
                self.get_img(orig_url)

    def close_driver(self):
        if self.driver is not None:
            self.driver.close()
            self.driver.quit()

    # def get_img(self, url = None):
    #     self.get_img_func(url)

    def scroll_slider(self):
        '''
        Description: 操作滚动条不断向下滚定，直到加载完所有内容
        '''
        #每次滚动1500像素
        js="window.scrollBy(0,1500)"
        #TODO:是否有更好的方式确定所有内容已经加载完成
        for _ in range(10):
            self.driver.execute_script(js)
            self.click_more_btn()
            time.sleep(2)
        time.sleep(2)

    def save_history_page_url(self):
        '''
        Description: 对于分页显示的网站，为了实现从中断页面往后继续爬取，
                抽象类中实现本方法用于保存每次爬取过的中间页面URL，下次中断
                从最近更新的页面进行抓取，为了达到这个目的，对于只有懒加载没
                有分页的网站，可不调用本方法
        Returns:
            True: 执行成功
            False: 执行失败
        '''
        self.last_page_url = self.driver.current_url
        with open(self.history_url_file_name, "w") as f:
            f.write(self.last_page_url + "\n")

    def load_last_page(self):
        '''
        Description: 让浏览器加载最近一次页面URL
                注意: 从文件中加载的最近一次URL已经爬取完成，断点应该从该URL的
                    下一页开始爬取，本方法并为实现进入下一页面功能，使用者
                    需要自己在上层完成，或者调用load_last_next_page方法
        '''
        self.driver.maximize_window()
        if self.driver:
            self.driver.get(self.last_page_url)
    
    def load_last_next_page(self):
        '''
        Description: 让浏览器加载最近一次页面URL的下一页面
                注意: 使用本方法需要先重载goto_next_page方法
        '''
        if self.driver:
            self.driver.get(self.last_page_url)
            time.sleep(3)
            self.goto_next_page()

    def is_last_page(self):
        '''
        Description: 获取是否为当前网站最后一页数据
        Returns: 
            True: 为当前网站最后一页数据
            False: 不是当前网站最后一页数据
        '''
        return self.last_page

    def set_last_page(self):
        self.last_page = True
        self.last_page_url = self.driver.current_url
        with open(self.history_url_file_name, "w") as f:
            f.write("#" + self.last_page_url + "\n")


    def _close_popup(self):
        if self.popup:
            return self.close_popup()
        return True


    #以下定义的方法均为根据实际情况可选重载的方法
    def click_more_btn(self):
        '''
        Description: 某些网站会在滚动条滚动一定位置后显示“more”按钮，点击后
                    才可以再进行滚动加载,此时用户需重载本函数
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

    def enter_keywords(self):
        '''
        Description: 页面输入关键字并查询，keywords被复制后该函数必须被重载
        Returns:
            True: 执行成功
            False: 执行失败
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

    def login(self):
        '''
        Description: 登录方法，须由子类实现，但不是必须实现
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

    def goto_next_page(self):
        '''
        Description: 获取下一个页面数据,该方法中需要判断当前是否为最后一页，
                如果是需要调用set_last_page方法
        Returns:
            True: 执行成功
            False: 执行失败
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

    def get_abstract_urls_this_page(self):
        '''
        Description: 大部分图片网站搜索后显示的都是当前页图片的缩略图，只有根据缩略图链接进入到新的页面才能
                拿到图片的原图URL，本方法就是获取本页面所有缩略图的URL
        Returns: 
            urls: 从当前页面上获取的缩略图URL
            None: 未获取到任何图片URL
        '''
        assert False, "Can't call this function of BaseSpiderWeb"
    
    def get_original_urls_this_page(self):
        '''
        Description: 直接从搜索的主页面获取原图URL
        Returns: 
            url: 从新页面上获取到的一张原图片的URL
            None: 未获取到图片URL
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

    #@abstractmethod
    def get_original_img_url(self, url = ""):
        '''
        Description: 本方法根据缩略图链接进入到原图页面，该新页面中找到原图URL
        Args:
            url: 缩略图URL
        Returns: 
            url: 从新页面上获取到的一张原图片的URL
            None: 未获取到图片URL
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

    def switch_to_split_mode(self):
        '''
        Description: 有些网站从lazy模式可以切换到split_page模式，从而可以方便抓取，
                使用者如果有这种要求时，需重载本方法
        Returns:
            True: 执行成功
            False: 执行失败
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

    def close_popup(self):
        '''
        Description: 关闭弹窗方法，当网站出现弹窗后需首先该方法
        Returns:
            True: 执行成功
            False: 执行失败
        '''
        assert False, "Can't call this function of BaseSpiderWeb"

if __name__ == "__main__":
    class BaiduSpiderWeb(BaseSpiderWeb):
        def __init__(self, put_url_2_queue_func, get_img_func, dev_mode = True):
            BaseSpiderWeb.__init__(self, "baidu", "", "lazy",
                                     put_url_2_queue_func = put_url_2_queue_func,
                                    get_img_func = get_img_func,)
            print("BaiduSpiderWeb __init__")
    b1 = BaiduSpiderWeb(lambda:1, lambda:2)

    try:
        b = BaseSpiderWeb()
    except Exception as e:
        print(e)