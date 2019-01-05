'''
该模块根据basespiderweb定义的抽象类实现了http://image.chinaso.com/网站的实现类，
该网站同时支持懒加载模式和分页模式
'''
import logging
from selenium import webdriver
import selenium.common.exceptions as exception
from basespiderweb import BaseSpiderWeb
import time

#此处实现split_page模式
class ChinasoSpiderWeb(BaseSpiderWeb):
    def __init__(self, put_url_2_queue_func, get_img_func = None, dev_mode = True,
                    image_folder = ".", keywrods = ""):
        BaseSpiderWeb.__init__(self, "Chinaso", "http://image.chinaso.com/",
                        load_mode = "split_page",
                        keywords = keywrods,
                        put_url_2_queue_func = put_url_2_queue_func,
                        get_img_func = get_img_func,
                        dev_mode = dev_mode,
                        switch_to_split = True,
                        able_get_original_from_main_page = True)

    def enter_keywords(self):
        self.driver.maximize_window()
        try:
            #找到input输入框
            inp = self.driver.find_element_by_id("q")
            if inp is None:
                raise AttributeError("inp is None")
            inp.send_keys(self.keywords)
            submit = self.driver.find_element_by_class_name("search_btn2")
            if submit is None:
                raise AttributeError("submit is None")
            submit.click()
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
            div = self.driver.find_element_by_id("ad-image-wrapper-outer")
            if div is None:
                logging.error("%s error: %s" %(self.name, "div is None"))
                return False
            next_span = div.find_element_by_css_selector("a.dt_next.dt_toggle")
            if next_span is None:
                logging.error("%s error: %s" %(self.name, "next_span is None"))
                return False
            next_span.click()
            time.sleep(1)
            if old_url == self.driver.current_url:
                self.set_last_page()
            else:
                self.save_history_page_url()
        except exception.NoSuchElementException as e:
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
        try:
            src_a = self.driver.find_element_by_id("yuanshi")
            return [src_a.get_attribute("href")]
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
            return None

    def switch_to_split_mode(self):
        '''
        Description: 有些网站从lazy模式可以切换到split_page模式，从而可以方便抓取，
                使用者如果有这种要求时，需重载本方法
        '''
        try:
            all_tag = self.driver.find_elements_by_class_name("rg_l")
            if all_tag is None or len(all_tag) <= 1:
                logging.error("%s error: %s" %(self.name, "all_tag is None or insufficient"))
                return False
            first_abs_img = all_tag[1]
            first_abs_img.click()
            self.driver.switch_to.window(self.driver.window_handles[-1])
        except exception.NoSuchElementException as e:
            logging.error("%s error: %s" %(self.name, e))
            return False

        return True
