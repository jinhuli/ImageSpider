'''
该模块根据basespiderweb定义的抽象类实现了1688图片的实现类，
该网站为lazy+split_page模式
'''

import logging
from selenium import webdriver
import selenium.common.exceptions as exception
from basespiderweb import BaseSpiderWeb
import time

class SpiderWeb1688(BaseSpiderWeb):
    def __init__(self, put_url_2_queue_func, get_img_func = None, dev_mode = True,
                    image_folder = ".", keywrods = ""):
        BaseSpiderWeb.__init__(self, "1688", "https://www.1688.com/",
                            load_mode = "lazy_split_page",
                            keywords = keywrods,
                            download_backend = False,
                            put_url_2_queue_func = put_url_2_queue_func,
                            get_img_func = get_img_func,
                            dev_mode = dev_mode,
                            able_get_original_from_main_page = False,
                            popup = True)

    def enter_keywords(self):
        self.driver.maximize_window()
        try:
            #找到input输入框
            inp = self.driver.find_element_by_id("alisearch-keywords")
            if inp is None:
                raise AttributeError("inp is None")
            inp.send_keys(self.keywords)
            submit = self.driver.find_element_by_id("alisearch-submit")
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

    def close_popup(self):
        #1688有两种弹窗
        pop_wind_home = None
        pop_wind_overlay = None
        try:
            pop_wind_home = self.driver.find_element_by_class_name("home-identity-dialog")
        except exception.NoSuchElementException as e:
            try:
                pop_wind_overlay =self.driver.find_element_by_class_name("s-overlay-box")
            except exception.NoSuchElementException as e:
                logging.info("%s : %s" %(self.name, "没有弹窗，继续"))

        try:
            if pop_wind_home:
                close_btn = pop_wind_home.find_element_by_class_name("identity-close")
            else:
                close_btn = pop_wind_overlay.find_element_by_class_name("s-overlay-close")
        except exception.NoSuchElementException as e:
            logging.error("%s : %s" %(self.name, e))
            return False
        if close_btn is None:
            logging.error("%s : %s" %(self.name, "close_btn is None"))
            return False
        if close_btn.is_displayed():
            close_btn.click()
        return True

    def scroll_slider(self):
        js="window.scrollBy(0, 1000)"
        img_page_count = 0
        #TODO:是否有更好的方式确定所有内容已经加载完成
        while True:
            self.driver.execute_script(js)
            time.sleep(5)
            image_items = self.driver.find_elements_by_css_selector("li.sm-offer-item.sw-dpl-offer-item")
            if len(image_items) <= img_page_count:
                break
            img_page_count = len(image_items)

    def goto_next_page(self):
        try:
            next_btn = self.driver.find_element_by_class_name("fui-next")
        except exception.NoSuchElementException as e:
            self.set_last_page()
            logging.error("%s error: %s" %(self.name, e))
            return True
        if next_btn is None:
            logging.error("%s error: %s" %(self.name, "next_btn is None"))
            self.set_last_page()
            return False
        self.save_history_page_url()
        next_btn.click()
        return True

    def get_abstract_urls_this_page(self):
        '''
        Description: 大部分图片网站搜索后显示的都是当前页图片的缩略图，只有根据缩略图链接进入到新的页面才能
                拿到图片的原图URL，本方法就是获取本页面所有进入详细页面的URL,
        Returns: 
            urls: 从当前页面上获取的缩略图URL
            None: 未获取到任何图片URL
        '''
        try:
            items = self.driver.find_elements_by_css_selector("li.sm-offer-item.sw-dpl-offer-item")
        except exception.NoSuchElementException as e:
            logging.error("%s : %s" %(self.name, "没有弹窗，继续"))
            return None

        urls = []
        for item in items:
            try:
                a = item.find_element_by_xpath("div/div/a")
                url = a.get_attribute("href")
                urls.append(url)
            except exception.NoSuchElementException as e:
                logging.info("%s : %s" %(self.name, e))
        
        return urls

    def iterate_all_url(self, urls):
        '''
        Description: 1688的特殊性，此处重载该方法
        Args:
            urls: 传入的URL列表
        '''
        if urls is None:
            return

        #新开一个窗口
        js = 'window.open("");'
        self.driver.execute_script(js)
        self.driver.switch_to_window(self.driver.window_handles[-1])
        for url in urls:
            try:
                self.driver.get(url)
                orig_urls = self.get_original_img_url(url)

                if orig_urls is None:
                    logging.error("%s, 当前缩略页面%s页面对应的原图url为None" % (self.name, url))
                    continue
                for url in orig_urls:
                    if self.download_backend:
                        #将图片url传给后台下载
                        self.put_url_2_queue_func(url)
                    else:
                        #直接下载图片
                        self.get_img(url, self.driver.get_cookies())
            except Exception as e:
                logging.error("%s : %s" %(self.name, e))
        self.driver.close()
        self.driver.switch_to_window(self.driver.window_handles[0])

    def scroll_slider_in_detail_page(self):
        js="window.scrollBy(0, 1500)"
        img_count = -1
        #TODO:是否有更好的方式确定所有内容已经加载完成
        while True:
            self.driver.execute_script(js)
            time.sleep(3)
            self.driver.execute_script(js)
            time.sleep(3)
            detail = self.driver.find_element_by_id("mod-detail-description")
            img = detail.find_elements_by_tag_name("img")
            if img_count == len(img):
                break
            img_count = len(img)

    def get_original_img_url(self, url = None):
        #详细页面也有懒加载
        self.scroll_slider_in_detail_page()
        urls = []
        try:
            detail = self.driver.find_element_by_id("mod-detail-description")
            img_items = detail.find_elements_by_tag_name("img")
            urls = [item.get_attribute("src") for item in img_items]
        except exception.NoSuchElementException as e:
                logging.info("%s : %s" %(self.name, e))
        return urls

