import logging

from spider import MasterSpider
from baiduspiderweb import BaiduSpiderWebLazy
from baiduspiderweb import BaiduSpiderWebSplit
from spiderweb1688 import SpiderWeb1688
from dogpilespiderweb import DogPileSpiderWeb
from chinasospiderweb import ChinasoSpiderWeb
#import pdb

if __name__ == "__main__":

    logging.basicConfig(level = logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.FATAL)
    logging.getLogger("urllib3").setLevel(logging.FATAL)
    logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.FATAL)

    # master_spider = MasterSpider([(ChinasoSpiderWeb, "chinese")], 
    #                             image_folder="F:\\ImageSpider\\test", dev_mode=True, worker_num=5)
    master_spider = MasterSpider([(ChinasoSpiderWeb, "chinese"),
                                    (DogPileSpiderWeb, "english"),
                                    (BaiduSpiderWebSplit, "chinese")], 
                                dev_mode=True,  
                                image_folder = "F:\\ImageSpider\\test", worker_num = 5)
    #pdb.set_trace()
    master_spider.start()

