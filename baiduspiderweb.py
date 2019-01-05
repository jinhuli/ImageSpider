'''
该模块根据basespiderweb定义的抽象类实现了baidu图片的实现类，
本文件实现了使用网站的懒加载模式和分页模式
'''
import logging
from selenium import webdriver
import selenium.common.exceptions as exception
from basespiderweb import BaseSpiderWeb
import time

#懒加载模式实现
class BaiduSpiderWebLazy(BaseSpiderWeb):
    def __init__(self, put_url_2_queue_func, get_img_func = None, dev_mode = True,
                keywrods = ""):
        BaseSpiderWeb.__init__(self, "baidu", "https://image.baidu.com/",
                            load_mode = "lazy",
                            keywords = keywrods, 
                            put_url_2_queue_func = put_url_2_queue_func,
                            get_img_func = get_img_func,
                            dev_mode = dev_mode,
                            able_get_original_from_main_page = True)

    def enter_keywords(self):
        '''
        Description: 页面输入关键字并查询，keywords被复制后该函数必须被重载
        '''
        #知道input输入框
        try:
            inp = self.driver.find_element_by_id("kw")
            if inp is None:
                raise AttributeError("inp is None")
            inp.send_keys(self.keywords)
            submit = self.driver.find_element_by_class_name("s_btn")
            if submit is None:
                raise AttributeError("submit is None")
            submit.submit()
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
            return False
        except AttributeError as e:
            logging.error("%s error: %s" %(self.name, e))
            return False
        return True

    def scroll_slider(self):
        '''
        Description: 操作滚动条不断向下滚定，直到加载完所有内容
        '''
        #每次滚动1500像素
        js="window.scrollBy(0, 1500)"
        img_page_count = 0
        #TODO:是否有更好的方式确定所有内容已经加载完成
        while True:
            self.driver.execute_script(js)
            time.sleep(5)
            image_items = self.driver.find_elements_by_class_name("imgpage")
            if len(image_items) <= img_page_count:
                break
            img_page_count = len(image_items)

    def get_original_urls_this_page(self):
        '''
        Description: 百度可直接从搜索的主页面获取原图URL
        Returns: 
            url: 从新页面上获取到的一张原图片的URL
            None: 未获取到图片URL
        '''
        try:
            img_items = self.driver.find_elements_by_class_name("imgitem")
        except exception.NoSuchElementException as e:
            logging.error("%s, 找不到该元素:%s" % (self.name, e))
            return None  	
        if img_items is None:
            logging.error("%s, img_items is None:%s" % (self.name))
        
        return [item.get_attribute("data-objurl") for item in img_items]

#分页模式实现
class BaiduSpiderWebSplit(BaseSpiderWeb):
    def __init__(self, put_url_2_queue_func, get_img_func = None, dev_mode = True,
                    image_folder = ".", keywrods = ""):
        BaseSpiderWeb.__init__(self, "baidu", "https://image.baidu.com/",
                            load_mode = "split_page",
                            keywords = keywrods, 
                            download_backend = False,
                            get_img_func = get_img_func,
                            put_url_2_queue_func = put_url_2_queue_func,
                            dev_mode = dev_mode,
                            switch_to_split = True,
                            able_get_original_from_main_page = True,
                            image_folder = image_folder)

    def enter_keywords(self):
        '''
        Description: 页面输入关键字并查询，keywords被复制后该函数必须被重载
        '''
        self.driver.maximize_window()
        try:
            #找到input输入框
            inp = self.driver.find_element_by_id("kw")
            if inp is None:
                raise AttributeError("inp is None")
            inp.send_keys(self.keywords)
            submit = self.driver.find_element_by_class_name("s_btn")
            if submit is None:
                raise AttributeError("submit is None")
            submit.submit()
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
            return False
        except AttributeError as e:
            logging.error("%s error: %s" %(self.name, e))
            return False
        return True

    def goto_next_page(self):
        '''
        获取下一个页面数据,该方法中需要判断当前是否为最后一页，
        如果是需要调用set_last_page方法
        '''
        old_url = self.driver.current_url
        try:
            next_span = self.driver.find_element_by_class_name("img-next")
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
            return False
        if next_span is None:
            logging.error("%s error: %s" %(self.name, "next_span is None"))
            self.set_last_page()
            return False
        next_span.click()
        if old_url == self.driver.current_url:
            self.set_last_page()
            return False
        self.save_history_page_url()
        return True
    
    def get_original_urls_this_page(self):
        '''
        Description: 直接从搜索的主页面获取原图URL
        Returns: 
            url: 从新页面上获取到的一张原图片的URL
            None: 未获取到图片URL
        '''
        return [self.driver.current_url]

    def switch_to_split_mode(self):
        '''
        Description: 有些网站从lazy模式可以切换到split_page模式，从而可以方便抓取，
                使用者如果有这种要求时，需重载本方法
        '''
        try:
            first_abs_img = self.driver.find_element_by_name("pn0")
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
        if first_abs_img is not None:
            first_abs_img.click()
            self.driver.switch_to.window(self.driver.window_handles[-1])
            return True
        else:
            logging.error("%s error: %s" %(self.name, "pn0 is None"))
        return False


    def get_img(self, url = None, cookies = None):
        try:
            down_btn = self.driver.find_element_by_css_selector("span.bar-btn.btn-download")
            if down_btn is not None:
                down_btn.click()
                time.sleep(2)
                return True
            else:
                logging.error("%s error: %s" %(self.name, "span.bar-btn.btn-download is None"))
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
        return False
