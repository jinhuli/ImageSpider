'''
该模块根据basespiderweb定义的抽象类实现了http://www.dogpile.com/?qc=images网站的实现类，
该网站为split_page模式
'''

import logging
from selenium import webdriver
import selenium.common.exceptions as exception
from basespiderweb import BaseSpiderWeb
import time

class DogPileSpiderWeb(BaseSpiderWeb):
    def __init__(self, put_url_2_queue_func, get_img_func = None, dev_mode = True,
                    image_folder = ".", keywrods = ""):
        BaseSpiderWeb.__init__(self, "DogPile", "http://www.dogpile.com/?qc=images",
                        load_mode = "split_page",
                        keywords = keywrods,
                        download_backend = True,
                        put_url_2_queue_func = put_url_2_queue_func,
                        get_img_func = get_img_func,
                        dev_mode = dev_mode,
                        able_get_original_from_main_page = True)

    def enter_keywords(self):
        self.driver.maximize_window()
        try:
            #找到input输入框
            inp = self.driver.find_element_by_id("topSearchTextBox")
            if inp is None:
                raise AttributeError("inp is None")
            inp.send_keys(self.keywords)
            submit = self.driver.find_element_by_id("topSearchSubmit")
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

    def get_original_urls_this_page(self):
        '''
        Description: 直接从搜索的主页面获取原图URL
        Returns: 
            url: 从新页面上获取到的一张原图片的URL
            None: 未获取到图片URL
        '''
        urls = []
        try:
            image_divs = self.driver.find_elements_by_class_name("image")
            if image_divs is None:
                logging.error("%s error: %s" %(self.name, e))
                return urls

            for img_div in image_divs:
                try:
                    img_a = img_div.find_element_by_class_name("link")
                    if img_a is None:
                        logging.error("%s error: %s" %(self.name, "img_a is None"))
                        continue
                    urls.append(img_a.get_attribute("href"))
                except exception.NoSuchElementException as e:
                    logging.error("%s error: %s" %(self.name, e))
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
            return urls

        return urls

    def goto_next_page(self):
        try:
            next_btn = self.driver.find_element_by_css_selector("[class='pagination__num pagination__num--next-prev pagination__num--next']")
        except exception.NoSuchElementException as e:
            #找不到该元素表示已经到最后一页
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

